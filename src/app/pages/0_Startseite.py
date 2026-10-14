"""
Startseite: KI-Jobexpositions-Analyse Schweiz
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import gemeinsam as g  # noqa: E402

df = g.lade_scores()
n_text = f"{len(df)}" if df is not None else "rund 190"

st.title("KI & Jobmarkt Schweiz")
st.subheader("Welche Berufe verändert die künstliche Intelligenz am stärksten?")

st.markdown(f"""
Diese App zeigt für **{n_text} Schweizer Berufe** — basierend auf amtlichen BFS-Daten
(Strukturerhebung 2024) —, wie stark generative KI ihre Arbeit verändern kann.

**So wird bewertet:** Für jeden Beruf werden zuerst 8–12 Kerntätigkeiten mit ihrem Anteil an der
Arbeitszeit bestimmt (aus der ESCO-Berufsbeschreibung und den ESCO-Kompetenzen). Dann wird jede
Tätigkeit einzeln beurteilt: Kann ein Sprachmodell — allein oder mit darauf aufbauender Software —
die Zeit für diese Tätigkeit bei gleicher Qualität **mindestens halbieren**? Das Vorgehen folgt
der aufgabenbasierten Methode von Eloundou et al. (*GPTs are GPTs*) und der ILO (Gmyrek et al.
2025). Zwei Sprachmodelle bewerten unabhängig voneinander nach derselben Rubrik:
**Claude Opus 5.5** (Anthropic, über das eigene Abo) und **Gemini 4 Argon** (Google), je in zwei
bis drei Läufen.

**Der KI-Expositions-Score (0–10)** ist der Anteil der Arbeitszeit in Tätigkeiten, die generative
KI so stark beschleunigen kann, mal zehn: Ein Score von 7 heisst, rund 70 % der Arbeitszeit
entfallen auf solche Tätigkeiten. Ergänzt wird die Exposition durch die **Anpassungsfähigkeit**
der Berufsangehörigen — denn ob ein exponierter Beruf schrumpft oder sich wandelt, hängt
massgeblich davon ab, wie gut sich Betroffene neu orientieren können.
""")

st.info(
    "**Wichtig:** Hohe KI-Exposition bedeutet nicht automatisch Jobverlust. "
    "Gemessen wird, was generative KI technisch beschleunigen *könnte* — nicht, ob Betriebe sie "
    "einsetzen. Die Scores sind Einschätzungen von Sprachmodellen nach einer festen Rubrik, keine "
    "Prognosen. Was bisher tatsächlich beobachtet wird (in der Schweiz u. a. mehr Arbeitslose in "
    "stark exponierten Berufen, weniger Einstiegsstellen), fasst die Seite «Methodik & Quellen» zusammen.",
    icon="ℹ️",
)

st.divider()

# ── Kennzahlen ─────────────────────────────────────────────────────────────────
if df is not None:
    hoch = df[df["exposure"] > g.SCHWELLE_EXPOSITION]
    schwelle = g.schwelle_anpassung(df)
    kritisch = g.kritische_zone(df, schwelle)
    spalten = st.columns(5)
    spalten[0].metric("Analysierte Berufe", len(df))
    spalten[1].metric("Ø KI-Exposition", f"{g.gewichtet(df, 'exposure'):.1f} / 10",
                      help="Mittel über alle Erwerbstätigen (beschäftigungsgewichtet). " + g.HILFE["exposure"])
    spalten[2].metric("Stark exponiert (Score > 6)", len(hoch),
                      help="Berufe, in denen mehr als 60 % der Arbeitszeit auf exponierte Tätigkeiten entfallen")
    spalten[3].metric("Erwerbstätige (Score > 6)", f"{g.tsd(hoch['employed_k'].sum())} Tsd.",
                      help=f"Anteil an allen erfassten Erwerbstätigen: "
                           f"{g.prozent(hoch['employed_k'].sum() / df['employed_k'].sum() * 100)}")
    spalten[4].metric("Kritische Zone", len(kritisch),
                      help=f"Score > 6 (stark exponiert) und Anpassungsfähigkeit höchstens {schwelle:.1f} — dem Median "
                           "aller Erwerbstätigen (nicht überdurchschnittlich anpassungsfähig)")

    # Frauen-Highlight (Brookings-Befund), neu berechnet
    frauen_hoch = g.gewichtet(hoch, "women_pct")
    frauen_alle = g.gewichtet(df, "women_pct")
    if not kritisch.empty:
        frauen_kritisch = g.gewichtet(kritisch, "women_pct")
        st.info(
            f"👩 **{frauen_kritisch:.0f} % der Erwerbstätigen in der kritischen Zone sind Frauen** — "
            "also in Berufen mit hoher KI-Exposition *und* geringer Anpassungsfähigkeit "
            f"({len(kritisch)} Berufe, {g.tsd(kritisch['employed_k'].sum())} Tsd. Erwerbstätige; über alle "
            f"erfassten Berufe: {frauen_alle:.0f} % Frauen). Die Brookings/GovAI-Studie (2024) weist für den "
            "US-Arbeitsmarkt 86 % aus (mit anderer Abgrenzung). Welche Berufe in die Zone fallen, hängt stark "
            "von den Schwellen ab — siehe «Methodik & Quellen».",
        )
    else:
        tiefste = hoch.nsmallest(1, "adaptability")
        tief_text = (f" Die tiefste Anpassungsfähigkeit unter ihnen hat «{tiefste['occupation'].iloc[0]}» "
                     f"mit {tiefste['adaptability'].iloc[0]:.1f}." if not tiefste.empty else "")
        if not hoch.empty and set(hoch["qualification"]) <= {"Tertiär", "Sekundär II"}:
            tief_text = (" Die stark exponierten Berufe verlangen alle eine Berufslehre oder einen "
                         "Hochschulabschluss." + tief_text)
        st.info(
            f"👩 **In den stark exponierten Berufen sind {frauen_hoch:.0f} % der Erwerbstätigen Frauen** "
            f"(alle erfassten Berufe: {frauen_alle:.0f} %). Frauen sind damit überdurchschnittlich "
            "exponiert — die Brookings/GovAI-Studie (2024) fand für den US-Markt sogar 86 % Frauen in "
            "der kritischen Zone (hoch exponiert *und* schwer anpassbar). In der Schweiz liegt nach "
            "dieser Bewertung **kein Beruf in der kritischen Zone** (Score > 6 und Anpassungsfähigkeit "
            f"höchstens im Median {schwelle:.1f}).{tief_text}",
        )

st.divider()

# ── Navigation ─────────────────────────────────────────────────────────────────
st.markdown("### Erkunden")

col_a, col_b = st.columns(2)

with col_a:
    st.markdown(f"""
    **🗺️ Treemap**
    Alle {n_text} Berufe auf einen Blick. Grösse = Erwerbstätige, Farbe = KI-Exposition,
    Zeitersparnis oder physische Automatisierung. Sofort sichtbar: Wo konzentriert sich die Exposition?
    """)
    st.page_link("pages/1_Treemap.py", label="→ Treemap öffnen")

    st.markdown("""
    **🏭 Branchenanalyse**
    Welche Branchen sind am stärksten exponiert, und wo treffen mehrere Automatisierungswellen
    zusammen? Branchenvergleich, Grenzgänger-Kontext und Konvergenz-Heatmap nach Amy Webb.
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
    Gib einen Beruf ein und sieh die bewerteten Tätigkeiten, die Werte beider Modelle,
    den Zeitrahmen und die Begründung.
    """)
    st.page_link("pages/4_Berufssuche.py", label="→ Berufssuche öffnen")

st.divider()
st.caption("Datenquellen: BFS Strukturerhebung (SE) 2024, BFS LSE 2024 und Salarium, BFS STATENT 2024, "
           "BFS Grenzgängerstatistik, ESCO v1.2.1 (© EU, CC BY 4.0) · Bewertung: Claude Opus 5.5 "
           "(Anthropic, Abo) und Gemini 4 Argon (Google), Rubrik v2.2 · Methodik: Eloundou et al. (2024), "
           "ILO/Gmyrek et al. (2025), Brookings Institution")
st.page_link("pages/5_Methodik.py", label="📖 Methodik & Quellen im Detail")
