# Entwicklungskonzept: KI-Jobexpositions-Analyse Schweiz

**Version:** 0.1
**Datum:** 2026-04-01
**Ausgabeformat:** Interaktive Streamlit-Webapp (öffentlich publizierbar)

---

## 1. Projektziel

Replizierung des Karpathy/Webb-Ansatzes zur KI-Jobexposition, angepasst auf den **Schweizer Arbeitsmarkt**. Die Webapp soll zeigen, welche Berufe und Branchen in der Schweiz am stärksten von KI-Automatisierung betroffen sind – unter Berücksichtigung CH-spezifischer Faktoren.

### Kernfragen
- Welche Schweizer Berufe haben den höchsten KI-Expositions-Score?
- Welche Branchen werden durch mehrere technologische Wellen gleichzeitig getroffen?
- Welche Berufsgruppen sind besonders vulnerabel (hohe Exposition + geringe Anpassungsfähigkeit)?

---

## 2. Datenquellen

### 2.1 Arbeitsmarktdaten Schweiz
| Quelle | Inhalt | Format | URL |
|--------|--------|--------|-----|
| BFS SAKE | Schweizerische Arbeitskräfteerhebung – Beschäftigte nach Beruf | CSV/Excel | bfs.admin.ch |
| BFS LSE | Lohnstrukturerhebung – Löhne nach Beruf und Branche | CSV/Excel | bfs.admin.ch |
| SECO | Arbeitslosenstatistik nach Berufsgruppe | CSV | seco.admin.ch |
| BFS | Erwerbstätige nach Wirtschaftsabschnitt (NOGA) | CSV/Excel | bfs.admin.ch |

### 2.2 Berufsbeschreibungen für Scoring
| Quelle | Inhalt | Format |
|--------|--------|--------|
| ESCO v1.2 | 3'000+ Berufe mit Beschreibungen (DE/FR/IT) | CSV/JSON (API) |
| BERUFENET (D) | Detaillierte Tätigkeitsbeschreibungen | Web-Scraping |
| CH-spezifisch | Berufsbilder SBBK (Schweizer Berufsbildung) | PDF/Web |

### 2.3 Referenzstudien (für Methodenvalidierung)
- Karpathy Treemap: 342 US-Berufe, O*NET-Daten + LLM-Scoring
- Brookings/GovAI: Exposition vs. Anpassungsfähigkeit
- Amy Webb Convergence Outlook 2026

---

## 3. Methodik

### 3.1 Schritt 1: Berufsliste aufbauen (Top 150–200 CH-Berufe)
```
SAKE-Daten → Berufe nach Beschäftigtenzahl sortieren → Top 200
→ Mapping auf ISCO-08 (internationale Klassifikation)
→ Matching mit ESCO-IDs für Berufsbeschreibungen
```

**Zielstruktur pro Beruf:**
- Berufsbezeichnung (DE + FR)
- ISCO-08 Code
- Beschäftigtenzahl CH
- Branche (NOGA-Abschnitt)
- Durchschnittslohn (LSE)
- Frauenanteil

### 3.2 Schritt 2: KI-Expositions-Scoring via Claude API
**Prompt-Logik (pro Beruf):**
```
Berufsbeschreibung (ESCO) → Claude Sonnet 4.6 → Score 0-10 + Begründung
```

**Scoring-Kriterien (nach Karpathy):**
| Kriterium | Gewichtung | Beschreibung |
|-----------|-----------|--------------|
| Digitaler Output | 25% | Arbeitet der Beruf primär mit digitalen Informationen? |
| Wiederholbarkeit | 25% | Sind die Aufgaben strukturiert und vorhersehbar? |
| Physische Präsenz | 20% | Erfordert der Beruf körperliche Anwesenheit? (negativ) |
| Kreativität | 15% | Erfordert der Beruf originelles Denken? (negativ) |
| Soziale Interaktion | 15% | Erfordert der Beruf Empathie/Vertrauen? (negativ) |

**Output pro Beruf:**
```json
{
  "beruf": "Buchhalter/in",
  "isco_code": "2411",
  "score": 8.2,
  "begruendung": "...",
  "haupt_risiko": "Automatische Buchführung, Steuertools",
  "zeitrahmen": "2-4 Jahre"
}
```

### 3.3 Schritt 3: Anpassungsfähigkeit (Brookings-Methode)
**Kriterien:**
- Bildungsniveau (je höher, desto anpassungsfähiger)
- Digitale Grundkompetenzen im Berufsbild
- Branchenmobilität (wie leicht ist ein Wechsel?)
- Lohn (höhere Löhne = mehr Ressourcen zur Umschulung)

**Matrix-Output:**
```
Hoch exponiert + Niedrige Anpassungsfähigkeit → ROT (kritisch)
Hoch exponiert + Hohe Anpassungsfähigkeit    → GELB (transformierend)
Niedrig exponiert + Niedrige Anpassungsfähigkeit → GRAU (stabil/stagnierend)
Niedrig exponiert + Hohe Anpassungsfähigkeit    → GRÜN (sicher)
```

### 3.4 Schritt 4: CH-spezifische Adjustierungen
Die Rohscores werden mit CH-Faktoren gewichtet:

| Faktor | Effekt auf Score | Begründung |
|--------|-----------------|------------|
| Sehr hohe CH-Löhne | Score +0.5 | Stärkerer Automatisierungsdruck |
| GAV-Abdeckung | Score -0.3 | Verlangsamt Strukturwandel |
| KMU-Dominanz | Score -0.2 | Langsamere Adoptionsrate |
| Fachkräftemangel | Score -0.4 | Automatisierung als Lösung, nicht Bedrohung |
| Grenzgänger-Konkurrenz | Kontext | In bestimmten Grenzregionen relevant |

---

## 4. Projektstruktur

```
Jobmarkt - Schweiz/
├── ENTWICKLUNGSKONZEPT.md       ← dieses Dokument
├── README.md
├── requirements.txt
├── .gitignore
│
├── src/
│   ├── data/
│   │   ├── fetch_sake.py        ← BFS SAKE Daten laden
│   │   ├── fetch_esco.py        ← ESCO Berufsbeschreibungen
│   │   └── prepare_jobs.py      ← Berufsliste aufbauen + ISCO-Mapping
│   │
│   ├── scoring/
│   │   ├── exposure_scorer.py   ← Claude API Scoring-Pipeline
│   │   ├── adaptability.py      ← Anpassungsfähigkeits-Score
│   │   └── ch_adjustments.py    ← CH-spezifische Korrekturen
│   │
│   ├── analysis/
│   │   ├── sector_analysis.py   ← Branchenanalyse (Webb-Methode)
│   │   └── convergence.py       ← Technologie-Konvergenz-Matrix
│   │
│   └── app/
│       ├── app.py               ← Streamlit Haupt-App
│       ├── pages/
│       │   ├── 1_Treemap.py     ← Karpathy-Treemap Schweiz
│       │   ├── 2_Matrix.py      ← Exposition × Anpassungsfähigkeit
│       │   ├── 3_Branchen.py    ← Branchenanalyse
│       │   └── 4_Berufssuche.py ← Einzelberuf-Detail
│       └── components/
│           └── charts.py        ← Wiederverwendbare Plotly-Charts
│
├── data/
│   ├── raw/                     ← Rohdaten (BFS, ESCO, SECO)
│   └── processed/               ← Berechnete Scores, fertige Datasets
│
└── notebooks/
    ├── 01_daten_exploration.ipynb
    ├── 02_scoring_test.ipynb
    └── 03_visualisierung_prototyp.ipynb
```

---

## 5. Entwicklungsphasen

### Phase 1: Datenbasis (Woche 1–2)
**Ziel:** Saubere Berufsliste mit 150–200 CH-Berufen

- [ ] SAKE-Daten vom BFS herunterladen und parsen
- [ ] ESCO API einbinden (kostenlos, REST)
- [ ] ISCO-08 ↔ ESCO Mapping erstellen
- [ ] Lohndaten (LSE) integrieren
- [ ] Berufsliste als `data/processed/berufe_ch.csv` abspeichern

**Deliverable:** `berufe_ch.csv` mit ~150 Berufen, Beschäftigtenzahlen, Löhnen

---

### Phase 2: Scoring-Pipeline (Woche 2–3)
**Ziel:** KI-Expositions-Scores für alle Berufe

- [ ] Claude API Setup (Anthropic SDK)
- [ ] Prompt-Template entwickeln und testen (10 Berufe manuell)
- [ ] Batch-Scoring aller Berufe (~150 API Calls)
- [ ] Ergebnisse validieren (Plausibilitätscheck)
- [ ] Anpassungsfähigkeits-Score berechnen
- [ ] CH-Adjustierungen anwenden

**Deliverable:** `data/processed/scores.csv`

**Kostenschätzung:** ~150 Berufe × ~1000 Tokens = ~150K Tokens ≈ < 1 CHF

---

### Phase 3: Branchenanalyse (Woche 3)
**Ziel:** Webb-ähnliche Konvergenzanalyse für CH-Branchen

- [ ] 10–12 Schlüsselbranchen definieren (nach NOGA)
- [ ] Technologie-Konvergenz-Matrix aufbauen
- [ ] Priorität: Finanz/Versicherung, Verwaltung, Gesundheit, Industrie/MEM

**CH-Fokus-Branchen:**
1. Finanz- und Versicherungsdienstleistungen (Bankplatz CH)
2. Öffentliche Verwaltung
3. Gesundheits- und Sozialwesen
4. Industrie (Pharma, MEM, Uhren)
5. Detailhandel
6. ICT / Telekommunikation
7. Bildungswesen
8. Freiberufliche/technische Dienstleistungen

---

### Phase 4: Streamlit-App (Woche 4–5)
**Ziel:** Publizierbare, interaktive Webapp

**Seiten:**

**1. Treemap** (Hauptseite)
- Alle ~150 Berufe als Kacheln
- Grösse = Beschäftigtenzahl, Farbe = Expositions-Score
- Hover: Berufsdetails, Score-Begründung
- Filter: Branche, Qualifikation, Lohnklasse

**2. Matrix: Exposition × Anpassungsfähigkeit**
- X-Achse: Anpassungsfähigkeit (0–10)
- Y-Achse: KI-Exposition (0–10)
- Punkt = Beruf, Grösse = Beschäftigtenzahl
- Quadranten farblich markiert

**3. Branchenanalyse**
- Horizontal Bar Chart: Branchen nach Ø-Score
- Konvergenz-Heatmap (Branchen × Technologiewellen)

**4. Beruf-Detail**
- Suchfeld: Beruf eingeben
- Vollständige Analyse: Score, Begründung, Vergleich, Trends

---

### Phase 5: Publikation (Woche 5–6)
- [ ] Streamlit Community Cloud Deployment
- [ ] Artikel-Text als Begleitung (ainauten.com-Stil)
- [ ] Datenquellen und Methodik transparent dokumentieren
- [ ] Social-Media Assets (Treemap als statisches PNG)

---

## 6. Technologie-Stack

| Komponente | Technologie |
|-----------|-------------|
| Datenverarbeitung | Python, Pandas, NumPy |
| API-Calls | `anthropic` SDK, `requests` |
| Visualisierung | Plotly Express, Plotly Graph Objects |
| Webapp | Streamlit |
| Deployment | Streamlit Community Cloud |
| Datenhaltung | CSV/Parquet (kein DB nötig) |
| Versionskontrolle | Git |

---

## 7. Risiken & Mitigationen

| Risiko | Wahrscheinlichkeit | Mitigation |
|--------|-------------------|------------|
| SAKE-Daten nicht granular genug | Mittel | ESCO als Fallback, manuelle Ergänzung |
| LLM-Scoring inkonsistent | Mittel | Prompt-Tuning, Mehrfach-Sampling, manuelle Kalibrierung |
| ESCO-Mapping unvollständig | Mittel | BERUFENET als Ergänzung |
| Politische Sensitivität | Niedrig | Klare Methodentransparenz, Exposition ≠ Jobverlust betonen |

---

## 8. Nächste Schritte (sofort)

1. **Python-Umgebung einrichten** → `requirements.txt` installieren
2. **SAKE-Daten holen** → bfs.admin.ch, Tabelle "Erwerbstätige nach Beruf"
3. **ESCO-API testen** → `https://esco.ec.europa.eu/api/resource/occupation`
4. **Ersten Scoring-Test** → 5 Berufe manuell mit Claude scoren
5. **Streamlit-Skeleton** → App-Grundgerüst aufsetzen

---

## 9. Offene Entscheidungen

- [ ] Sprache der App: Deutsch oder Englisch?
- [ ] Sollen FR/IT-Berufsbezeichnungen auch angezeigt werden?
- [ ] Vergleich CH vs. DACH optional einbauen?
- [ ] Datenstand: Welches Jahr als Referenz (aktuellstes verfügbar)?
