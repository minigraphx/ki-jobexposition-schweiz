"""
KI-Jobexpositions-Analyse Schweiz — Streamlit App
"""

import streamlit as st

st.set_page_config(
    page_title="KI & Jobmarkt Schweiz",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

pages = st.navigation([
    st.Page("pages/0_Startseite.py", title="Startseite", icon="🏠"),
    st.Page("pages/1_Treemap.py",    title="Treemap",    icon="🗺️"),
    st.Page("pages/2_Matrix.py",     title="Matrix",     icon="📊"),
    st.Page("pages/3_Branchen.py",   title="Branchen",   icon="🏭"),
    st.Page("pages/4_Berufssuche.py", title="Berufssuche", icon="🔍"),
    st.Page("pages/5_Methodik.py",   title="Methodik & Quellen", icon="📖"),
])
pages.run()
