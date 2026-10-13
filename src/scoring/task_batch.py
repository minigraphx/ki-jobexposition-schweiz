"""Batch-Modus der aufgabenbasierten Bewertung (Rubrik v2.2) — 50 % günstiger, Ergebnis bis 24 h.

Aufgerufen über ``task_scorer.py --provider claude|gemini --batch submit|status|collect|followup``.
Gleiche Prompts, Schemas und Validierung wie im synchronen Modus; die Ergebnisse landen im
gleichen Format unter ``data/processed/bewertungen/<provider>/run<N>/`` (``meta.modus = "batch"``).

Zustand (robust gegen Abbruch, Terminal darf geschlossen werden): je eingereichtem Batch eine Datei
``data/processed/bewertungen/<provider>/batches/<batch_id>.json`` mit custom_id → Eintrag/Lauf/
Input-Hash, Modell, Rubrik-Version, Einstellungen und Zeitpunkt (keine Keys). ``collect`` holt nur
fertige, noch nicht eingesammelte Batches und ist damit idempotent.

Provider
    claude   Message Batches API: ``client.messages.batches.create/retrieve/results``. Ergebnisse
             kommen in beliebiger Reihenfolge → Zuordnung strikt über ``custom_id``
             (``^[a-zA-Z0-9_-]{1,64}$``). Der Refusal-Fallback (``fallbacks``) wird von der
             Batches-API abgelehnt → im Batch ohne Fallback; Refusals werden protokolliert und mit
             ``followup --refusal-sync`` synchron mit Fallback nachgeholt. Prompt-Caching des
             System-Prompts im Batch (Treffer «best effort», laut Doku typisch 30–98 %). Standard-TTL
             5 min: ein Fehltreffer kostet dann 1.25× statt 2× (1 h) des Input-Preises, bleibt also
             auch bei tiefer Trefferquote unter «ohne Cache». Die Doku regt für Batches die 1-h-TTL
             an (bessere Trefferquote) → ``--cache-ttl 1h``; der Dry-Run zeigt beide Grenzfälle.
    gemini   Gemini Batch Mode: ``client.batches.create(model, src=[InlinedRequest…])`` mit derselben
             GenerateContentConfig wie synchron (system_instruction, response_json_schema,
             thinking_config) je Anfrage; Inline-Anfragen < 20 MB je Batch → automatisch in mehrere
             Batches geteilt. Zuordnung über ``metadata.custom_id`` (vom SDK in der Antwort
             zurückgegeben); nur wenn keine Antwort Metadaten trägt und die Anzahl stimmt, über die
             Position (in ``meta.zuordnung`` vermerkt; isco_code/beruf werden ohnehin geprüft).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator

import task_inputs as ti
import task_rubrik as tr
import task_scorer as ts

log = logging.getLogger("task_batch")

CUSTOM_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")     # Vorgabe der Message Batches API
CLAUDE_MAX_ANFRAGEN = 100_000                           # Limit je Batch: 100 000 Anfragen oder 256 MB
CLAUDE_MAX_BYTES = 200_000_000
GEMINI_MAX_ANFRAGEN = 10_000
GEMINI_MAX_BYTES = 15_000_000                           # Inline-Anfragen: Gesamtgrösse < 20 MB
GEMINI_FERTIG = {"JOB_STATE_SUCCEEDED", "JOB_STATE_PARTIALLY_SUCCEEDED", "JOB_STATE_FAILED",
                 "JOB_STATE_CANCELLED", "JOB_STATE_EXPIRED"}
GEMINI_SPERRGRUENDE = {"SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII", "IMAGE_SAFETY"}


def custom_id(lauf: int, e: ti.Eintrag) -> str:
    cid = f"r{lauf}-{e.schluessel}"
    if not CUSTOM_ID_RE.match(cid):
        cid = f"r{lauf}-{re.sub(r'[^0-9]', '', e.isco_code)[:8]}-{hashlib.sha1(e.schluessel.encode()).hexdigest()[:16]}"
    return cid


@dataclass
class Auftrag:
    eintrag: ti.Eintrag
    lauf: int
    typ: str = "neu"                  # neu | wiederholung | korrektur | dritter_lauf
    versuch: int = 1
    korrektur: tuple[str, list[str]] | None = None    # (bisherige Antwort, Validierungsfehler)
    verlauf: Any = None

    @property
    def cid(self) -> str:
        return custom_id(self.lauf, self.eintrag)


# --------------------------------------------------------------------------- Provider-Adapter

class ClaudeBatchAPI:
    provider = "claude"
    max_anfragen, max_bytes = CLAUDE_MAX_ANFRAGEN, CLAUDE_MAX_BYTES

    def __init__(self, bewerter: ts.ClaudeBewerter, cache_ttl: str = "5m"):
        self.bewerter, self.cache_ttl = bewerter, cache_ttl

    def einstellungen(self) -> dict:
        return {**self.bewerter.einstellungen(), "fallbacks": None, "cache_ttl": self.cache_ttl, "modus": "batch"}

    def anfrage(self, cid: str, verlauf: list[dict]) -> dict:
        params = self.bewerter._anfrage(verlauf)
        params.pop("betas", None)            # Refusal-Fallback wird von der Batches-API abgelehnt
        params.pop("fallbacks", None)
        cc = {"type": "ephemeral"} if self.cache_ttl == "5m" else {"type": "ephemeral", "ttl": self.cache_ttl}
        params["system"] = [{**b, "cache_control": cc} for b in params["system"]]
        return {"custom_id": cid, "params": params}

    @staticmethod
    def groesse(req: dict) -> int:
        return len(json.dumps(req, ensure_ascii=False).encode("utf-8"))

    def _api(self, fn: Callable[[], Any]) -> Any:
        import anthropic
        try:
            return fn()
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as e:
            raise ts.FatalerFehler(f"Anthropic: Zugriff verweigert ({e.status_code}) — ANTHROPIC_API_KEY prüfen") from e
        except anthropic.NotFoundError as e:
            raise ts.FatalerFehler(f"Anthropic: Batch oder Modell nicht gefunden: {e.message}") from e
        except anthropic.APIStatusError as e:
            raise ts.FatalerFehler(f"Anthropic-Batch-API: Fehler {e.status_code}: {e.message} "
                                   "(Zustand ist gespeichert — Befehl später wiederholen)") from e
        except anthropic.APIConnectionError as e:
            raise ts.FatalerFehler(f"Anthropic-Batch-API: Verbindungsfehler: {e} — später wiederholen") from e

    def einreichen(self, anfragen: list[dict]) -> str:
        return self._api(lambda: self.bewerter.client.messages.batches.create(requests=anfragen)).id

    def status(self, batch_id: str) -> dict:
        b = self._api(lambda: self.bewerter.client.messages.batches.retrieve(batch_id))
        st = getattr(b, "processing_status", None)
        return {"status": st, "fertig": st == "ended", "zaehler": ts._als_dict(getattr(b, "request_counts", None)),
                "ablauf": str(getattr(b, "expires_at", "") or "") or None}

    def ergebnisse(self, batch_id: str, reihenfolge: list[str]) -> Iterator[tuple[str, str, Any, str]]:
        for r in self._api(lambda: self.bewerter.client.messages.batches.results(batch_id)):
            res = r.result
            typ = getattr(res, "type", None)
            payload = getattr(res, "message", None) if typ == "succeeded" else getattr(res, "error", None)
            yield r.custom_id, typ, payload, "custom_id"

    def auswerten(self, payload: Any) -> ts.Antwort:
        a = self.bewerter._auswerten(payload)
        a.request_id = getattr(payload, "id", None)
        return a

    @staticmethod
    def ist_refusal(fehler: str, roh: dict) -> bool:
        return roh.get("stop_reason") == "refusal"


class GeminiBatchAPI:
    provider = "gemini"
    max_anfragen, max_bytes = GEMINI_MAX_ANFRAGEN, GEMINI_MAX_BYTES

    def __init__(self, bewerter: ts.GeminiBewerter):
        self.bewerter = bewerter

    @property
    def max_output_tokens(self) -> int:
        return min(self.bewerter.max_output_tokens, ts.GEMINI_BATCH_MAX_OUTPUT_TOKENS)

    def einstellungen(self) -> dict:
        return {**self.bewerter.einstellungen(), "max_output_tokens": self.max_output_tokens, "modus": "batch"}

    def anfrage(self, cid: str, verlauf: list) -> Any:
        from google.genai import types
        return types.InlinedRequest(contents=verlauf, config=self.bewerter._config(self.max_output_tokens),
                                    metadata={"custom_id": cid})

    @staticmethod
    def groesse(req: Any) -> int:
        return len(json.dumps(req.model_dump(mode="json", exclude_none=True), ensure_ascii=False).encode("utf-8"))

    def _api(self, fn: Callable[[], Any]) -> Any:
        from google.genai import errors
        try:
            return fn()
        except errors.ClientError as e:
            if e.code in (401, 403):
                raise ts.FatalerFehler(f"Gemini: Zugriff verweigert ({e.code}) — GEMINI_API_KEY/GOOGLE_API_KEY "
                                       "und Paid-Tier prüfen") from e
            raise ts.FatalerFehler(f"Gemini-Batch-API: Fehler {e.code}: {e.message} "
                                   "(Zustand ist gespeichert — Befehl später wiederholen)") from e
        except errors.APIError as e:
            raise ts.FatalerFehler(f"Gemini-Batch-API: Fehler {e.code}: {e.message} — später wiederholen") from e
        except ts._netzfehler() as e:
            raise ts.FatalerFehler(f"Gemini-Batch-API: Verbindungsfehler: {e} — später wiederholen") from e

    def einreichen(self, anfragen: list) -> str:
        name = f"ki-jobexposition {self.bewerter.model} {ts._jetzt()}"
        job = self._api(lambda: self.bewerter.client.batches.create(model=self.bewerter.model, src=anfragen,
                                                                     config={"display_name": name}))
        return job.name

    @staticmethod
    def _zustand(job: Any) -> str | None:
        st = getattr(job, "state", None)
        return getattr(st, "name", None) or (str(st) if st is not None else None)

    def status(self, batch_id: str) -> dict:
        job = self._api(lambda: self.bewerter.client.batches.get(name=batch_id))
        st = self._zustand(job)
        zaehler = ts._als_dict(getattr(job, "completion_stats", None))
        antworten = getattr(getattr(job, "dest", None), "inlined_responses", None)
        if not zaehler and antworten:
            zaehler = {"antworten": len(antworten), "fehler": sum(1 for r in antworten if getattr(r, "error", None))}
        return {"status": st, "fertig": st in GEMINI_FERTIG, "zaehler": zaehler or None, "ablauf": None}

    def ergebnisse(self, batch_id: str, reihenfolge: list[str]) -> Iterator[tuple[str, str, Any, str]]:
        job = self._api(lambda: self.bewerter.client.batches.get(name=batch_id))
        antworten = list(getattr(getattr(job, "dest", None), "inlined_responses", None) or [])
        ids = [(getattr(r, "metadata", None) or {}).get("custom_id") for r in antworten]
        positionell = not any(ids) and len(antworten) == len(reihenfolge)
        if not any(ids) and antworten and not positionell:
            log.error("Gemini-Batch %s: Antworten ohne custom_id und Anzahl %d ≠ %d — nicht zuordenbar",
                      batch_id, len(antworten), len(reihenfolge))
        for i, r in enumerate(antworten):
            cid, zuordnung = ids[i], "custom_id"
            if not cid:
                if not positionell:
                    continue
                cid, zuordnung = reihenfolge[i], "position"
            if getattr(r, "error", None) is not None or getattr(r, "response", None) is None:
                yield cid, "errored", getattr(r, "error", None), zuordnung
            else:
                yield cid, "succeeded", r.response, zuordnung

    def auswerten(self, payload: Any) -> ts.Antwort:
        return self.bewerter._auswerten(payload, self.max_output_tokens)

    @staticmethod
    def ist_refusal(fehler: str, roh: dict) -> bool:
        return fehler.startswith("Prompt blockiert") or roh.get("stop_reason") in GEMINI_SPERRGRUENDE


def erstelle_api(bewerter: Any, cache_ttl: str = "5m") -> Any:
    return ClaudeBatchAPI(bewerter, cache_ttl) if bewerter.provider == "claude" else GeminiBatchAPI(bewerter)


# --------------------------------------------------------------------------- Zustandsdateien

def batch_dir(basis: Path, provider: str) -> Path:
    return basis / provider / "batches"


def zustand_pfad(basis: Path, provider: str, batch_id: str) -> Path:
    return batch_dir(basis, provider) / (re.sub(r"[^A-Za-z0-9_.-]", "_", batch_id) + ".json")


def lade_zustaende(basis: Path, provider: str) -> list[tuple[Path, dict]]:
    res = []
    for p in sorted(batch_dir(basis, provider).glob("*.json")):
        try:
            res.append((p, json.loads(p.read_text(encoding="utf-8"))))
        except (OSError, json.JSONDecodeError) as e:
            log.warning("Zustandsdatei %s nicht lesbar: %s", p, e)
    return sorted(res, key=lambda x: x[1].get("erstellt") or "")


def offene_schluessel(zustaende: list[tuple[Path, dict]]) -> dict[tuple[int, str], dict]:
    """(lauf, datei) → Anfrage-Info aller noch nicht eingesammelten Batches."""
    res = {}
    for _, z in zustaende:
        if z.get("eingesammelt"):
            continue
        for info in (z.get("anfragen") or {}).values():
            res[(info["lauf"], info["datei"])] = {**info, "batch_id": z["batch_id"], "model": z.get("model")}
    return res


def ist_offen(offen: dict, lauf: int, e: ti.Eintrag, model: str) -> bool:
    o = offen.get((lauf, e.datei))
    return bool(o) and o.get("input_hash") == e.input_hash and o.get("model") == model


# --------------------------------------------------------------------------- Einreichen

def teile(reqs: list[tuple[Auftrag, Any, int]], max_anfragen: int, max_bytes: int) -> list[list]:
    teile_, akt, groesse = [], [], 0
    for item in reqs:
        if akt and (len(akt) >= max_anfragen or groesse + item[2] > max_bytes):
            teile_.append(akt)
            akt, groesse = [], 0
        akt.append(item)
        groesse += item[2]
    if akt:
        teile_.append(akt)
    return teile_


def einreichen(api: Any, auftraege: list[Auftrag], basis: Path, art: str, force: bool) -> list[str]:
    """Anfragen bauen, (ggf. geteilt) einreichen und je Batch sofort die Zustandsdatei schreiben."""
    bewerter = api.bewerter
    reqs = []
    for a in auftraege:
        if a.verlauf is None:
            a.verlauf = bewerter.start(a.eintrag.input)
            if a.korrektur:
                text, probleme = a.korrektur
                antwort = ts.Antwort(text=text, model_served=None, stop_reason=None, usage={})
                a.verlauf = bewerter.weiter(a.verlauf, antwort, probleme)
        req = api.anfrage(a.cid, a.verlauf)
        reqs.append((a, req, api.groesse(req)))
    cids = [a.cid for a in auftraege]
    if len(set(cids)) != len(cids):
        raise ts.FatalerFehler("custom_id nicht eindeutig (gleicher Eintrag und Lauf doppelt)")
    ids = []
    for teil in teile(reqs, api.max_anfragen, api.max_bytes):
        batch_id = api.einreichen([r for _, r, _ in teil])
        z = {
            "provider": api.provider,
            "batch_id": batch_id,
            "art": art,
            "model": bewerter.model,
            "rubrik_version": tr.RUBRIK_VERSION,
            "erstellt": ts._jetzt(),
            "einstellungen": api.einstellungen(),
            "force": force,
            "anzahl": len(teil),
            "bytes": sum(g for _, _, g in teil),
            "reihenfolge": [a.cid for a, _, _ in teil],
            "anfragen": {a.cid: {"isco_code": a.eintrag.isco_code, "beruf": a.eintrag.beruf, "datei": a.eintrag.datei,
                                 "lauf": a.lauf, "input_hash": a.eintrag.input_hash, "typ": a.typ,
                                 "versuch": a.versuch} for a, _, _ in teil},
            "letzter_status": None,
            "eingesammelt": None,
            "ergebnis": None,
        }
        ts._schreibe_json(zustand_pfad(basis, api.provider, batch_id), z)
        log.info("Batch %s eingereicht: %d Anfragen (%.1f MB)", batch_id, len(teil), z["bytes"] / 1e6)
        ids.append(batch_id)
    return ids


# --------------------------------------------------------------------------- Einsammeln

@dataclass
class Sammlung:
    zaehler: Counter = field(default_factory=Counter)
    offen: list[str] = field(default_factory=list)
    eingesammelt: list[str] = field(default_factory=list)
    probleme: list[str] = field(default_factory=list)
    usage: list[dict] = field(default_factory=list)


def verarbeite(api: Any, z: dict, info: dict, e: ti.Eintrag, typ: str, payload: Any,
               zuordnung: str) -> tuple[ts.Ergebnis, str]:
    """Ein Batch-Ergebnis → (Ergebnis wie im synchronen Modus, Kategorie)."""
    usage: dict = {}
    roh: dict = {}
    antwort = None
    bewertung, rohtext, probleme, hinweise, fehler = None, None, [], [], []
    if typ == "succeeded":
        try:
            antwort = api.auswerten(payload)
        except ts.AntwortFehler as ex:
            roh = ex.roh or {}
            usage = roh.get("usage") or {}
            fehler = [str(ex)]
            kat = "refusal" if api.ist_refusal(str(ex), roh) else "antwort"
        else:
            usage = antwort.usage or {}
            rohtext = antwort.text
            try:
                kandidat = ts.parse_json_text(antwort.text)
                probleme = tr.pruefe_bewertung(kandidat, e.input)
            except json.JSONDecodeError as ex:
                kandidat, probleme = None, [f"kein gültiges JSON: {ex}"]
            if probleme:
                kat = "validierung"
                fehler = [f"Versuch {info.get('versuch', 1)}: " + "; ".join(probleme[:10])]
            else:
                kat, bewertung, hinweise, rohtext = "ok", kandidat, tr.hinweise(kandidat), None
    else:
        detail = ts._als_dict(payload)
        kat = typ or "unbekannt"
        fehler = [f"Batch-Ergebnis «{kat}»" + (f": {json.dumps(detail, ensure_ascii=False)[:500]}" if detail else "")]
    ok = kat == "ok"
    meta = {
        "provider": api.provider,
        "model_requested": z.get("model"),
        "model_served": antwort.model_served if antwort else roh.get("model_served"),
        "fallback": None,
        "rubrik_version": z.get("rubrik_version"),
        "input_hash": info.get("input_hash"),
        "isco_code": e.isco_code,
        "beruf": e.beruf,
        "lauf": info["lauf"],
        "reihenfolge_seed": None,
        "timestamp": ts._jetzt(),
        "einstellungen": z.get("einstellungen"),
        "stop_reason": antwort.stop_reason if antwort else roh.get("stop_reason"),
        "stop_details": roh.get("stop_details"),
        "usage": usage,
        "usage_je_versuch": [usage] if usage else [],
        "request_ids": [antwort.request_id] if antwort and antwort.request_id else [],
        "versuche": info.get("versuch", 1),
        "status": "ok" if ok else "fehlgeschlagen",
        "fehler": fehler,
        "hinweise": hinweise,
        "modus": "batch",
        "batch_id": z["batch_id"],
        "custom_id": custom_id(info["lauf"], e),
        "anfrage_typ": info.get("typ"),
        "batch_ergebnis": typ,
        "fehler_art": None if ok else kat,
        "probleme": probleme if kat == "validierung" else [],
        "zuordnung": zuordnung,
    }
    return ts.Ergebnis(meta["status"], bewertung, meta, rohtext), kat


def _speichern(basis: Path, api: Any, z: dict, e: ti.Eintrag, erg: ts.Ergebnis, protokoll: ts.Protokoll,
               s: Sammlung) -> None:
    pfad = ts.ziel_pfad(basis, api.provider, erg.meta["lauf"], e)
    if not z.get("force") and ts.ist_aktuell(ts.lade_ergebnis(pfad), e, z.get("model")):
        s.zaehler["behalten"] += 1
        log.info("run%d/%s: vorhandene gültige Bewertung bleibt (Batch-Ergebnis: %s)",
                 erg.meta["lauf"], e.datei, erg.status)
        return
    ts.speichere(pfad, erg)
    protokoll.schreibe({"timestamp": erg.meta["timestamp"], "lauf": erg.meta["lauf"], "datei": e.datei,
                        "status": erg.status, "model_served": erg.meta["model_served"], "fallback": False,
                        "usage": erg.meta["usage"], "fehler": erg.meta["fehler"], "modus": "batch",
                        "batch_id": z["batch_id"], "custom_id": erg.meta["custom_id"],
                        "fehler_art": erg.meta["fehler_art"]})


def einsammeln(api: Any, basis: Path, alle: list[ti.Eintrag], protokoll: ts.Protokoll,
               batch_id: str | None = None) -> Sammlung:
    nach_datei = {e.datei: e for e in alle}
    s = Sammlung()
    for pfad, z in lade_zustaende(basis, api.provider):
        if z.get("eingesammelt") or (batch_id and z.get("batch_id") != batch_id):
            continue
        st = api.status(z["batch_id"])
        z["letzter_status"] = {**st, "abgefragt": ts._jetzt()}
        if not st["fertig"]:
            ts._schreibe_json(pfad, z)
            s.offen.append(f"{z['batch_id']} ({st['status']})")
            continue
        gesehen: set[str] = set()
        zaehler: Counter = Counter()
        for cid, typ, payload, zuordnung in api.ergebnisse(z["batch_id"], z.get("reihenfolge") or []):
            info = (z.get("anfragen") or {}).get(cid)
            if info is None or cid in gesehen:
                log.warning("Batch %s: unbekannte oder doppelte custom_id %s — ignoriert", z["batch_id"], cid)
                zaehler["unbekannt"] += 1
                continue
            gesehen.add(cid)
            e = nach_datei.get(info["datei"])
            if e is None:
                log.warning("Batch %s: Eintrag %s nicht mehr in scores.csv — ignoriert", z["batch_id"], info["datei"])
                zaehler["unbekannt"] += 1
                continue
            erg, kat = verarbeite(api, z, info, e, typ, payload, zuordnung)
            zaehler[kat] += 1
            s.usage.append(erg.meta["usage"])
            if kat != "ok":
                s.probleme.append(f"run{info['lauf']}/{e.datei}: [{kat}] {'; '.join(erg.meta['fehler'])[:300]}")
            _speichern(basis, api, z, e, erg, protokoll, s)
        for cid in z.get("reihenfolge") or []:
            if cid in gesehen:
                continue
            info = z["anfragen"][cid]
            e = nach_datei.get(info["datei"])
            if e is None:
                continue
            erg, _ = verarbeite(api, z, info, e, "fehlt", {"hinweis": "kein Ergebnis im Batch"}, "custom_id")
            zaehler["fehlt"] += 1
            s.probleme.append(f"run{info['lauf']}/{e.datei}: [fehlt] kein Ergebnis im Batch ({st['status']})")
            _speichern(basis, api, z, e, erg, protokoll, s)
        z["eingesammelt"] = ts._jetzt()
        z["ergebnis"] = dict(zaehler)
        ts._schreibe_json(pfad, z)
        s.zaehler.update(zaehler)
        s.eingesammelt.append(z["batch_id"])
        log.info("Batch %s eingesammelt: %s", z["batch_id"], dict(zaehler))
    return s


# --------------------------------------------------------------------------- Followup-Auswahl

def followup_auswahl(bewerter: Any, eintraege: list[ti.Eintrag], basis: Path, runs: int, offen: dict,
                     dritter: bool, schwelle: float) -> tuple[list[Auftrag], list[tuple[ti.Eintrag, int]], int]:
    """(a) ungültige/fehlgeschlagene Ergebnisse → Wiederholung bzw. Korrektur; (b) Lauf 3 bei |Δζ| > Schwelle.

    Refusals werden separat zurückgegeben (synchroner Nachlauf). Einträge in offenen Batches und
    aktuelle gültige Ergebnisse werden übersprungen. Rückgabe: (Aufträge, Refusals, fehlende Dateien).
    """
    provider, model = bewerter.provider, bewerter.model
    laeufe = set(range(1, runs + 1))
    if (basis / provider / "run3").is_dir():
        laeufe.add(3)
    auftraege: list[Auftrag] = []
    refusals: list[tuple[ti.Eintrag, int]] = []
    fehlend = 0
    gewaehlt: set[tuple[int, str]] = set()
    for lauf in sorted(laeufe):
        for e in eintraege:
            if ist_offen(offen, lauf, e, model):
                continue
            d = ts.lade_ergebnis(ts.ziel_pfad(basis, provider, lauf, e))
            if d is None:
                fehlend += lauf <= runs
                continue
            if ts.ist_aktuell(d, e, model):
                continue
            m = d.get("meta") or {}
            if m.get("fehler_art") == "refusal" or m.get("stop_reason") == "refusal":
                refusals.append((e, lauf))
                continue
            versuche = int(m.get("versuche") or 1)
            if (m.get("fehler_art") == "validierung" and d.get("rohantwort") and m.get("probleme")
                    and m.get("input_hash") == e.input_hash and m.get("model_requested") == model
                    and versuche <= ts.VALIDIERUNGS_KORREKTUREN):
                auftraege.append(Auftrag(e, lauf, "korrektur", versuche + 1, (d["rohantwort"], m["probleme"])))
            else:
                auftraege.append(Auftrag(e, lauf, "wiederholung"))
            gewaehlt.add((lauf, e.datei))
    if dritter:
        for e in ts.kandidaten_dritter_lauf(provider, eintraege, basis, schwelle):
            if (3, e.datei) in gewaehlt or ist_offen(offen, 3, e, model):
                continue
            d3 = ts.lade_ergebnis(ts.ziel_pfad(basis, provider, 3, e))
            if d3 is not None:
                continue      # vorhanden: aktuell, oder oben als Wiederholung/Refusal behandelt
            auftraege.append(Auftrag(e, 3, "dritter_lauf"))
    return auftraege, refusals, fehlend


# --------------------------------------------------------------------------- Befehle

def _kosten(a: argparse.Namespace, bewerter: Any, eintraege: list[ti.Eintrag], n: int, n3: int,
            basis: Path) -> str:
    s = ts.schaetze(bewerter, eintraege, n, n3, basis=basis, cache_ttl=a.cache_ttl)
    return ts.formatiere_schaetzung(bewerter.provider, bewerter.model, s, batch=True)


def _vorbereiten(provider: str) -> None:
    ts.pruefe_pakete(provider)
    ts.pruefe_keys(provider)


def cmd_submit(a: argparse.Namespace, api: Any, eintraege: list[ti.Eintrag], basis: Path) -> int:
    bewerter = api.bewerter
    offen = offene_schluessel(lade_zustaende(basis, api.provider))
    auftraege, n_aktuell, n_offen = [], 0, 0
    for lauf in range(1, a.runs + 1):
        for e in ts.reihenfolge(eintraege, lauf):
            if not a.force:
                if ts.ist_aktuell(ts.lade_ergebnis(ts.ziel_pfad(basis, api.provider, lauf, e)), e, bewerter.model):
                    n_aktuell += 1
                    continue
                if ist_offen(offen, lauf, e, bewerter.model):
                    n_offen += 1
                    continue
            auftraege.append(Auftrag(e, lauf, "neu"))
    print(f"{len(eintraege)} Einträge × {a.runs} Läufe: {len(auftraege)} einzureichen, {n_aktuell} aktuell, "
          f"{n_offen} bereits in offenen Batches")
    if a.dry_run:
        n3 = len(eintraege) if (a.runs == 2 and not a.no_third_run) else 0
        print(_kosten(a, bewerter, eintraege, len(auftraege), n3, basis))
        return 0
    if not auftraege:
        print("Nichts einzureichen.")
        return 0
    _vorbereiten(api.provider)
    ids = einreichen(api, auftraege, basis, "submit", a.force)
    print(f"Eingereicht: {len(ids)} Batch(es) — {', '.join(ids)}")
    print(f"Zustand: {batch_dir(basis, api.provider)}/ · Laufzeit meist < 1 h, höchstens 24 h; "
          "das Terminal darf geschlossen werden.")
    print(f"Weiter: task_scorer.py --provider {api.provider} --batch status  bzw.  --batch collect")
    return 0


def cmd_status(a: argparse.Namespace, api: Any, basis: Path) -> int:
    zust = lade_zustaende(basis, api.provider)
    offen = [(p, z) for p, z in zust if not z.get("eingesammelt") and (not a.batch_id or z["batch_id"] == a.batch_id)]
    n_fertig = sum(1 for _, z in zust if z.get("eingesammelt"))
    if not offen:
        print(f"Keine offenen Batches ({n_fertig} bereits eingesammelt).")
        return 0
    _vorbereiten(api.provider)
    for p, z in offen:
        st = api.status(z["batch_id"])
        z["letzter_status"] = {**st, "abgefragt": ts._jetzt()}
        ts._schreibe_json(p, z)
        zaehler = json.dumps(st.get("zaehler"), ensure_ascii=False) if st.get("zaehler") else "—"
        print(f"{z['batch_id']}  {st['status']}  {z['anzahl']} Anfragen ({z['art']})  eingereicht {z['erstellt']}"
              f"  Zähler: {zaehler}" + ("  → fertig, bitte --batch collect" if st["fertig"] else ""))
    print(f"{len(offen)} offen · {n_fertig} bereits eingesammelt")
    return 0


def cmd_collect(a: argparse.Namespace, api: Any, basis: Path, protokoll: ts.Protokoll,
                alle: Callable[[], list[ti.Eintrag]]) -> int:
    if not any(not z.get("eingesammelt") for _, z in lade_zustaende(basis, api.provider)):
        print("Keine offenen Batches — nichts einzusammeln.")
        return 0
    _vorbereiten(api.provider)
    s = einsammeln(api, basis, alle(), protokoll, a.batch_id)
    z = s.zaehler
    print(f"Eingesammelt: {len(s.eingesammelt)} Batch(es) · {z['ok']} ok, {z['validierung']} ungültig, "
          f"{z['refusal']} Refusal, {z['antwort'] + z['errored'] + z['expired'] + z['canceled'] + z['fehlt']} "
          f"Fehler/abgelaufen/fehlend, {z['behalten']} vorhandene gültige behalten")
    if s.usage:
        print(ts.token_zeile(api.provider, s.usage))
    for o in s.offen:
        print(f"  noch nicht fertig: {o}")
    for p in s.probleme:
        print(f"  {p}")
    if s.probleme:
        hinweis = " (Refusals: --refusal-sync)" if z["refusal"] else ""
        print(f"Weiter: task_scorer.py --provider {api.provider} --batch followup{hinweis}")
    return 1 if s.probleme else 0


def cmd_followup(a: argparse.Namespace, api: Any, eintraege: list[ti.Eintrag], basis: Path,
                 protokoll: ts.Protokoll, schlafen: Callable[[float], None]) -> int:
    bewerter = api.bewerter
    offen = offene_schluessel(lade_zustaende(basis, api.provider))
    dritter = a.runs == 2 and not a.no_third_run
    auftraege, refusals, fehlend = followup_auswahl(bewerter, eintraege, basis, a.runs, offen, dritter, a.threshold)
    typen = Counter(x.typ for x in auftraege)
    print(f"Followup: {typen['wiederholung']} Wiederholungen, {typen['korrektur']} Korrekturen, "
          f"{typen['dritter_lauf']} dritte Läufe (|Δζ| > {a.threshold:g}), {len(refusals)} Refusals"
          + (f" · {fehlend} noch nie eingereicht (→ --batch submit)" if fehlend else ""))
    if a.dry_run:
        print(_kosten(a, bewerter, eintraege, len(auftraege), 0, basis))
        if refusals:
            print(f"  + {len(refusals)} synchrone Aufrufe mit --refusal-sync (ohne Batch-Rabatt)")
        return 0
    if not auftraege and not refusals:
        print("Nichts nachzuholen.")
        return 0
    _vorbereiten(api.provider)
    rc = 0
    if refusals and a.refusal_sync:
        drossel = ts.Drossel(schlafen)
        for e, lauf in refusals:
            erg = ts.bewerte(bewerter, e, lauf, drossel, schlafen=schlafen)
            erg.meta.update({"modus": "synchron", "anlass": "refusal im Batch"})
            ts.speichere(ts.ziel_pfad(basis, api.provider, lauf, e), erg)
            protokoll.schreibe({"timestamp": erg.meta["timestamp"], "lauf": lauf, "datei": e.datei,
                                "status": erg.status, "model_served": erg.meta["model_served"],
                                "fallback": bool(erg.meta["fallback"]), "usage": erg.meta["usage"],
                                "fehler": erg.meta["fehler"], "modus": "synchron", "anlass": "refusal im Batch"})
            served = erg.meta["model_served"]
            print(f"  synchron run{lauf}/{e.datei}: {erg.status}"
                  + (f" (bedient von {served})" if served and served != bewerter.model else ""))
            rc = rc or (0 if erg.status == "ok" else 1)
    elif refusals:
        for e, lauf in refusals:
            print(f"  vorgemerkt (Refusal): run{lauf}/{e.datei} → synchron mit --batch followup --refusal-sync")
    if auftraege:
        ids = einreichen(api, auftraege, basis, "followup", a.force)
        print(f"Eingereicht: {len(ids)} Batch(es) — {', '.join(ids)}")
        print(f"Weiter: task_scorer.py --provider {api.provider} --batch collect")
    return rc


def ausfuehren(a: argparse.Namespace, bewerter: Any, eintraege: list[ti.Eintrag], basis: Path,
               schlafen: Callable[[float], None] = time.sleep,
               alle: Callable[[], list[ti.Eintrag]] = ti.baue_eintraege) -> int:
    api = erstelle_api(bewerter, a.cache_ttl)
    protokoll = ts.Protokoll(basis / bewerter.provider / "protokoll.jsonl")
    try:
        if a.batch == "submit":
            return cmd_submit(a, api, eintraege, basis)
        if a.batch == "status":
            return cmd_status(a, api, basis)
        if a.batch == "collect":
            return cmd_collect(a, api, basis, protokoll, alle)
        return cmd_followup(a, api, eintraege, basis, protokoll, schlafen)
    except ts.FatalerFehler as e:
        log.error("Abbruch: %s", e)
        return 3
