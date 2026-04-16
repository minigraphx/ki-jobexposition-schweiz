"""
Seite 2: Matrix – Exposition × Anpassungsfähigkeit (Brookings-Methode)
Kritischste Zone: oben links (hoch exponiert, schwer anpassbar)
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="Matrix", layout="wide")
st.title("📊 Exposition × Anpassungsfähigkeit")

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

st.markdown("""
Die Matrix zeigt zwei Dimensionen:
- **Y-Achse: KI-Exposition** (0 = sicher, 10 = stark exponiert)
- **X-Achse: Anpassungsfähigkeit** (0 = schwer anzupassen, 10 = sehr flexibel)

**Kritische Zone (rot):** Hoch exponiert + schwer anpassbar → höchstes Risiko
""")

fig = go.Figure()

# Quadranten-Hintergrund
fig.add_shape(type="rect", x0=0, y0=5, x1=5, y1=10,
              fillcolor="rgba(231,76,60,0.1)", line=dict(width=0))
fig.add_shape(type="rect", x0=5, y0=5, x1=10, y1=10,
              fillcolor="rgba(243,156,18,0.1)", line=dict(width=0))
fig.add_shape(type="rect", x0=0, y0=0, x1=5, y1=5,
              fillcolor="rgba(149,165,166,0.1)", line=dict(width=0))
fig.add_shape(type="rect", x0=5, y0=0, x1=10, y1=5,
              fillcolor="rgba(46,204,113,0.1)", line=dict(width=0))

# Quadranten-Labels
fig.add_annotation(x=2.5, y=9, text="KRITISCH", showarrow=False,
                   font=dict(color="rgba(231,76,60,0.6)", size=14, family="Arial Black"))
fig.add_annotation(x=7.5, y=9, text="TRANSFORMIEREND", showarrow=False,
                   font=dict(color="rgba(243,156,18,0.6)", size=12))
fig.add_annotation(x=2.5, y=1, text="STAGNIEREND", showarrow=False,
                   font=dict(color="rgba(149,165,166,0.6)", size=12))
fig.add_annotation(x=7.5, y=1, text="SICHER", showarrow=False,
                   font=dict(color="rgba(46,204,113,0.6)", size=14, family="Arial Black"))

# Datenpunkte
if "adaptabilitaet" in df.columns:
    fig.add_trace(go.Scatter(
        x=df["adaptabilitaet"],
        y=df["score_ch"],
        mode="markers+text",
        text=df["beruf"],
        textposition="top center",
        marker=dict(
            size=df["beschaeftigte_1000"].fillna(10) / 5,
            color=df["score_ch"],
            colorscale=["#2ecc71", "#f39c12", "#e74c3c"],
            showscale=True,
            colorbar=dict(title="KI-Score"),
        ),
        hovertemplate="<b>%{text}</b><br>Exposition: %{y:.1f}<br>Anpassung: %{x:.1f}<extra></extra>",
    ))
else:
    st.warning("Spalte 'adaptabilitaet' fehlt in scores.csv. Bitte adaptability_scorer.py ausführen.")

fig.update_layout(
    height=650,
    xaxis=dict(title="Anpassungsfähigkeit", range=[0, 10]),
    yaxis=dict(title="KI-Exposition", range=[0, 10]),
    showlegend=False,
)
st.plotly_chart(fig, use_container_width=True)
