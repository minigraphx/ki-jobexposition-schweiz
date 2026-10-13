"""Tests der aufgabenbasierten API-Pipeline (Rubrik v2.2): Rubrik/Schema, Inputs, Validierung,
Kennzahlen (inkl. Kalibrierungsbeispiele der Rubrik), Scorer mit gemockten Clients (Claude, Gemini),
Hash-Delta, dritter Lauf, Aggregation, Dry-Run ohne Netz, Vergleichsbericht.

Keine echten API-Aufrufe: Clients werden durch Attrappen ersetzt, Netzzugriffe im Dry-Run-Test
durch einen blockierten Socket ausgeschlossen.
"""
from __future__ import annotations

import copy
import json
import math
import re
import socket
import threading
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import pytest

import task_aggregate as ta
import task_batch as tb
import task_inputs as ti
import task_rubrik as tr
import task_scorer as ts
import task_vergleich as tv

PILOT_ABO = tr.BEWERTUNGEN_DIR / "pilot_abo"


def close(a, b, tol=1e-9):
    assert math.isclose(a, b, abs_tol=tol), f"{a} != {b}"


# --------------------------------------------------------------------------- Hilfen

def taet(pct, stufe, modus=None, rest=None, p="P0", p_art=None, sich="hoch", hemm=()):
    return {"name": f"Testtätigkeit {stufe} mit {pct} Prozent", "zeitanteil_pct": pct, "stufe": stufe,
            "modus": modus, "restzeit_mensch": rest, "physisch_automatisierbar": p, "p_art": p_art,
            "sicherheit": sich,
            "sicherheit_begruendung": "Unsicher, ob die Schwelle erreicht wird; E0 ebenso plausibel." if sich == "tief" else None,
            "ch_hemmnis": list(hemm), "begruendung": "Synthetische Begründung für den Test der Kennzahlen."}


def bewertung(isco="9901", beruf="Testberuf", taetigkeiten=None, zeitrahmen="3-5 Jahre", risiko=None):
    t = taetigkeiten or ([taet(20, "E1", "ersetzend", "<10")] + [taet(10, "E0") for _ in range(8)])
    return {"isco_code": isco, "beruf": beruf, "taetigkeiten": t, "unsicherheit": "mittel",
            "kommentar": "Synthetisches Setting.",
            "zusammenfassung": {"haupt_risiko": risiko or "Standardkorrespondenz wird vom Chat-LLM übernommen.",
                                "begruendung": "Ein Fünftel der Zeit ist exponiert, ersetzend; die übrige Arbeit "
                                               "ist physisch. Kein wesentliches CH-Hemmnis.",
                                "zeitrahmen": zeitrahmen}}


def bewertung_mit_zeta(isco, beruf, zeta_pct: int, zeitrahmen="3-5 Jahre", risiko=None):
    """8 Tätigkeiten: eine exponierte mit zeta_pct %, Rest E0 (Summe 100)."""
    rest = 100 - zeta_pct
    e0 = [rest // 7] * 7
    e0[0] += rest - sum(e0)
    t = [taet(zeta_pct, "E1", "delegierend", "30-50")] + [taet(x, "E0") for x in e0]
    return bewertung(isco, beruf, t, zeitrahmen, risiko)


@pytest.fixture(scope="module")
def eintraege():
    return ti.baue_eintraege()


def _anzahl_eintraege() -> int:
    """Anzahl Einträge in scores.csv (wächst, wenn Berufsgattungen dazukommen)."""
    import pandas as pd
    return len(pd.read_csv(Path(__file__).parent.parent / "data" / "processed" / "scores.csv"))


@pytest.fixture(scope="module")
def pilot(eintraege):
    return ti.baue_eintraege(pilot=True)


# --------------------------------------------------------------------------- Rubrik und Schema

def test_rubrik_version_und_dateien():
    assert tr.RUBRIK_VERSION == "2.2"
    assert "Version 2.2" in tr.lade_rubrik().splitlines()[2]
    assert "Version 2.1" in tr.lade_rubrik("2.1").splitlines()[2]
    assert "## 11. Zusammenfassung je Beruf" in tr.lade_rubrik()


def test_schema_v22_ist_v21_plus_zusammenfassung():
    s21, s22 = copy.deepcopy(tr.lade_schema("2.1")), copy.deepcopy(tr.lade_schema("2.2"))
    z = s22["properties"].pop("zusammenfassung")
    s22["required"].remove("zusammenfassung")
    for k in ("$id", "title"):
        s21.pop(k), s22.pop(k)
    assert s21 == s22
    assert z["required"] == ["haupt_risiko", "begruendung", "zeitrahmen"]
    assert z["properties"]["zeitrahmen"]["enum"] == tr.ZEITRAHMEN


def test_rubrik_v22_enthaelt_v21_text():
    """v2.2 ändert v2.1 nur punktuell (Version, Schemaname, Zusammenfassung) — alle Abschnitte bleiben."""
    v21, v22 = tr.lade_rubrik("2.1"), tr.lade_rubrik("2.2")
    for abschnitt in [z for z in v21.splitlines() if z.startswith("## ") or z.startswith("### ")]:
        assert abschnitt in v22
    unveraendert = [z for z in v21.splitlines() if "2.1" not in z and "v2_1" not in z]
    fehlend = [z for z in unveraendert if z not in v22.splitlines()]
    assert len(fehlend) <= 4, fehlend   # nur die ersetzten Zeilen (Schrittzahl, unsicherheit-Zeile, Beispiel-Ende)


def test_system_prompt():
    sp = tr.system_prompt()
    assert "Antworte ausschliesslich mit JSON gemäss Schema" in sp
    assert tr.lade_rubrik().strip()[:200] in sp
    assert '"zusammenfassung"' in sp
    for verboten in ("/tmp", "scratchpad", "validate.py", "AUSGABEVERZEICHNIS", "{{"):
        assert verboten not in sp


def _alle_schluessel(node, acc=None):
    acc = set() if acc is None else acc
    if isinstance(node, dict):
        for k, v in node.items():
            acc.add(k)
            if k != "properties":
                _alle_schluessel(v, acc)
        if "properties" in node:
            for v in node["properties"].values():
                _alle_schluessel(v, acc)
    elif isinstance(node, list):
        for v in node:
            _alle_schluessel(v, acc)
    return acc


def _objekte(node):
    if isinstance(node, dict):
        if node.get("type") == "object":
            yield node
        for v in node.values():
            yield from _objekte(v)
    elif isinstance(node, list):
        for v in node:
            yield from _objekte(v)


def test_schema_fuer_claude_nur_unterstuetzte_features():
    s = tr.schema_fuer_claude()
    keys = _alle_schluessel(s)
    assert not keys & {"if", "then", "else", "allOf", "minLength", "maxLength", "pattern", "uniqueItems",
                       "minimum", "maximum", "$schema", "$id"}
    assert all(o.get("additionalProperties") is False for o in _objekte(s))
    assert not any(isinstance(n.get("type"), list) for n in _iter_dicts(s))
    assert "$defs" in s and s["properties"]["taetigkeiten"]["items"] == {"$ref": "#/$defs/taetigkeit"}


def _iter_dicts(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _iter_dicts(v)
    elif isinstance(node, list):
        for v in node:
            yield from _iter_dicts(v)


def test_schema_fuer_gemini_nur_unterstuetzte_features():
    s = tr.schema_fuer_gemini()
    erlaubt = {"type", "format", "title", "description", "enum", "items", "prefixItems", "minItems", "maxItems",
               "minimum", "maximum", "anyOf", "additionalProperties", "required", "properties"}
    assert _alle_schluessel(s) <= erlaubt
    assert s["properties"]["taetigkeiten"]["items"]["properties"]["zeitanteil_pct"]["maximum"] == 80


def test_vereinfachtes_schema_akzeptiert_gueltige_bewertung():
    from jsonschema import Draft202012Validator
    b = bewertung()
    for s in (tr.schema_fuer_claude(), tr.schema_fuer_gemini()):
        assert not list(Draft202012Validator(s).iter_errors(b))


# --------------------------------------------------------------------------- Validierung

def test_pruefe_bewertung_gueltig_und_hinweise():
    b = bewertung()
    assert tr.pruefe_bewertung(b, {"isco_code": "9901", "beruf": "Testberuf"}) == []
    b["taetigkeiten"][0]["restzeit_mensch"] = "30-50"     # ersetzend + 30-50 → nur Hinweis
    assert tr.pruefe_bewertung(b) == []
    assert len(tr.hinweise(b)) == 1


@pytest.mark.parametrize("aendern, erwartet", [
    (lambda b: b["taetigkeiten"][1].update(zeitanteil_pct=9), "summieren auf 99"),
    (lambda b: b.update(isco_code="9902"), "weichen vom Input ab"),
    (lambda b: b["taetigkeiten"][1].update(modus="ersetzend"), "taetigkeiten/1/modus"),
    (lambda b: b["taetigkeiten"][1].update(sicherheit="tief"), "sicherheit_begruendung"),
    (lambda b: b["taetigkeiten"][0].update(modus="automatisierend"), "automatisierend"),
    (lambda b: b.pop("zusammenfassung"), "zusammenfassung"),
    (lambda b: b["zusammenfassung"].update(zeitrahmen="bald"), "zeitrahmen"),
    (lambda b: b.update(taetigkeiten=b["taetigkeiten"][:7]), "taetigkeiten"),
])
def test_pruefe_bewertung_fehler(aendern, erwartet):
    b = bewertung()
    aendern(b)
    probleme = tr.pruefe_bewertung(b, {"isco_code": "9901", "beruf": "Testberuf"})
    assert probleme and any(erwartet in p for p in probleme), probleme


def test_pilot_abo_dateien_sind_gueltig_v21():
    dateien = sorted(PILOT_ABO.glob("run*_v21/*.json"))
    assert len(dateien) == 30
    for f in dateien:
        d = json.loads(f.read_text(encoding="utf-8"))
        assert tr.version_aus_bewertung(d) == "2.1"
        assert tr.pruefe_bewertung(d, None, "2.1") == [], f.name
        assert tr.pruefe_bewertung(d, None, "2.2")         # ohne zusammenfassung ungültig in v2.2


# --------------------------------------------------------------------------- Inputs

def test_inputs_alle_eintraege(eintraege):
    n = _anzahl_eintraege()
    assert len(eintraege) == n
    assert len({e.datei for e in eintraege}) == n
    for e in eintraege:
        assert e.input["isco_code"] == e.isco_code and len(e.input_hash) == 64
        typen = [k["typ"] for k in e.input["wesentliche_kompetenzen"]]
        assert typen == sorted(typen, key=lambda t: t != "skill")


def test_inputs_pilot(pilot):
    assert len(pilot) == 15
    assert sorted(e.isco_code for e in pilot) == sorted(i for i, _ in ti.PILOT_BERUFE)
    namen = {e.isco_code: e.beruf for e in pilot}
    assert namen["5223"] == "Verkäufer in Handelsgeschäften"    # nicht «Drogist/in» (gleicher ISCO)
    assert namen["4110"] == "Allgemeine Bürokräfte"


def test_input_inhalt_wie_pilot(eintraege):
    e = next(x for x in eintraege if x.isco_code == "2411")
    rec = e.input
    for k in ("beruf", "isco_code", "synonyme", "ch_kontext", "esco_uri", "esco_titel", "esco_beschreibung",
              "beschreibung_quelle", "esco_match_qualitaet", "wesentliche_kompetenzen", "anzahl_kompetenzen",
              "optionale_kompetenzen_skills", "datenlage_hinweis"):
        assert k in rec
    assert rec["anzahl_kompetenzen"]["skill"] == sum(1 for k in rec["wesentliche_kompetenzen"] if k["typ"] == "skill")
    assert "Controller" in rec["datenlage_hinweis"]
    assert "score_gesamt" not in json.dumps(rec)


def test_input_ohne_esco(eintraege):
    e = next(x for x in eintraege if x.beruf == "Drogist/in")
    assert e.input["wesentliche_kompetenzen"] == [] and e.input["esco_uri"] is None
    assert "Keine ESCO-Zuordnung" in e.input["datenlage_hinweis"]


def test_input_hash():
    rec = {"beruf": "X", "isco_code": "1234"}
    h = tr.input_hash(rec)
    assert h == tr.input_hash(dict(reversed(list(rec.items()))))      # unabhängig von der Schlüsselreihenfolge
    assert h != tr.input_hash({**rec, "beruf": "Y"})
    assert h != tr.input_hash(rec, version="2.1")
    assert h != tr.input_hash(rec, schema=tr.lade_schema("2.1"))


# --------------------------------------------------------------------------- Kennzahlen (Rubrik-Kalibrierung)

def test_kalibrierung_81_schadenabteilung():
    t = [taet(20, "E2", "ersetzend", "10-30"), taet(15, "E1", "delegierend", "30-50", sich="mittel"),
         taet(10, "E2", "unterstützend", "30-50"), taet(15, "E1", "ersetzend", "<10"),
         taet(10, "E2", "ersetzend", "10-30", sich="tief", hemm=["vertrauen"]),
         taet(5, "E0", p="P1", p_art="software"), taet(15, "E0"), taet(5, "E1", "delegierend", "30-50"),
         taet(5, "E0")]
    k = tr.kennzahlen(bewertung(taetigkeiten=t))
    close(k["zeta"], 0.75)
    close(k["beta"], 0.55)
    close(k["zeitersparnis"], 0.5625)
    close(k["ersetzbare_zeit"], 0.3825)
    close(k["anteil_ersetzend"], 0.45 / 0.75)
    close(k["anteil_delegierend"], 0.20 / 0.75)
    close(k["anteil_unterstuetzend"], 0.10 / 0.75)
    close(k["score_software_auto"], 0.5)
    close(k["score_physisch_auto"], 0.0)
    close(k["sicherheit_tief_anteil"], 0.10)


def test_kalibrierung_82_physiotherapie():
    t = [taet(15, "E0"), taet(35, "E0"), taet(20, "E0"), taet(5, "E1", "unterstützend", "30-50"),
         taet(10, "E2", "delegierend", "30-50", hemm=["regulatorisch"]), taet(5, "E1", "delegierend", "10-30"),
         taet(5, "E0", p="P1", p_art="software"), taet(5, "E0")]
    k = tr.kennzahlen(bewertung(taetigkeiten=t))
    close(k["score_aufgaben"], 2.0)
    close(k["beta"], 0.15)
    close(k["zeitersparnis"], 0.13)
    close(k["ersetzbare_zeit"], 0.0)
    close(k["anteil_delegierend"], 0.75)
    close(k["anteil_unterstuetzend"], 0.25)
    close(k["score_software_auto"], 0.5)


def test_kalibrierung_83_maurer():
    t = [taet(30, "E0"), taet(25, "E0"), taet(10, "E0"), taet(10, "E0"), taet(10, "E0"),
         taet(5, "E1", "delegierend", "30-50", sich="tief"), taet(5, "E2", "delegierend", "30-50"), taet(5, "E0")]
    k = tr.kennzahlen(bewertung(taetigkeiten=t))
    close(k["zeta"], 0.10)
    close(k["beta"], 0.075)
    close(k["zeitersparnis"], 0.06)
    close(k["anteil_delegierend"], 1.0)
    close(k["anteil_p1"], 0.0)


def test_kennzahlen_ohne_exposition_und_normierung():
    k = tr.kennzahlen(bewertung(taetigkeiten=[taet(10, "E0", p="P1", p_art="physisch")] + [taet(10, "E0") for _ in range(9)]))
    assert k["zeta"] == 0 and math.isnan(k["anteil_ersetzend"])
    close(k["score_physisch_auto"], 1.0)
    w: list[str] = []
    n = tr.normiere(bewertung(taetigkeiten=[taet(25, "E1", "ersetzend", "<10")] + [taet(10, "E0") for _ in range(7)]), w, "x")
    close(sum(x["zeitanteil_pct"] for x in n["taetigkeiten"]), 100.0)
    assert w and "normiert" in w[0]


# --------------------------------------------------------------------------- Attrappen der SDK-Clients

class _Stream:
    def __init__(self, msg):
        self._msg = msg

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get_final_message(self):
        return self._msg


class FakeAnthropic:
    """Attrappe für client.beta.messages.stream(...) / count_tokens(...)."""

    def __init__(self, antworten):
        self.antworten = list(antworten)
        self.aufrufe: list[dict] = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._stream, count_tokens=self._count))

    def _stream(self, **kw):
        self.aufrufe.append(copy.deepcopy(kw))
        a = self.antworten.pop(0)
        if isinstance(a, Exception):
            raise a
        return _Stream(a)

    def _count(self, **kw):
        self.aufrufe.append(kw)
        return SimpleNamespace(input_tokens=12345)


def claude_msg(text, stop="end_turn", model="claude-opus-5-5", vorher=None, iterations=None, stop_details=None):
    content = list(vorher or []) + [SimpleNamespace(type="thinking", thinking=""),
                                    SimpleNamespace(type="text", text=text)]
    usage = {"input_tokens": 1000, "output_tokens": 500, "cache_read_input_tokens": 20000}
    if iterations:
        usage["iterations"] = iterations
    return SimpleNamespace(content=content, stop_reason=stop, model=model, usage=usage,
                           stop_details=stop_details, _request_id="req_1")


@pytest.fixture
def eintrag(pilot):
    return next(e for e in pilot if e.isco_code == "2512")


def _rate_limit():
    import anthropic
    import httpx2
    r = httpx2.Response(429, headers={"retry-after": "1"},
                        request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"))
    return anthropic.RateLimitError("rate limited", response=r, body=None)


def _gueltig(e, **kw):
    return json.dumps(bewertung(e.isco_code, e.beruf, **kw), ensure_ascii=False)


def test_claude_anfrage_parameter_und_erfolg(eintrag):
    fake = FakeAnthropic([claude_msg(_gueltig(eintrag))])
    b = ts.ClaudeBewerter(client=fake)
    erg = ts.bewerte(b, eintrag, 1, ts.Drossel(), schlafen=lambda s: None)
    assert erg.status == "ok" and erg.bewertung["isco_code"] == eintrag.isco_code
    kw = fake.aufrufe[0]
    assert kw["model"] == "claude-opus-5-5"
    assert kw["thinking"] == {"type": "adaptive"}
    assert kw["output_config"]["effort"] == "high"
    assert kw["output_config"]["format"]["type"] == "json_schema"
    assert kw["output_config"]["format"]["schema"] == tr.schema_fuer_claude()
    assert kw["betas"] == ["server-side-fallback-2026-07-01"] and kw["fallbacks"] == "default"
    assert kw["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert kw["max_tokens"] == ts.CLAUDE_MAX_TOKENS
    assert "temperature" not in kw and "budget_tokens" not in json.dumps(kw["thinking"])
    m = erg.meta
    assert m["model_requested"] == m["model_served"] == "claude-opus-5-5" and m["fallback"] is None
    assert m["stop_reason"] == "end_turn" and m["rubrik_version"] == "2.2"
    assert m["input_hash"] == eintrag.input_hash and m["usage"]["cache_read_input_tokens"] == 20000


def test_claude_fallback_wird_protokolliert(eintrag):
    vorher = [SimpleNamespace(type="text", text="abgebrochen"),
              SimpleNamespace(type="fallback", from_=SimpleNamespace(model="claude-opus-5-5"),
                              to=SimpleNamespace(model="claude-opus-5"))]
    msg = claude_msg(_gueltig(eintrag), model="claude-opus-5", vorher=vorher,
                     iterations=[{"type": "message"}, {"type": "fallback_message", "model": "claude-opus-5"}])
    erg = ts.bewerte(ts.ClaudeBewerter(client=FakeAnthropic([msg])), eintrag, 1, ts.Drossel(), lambda s: None)
    assert erg.status == "ok"
    assert erg.meta["model_served"] == "claude-opus-5"
    assert erg.meta["fallback"]["wechsel"] == [{"von": "claude-opus-5-5", "zu": "claude-opus-5"}]


def test_claude_refusal_und_max_tokens(eintrag):
    for msg, text in ((claude_msg("", stop="refusal", stop_details={"category": "cyber", "explanation": "x"}),
                       "Refusal"),
                      (claude_msg("{", stop="max_tokens"), "abgeschnitten")):
        erg = ts.bewerte(ts.ClaudeBewerter(client=FakeAnthropic([msg])), eintrag, 1, ts.Drossel(), lambda s: None)
        assert erg.status == "fehlgeschlagen" and text in erg.meta["fehler"][0]


def test_claude_korrekturversuch(eintrag):
    falsch = bewertung(eintrag.isco_code, eintrag.beruf)
    falsch["taetigkeiten"][1]["zeitanteil_pct"] = 5
    fake = FakeAnthropic([claude_msg(json.dumps(falsch)), claude_msg(_gueltig(eintrag))])
    erg = ts.bewerte(ts.ClaudeBewerter(client=fake), eintrag, 1, ts.Drossel(), lambda s: None)
    assert erg.status == "ok" and erg.meta["versuche"] == 2
    zweite = fake.aufrufe[1]["messages"]
    assert [m["role"] for m in zweite] == ["user", "assistant", "user"]
    assert "summieren auf 95" in zweite[2]["content"], zweite[2]["content"]


def test_claude_zweimal_ungueltig_fehlgeschlagen(eintrag):
    fake = FakeAnthropic([claude_msg("kein json"), claude_msg("immer noch nicht")])
    erg = ts.bewerte(ts.ClaudeBewerter(client=fake), eintrag, 1, ts.Drossel(), lambda s: None)
    assert erg.status == "fehlgeschlagen" and erg.rohantwort == "immer noch nicht"
    assert len(erg.meta["fehler"]) == 2


def test_claude_rate_limit_wird_wiederholt(eintrag):
    pausen = []
    fake = FakeAnthropic([_rate_limit(), claude_msg(_gueltig(eintrag))])
    erg = ts.bewerte(ts.ClaudeBewerter(client=fake), eintrag, 1, ts.Drossel(lambda s: None), pausen.append)
    assert erg.status == "ok" and pausen == [1.0]


def test_claude_fatale_fehler(eintrag):
    import anthropic
    import httpx2
    r = httpx2.Response(401, request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"))
    fake = FakeAnthropic([anthropic.AuthenticationError("bad key", response=r, body=None)])
    with pytest.raises(ts.FatalerFehler):
        ts.bewerte(ts.ClaudeBewerter(client=fake), eintrag, 1, ts.Drossel(), lambda s: None)


class FakeGemini:
    def __init__(self, antworten):
        self.antworten = list(antworten)
        self.aufrufe: list[dict] = []
        self.models = SimpleNamespace(generate_content=self._gen,
                                      count_tokens=lambda **kw: SimpleNamespace(total_tokens=23456))

    def _gen(self, **kw):
        self.aufrufe.append(kw)
        a = self.antworten.pop(0)
        if isinstance(a, Exception):
            raise a
        return a


def gemini_resp(text, finish="STOP"):
    from google.genai import types
    return types.GenerateContentResponse.model_validate({
        "candidates": [{"content": {"role": "model", "parts": [{"text": text}]}, "finish_reason": finish}],
        "model_version": "gemini-4-argon", "response_id": "r1",
        "usage_metadata": {"prompt_token_count": 24000, "candidates_token_count": 3000, "thoughts_token_count": 9000}})


def test_gemini_anfrage_parameter_und_erfolg(eintrag):
    fake = FakeGemini([gemini_resp(_gueltig(eintrag))])
    erg = ts.bewerte(ts.GeminiBewerter(client=fake), eintrag, 2, ts.Drossel(), lambda s: None)
    assert erg.status == "ok"
    kw = fake.aufrufe[0]
    assert kw["model"] == "gemini-4-argon"
    cfg = kw["config"]
    assert cfg.response_mime_type == "application/json"
    assert cfg.response_json_schema == tr.schema_fuer_gemini()
    lvl = cfg.thinking_config.thinking_level
    assert str(getattr(lvl, "value", lvl)).upper() == "HIGH"
    assert cfg.temperature is None and cfg.max_output_tokens == 65536
    assert cfg.system_instruction == tr.system_prompt()
    assert erg.meta["model_served"] == "gemini-4-argon" and erg.meta["stop_reason"] == "STOP"
    assert erg.meta["usage"]["thoughts_token_count"] == 9000 and erg.meta["lauf"] == 2


def test_gemini_korrektur_gibt_modellturn_zurueck(eintrag):
    fake = FakeGemini([gemini_resp("{}"), gemini_resp(_gueltig(eintrag))])
    erg = ts.bewerte(ts.GeminiBewerter(client=fake), eintrag, 1, ts.Drossel(), lambda s: None)
    assert erg.status == "ok"
    inhalte = fake.aufrufe[1]["contents"]
    assert [c.role for c in inhalte] == ["user", "model", "user"]
    assert "Validierung nicht bestanden" in inhalte[2].parts[0].text


def test_gemini_max_tokens_und_429(eintrag):
    from google.genai import errors
    erg = ts.bewerte(ts.GeminiBewerter(client=FakeGemini([gemini_resp("{", "MAX_TOKENS")])), eintrag, 1,
                     ts.Drossel(), lambda s: None)
    assert erg.status == "fehlgeschlagen" and "abgeschnitten" in erg.meta["fehler"][0]
    fehler = errors.ClientError(429, {"error": {"code": 429, "message": "quota", "status": "RESOURCE_EXHAUSTED"}})
    fake = FakeGemini([fehler, gemini_resp(_gueltig(eintrag))])
    erg = ts.bewerte(ts.GeminiBewerter(client=fake), eintrag, 1, ts.Drossel(lambda s: None), lambda s: None)
    assert erg.status == "ok" and len(fake.aufrufe) == 2
    fake = FakeGemini([errors.ClientError(403, {"error": {"code": 403, "message": "no", "status": "PERMISSION_DENIED"}})])
    with pytest.raises(ts.FatalerFehler):
        ts.bewerte(ts.GeminiBewerter(client=fake), eintrag, 1, ts.Drossel(), lambda s: None)


# --------------------------------------------------------------------------- Lauf-Steuerung: Delta & dritter Lauf

class FakeBewerter:
    """Provider-neutrale Attrappe: liefert gültige Bewertungen; ζ je Aufruf über ``zeta_folge``."""
    provider = "claude"

    def __init__(self, model="claude-opus-5-5", zeta_folge=None):
        self.model = model
        self.zeta_folge = zeta_folge or {}
        self.aufrufe: list[str] = []
        self._lock = threading.Lock()
        self._n: dict[str, int] = {}

    def einstellungen(self):
        return {"test": True}

    def start(self, rec):
        return [rec]

    def weiter(self, verlauf, antwort, fehler):
        return verlauf

    def frage(self, verlauf):
        rec = verlauf[0]
        with self._lock:
            self.aufrufe.append(rec["isco_code"])
            n = self._n.get(rec["isco_code"], 0)
            self._n[rec["isco_code"]] = n + 1
        folge = self.zeta_folge.get(rec["isco_code"], [30])
        z = folge[min(n, len(folge) - 1)]
        return ts.Antwort(text=json.dumps(bewertung_mit_zeta(rec["isco_code"], rec["beruf"], z)),
                          model_served=self.model, stop_reason="end_turn", usage={"input_tokens": 1})


def _main(argv, bewerter, tmp_path):
    return ts.main(argv + ["--out", str(tmp_path)], bewerter=bewerter, schlafen=lambda s: None)


def test_delta_lauf_ueberspringt_aktuelle(tmp_path):
    b = FakeBewerter()
    assert _main(["--provider", "claude", "--only", "2411", "2512", "--runs", "2", "--max-parallel", "1"], b, tmp_path) == 0
    assert len(b.aufrufe) == 4
    for lauf in (1, 2):
        assert len(list((tmp_path / "claude" / f"run{lauf}").glob("*.json"))) == 2
    assert not (tmp_path / "claude" / "run3").exists()
    b2 = FakeBewerter()
    _main(["--provider", "claude", "--only", "2411", "2512", "--runs", "2"], b2, tmp_path)
    assert b2.aufrufe == []                                   # alles aktuell
    _main(["--provider", "claude", "--only", "2411", "--runs", "1", "--force"], b2, tmp_path)
    assert b2.aufrufe == ["2411"]
    b3 = FakeBewerter(model="anderes-modell")
    _main(["--provider", "claude", "--only", "2512", "--runs", "1"], b3, tmp_path)
    assert b3.aufrufe == ["2512"]                             # anderes Modell → neu
    zeilen = (tmp_path / "claude" / "protokoll.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(zeilen) == 6


def test_veralteter_hash_wird_neu_bewertet(tmp_path, pilot):
    b = FakeBewerter()
    _main(["--provider", "claude", "--only", "2512", "--runs", "1"], b, tmp_path)
    pfad = next((tmp_path / "claude" / "run1").glob("2512_*.json"))
    d = json.loads(pfad.read_text(encoding="utf-8"))
    d["meta"]["input_hash"] = "0" * 64
    pfad.write_text(json.dumps(d), encoding="utf-8")
    b2 = FakeBewerter()
    _main(["--provider", "claude", "--only", "2512", "--runs", "1"], b2, tmp_path)
    assert b2.aufrufe == ["2512"]


def test_dritter_lauf_nur_bei_grosser_abweichung(tmp_path):
    # 2411: ζ 30 % → 50 % (Δ Score 2.0 > 1.0) → Lauf 3; 2512: 30 % → 35 % (Δ 0.5) → kein Lauf 3
    b = FakeBewerter(zeta_folge={"2411": [30, 50, 40], "2512": [30, 35]})
    _main(["--provider", "claude", "--only", "2411", "2512", "--runs", "2", "--max-parallel", "1"], b, tmp_path)
    run3 = list((tmp_path / "claude" / "run3").glob("*.json"))
    assert [p.name[:4] for p in run3] == ["2411"]
    assert b.aufrufe.count("2411") == 3 and b.aufrufe.count("2512") == 2
    d = json.loads(run3[0].read_text(encoding="utf-8"))
    assert d["meta"]["lauf"] == 3 and d["meta"]["reihenfolge_seed"] == ts.SEED + 3


def test_braucht_dritten_lauf_schwelle():
    def datei(z):
        return {"meta": {"status": "ok"}, "bewertung": bewertung_mit_zeta("9901", "T", z)}
    assert ts.braucht_dritten_lauf(datei(30), datei(41))
    assert not ts.braucht_dritten_lauf(datei(30), datei(40))       # genau 1.0 → nicht > Schwelle
    assert not ts.braucht_dritten_lauf(datei(30), None)


def test_reihenfolge_fest_gemischt(pilot):
    r1, r1b, r2 = ts.reihenfolge(pilot, 1), ts.reihenfolge(pilot, 1), ts.reihenfolge(pilot, 2)
    assert [e.datei for e in r1] == [e.datei for e in r1b]
    assert [e.datei for e in r1] != [e.datei for e in r2]
    assert sorted(e.datei for e in r1) == sorted(e.datei for e in pilot)


# --------------------------------------------------------------------------- Dry-Run ohne Netz

@pytest.fixture
def kein_netz(monkeypatch):
    def verboten(*a, **kw):
        raise AssertionError("Netzzugriff im Dry-Run")
    monkeypatch.setattr(socket, "socket", verboten)
    monkeypatch.setattr(socket, "create_connection", verboten)


@pytest.mark.parametrize("provider", ["claude", "gemini"])
def test_dry_run_ohne_netz(provider, tmp_path, capsys, kein_netz, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    assert ts.main(["--provider", provider, "--pilot", "--runs", "2", "--dry-run", "--out", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "15 Einträge × 2 Läufe" in out and "Aufrufe (Lauf 1..N, ohne dritten Lauf): 30" in out
    assert "bis zu 15 weitere" in out and "$" in out
    assert not (tmp_path / provider).exists()


def test_schaetzung_rechnet_kosten(pilot):
    b = ts.ClaudeBewerter(client=FakeAnthropic([]))
    s = ts.schaetze(b, pilot, 30, 15)
    assert s["aufrufe"] == 30 and s["usd_mit_cache"] < s["usd_ohne_cache"]
    close(s["usd_ohne_cache"], ts.kosten_usd("claude", s["input_tokens"], s["output_tokens"]), tol=0.01)
    s2 = ts.schaetze(b, pilot[:2], 2, 0, zaehlen=True)
    assert s2["methode"] == "count_tokens" and s2["input_tokens_je_aufruf"] == 12345
    g = ts.schaetze(ts.GeminiBewerter(client=FakeGemini([])), pilot[:1], 1, 0, zaehlen=True)
    assert g["input_tokens_je_aufruf"] == 23456 and g["usd_ab_2026_12"] > g["usd_ohne_cache"]


# --------------------------------------------------------------------------- Aggregation

def _schreibe(basis: Path, provider: str, lauf: int, e: ti.Eintrag, bew: dict, status="ok", h=None):
    p = basis / provider / f"run{lauf}" / e.datei
    p.parent.mkdir(parents=True, exist_ok=True)
    meta = {"status": status, "input_hash": h or e.input_hash, "rubrik_version": "2.2", "provider": provider,
            "model_requested": "x", "lauf": lauf}
    p.write_text(json.dumps({"meta": meta, "bewertung": bew}, ensure_ascii=False), encoding="utf-8")


def test_aggregation_von_hand_nachgerechnet(tmp_path, eintraege):
    e = next(x for x in eintraege if x.isco_code == "2512")
    _schreibe(tmp_path, "claude", 1, e, bewertung_mit_zeta(e.isco_code, e.beruf, 40, "1-2 Jahre", "Risiko C1 betrifft Code."))
    _schreibe(tmp_path, "claude", 2, e, bewertung_mit_zeta(e.isco_code, e.beruf, 60, "3-5 Jahre", "Risiko C2 betrifft Code."))
    _schreibe(tmp_path, "gemini", 1, e, bewertung_mit_zeta(e.isco_code, e.beruf, 20, "5-10 Jahre", "Risiko G1 betrifft Code."))
    _schreibe(tmp_path, "gemini", 2, e, bewertung_mit_zeta(e.isco_code, e.beruf, 99), status="fehlgeschlagen")
    w: list[str] = []
    laeufe = {p: ta.lade_laeufe(tmp_path, p, eintraege, w) for p in ta.PROVIDER}
    df = ta.aggregiere(eintraege, laeufe)
    assert len(df) == _anzahl_eintraege() and list(df.columns) == ta.SPALTEN
    r = df[df.isco_code == "2512"].iloc[0]
    close(r.score_aufgaben, 4.0)                    # (4 + 6 + 2) / 3
    close(r.score_aufgaben_claude, 5.0)
    close(r.score_aufgaben_gemini, 2.0)
    close(r.delta_provider, 3.0)
    close(r.delta_laeufe_claude, 2.0)
    assert math.isnan(r.delta_laeufe_gemini)
    close(r.delta_laeufe, 2.0)
    close(r.score_zeitersparnis, 4.0 * 0.6)         # delegierend 30-50 → (1 − 0.40)
    close(r.anteil_delegierend, 1.0)
    close(r.score_aufgaben_beta, 4.0)
    assert r.n_laeufe_claude == 2 and r.n_laeufe_gemini == 1
    assert r.flag_unsicher and "Provider-Abweichung" in r.flag_grund and "Läufe-Spannweite" in r.flag_grund
    assert r.zeitrahmen == "3-5 Jahre"              # Median von 1-2 / 3-5 / 5-10
    assert r.zeitrahmen_claude == "3-5 Jahre"       # Gleichstand 1-2 / 3-5 → spätere
    assert r.haupt_risiko == "Risiko C1 betrifft Code."   # |4−4| = 0 → claude/run1
    assert r.text_quelle == "claude/run1"
    assert any("fehlgeschlagen" in x for x in w)
    leer = df[df.isco_code == "2411"].iloc[0]
    assert leer.n_laeufe_claude == 0 and math.isnan(leer.score_aufgaben) and leer.flag_unsicher


def test_aggregation_ignoriert_veraltete_und_ungueltige(tmp_path, eintraege):
    e = next(x for x in eintraege if x.isco_code == "2411")
    _schreibe(tmp_path, "claude", 1, e, bewertung_mit_zeta(e.isco_code, e.beruf, 50), h="f" * 64)
    kaputt = bewertung_mit_zeta(e.isco_code, e.beruf, 50)
    kaputt["taetigkeiten"][0]["zeitanteil_pct"] = 49
    _schreibe(tmp_path, "claude", 2, e, kaputt)
    w: list[str] = []
    laeufe = ta.lade_laeufe(tmp_path, "claude", eintraege, w)
    assert laeufe[e.schluessel] == []
    assert any("veraltet" in x for x in w) and any("ungültig" in x for x in w)
    laeufe = ta.lade_laeufe(tmp_path, "claude", eintraege, [], auch_veraltet=True)
    assert len(laeufe[e.schluessel]) == 1


def test_zeitrahmen_median_und_textwahl():
    assert ta.zeitrahmen_median(["1-2 Jahre", ">10 Jahre"]) == ">10 Jahre"
    assert ta.zeitrahmen_median(["5-10 Jahre", "1-2 Jahre", "3-5 Jahre", "5-10 Jahre"]) == "5-10 Jahre"
    assert ta.zeitrahmen_median(["3-5 Jahre"]) == "3-5 Jahre"
    assert ta.zeitrahmen_median([]) is None

    def lauf(p, n, z):
        b = bewertung_mit_zeta("9901", "T", z, risiko=f"Text {p}{n} zum Testen.")
        return ta.Lauf(p, n, b, tr.kennzahlen(b))
    laeufe = [lauf("claude", 1, 30), lauf("claude", 2, 50), lauf("gemini", 1, 50)]
    assert ta.text_lauf(laeufe, 4.0).quelle == "claude/run1"     # Gleichstand → erster
    assert ta.text_lauf(laeufe, 4.6).quelle == "claude/run2"


def test_aggregate_main_schreibt_csv(tmp_path, eintraege):
    e = next(x for x in eintraege if x.isco_code == "2512")
    _schreibe(tmp_path, "claude", 1, e, bewertung_mit_zeta(e.isco_code, e.beruf, 40))
    out = tmp_path / "scores_aufgaben.csv"
    assert ta.main(["--base-dir", str(tmp_path), "--out", str(out)]) == 0
    import pandas as pd
    df = pd.read_csv(out, dtype={"isco_code": str})
    assert len(df) == _anzahl_eintraege() and df.loc[df.isco_code == "2512", "score_aufgaben"].iloc[0] == 4.0


# --------------------------------------------------------------------------- Vergleichsbericht

def test_vergleich_bericht(tmp_path, eintraege):
    e = next(x for x in eintraege if x.isco_code == "2512")
    _schreibe(tmp_path, "claude", 1, e, bewertung_mit_zeta(e.isco_code, e.beruf, 70))
    _schreibe(tmp_path, "gemini", 1, e, bewertung_mit_zeta(e.isco_code, e.beruf, 60))
    out = tmp_path / "vergleich.md"
    assert tv.main(["--base-dir", str(tmp_path), "--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    # Pilot-ζ 7.25 → kaufmännisch 7.3 (deterministisch, unabhängig von Gleitkomma-Rauschen)
    assert "| 2512 | Softwareentwickler | 7.3 | 7.0 | 6.0 | 6.5 | -0.3 | -1.3 | 1.0 |" in text
    assert "ILO 2025" in text and "Pilot (Abo) ζ (n)" in text
    assert "0.88 (15)" in text          # Pilot vs. ILO, wie in der Pilot-Auswertung


# --------------------------------------------------------------------------- Messwerte, Paketprüfung, Token-Zeile

@pytest.fixture
def gemini_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-ohne-netz")


def _messdatei(basis: Path, e: ti.Eintrag, usage: dict, provider="claude", stufe=("effort", "high")):
    p = basis / provider / "run1" / e.datei
    p.parent.mkdir(parents=True, exist_ok=True)
    meta = {"status": "ok", "einstellungen": {stufe[0]: stufe[1]}, "usage": usage, "usage_je_versuch": [usage]}
    p.write_text(json.dumps({"meta": meta, "bewertung": None}), encoding="utf-8")


def test_dry_run_nutzt_gemessene_usage(tmp_path, pilot, capsys):
    e = next(x for x in pilot if x.isco_code == "2512")
    _messdatei(tmp_path, e, {"input_tokens": 3003, "cache_creation_input_tokens": 36937,
                             "cache_read_input_tokens": 0, "output_tokens": 4847})
    b = ts.ClaudeBewerter(client=FakeAnthropic([]))
    s = ts.schaetze(b, pilot, 30, 15, basis=tmp_path)
    assert s["output_tokens_je_aufruf"] == 4847 and s["output_methode"] == "gemessen aus 1 Aufrufen"
    assert s["input_tokens_je_aufruf"] == 39940 and s["system_tokens_geschaetzt"] == 36937
    assert s["usd_batch_cache_hoch"] < s["usd_batch_ohne_cache"] < s["usd_ohne_cache"]
    close(s["usd_batch_ohne_cache"], s["usd_ohne_cache"] * 0.5)
    # andere Stufe → nicht verwendet, Schätzwert aus AUSGABE_TOKENS
    s2 = ts.schaetze(ts.ClaudeBewerter(client=FakeAnthropic([]), effort="low"), pilot, 30, 15, basis=tmp_path)
    assert s2["output_methode"] == "Schätzung" and s2["output_tokens_je_aufruf"] == ts.AUSGABE_TOKENS["low"]
    assert ts.schaetze(b, pilot, 1, 0)["output_tokens_je_aufruf"] == ts.AUSGABE_TOKENS["high"] == 5500
    assert ts.main(["--provider", "claude", "--pilot", "--runs", "2", "--dry-run", "--out", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "gemessen aus 1 Aufrufen" in out and "~4,847" in out and "im Batch-Modus (−50%)" in out


def test_gemessene_usage_gemini(tmp_path, pilot):
    e = pilot[0]
    _messdatei(tmp_path, e, {"prompt_token_count": 40000, "candidates_token_count": 3000,
                             "thoughts_token_count": 2000, "cached_content_token_count": 30000},
               provider="gemini", stufe=("thinking_level", "high"))
    g = ts.gemessene_usage(tmp_path, "gemini", "high")
    assert g == {"n": 1, "output": 5000.0, "input": 40000.0, "system": 30000.0}
    assert ts.gemessene_usage(tmp_path, "claude", "high") is None


def test_fehlendes_sdk_klare_meldung(tmp_path, monkeypatch, caplog):
    import sys
    monkeypatch.setitem(sys.modules, "google.genai", None)        # Import scheitert wie ohne Paket
    with pytest.raises(ts.FatalerFehler) as ex:
        ts.pruefe_pakete("gemini")
    msg = str(ex.value)
    assert "google-genai" in msg and "python -m pip install -r requirements-scoring.txt" in msg
    assert "pip show google" in msg
    assert ts.main(["--provider", "gemini", "--only", "2512", "--runs", "1", "--out", str(tmp_path)]) == 3
    assert "requirements-scoring.txt" in caplog.text
    assert not (tmp_path / "gemini").exists()

    def kaputt(name):
        raise ModuleNotFoundError(f"No module named '{name}'")
    with pytest.raises(ts.FatalerFehler, match="«anthropic» fehlt"):
        ts.pruefe_pakete("claude", importieren=kaputt)


def test_gemini_tokenzeile_und_usage(tmp_path, eintrag, capsys, gemini_key):
    from google.genai import types
    r = types.GenerateContentResponse.model_validate({
        "candidates": [{"content": {"role": "model", "parts": [{"text": _gueltig(eintrag)}]}, "finish_reason": "STOP"}],
        "model_version": "gemini-4-argon",
        "usage_metadata": {"prompt_token_count": 40000, "candidates_token_count": 3000, "thoughts_token_count": 9000,
                           "cached_content_token_count": 30000, "total_token_count": 52000,
                           "prompt_tokens_details": [{"modality": "TEXT", "token_count": 40000}]}})
    b = ts.GeminiBewerter(client=FakeGemini([r]))
    assert b._config().automatic_function_calling.disable is True
    assert ts.main(["--provider", "gemini", "--only", "2512", "--runs", "1", "--out", str(tmp_path)], bewerter=b) == 0
    out = capsys.readouterr().out
    assert "Tokens: Input 40,000 (davon Cache 30,000) · Output 12,000" in out
    d = json.loads(next((tmp_path / "gemini" / "run1").glob("2512_*.json")).read_text(encoding="utf-8"))
    u = d["meta"]["usage"]
    assert u["prompt_token_count"] == 40000 and u["thoughts_token_count"] == 9000
    assert u["cached_content_token_count"] == 30000
    assert d["meta"]["usage_je_versuch"][0]["prompt_tokens_details"][0]["modality"] == "TEXT"


# --------------------------------------------------------------------------- Batch-Modus

BATCH_ISCO = ["2411", "2512", "4110", "5223"]      # 5 Einträge (5223: Verkäufer + Drogist)


class FakeAnthropicBatch(FakeAnthropic):
    """Attrappe für client.messages.batches.create/retrieve/results (+ beta.messages.stream)."""

    def __init__(self, antworten=()):
        super().__init__(antworten)
        self.erstellt: list[list[dict]] = []
        self.status: dict[str, str] = {}
        self.ergebnisse: dict[str, list] = {}
        self.abrufe = Counter()
        self.messages = SimpleNamespace(batches=SimpleNamespace(create=self._create, retrieve=self._retrieve,
                                                                results=self._results))

    def _create(self, requests):
        self.erstellt.append(copy.deepcopy(list(requests)))
        bid = f"msgbatch_{len(self.erstellt):02d}"
        self.status[bid] = "in_progress"
        return SimpleNamespace(id=bid, processing_status="in_progress")

    def _retrieve(self, bid):
        self.abrufe["retrieve"] += 1
        return SimpleNamespace(processing_status=self.status[bid], expires_at="2026-10-14T12:00:00Z",
                               request_counts=SimpleNamespace(processing=0, succeeded=3, errored=1, canceled=0,
                                                              expired=0))

    def _results(self, bid):
        self.abrufe["results"] += 1
        return iter(self.ergebnisse.get(bid, []))


def c_erg(cid, typ="succeeded", message=None, error=None):
    res = SimpleNamespace(type=typ, message=message) if typ == "succeeded" else SimpleNamespace(type=typ, error=error)
    return SimpleNamespace(custom_id=cid, result=res)


def _zustand(tmp_path, provider="claude"):
    return [z for _, z in tb.lade_zustaende(tmp_path, provider)]


def _batch(argv, b, tmp_path):
    return ts.main(argv + ["--out", str(tmp_path)], bewerter=b, schlafen=lambda s: None)


def _datei(tmp_path, provider, lauf, isco, beruf_teil=""):
    treffer = [p for p in (tmp_path / provider / f"run{lauf}").glob(f"{isco}_*.json") if beruf_teil in p.name]
    assert len(treffer) == 1, treffer
    return json.loads(treffer[0].read_text(encoding="utf-8"))


def test_custom_id_schema_und_eindeutig(eintraege):
    ids = [tb.custom_id(lauf, e) for lauf in (1, 2, 3) for e in eintraege]
    assert all(re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", i) for i in ids)
    assert len(set(ids)) == len(ids)
    assert tb.custom_id(1, ti.Eintrag("2512", "x", {}, "h")) == "r1-2512_x"
    lang = SimpleNamespace(schluessel="2512_" + "x" * 70, isco_code="2512")
    assert tb.CUSTOM_ID_RE.match(tb.custom_id(1, lang))


def test_claude_submit_payload_und_zustand(tmp_path, capsys):
    fake = FakeAnthropicBatch()
    b = ts.ClaudeBewerter(client=fake)
    assert _batch(["--provider", "claude", "--only", "2411", "2512", "--runs", "2", "--batch", "submit"], b, tmp_path) == 0
    assert len(fake.erstellt) == 1 and len(fake.erstellt[0]) == 4
    for req in fake.erstellt[0]:
        assert tb.CUSTOM_ID_RE.match(req["custom_id"])
        p = req["params"]
        assert set(p) == {"model", "max_tokens", "system", "messages", "thinking", "output_config"}
        assert p["model"] == "claude-opus-5-5" and p["thinking"] == {"type": "adaptive"}
        assert p["output_config"]["effort"] == "high"
        assert p["output_config"]["format"] == {"type": "json_schema", "schema": tr.schema_fuer_claude()}
        assert p["system"][0]["text"] == tr.system_prompt()
        assert p["system"][0]["cache_control"] == {"type": "ephemeral"}
        assert p["messages"][0]["role"] == "user" and "Input-Datei des Berufs" in p["messages"][0]["content"]
    assert sorted(r["custom_id"][:3] for r in fake.erstellt[0]) == ["r1-", "r1-", "r2-", "r2-"]
    pfad = tmp_path / "claude" / "batches" / "msgbatch_01.json"
    z = json.loads(pfad.read_text(encoding="utf-8"))
    assert z["batch_id"] == "msgbatch_01" and z["model"] == "claude-opus-5-5" and z["rubrik_version"] == "2.2"
    assert z["eingesammelt"] is None and z["anzahl"] == 4 and z["einstellungen"]["fallbacks"] is None
    assert z["einstellungen"]["cache_ttl"] == "5m" and z["erstellt"]
    info = z["anfragen"]["r1-2512_softwareentwickler"]
    assert info["lauf"] == 1 and info["isco_code"] == "2512" and len(info["input_hash"]) == 64
    assert info["datei"] == "2512_softwareentwickler.json" and info["typ"] == "neu"
    text = pfad.read_text(encoding="utf-8")
    assert "sk-ant" not in text and "api_key" not in text.lower()
    assert "Eingereicht: 1 Batch" in capsys.readouterr().out
    # Delta: alles in offenem Batch → nichts erneut einreichen; --force reicht neu ein
    assert _batch(["--provider", "claude", "--only", "2411", "2512", "--runs", "2", "--batch", "submit"], b, tmp_path) == 0
    assert len(fake.erstellt) == 1 and "4 bereits in offenen Batches" in capsys.readouterr().out
    _batch(["--provider", "claude", "--only", "2512", "--runs", "1", "--batch", "submit", "--force",
            "--cache-ttl", "1h"], b, tmp_path)
    assert len(fake.erstellt) == 2
    assert fake.erstellt[1][0]["params"]["system"][0]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}


def _submit_und_ergebnisse(tmp_path):
    """5 Einträge × 1 Lauf: ok, ungültig, Refusal, errored — einer fehlt; Ergebnisse in vertauschter Reihenfolge."""
    fake = FakeAnthropicBatch()
    b = ts.ClaudeBewerter(client=fake)
    assert _batch(["--provider", "claude", "--only", *BATCH_ISCO, "--runs", "1", "--batch", "submit"], b, tmp_path) == 0
    z = _zustand(tmp_path)[0]
    cid = {info["isco_code"] + ("D" if "drogist" in info["datei"] else ""): c for c, info in z["anfragen"].items()}
    falsch = bewertung("4110", "Allgemeine Bürokräfte")
    falsch["taetigkeiten"][1]["zeitanteil_pct"] = 5
    fake.ergebnisse["msgbatch_01"] = [
        c_erg(cid["4110"], message=claude_msg(json.dumps(falsch, ensure_ascii=False))),
        c_erg(cid["2411"], typ="errored", error=SimpleNamespace(type="error", error={"type": "api_error", "message": "x"})),
        c_erg(cid["5223"], message=claude_msg("", stop="refusal", stop_details={"category": "cyber", "explanation": "e"})),
        c_erg(cid["2512"], message=claude_msg(json.dumps(bewertung("2512", "Softwareentwickler"), ensure_ascii=False))),
    ]                                                   # 5223 Drogist/in fehlt (Teil-Ergebnis)
    fake.status["msgbatch_01"] = "ended"
    return fake, b


def test_claude_collect_gemischt_und_idempotent(tmp_path, capsys):
    fake, b = _submit_und_ergebnisse(tmp_path)
    assert _batch(["--provider", "claude", "--batch", "collect"], b, tmp_path) == 1
    out = capsys.readouterr().out
    assert "1 ok, 1 ungültig, 1 Refusal, 2 Fehler/abgelaufen/fehlend" in out and "--batch followup" in out
    ok = _datei(tmp_path, "claude", 1, "2512")
    m = ok["meta"]
    assert m["status"] == "ok" and m["modus"] == "batch" and m["batch_id"] == "msgbatch_01"
    assert m["custom_id"] == "r1-2512_softwareentwickler" and m["model_served"] == "claude-opus-5-5"
    assert m["stop_reason"] == "end_turn" and m["usage"]["cache_read_input_tokens"] == 20000
    assert m["einstellungen"]["fallbacks"] is None and ok["bewertung"]["isco_code"] == "2512"
    ung = _datei(tmp_path, "claude", 1, "4110")
    assert ung["meta"]["fehler_art"] == "validierung" and "summieren auf 95" in ung["meta"]["probleme"][0]
    assert ung["rohantwort"] and ung["meta"]["status"] == "fehlgeschlagen"
    ref = _datei(tmp_path, "claude", 1, "5223", "verkaeufer")
    assert ref["meta"]["fehler_art"] == "refusal" and ref["meta"]["stop_reason"] == "refusal"
    assert ref["meta"]["stop_details"]["category"] == "cyber"
    assert _datei(tmp_path, "claude", 1, "2411")["meta"]["fehler_art"] == "errored"
    assert _datei(tmp_path, "claude", 1, "5223", "drogist")["meta"]["fehler_art"] == "fehlt"
    z = _zustand(tmp_path)[0]
    assert z["eingesammelt"] and z["ergebnis"] == {"ok": 1, "validierung": 1, "refusal": 1, "errored": 1, "fehlt": 1}
    assert len((tmp_path / "claude" / "protokoll.jsonl").read_text(encoding="utf-8").splitlines()) == 5
    # Idempotenz: zweites collect ruft nichts ab und ändert keine Datei
    vorher = {p: p.read_text(encoding="utf-8") for p in (tmp_path / "claude").rglob("*.json*")}
    abrufe = dict(fake.abrufe)
    assert _batch(["--provider", "claude", "--batch", "collect"], b, tmp_path) == 0
    assert "nichts einzusammeln" in capsys.readouterr().out and dict(fake.abrufe) == abrufe
    assert {p: p.read_text(encoding="utf-8") for p in (tmp_path / "claude").rglob("*.json*")} == vorher


def test_collect_wartet_auf_unfertigen_batch(tmp_path, capsys):
    fake = FakeAnthropicBatch()
    b = ts.ClaudeBewerter(client=fake)
    _batch(["--provider", "claude", "--only", "2512", "--runs", "1", "--batch", "submit"], b, tmp_path)
    assert _batch(["--provider", "claude", "--batch", "status"], b, tmp_path) == 0
    out = capsys.readouterr().out
    assert "msgbatch_01  in_progress  1 Anfragen" in out and '"succeeded": 3' in out
    assert _batch(["--provider", "claude", "--batch", "collect"], b, tmp_path) == 0
    assert "noch nicht fertig: msgbatch_01 (in_progress)" in capsys.readouterr().out
    assert not (tmp_path / "claude" / "run1").exists() and fake.abrufe["results"] == 0
    z = _zustand(tmp_path)[0]
    assert z["eingesammelt"] is None and z["letzter_status"]["status"] == "in_progress"


def test_collect_behaelt_vorhandene_gueltige(tmp_path):
    fake = FakeAnthropicBatch()
    b = ts.ClaudeBewerter(client=fake)
    _batch(["--provider", "claude", "--only", "2512", "--runs", "1", "--batch", "submit"], b, tmp_path)
    _main(["--provider", "claude", "--only", "2512", "--runs", "1"], FakeBewerter(), tmp_path)   # inzwischen synchron
    vorher = _datei(tmp_path, "claude", 1, "2512")
    fake.status["msgbatch_01"] = "ended"
    fake.ergebnisse["msgbatch_01"] = [c_erg("r1-2512_softwareentwickler", typ="expired")]
    assert _batch(["--provider", "claude", "--batch", "collect"], b, tmp_path) == 1
    assert _datei(tmp_path, "claude", 1, "2512") == vorher
    assert _zustand(tmp_path)[0]["ergebnis"] == {"expired": 1}


def test_followup_wiederholung_korrektur_refusal(tmp_path, capsys):
    fake, b = _submit_und_ergebnisse(tmp_path)
    _batch(["--provider", "claude", "--batch", "collect"], b, tmp_path)
    capsys.readouterr()
    argv = ["--provider", "claude", "--only", *BATCH_ISCO, "--runs", "1", "--batch", "followup"]
    assert _batch(argv + ["--dry-run"], b, tmp_path) == 0
    out = capsys.readouterr().out
    assert "2 Wiederholungen, 1 Korrekturen, 0 dritte Läufe" in out and "1 Refusals" in out
    assert "Dry-Run Batch" in out and len(fake.erstellt) == 1
    assert _batch(argv, b, tmp_path) == 0
    assert "vorgemerkt (Refusal): run1/5223_verkaeufer" in capsys.readouterr().out
    reqs = {r["custom_id"]: r["params"] for r in fake.erstellt[1]}
    assert set(reqs) == {"r1-2411_wirtschaftspruefer_steuerberater_und_ver", "r1-4110_allgemeine_buerokraefte",
                         "r1-5223_drogist_in"}
    korr = reqs["r1-4110_allgemeine_buerokraefte"]["messages"]
    assert [x["role"] for x in korr] == ["user", "assistant", "user"] and "summieren auf 95" in korr[2]["content"]
    assert all("fallbacks" not in p for p in reqs.values())
    z = [z for z in _zustand(tmp_path) if z["art"] == "followup"][0]
    assert z["anfragen"]["r1-4110_allgemeine_buerokraefte"]["typ"] == "korrektur"
    assert z["anfragen"]["r1-4110_allgemeine_buerokraefte"]["versuch"] == 2
    assert z["anfragen"]["r1-2411_wirtschaftspruefer_steuerberater_und_ver"]["typ"] == "wiederholung"
    # erneuter followup: Rest ist offen → nur noch der Refusal, jetzt synchron mit Fallback
    verk = next(e for e in ti.baue_eintraege(["5223"]) if "Verk" in e.beruf)
    fake.antworten = [claude_msg(_gueltig(verk))]
    assert _batch(argv + ["--refusal-sync"], b, tmp_path) == 0
    assert len(fake.erstellt) == 2
    sync = fake.aufrufe[-1]
    assert sync["fallbacks"] == "default" and sync["betas"] == ["server-side-fallback-2026-07-01"]
    ref = _datei(tmp_path, "claude", 1, "5223", "verkaeufer")
    assert ref["meta"]["status"] == "ok" and ref["meta"]["modus"] == "synchron"


def _gueltige_datei(basis, e, lauf, zeta, model="claude-opus-5-5"):
    meta = {"status": "ok", "input_hash": e.input_hash, "rubrik_version": tr.RUBRIK_VERSION,
            "model_requested": model, "lauf": lauf}
    ts.speichere(ts.ziel_pfad(basis, "claude", lauf, e),
                 ts.Ergebnis("ok", bewertung_mit_zeta(e.isco_code, e.beruf, zeta), meta))


def test_followup_dritter_lauf_nach_delta_zeta(tmp_path, capsys):
    es = {e.isco_code: e for e in ti.baue_eintraege(["2411", "2512"])}
    for isco, (z1, z2) in {"2411": (30, 50), "2512": (30, 35)}.items():
        _gueltige_datei(tmp_path, es[isco], 1, z1)
        _gueltige_datei(tmp_path, es[isco], 2, z2)
    fake = FakeAnthropicBatch()
    b = ts.ClaudeBewerter(client=fake)
    argv = ["--provider", "claude", "--only", "2411", "2512", "--runs", "2", "--batch"]
    assert _batch(argv + ["followup", "--no-third-run"], b, tmp_path) == 0
    assert "Nichts nachzuholen" in capsys.readouterr().out and not fake.erstellt
    assert _batch(argv + ["followup"], b, tmp_path) == 0
    assert "0 Wiederholungen, 0 Korrekturen, 1 dritte Läufe" in capsys.readouterr().out
    cid3 = "r3-2411_wirtschaftspruefer_steuerberater_und_ver"
    assert [r["custom_id"] for r in fake.erstellt[0]] == [cid3]
    assert _zustand(tmp_path)[0]["anfragen"][cid3]["typ"] == "dritter_lauf"
    # offen → kein zweites Mal
    _batch(argv + ["followup"], b, tmp_path)
    assert len(fake.erstellt) == 1 and "Nichts nachzuholen" in capsys.readouterr().out
    # nach collect: Lauf 3 gültig → followup/submit reichen nichts mehr ein
    fake.status["msgbatch_01"] = "ended"
    fake.ergebnisse["msgbatch_01"] = [c_erg(cid3, message=claude_msg(json.dumps(
        bewertung_mit_zeta("2411", es["2411"].beruf, 40), ensure_ascii=False)))]
    assert _batch(["--provider", "claude", "--batch", "collect"], b, tmp_path) == 0
    assert _datei(tmp_path, "claude", 3, "2411")["meta"]["lauf"] == 3
    _batch(argv + ["followup"], b, tmp_path)
    _batch(argv + ["submit"], b, tmp_path)
    assert len(fake.erstellt) == 1


def test_batch_dry_run_ohne_netz(tmp_path, capsys, kein_netz):
    b = ts.ClaudeBewerter(client=FakeAnthropicBatch())
    assert _batch(["--provider", "claude", "--pilot", "--runs", "2", "--batch", "submit", "--dry-run"], b, tmp_path) == 0
    out = capsys.readouterr().out
    assert "30 einzureichen" in out and "Dry-Run Batch claude" in out and "Kosten Batch (−50%)" in out
    assert "Cache-Treffer 98%" in out and not (tmp_path / "claude").exists()
    g = ts.GeminiBewerter(client=SimpleNamespace())
    assert _batch(["--provider", "gemini", "--pilot", "--runs", "2", "--batch", "submit", "--dry-run"], g, tmp_path) == 0
    assert "ab 1.12.2026" in capsys.readouterr().out


def test_claude_batch_fataler_fehler(tmp_path, caplog):
    import anthropic
    import httpx2
    fake = FakeAnthropicBatch()
    r = httpx2.Response(401, request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages/batches"))

    def nein(requests):
        raise anthropic.AuthenticationError("bad key", response=r, body=None)
    fake.messages.batches.create = nein
    assert _batch(["--provider", "claude", "--only", "2512", "--runs", "1", "--batch", "submit"],
                  ts.ClaudeBewerter(client=fake), tmp_path) == 3
    assert "Zugriff verweigert" in caplog.text and not (tmp_path / "claude" / "batches").exists()


class FakeGeminiBatch:
    def __init__(self):
        self.erstellt: list[dict] = []
        self.jobs: dict[str, SimpleNamespace] = {}
        self.batches = SimpleNamespace(create=self._create, get=self._get)

    def _create(self, model, src, config):
        self.erstellt.append({"model": model, "src": list(src), "config": config})
        name = f"batches/job{len(self.erstellt)}"
        self.jobs[name] = SimpleNamespace(name=name, state=SimpleNamespace(name="JOB_STATE_PENDING"),
                                          dest=None, completion_stats=None)
        return self.jobs[name]

    def _get(self, name):
        return self.jobs[name]

    def fertig(self, name, antworten, state="JOB_STATE_SUCCEEDED"):
        self.jobs[name].state = SimpleNamespace(name=state)
        self.jobs[name].dest = SimpleNamespace(inlined_responses=antworten)


def test_gemini_batch_submit_teilen_collect(tmp_path, monkeypatch, capsys, gemini_key):
    from google.genai import types
    monkeypatch.setattr(tb.GeminiBatchAPI, "max_bytes", 200_000)      # ≈ 2 Anfragen je Batch
    fake = FakeGeminiBatch()
    g = ts.GeminiBewerter(client=fake)
    assert _batch(["--provider", "gemini", "--only", *BATCH_ISCO, "--runs", "1", "--batch", "submit"], g, tmp_path) == 0
    assert len(fake.erstellt) >= 2 and sum(len(x["src"]) for x in fake.erstellt) == 5
    req = fake.erstellt[0]["src"][0]
    assert isinstance(req, types.InlinedRequest) and fake.erstellt[0]["model"] == "gemini-4-argon"
    assert tb.CUSTOM_ID_RE.match(req.metadata["custom_id"])
    cfg = req.config
    assert cfg.system_instruction == tr.system_prompt() and cfg.response_mime_type == "application/json"
    assert cfg.response_json_schema == tr.schema_fuer_gemini() and cfg.max_output_tokens == 65536
    lvl = cfg.thinking_config.thinking_level
    assert str(getattr(lvl, "value", lvl)).upper() == "HIGH"
    assert cfg.automatic_function_calling.disable is True and cfg.temperature is None
    assert req.contents[0].parts[0].text.startswith("Bewerte den folgenden Beruf")
    zust = tb.lade_zustaende(tmp_path, "gemini")
    assert len(zust) == len(fake.erstellt) and all(p.name.startswith("batches_job") for p, _ in zust)
    # erster Job: Antworten mit metadata in umgekehrter Reihenfolge, eine mit Fehler; übrige Jobs unfertig
    z1 = next(z for _, z in zust if z["batch_id"] == "batches/job1")
    antworten = []
    for cid in reversed(z1["reihenfolge"]):
        info = z1["anfragen"][cid]
        antworten.append(types.InlinedResponse(
            metadata={"custom_id": cid},
            response=gemini_resp(json.dumps(bewertung(info["isco_code"], info["beruf"]), ensure_ascii=False))))
    antworten[0] = types.InlinedResponse(metadata={"custom_id": z1["reihenfolge"][-1]},
                                         error=types.JobError(code=13, message="intern"))
    fake.fertig(z1["batch_id"], antworten)
    assert _batch(["--provider", "gemini", "--batch", "collect"], g, tmp_path) == 1
    out = capsys.readouterr().out
    assert "noch nicht fertig: batches/job2 (JOB_STATE_PENDING)" in out
    assert f"{len(z1['reihenfolge']) - 1} ok" in out
    for cid in z1["reihenfolge"][:-1]:
        info = z1["anfragen"][cid]
        d = json.loads((tmp_path / "gemini" / "run1" / info["datei"]).read_text(encoding="utf-8"))
        assert d["meta"]["status"] == "ok" and d["meta"]["model_served"] == "gemini-4-argon"
        assert d["meta"]["zuordnung"] == "custom_id" and d["meta"]["usage"]["thoughts_token_count"] == 9000
    letzte = z1["anfragen"][z1["reihenfolge"][-1]]
    d = json.loads((tmp_path / "gemini" / "run1" / letzte["datei"]).read_text(encoding="utf-8"))
    assert d["meta"]["fehler_art"] == "errored" and "intern" in d["meta"]["fehler"][0]
    assert _batch(["--provider", "gemini", "--batch", "status"], g, tmp_path) == 0
    assert "JOB_STATE_PENDING" in capsys.readouterr().out


def test_gemini_collect_positionell_und_blockiert(tmp_path, gemini_key):
    from google.genai import types
    fake = FakeGeminiBatch()
    g = ts.GeminiBewerter(client=fake)
    _batch(["--provider", "gemini", "--only", "2411", "2512", "--runs", "1", "--batch", "submit"], g, tmp_path)
    z = _zustand(tmp_path, "gemini")[0]
    infos = [z["anfragen"][c] for c in z["reihenfolge"]]
    blockiert = types.GenerateContentResponse.model_validate({"prompt_feedback": {"block_reason": "SAFETY"}})
    fake.fertig(z["batch_id"], [
        types.InlinedResponse(response=gemini_resp(json.dumps(bewertung(infos[0]["isco_code"], infos[0]["beruf"]),
                                                              ensure_ascii=False))),
        types.InlinedResponse(response=blockiert)])
    assert _batch(["--provider", "gemini", "--batch", "collect"], g, tmp_path) == 1
    d0 = json.loads((tmp_path / "gemini" / "run1" / infos[0]["datei"]).read_text(encoding="utf-8"))
    assert d0["meta"]["status"] == "ok" and d0["meta"]["zuordnung"] == "position"
    d1 = json.loads((tmp_path / "gemini" / "run1" / infos[1]["datei"]).read_text(encoding="utf-8"))
    assert d1["meta"]["fehler_art"] == "refusal"
    auftraege, refusals, _ = tb.followup_auswahl(g, ti.baue_eintraege(["2411", "2512"]), tmp_path, 1, {}, False, 1.0)
    assert auftraege == [] and [e.datei for e, _ in refusals] == [infos[1]["datei"]]
