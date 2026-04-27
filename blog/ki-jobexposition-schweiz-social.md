# Begleittexte & Veröffentlichungs-Vorbereitung

Ergänzung zum Blogpost `ki-jobexposition-schweiz.md`.

---

## Social Media Begleittexte

### LinkedIn (~350 Wörter, professioneller Ton)

---

**Welche Schweizer Berufe sind wirklich von KI exponiert — und welche nicht?**

Fast jede Diskussion über KI und Arbeitsplätze in der Schweiz stützt sich auf US-amerikanische
oder globale Studien: Goldman Sachs, McKinsey, WEF. Was in diesen Zahlen nicht vorkommt:
das duale Bildungssystem, die Lohnstruktur des Schweizer Finanzplatzes, der Fachkräftemangel
in der Pflege oder die Rolle von Gesamtarbeitsverträgen beim Tempo der Automatisierung.

Die KOF ETH Zürich hat im Oktober 2025 erstmals empirisch gezeigt, dass KI bereits
konkrete Spuren auf dem Schweizer Arbeitsmarkt hinterlässt — mit einem 27 % stärkeren
Anstieg an Stellensuchenden in stark exponierten Berufen seit Ende 2022. Betroffen:
vor allem Software-Entwickler:innen, Journalist:innen und Fachleute in Marketing und Werbung.

Ich habe ein offenes Tool gebaut, das für **204 Schweizer Berufe** einen nachvollziehbaren
Expositionsscore liefert — basierend auf BFS-Daten, der europäischen ESCO-Klassifikation
und einem transparent dokumentierten Scoring-Modell.

Zwei Beispiele aus den Daten:

- **Sachbearbeiter/in Buchhaltung** — Score 8.5, Zeitrahmen 3–5 Jahre. ERP-Systeme und
  KI-gestützte Belegerfassung automatisieren bereits grosse Teile der Routine.
- **Diplomierte Pflegefachperson** — Score 1.8, rund 130'000 Beschäftigte. Körperlich-
  empathische Betreuung lässt sich nicht automatisieren; KI entlastet eher Dokumentation.

Das Tool ist kein Orakel. Ein hoher Score bedeutet nicht, dass ein Beruf verschwindet —
er bedeutet, dass viele der heutigen Tätigkeiten technisch grundsätzlich für KI-
Unterstützung geeignet sind. Ob und wann sich das in echten Veränderungen am Arbeitsmarkt
niederschlägt, hängt von Regulierung, Sozialpartnerschaft und Investitionsentscheiden ab.

Die Daten, der Code und die vollständige Methodik sind öffentlich — damit die Diskussion
über konkrete Berufe und konkrete Massnahmen geführt werden kann, statt zwischen Panik
und Beschwichtigung zu pendeln.

👉 Tool: https://huggingface.co/spaces/AndyWHV/ki-jobexposition-schweiz
📄 Methodik & Code: https://github.com/minigraphx/ki-jobexposition-schweiz

Feedback, Korrekturen und Branchen-Expertise sind ausdrücklich willkommen.

#KI #Arbeitsmarkt #Schweiz #Automatisierung #Berufe #OpenSource

---

### X / Twitter (Thread, 6 Tweets)

---

**Tweet 1 (Hook):**
Welche Schweizer Berufe sind wirklich von KI exponiert? Fast alle Studien dazu stammen
aus den USA — ich habe versucht, das mit Schweizer Zahlen zu unterfüttern. 🧵

**Tweet 2 (Problem):**
Goldman Sachs, McKinsey, WEF — grosse Zahlen, aber nicht auf die Schweiz gerechnet.
Kein duales Bildungssystem, keine CH-Lohnstruktur, keine Gesamtarbeitsverträge.
Die KOF ETH hat Oktober 2025 erstmals eigene Empirie geliefert.

**Tweet 3 (Tool):**
Ergebnis: KI-Jobexposition Schweiz — 204 Berufe, nachvollziehbarer Score 0–10,
offen dokumentierte Methodik. Gebaut auf BFS SAKE 2024, ESCO und BFS LSE 2022.
Jeder Score hat eine Begründung.

**Tweet 4 (Beispiele):**
Stark exponiert: Sachbearbeiter/in Buchhaltung (8.5), Übersetzer/in (7.3)
Schwach exponiert: Coiffeur/in EFZ (1.6), Dipl. Pflegefachperson (1.8)
→ 130'000 Pflegefachpersonen: KI entlastet eher, als dass sie verdrängt.

**Tweet 5 (Grenzen):**
Was das Tool *nicht* ist: kein Orakel, keine Berufsempfehlung. Ein Score ist
ein Einstieg in ein Gespräch — keine Grundlage für Kündigung oder Berufswahl.
Regulierung, Sozialpartnerschaft und GAV modelliert es nicht.

**Tweet 6 (CTA):**
Tool: https://huggingface.co/spaces/AndyWHV/ki-jobexposition-schweiz
Code & Methodik: https://github.com/minigraphx/ki-jobexposition-schweiz
Kritik, Korrekturen, Branchen-Expertise willkommen — gerne hier oder via GitHub Issues.

---

### Newsletter (120 Wörter, persönlicher Ton)

---

**Schweizer Berufe und KI — endlich eigene Zahlen**

Fast alle Studien zu KI und Arbeitsplätzen rechnen für die USA. Ich habe versucht,
das für die Schweiz nachzubauen: 204 Berufe aus der BFS-Arbeitskräfteerhebung,
bewertet nach fünf Kriterien, mit Schweizer Branchen- und Lohnanpassungen.

Zwei Befunde, die mich überrascht haben: Software-Entwickler:innen sind laut
KOF-Studie (Oktober 2025) unter den am stärksten betroffenen Berufen — nicht
die sicherste Wette, wie lange angenommen. Und 130'000 diplomierte Pflegefachpersonen
haben einen Score von 1.8 — KI entlastet hier, verdrängt nicht.

Das Tool ist offen, die Methodik dokumentiert, Kritik willkommen.

→ https://huggingface.co/spaces/AndyWHV/ki-jobexposition-schweiz

---

## Bild- und Grafik-Vorschläge

Folgende Screenshots / Grafiken sollten vor der Veröffentlichung erstellt werden:

| # | Beschreibung | Wo im Artikel | Hinweis |
|---|---|---|---|
| 1 | **Treemap-Screenshot** — alle 204 Berufe sichtbar, Zoom auf einige Extremfälle | Nach «Was das Tool macht» | Im Tool: Treemap-Tab öffnen, Vollbild-Screenshot |
| 2 | **Radar-Chart** für Sachbearbeiter/in Buchhaltung | Im Abschnitt «Vier Beispiele» | In der Berufssuche des Tools exportieren oder Screenshot |
| 3 | **Matrix-View** (Exposition × Anpassungsfähigkeit) — 4 Quadranten sichtbar | Alternativ nach Beispielen | Matrix-Tab im Tool |
| 4 | **Score-Verteilung** (Histogramm 0–10) — zeigt, dass die meisten Berufe im mittleren Bereich liegen | Optional in der Methodik-Sektion | Via `scores.csv` mit Python/Plotly/Matplotlib generieren |

**Vorgeschlagene Alt-Texte:**
- Bild 1: `Treemap aller 204 Schweizer Berufe nach KI-Expositionsscore — Grösse entspricht Beschäftigtenzahl, Farbe dem Score (rot = hoch, grün = niedrig)`
- Bild 2: `Radar-Chart Sachbearbeiter/in Buchhaltung: hohe Scores bei digitalem Output und Wiederholbarkeit, niedrig bei physischer Präsenz`
- Bild 3: `Matrix: KI-Exposition (Y-Achse) gegen Anpassungsfähigkeit (X-Achse) — vier Quadranten`

---

## Veröffentlichungs-Checkliste

Vor der Publikation folgende Punkte prüfen:

### Pflichtprüfungen

- [ ] **HuggingFace Space** erreichbar: https://huggingface.co/spaces/AndyWHV/ki-jobexposition-schweiz
- [ ] **GitHub Repo** erreichbar: https://github.com/minigraphx/ki-jobexposition-schweiz
- [ ] **EU AI Act** (EUR-Lex): https://eur-lex.europa.eu/eli/reg/2024/1689/oj
- [ ] **revDSG** (Fedlex): https://www.fedlex.admin.ch/eli/cc/2022/491/de
- [ ] **BFS SAKE**: https://www.bfs.admin.ch/bfs/de/home/statistiken/arbeit-erwerb/erhebungen/sake.html
- [ ] **ESCO**: https://esco.ec.europa.eu/de

### Schweizer Medien-URLs (liefern meist 403 bei direktem Fetch — im Browser prüfen)

- [ ] Blick: https://www.blick.ch/wirtschaft/grosse-studie-zur-ki-revolution-mehr-als-jeder-zweite-schweizer-fuerchtet-sich-vor-job-verlust-id19927518.html
- [ ] 20 Minuten: https://www.20min.ch/story/duesteres-szenario-ki-koryphaee-warnt-vor-80-prozent-arbeitslosigkeit-103464159
- [ ] NZZ: https://www.nzz.ch/wirtschaft/kof-studie-ki-veraendert-den-schweizer-arbeitsmarkt-dramatisch-ld.1905520

### Akademische/institutionelle Quellen

- [ ] KOF ETH: https://kof.ethz.ch/news-und-veranstaltungen/kof-news/2025/10/kuenstliche-intelligenz-hinterlaesst-deutliche-spuren-auf-dem-schweizer-arbeitsmarkt.html
- [ ] Avenir Suisse: https://www.avenir-suisse.ch/publication/zukunftssichere-berufe/
- [ ] PwC: https://www.pwc.ch/de/presse/AI_Jobs_Barometer_2025.html
- [ ] WEF: https://reports.weforum.org/docs/WEF_Future_of_Jobs_Report_2025.pdf
- [ ] IMF: https://www.imf.org/-/media/files/publications/sdn/2024/english/sdnea2024001.pdf
- [ ] arXiv Eloundou: https://arxiv.org/abs/2303.10130
- [ ] SSRN Webb: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3482150
- [ ] KOF «richer»: https://kof.ethz.ch/en/publications/kof-insights/articles/2025/12/i-expect-ai-to-make-us-all-richer.html

### Inhaltliche Endprüfung

- [ ] Score-Werte der 4 Beispielberufe in `data/processed/scores.csv` nochmals verifiziert
- [ ] Alle Zahlen (27 %, 20'000 Stellen, 130'000 Beschäftigte) mit Quellen abgeglichen
- [ ] Schreibweise konsistent: «KI» (nicht «AI»), «KI-Exposition», «Expositionsscore»
- [ ] Kein Plural-s bei Berufsbezeichnungen im Generischen (Tool verwendet offizielle BFS-Schreibweise)
- [ ] Fussnoten vollständig und nummeriert im Markdown korrekt gerendert (Vorschau im Browser testen)

### Formales

- [ ] YAML Frontmatter: `date` auf Publikationstag anpassen
- [ ] Tags vollständig und korrekt: `[KI, Arbeitsmarkt, Schweiz, Datenanalyse, Automatisierung]`
- [ ] Bilder vorhanden (siehe Grafik-Vorschläge oben) und Alt-Texte gesetzt
- [ ] Artikel-URL (Slug) festgelegt — Vorschlag: `ki-jobexposition-schweiz`
