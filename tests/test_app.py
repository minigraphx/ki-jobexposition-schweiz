"""Streamlit-AppTest: alle Seiten laufen ohne Exception mit den versionierten Daten."""

import json
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


def _unbewertet() -> pd.DataFrame:
    df = pd.read_csv(SCORES)
    return df[df["score_ch"].isna()]


def test_startseite_zeigt_anzahl_berufe():
    at = _app()
    df = pd.read_csv(SCORES)
    n = int(df["score_ch"].notna().sum())  # nur bewertete Berufe
    texte = " ".join(m.value for m in at.markdown)
    assert f"für {n} Schweizer Berufe" in texte
    assert "204" not in texte
    assert next(m.value for m in at.metric if m.label == "Analysierte Berufe") == str(n)
    offen = _unbewertet()
    if not offen.empty:
        assert f"Weitere {len(offen)} Berufe" in texte and "noch nicht bewertet" in texte


# ---------------------------------------------------------------------------
# Neu aufgenommene Berufe ohne Exposure-Bewertung
# ---------------------------------------------------------------------------

def test_unbewertete_eintraege_vollstaendig():
    """Unbewertet = alle LLM-Felder leer, Hash leer; Stammdaten, ESCO und Lohn vorhanden."""
    df = pd.read_csv(SCORES, dtype=str, keep_default_na=False)
    offen = df[df["score_ch"] == ""]
    llm = ["score_gesamt", "score_digital", "score_wiederholbarkeit", "score_physisch",
           "score_kreativitaet", "score_sozial", "haupt_risiko", "zeitrahmen", "begruendung",
           "adaptabilitaet", "beschreibung_hash"]
    pflicht = ["beruf", "isco_code", "beschaeftigte_1000", "frauen_pct", "branche",
               "lohn_median_chf", "lohn_quelle", "qualifikation", "esco_beschreibung",
               "beschreibung_quelle", "esco_match_qualitaet", "delta_branche", "lohnklasse",
               "delta_lohn"]
    for _, r in offen.iterrows():
        assert (r[llm] == "").all(), r["beruf"]
        assert (r[pflicht] != "").all(), (r["beruf"], [c for c in pflicht if r[c] == ""])
        assert r["scores_gemittelt"] == "False"
    # bewertete Einträge haben alle Score-Felder
    bewertet = df[df["score_ch"] != ""]
    assert (bewertet[["score_gesamt", "adaptabilitaet"]] != "").all().all()


@pytest.mark.parametrize("seite", ["pages/1_Treemap.py", "pages/2_Matrix.py", "pages/3_Branchen.py"])
def test_diagramme_ohne_unbewertete(seite):
    offen = _unbewertet()
    if offen.empty:
        pytest.skip("alle Berufe bewertet")
    at = _app()
    at.switch_page(seite)
    at.run()
    assert not at.exception
    assert any(f"{len(offen)} neu aufgenommene Berufe" in c.value and "noch nicht bewertet" in c.value
               for c in at.caption)
    spec = " ".join(json.dumps(json.loads(c.proto.spec), ensure_ascii=False)
                    for c in at.get("plotly_chart"))
    assert spec and not any(b in spec for b in offen["beruf"])
    if seite != "pages/3_Branchen.py":  # Treemap/Matrix beschriften einzelne Berufe
        assert "Köche" in spec


def test_berufssuche_unbewertet():
    offen = _unbewertet()
    if offen.empty:
        pytest.skip("alle Berufe bewertet")
    beruf = offen.sort_values("beschaeftigte_1000").iloc[-1]["beruf"]
    at = AppTest.from_file(APP, default_timeout=120)
    at.query_params["beruf"] = beruf
    at.run()
    at.switch_page("pages/4_Berufssuche.py")
    at.run()
    assert not at.exception
    assert at.selectbox[0].value == beruf
    assert "noch nicht bewertet" in at.selectbox[0].format_func(beruf)
    assert any("Noch nicht bewertet" in i.value for i in at.info)
    metriken = {m.label: m.value for m in at.metric}
    assert metriken["KI-Expositions-Score"] == "–" and metriken["Zeitrahmen"] == "–"
    texte = " ".join([m.value for m in at.markdown] + list(metriken.values()))
    assert "nan" not in texte and "Hauptrisiko" not in texte
    assert not at.get("plotly_chart")  # kein Radar-Chart
    assert any("ESCO URI" in c.value for c in at.caption)  # Beschreibung bleibt sichtbar


def test_berufssuche_bewertet_unveraendert():
    at = AppTest.from_file(APP, default_timeout=120)
    at.query_params["beruf"] = "Dipl. Pflegefachperson"
    at.run()
    at.switch_page("pages/4_Berufssuche.py")
    at.run()
    assert not at.info or not any("Noch nicht bewertet" in i.value for i in at.info)
    assert next(m.value for m in at.metric if m.label == "KI-Expositions-Score").endswith("/ 10")
    assert at.get("plotly_chart")


def test_methodik_zeigt_abdeckung():
    at = _app()
    at.switch_page("pages/5_Methodik.py")
    at.run()
    df = pd.read_csv(SCORES)
    texte = " ".join(m.value for m in at.markdown)
    abdeckung = f"{df['beschaeftigte_1000'].sum() / 4583.7 * 100:.1f} %".replace(".", ",")
    assert f"**{len(df)} Berufe**" in texte and abdeckung in texte
    offen = _unbewertet()
    if not offen.empty:
        assert f"**{len(offen)} neu aufgenommene Berufe**" in texte


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


def test_methodik_zeigt_lohnverhaeltnisse():
    """Tabelle der Verhältniszahlen Gruppe 22: Werte aus scores.csv, Band, Unsicher-Markierung."""
    at = _app()
    at.switch_page("pages/5_Methodik.py")
    at.run()
    assert not at.exception
    tab = next(d.value for d in at.dataframe if "Faktor" in d.value.columns).set_index("ISCO")
    df = pd.read_csv(SCORES, dtype={"isco_code": str}).set_index("isco_code")
    for code in ("2211", "2212", "2221"):
        assert tab.loc[code, "Lohn (CHF/Jahr)"] == f"{df.loc[code, 'lohn_median_chf']:,}".replace(",", "'")
    assert tab.loc["2212", "Band (CHF/Jahr)"] != "–"
    assert set(tab.index[tab["Unsicher"] == "ja"]) == {"2261", "2262"}
    assert "Salarium" in tab.loc["2262", "Lohn (CHF/Jahr)"]
