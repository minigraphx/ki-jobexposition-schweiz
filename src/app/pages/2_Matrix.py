"""
Seite 2: Matrix – Exposition × Anpassungsfähigkeit (Brookings-Methode)
Kritischste Zone: oben links (hoch exponiert, schwer anpassbar)
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import gemeinsam as g  # noqa: E402

st.title("📊 Exposition × Anpassungsfähigkeit")

df = g.lade_scores()
if df is None:
    st.warning("Noch keine Score-Daten vorhanden.")
    st.stop()

X, YS = g.schwelle_anpassung(df), g.SCHWELLE_EXPOSITION
XG = X + 0.05     # Zonengrenze: halber Rundungsschritt rechts vom Median (Berufe genau auf dem Median gehören dazu)

st.markdown(f"""
Die Matrix zeigt zwei Dimensionen:
- **Y-Achse: KI-Exposition** (0 = kaum betroffen, 10 = fast die ganze Arbeitszeit exponiert) — wahlweise
  die **physische Automatisierung** (Robotik, Automaten, Selbstbedienung ohne generative KI)
- **X-Achse: Anpassungsfähigkeit** (0 = schwer anzupassen, 10 = sehr flexibel)

**Kritische Zone (rot, oben links):** Score > {YS:g} und Anpassungsfähigkeit höchstens {X:.1f}, dem Median
aller Erwerbstätigen (die Hälfte arbeitet in Berufen mit tieferem Wert) → höchstes Risiko.
Punktgrösse = Erwerbstätige.
""")

c1, c2 = st.columns(2)
y_spalte = c1.radio("Y-Achse:", ["exposure", "physical_automation"], format_func=g.LABELS.get, horizontal=True)
farb_modus = c2.radio("Farbe der Punkte:", ["Einheitlich", "Frauenanteil (%)"], horizontal=True)
y_label = g.LABELS[y_spalte]

fig = go.Figure()

# Quadranten-Hintergrund (dezent; nur die kritische Zone farbig)
for x0, x1, y0, y1, farbe in [(0, XG, YS, 10, "rgba(208,59,59,0.10)"), (XG, 10, YS, 10, "rgba(250,178,25,0.08)"),
                              (0, XG, 0, YS, "rgba(137,135,129,0.06)"), (XG, 10, 0, YS, "rgba(12,163,12,0.05)")]:
    fig.add_shape(type="rect", x0=x0, y0=y0, x1=x1, y1=y1, fillcolor=farbe, line=dict(width=0), layer="below")
for x, y, text, farbe, ausrichtung in [
        (0.15, 9.7, "KRITISCH", "rgba(208,59,59,0.9)", "left"),
        (9.85, 9.7, "TRANSFORMIEREND", "rgba(160,110,0,0.85)", "right"),
        (0.15, YS - 0.3, "STAGNIEREND", "rgba(82,81,78,0.75)", "left"),
        (9.85, YS - 0.3, "WENIG BETROFFEN", "rgba(0,99,0,0.8)", "right")]:
    fig.add_annotation(x=x, y=y, text=f"<b>{text}</b>", showarrow=False, xanchor=ausrichtung,
                       font=dict(color=farbe, size=12))

groesse = 6 + 3 * np.sqrt(df["employed_k"].fillna(1.0))   # Fläche ~ Erwerbstätige
symbole = {False: ("circle", "Bewertung übereinstimmend"),
           True: ("diamond", "Weniger sichere Bewertung (Modelle oder Wiederholungen weichen ab)")}
for unsicher, (symbol, name) in symbole.items():
    d = df[df["uncertain"] == unsicher]
    if d.empty:
        continue
    marker = dict(size=groesse[d.index], symbol=symbol, line=dict(width=1.5, color="#fcfcfb"), opacity=0.85)
    if farb_modus == "Frauenanteil (%)":
        marker.update(color=d["women_pct"], colorscale=g.DIVERGIEREND, cmin=0, cmax=100,
                      showscale=not unsicher, colorbar=dict(title="Frauen-<br>anteil (%)"))
    else:
        marker.update(color=g.SERIE[0] if not unsicher else g.SERIE[1])
    grund = pd.Series([("<br>Weniger sicher: " + "; ".join(g.unsicher_gruende(z))) if z["uncertain"] else ""
                       for _, z in d.iterrows()], index=d.index)
    fig.add_trace(go.Scatter(
        x=d["adaptability"], y=d[y_spalte], mode="markers", name=name, marker=marker,
        customdata=np.stack([d["occupation"], d["exposure_claude"], d["exposure_gemini"], d["employed_k"],
                             d["women_pct"].fillna(-1), grund, d["exposure"]], axis=-1),
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            f"{y_label}: %{{y:.1f}}<br>"
            "Anpassungsfähigkeit: %{x:.1f}<br>"
            "KI-Exposition: %{customdata[6]:.1f}<br>"
            f"{g.CLAUDE_NAME} gibt %{{customdata[1]:.1f}} Punkte, {g.GEMINI_NAME} %{{customdata[2]:.1f}} Punkte<br>"
            "Erwerbstätige: %{customdata[3]:.1f} Tsd. · Frauen: %{customdata[4]:.0f} %"
            "%{customdata[5]}<extra></extra>"
        ),
    ))

fig.update_layout(
    height=680,
    xaxis=dict(title="Anpassungsfähigkeit", range=[-0.3, 10.3], gridcolor="#e1e0d9", zeroline=False,
               tickvals=list(range(0, 11, 2))),
    yaxis=dict(title=y_label, range=[-0.5, 10.3], gridcolor="#e1e0d9", zeroline=False,
               tickvals=list(range(0, 11, 2))),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, itemsizing="constant"),
    hoverlabel=dict(align="left"),
    margin=dict(t=40),
)
st.plotly_chart(fig, width="stretch")

n_unsicher = int(df["uncertain"].sum())
kritisch = g.kritische_zone(df, X, y_spalte)
st.caption(
    f"◆ Raute = **weniger sichere** Bewertung ({n_unsicher} von {len(df)} Berufen): Die beiden Sprachmodelle weichen um "
    "mehr als 1 Punkt voneinander ab, wiederholte Bewertungen desselben Modells streuen um mehr als 1 Punkt, "
    "oder es liegt nur eine gültige Bewertung vor. ● Kreis = übereinstimmende Bewertung. Die Werte beider Modelle und "
    "der Grund stehen im Tooltip. "
    + (f"In der kritischen Zone liegen {len(kritisch)} Berufe mit {g.tsd(kritisch['employed_k'].sum())} Tsd. "
       f"Erwerbstätigen: {', '.join(kritisch.sort_values('employed_k', ascending=False)['occupation'])}. "
       "Wie viele Berufe in der Zone liegen, hängt stark von den Schwellen ab (siehe «Methodik & Quellen»)."
       if not kritisch.empty else "In der kritischen Zone liegt derzeit kein Beruf.")
)
if farb_modus == "Frauenanteil (%)":
    st.caption("Farbe: blau = überwiegend Männer, grau = ausgeglichen, rot = überwiegend Frauen "
               "(BFS Strukturerhebung 2024).")
if y_spalte == "physical_automation":
    st.caption("Physische Automatisierung ist eine separate Kennzahl: Sie misst nicht-generative Technik "
               "(z. B. Selbstbedienungskassen) und fliesst nicht in den KI-Expositions-Score ein.")
