"""
Streamlit App: KI-Jobexpositions-Analyse Schweiz
"""

from pathlib import Path

import pandas as pd
import streamlit as st

DATA_PATH = Path(__file__).parent.parent.parent / "data" / "processed" / "scores.csv"

st.set_page_config(
    page_title="KI & Jobmarkt Schweiz",
    page_icon="🇨🇭",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data
def load_data() -> pd.DataFrame | None:
    if not DATA_PATH.exists():
        return None
    return pd.read_csv(DATA_PATH)


# Sidebar
st.sidebar.title("KI & Jobmarkt Schweiz")
st.sidebar.caption("Welche Berufe trifft der KI-Sturm zuerst?")
st.sidebar.divider()
st.sidebar.info(
    "Diese Analyse zeigt den KI-Expositions-Score für ~150 Schweizer Berufe, "
    "basierend auf der Methodik von Andrej Karpathy (2024), angepasst für den CH-Kontext."
)

# Hauptseite
st.title("🇨🇭 KI-Jobexposition Schweiz")
st.subheader("Welche Berufe trifft der KI-Sturm zuerst?")

st.markdown("""
Diese interaktive Analyse zeigt, welche Schweizer Berufe am stärksten von KI-Automatisierung
betroffen sein könnten – und welche Branchen durch mehrere technologische Wellen gleichzeitig
getroffen werden.

**Wichtiger Hinweis:** Hohe Exposition bedeutet nicht automatisch Jobverlust.
Die Transformation läuft graduell, und viele Berufe werden sich wandeln statt verschwinden.
""")

df = load_data()

col1, col2, col3 = st.columns(3)
if df is not None:
    n_berufe = len(df)
    n_hoch = int((df["score_ch"] > 7).sum())
    beschaeftigte_hoch = df.loc[df["score_ch"] > 7, "beschaeftigte_1000"].sum()
    with col1:
        st.metric("Analysierte Berufe", n_berufe)
    with col2:
        st.metric("Stark exponiert (Score > 7)", n_hoch)
    with col3:
        st.metric("Betroffene Beschäftigte", f"{beschaeftigte_hoch:,.0f} Tsd.")
else:
    with col1:
        st.metric("Analysierte Berufe", "–", help="Wird geladen sobald Scoring abgeschlossen")
    with col2:
        st.metric("Stark exponiert (Score > 7)", "–")
    with col3:
        st.metric("Betroffene Beschäftigte", "–")

st.divider()

if df is None:
    st.info("Scoring noch nicht ausgeführt. → `python src/scoring/generate_demo_scores.py`")

st.markdown("### Navigiere zu:")
st.page_link("pages/1_Treemap.py", label="Treemap: Alle Berufe nach Score", icon="🗺️")
st.page_link("pages/2_Matrix.py", label="Matrix: Exposition × Anpassungsfähigkeit", icon="📊")
st.page_link("pages/3_Branchen.py", label="Branchenanalyse", icon="🏭")
st.page_link("pages/4_Berufssuche.py", label="Beruf nachschlagen", icon="🔍")
st.page_link("pages/5_Methodik.py", label="Methodik & Quellen", icon="📖")
