"""Streamlit-AppTest: alle Seiten laufen ohne Exception mit den versionierten Daten."""

from pathlib import Path

import pandas as pd
import pytest

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest

APP = str(Path(__file__).parent.parent / "src" / "app" / "app.py")
SEITEN = [
    "pages/0_Startseite.py",
    "pages/1_Treemap.py",
    "pages/2_Matrix.py",
    "pages/3_Branchen.py",
    "pages/4_Berufssuche.py",
    "pages/5_Methodik.py",
]
SCORES = Path(__file__).parent.parent / "data" / "processed" / "scores.csv"


def _app() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    return at


@pytest.mark.parametrize("seite", SEITEN)
def test_seite_ohne_fehler(seite):
    at = _app()
    at.switch_page(seite)
    at.run()
    assert not at.exception, [e.value for e in at.exception]


def test_startseite_zeigt_anzahl_berufe():
    at = _app()
    n = len(pd.read_csv(SCORES))
    texte = " ".join(m.value for m in at.markdown)
    assert f"für {n} Schweizer Berufe" in texte
    assert "204" not in texte


def test_berufssuche_findet_synonym_im_permalink():
    """Alter Permalink mit bisherigem CH-Titel → zusammengelegter Eintrag."""
    at = AppTest.from_file(APP, default_timeout=120)
    at.query_params["beruf"] = "Koch/Köchin EFZ"
    at.run()
    at.switch_page("pages/4_Berufssuche.py")
    at.run()
    assert not at.exception
    assert at.selectbox[0].value == "Köche"
    assert any("Koch/Köchin EFZ" in c.value for c in at.caption)
    assert any("Zusammengelegter Eintrag" in w.value for w in at.warning)


def test_berufssuche_label_enthaelt_synonyme():
    at = _app()
    at.switch_page("pages/4_Berufssuche.py")
    at.run()
    sb = at.selectbox[0]
    labels = sb.options
    assert any("Verkäufer in Handelsgeschäften" in o and "Detailhandelsfachmann/-frau EFZ" in o
               for o in labels)


@pytest.mark.parametrize("beruf, erwartet", [
    ("Dipl. Pflegefachperson", "Match-Qualität: korrekt (ESCO-ISCO 2221)"),
    ("Fachperson Gesundheit EFZ (FaGe)", "Match-Qualität: plausibel (ESCO-ISCO 5321)"),
])
def test_berufssuche_zeigt_match_qualitaet(beruf, erwartet):
    at = AppTest.from_file(APP, default_timeout=120)
    at.query_params["beruf"] = beruf
    at.run()
    at.switch_page("pages/4_Berufssuche.py")
    at.run()
    assert not at.exception
    captions = [c.value for c in at.caption]
    assert erwartet in captions
    assert any("CC BY 4.0" in c for c in captions)
    assert not any("Diplomat" in c for c in captions)


def test_berufssuche_fallback_ohne_esco():
    at = AppTest.from_file(APP, default_timeout=120)
    at.query_params["beruf"] = "Drogist/in"
    at.run()
    at.switch_page("pages/4_Berufssuche.py")
    at.run()
    assert not at.exception
    assert any("Kein ESCO-Match" in c.value for c in at.caption)


def test_methodik_zeigt_match_qualitaet():
    at = _app()
    at.switch_page("pages/5_Methodik.py")
    at.run()
    df = pd.read_csv(SCORES)
    n = int((df["esco_match_qualitaet"] == "korrekt").sum())
    texte = " ".join(m.value for m in at.markdown)
    assert f"**korrekt** ({n})" in texte
    assert "Version 1.2.1" in texte and "CC BY 4.0" in texte
    assert "Haiku" not in texte
