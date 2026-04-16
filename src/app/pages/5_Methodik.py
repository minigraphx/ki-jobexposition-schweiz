"""
Seite 5: Methodik & Quellen
"""

import streamlit as st

st.set_page_config(page_title="Methodik & Quellen", layout="wide")
st.title("Methodik & Quellen")

st.markdown("""
Diese Seite erklärt, wie die KI-Expositions-Scores berechnet wurden und woher die Daten stammen.
""")

# ─── Datenquellen ─────────────────────────────────────────────────────────────
st.header("Datenquellen")

st.subheader("Beschäftigungsdaten")
st.markdown("""
Die Beschäftigungszahlen und Frauenanteile stammen aus der offiziellen Schweizer Statistik:

- **Quelle:** Bundesamt für Statistik (BFS)
- **Erhebung:** Schweizerische Arbeitskräfteerhebung (SAKE) 2024
- **Tabelle:** *Ausgeübter Beruf (CH-ISCO-19) nach Geschlecht und Staatsangehörigkeit*
- **Download:** [bfs.admin.ch](https://www.bfs.admin.ch/bfs/de/home/statistiken/kataloge-datenbanken.assetdetail.36492006.html)
- **Einheit:** Erwerbstätige ab 15 Jahren, in 1'000 Personen
- **Klassifikation:** CH-ISCO-19 (basiert auf ISCO-08), Ebene Berufsgattung (4-stellig)

Es werden Berufe mit mindestens **5'000 Beschäftigten** berücksichtigt.
""")

st.subheader("Berufsbeschreibungen")
st.markdown("""
Für das KI-Scoring benötigt jeder Beruf eine inhaltliche Beschreibung seiner Kerntätigkeiten.
Diese stammt aus:

- **Quelle:** ESCO (European Skills, Competences, Qualifications and Occupations), Version 1.2
- **Betreiber:** Europäische Kommission
- **API:** [esco.ec.europa.eu](https://esco.ec.europa.eu/de/use-esco/esco-api)
- **Sprache:** Deutsch, Fallback Englisch
- **Matching:** Primär via ISCO-Code, Fallback via Textsuche mit Berufsbezeichnung
""")

st.subheader("Lohndaten")
st.markdown("""
Die medianen Jahresbruttolöhne sind Schätzwerte basierend auf:

- **Quelle:** BFS Lohnstrukturerhebung (LSE) 2022
- **Aggregation:** Medianwert pro ISCO-Untergruppe (2-stellig), inkl. 13. Monatslohn
- **Hinweis:** Für Berufe aus dem BFS-SAKE-Datensatz (neue Einträge) werden Lohnschätzungen
  auf Basis der ISCO-Berufsgruppe verwendet, nicht berufsindividuelle Werte.
""")

st.divider()

# ─── Scoring-Methodik ─────────────────────────────────────────────────────────
st.header("KI-Expositions-Score (0–10)")

st.markdown("""
Die Scoring-Methodik folgt dem Ansatz von **Andrej Karpathy (2024)** und der
**Brookings Institution**, adaptiert für den Schweizer Kontext.

Für jeden Beruf wird Claude (claude-sonnet-4-6) beauftragt, anhand der ESCO-Berufsbeschreibung
fünf Kriterien auf einer Skala von 0–10 zu bewerten:
""")

st.markdown("""
| Kriterium | Gewichtung | Beschreibung |
|---|---|---|
| Digitaler Output | 25 % | Arbeitet der Beruf primär mit digitalen Informationen, Texten oder Daten? |
| Wiederholbarkeit | 25 % | Sind die Kerntätigkeiten strukturiert, vorhersehbar und regelbasiert? |
| Physische Präsenz | 20 % | Je mehr körperliche Präsenz nötig, desto **tiefer** der Score |
| Kreativität | 15 % | Je mehr originelles Denken gefragt, desto **tiefer** der Score |
| Soziale Interaktion | 15 % | Je mehr Empathie und Vertrauen nötig, desto **tiefer** der Score |

Der **Rohscore** ergibt sich aus der gewichteten Summe dieser Kriterien.
""")

st.subheader("Schweiz-spezifische Anpassungen")
st.markdown("""
Auf den Rohscore werden CH-spezifische Faktoren angewendet, die den lokalen Arbeitsmarktkontext
berücksichtigen:

| Faktor | Effekt | Begründung |
|---|---|---|
| Finanz- & Versicherungssektor | +0.3 | Hoher Automatisierungsdruck, digitaler Reifegrad |
| Gesundheit & Soziales | −0.3 | Fachkräftemangel, Schutzinteressen, hoher Regulierungsgrad |
| Öffentliche Verwaltung | −0.2 | Langsame Adoptionsrate, politische Rahmenbedingungen |
| Bildungssektor | −0.1 | Gesellschaftlicher Konsens über menschliche Lehrvermittlung |
| Hohe Löhne (> 120'000 CHF) | +0.2 | Stärkerer wirtschaftlicher Anreiz zur Automatisierung |
| Tiefe Löhne (< 60'000 CHF) | −0.1 | Geringerer ROI für Automatisierungsinvestitionen |

Der finale **score_ch** wird auf den Bereich 0–10 begrenzt.
""")

st.divider()

# ─── Anpassungsfähigkeit ──────────────────────────────────────────────────────
st.header("Anpassungsfähigkeits-Score (0–10)")

st.markdown("""
Der Anpassungsfähigkeits-Score (verwendet in der Matrix-Ansicht) misst, wie leicht
Berufsangehörige sich bei Automatisierungsdruck neu orientieren können.
Er basiert auf der Methodik der **Brookings Institution** und setzt sich zusammen aus:

| Kriterium | Max. Punkte | Quelle |
|---|---|---|
| Qualifikationsniveau | 4 | BFS SAKE (Bildungsabschluss nach ISCO) |
| Lohnniveau | 3 | LSE 2022 (höherer Lohn = mehr Ressourcen für Umschulung) |
| Digitale Affinität | 2 | KI-Score Teilkriterium «Digitaler Output» |
| Branchenmobilität | 1 | Schätzung basierend auf Branchencharakteristika |

Skala: 0 = sehr schwer anzupassen, 10 = sehr flexibel
""")

st.divider()

# ─── Einschränkungen ──────────────────────────────────────────────────────────
st.header("Einschränkungen & Hinweise")

st.markdown("""
- **KI-Scoring ist keine exakte Wissenschaft.** Die Scores sind Einschätzungen eines
  Sprachmodells, keine empirisch gemessenen Werte. Sie sollten als Orientierung, nicht als
  Prognose verstanden werden.
- **Exposition ≠ Jobverlust.** Ein hoher Score bedeutet, dass Teile des Berufs automatisierbar
  *sein könnten* – nicht dass Jobs verschwinden. Viele Berufe wandeln sich.
- **Datenbasis 2024.** Die Beschäftigungszahlen basieren auf SAKE 2024. Die KI-Landschaft
  verändert sich schnell; Scores können in 1–2 Jahren bereits überholt sein.
- **ESCO-Matching nicht immer perfekt.** Für einige Schweizer Berufsbezeichnungen existiert
  kein exakter ESCO-Eintrag. In diesen Fällen wurde der nächstähnliche Beruf verwendet.
- **Lohnschätzungen für neue Einträge** basieren auf ISCO-Gruppendurchschnitten, nicht auf
  berufsindividuellen Erhebungen.
""")

st.divider()

# ─── Referenzen ───────────────────────────────────────────────────────────────
st.header("Referenzen")

st.markdown("""
- Karpathy, A. (2024). [AI job exposure treemap](https://x.com/karpathy) — Methodik-Impuls
- Brookings Institution (2019). *Automation and Artificial Intelligence: How machines are affecting people and places*
- Webb, A. (2026). *Tech Trends Report* — Convergence-Ansatz für Branchenanalyse
- BFS (2024). [Schweizerische Arbeitskräfteerhebung (SAKE)](https://www.bfs.admin.ch/bfs/de/home/statistiken/arbeit-erwerb/erhebungen/sake.html)
- Europäische Kommission (2023). [ESCO v1.2](https://esco.ec.europa.eu)
- BFS (2022). [Lohnstrukturerhebung (LSE)](https://www.bfs.admin.ch/bfs/de/home/statistiken/arbeit-erwerb/loehne-erwerbseinkommen-arbeitskosten/lohnstruktur.html)
""")
