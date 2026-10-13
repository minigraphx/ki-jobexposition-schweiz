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
- **Erhebung:** Strukturerhebung (SE) 2024 (Stichprobenerhebung im Rahmen der jährlichen Volkszählung)
- **Tabelle:** *Ausgeübter Beruf (CH-ISCO-19) nach Geschlecht und Staatsangehörigkeit*
  (su-d-40.02.03.02.01.03.10, Blatt «2024»)
- **Download:** [bfs.admin.ch](https://www.bfs.admin.ch/bfs/de/home/statistiken/kataloge-datenbanken.assetdetail.36492006.html)
- **Einheit:** Erwerbstätige ab 15 Jahren, in 1'000 Personen
- **Grundgesamtheit:** Ständige Wohnbevölkerung in Privathaushalten — Grenzgänger/-innen
  sind nicht enthalten
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
- **Hinweis:** Für Berufe aus dem BFS-SE-Datensatz (neue Einträge) werden Lohnschätzungen
  auf Basis der ISCO-Berufsgruppe verwendet, nicht berufsindividuelle Werte.
""")

st.subheader("Branchenzuordnung")
st.markdown("""
Jeder Beruf ist einer von 21 internen Branchen zugeordnet (Grundlage für Brancheneffekt,
KMU-Faktor und Branchenanalyse):

- **Kuratierte Berufe** (Kernliste): Branche manuell gesetzt.
- **Ergänzte BFS-SE-Berufe:** Zuordnung über den ISCO-Code, wobei der **spezifischste Präfix**
  gilt (4-stellig vor 3-stellig vor 2-stellig). So werden heterogene Gruppen wie die
  Führungskräfte (ISCO 13/14) nach Wirtschaftszweig aufgeteilt — z. B. Produktionsleitung →
  Industrie, Bau → Bau, ICT-Dienstleistungen → ICT, Bildungswesen → Bildung, Finanzdienstleistungen
  → Finanzen, Hotels/Restaurants → Gastgewerbe, Handel → Detailhandel.
- Die Abgrenzung orientiert sich an der NOGA-Zuordnung der Grenzgänger- und KMU-Daten
  (z. B. Grosshandel → Dienstleistungen, Heime → Soziales).
- **Limitation:** Ein Beruf wird genau einer Branche zugeordnet, auch wenn er in mehreren
  Wirtschaftszweigen ausgeübt wird (z. B. Einkäufer, Kranführer).
""")

st.subheader("Grenzgänger-Anteil (Kontext)")
st.markdown("""
Der Grenzgänger-Anteil pro Branche dient als zusätzlicher Kontext-Layer in der Branchenanalyse.

- **Quelle:** BFS Grenzgängerstatistik (BGS), Cube [`DF_GGS_4`](https://stats.swiss/vis?lc=de&df[ds]=ds%3Adisseminate&df[id]=DF_GGS_4&df[ag]=CH1.GGS&df[vs]=1.0.0&dq=..Q&lom=LASTNPERIODS&lo=5) —
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

# ─── Beobachtete Wirkung ──────────────────────────────────────────────────────
st.header("Was wir über die tatsächliche Wirkung wissen (Stand Oktober 2026)")

st.markdown("""
Die Scores dieser App messen die **Exposition**, also was KI technisch übernehmen *könnte*.
Ob und wie stark sich das bereits auf dem Arbeitsmarkt zeigt, ist eine andere Frage.
Hier ist zusammengefasst, was die Forschung bisher beobachtet. Schweizer Zahlen und
internationale Befunde sind bewusst getrennt: Arbeitsmärkte, Daten und Definitionen
unterscheiden sich zu stark, als dass sich ausländische Zahlen auf die Schweiz übertragen liessen.
""")

st.subheader("Schweiz (Zahlen)")
st.markdown("""
- **KOF/ETH — Arbeitslosigkeit und Stelleninserate** (Kläui & Siegenthaler, Okt. 2025):
  Die Zahl der Arbeitslosen stieg in stark KI-exponierten Berufen um **bis zu 27 %** stärker
  als in wenig exponierten.
  *Definition:* 20- bis 49-Jährige, Sept. 2024 bis Aug. 2025 gegenüber Herbst 2022; oberstes vs.
  unterstes Drittel der Berufe nach dem Expositionsmass von Eloundou et al.
  Die Stelleninserate (Daten x28) in exponierten Berufen lagen zuletzt rund **38 %** tiefer
  (relativ zu wenig exponierten Berufen).
  *Einschränkung:* kein Kausalnachweis. Die Inserate in exponierten Berufen entwickelten sich
  laut den Autoren bereits **2020** signifikant schwächer, also vor ChatGPT.
- **EY AI Survey 2026** (Mai 2026): Von **604 Befragten** (Personen, nicht Firmen) geben
  **7 %** an, ihr Unternehmen habe wegen KI Stellen abgebaut, **11 %**, Stellen würden wegen KI
  nicht mehr nachbesetzt, und **18 %**, es seien neue KI-Stellen entstanden; **42 %** können es
  nicht einschätzen. **18 %** erwarten künftig einen Abbau.
  *Einschränkung:* nicht repräsentativ (23 % aus Banken, 55 % aus Firmen mit ≥ 1'000 Mitarbeitenden).
- **jobs.ch KI Report 2026** (JobCloud, Juni 2026): Der Anteil der Inserate für Berufseinsteiger
  sank im **Gesamtmarkt** 2025 um **32 %** gegenüber dem Durchschnitt 2019–2022.
  In den KI-exponierten Kategorien (IT, Administration/HR, Banking, Marketing, Einkauf, Vertrieb)
  weist der Report für Junior-Inserate **−16 %** und für Senior-Inserate **+26 %** aus.
  *Einschränkung:* Inserate einer Plattform, keine Einstellungen; keine Werte je Kategorie.
  Die −32 % beziehen sich auf den Gesamtmarkt, nicht auf KI-exponierte Berufe — so werden sie in
  einzelnen Sekundärquellen falsch wiedergegeben. Der Report-Text spricht von einem «weitaus
  stärkeren» Rückgang in exponierten Berufen; die ausgewiesenen Werte belegen das nicht eindeutig.
- **AXA KMU-Arbeitsmarktstudie 2026** (Sotomo, Befragung März 2026): **12 %** der KMU, die KI
  nutzen, erwarten, dank KI auf Personal verzichten zu können.
  *Einschränkung:* Erwartung, keine gemessene Entwicklung; N = 336 KMU.
- **einstAIn / Angestellte Schweiz** (Juni 2026): **28 %** der Schweizer Jobs gelten als
  hoch exponiert.
  *Einschränkung:* Wie diese App eine Expositionsschätzung, keine Wirkungsmessung; der
  Schwellenwert für «hoch exponiert» ist nicht dokumentiert.
- **HSLU AI Jobs Report 2026** (Okt. 2026): Ergänzende Perspektive auf die Gegenbewegung —
  die Nachfrage nach KI-Fachkräften in Stelleninseraten wächst, vor allem für erfahrene Profile.

**Zwischenfazit Schweiz:** In stark exponierten Berufen ist ein überdurchschnittlicher Anstieg
der Arbeitslosigkeit messbar (KOF). Befragungen deuten darauf hin, dass dies weniger über breite
Entlassungen als über **Nicht-Nachbesetzung** und **weniger Einstiegsstellen** geschieht.
Ein kausaler Nachweis fehlt.
""")

st.subheader("International (nur qualitativ — Zahlen nicht auf die Schweiz übertragbar)")
st.markdown("""
- **Stanford «Canaries in the Coal Mine?»** (Brynjolfsson, Chandar & Chen, Rev. Aug. 2026):
  In den USA entwickelt sich die Beschäftigung junger Berufseinsteiger in stark exponierten Berufen
  schwächer. Die Wirkung läuft über **weniger Einstellungen junger Beschäftigter**, nicht über
  Entlassungen — vor allem dort, wo KI Tätigkeiten automatisiert statt ergänzt. Beschreibend,
  nicht kausal.
- **Federal Reserve Bank of New York** (Unternehmensumfragen 2025/26): Firmen nutzen KI
  zunehmend, reagieren aber eher mit **Umschulung und weniger Neueinstellungen** als mit
  Entlassungen.
- **The Budget Lab at Yale** (Tracker, Update Sept. 2026): Gesamtwirtschaftlich gibt es in den USA
  bisher **keine klare Evidenz** für eine Verdrängung durch KI.
- **Oxford Economics** (Jan. 2026): Die Belege für einen KI-getriebenen Umbruch sind lückenhaft.
  Manche Firmen stellen Stellenabbau als positive KI-Story dar
  («dress up layoffs as a good news story»).
- **Economic Innovation Group** (Iscenko & Curto Millet, Jan. 2026): Die Inserate in exponierten
  Berufen erreichten ihren Höchststand bereits im Frühjahr 2022, also **vor ChatGPT** — ein
  Hinweis, dass der spätere Rückgang nicht allein auf KI zurückgeht.
""")

st.divider()

# ─── Kündigungsgründe ─────────────────────────────────────────────────────────
st.header("Warum wir keine Kündigungsgründe zählen")

st.markdown("""
Naheliegend wäre, Entlassungen zu zählen, die mit KI begründet werden. Das ergibt aus mehreren
Gründen kein verlässliches Bild:

- **Verdeckte KI-Effekte:** Ein grosser Teil der Wirkung taucht in keiner Kündigung auf —
  Stellen werden nicht nachbesetzt, Einstellungen gestoppt oder Abbau wird unter
  «Restrukturierung» oder «Kostendruck» kommuniziert.
- **KI als vorgeschobener Grund:** Umgekehrt wird KI mitunter genannt, obwohl andere Ursachen
  dahinterstehen (Nachfragerückgang, Überanstellung) — gegenüber Investoren klingt KI besser.
  In den Medien wird dies als «AI washing» bezeichnet.
- **Keine Schweizer Statistik:** Für die Schweiz gibt es keine Statistik der Kündigungsgründe.
  Die oft zitierten US-Zahlen (Challenger, Gray & Christmas) beruhen auf Selbstangaben der
  Unternehmen in Abbauankündigungen.

**Unser Ansatz:** Statt Gründe zu zählen, soll die Wirkung über **Ergebnisse je Beruf** gemessen
werden — z. B. die Entwicklung der Arbeitslosen und Stellensuchenden sowie der Einstiegsinserate,
jeweils exponierte im Vergleich zu wenig exponierten Berufen. Das erfasst KI-Effekte unabhängig
davon, welcher Grund genannt wird. Dafür sind nicht-öffentliche SECO-Daten nach CH-ISCO-19
(4-stellig) nötig; der Datenbezug ist **in Abklärung** (Issue #43).
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
  **Exposition** beschreibt die technische Möglichkeit; die **beobachtete Wirkung** ist die
  tatsächlich gemessene Entwicklung auf dem Arbeitsmarkt. Beides sind getrennte Grössen.
  Bisher wirkt KI in der Schweiz nach heutigem Wissensstand vor allem über **weniger
  Einstiegsstellen** und **Nicht-Nachbesetzung**, weniger über breite Entlassungen
  (siehe «Was wir über die tatsächliche Wirkung wissen»).
- **Datenbasis 2024.** Die Beschäftigungszahlen basieren auf der BFS Strukturerhebung (SE) 2024
  (Stichprobe; Werte kleiner Berufe sind entsprechend unsicher). Die KI-Landschaft
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

- **Sprachregionen:** Die verwendete SE-Tabelle ist nicht nach Sprachregion × Beruf aufgeschlüsselt.
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
- BFS (2026). [Strukturerhebung (SE) 2024 — Ausgeübter Beruf (CH-ISCO-19) nach Geschlecht und Staatsangehörigkeit](https://www.bfs.admin.ch/bfs/de/home/statistiken/kataloge-datenbanken.assetdetail.36492006.html) · [Über die Strukturerhebung](https://www.bfs.admin.ch/bfs/de/home/statistiken/bevoelkerung/erhebungen/se.html)
- Europäische Kommission (2023). [ESCO v1.2](https://esco.ec.europa.eu)
- BFS (2022). [Lohnstrukturerhebung (LSE)](https://www.bfs.admin.ch/bfs/de/home/statistiken/arbeit-erwerb/loehne-erwerbseinkommen-arbeitskosten/lohnstruktur.html)
""")

st.subheader("Beobachtete Wirkung — Schweiz")
st.markdown("""
- Kläui, J. & Siegenthaler, M. (Okt. 2025). [KI und der Schweizer Arbeitsmarkt: Erste Evidenz zu Auswirkungen auf Arbeitslosigkeit und Stellenausschreibungen](https://doi.org/10.3929/ethz-c-000785283) — KOF Studien Nr. 186
- EY Schweiz (27.05.2026). [EY AI Survey 2026](https://www.ey.com/de_ch/newsroom/2026/05/artificial-intelligence-widely-established-in-swiss-companies-but-many-are-still-in-the-early-stages-of-scaling)
- JobCloud (Juni 2026). [jobs.ch KI Report 2026](https://www.jobcloud.ch/wp-content/uploads/2026/06/jobs.ch-KI-Report.pdf)
- AXA / Sotomo (2026). [AXA KMU-Arbeitsmarktstudie 2026](https://www.axa.ch/de/ueber-axa/medien/medienmitteilungen/aktuelle-medienmitteilungen/2026/20260915-kmu-arbeitsmarktstudie-kuenstliche-intelligenz.html)
- Derungs, C. et al. (08.10.2026). [HSLU AI Jobs Report 2026](https://www.hslu.ch/-/media/campus/common/files/dokumente/h/1-medienmitteilungen-und-news/2026/i/260922-hslu-ai-job-report-screen-def.pdf)
- einstAIn / Angestellte Schweiz (16.06.2026). [Nahezu jeder dritte Schweizer Job wegen KI unter Druck](https://angestellte.ch/medien/medienmitteilungen/nahezu-jeder-dritte-schweizer-job-wegen-ki-unter-druck)
- Lundsgaard-Hansen, C. / sparkr (Sept. 2026). [Künstliche Intelligenz und der Schweizer Arbeitsmarkt](https://sparkr.ch/wp-content/uploads/2026/09/Kuenstliche-Intelligenz-und-Schweizer-Arbeitsmarkt_sparkr_20260930.pdf)
""")

st.subheader("Beobachtete Wirkung — International")
st.markdown("""
- Iscenko, Z. & Curto Millet, F. (Jan. 2026). [Looking for the Ladder](https://eig.org/wp-content/uploads/2026/01/TAWP-Iscenko-Millet.pdf) — Economic Innovation Group
- Brynjolfsson, E., Chandar, B. & Chen, R. (12.08.2026). [Canaries in the Coal Mine?](https://digitaleconomy.stanford.edu/app/uploads/2026/08/Canaries_August2026.pdf)
- Abel, J. R. et al. (01.09.2026). [Businesses Are Using AI to Transform Work, Not Cut Jobs](https://libertystreeteconomics.newyorkfed.org/2026/09/businesses-are-using-ai-to-transform-work-not-cut-jobs/) — NY Fed
- The Budget Lab at Yale (Update 15.09.2026). [Tracking the Impact of AI on the Labor Market](https://budgetlab.yale.edu/research/tracking-impact-ai-labor-market)
- May, B. & Badawy, Y. (07.01.2026). [Evidence of an AI-driven shakeup of job markets is patchy](https://www.oxfordeconomics.com/wp-content/uploads/2026/01/Evidence-of-an-AI-driven-shakeup-of-job-markets-is-patchy.pdf) — Oxford Economics
- Challenger, Gray & Christmas (01.10.2026). [Challenger Report September 2026](https://www.challengergray.com/wp-content/uploads/2026/10/Challenger-Report-September-2026.pdf)
""")
