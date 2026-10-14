"""
Seite 3: Branchenanalyse – beschäftigungsgewichtete Exposition je Branche, Grenzgänger-Kontext,
Konvergenz-Heatmap (Webb-Logik) aus den aufgabenbasierten Kennzahlen
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import gemeinsam as g  # noqa: E402

st.title("🏭 Branchenanalyse Schweiz")

df = g.lade_scores()
ggs = g.lade_csv(str(g.GGS_PATH))

st.markdown("""
Welche Schweizer Branchen sind am stärksten von generativer KI betroffen?
Und welche werden durch mehrere Automatisierungswellen gleichzeitig getroffen?
Inspiriert von Amy Webbs *Future Today Institute Convergence Outlook 2026*.
""")

if df is None:
    st.warning("Noch keine Score-Daten vorhanden.")
    st.stop()


def _branchen(df: pd.DataFrame) -> pd.DataFrame:
    zeilen = []
    for branche, d in df.groupby("sector"):
        zeilen.append({
            "sector": branche,
            "exposure_w": g.gewichtet(d, "exposure"),
            "exposure_mean": d["exposure"].mean(),
            "exposure_min": d["exposure"].min(),
            "exposure_max": d["exposure"].max(),
            "time_savings_w": g.gewichtet(d, "time_savings"),
            "replaceable_w": g.gewichtet(d, "replaceable_time") * 10,
            "software_w": g.gewichtet(d, "software_automation"),
            "physical_w": g.gewichtet(d, "physical_automation"),
            "berufe": len(d),
            "employed": d["employed_k"].sum(),
        })
    return pd.DataFrame(zeilen)


stats = _branchen(df)
if ggs is not None:
    stats = stats.merge(ggs[["sector", "cross_border_share", "cross_border"]], on="sector", how="left")

# --- Sektion 1: Exposition je Branche ------------------------------------------------------------
st.subheader("KI-Exposition nach Branche")
bar = stats.sort_values("exposure_w", ascending=True)
hover = {"exposure_w": ":.2f", "exposure_mean": ":.2f", "exposure_min": ":.1f", "exposure_max": ":.1f",
         "berufe": True, "employed": ":.0f", "sector": False}
labels = {"exposure_w": "Ø KI-Exposition (gewichtet)", "exposure_mean": "Ø ungewichtet", "sector": "Branche",
          "exposure_min": "tiefster Beruf", "exposure_max": "höchster Beruf", "berufe": "Berufe",
          "employed": "Erwerbstätige (Tsd.)", "cross_border_share": "Grenzgänger-Anteil"}
if "cross_border_share" in bar:
    hover["cross_border_share"] = ":.1%"
fig_bar = px.bar(bar, x="exposure_w", y="sector", orientation="h", hover_data=hover, labels=labels,
                 text="exposure_w",
                 title="Ø KI-Exposition je Branche, gewichtet mit den Erwerbstätigen der Berufe")
fig_bar.update_traces(marker_color=g.SERIE[0], texttemplate="%{x:.1f}", textposition="outside",
                      cliponaxis=False)
fig_bar.update_layout(height=640, bargap=0.25, xaxis=dict(range=[0, 10], title="Ø KI-Exposition (0–10)",
                                                          gridcolor="#e1e0d9"),
                      yaxis_title=None, margin=dict(l=8, r=24))
st.plotly_chart(fig_bar, width="stretch")

col1, col2 = st.columns(2)
tab = stats.assign(exposure_w=stats["exposure_w"].round(1))[["sector", "exposure_w", "berufe", "employed"]]
tab.columns = ["Branche", "Ø Exposition", "Berufe", "Erwerbstätige (Tsd.)"]
with col1:
    st.markdown("**Meist exponierte Branchen**")
    st.dataframe(tab.nlargest(5, "Ø Exposition"), hide_index=True, width="stretch")
with col2:
    st.markdown("**Am wenigsten exponierte Branchen**")
    st.dataframe(tab.nsmallest(5, "Ø Exposition"), hide_index=True, width="stretch")
st.caption("Gewichtet = jeder Beruf zählt mit seinen Erwerbstätigen (BFS Strukturerhebung 2024); "
           "ungewichtete Mittel, Spannweite und Grenzgänger-Anteil im Tooltip.")

# --- Sektion 2: Grenzgänger-Kontext ----------------------------------------------------------------
if ggs is not None and "cross_border_share" in stats:
    st.divider()
    st.subheader("Grenzgänger-Anteil und KI-Exposition")
    st.markdown(
        "Branchen mit hohem Grenzgänger-Anteil und hoher KI-Exposition sind doppelt exponiert: "
        "Automatisierungsdruck trifft überproportional auf ausländische Beschäftigte, "
        "die weniger von Schweizer Auffangnetzen profitieren."
    )
    fig_ggs = px.scatter(
        stats, x="cross_border_share", y="exposure_w", size="employed", text="sector",
        title="Grenzgänger-Anteil und Ø KI-Exposition je Branche",
        labels={"cross_border_share": "Grenzgänger-Anteil", "exposure_w": "Ø KI-Exposition (gewichtet)",
                "employed": "Erwerbstätige (Tsd.)", "cross_border": "Grenzgänger/-innen",
                "sector": "Branche"},
        hover_data={"cross_border": ":,", "employed": ":.0f", "exposure_w": ":.2f",
                    "cross_border_share": ":.1%", "sector": False},
        size_max=45,
    )
    fig_ggs.update_traces(marker=dict(color=g.SERIE[0], opacity=0.7, line=dict(width=1.5, color="#fcfcfb")),
                          textposition="top center", textfont=dict(size=11, color=g.TEXT_GEDAEMPFT))
    fig_ggs.update_layout(height=540, xaxis=dict(tickformat=".0%", gridcolor="#e1e0d9"),
                          yaxis=dict(range=[0, max(6.0, stats["exposure_w"].max() + 1)], gridcolor="#e1e0d9"))
    st.plotly_chart(fig_ggs, width="stretch")
    periode = str(ggs["ggs_period"].iloc[0])
    periode = f"Jahresmittel {periode}" if periode.isdigit() else periode
    st.caption(
        "Grenzgänger-Anteil = ausländische Grenzgänger/-innen in den NOGA-Abteilungen der Branche "
        f"/ Beschäftigte derselben Abteilungen (BFS STATENT {ggs['statent_year'].iloc[0]}, arbeitsortbasiert, "
        f"Grenzgänger enthalten). Zähler: BFS Grenzgängerstatistik (GGS), stats.swiss DF_GGS_4, {periode} "
        f"(provisorisch), {g.tsd(ggs['cross_border'].sum())} Grenzgänger/-innen in den 21 Branchen. "
        "Blasengrösse = Erwerbstätige der erfassten Berufe in Tsd. (BFS Strukturerhebung 2024). "
        "Fliesst nicht in die Exposition ein — rein additiver Kontext-Layer."
    )

st.divider()

# --- Sektion 3: Konvergenz-Heatmap ----------------------------------------------------------------
st.subheader("Konvergenz: Wo treffen mehrere Automatisierungswellen zusammen?")
st.markdown(
    "Welche Branchen werden durch **mehrere Wellen gleichzeitig** getroffen? Die Heatmap stellt je "
    "Branche fünf Kennzahlen aus der Tätigkeitsbewertung nebeneinander — drei zur generativen KI, zwei "
    "zur Automatisierung mit klassischer Technik."
)
WELLEN = [
    ("exposure_w", "Generative KI<br>(Exposition)"),
    ("time_savings_w", "Zeitersparnis<br>durch KI"),
    ("replaceable_w", "Ersetzbare<br>Arbeitszeit"),
    ("software_w", "Klassische<br>Software"),
    ("physical_w", "Physische<br>Automatisierung"),
]
cols = [c for c, _ in WELLEN]
werte = stats.set_index("sector")[cols]
relativ = werte / werte.max().where(werte.max() > 0, 1)          # 0–1 je Spalte (Rang innerhalb der Welle)
relativ = relativ.assign(index=relativ.mean(axis=1)).sort_values("index", ascending=True)
werte = werte.loc[relativ.index]
z = relativ[cols].to_numpy()

fig_heat = go.Figure(go.Heatmap(
    z=z, x=[t for _, t in WELLEN], y=list(werte.index), zmin=0, zmax=1, colorscale=g.SKALA_0_10,
    customdata=werte.to_numpy(), xgap=2, ygap=2,
    hovertemplate="<b>%{y}</b><br>%{x}: %{customdata:.2f} (0–10)<extra></extra>",
    colorbar=dict(title="relativ zum<br>Höchstwert", tickvals=[0, 0.5, 1], ticktext=["0", "50 %", "100 %"]),
))
for i, branche in enumerate(werte.index):
    for j, c in enumerate(cols):
        fig_heat.add_annotation(x=WELLEN[j][1], y=branche, text=f"{werte.at[branche, c]:.1f}", showarrow=False,
                                font=dict(size=11, color="#fcfcfb" if z[i, j] > 0.55 else "#0b0b0b"))
fig_heat.update_layout(height=720, title="Konvergenz-Heatmap: Branchen × Automatisierungswellen",
                       xaxis=dict(side="top"), yaxis_title=None, margin=dict(t=110, l=8, r=8))
st.plotly_chart(fig_heat, width="stretch")
st.caption(
    "Zahlen = beschäftigungsgewichtetes Mittel der Branche auf der Skala 0–10 (Anteil der Arbeitszeit × 10). "
    "**Generative KI** = KI-Exposition; **Zeitersparnis** = davon eingesparte Zeit; **Ersetzbare Arbeitszeit** "
    "= Zeit in Tätigkeiten, die KI weitgehend selbständig erledigt (Modus «ersetzend»); **Klassische "
    "Software** und **Physische Automatisierung** = Tätigkeiten, die Technik ohne generative KI übernehmen "
    "kann (Regel-Software bzw. Robotik, Automaten, Selbstbedienung). Die Farbe zeigt den Wert relativ zum "
    "Höchstwert der jeweiligen Welle, damit auch die kleinen Werte der klassischen Automatisierung "
    "vergleichbar sind; sortiert nach dem Mittel dieser relativen Werte (Konvergenz-Index). Bis Oktober "
    "2026 war die Heatmap eine qualitative Einschätzung; jetzt beruht sie auf den Tätigkeitsbewertungen."
)
