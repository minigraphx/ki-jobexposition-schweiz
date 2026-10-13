"""
Startseite: KI-Jobexpositions-Analyse Schweiz
"""

from pathlib import Path

import pandas as pd
import streamlit as st

DATA_PATH = Path(__file__).parent.parent.parent.parent / "data" / "processed" / "scores.csv"


@st.cache_data
def load_data() -> pd.DataFrame | None:
    if not DATA_PATH.exists():
        return None
    return pd.read_csv(DATA_PATH)


df = load_data()
offen = None
if df is not None:
    # Neu aufgenommene Berufe ohne Exposure-Bewertung zählen in den Kennzahlen nicht mit
    offen = df[df["score_ch"].isna()]
    df = df[df["score_ch"].notna()]
n_text = f"{len(df)}" if df is not None else "rund 180"
offen_text = ""
if offen is not None and not offen.empty:
    offen_text = (f" Weitere {len(offen)} Berufe ({offen['beschaeftigte_1000'].sum():,.0f} Tsd. "
                  "Erwerbstätige) sind neu erfasst und noch nicht bewertet.")

st.title("KI & Jobmarkt Schweiz")
st.subheader("Welche Berufe verändert die künstliche Intelligenz am stärksten?")

st.markdown(f"""
Andrej Karpathy — Mitgründer von OpenAI — hat im März 2026 eine Analyse veröffentlicht,
die zeigt, wie stark 342 US-Berufe durch KI automatisierbar sind. Die Methodik: Berufsbeschreibungen
in ein Sprachmodell einspeisen, fünf Kriterien bewerten, Score 0–10 berechnen.

**Diese App überträgt diesen Ansatz auf die Schweiz.** Sie zeigt für {n_text} Schweizer Berufe —
basierend auf amtlichen BFS-Daten (Strukturerhebung 2024) — wie stark jede Berufsgruppe von
KI-Automatisierung betroffen sein könnte.{offen_text} Ergänzt wird die reine Exposition durch eine zweite
Dimension: die **Anpassungsfähigkeit** der Berufsangehörigen. Denn ob ein exponierter Beruf
verschwindet oder sich wandelt, hängt massgeblich davon ab, wie gut sich Betroffene neu
orientieren können.
""")

st.info(
    "**Wichtig:** Hohe KI-Exposition bedeutet nicht automatisch Jobverlust. "
    "Viele Berufe werden sich transformieren, nicht verschwinden. "
    "Die Scores sind Einschätzungen eines Sprachmodells — keine Prognosen. "
    "Was bisher tatsächlich beobachtet wird (in der Schweiz u. a. mehr Arbeitslose in stark "
    "exponierten Berufen, weniger Einstiegsstellen), fasst die Seite «Methodik & Quellen» zusammen.",
    icon="ℹ️",
)

st.divider()

# Kennzahlen
if df is not None:
    col1, col2, col3, col4 = st.columns(4)
    n_berufe = len(df)
    n_hoch = int((df["score_ch"] > 6).sum())
    n_kritisch = int(((df["score_ch"] > 6) & (df["adaptabilitaet"] < 5)).sum())
    beschaeftigte_hoch = df.loc[df["score_ch"] > 6, "beschaeftigte_1000"].sum()

    # Frauen in kritischer Zone (gewichtet nach Beschäftigtenzahl)
    kritisch_df = df[(df["score_ch"] > 6) & (df["adaptabilitaet"] < 5)]
    if not kritisch_df.empty and "frauen_pct" in df.columns:
        frauen_gewichtet = (
            (kritisch_df["frauen_pct"] / 100 * kritisch_df["beschaeftigte_1000"]).sum()
            / kritisch_df["beschaeftigte_1000"].sum() * 100
        )
    else:
        frauen_gewichtet = None

    with col1:
        st.metric("Analysierte Berufe", n_berufe)
    with col2:
        st.metric("Stark exponiert (Score > 6)", n_hoch)
    with col3:
        st.metric("Kritische Zone", n_kritisch, help="Hoch exponiert UND schwer anpassbar")
    with col4:
        st.metric("Betroffene Beschäftigte", f"{beschaeftigte_hoch:,.0f} Tsd.",
                  help="Beschäftigte in Berufen mit Score > 6")

    # Frauen-Highlight (Brookings-Befund)
    if frauen_gewichtet is not None:
        st.info(
            f"👩 **{frauen_gewichtet:.0f} % der Beschäftigten in der kritischen Zone sind Frauen** — "
            "also in Berufen mit hoher KI-Exposition *und* geringer Anpassungsfähigkeit. "
            "Das bestätigt den Befund der Brookings/GovAI-Studie (2024), die für den US-Markt 86 % ausweist — "
            "Frauen tragen also in beiden Arbeitsmärkten überproportional das KI-Automatisierungsrisiko.",
            icon=None,
        )

st.divider()

# Navigation
st.markdown("### Erkunden")

col_a, col_b = st.columns(2)

with col_a:
    st.markdown(f"""
    **🗺️ Treemap**
    Alle {n_text} Berufe auf einen Blick. Grösse = Beschäftigtenzahl,
    Farbe = KI-Expositions-Score. Sofort sichtbar: Wo konzentriert sich das Risiko?
    """)
    st.page_link("pages/1_Treemap.py", label="→ Treemap öffnen")

    st.markdown("""
    **🏭 Branchenanalyse**
    Welche Branchen sind am stärksten exponiert?
    Balkendiagramm + Konvergenz-Heatmap nach Amy Webb.
    """)
    st.page_link("pages/3_Branchen.py", label="→ Branchenanalyse öffnen")

with col_b:
    st.markdown("""
    **📊 Matrix: Exposition × Anpassungsfähigkeit**
    Die entscheidende Frage: Wer ist stark exponiert *und* schwer anpassbar?
    Die rote Zone oben links zeigt den grössten Handlungsbedarf.
    """)
    st.page_link("pages/2_Matrix.py", label="→ Matrix öffnen")

    st.markdown("""
    **🔍 Beruf nachschlagen**
    Gib einen Beruf ein und sieh den vollständigen Score,
    die KI-Begründung und den Vergleich mit ähnlichen Berufen.
    """)
    st.page_link("pages/4_Berufssuche.py", label="→ Berufssuche öffnen")

st.divider()
st.caption("Datenquellen: BFS Strukturerhebung (SE) 2024, ESCO v1.2.1 (© EU, CC BY 4.0), BFS LSE 2024 · Scoring: Claude Sonnet (Anthropic) · Methodik: Karpathy (2026), Brookings Institution")
st.page_link("pages/5_Methodik.py", label="📖 Methodik & Quellen im Detail")
