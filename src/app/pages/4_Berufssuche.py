"""
Seite 4: Beruf-Detail-Suche
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="Berufssuche", layout="wide")
st.title("🔍 Beruf nachschlagen")

DATA_PATH = Path(__file__).parent.parent.parent.parent / "data" / "processed" / "scores.csv"


@st.cache_data
def load_data():
    if not DATA_PATH.exists():
        return None
    return pd.read_csv(DATA_PATH)


df = load_data()

if df is None:
    st.warning("Noch keine Score-Daten vorhanden.")
    st.stop()

beruf = st.selectbox("Beruf auswählen", sorted(df["beruf"].unique()))
row = df[df["beruf"] == beruf].iloc[0]

col1, col2, col3 = st.columns(3)
with col1:
    score = row.get("score_ch", row.get("score_gesamt", 0))
    color = "normal" if score < 5 else ("off" if score > 7 else "normal")
    st.metric("KI-Expositions-Score", f"{score:.1f} / 10")
with col2:
    st.metric("Beschäftigte CH", f"{row.get('beschaeftigte_1000', '?')} Tsd.")
with col3:
    st.metric("Zeitrahmen", row.get("zeitrahmen", "–"))

st.divider()

# Radar-Chart der Teilscores
if all(c in row.index for c in ["score_digital", "score_wiederholbarkeit", "score_physisch",
                                  "score_kreativitaet", "score_sozial"]):
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
