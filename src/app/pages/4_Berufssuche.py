"""
Seite 4: Beruf-Detail-Suche mit URL-Permalink via st.query_params
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import gemeinsam as g  # noqa: E402

st.title("🔍 Beruf nachschlagen")

df = g.lade_scores()
if df is None:
    st.warning("Noch keine Score-Daten vorhanden.")
    st.stop()

# ── Lookup: ESCO-Titel und Synonyme pro Beruf ───────────────────────────────────
_esco_map: dict[str, str] = {}
_syn_map: dict[str, list[str]] = {}
for _, _row in df.iterrows():
    _t = g.text(_row.get("esco_title"))
    if _t:
        _esco_map[_row["occupation"]] = _t
    _s = [s.strip() for s in g.text(_row.get("synonyms")).split(";") if s.strip()]
    if _s:
        _syn_map[_row["occupation"]] = _s

# Synonym (bisheriger CH-Titel eines zusammengelegten Berufs) → Eintrag
_synonym_zu_beruf = {s.lower(): b for b, syn in _syn_map.items() for s in syn}


def _label(beruf: str) -> str:
    teile = [beruf] + _syn_map.get(beruf, [])
    esco = _esco_map.get(beruf, "")
    if esco and esco.lower() not in {t.lower() for t in teile}:
        teile.append(esco)
    return "  ·  ".join(teile)


# ── URL-State / Permalink ───────────────────────────────────────────────────────
berufe_sorted = sorted(df["occupation"].unique())
url_beruf = st.query_params.get("beruf", "")
if url_beruf not in berufe_sorted:  # alte Permalinks: bisherige CH-Titel als Synonym
    url_beruf = _synonym_zu_beruf.get(url_beruf.lower(), url_beruf)
default_index = berufe_sorted.index(url_beruf) if url_beruf in berufe_sorted else 0

beruf = st.selectbox(
    "Beruf auswählen  (Schweizer Titel, Synonym oder ESCO-Bezeichnung)",
    berufe_sorted,
    index=default_index,
    format_func=_label,
)
st.query_params["beruf"] = beruf

row = df[df["occupation"] == beruf].iloc[0]
if beruf in _syn_map:
    st.caption("Umfasst auch: " + " · ".join(_syn_map[beruf]) + " — die Strukturerhebung weist diese "
               "Berufe nicht getrennt aus; der Eintrag ist als Ganzes bewertet.")

# ── Kennzahlen ──────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("KI-Exposition", f"{row['exposure']:.1f} / 10", help=g.HILFE["exposure"])
c2.metric("Zeitersparnis", f"{row['time_savings']:.1f} / 10", help=g.HILFE["time_savings"])
verschiebung = int(row["timeframe_sme_shift"]) if pd.notna(row["timeframe_sme_shift"]) else 0
zeit_hilfe = (f"Adoption in mindestens rund einem Drittel der Schweizer Betriebe. Einschätzung der Modelle: "
              f"{g.text(row['timeframe_raw']) or '–'}"
              + ({-1: "; eine Stufe früher, weil die Branche von Grossunternehmen geprägt ist (KMU-Faktor).",
                  1: "; eine Stufe später, weil die Branche von KMU geprägt ist (KMU-Faktor).",
                  0: "; KMU-Faktor der Branche neutral."}[verschiebung]))
c3.metric("Zeitrahmen", g.text(row["timeframe"]) or "–", help=zeit_hilfe)
c4.metric("Erwerbstätige CH", f"{row['employed_k']:.1f} Tsd.",
          help="BFS Strukturerhebung 2024, Erwerbstätige der CH-ISCO-19-Berufsgattung "
               f"{row['isco_code']} (bzw. der zugeordneten Berufsarten)")

if row["uncertain"]:
    st.warning(
        f"**Weniger sichere Bewertung:** {'; '.join(g.unsicher_gruende(row))}. "
        f"Angezeigt wird der Mittelwert {row['exposure']:.1f}.",
        icon="⚠️",
    )
else:
    st.caption(f"Claude {row['exposure_claude']:.1f}, Gemini {row['exposure_gemini']:.1f} — übereinstimmend.")

# ── Arbeitszeit nach Modus ──────────────────────────────────────────────────────
st.subheader("Wie die Arbeitszeit betroffen ist")
zeta = float(row["exposure"]) / 10.0
segmente = [(f"KI {name}", (0.0 if pd.isna(row[spalte]) else float(row[spalte])) * zeta * 100, farbe)
            for name, spalte, farbe in g.MODI]
segmente.append(("nicht exponiert", max(0.0, 100.0 - sum(s[1] for s in segmente)), g.GRAU))
fig = go.Figure()
for name, wert, farbe in segmente:
    fig.add_trace(go.Bar(
        x=[wert], y=["Arbeitszeit"], orientation="h", name=name, marker=dict(color=farbe,
                                                                            line=dict(width=2, color="#fcfcfb")),
        text=[f"{wert:.0f} %" if wert >= 6 else ""], textposition="inside", insidetextanchor="middle",
        textfont=dict(color="#0b0b0b" if farbe in (g.GRAU, g.SERIE[2]) else "#fcfcfb"),
        hovertemplate=f"{name}: %{{x:.1f}} % der Arbeitszeit<extra></extra>",
    ))
fig.update_layout(barmode="stack", height=170, showlegend=True,
                  legend=dict(orientation="h", yanchor="bottom", y=1.05, x=0, traceorder="normal"),
                  xaxis=dict(range=[0, 100], ticksuffix=" %", gridcolor="#e1e0d9"), yaxis=dict(visible=False),
                  margin=dict(t=40, b=30, l=8, r=8))
st.plotly_chart(fig, width="stretch")
st.caption(
    "**Ersetzend:** KI führt aus, der Mensch prüft höchstens stichprobenartig. **Delegierend:** KI erstellt "
    "das Ergebnis, der Mensch prüft jede Ausgabe fachlich. **Unterstützend:** Der Mensch arbeitet selbst, "
    "KI liefert Teilergebnisse. Summe der drei KI-Anteile = KI-Exposition. "
    + " · ".join(f"{name}: {wert:.0f} %" for name, wert, _ in segmente)
)

d1, d2, d3, d4 = st.columns(4)
d1.metric("Physische Automatisierung", f"{row['physical_automation']:.1f} / 10", help=g.HILFE["physical_automation"])
d2.metric("Software-Automatisierung", f"{row['software_automation']:.1f} / 10", help=g.HILFE["software_automation"])
d3.metric("Ersetzbare Arbeitszeit", g.prozent(row["replaceable_time"] * 100),
          help="Anteil der Arbeitszeit, der in Tätigkeiten mit Modus «ersetzend» tatsächlich eingespart wird.")
d4.metric("Anpassungsfähigkeit", f"{row['adaptability']:.1f} / 10",
          help="Regelbasiert: Qualifikation, Lohn, Branchenmobilität (siehe Methodik).")
if row["physical_automation"] >= 2 * max(row["exposure"], 0.5):
    st.info("Bei diesem Beruf ist die **Automatisierung ohne generative KI** (z. B. Robotik, Automaten, "
            "Selbstbedienung) deutlich grösser als die KI-Exposition — der KI-Score allein unterschätzt den "
            "technischen Wandel.", icon="🤖")

st.markdown(f"**Hauptrisiko:** {g.text(row['main_risk']) or '–'}")
st.markdown(f"**Begründung:** {g.text(row['rationale']) or '–'}")

# ── Tätigkeiten aus der Bewertung ───────────────────────────────────────────────
st.subheader("Bewertete Tätigkeiten")
pfad = g.bewertungsdatei(row["text_source"], row["isco_code"], beruf)
bewertung = g.lade_bewertung(str(pfad)) if pfad is not None else None
if bewertung and bewertung.get("taetigkeiten"):
    zeilen = [{
        "Tätigkeit": t.get("name", ""),
        "Anteil": t.get("zeitanteil_pct"),
        "Stufe": t.get("stufe", ""),
        "Modus": t.get("modus") or "–",
        "Restzeit": f"{t['restzeit_mensch']} %" if t.get("restzeit_mensch") else "–",
        "Ohne gen. KI": ({"physisch": "physisch", "software": "Software"}.get(t.get("p_art"), "ja")
                         if t.get("physisch_automatisierbar") == "P1" else "–"),
        "Sicherheit": t.get("sicherheit", ""),
    } for t in sorted(bewertung["taetigkeiten"], key=lambda t: -t.get("zeitanteil_pct", 0))]
    st.dataframe(pd.DataFrame(zeilen), hide_index=True, width="stretch", column_config={
        "Tätigkeit": st.column_config.TextColumn("Tätigkeit", width="large"),
        "Anteil": st.column_config.ProgressColumn("Anteil", format="%d %%", min_value=0,
                                                  max_value=100, width="small"),
        "Stufe": st.column_config.TextColumn("Stufe", width="small",
                                             help="E0 nicht exponiert · E1 Chat-LLM reicht · E2 mit KI-Werkzeugen"),
        "Restzeit": st.column_config.TextColumn("Restzeit", width="small",
                                                help="Verbleibender menschlicher Aufwand in % der heutigen Zeit"),
        "Ohne gen. KI": st.column_config.TextColumn(
            "Ohne gen. KI", width="small",
            help="P1: mit heute verfügbarer nicht-generativer Technik zu ≥ 50 % übernehmbar (physisch oder Software)"),
        "Sicherheit": st.column_config.TextColumn("Sicherheit", width="small"),
    })
    with st.expander("Begründung je Tätigkeit"):
        for t in sorted(bewertung["taetigkeiten"], key=lambda t: -t.get("zeitanteil_pct", 0)):
            st.markdown(f"- **{t.get('name', '')}** ({t.get('stufe', '')}, {t.get('zeitanteil_pct', '')} %): "
                        f"{t.get('begruendung', '')}")
        if g.text(bewertung.get("kommentar")):
            st.caption(f"Kommentar der Bewertung: {bewertung['kommentar']}")
    st.caption(
        f"Tätigkeitsliste aus {g.quelle_lesbar(row['text_source'])} — dem Lauf, dessen Score dem Mittel "
        "am nächsten liegt (Texte oben ebenfalls daraus). Andere Läufe und das zweite Modell können "
        "die Tätigkeiten etwas anders schneiden. Stufe: **E0** nicht exponiert, **E1** ein Chat-Sprachmodell "
        "reicht, **E2** erst mit KI-Werkzeugen oder Integration — bei E1/E2 halbiert generative KI die Zeit "
        "mindestens (Prüfaufwand eingerechnet); Restzeit = verbleibender menschlicher Aufwand. Rubrik v2.2."
    )
else:
    st.info("Die Tätigkeitsliste dieser Bewertung ist nicht verfügbar.", icon="ℹ️")

# ── Bewertungsgrundlage ─────────────────────────────────────────────────────────
st.divider()
esco_uri = g.text(row.get("esco_uri"))
esco_titel = g.text(row.get("esco_title"))
esco_desc = g.text(row.get("esco_description"))

if esco_uri:
    lbl = f"ESCO-Beschreibung ({esco_titel})" if esco_titel else "ESCO-Beschreibung"
    with st.expander(lbl):
        if esco_desc:
            st.caption(esco_desc)
        st.caption(f"ESCO URI: {esco_uri}")
        qual = g.text(row.get("esco_match_quality"))
        esco_isco = g.text(row.get("esco_isco_code"))
        if qual:
            st.caption(f"Match-Qualität: {qual}" + (f" (ESCO-ISCO {esco_isco})" if esco_isco else ""))
        st.caption("Quelle: ESCO v1.2.1 © Europäische Union, CC BY 4.0; Beschreibung ggf. gekürzt/angepasst. "
                   "Die ESCO-Kompetenzen des Berufs sind Teil der Bewertungsgrundlage.")
else:
    with st.expander("Bewertungsgrundlage"):
        st.caption(
            "Kein ESCO-Match gefunden. Die Bewertung basiert auf dem Berufstitel, dem Schweizer Kontext und "
            f"einer Beschreibung aus der Quelle «{g.text(row.get('description_source')) or 'unbekannt'}»."
        )
        if esco_desc:
            st.caption(esco_desc)

# ── Permalink ──────────────────────────────────────────────────────────────────
st.caption(f"🔗 Direktlink zu diesem Beruf: füge `?beruf={beruf}` an die URL an.")
