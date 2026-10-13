"""Tests für enrich_with_esco.py — ESCO-API gemockt, kein Netzwerk, kein Sprachmodell."""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "data"))
import enrich_with_esco as E  # noqa: E402

OCC = "http://data.europa.eu/esco/occupation/"
ISCO = "http://data.europa.eu/esco/isco/C"


class FakeResponse:
    def __init__(self, data, status=200):
        self._data = data
        self.status_code = status

    def json(self):
        return self._data


def concept(code, occupations=(), sub_codes=()):
    return {
        "uri": f"{ISCO}{code}", "code": code, "title": f"Gruppe {code}",
        "_links": {
            "narrowerOccupation": [{"uri": OCC + u, "title": t} for u, t in occupations],
            "narrowerConcept": [{"uri": f"{ISCO}{c}", "code": c} for c in sub_codes],
        },
    }


def occupation(uid, title, isco, code=None, desc="Beschreibung."):
    links = {"broaderIscoGroup": [{"uri": f"{ISCO}{isco}", "code": isco}]} if isco else {}
    return {"uri": OCC + uid, "title": title, "code": code or f"{isco}.1",
            "description": {"de": {"literal": desc}}, "_links": links}


@pytest.fixture
def fake_api(monkeypatch):
    """Ersetzt requests.get; Antworten je (Pfad, uri). Zeichnet alle Aufrufe auf."""
    concepts: dict[str, dict] = {}
    occupations: dict[str, dict] = {}
    calls: list[tuple[str, dict]] = []

    def get(url, params=None, headers=None, timeout=None):
        params = params or {}
        calls.append((url, dict(params)))
        uri = params.get("uri", "")
        if url.endswith("/resource/concept"):
            return FakeResponse(concepts[uri]) if uri in concepts else FakeResponse({}, 404)
        if url.endswith("/resource/occupation"):
            return FakeResponse(occupations[uri]) if uri in occupations else FakeResponse({}, 500)
        if url.endswith("/search"):
            return FakeResponse({"_embedded": {"results": []}})
        raise AssertionError(f"unerwartete URL {url}")

    monkeypatch.setattr(E.requests, "get", get)
    monkeypatch.setattr(E.time, "sleep", lambda s: None)

    def add_concept(c):
        concepts[c["uri"]] = c

    def add_occ(o):
        occupations[o["uri"]] = o

    return add_concept, add_occ, calls


# ---------------------------------------------------------------------------
# ISCO-Konsistenz
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("ours, theirs, erwartet", [
    ("2221", "2221", "korrekt"),
    (2221, "2221.2", "korrekt"),          # Zahl und ESCO-Code mit Unterebene
    ("2514", "2511", "plausibel"),        # gleiche 3-stellige Gruppe
    ("2221", "1112", None),               # Pflegefachperson → Diplomat (#48)
    ("5223", "2166", None),               # Detailhandel → Kameramann
    ("3221", "5321", "plausibel"),        # Ausnahme: ESCO hat keinen 3221-Beruf
    ("3221", "3412", None),               # Ausnahme gilt nur für die genannte Gruppe
    ("7200", "7223", "plausibel"),        # CH-Sammelcode → Untergruppe 72
    ("7200", "8211", None),
    ("2221", "", None),
    ("", "2221", None),
])
def test_isco_konsistenz(ours, theirs, erwartet):
    assert E.isco_konsistenz(ours, theirs) == erwartet


def test_ausnahmen_sind_begruendet():
    for code, (praefixe, grund) in E.ISCO_AUSNAHMEN.items():
        assert len(code) == 4 and code.isdigit()
        assert praefixe and all(p.isdigit() for p in praefixe)
        assert len(grund) > 20


def test_occupation_isco_code_ohne_broader_group():
    """Unterberufe (z. B. 2330.1.4) haben nur broaderOccupation → Präfix des ESCO-Codes."""
    assert E.occupation_isco_code({"code": "2330.1.4", "_links": {}}) == "2330"
    assert E.occupation_isco_code(occupation("x", "X", "2221")) == "2221"
    assert E.occupation_isco_code({"code": "", "_links": {}}) == ""


# ---------------------------------------------------------------------------
# Stufe 3: ISCO-Concept-Endpunkt
# ---------------------------------------------------------------------------

def test_esco_search_isco_nutzt_concept_endpunkt(fake_api):
    add_concept, _, calls = fake_api
    add_concept(concept("2221", [("a", "Krankenpfleger Allgemeine Krankenpflege"),
                                 ("b", "Fachkrankenpfleger")]))
    res = E.esco_search_isco("2221")
    assert [r["uri"] for r in res] == [OCC + "a", OCC + "b"]
    assert all(r["isco_code"] == "2221" for r in res)
    url, params = calls[0]
    assert url.endswith("/resource/concept")
    assert params["uri"] == f"{ISCO}2221"
    assert params["selectedVersion"] == E.ESCO_VERSION
    assert "iscoGroup" not in params  # wird von der API ignoriert (Ursache #52)


def test_esco_search_isco_rekursiv_und_limit(fake_api):
    """CH-Sammelcode 7200 → Concept C72 → Untergruppen → Berufe."""
    add_concept, _, _ = fake_api
    add_concept(concept("72", sub_codes=["722", "723"]))
    add_concept(concept("722", sub_codes=["7223"]))
    add_concept(concept("7223", [("z", "Zerspanungsmechaniker")]))
    add_concept(concept("723", sub_codes=["7233"]))
    add_concept(concept("7233", [("i", "Industriemechaniker"), ("l", "Landmaschinen")]))
    res = E.esco_search_isco("7200", limit=2)
    assert [r["uri"] for r in res] == [OCC + "z", OCC + "i"]
    assert res[0]["isco_code"] == "7223"


def test_esco_search_isco_ohne_beruf(fake_api):
    add_concept, _, _ = fake_api
    add_concept(concept("3221"))
    assert E.esco_search_isco("3221") == []


def test_alle_anfragen_mit_version(fake_api):
    _, add_occ, calls = fake_api
    add_occ(occupation("a", "A", "2221"))
    E.esco_get_occupation(OCC + "a")
    E.esco_search_text("Pflege")
    assert calls and all(p.get("selectedVersion") == "v1.2.1" for _, p in calls)


# ---------------------------------------------------------------------------
# Kandidatenprüfung
# ---------------------------------------------------------------------------

def test_kandidat_mit_falschem_isco_wird_ohne_ki_verworfen(fake_api, monkeypatch):
    _, add_occ, _ = fake_api
    add_occ(occupation("dipl", "Diplomat/Diplomatin", "1112"))
    add_occ(occupation("nurse", "Krankenpfleger Allgemeine Krankenpflege", "2221"))
    geprueft = []

    def validate(client, beruf, titel, beschreibung):
        geprueft.append(titel)
        return True

    monkeypatch.setattr(E, "ki_validate", validate)
    res = E._try_esco_candidates(None, "Dipl. Pflegefachperson", "2221",
                                 [{"uri": OCC + "dipl"}, {"uri": OCC + "nurse"}])
    assert geprueft == ["Krankenpfleger Allgemeine Krankenpflege"]
    assert res["esco_uri"] == OCC + "nurse"
    assert res["esco_isco_code"] == "2221"
    assert res["esco_match_qualitaet"] == "korrekt"
    assert res["beschreibung_quelle"] == "ESCO"


def test_kandidat_plausibel_und_blockiert(fake_api, monkeypatch):
    _, add_occ, _ = fake_api
    add_occ(occupation("ds", "Datenwissenschaftler", "2511"))
    add_occ(occupation("x", "Vergeben", "2514"))
    monkeypatch.setattr(E, "ki_validate", lambda *a: True)
    res = E._try_esco_candidates(None, "Data Scientist", "2514",
                                 [{"uri": OCC + "x"}, {"uri": OCC + "ds"}],
                                 blocked_uris={OCC + "x"})
    assert res["esco_uri"] == OCC + "ds"
    assert res["esco_match_qualitaet"] == "plausibel"


def test_kandidat_inhaltlich_abgelehnt(fake_api, monkeypatch):
    _, add_occ, _ = fake_api
    add_occ(occupation("a", "A", "2221"))
    monkeypatch.setattr(E, "ki_validate", lambda *a: False)
    assert E._try_esco_candidates(None, "B", "2221", [{"uri": OCC + "a"}]) is None


def test_find_best_match_stufe3_und_fallback(fake_api, monkeypatch):
    add_concept, add_occ, _ = fake_api
    add_concept(concept("5322", [("h", "Haus- und Familienpfleger")]))
    add_occ(occupation("h", "Haus- und Familienpfleger", "5322"))
    monkeypatch.setattr(E, "ki_validate", lambda *a: True)
    monkeypatch.setattr(E, "ki_alt_terms", lambda *a: [])
    res = E.find_best_match(None, "Spitex-Mitarbeiter/in", "5322")
    assert res["esco_uri"] == OCC + "h"
    assert res["esco_match_qualitaet"] == "korrekt"

    # ohne ESCO-Treffer: Fallback mit generierter Beschreibung
    monkeypatch.setattr(E, "berufsberatung_search", lambda b: "")
    monkeypatch.setattr(E, "wikipedia_description", lambda b: "")
    monkeypatch.setattr(E, "ki_generate_description", lambda *a: "Generierter Text.")
    res = E.find_best_match(None, "Maschinenführer/in", "8211")
    assert res == {"esco_uri": "", "esco_titel": "Maschinenführer/in",
                   "esco_beschreibung": "Generierter Text.", "beschreibung_quelle": "KI-generiert",
                   "esco_isco_code": "", "esco_match_qualitaet": "fallback"}


def test_merge_into_aktualisiert_und_haengt_an():
    alt = pd.DataFrame({"beruf": ["A", "B"], "isco_code": [1111, 2222],
                        "esco_uri": ["u1", "u2"], "esco_titel": ["t1", "t2"],
                        "esco_beschreibung": ["d1", "d2"], "beschreibung_quelle": ["ESCO", "ESCO"]})
    neu = pd.DataFrame([{"beruf": "B", "isco_code": 2222, "esco_uri": "u3", "esco_titel": "t3",
                         "esco_beschreibung": "d3", "beschreibung_quelle": "ESCO",
                         "esco_isco_code": "2222", "esco_match_qualitaet": "korrekt"},
                        {"beruf": "C", "isco_code": 3333, "esco_uri": "", "esco_titel": "C",
                         "esco_beschreibung": "d", "beschreibung_quelle": "KI-generiert",
                         "esco_isco_code": "", "esco_match_qualitaet": "fallback"}])
    out = E.merge_into(alt, neu)
    assert list(out["beruf"]) == ["A", "B", "C"]
    assert out.loc[1, "esco_uri"] == "u3" and out.loc[1, "esco_match_qualitaet"] == "korrekt"
    assert out.loc[0, "esco_uri"] == "u1"
