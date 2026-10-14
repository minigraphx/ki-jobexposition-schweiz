"""
Seite 1: Treemap aller Schweizer Berufe.
Grösse = Erwerbstätige, Farbe = wählbare Kennzahl (KI-Exposition, Zeitersparnis, physische Automatisierung)
"""

import sys
from datetime import date
from pathlib import Path

import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import gemeinsam as g  # noqa: E402

st.title("🗺️ KI-Exposition: Alle Schweizer Berufe")

df = g.lade_scores()
if df is None:
    st.warning("Noch keine Score-Daten vorhanden. Bitte zuerst die aufgabenbasierte Bewertung übernehmen.")
    st.code("python src/scoring/apply_task_scores.py", language="bash")
    st.stop()

KENNZAHLEN = ["exposure", "time_savings", "physical_automation"]

# ── Sidebar Filter ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filter")
    kennzahl = st.radio("Farbe nach", KENNZAHLEN, format_func=g.LABELS.get,
                        help="Alle drei Kennzahlen auf der Skala 0–10 (Anteil der Arbeitszeit × 10).")

    branchen = ["Alle"] + sorted(df["sector"].dropna().unique().tolist())
    selected_branche = st.selectbox("Branche", branchen)

    qualifikationen = sorted(df["qualification"].dropna().unique().tolist())
    selected_qual = st.multiselect("Qualifikation", qualifikationen, default=qualifikationen,
                                   help="Leer lassen = alle anzeigen")

    frauen_min, frauen_max = st.slider("Frauenanteil (%)", min_value=0, max_value=100, value=(0, 100), step=5)
    min_score = st.slider(f"Minimum {g.LABELS[kennzahl]}", 0.0, 10.0, 0.0, 0.5)

    st.divider()
    st.caption(f"{len(df)} Berufe bewertet")

# ── Filtern ────────────────────────────────────────────────────────────────────
filtered = df.copy()
if selected_branche != "Alle":
    filtered = filtered[filtered["sector"] == selected_branche]
if selected_qual:
    filtered = filtered[filtered["qualification"].isin(selected_qual)]
filtered = filtered[filtered["women_pct"].between(frauen_min, frauen_max) | filtered["women_pct"].isna()]
filtered = filtered[filtered[kennzahl] >= min_score]

if filtered.empty:
    st.warning("Keine Berufe entsprechen den gewählten Filtern.")
    st.stop()

st.caption(f"**{len(filtered)}** Berufe angezeigt · {g.tsd(filtered['employed_k'].sum())} Tsd. Erwerbstätige · "
           f"Ø {g.LABELS[kennzahl]} (beschäftigungsgewichtet): {g.gewichtet(filtered, kennzahl):.1f}")

# ── Treemap ────────────────────────────────────────────────────────────────────
WURZEL = "Alle Berufe"
fig = px.treemap(
    filtered,
    path=[px.Constant(WURZEL), "sector", "occupation"],
    values="employed_k",
    color=kennzahl,
    color_continuous_scale=g.SKALA_0_10,
    range_color=[0, 10],
    title=f"{g.LABELS[kennzahl]} der Schweizer Berufe (Grösse = Erwerbstätige, Farbe = {g.LABELS[kennzahl]})",
)


def _zeilen_gruppe(name: str, d) -> str:
    """Tooltip einer Branche bzw. aller Berufe: Mittelwert, Umfang, Frauenanteil."""
    frauen = g.gewichtet(d, "women_pct")
    return (f"<b>{name}</b><br>"
            f"Ø {g.LABELS[kennzahl]}: {g.gewichtet(d, kennzahl):.1f} von 10 (gewichtet nach Erwerbstätigen)<br>"
            f"{len(d)} Berufe · {g.tsd(d['employed_k'].sum() * 1000)} Erwerbstätige<br>"
            + (f"Frauenanteil: {frauen:.0f} %" if frauen == frauen else ""))


def _zeilen_beruf(z) -> str:
    """Tooltip eines Berufs in Alltagssprache."""
    teile = [f"<b>{z['occupation']}</b>", f"Branche: {z['sector']}",
             f"{g.LABELS[kennzahl]}: {z[kennzahl]:.1f} von 10"]
    if kennzahl != "exposure":
        teile.append(f"KI-Exposition: {z['exposure']:.1f} von 10")
    teile.append(f"Erwerbstätige: {g.tsd(z['employed_k'] * 1000)}")
    if z["women_pct"] == z["women_pct"]:
        teile.append(f"Frauenanteil: {z['women_pct']:.0f} %")
    teile.append(f"Ausbildung: {z['qualification']}")
    if z["uncertain"]:
        teile.append(f"Bewertung unsicher — Claude {z['exposure_claude']:.1f}, Gemini {z['exposure_gemini']:.1f}")
    return "<br>".join(teile)


# Tooltip je Knoten selbst bauen: die Standard-Tooltips zeigen technische Felder (labels=, parent=, id=)
nach_beruf = {(z["sector"], z["occupation"]): z for _, z in filtered.iterrows()}
texte = []
for label, parent in zip(fig.data[0].labels, fig.data[0].parents):
    if not parent:                                            # Wurzel
        texte.append(_zeilen_gruppe(WURZEL, filtered))
    elif parent == WURZEL:                                    # Branche
        texte.append(_zeilen_gruppe(label, filtered[filtered["sector"] == label]))
    else:                                                     # Beruf
        z = nach_beruf.get((parent[len(WURZEL) + 1:], label))
        texte.append(_zeilen_beruf(z) if z is not None else f"<b>{label}</b>")
fig.update_traces(customdata=texte, hovertemplate="%{customdata}<extra></extra>",
                  marker=dict(line=dict(width=1, color="#fcfcfb")), root_color="#f9f9f7")
fig.update_layout(height=720, margin=dict(t=60, l=8, r=8, b=8),
                  coloraxis_colorbar=dict(title=g.LABELS[kennzahl].replace(" ", "<br>")))
st.plotly_chart(fig, width="stretch")

# ── PNG-Export ─────────────────────────────────────────────────────────────────
try:
    img_bytes = fig.to_image(format="png", width=1400, height=900, scale=2)
    st.download_button(
        label="📥 Als PNG herunterladen",
        data=img_bytes,
        file_name=f"treemap_ki_schweiz_{kennzahl}_{date.today().strftime('%Y-%m')}.png",
        mime="image/png",
        help="Hochauflösendes PNG (1400×900px, Retina) für Artikel und Social Media",
    )
except Exception:
    st.caption("PNG-Export nicht verfügbar (kaleido nicht installiert).")

with st.expander("Tabelle der angezeigten Berufe"):
    tab = filtered.sort_values(kennzahl, ascending=False)[
        ["occupation", "sector", kennzahl, "employed_k", "women_pct"]].rename(columns={
            "occupation": "Beruf", "sector": "Branche", kennzahl: g.LABELS[kennzahl],
            "employed_k": "Erwerbstätige (Tsd.)", "women_pct": "Frauenanteil (%)"})
    st.dataframe(tab, hide_index=True, width="stretch")

st.caption(
    "Skala 0–10 = Anteil der Arbeitszeit × 10. **KI-Exposition:** Tätigkeiten, die generative KI um "
    "mindestens die Hälfte beschleunigen kann. **Zeitersparnis:** davon tatsächlich eingesparte Zeit. "
    "**Physische Automatisierung:** Tätigkeiten, die Robotik, Automaten oder Selbstbedienung ohne "
    "generative KI übernehmen können (separate Kennzahl, nicht im KI-Score). Grösse = Erwerbstätige der "
    "Berufsgattung bzw. der zugeordneten Berufsarten (BFS Strukturerhebung 2024) — jede Gattung zählt "
    "nur einmal. Bewertung: Claude Opus 5.5 und Gemini 4 Argon, Rubrik v2.2. Die Farbe einer Branche ist "
    "das beschäftigungsgewichtete Mittel ihrer Berufe."
)
