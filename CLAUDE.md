# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

**KI-Jobexpositions-Analyse Schweiz** — A Streamlit webapp that visualizes AI automation
exposure scores for **204 Swiss occupations**, using the Karpathy/Webb methodology adapted
for the Swiss labor market. Deployed on **HuggingFace Spaces**.

- HuggingFace: `https://huggingface.co/spaces/AndyWHV/ki-jobexposition-schweiz`
- GitHub: `https://github.com/minigraphx/ki-jobexposition-schweiz`

## Commands

```bash
# Use the project's virtual environment
source .venv/bin/activate   # or: .venv/bin/python for one-off calls

# Run the Streamlit app (from repo root)
streamlit run src/app/app.py

# --- Data Pipeline (run once) ---
python src/data/update_from_bfs.py       # Load & process BFS SAKE Excel
python src/data/enrich_with_esco.py      # Fetch ESCO descriptions via API
python src/data/verify_esco_matches.py   # Validate & fix ESCO matches
python src/data/patch_unmatched.py       # Manual patches for bad matches

# --- Scoring Pipeline (requires ANTHROPIC_API_KEY in .env) ---
python src/scoring/exposure_scorer.py    # Claude Batch API scoring (all 204 jobs)
python src/scoring/adaptability_scorer.py  # Compute adaptability scores
python src/scoring/ch_adjustments.py    # Apply CH-specific deltas

# --- Tests ---
pytest tests/ -v
pytest tests/ --cov=src --cov-report=term-missing
```

## Architecture

### Data Pipeline (outputs to `data/processed/`)

```
data/raw/sake_berufe_ch_isco19.xlsx   (manually downloaded from bfs.admin.ch)
  → src/data/update_from_bfs.py
  → data/processed/berufe_ch.csv          (204 jobs, ISCO codes, headcount, wages)

berufe_ch.csv
  → src/data/enrich_with_esco.py
  → data/processed/berufe_ch_esco.csv     (+ ESCO URI + description)

berufe_ch_esco.csv
  → src/data/verify_esco_matches.py
  → data/processed/berufe_ch_esco_verified.csv  (+ match_score 0/1/2)
```

**SAKE data** downloaded from:
`https://www.bfs.admin.ch/bfs/de/home/statistiken/kataloge-datenbanken.assetdetail.36492006.html`

### Scoring Pipeline (outputs `data/processed/scores.csv`)

```
berufe_ch_esco_verified.csv
  → exposure_scorer.py      (Claude Batch API, claude-sonnet-4-6, ~204 calls, < 2 CHF)
  → adaptability_scorer.py  (rule-based: education, wage, digital affinity, mobility)
  → ch_adjustments.py       (sector/salary deltas, score clipped 0–10)
  → scores.csv
```

Scoring criteria: digital output (25%), repeatability (25%), physical presence (20% neg.),
creativity (15% neg.), social interaction (15% neg.).

CH deltas: Finance +0.3, Health −0.3, high wages (>120k CHF) +0.2, etc.

### Streamlit App (`src/app/`)

Entry point: `src/app/app.py` — uses `st.navigation()` for multi-page routing.
Pages in `src/app/pages/`:

| File | Menu Title | Content |
|------|-----------|---------|
| `0_Startseite.py` | Startseite | Landing page, key metrics, navigation |
| `1_Treemap.py` | Treemap | All jobs as tiles; size = headcount, color = score |
| `2_Matrix.py` | Matrix | Scatter: X = adaptability, Y = exposure; quadrant-colored |
| `3_Branchen.py` | Branchen | Sector bar chart + Webb convergence heatmap |
| `4_Berufssuche.py` | Berufssuche | Job search with full score breakdown + radar chart |
| `5_Methodik.py` | Methodik & Quellen | Methodology, data sources, limitations |

All charts use **Plotly**. App reads from `data/processed/scores.csv`.

### Key Data Columns in `scores.csv`

| Column | Type | Description |
|--------|------|-------------|
| `beruf` | str | German job title |
| `isco_code` | int | ISCO-08 / CH-ISCO-19 code |
| `beschaeftigte_1000` | float | Employed persons in thousands (BFS SAKE 2024) |
| `frauen_pct` | float | Share of women in percent (0–100) |
| `branche` | str | Sector (21 categories) |
| `lohn_median_chf` | int | Median annual gross salary CHF (BFS LSE 2022) |
| `qualifikation` | str | Education level: Tertiär / Sekundär II / Keine Ausbildung |
| `esco_uri` | str | ESCO occupation URI |
| `esco_titel` | str | ESCO occupation title (German) |
| `esco_beschreibung` | str | ESCO occupation description (German) |
| `score_gesamt` | float | Raw AI exposure score 0–10 (Claude API) |
| `score_digital` | float | Sub-score: digital output |
| `score_wiederholbarkeit` | float | Sub-score: repeatability |
| `score_physisch` | float | Sub-score: physical presence (inverted) |
| `score_kreativitaet` | float | Sub-score: creativity (inverted) |
| `score_sozial` | float | Sub-score: social interaction (inverted) |
| `haupt_risiko` | str | Main automation risk description |
| `zeitrahmen` | str | Estimated time horizon |
| `begruendung` | str | 2–3 sentence justification |
| `delta_branche` | float | CH sector adjustment |
| `delta_lohn` | float | CH wage-level adjustment |
| `score_ch` | float | Final CH-adjusted score 0–10 |
| `adaptabilitaet` | float | Adaptability score 0–10 |

## Deployment (HuggingFace Spaces)

```bash
# Push to HuggingFace (Streamlit Space)
git push hf main

# The HF remote URL contains credentials — do NOT display or log it
# Remote is named 'hf', see: git remote -v
```

HuggingFace Spaces runs `streamlit run src/app/app.py` automatically.
`data/processed/scores.csv` is committed and available at runtime (no DB needed).

## Security Notes

- `.env` is in `.gitignore` — never commit it
- `ANTHROPIC_API_KEY` is only needed for re-scoring, not for running the app
- HF token is embedded in the `hf` remote URL — do not echo `git remote -v` in logs
