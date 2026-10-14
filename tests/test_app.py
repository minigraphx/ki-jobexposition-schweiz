"""Streamlit-AppTest: alle Seiten laufen ohne Exception mit den versionierten Daten."""

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest

APP_DIR = Path(__file__).parent.parent / "src" / "app"
APP = str(APP_DIR / "app.py")
SEITEN = [
    "seiten/0_Startseite.py",
    "seiten/1_Treemap.py",
    "seiten/2_Matrix.py",
    "seiten/3_Branchen.py",
    "seiten/4_Berufssuche.py",
    "seiten/5_Methodik.py",
]
SCORES = Path(__file__).parent.parent / "data" / "processed" / "scores.csv"
ALTE_SPALTEN = ["score_ch", "score_gesamt", "beruf", "branche", "beschaeftigte_1000", "adaptabilitaet"]

sys.path.insert(0, str(APP_DIR))
import gemeinsam as g  # noqa: E402


def _scores() -> pd.DataFrame:
    return pd.read_csv(SCORES, dtype={"isco_code": str})


def _seite(seite: str, **params) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=120)
    for k, v in params.items():
        at.query_params[k] = v
    at.run()
    at.switch_page(seite)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _texte(at: AppTest) -> str:
    return " ".join([m.value for m in at.markdown] + [c.value for c in at.caption]
                    + [i.value for i in at.info] + [w.value for w in at.warning])


def _spec(at: AppTest) -> str:
    return " ".join(json.dumps(json.loads(c.proto.spec), ensure_ascii=False) for c in at.get("plotly_chart"))


@pytest.mark.parametrize("seite", SEITEN)
def test_seite_ohne_fehler(seite):
    at = _seite(seite)
    texte = _texte(at)
    assert "nan" not in texte.replace("Tsd.", "").split()
    for alt in ALTE_SPALTEN:          # keine alten Spaltennamen in sichtbaren Texten
        assert f"`{alt}`" not in texte


def test_startseite_kennzahlen():
    at = _seite("seiten/0_Startseite.py")
    df = _scores()
    texte = _texte(at)
    assert f"**{len(df)} Schweizer Berufe**" in texte
    assert "Claude Opus 5.5" in texte and "Gemini 4 Argon" in texte
    assert "noch nicht bewertet" not in texte
    metriken = {m.label: m.value for m in at.metric}
    assert metriken["Analysierte Berufe"] == str(len(df))
    assert metriken["Stark exponiert (Score > 6)"] == str(int((df["exposure"] > 6).sum()))
    # kritische Zone: exposure > 6 und adaptability höchstens im beschäftigungsgewichteten Median
    d = df[["adaptability", "employed_k"]].dropna().sort_values("adaptability", kind="mergesort")
    median = d.loc[d["employed_k"].cumsum() / d["employed_k"].sum() >= 0.5, "adaptability"].iloc[0]
    kritisch = df[(df["exposure"] > 6) & (df["adaptability"] <= median)]
    assert metriken["Kritische Zone"] == str(len(kritisch))
    w = df[df["exposure"] > 6]
    frauen = (w["women_pct"] * w["employed_k"]).sum() / w["employed_k"].sum()
    if not kritisch.empty:
        fk = (kritisch["women_pct"] * kritisch["employed_k"]).sum() / kritisch["employed_k"].sum()
        assert f"{fk:.0f} % der Erwerbstätigen in der kritischen Zone sind Frauen" in texte
    else:
        assert f"sind {frauen:.0f} % der Erwerbstätigen Frauen" in texte
        assert "kein Beruf in der kritischen Zone" in texte
    assert any("Claude Opus 5.5" in c.value and "Gemini 4 Argon" in c.value for c in at.caption)


@pytest.mark.parametrize("kennzahl", ["exposure", "time_savings", "physical_automation"])
def test_treemap_farbe_waehlbar(kennzahl):
    at = _seite("seiten/1_Treemap.py")
    at.sidebar.radio[0].set_value(kennzahl).run()
    assert not at.exception
    spec = _spec(at)
    assert g.LABELS[kennzahl] in spec and "Köche" in spec


def test_matrix_unsichere_markiert():
    at = _seite("seiten/2_Matrix.py")
    spec = json.loads(at.get("plotly_chart")[0].proto.spec)
    spuren = {t["name"]: t for t in spec["data"]}
    df = _scores()
    unsicher = spuren["Weniger sichere Bewertung (Modelle oder Wiederholungen weichen ab)"]
    assert unsicher["marker"]["symbol"] == "diamond" and len(unsicher["customdata"]) == int(df["uncertain"].sum())
    assert spuren["Bewertung übereinstimmend"]["marker"]["symbol"] == "circle"
    assert "Claude" in unsicher["hovertemplate"] and "Gemini" in unsicher["hovertemplate"]
    assert any("Weniger sicher:" in str(c) for c in unsicher["customdata"])
    at.radio[0].set_value("physical_automation").run()
    at.radio[1].set_value("Frauenanteil (%)").run()
    assert not at.exception
    assert "Physische Automatisierung" in _spec(at)


def test_branchen_gewichtet_und_heatmap():
    at = _seite("seiten/3_Branchen.py")
    charts = [json.loads(c.proto.spec) for c in at.get("plotly_chart")]
    assert len(charts) == 3
    df = _scores()
    fin = df[df["sector"] == "Finanzen"]
    erwartet = (fin["exposure"] * fin["employed_k"]).sum() / fin["employed_k"].sum()
    assert "Finanzen" in charts[0]["data"][0]["y"]
    tabellen = pd.concat([d.value for d in at.dataframe if "Ø Exposition" in d.value.columns])
    assert tabellen.set_index("Branche").loc["Finanzen", "Ø Exposition"].max() == pytest.approx(round(erwartet, 1))
    heat = charts[2]["data"][0]
    assert heat["type"] == "heatmap" and len(heat["y"]) == df["sector"].nunique()
    assert any("Grenzgänger" in c.value for c in at.caption)


def test_berufssuche_details_und_taetigkeiten():
    df = _scores().set_index("occupation")
    beruf = "Dipl. Pflegefachperson"
    at = _seite("seiten/4_Berufssuche.py", beruf=beruf)
    assert at.selectbox[0].value == beruf
    metriken = {m.label: m.value for m in at.metric}
    assert metriken["KI-Exposition"] == f"{df.at[beruf, 'exposure']:.1f} / 10"
    assert metriken["Zeitrahmen"] == df.at[beruf, "timeframe"]
    assert metriken["Physische Automatisierung"].endswith("/ 10")
    pfad = g.bewertungsdatei(df.at[beruf, "text_source"], df.at[beruf, "isco_code"], beruf)
    taetigkeiten = json.loads(pfad.read_text(encoding="utf-8"))["bewertung"]["taetigkeiten"]
    tab = next(d.value for d in at.dataframe if "Tätigkeit" in d.value.columns)
    assert len(tab) == len(taetigkeiten) and tab["Anteil"].sum() == 100
    assert set(tab["Stufe"]) <= {"E0", "E1", "E2"}
    texte = _texte(at)
    assert df.at[beruf, "main_risk"] in texte
    assert (f"Claude Opus 5.5 gibt {df.at[beruf, 'exposure_claude']:.1f} Punkte, "
            f"Gemini 4 Argon {df.at[beruf, 'exposure_gemini']:.1f} Punkte") in texte
    assert "Opus 5.5 " + f"{df.at[beruf, 'exposure_claude']:.1f}" not in texte   # keine Zahl direkt nach der Modellnummer
    assert "Radar" not in texte


def test_berufssuche_unsicher_zeigt_beide_modelle():
    df = _scores()
    r = df[df["uncertain"] & (df["delta_provider"] > 1.0)].iloc[0]     # Grund: Modelle uneinig
    at = _seite("seiten/4_Berufssuche.py", beruf=r["occupation"])
    warnung = " ".join(w.value for w in at.warning)
    assert "Weniger sichere Bewertung" in warnung and f"Claude Opus 5.5 gibt {r['exposure_claude']:.1f} Punkte" in warnung
    assert f"{r['exposure_claude']:.1f}" in warnung and f"{r['exposure_gemini']:.1f}" in warnung
    assert "> 1" not in warnung                                  # kein technischer Grund-Text


def test_berufssuche_findet_synonym_im_permalink():
    """Alter Permalink mit bisherigem CH-Titel → zusammengelegter Eintrag."""
    at = _seite("seiten/4_Berufssuche.py", beruf="Koch/Köchin EFZ")
    assert at.selectbox[0].value == "Köche"
    assert any("Koch/Köchin EFZ" in c.value and "als Ganzes bewertet" in c.value for c in at.caption)


def test_berufssuche_label_enthaelt_synonyme():
    at = _seite("seiten/4_Berufssuche.py")
    assert any("Verkäufer in Handelsgeschäften" in o and "Detailhandelsfachmann/-frau EFZ" in o
               for o in at.selectbox[0].options)


@pytest.mark.parametrize("beruf, erwartet", [
    ("Dipl. Pflegefachperson", "Match-Qualität: korrekt (ESCO-ISCO 2221)"),
    ("Fachperson Gesundheit EFZ (FaGe)", "Match-Qualität: plausibel (ESCO-ISCO 5321)"),
])
def test_berufssuche_zeigt_match_qualitaet(beruf, erwartet):
    at = _seite("seiten/4_Berufssuche.py", beruf=beruf)
    captions = [c.value for c in at.caption]
    assert erwartet in captions
    assert any("CC BY 4.0" in c for c in captions)
    assert not any("Diplomat" in c for c in captions)


def test_berufssuche_fallback_ohne_esco():
    at = _seite("seiten/4_Berufssuche.py", beruf="Drogist/in")
    assert any("Kein ESCO-Match" in c.value for c in at.caption)


def test_methodik_abdeckung_und_match_qualitaet():
    at = _seite("seiten/5_Methodik.py")
    df = _scores()
    texte = _texte(at)
    abdeckung = f"{df['employed_k'].sum() / 4583.7 * 100:.1f} %".replace(".", ",")
    assert f"**{len(df)} Berufe**" in texte and abdeckung in texte
    assert f"**korrekt** ({int((df['esco_match_quality'] == 'korrekt').sum())})" in texte
    assert "Version 1.2.1" in texte and "CC BY 4.0" in texte and "Haiku" not in texte
    assert f"**{int(df['uncertain'].sum())} von {len(df)} Berufen**" in texte
    for wort in ("E0", "E1", "E2", "ζ", "dritter", "KMU-Adoptions-Faktor", "Keine Zuschläge",
                 "Betriebszählung 2008", "qualitative Einschätzung"):
        assert wort in texte, wort


def test_methodik_validierung_zur_laufzeit():
    at = _seite("seiten/5_Methodik.py")
    df = _scores()
    bench = pd.read_csv(g.BENCHMARK_PATH, dtype={"isco_code": str})
    je_code = df.groupby("isco_code").apply(
        lambda d: (d["exposure"] * d["employed_k"]).sum() / d["employed_k"].sum()).rename("exposure").reset_index()
    m = je_code.merge(bench, on="isco_code")
    texte = _texte(at)
    for spalte in ("ilo25_mean", "eloundou_gpt4_beta", "aei_observed_exposure"):
        rho, n = g.spearman(m["exposure"], m[spalte])
        assert f"**{rho:.2f}** | {n} |" in texte, spalte
    assert "keine unabhängige Prüfung" in texte and "Reihenfolge" in texte
    assert "Einen Schweizer Benchmark gibt es nicht" in texte
    rho_alt, _ = g.spearman(df["legacy_score"], df["exposure"])
    assert f"Spearman ρ = {rho_alt:.2f}" in texte


def test_methodik_zeigt_lohnverhaeltnisse():
    """Tabelle der Verhältniszahlen Gruppe 22: Werte aus scores.csv, Band, Unsicher-Markierung."""
    at = _seite("seiten/5_Methodik.py")
    tab = next(d.value for d in at.dataframe if "Faktor" in d.value.columns).set_index("ISCO")
    df = _scores().set_index("isco_code")
    for code in ("2211", "2212", "2221"):
        assert tab.loc[code, "Lohn (CHF/Jahr)"] == f"{df.loc[code, 'wage_median_chf']:,}".replace(",", "'")
    assert tab.loc["2212", "Band (CHF/Jahr)"] != "–"
    assert set(tab.index[tab["Unsicher"] == "ja"]) == {"2261", "2262"}
    assert "Salarium" in tab.loc["2262", "Lohn (CHF/Jahr)"]


# --------------------------------------------------------------------------- Hilfsmodul

def test_bewertungsdateien_vorhanden_und_slug_wie_rubrik():
    import task_rubrik as tr
    df = _scores()
    for r in df.itertuples():
        assert g.slug(r.occupation) == tr.slugify(r.occupation)
        pfad = g.bewertungsdatei(r.text_source, r.isco_code, r.occupation)
        assert pfad is not None and pfad.exists(), (r.occupation, r.text_source)
        d = json.loads(pfad.read_text(encoding="utf-8"))
        assert d["meta"]["status"] == "ok" and d["bewertung"]["beruf"] == r.occupation


def test_hilfsfunktionen():
    assert g.spearman(pd.Series([1, 2, 3, 4]), pd.Series([10, 20, 30, 40]))[0] == pytest.approx(1.0)
    assert g.spearman(pd.Series([1, 2]), pd.Series([2, 1]))[1] == 2
    assert g.tsd(1234567) == "1'234'567" and g.prozent(12.34, 1) == "12,3 %"
    assert g.quelle_lesbar("claude-cli/run2") == "Claude Opus 5.5, Lauf 2"
    assert g.bewertungsdatei("", "1111", "X") is None
