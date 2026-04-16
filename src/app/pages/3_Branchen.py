"""
Seite 3: Branchenanalyse – echte Scores + Webb-Konvergenz-Logik für CH-Branchen
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.title("🏭 Branchenanalyse Schweiz")

DATA_PATH = Path(__file__).parent.parent.parent.parent / "data" / "processed" / "scores.csv"


@st.cache_data
def load_data() -> pd.DataFrame | None:
    if not DATA_PATH.exists():
        return None
    return pd.read_csv(DATA_PATH)


df = load_data()

st.markdown("""
Welche Schweizer Branchen sind am stärksten von KI-Automatisierung betroffen?
Und welche werden durch mehrere technologische Wellen gleichzeitig getroffen?
Inspiriert von Amy Webbs *Future Today Institute Convergence Outlook 2026*.
""")

# --- Sektion 1: Echte Scores pro Branche ---
st.subheader("KI-Expositions-Score nach Branche")

if df is not None:
    branche_stats = (
        df.groupby("branche")
        .agg(
            score_mean=("score_ch", "mean"),
            score_min=("score_ch", "min"),
            score_max=("score_ch", "max"),
            berufe=("beruf", "count"),
            beschaeftigte=("beschaeftigte_1000", "sum"),
        )
        .reset_index()
        .sort_values("score_mean", ascending=True)
    )
    branche_stats["score_mean"] = branche_stats["score_mean"].round(2)

    fig_bar = px.bar(
        branche_stats,
        x="score_mean",
        y="branche",
        orientation="h",
        color="score_mean",
        color_continuous_scale=["#2ecc71", "#f39c12", "#e74c3c"],
        range_color=[0, 10],
        hover_data={"berufe": True, "beschaeftigte": ":.0f", "score_min": ":.1f", "score_max": ":.1f"},
        title="Ø KI-Expositions-Score pro Branche (Claude Sonnet 4.6 Scoring)",
        labels={"score_mean": "Ø Score", "branche": "Branche", "berufe": "Berufe", "beschaeftigte": "Beschäftigte (Tsd.)"},
    )
    fig_bar.update_layout(height=550, coloraxis_showscale=False)
    st.plotly_chart(fig_bar, use_container_width=True)

    # Top/Bottom Tabelle
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Meist exponierte Branchen**")
        top = branche_stats.nlargest(5, "score_mean")[["branche", "score_mean", "berufe"]]
        top.columns = ["Branche", "Ø Score", "Berufe"]
        st.dataframe(top, hide_index=True, use_container_width=True)
    with col2:
        st.markdown("**Am wenigsten exponierte Branchen**")
        bot = branche_stats.nsmallest(5, "score_mean")[["branche", "score_mean", "berufe"]]
        bot.columns = ["Branche", "Ø Score", "Berufe"]
        st.dataframe(bot, hide_index=True, use_container_width=True)
else:
    st.warning("Noch keine Score-Daten vorhanden.")

st.divider()

# --- Sektion 2: Konvergenz-Heatmap (qualitativ, Webb-Methode) ---
st.subheader("Technologie-Konvergenz nach Branche")
st.markdown("Welche Branchen werden durch **mehrere Wellen gleichzeitig** getroffen? (Qualitative Einschätzung)")

konvergenz = pd.DataFrame({
    "Branche": [
        "Finanzen & Versicherungen", "ICT / Telekommunikation", "Öffentliche Verwaltung",
        "Gesundheit & Soziales", "Industrie (MEM/Pharma)", "Bildung",
        "Detailhandel", "Transport & Logistik", "Recht & Beratung",
    ],
    "Generative KI": [5, 4, 3, 3, 3, 4, 3, 2, 5],
    "Prozessautomatisierung": [5, 4, 4, 3, 5, 2, 4, 4, 4],
    "Datenanalyse": [5, 4, 3, 4, 4, 3, 3, 3, 4],
    "Robotik": [1, 1, 1, 2, 5, 1, 3, 4, 1],
    "Autonome Systeme": [1, 2, 1, 2, 3, 1, 2, 5, 1],
})
tech_cols = ["Generative KI", "Prozessautomatisierung", "Datenanalyse", "Robotik", "Autonome Systeme"]
konvergenz["Gesamt"] = konvergenz[tech_cols].sum(axis=1)
konvergenz = konvergenz.sort_values("Gesamt", ascending=True)

fig_heat = go.Figure(go.Heatmap(
    z=konvergenz[tech_cols].values,
    x=tech_cols,
    y=konvergenz["Branche"].tolist(),
    colorscale="RdYlGn_r",
    zmin=1,
    zmax=5,
    text=konvergenz[tech_cols].values,
    texttemplate="%{text}",
    showscale=True,
    colorbar=dict(title="Intensität<br>(1–5)"),
))
fig_heat.update_layout(
    height=450,
    title="Konvergenz-Heatmap: Branchen × Technologiewellen",
    xaxis_title="Technologiewelle",
    yaxis_title="Branche",
)
st.plotly_chart(fig_heat, use_container_width=True)
st.caption("Intensität: 1 = kaum betroffen, 5 = stark betroffen. Qualitative Einschätzung nach Webb-Methode.")
