"""Gemeinsame Bausteine der aufgabenbasierten KI-Expositionsbewertung (Rubrik v2.2; Pilot-Ergebnisse v2.1).

- Pfade zu Rubrik, Schema und Bewerter-System-Prompt (``src/scoring/rubrik/``)
- System-Prompt für die API-Bewertung (Bewerter-Auftrag + Rubrik + Schema)
- Validierung einer Bewertung: JSON-Schema (Draft 2020-12) + Plausibilitätsregeln
  (Zeitanteile = 100, isco_code/beruf wie im Input, Hinweise Modus × Restzeit)
- provider-kompatible Ableitungen des Schemas für Structured Outputs
- Kennzahlen je Bewertung (ζ, β, Zeitersparnis, Modus-Anteile, ersetzbare Zeit, P, Sicherheit)

Die Kennzahlen-Logik entspricht der Pilot-Auswertung (aggregate.py, ``--schema v2_1``).
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

RUBRIK_VERSION = "2.2"     # v2.2 = v2.1 + Block «zusammenfassung» (haupt_risiko, begruendung, zeitrahmen)

SCORING_DIR = Path(__file__).resolve().parent
RUBRIK_DIR = SCORING_DIR / "rubrik"
RUBRIKEN = {   # Version → (Rubrik, Schema); v2.1 bleibt für die Pilot-Ergebnisse (Abo-Läufe) erhalten
    "2.1": (RUBRIK_DIR / "rubrik_aufgaben_v2_1.md", RUBRIK_DIR / "schema_v2_1.json"),
    "2.2": (RUBRIK_DIR / "rubrik_aufgaben_v2_2.md", RUBRIK_DIR / "schema_v2_2.json"),
}
RUBRIK_PATH, SCHEMA_PATH = RUBRIKEN[RUBRIK_VERSION]
SYSTEM_PATH = RUBRIK_DIR / "bewerter_system_v2_2.md"
ZEITRAHMEN = ["1-2 Jahre", "3-5 Jahre", "5-10 Jahre", ">10 Jahre"]   # geordnet (früh → spät)

REPO_DIR = SCORING_DIR.parent.parent
DATA_DIR = REPO_DIR / "data" / "processed"
SCORES_PATH = DATA_DIR / "scores.csv"
KOMPETENZEN_PATH = DATA_DIR / "esco_kompetenzen.csv"
BEWERTUNGEN_DIR = DATA_DIR / "bewertungen"
BENCHMARK_PATH = DATA_DIR / "benchmarks_isco4.csv"
SCORES_AUFGABEN_PATH = DATA_DIR / "scores_aufgaben.csv"

SUMME_TOLERANZ = 2.0      # Aggregation: Zeitanteile 100 ± 2 still normieren, sonst normieren + warnen
RESTZEIT_MITTE = {"<10": 0.05, "10-30": 0.20, "30-50": 0.40}       # Bandmitten restzeit_mensch
GEWICHT_BETA = {"E0": 0.0, "E1": 1.0, "E2": 0.5}
MODI = {"ersetzend": "ersetzend", "delegierend": "delegierend", "unterstützend": "unterstuetzend"}
WIDERSPRUCH = {("ersetzend", "30-50"), ("unterstützend", "<10")}

# Schlüsselwörter, die für Structured Outputs entfernt werden (lokal weiterhin geprüft)
_ENTFERNEN = {"$schema", "$id", "allOf", "if", "then", "else", "uniqueItems", "pattern",
              "minLength", "maxLength"}


# --------------------------------------------------------------------------- Dateien

@lru_cache(maxsize=4)
def lade_schema(version: str = RUBRIK_VERSION) -> dict:
    return json.loads(RUBRIKEN[version][1].read_text(encoding="utf-8"))


@lru_cache(maxsize=4)
def lade_rubrik(version: str = RUBRIK_VERSION) -> str:
    return RUBRIKEN[version][0].read_text(encoding="utf-8")


def version_aus_bewertung(d: Any) -> str:
    """'2.2', wenn ein Block zusammenfassung vorhanden ist, sonst '2.1' (Pilot-Abo-Läufe)."""
    return "2.2" if isinstance(d, dict) and "zusammenfassung" in d else "2.1"


@lru_cache(maxsize=1)
def system_prompt() -> str:
    """Bewerter-Auftrag + vollständige Rubrik + Ausgabeschema (für alle Aufrufe identisch → cachebar)."""
    auftrag = SYSTEM_PATH.read_text(encoding="utf-8").strip()
    schema = json.dumps(lade_schema(), ensure_ascii=False, indent=2)
    return (f"{auftrag}\n\n"
            f"<rubrik version=\"{RUBRIK_VERSION}\">\n{lade_rubrik().strip()}\n</rubrik>\n\n"
            f"<ausgabeschema>\n{schema}\n</ausgabeschema>\n")


def user_prompt(input_rec: dict) -> str:
    """Nachricht je Beruf: Input-JSON des Berufs."""
    return (f"Bewerte den folgenden Beruf nach der Rubrik v{RUBRIK_VERSION}. Input-Datei des Berufs:\n\n"
            + json.dumps(input_rec, ensure_ascii=False, indent=2))


def korrektur_prompt(fehler: list[str]) -> str:
    """Folgenachricht, wenn die Antwort die Validierung nicht bestanden hat."""
    liste = "\n".join(f"- {f}" for f in fehler[:20])
    return ("Deine Antwort hat die Validierung nicht bestanden:\n" + liste
            + "\n\nKorrigiere die Bewertung und antworte erneut ausschliesslich mit dem vollständigen "
              "JSON-Objekt gemäss Schema.")


def kanonisch(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def input_hash(input_rec: dict, schema: dict | None = None, version: str = RUBRIK_VERSION) -> str:
    """SHA-256 über (Rubrik-Version, Schema, Input-JSON) — Grundlage der Delta-Läufe."""
    payload = kanonisch({"rubrik_version": version, "schema": schema if schema is not None else lade_schema(),
                         "input": input_rec})
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def slugify(text: str) -> str:
    """Dateinamen-Slug wie im Pilot (Umlaute ausschreiben, Klammern entfernen, max. 40 Zeichen)."""
    t = (text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("Ä", "Ae")
         .replace("Ö", "Oe").replace("Ü", "Ue").replace("ß", "ss"))
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    t = re.sub(r"\(.*?\)", "", t)
    t = re.sub(r"[^a-zA-Z0-9]+", "_", t).strip("_").lower()
    return t[:40].rstrip("_")


def dateiname(isco_code: str, beruf: str) -> str:
    return f"{isco_code}_{slugify(beruf)}.json"


# --------------------------------------------------------------------------- Validierung

@lru_cache(maxsize=4)
def _validator(version: str = RUBRIK_VERSION) -> Draft202012Validator:
    return Draft202012Validator(lade_schema(version))


def schema_fehler(d: Any, version: str = RUBRIK_VERSION) -> list[str]:
    fehler = sorted(_validator(version).iter_errors(d), key=lambda e: list(e.absolute_path))
    return [f"{'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}" for e in fehler]


def pruefe_bewertung(d: Any, input_rec: dict | None = None, version: str = RUBRIK_VERSION) -> list[str]:
    """Fatale Probleme einer Bewertung (leer = gültig): Schema der Version, Summe = 100, isco_code/beruf."""
    if not isinstance(d, dict):
        return ["(root): Antwort ist kein JSON-Objekt"]
    taet = d.get("taetigkeiten")
    if isinstance(taet, list) and any(isinstance(t, dict) and t.get("modus") == "automatisierend" for t in taet):
        return ["modus «automatisierend» gibt es seit v2.1 nicht mehr → «ersetzend», «delegierend» "
                "oder «unterstützend» (Rubrik, Abschnitt 3.1)"]
    probleme = schema_fehler(d, version)
    if probleme:
        return probleme
    s = sum(t["zeitanteil_pct"] for t in d["taetigkeiten"])
    if s != 100:
        probleme.append(f"Zeitanteile summieren auf {s}, nicht exakt 100")
    if input_rec is not None and (d["isco_code"], d["beruf"]) != (input_rec["isco_code"], input_rec["beruf"]):
        probleme.append(f"isco_code/beruf weichen vom Input ab: erwartet {input_rec['isco_code']} / "
                        f"{input_rec['beruf']}, erhalten {d['isco_code']} / {d['beruf']}")
    return probleme


def hinweise(d: Any) -> list[str]:
    """Nicht-fatale Hinweise: unplausible Kombination Modus × Restzeit (Rubrik 3.2)."""
    if not isinstance(d, dict):
        return []
    res = []
    for i, t in enumerate(d.get("taetigkeiten") or [], 1):
        if isinstance(t, dict) and (t.get("modus"), t.get("restzeit_mensch")) in WIDERSPRUCH:
            res.append(f"Tätigkeit {i} «{t.get('name', '')}»: Modus «{t['modus']}» mit Restzeit "
                       f"«{t['restzeit_mensch']}» ist unplausibel (Rubrik, Abschnitt 3.2)")
    return res


# --------------------------------------------------------------------------- Schema für Structured Outputs

def _vereinfache(node: Any) -> Any:
    """Entfernt bedingte/nicht unterstützte Schlüsselwörter, Typ-Listen → anyOf."""
    if isinstance(node, list):
        return [_vereinfache(x) for x in node]
    if not isinstance(node, dict):
        return node
    n = {k: _vereinfache(v) for k, v in node.items() if k not in _ENTFERNEN}
    typ = n.get("type")
    if isinstance(typ, list):
        nicht_null = [t for t in typ if t != "null"]
        varianten = []
        for t in nicht_null:
            v: dict = {"type": t}
            if "enum" in n:
                v["enum"] = [e for e in n["enum"] if e is not None]
            varianten.append(v)
        if "null" in typ:
            varianten.append({"type": "null"})
        neu = {"anyOf": varianten}
        if "description" in n:
            neu["description"] = n["description"]
        return neu
    return n


def _inline_refs(node: Any, defs: dict) -> Any:
    if isinstance(node, list):
        return [_inline_refs(x, defs) for x in node]
    if not isinstance(node, dict):
        return node
    if "$ref" in node:
        name = node["$ref"].rsplit("/", 1)[-1]
        return _inline_refs(copy.deepcopy(defs[name]), defs)
    return {k: _inline_refs(v, defs) for k, v in node.items() if k != "$defs"}


def schema_fuer_claude(schema: dict | None = None) -> dict:
    """Schema für ``output_config.format``: Bedingungen/Typ-Listen umgeschrieben, danach das
    SDK-Hilfsmittel ``anthropic.transform_schema`` (verschiebt nicht unterstützte Constraints
    wie minimum/maximum/minItems>1 in die Beschreibung). Lokal wird immer gegen das
    Originalschema validiert."""
    import anthropic

    return anthropic.transform_schema(_vereinfache(copy.deepcopy(schema or lade_schema())))


def schema_fuer_gemini(schema: dict | None = None) -> dict:
    """Schema für ``response_json_schema`` (Gemini): wie oben vereinfacht, $refs aufgelöst.
    Unterstützt laut SDK: type, format, title, description, enum, items, minItems, maxItems,
    minimum, maximum, anyOf, properties, additionalProperties, required, $defs/$ref."""
    s = _vereinfache(copy.deepcopy(schema or lade_schema()))
    defs = s.get("$defs", {})
    return _inline_refs(s, defs)


# --------------------------------------------------------------------------- Kennzahlen

def normiere(bewertung: dict, warnungen: list[str] | None = None, quelle: str = "") -> dict:
    """Zeitanteile proportional auf 100 normieren (Kopie). Ausserhalb 100 ± Toleranz → Warnung."""
    b = copy.deepcopy(bewertung)
    summe = sum(x["zeitanteil_pct"] for x in b["taetigkeiten"])
    if summe <= 0:
        raise ValueError("Zeitanteile summieren auf 0")
    if abs(summe - 100) > SUMME_TOLERANZ and warnungen is not None:
        warnungen.append(f"{quelle}: Zeitanteile summieren auf {summe} (≠ 100 ± {SUMME_TOLERANZ:g}) → normiert")
    if summe != 100:
        for x in b["taetigkeiten"]:
            x["zeitanteil_pct"] = x["zeitanteil_pct"] * 100.0 / summe
    return b


def kennzahlen(bewertung: dict) -> dict:
    """Kennzahlen eines Berufs aus einer gültigen, auf 100 normierten v2.1- oder v2.2-Bewertung (zusammenfassung zählt nicht).

    w = Zeitanteil (Σ w = 1), exp = E1 oder E2, m = Bandmitte der Restzeit:
      ζ = Σ w·1[exp]; β = Σ w·(1[E1] + 0.5·1[E2]); Zeitersparnis = Σ w·1[exp]·(1 − m);
      Modus-Anteile ζ-gewichtet; ersetzbare Zeit = Σ w·1[ersetzend]·(1 − m);
      P1-Anteile gesamt / nur p_art «physisch» / nur «software».
    """
    t = bewertung["taetigkeiten"]
    w = [x["zeitanteil_pct"] / 100.0 for x in t]
    exp = [x["stufe"] in ("E1", "E2") for x in t]
    w_exp = sum(wi for wi, e in zip(w, exp) if e)

    def quote(z: float) -> float:
        return z / w_exp if w_exp > 0 else math.nan

    def anteil(feld: str, wert: str) -> float:
        return sum(wi for wi, x in zip(w, t) if x.get(feld) == wert)

    beta = sum(wi * GEWICHT_BETA[x["stufe"]] for wi, x in zip(w, t))
    ersp = [wi * (1.0 - RESTZEIT_MITTE[x["restzeit_mensch"]]) if e else 0.0 for wi, e, x in zip(w, exp, t)]
    zeitersparnis = sum(ersp)
    zeit_modus = {k: sum(wi for wi, e, x in zip(w, exp, t) if e and x["modus"] == m) for m, k in MODI.items()}
    p1 = [x["physisch_automatisierbar"] == "P1" for x in t]
    w_p1 = sum(wi for wi, p in zip(w, p1) if p)
    w_p = {a: sum(wi for wi, p, x in zip(w, p1, t) if p and x["p_art"] == a) for a in ("physisch", "software")}
    res = {
        "n_taetigkeiten": len(t),
        "zeta": w_exp,
        "score_aufgaben": 10.0 * w_exp,
        "beta": beta,
        "score_aufgaben_beta": 10.0 * beta,
        "zeitersparnis": zeitersparnis,
        "score_zeitersparnis": 10.0 * zeitersparnis,
        "ersparnis_je_exp": quote(zeitersparnis),
        "anteil_e0": anteil("stufe", "E0"),
        "anteil_e1": anteil("stufe", "E1"),
        "anteil_e2": anteil("stufe", "E2"),
    }
    for k, v in zeit_modus.items():
        res[f"anteil_{k}"] = quote(v)
    for k, v in zeit_modus.items():
        res[f"zeit_{k}"] = v
    res.update({
        "ersetzbare_zeit": sum(ei for ei, e, x in zip(ersp, exp, t) if e and x["modus"] == "ersetzend"),
        "anteil_p1": w_p1,
        "score_p1_gesamt": 10.0 * w_p1,
        "score_physisch_auto": 10.0 * w_p["physisch"],
        "score_software_auto": 10.0 * w_p["software"],
        "anteil_sicherheit_hoch": anteil("sicherheit", "hoch"),
        "anteil_sicherheit_mittel": anteil("sicherheit", "mittel"),
        "sicherheit_tief_anteil": anteil("sicherheit", "tief"),
        "n_sicherheit_tief": sum(1 for x in t if x["sicherheit"] == "tief"),
        "n_modus_restzeit_widerspruch": sum(1 for x in t if (x["modus"], x["restzeit_mensch"]) in WIDERSPRUCH),
        "anteil_exp_mit_hemmnis": quote(sum(wi for wi, e, x in zip(w, exp, t) if e and x["ch_hemmnis"])),
        "unsicherheit": bewertung["unsicherheit"],
    })
    return res


def ueber_schwelle(wert: float, schwelle: float) -> bool:
    """wert > schwelle ohne Gleitkomma-Rauschen: Scores sind Summen von Prozentanteilen, eine Differenz
    von genau 1.0 ergibt je nach Plattform 0.9999999999999 oder 1.0000000000002."""
    return round(float(wert), 9) > schwelle


def zeta_score(bewertung: dict) -> float:
    """10·ζ einer (ggf. nicht exakt auf 100 summierenden) Bewertung."""
    return kennzahlen(normiere(bewertung))["score_aufgaben"]
