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

# Seiten liegen in «seiten/», nicht «pages/»: Ein Ordner «pages/» neben app.py aktiviert Streamlits
# automatische Seitenerkennung; Direktlinks (z. B. /Berufssuche?beruf=…) zeigten dann deren
# Navigation («app», Dateinamen statt Titel) statt der hier definierten.
pages = st.navigation([
    st.Page("seiten/0_Startseite.py", title="Startseite", icon="🏠"),
    st.Page("seiten/1_Treemap.py",    title="Treemap",    icon="🗺️"),
    st.Page("seiten/2_Matrix.py",     title="Matrix",     icon="📊"),
    st.Page("seiten/3_Branchen.py",   title="Branchen",   icon="🏭"),
    st.Page("seiten/4_Berufssuche.py", title="Berufssuche", icon="🔍"),
    st.Page("seiten/5_Methodik.py",   title="Methodik & Quellen", icon="📖"),
])
pages.run()
