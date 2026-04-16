"""
KI-Jobexpositions-Analyse Schweiz — Streamlit App
"""

from pathlib import Path

import pandas as pd
import streamlit as st

DATA_PATH = Path(__file__).parent.parent.parent / "data" / "processed" / "scores.csv"

st.set_page_config(
    page_title="KI & Jobmarkt Schweiz",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data
def load_data() -> pd.DataFrame | None:
    if not DATA_PATH.exists():
        return None
    return pd.read_csv(DATA_PATH)


pages = st.navigation([
    st.Page("pages/0_Startseite.py", title="Startseite", icon="🏠"),
    st.Page("pages/1_Treemap.py",    title="Treemap",    icon="🗺️"),
    st.Page("pages/2_Matrix.py",     title="Matrix",     icon="📊"),
    st.Page("pages/3_Branchen.py",   title="Branchen",   icon="🏭"),
    st.Page("pages/4_Berufssuche.py", title="Berufssuche", icon="🔍"),
    st.Page("pages/5_Methodik.py",   title="Methodik & Quellen", icon="📖"),
])
pages.run()
