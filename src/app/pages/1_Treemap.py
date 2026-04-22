"""
Seite 1: Treemap aller Schweizer Berufe nach KI-Expositions-Score.
Grösse = Beschäftigtenzahl, Farbe = Score (grün→rot)
"""

from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.title("🗺️ KI-Exposition: Alle Schweizer Berufe")

DATA_PATH = Path(__file__).parent.parent.parent.parent / "data" / "processed" / "scores.csv"


@st.cache_data
def load_data() -> pd.DataFrame | None:
    if not DATA_PATH.exists():
        return None
    return pd.read_csv(DATA_PATH)


df = load_data()

if df is None:
    st.warning("Noch keine Score-Daten vorhanden. Bitte zuerst das Scoring ausführen.")
    st.code("python src/scoring/exposure_scorer.py", language="bash")
    st.stop()

# ── Sidebar Filter ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filter")

    branchen = ["Alle"] + sorted(df["branche"].dropna().unique().tolist())
    selected_branche = st.selectbox("Branche", branchen)

    qualifikationen = sorted(df["qualifikation"].dropna().unique().tolist())
    selected_qual = st.multiselect(
        "Qualifikation",
        qualifikationen,
        default=qualifikationen,
        help="Leer lassen = alle anzeigen",
    )

    frauen_min, frauen_max = st.slider(
        "Frauenanteil (%)",
        min_value=0,
        max_value=100,
        value=(0, 100),
        step=5,
    )

    min_score = st.slider("Minimaler KI-Score", 0.0, 10.0, 0.0, 0.5)

    st.divider()
    st.caption(f"{len(df)} Berufe total")

# ── Filtern ────────────────────────────────────────────────────────────────────
filtered = df.copy()

if selected_branche != "Alle":
    filtered = filtered[filtered["branche"] == selected_branche]

if selected_qual:
    filtered = filtered[filtered["qualifikation"].isin(selected_qual)]

if "frauen_pct" in filtered.columns:
    filtered = filtered[
        (filtered["frauen_pct"] >= frauen_min) &
        (filtered["frauen_pct"] <= frauen_max)
    ]

filtered = filtered[filtered["score_ch"] >= min_score]

if filtered.empty:
    st.warning("Keine Berufe entsprechen den gewählten Filtern.")
    st.stop()

st.caption(f"**{len(filtered)}** Berufe angezeigt · {filtered['beschaeftigte_1000'].sum():,.0f} Tsd. Beschäftigte")

# ── Treemap ────────────────────────────────────────────────────────────────────
fig = px.treemap(
    filtered,
    path=["branche", "beruf"],
    values="beschaeftigte_1000",
    color="score_ch",
    color_continuous_scale=["#2ecc71", "#f39c12", "#e74c3c"],
    range_color=[0, 10],
    hover_data={
        "score_ch": ":.1f",
        "beschaeftigte_1000": ":.0f",
        "frauen_pct": ":.0f",
        "qualifikation": True,
    },
    title="KI-Expositions-Score Schweizer Berufe (Grösse = Beschäftigte, Farbe = Score)",
    labels={
        "score_ch": "KI-Score",
        "beschaeftigte_1000": "Beschäftigte (Tsd.)",
        "frauen_pct": "Frauenanteil %",
    },
)
fig.update_layout(height=700, coloraxis_colorbar_title="KI-Score")
st.plotly_chart(fig, use_container_width=True)

# ── PNG-Export ─────────────────────────────────────────────────────────────────
try:
    img_bytes = fig.to_image(format="png", width=1400, height=900, scale=2)
    filename = f"treemap_ki_schweiz_{date.today().strftime('%Y-%m')}.png"
    st.download_button(
        label="📥 Als PNG herunterladen",
        data=img_bytes,
        file_name=filename,
        mime="image/png",
        help="Hochauflösendes PNG (1400×900px, Retina) für Artikel und Social Media",
    )
except Exception:
    st.caption("PNG-Export nicht verfügbar (kaleido nicht installiert).")

st.caption("Score 0–10: 0 = kaum betroffen, 10 = stark exponiert. Quelle: BFS SAKE 2024 + Claude Sonnet Scoring.")
