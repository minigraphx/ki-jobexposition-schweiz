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

# ── Lookup: ESCO-Titel pro Beruf ────────────────────────────────────────────────
_esco_map: dict[str, str] = {}
for _, _row in df.iterrows():
    _t = str(_row.get("esco_titel", "") or "").strip()
    if _t and _t != "nan":
        _esco_map[_row["beruf"]] = _t


def _label(beruf: str) -> str:
    esco = _esco_map.get(beruf, "")
    if esco and esco.lower() != beruf.lower():
        return f"{beruf}  ·  {esco}"
    return beruf


# ── URL-State / Permalink ───────────────────────────────────────────────────────
berufe_sorted = sorted(df["beruf"].unique())
url_beruf = st.query_params.get("beruf", "")
default_index = berufe_sorted.index(url_beruf) if url_beruf in berufe_sorted else 0

beruf = st.selectbox(
    "Beruf auswählen  (Schweizer oder ESCO-Bezeichnung)",
    berufe_sorted,
    index=default_index,
    format_func=_label,
)
st.query_params["beruf"] = beruf

# ── Daten für ausgewählten Beruf ────────────────────────────────────────────────
row = df[df["beruf"] == beruf].iloc[0]

# ── Metriken ────────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
with col1:
    score = row.get("score_ch", row.get("score_gesamt", 0))
    st.metric("KI-Expositions-Score", f"{score:.1f} / 10")
with col2:
    st.metric("Beschäftigte CH", f"{row.get('beschaeftigte_1000', '?')} Tsd.")
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
