"""
Seite 4: Beruf-Detail-Suche mit URL-Permalink via st.query_params
"""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.title("🔍 Beruf nachschlagen")

DATA_PATH = Path(__file__).parent.parent.parent.parent / "data" / "processed" / "scores.csv"


@st.cache_data
def load_data() -> pd.DataFrame | None:
    if not DATA_PATH.exists():
        return None
    return pd.read_csv(DATA_PATH)


df = load_data()

if df is None:
    st.warning("Noch keine Score-Daten vorhanden.")
    st.stop()

# ── Lookup: ESCO-Titel und Synonyme pro Beruf ───────────────────────────────────
def _text(wert) -> str:
    t = str(wert or "").strip()
    return "" if t == "nan" else t


_esco_map: dict[str, str] = {}
_syn_map: dict[str, list[str]] = {}
for _, _row in df.iterrows():
    _t = _text(_row.get("esco_titel", ""))
    if _t:
        _esco_map[_row["beruf"]] = _t
    _s = [s.strip() for s in _text(_row.get("synonyme", "")).split(";") if s.strip()]
    if _s:
        _syn_map[_row["beruf"]] = _s

# Synonym (bisheriger CH-Titel eines zusammengelegten Berufs) → Eintrag
_synonym_zu_beruf = {s.lower(): b for b, syn in _syn_map.items() for s in syn}


def _label(beruf: str) -> str:
    teile = [beruf] + _syn_map.get(beruf, [])
    esco = _esco_map.get(beruf, "")
    if esco and esco.lower() not in {t.lower() for t in teile}:
        teile.append(esco)
    return "  ·  ".join(teile)


# ── URL-State / Permalink ───────────────────────────────────────────────────────
berufe_sorted = sorted(df["beruf"].unique())
url_beruf = st.query_params.get("beruf", "")
if url_beruf not in berufe_sorted:  # alte Permalinks: bisherige CH-Titel als Synonym
    url_beruf = _synonym_zu_beruf.get(url_beruf.lower(), url_beruf)
default_index = berufe_sorted.index(url_beruf) if url_beruf in berufe_sorted else 0

beruf = st.selectbox(
    "Beruf auswählen  (Schweizer Titel, Synonym oder ESCO-Bezeichnung)",
    berufe_sorted,
    index=default_index,
    format_func=_label,
)
st.query_params["beruf"] = beruf

# ── Daten für ausgewählten Beruf ────────────────────────────────────────────────
row = df[df["beruf"] == beruf].iloc[0]

if beruf in _syn_map:
    st.caption("Umfasst auch: " + " · ".join(_syn_map[beruf]))
if str(row.get("scores_gemittelt", "")).strip().lower() == "true":
    st.warning(
        "**Zusammengelegter Eintrag:** Die Strukturerhebung weist diese Berufe nicht getrennt aus. "
        "Die Scores sind vorläufig das beschäftigungsgewichtete Mittel der bisherigen Einzelberufe "
        f"({', '.join(_syn_map.get(beruf, []))}); Texte stammen vom grössten Teilberuf. "
        "Eine Neubewertung des Gesamteintrags folgt.",
        icon="⚠️",
    )

# ── Metriken ────────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
with col1:
    score = row.get("score_ch", row.get("score_gesamt", 0))
    st.metric("KI-Expositions-Score", f"{score:.1f} / 10")
with col2:
    st.metric("Beschäftigte CH", f"{row.get('beschaeftigte_1000', '?')} Tsd.",
              help="BFS Strukturerhebung 2024, Erwerbstätige der CH-ISCO-19-Berufsgattung "
                   f"{row.get('isco_code', '')} (bzw. der zugeordneten Berufsarten)")
with col3:
    st.metric("Zeitrahmen", row.get("zeitrahmen", "–"))

st.divider()

# ── Radar-Chart der Teilscores ──────────────────────────────────────────────────
radar_cols = ["score_digital", "score_wiederholbarkeit", "score_physisch",
              "score_kreativitaet", "score_sozial"]
if all(c in row.index for c in radar_cols):
    kategorien = ["Digital", "Wiederholbarkeit", "Physisch (inv.)", "Kreativität (inv.)", "Sozial (inv.)"]
    werte = [
        row["score_digital"],
        row["score_wiederholbarkeit"],
        10 - row["score_physisch"],
        10 - row["score_kreativitaet"],
        10 - row["score_sozial"],
    ]
    fig = go.Figure(go.Scatterpolar(
        r=werte + [werte[0]],
        theta=kategorien + [kategorien[0]],
        fill="toself",
        fillcolor="rgba(231,76,60,0.2)",
        line=dict(color="#e74c3c"),
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(range=[0, 10])),
        title="Expositions-Profil",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)

st.markdown(f"**Hauptrisiko:** {row.get('haupt_risiko', '–')}")
st.markdown(f"**Begründung:** {row.get('begruendung', '–')}")

# ── Scoring-Grundlage ───────────────────────────────────────────────────────────
st.divider()

esco_uri = str(row.get("esco_uri", "") or "").strip()
esco_titel = str(row.get("esco_titel", "") or "").strip()
esco_desc = str(row.get("esco_beschreibung", "") or "").strip()

if esco_uri and esco_uri != "nan":
    lbl = f"ESCO-Beschreibung ({esco_titel})" if esco_titel and esco_titel != "nan" else "ESCO-Beschreibung"
    with st.expander(lbl):
        if esco_desc and esco_desc != "nan":
            st.caption(esco_desc)
        st.caption(f"ESCO URI: {esco_uri}")
        qual = str(row.get("esco_match_qualitaet", "") or "").strip()
        esco_isco = row.get("esco_isco_code", "")
        esco_isco = str(int(esco_isco)) if isinstance(esco_isco, float) and esco_isco == esco_isco \
            else str(esco_isco or "").strip()
        if qual and qual != "nan":
            st.caption(f"Match-Qualität: {qual}"
                       + (f" (ESCO-ISCO {esco_isco})" if esco_isco and esco_isco != "nan" else ""))
        st.caption("Quelle: ESCO v1.2.1 © Europäische Union, CC BY 4.0; Beschreibung ggf. gekürzt/angepasst")
else:
    with st.expander("Scoring-Grundlage"):
        st.caption(
            "Kein ESCO-Match gefunden. Das Scoring basiert auf dem Berufstitel "
            "und einer KI-generierten Beschreibung."
        )
        if esco_desc and esco_desc != "nan":
            st.caption(esco_desc)

# ── Permalink ──────────────────────────────────────────────────────────────────
st.caption(
    f"🔗 Direktlink zu diesem Beruf: füge `?beruf={beruf}` an die URL an."
)
