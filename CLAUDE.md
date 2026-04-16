# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**KI-Jobexpositions-Analyse Schweiz** — A Streamlit webapp that visualizes AI automation exposure scores for ~150 Swiss occupations, using the Karpathy/Webb methodology adapted for the Swiss labor market. Intended for public deployment on Streamlit Community Cloud.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the Streamlit app (from repo root)
streamlit run src/app/app.py

# Generate placeholder job data (no SAKE file needed)
python src/data/fetch_sake.py

# Build ESCO-enriched job list
python src/data/build_berufeliste.py

# Run scoring pipeline (requires ANTHROPIC_API_KEY in .env)
python src/scoring/exposure_scorer.py

# Generate demo scores (no API key needed)
python src/scoring/generate_demo_scores.py

# Test CH adjustments
python src/scoring/ch_adjustments.py
```

## Architecture

### Data Pipeline (run once, outputs to `data/processed/`)

```
src/data/fetch_sake.py        → data/raw/sake_berufe.xlsx → data/processed/berufe_ch.csv
src/data/fetch_esco.py        → ESCO REST API (free) → enriches job descriptions
src/data/enrich_with_esco.py  → merges SAKE + ESCO → data/processed/berufe_ch_esco.csv
src/data/build_berufeliste.py → final curated list
```

**SAKE data** must be manually downloaded from bfs.admin.ch (no public API). Place as `data/raw/sake_berufe.xlsx`. Until then, `fetch_sake.py` generates placeholder data.

### Scoring Pipeline (run once, outputs `data/processed/scores.csv`)

```
berufe_ch_esco.csv
  → exposure_scorer.py  (Claude API, claude-sonnet-4-6, ~150 calls, < 1 CHF)
  → ch_adjustments.py   (sector/salary delta applied, score clipped 0–10)
  → scores.csv
```

Scoring uses 5 weighted criteria: digital output (25%), repeatability (25%), physical presence (20%, negative), creativity (15%, negative), social interaction (15%, negative).

CH adjustments apply sector deltas (e.g. Finance +0.3, Health −0.3) and salary-bracket deltas.

Requires `ANTHROPIC_API_KEY` in `.env`.

### Streamlit App (`src/app/`)

Multi-page app; entry point is `src/app/app.py`, pages in `src/app/pages/`:

| Page | Content |
|------|---------|
| `1_Treemap.py` | All jobs as tiles; size = headcount, color = exposure score |
| `2_Matrix.py` | Scatter: X = adaptability, Y = exposure; quadrant-colored |
| `3_Branchen.py` | Sector bar chart + convergence heatmap |
| `4_Berufssuche.py` | Job search with full score breakdown |

All charts use **Plotly**. App reads from `data/processed/scores.csv` (or demo data if not yet generated).

### Key Data Columns

`scores.csv` contains: `beruf`, `isco_code`, `beschaeftigte_1000`, `frauen_anteil_pct`, `branche`, `jahresbruttolohn`, `score_gesamt`, `score_digital`, `score_wiederholbarkeit`, `score_physisch`, `score_kreativitaet`, `score_sozial`, `score_ch`, `haupt_risiko`, `zeitrahmen`, `begruendung`.
