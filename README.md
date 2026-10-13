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

Interaktive Webapp zur KI-Automatisierungsexposition von **204 Schweizer Berufen** — basierend auf der Methodik von Andrej Karpathy, adaptiert für den Schweizer Arbeitsmarkt.

**👉 [Live-App auf HuggingFace Spaces](https://huggingface.co/spaces/AndyWHV/ki-jobexposition-schweiz)**

---

## Seiten

| Seite | Inhalt |
|-------|--------|
| 🗺️ Treemap | Alle 204 Berufe als Kacheln — Grösse = Beschäftigte, Farbe = KI-Score |
| 📊 Matrix | Exposition × Anpassungsfähigkeit — vier Quadranten |
| 🏭 Branchen | Branchenvergleich und Webb-Konvergenz-Heatmap |
| 🔍 Berufssuche | Einzelberuf mit Radar-Chart und Permalink (`?beruf=…`) |
| 📖 Methodik | Datenquellen, Scoring-Logik, Einschränkungen |

## Methodik

Für jeden Beruf bewertet **Claude (claude-sonnet-4-6)** fünf Kriterien (je 0–10):

| Kriterium | Gewicht |
|-----------|---------|
| Digitaler Output | 25 % |
| Wiederholbarkeit | 25 % |
| Physische Präsenz | 20 % (negativ) |
| Kreativität | 15 % (negativ) |
| Soziale Interaktion | 15 % (negativ) |

Auf den Rohscore werden **Schweiz-spezifische Anpassungen** angewendet (Branche, Lohnklasse). Datenquellen: BFS Strukturerhebung (SE) 2024 · ESCO v1.2 · BFS LSE 2024.

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
│   ├── data/             # Datenpipeline (BFS, ESCO)
│   └── scoring/          # KI-Scoring & CH-Anpassungen
├── data/processed/       # Aufbereitete Daten (scores.csv)
├── tests/                # pytest, Coverage ≥ 80 %
├── Dockerfile            # HuggingFace Spaces Deployment
└── requirements.txt      # Produktionsabhängigkeiten
```

## Datenquellen

- **BFS Strukturerhebung (SE) 2024** — Erwerbstätige und Frauenanteil pro Beruf (CH-ISCO-19, 4-stellig)
- **ESCO v1.2** — Berufsbeschreibungen (Europäische Kommission)
- **BFS LSE 2024** (T17) — Medianlöhne nach 2-stelliger ISCO-Gruppe, für heterogene Gruppen mit BFS Salarium differenziert

## Lizenz

MIT — Details in [LICENSE](LICENSE).
