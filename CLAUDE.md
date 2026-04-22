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

# --- Data Pipeline (run once, in order) ---
python src/data/update_from_bfs.py          # BFS SAKE Excel → berufe_ch.csv
python src/data/enrich_with_esco.py         # ESCO API → berufe_ch_esco.csv  [LOCAL ONLY]
python src/data/verify_esco_matches.py      # validate matches → berufe_ch_esco_verified.csv
python src/data/patch_unmatched.py          # manual fixes for bad matches

# Fix known wrong ESCO matches (re-run locally after adding to KNOWN_WRONG_MATCHES):
python src/data/enrich_with_esco.py --fix-wrong
# Test a single job:
python src/data/enrich_with_esco.py --job "Bankkaufmann/-frau"

# --- Scoring Pipeline (requires ANTHROPIC_API_KEY in .env) ---
python src/scoring/exposure_scorer.py       # Claude Batch API, all 204 jobs
python src/scoring/adaptability_scorer.py   # rule-based adaptability scores
python src/scoring/ch_adjustments.py        # CH sector/salary deltas → scores.csv

# --- Quality Assurance (run as needed) ---
python src/data/full_quality_audit.py       # Haiku audit + Sonnet re-score wrong descriptions

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
  → src/data/enrich_with_esco.py          [requires local ESCO API access]
  → data/processed/berufe_ch_esco.csv     (+ ESCO URI + description)

berufe_ch_esco.csv
  → src/data/verify_esco_matches.py
  → data/processed/berufe_ch_esco_verified.csv  (+ match_score 0/1/2)
  note: only covers the 107 jobs that had a valid match; 97 jobs have no ESCO URI
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

CH sector deltas: Finance +0.3, Insurance +0.4, ICT −0.2, Health −0.3, Education −0.2,
Public admin +0.1, Industry −0.1, Retail +0.2, Legal +0.2.

CH wage deltas: <60k CHF −0.2, 60–100k 0.0, 100–150k +0.2, >150k +0.4.

### Script Reference

| Script | Input | Output | Notes |
|--------|-------|--------|-------|
| `src/data/update_from_bfs.py` | `data/raw/sake_berufe_ch_isco19.xlsx` | `berufe_ch.csv` | BFS SAKE 2024, sheet "2024", 4-digit ISCO groups |
| `src/data/enrich_with_esco.py` | `berufe_ch.csv` | `berufe_ch_esco.csv` | **Must run locally** (ESCO API blocked in cloud); 6-stage search with Haiku validation |
| `src/data/verify_esco_matches.py` | `berufe_ch_esco.csv` | `berufe_ch_esco_verified.csv` | Haiku-based match quality scoring 0/1/2 |
| `src/data/patch_unmatched.py` | `berufe_ch_esco_verified.csv` | `berufe_ch_esco_verified.csv` | Manual overrides for known bad matches |
| `src/scoring/exposure_scorer.py` | `berufe_ch_esco_verified.csv` | `scores.csv` (partial) | Claude Batch API, async, ~204 jobs |
| `src/scoring/adaptability_scorer.py` | `scores.csv` | `scores.csv` | Rule-based: education, wage, digital affinity, mobility |
| `src/scoring/ch_adjustments.py` | `scores.csv` | `scores.csv` | CH sector/wage deltas, clips to 0–10 |
| `src/data/full_quality_audit.py` | `scores.csv` | `scores.csv` + `audit_report.json` | Phase 1: Haiku audit; Phase 2: Haiku desc generation; Phase 3: Sonnet re-score |
| `src/scoring/fix_brennschneider_contamination.py` | `scores.csv` | `scores.csv` | One-time fix; kept for reference |

### ESCO Search Strategy (`enrich_with_esco.py`)

Six stages, first valid match wins (each candidate validated by Haiku before accepting):

1. ESCO REST API — direct German title search
2. ESCO REST API — Haiku-generated alternative terms (4 synonyms/broader terms)
3. ESCO REST API — filtered by ISCO-08 group code
4. berufsberatung.ch — HTML scrape of official CH job descriptions
5. Wikipedia DE — API search
6. Haiku direct — generates description from job title + ISCO context (fallback)

`KNOWN_WRONG_MATCHES` in the script lists 16 jobs with confirmed bad ESCO matches.
Run `--fix-wrong` locally to reprocess them. Run `--job "Berufname"` to test a single job.

### Streamlit App (`src/app/`)

Entry point: `src/app/app.py` — uses `st.navigation()` for multi-page routing.
Pages in `src/app/pages/`:

| File | Menu Title | Content |
|------|-----------|---------|
| `0_Startseite.py` | Startseite | Landing page, key metrics, navigation |
| `1_Treemap.py` | Treemap | All jobs as tiles; size = headcount, color = score |
| `2_Matrix.py` | Matrix | Scatter: X = adaptability, Y = exposure; quadrant-colored |
| `3_Branchen.py` | Branchen | Sector bar chart + Webb convergence heatmap |
| `4_Berufssuche.py` | Berufssuche | Job search (Swiss + ESCO title), score breakdown, radar chart |
| `5_Methodik.py` | Methodik & Quellen | Methodology, data sources, limitations |

All charts use **Plotly**. App reads from `data/processed/scores.csv`.

### Key Data Columns in `scores.csv`

| Column | Source | Description |
|--------|--------|-------------|
| `beruf` | BFS SAKE | German Swiss job title (CH-ISCO-19, 4-digit groups) |
| `isco_code` | BFS SAKE | ISCO-08 / CH-ISCO-19 code |
| `beschaeftigte_1000` | BFS SAKE 2024 | Employed persons in thousands |
| `frauen_pct` | BFS SAKE 2024 | Share of women in percent (0–100) |
| `branche` | BFS SAKE | Sector (21 categories, manually mapped from ISCO groups) |
| `lohn_median_chf` | BFS LSE 2022 | Median annual gross salary CHF |
| `qualifikation` | BFS LSE 2022 | Education level: Tertiär / Sekundär II / Keine Ausbildung |
| `esco_uri` | ESCO REST API | ESCO occupation URI — empty for 97 of 204 jobs |
| `esco_titel` | ESCO REST API | ESCO occupation title (German) |
| `esco_beschreibung` | ESCO API or Haiku | ESCO description, or Haiku-generated if no ESCO match |
| `score_gesamt` | Claude Sonnet | Raw AI exposure score 0–10 (Batch API) |
| `score_digital` | Claude Sonnet | Sub-score: digital output (25% weight) |
| `score_wiederholbarkeit` | Claude Sonnet | Sub-score: repeatability (25% weight) |
| `score_physisch` | Claude Sonnet | Sub-score: physical presence (20% weight, inverted) |
| `score_kreativitaet` | Claude Sonnet | Sub-score: creativity (15% weight, inverted) |
| `score_sozial` | Claude Sonnet | Sub-score: social interaction (15% weight, inverted) |
| `haupt_risiko` | Claude Sonnet | Main automation risk description |
| `zeitrahmen` | Claude Sonnet | Estimated time horizon (1-2 / 3-5 / 5-10 / >10 Jahre) |
| `begruendung` | Claude Sonnet | 2–3 sentence justification, CH-specific |
| `delta_branche` | `ch_adjustments.py` | CH sector adjustment (rule-based) |
| `delta_lohn` | `ch_adjustments.py` | CH wage-level adjustment (rule-based) |
| `score_ch` | `ch_adjustments.py` | Final score: score_gesamt + delta_branche + delta_lohn, clipped 0–10 |
| `adaptabilitaet` | `adaptability_scorer.py` | Adaptability score 0–10 (rule-based) |

## Datenqualität

### ESCO-Abdeckung

- **107 / 204** Berufe haben einen ESCO-URI (nach `--fix-wrong`-Lauf lokal: 188/204).
- **97 Berufe** haben keine ESCO-URI — ihr Scoring basiert auf dem Berufstitel + Haiku-generierter Beschreibung (Stage 6 des 6-stufigen Suchprozesses).
- `berufe_ch_esco_verified.csv` enthält nur die 107 verifizierten Einträge; die restlichen 97 wurden direkt über `enrich_with_esco.py` behandelt.

### Bekannte ESCO-Fehlzuordnungen

16 Berufe mit bestätigten ESCO-Fehlmatches (in `KNOWN_WRONG_MATCHES` gelistet):

```
Bankkaufmann/-frau              → Abfallmakler (korrekt: Bankbediensteter)
Logistiker/in EFZ               → Abfallmakler
Grafiker/in                     → Kartograf (korrekt: Grafiker/in)
Hochbauzeichner/in EFZ          → 3D-Druck-Techniker
Polymechaniker/in EFZ           → Brennschneider
Immobilienbewirtschafter/in     → Abfallmakler / Brennschneider
Automatiker/in EFZ              → 3D-Druck-Techniker / Brennschneider
Bauführer/in                    → 3D-Druck-Techniker
Elektroplaner/in EFZ            → 3D-Druck-Techniker
PR-Spezialist/in                → Preiskalkulation
Reinigungspersonal...           → Netzverankerung Aquakultur
Leitende Verwaltungsbedienstete → Leitender Hauswirtschafter
Technische Verkaufsfachkräfte   → Experte Geoinformationssysteme
Bürokräfte Transportwirtschaft  → Lebensmitteltechniker
Physiotherapeut. Techniker...   → Anästhesietechn. Assistent
Fachkräfte Personal & Schulung  → Hydraulik-Fachkraft
```

Die Scoring-Inhalte (`haupt_risiko`, `begruendung`) dieser Berufe wurden durch das
Quality Audit geprüft und sind inhaltlich korrekt — Claude ignorierte falsche ESCO-Beschreibungen
und bewertete auf Basis des Berufstitels. Die `esco_titel`-Metaspalte in `scores.csv` ist für
diese Berufe noch veraltet (tracking: Issue #21).

### ESCO API — wichtiger Hinweis

Die ESCO REST API (`ec.europa.eu/esco`) ist im **Anthropic Cloud-Environment geblockt**
(HTTP-Layer-Blockierung trotz erfolgreicher TLS-Verbindung). Folgende Skripte müssen
**lokal** ausgeführt werden:

- `enrich_with_esco.py` (alle Modi)
- `verify_esco_matches.py`
- `patch_unmatched.py`

### Quality Audit Prozess

`full_quality_audit.py` prüft ob `haupt_risiko`/`begruendung` zum Berufstitel passt:

1. **Phase 1 (Haiku)**: Prüft alle 204 Beschreibungen auf inhaltliche Korrektheit
2. **Phase 2 (Haiku)**: Generiert korrekte Berufsbeschreibung für fehlerhafte Jobs
3. **Phase 3 (Sonnet)**: Re-Scoring mit korrigierten Beschreibungen

Wann neu ausführen: nach `--fix-wrong`-Lauf oder wenn neue Batch-Scoring-Artefakte vermutet werden.
Report wird in `data/processed/audit_report.json` gespeichert.

### Nachträgliche Korrekturen (Historie)

| Zeitpunkt | Korrektur | Betroffene Berufe |
|-----------|-----------|-------------------|
| 2025-04 | Brennschneider-Kontamination (Batch API Artefakt) | 14 Berufe via `fix_brennschneider_contamination.py` |
| 2025-04 | Vollständiges Quality Audit | 12 weitere Berufe via `full_quality_audit.py` |
| 2025-04 | Manuelle Korrektur | Grafiker/in (Score 3.2 → 6.2, war Graveur-Beschreibung) |

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
