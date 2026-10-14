"""Invarianten der ESCO-Zuordnungen in den versionierten Daten (Issue #52)."""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "data"))
from enrich_with_esco import QUALITAETEN, isco_konsistenz  # noqa: E402

PROC = Path(__file__).parent.parent / "data" / "processed"
DATEIEN = ["berufe_ch_esco.csv", "berufe_ch_esco_verified.csv", "scores.csv"]
FELDER = ["esco_uri", "esco_title", "esco_description", "description_source",
          "esco_isco_code", "esco_match_quality"]


def lesen(name: str) -> pd.DataFrame:
    return pd.read_csv(PROC / name, dtype=str, keep_default_na=False)


@pytest.fixture(scope="module")
def scores() -> pd.DataFrame:
    return lesen("scores.csv")


@pytest.mark.parametrize("name", DATEIEN)
def test_spalten_und_werte(name):
    df = lesen(name)
    for f in FELDER:
        assert f in df.columns
    assert set(df["esco_match_quality"]) <= set(QUALITAETEN)
    mit_uri = df["esco_uri"] != ""
    # beschreibung_quelle «ESCO» genau dann, wenn eine URI vorhanden ist
    assert ((df["description_source"] == "ESCO") == mit_uri).all()
    assert ((df["esco_match_quality"] == "fallback") == ~mit_uri).all()
    assert (df["esco_description"].str.len() > 40).all()


@pytest.mark.parametrize("name", DATEIEN)
def test_jede_uri_nur_einmal(name):
    uris = lesen(name)["esco_uri"]
    uris = uris[uris != ""]
    assert not uris.duplicated().any(), uris[uris.duplicated()].tolist()


@pytest.mark.parametrize("name", DATEIEN)
def test_isco_konsistenz(name):
    df = lesen(name)
    for _, r in df[df["esco_uri"] != ""].iterrows():
        regel = isco_konsistenz(r["isco_code"], r["esco_isco_code"])
        assert regel is not None, (r["occupation"], r["isco_code"], r["esco_isco_code"])
        # «korrekt» nur bei gleichem 4-Steller; ISCO-gleich darf inhaltlich «plausibel» sein
        if r["esco_match_quality"] == "korrekt":
            assert regel == "korrekt", r["occupation"]


def test_dateien_konsistent(scores):
    s = scores.set_index("occupation")[FELDER]
    for name in DATEIEN[:2]:
        d = lesen(name).set_index("occupation")[FELDER]
        pd.testing.assert_frame_equal(d.sort_index(), s.sort_index())


def test_keine_englischen_titel(scores):
    """Titel kommen deutsch aus der API (früher z. B. «domestic cleaner»)."""
    for t in ["domestic cleaner", "public administration manager",
              "secondary school teacher", "cargo vehicle driver"]:
        assert t not in set(scores["esco_title"])


def test_bekannte_fehlzuordnungen_behoben(scores):
    s = scores.set_index("occupation")
    assert s.loc["Dipl. Pflegefachperson", "esco_isco_code"] == "2221"  # #48: nicht Diplomat
    assert "Diplomat" not in s.loc["Dipl. Pflegefachperson", "esco_title"]
    assert "Kameramann/Kamerafrau" not in set(scores["esco_title"])


def test_kompetenzen(scores):
    k = lesen("esco_kompetenzen.csv")
    assert list(k.columns) == ["occupation", "isco_code", "esco_uri", "competence",
                               "relation", "type", "competence_uri"]
    assert set(k["relation"]) == {"essential", "optional"}
    assert set(k["type"]) <= {"skill", "knowledge", ""}
    mit_uri = scores[scores["esco_uri"] != ""]
    paare = set(zip(mit_uri["occupation"], mit_uri["esco_uri"]))
    assert set(zip(k["occupation"], k["esco_uri"])) == paare  # jeder Eintrag mit URI, passende URI
    assert not k.duplicated(["occupation", "competence_uri"]).any()
    assert (k["competence"] != "").all()
