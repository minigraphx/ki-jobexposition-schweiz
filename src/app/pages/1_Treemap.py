"""
Seite 1: Treemap aller Schweizer Berufe nach KI-Expositions-Score.
Grösse = Beschäftigtenzahl, Farbe = Score (grün→rot)
"""

import pandas as pd
import plotly.express as px
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="Treemap", layout="wide")
st.title("🗺️ KI-Exposition: Alle Schweizer Berufe")

DATA_PATH = Path(__file__).parent.parent.parent.parent / "data" / "processed" / "scores.csv"


@st.cache_data
def load_data():
    if not DATA_PATH.exists():
        return None
    return pd.read_csv(DATA_PATH)


df = load_data()

if df is None:
    st.warning("Noch keine Score-Daten vorhanden. Bitte zuerst das Scoring ausführen.")
    st.code("python src/scoring/exposure_scorer.py", language="bash")
    st.stop()

# Filter
with st.sidebar:
    st.header("Filter")
    branchen = ["Alle"] + sorted(df["branche"].dropna().unique().tolist())
    selected_branche = st.selectbox("Branche", branchen)
    min_score = st.slider("Minimaler Score", 0.0, 10.0, 0.0, 0.5)

filtered = df.copy()
if selected_branche != "Alle":
    filtered = filtered[filtered["branche"] == selected_branche]
filtered = filtered[filtered["score_ch"] >= min_score]

# Treemap
fig = px.treemap(
    filtered,
    path=["branche", "beruf"],
    values="beschaeftigte_1000",
    color="score_ch",
    color_continuous_scale=["#2ecc71", "#f39c12", "#e74c3c"],
    range_color=[0, 10],
    hover_data={"score_ch": ":.1f", "beschaeftigte_1000": True},
    title="KI-Expositions-Score Schweizer Berufe (Grösse = Beschäftigte, Farbe = Score)",
    labels={"score_ch": "KI-Score", "beschaeftigte_1000": "Beschäftigte (Tsd.)"},
)
fig.update_layout(height=700, coloraxis_colorbar_title="KI-Score")
st.plotly_chart(fig, use_container_width=True)

st.caption("Score 0–10: 0 = kaum betroffen, 10 = stark exponiert. Quelle: BFS SAKE + Claude API Scoring.")
