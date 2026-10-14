---
title: KI-Jobexposition Schweiz
emoji: 💼
colorFrom: red
colorTo: gray
sdk: docker
pinned: false
tags:
  - streamlit
  - labor-market
  - ai-automation
  - switzerland
license: mit
---

# 🇨🇭 KI & Jobmarkt Schweiz

[![CI](https://github.com/minigraphx/ki-jobexposition-schweiz/actions/workflows/ci.yml/badge.svg)](https://github.com/minigraphx/ki-jobexposition-schweiz/actions/workflows/ci.yml)
[![HuggingFace Space](https://img.shields.io/badge/🤗%20HuggingFace-Live%20App-blue)](https://huggingface.co/spaces/AndyWHV/ki-jobexposition-schweiz)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Interaktive Webapp zur Exposition von **187 Schweizer Berufen** gegenüber generativer KI — aufgabenbasiert bewertet (Methode Eloundou et al. / ILO), mit amtlichen BFS-Daten für den Schweizer Arbeitsmarkt.

**👉 [Live-App auf HuggingFace Spaces](https://huggingface.co/spaces/AndyWHV/ki-jobexposition-schweiz)**

---

## Seiten

| Seite | Inhalt |
|-------|--------|
| 🗺️ Treemap | Alle 187 Berufe als Kacheln — Grösse = Erwerbstätige, Farbe = KI-Exposition, Zeitersparnis oder physische Automatisierung |
| 📊 Matrix | Exposition × Anpassungsfähigkeit — vier Quadranten, unsichere Bewertungen markiert |
| 🏭 Branchen | Branchenvergleich, Grenzgänger-Kontext, Konvergenz-Heatmap |
| 🔍 Berufssuche | Einzelberuf mit bewerteten Tätigkeiten, Werten beider Modelle und Permalink (`?beruf=…`) |
| 📖 Methodik | Rubrik, Validierung gegen ILO/Eloundou/AEI, Datenquellen, Einschränkungen |

## Methodik

Für jeden Beruf werden 8–12 Kerntätigkeiten mit ihrem Zeitanteil bestimmt und einzeln bewertet
(Rubrik v2.2, `src/scoring/rubrik/`): Kann generative KI die Zeit für die Tätigkeit bei gleicher
Qualität mindestens halbieren (Stufe E1/E2) oder nicht (E0)? Dazu Modus (ersetzend / delegierend /
unterstützend), verbleibende Restzeit und — separat — die Automatisierbarkeit mit klassischer
Technik. Zwei Modelle bewerten unabhängig, je 2–3 Läufe: **Claude Opus 5.5** (über das eigene Abo)
und **Gemini 4 Argon**.

**KI-Exposition (0–10)** = Anteil der Arbeitszeit in E1/E2-Tätigkeiten × 10, gemittelt über alle
Läufe. Weichen Modelle oder Läufe um mehr als 1 Punkt ab, gilt die Bewertung als unsicher. Der
Zeitrahmen wird je Branche mit dem KMU-Faktor (BFS STATENT) verschoben; einen Lohn- oder
Branchenzuschlag auf den Score gibt es nicht. Pipeline: `task_scorer.py` → `task_aggregate.py` →
`apply_task_scores.py` (Anleitung: `docs/neubewertung_lokal.md`).

Datenquellen: BFS Strukturerhebung (SE) 2024 · ESCO v1.2.1 · BFS LSE 2024 / Salarium · BFS STATENT 2024 · BFS Grenzgängerstatistik.

## Lokale Entwicklung

```bash
# Repository klonen
git clone https://github.com/minigraphx/ki-jobexposition-schweiz.git
cd ki-jobexposition-schweiz

# Virtuelle Umgebung & Abhängigkeiten
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# App starten
streamlit run src/app/app.py

# Tests ausführen
pytest tests/ -v --cov=src/scoring
```

## Projektstruktur

```
├── src/
│   ├── app/              # Streamlit-App (6 Seiten)
│   │   └── pages/
│   ├── data/             # Datenpipeline (BFS, ESCO), Spalten-Mapping
│   └── scoring/          # Aufgabenbasierte Bewertung, KMU-Faktor, Anpassungsfähigkeit
├── data/processed/       # Aufbereitete Daten (scores.csv, Bewertungen unter bewertungen/)
├── tests/                # pytest, Coverage ≥ 80 %
├── Dockerfile            # HuggingFace Spaces Deployment
└── requirements.txt      # Produktionsabhängigkeiten
```

## Datenquellen

- **BFS Strukturerhebung (SE) 2024** — Erwerbstätige und Frauenanteil pro Beruf (CH-ISCO-19, 4-stellige Berufsgattung bzw. 5-stellige Berufsart; jede Gattung zählt genau einmal, siehe `docs/audit_isco_codes.md`)
- **ESCO v1.2.1** — Berufsbeschreibungen und Kompetenzen (© Europäische Union, CC BY 4.0; Beschreibungen ggf. gekürzt/angepasst)
- **BFS LSE 2024** (T17) — Medianlöhne nach 2-stelliger ISCO-Gruppe, für heterogene Gruppen mit BFS Salarium differenziert

## Lizenz

MIT — Details in [LICENSE](LICENSE).
