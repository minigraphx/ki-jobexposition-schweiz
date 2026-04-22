"""
Seite 5: Methodik & Quellen
"""

import streamlit as st

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
Die Beschreibungen werden in einem mehrstufigen Prozess ermittelt:

| Stufe | Quelle | Berufe |
|---|---|---|
| 1–3 | ESCO API (ISCO-Code + Textsuche, Deutsch/Englisch) | 201 von 204 |
| 4 | berufsberatung.ch (Fallback bei keinem ESCO-Treffer) | — |
| 5 | Wikipedia (zweiter Fallback) | — |
| 6 | Claude Haiku (generierte Beschreibung als letzter Ausweg) | 3 von 204 |

Die verwendete Quelle ist in der Spalte `beschreibung_quelle` gespeichert und
wird bei der Berufssuche angezeigt.

- **ESCO:** [esco.ec.europa.eu](https://esco.ec.europa.eu/de/use-esco/esco-api), Version 1.2
- **Sprache:** Deutsch, Fallback Englisch
""")

st.subheader("Lohndaten")
st.markdown("""
Die medianen Jahresbruttolöhne sind Schätzwerte basierend auf:

- **Quelle:** BFS Lohnstrukturerhebung (LSE) 2022
- **Aggregation:** Medianwert pro ISCO-Untergruppe (2-stellig), inkl. 13. Monatslohn
- **Hinweis:** Für Berufe aus dem BFS-SAKE-Datensatz (neue Einträge) werden Lohnschätzungen
  auf Basis der ISCO-Berufsgruppe verwendet, nicht berufsindividuelle Werte.
""")

st.subheader("Grenzgänger-Anteil (Kontext)")
st.markdown("""
Der Grenzgänger-Anteil pro Branche dient als zusätzlicher Kontext-Layer in der Branchenanalyse.

- **Quelle:** BFS Grenzgängerstatistik (BGS), Cube `DF_GGS_4` —
  „Ausländische Grenzgänger/-innen nach Wirtschaftszweig und Erwerbsstatus",
  letztes verfügbares Quartal (stats.swiss)
- **Berechnung:** grenzgaenger_anteil = Grenzgänger in Branche / Beschäftigte in Branche
  (BFS STATENT/BZ, sektorweite Gesamtbeschäftigung)
- **Granularität:** NOGA-Wirtschaftsabteilungen (2-stellig), aggregiert auf die 21 internen Branchen
- **Wichtig: fliesst nicht in score_ch oder zeitrahmen ein** — rein additiver Kontext-Layer
- **Limitation:** Kein Pro-Beruf-Mapping möglich; NOGA-Ebene deckt nicht alle Berufe gleichmässig ab
""")

st.divider()

# ─── Scoring-Methodik ─────────────────────────────────────────────────────────
st.header("KI-Expositions-Score (0–10)")

st.markdown("""
Die Scoring-Methodik folgt dem Ansatz von **Andrej Karpathy (März 2026)** und der
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
berücksichtigen. Alle 21 Branchen aus dem Datensatz sind explizit bewertet:

**Brancheneffekte** (Deltawert auf den Rohscore):

| Branche | Delta | Begründung |
|---|---|---|
| Versicherungen | **+0.4** | Sehr standardisierte Prozesse, hoher Digitalisierungsgrad |
| Finanzen | **+0.3** | Bankplatz CH: hoher Automatisierungsdruck |
| Beratung | **+0.2** | Wissensarbeit: KI augmentiert Analyse & Strategie |
| Detailhandel | **+0.2** | E-Commerce-Druck, Self-Checkout, Logistikautomation |
| Recht | **+0.2** | LegalTech wächst; Dokumentenanalyse automatisierbar |
| Immobilien | **+0.1** | PropTech, Bewertungs-KI, digitale Plattformen |
| Medien | **+0.1** | KI-generierte Inhalte, aber Kreativität dämpft |
| Verwaltung | **+0.1** | Private Administration: strukturierte Büroprozesse |
| Dienstleistungen | **0.0** | Zu heterogen für einheitlichen Effekt |
| Transport | **0.0** | Physisch, aber autonomes Fahren mittelfristig |
| Umwelt | **0.0** | Spezialisiert; Monitoring-KI vs. Feldarbeit neutral |
| Gastgewerbe | **−0.1** | Serviceorientiert, Kundenkontakt; Buchungs-KI marginal |
| Industrie | **−0.1** | MEM/Pharma: Fachkräftemangel als Puffer |
| Landwirtschaft | **−0.1** | Precision Farming wächst, aber physische Arbeit dominiert |
| Öff. Verwaltung | **−0.1** | Öffentl. Sektor: langsame Adoption, politische Rahmenbedingungen |
| Sicherheit | **−0.1** | Physische Präsenz erforderlich; Überwachungs-KI ergänzt nur |
| Bau | **−0.2** | Stark physisch, handwerklich; Digitalisierung langsam |
| Bildung | **−0.2** | Gesellschaftlicher Konsens über menschliche Lehrvermittlung |
| ICT | **−0.2** | KI-Fachkräfte adaptiv; treiben Wandel selbst |
| Gesundheit | **−0.3** | Regulierung, Fachkräftemangel, Pflegekomponente als Bremse |
| Soziales | **−0.3** | Hoher Empathiebedarf, Schutzinteressen; ähnlich Gesundheit |

**Lohneffekte** (Deltawert auf den Rohscore):

| Lohnklasse (Jahresbruttolohn) | Delta | Begründung |
|---|---|---|
| > 150'000 CHF | **+0.4** | Sehr hoher ROI für Automatisierungsinvestitionen |
| 100'000–150'000 CHF | **+0.2** | Stärkerer wirtschaftlicher Anreiz zur Automatisierung |
| 60'000–100'000 CHF | **0.0** | Neutral |
| < 60'000 CHF | **−0.2** | Geringerer ROI; manuelle Arbeit oft günstiger |

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

st.subheader("Weitere CH-spezifische Faktoren (nicht in Score eingeflossen)")
st.markdown("""
Folgende Faktoren beeinflussen die KI-Exposition im Schweizer Kontext, sind aber in der
aktuellen Berechnung **nicht berücksichtigt**:

- **Sprachregionen:** Die SAKE-Daten sind nicht nach Sprachregion × Beruf aufgeschlüsselt.
  Deutschschweiz, Romandie und Tessin können strukturell unterschiedliche Expositionsmuster
  aufweisen.
- **Kantonale/regionale Lohnunterschiede:** Die LSE-Lohndaten sind national aggregiert.
  Regionale Lohndisparitäten (z.B. Zürich vs. Wallis) fliessen nicht ins Scoring ein.
- **KMU-Adoptionsgeschwindigkeit:** Kleine und mittlere Unternehmen (KMU, > 99 % der CH-Firmen)
  adoptieren KI-Technologien typischerweise langsamer als Grossunternehmen. Dies beeinflusst
  den realen Zeitrahmen der Automatisierung (BFS STATENT als mögliche Datenquelle, Issue #33).
- **Grenzgänger-Effekte:** Der Schweizer Arbeitsmarkt weist einen hohen Grenzgängeranteil auf.
  Grenzgänger konzentrieren sich auf bestimmte Branchen und Regionen; KI-Exposition dieser
  Gruppe kann vom inländischen Muster abweichen (BFS BGS als Datenquelle, Issue #34).
""")

st.divider()

# ─── Referenzen ───────────────────────────────────────────────────────────────
st.header("Referenzen")

st.markdown("""
- Karpathy, A. (März 2026). [US Job Market Visualizer](https://karpathy.ai/jobs/) — Methodik-Impuls (342 US-Berufe, BLS-Daten, LLM-Scoring)
- Brookings Institution (2019). *Automation and Artificial Intelligence: How machines are affecting people and places*
- Webb, A. (2026). *Tech Trends Report* — Convergence-Ansatz für Branchenanalyse
- BFS (2024). [Schweizerische Arbeitskräfteerhebung (SAKE)](https://www.bfs.admin.ch/bfs/de/home/statistiken/arbeit-erwerb/erhebungen/sake.html)
- Europäische Kommission (2023). [ESCO v1.2](https://esco.ec.europa.eu)
- BFS (2022). [Lohnstrukturerhebung (LSE)](https://www.bfs.admin.ch/bfs/de/home/statistiken/arbeit-erwerb/loehne-erwerbseinkommen-arbeitskosten/lohnstruktur.html)
""")
