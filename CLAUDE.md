# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

**KI-Jobexpositions-Analyse Schweiz** — A Streamlit webapp that visualizes AI automation
exposure scores for **179 Swiss occupations**, using the Karpathy/Webb methodology adapted
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
python src/data/update_from_bfs.py          # BFS SE → beschaeftigte_1000/frauen_pct/synonyme in all 4 CSVs (via mapping)
python src/data/update_from_bfs.py --blatt 2023        # other year sheet (default "2024"; needs data/raw file)
python src/data/update_from_bfs.py --neue-berufe       # also add new SE Berufsgattungen >= 5000 to berufe_ch.csv + mapping
python src/data/berufe_zusammenlegen.py     # one-time #51 migration (ISCO fixes + merges), idempotent, kept for reference
python src/data/enrich_with_esco.py         # ESCO API → berufe_ch_esco.csv  [LOCAL ONLY]
python src/data/verify_esco_matches.py      # validate matches → berufe_ch_esco_verified.csv
python src/data/patch_unmatched.py          # manual fixes for bad matches
python src/data/update_loehne.py --offline  # LSE 2024 wages (+ stored Salarium profiles) → all CSVs, recomputes score_ch/adaptabilitaet
python src/data/update_loehne.py            # same, but re-queries Salarium + STATENT online (~15 min, polite)
python src/data/fetch_bgs.py                # BFS GGS (stats.swiss SDMX) + STATENT online → grenzgaenger_anteil_branche.csv
python src/data/fetch_bgs.py --offline      # same from the versioned CSVs (no network); --periode 2026-Q2, --dry-run
python src/data/fetch_statent.py            # BFS STATENT ts-x-06.02.01.01 (DAM API) → statent_groessenklassen_noga.csv + kmu_anteil_branche.csv
python src/data/fetch_statent.py --offline --apply-scores --dry-run  # preview new zeitrahmen in scores.csv (writes nothing)
python src/data/fetch_statent.py --offline --apply-scores            # write kmu_anteil_branche.csv + recompute grossfirmen_anteil/zeitrahmen_kmu_delta/zeitrahmen

# Fix known wrong ESCO matches (re-run locally after adding to KNOWN_WRONG_MATCHES):
python src/data/enrich_with_esco.py --fix-wrong
# Test a single job:
python src/data/enrich_with_esco.py --job "Bankkaufmann/-frau"

# --- Scoring Pipeline (requires ANTHROPIC_API_KEY in .env) ---
python src/scoring/exposure_scorer.py       # synchronous scoring, hash-based delta (only changed jobs)
python src/scoring/exposure_scorer.py --force                  # re-score all jobs
python src/scoring/exposure_scorer.py --force "Buchhalter/in"  # re-score by name
python src/scoring/exposure_scorer.py --force 2411             # re-score by ISCO prefix
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
data/raw/su-d-40.02.03.02.01.03.10.xlsx   (BFS Strukturerhebung, manually downloaded from bfs.admin.ch)
  → src/data/update_from_bfs.py
  + data/processed/beruf_berufsart_mapping.csv  (beruf → 4-digit Berufsgattung or 5-digit Berufsart(en), versioned)
  → data/processed/se_berufe.csv          (versioned SE extract: sheets 2024 + 2022-2024, both levels)
  → beschaeftigte_1000, frauen_pct, synonyme in berufe_ch*.csv and scores.csv (179 jobs)

berufe_ch.csv
  → src/data/enrich_with_esco.py          [requires local ESCO API access]
  → data/processed/berufe_ch_esco.csv     (+ ESCO URI + description)

berufe_ch_esco.csv
  → src/data/verify_esco_matches.py
  → data/processed/berufe_ch_esco_verified.csv  (+ match_score 0/1/2)
  note: 5 of 179 jobs have no ESCO URI (fallback description)

data/raw/je-d-03.04.01.02.47.xlsx         (BFS LSE 2024 T17, optional — parsed copy is versioned)
data/processed/lohn_profile_salarium.csv  (curated Salarium profile per job, groups 11–14/22/24/26)
  → src/data/update_loehne.py             (--offline: uses stored Salarium/STATENT values)
  → lohn_median_chf + lohn_quelle in berufe_ch*.csv and scores.csv;
    scores.csv: lohnklasse, delta_lohn, delta_branche, score_ch, adaptabilitaet recomputed
  versioned helper files: lse2024_monatslohn_isco.csv, lohn_salarium_abfragen.csv,
    statent_vzae_grossregion.csv

stats.swiss SDMX DF_GGS_4 (BFS GGS, quarterly, NOGA division)  +  STATENT px-x-0602010000_101
  → src/data/fetch_bgs.py                 (raw SDMX-CSV → data/raw/bgs_df_ggs_4.csv, gitignored;
                                           --offline: versioned CSVs below)
  → data/processed/bgs_grenzgaenger_noga.csv, statent_beschaeftigte_noga.csv (versioned)
  → data/processed/grenzgaenger_anteil_branche.csv  (context layer in 3_Branchen.py, no score effect)

BFS DAM API orderNr=ts-x-06.02.01.01 (STATENT, market enterprises × NOGA division × size class)
  → src/data/fetch_statent.py             (raw CSV → data/raw/statent_ts-x-06.02.01.01.csv, gitignored;
                                           --offline: versioned table below)
  → data/processed/statent_groessenklassen_noga.csv (versioned, all years 2011–2024)
  → data/processed/kmu_anteil_branche.csv (grossfirmen_anteil per sector)
  → --apply-scores: scores.csv grossfirmen_anteil, zeitrahmen_kmu_delta, zeitrahmen (from zeitrahmen_roh)
```

**KMU adoption factor** = **BFS STATENT 2024**, table `ts-x-06.02.01.01` «Marktwirtschaftliche
Unternehmen nach Wirtschaftsabteilungen und Grössenklasse» (asset 36734598, OGD CSV, status
20.08.2026; columns PERIOD, NOGA, SIZE 1–4/999, INDICATOR 1 = enterprises / 2 = employed persons,
VALUE, STATUS A/Q). Unit = **enterprise** (not establishment), size class and count = employed
persons (headcount; no FTE variant exists per division × size class). `grossfirmen_anteil` = employed
in enterprises ≥250 / all employed of the sector's NOGA divisions (`NOGA_ZU_BRANCHE`). Suppressed
cells (Q): residual total − known classes split equally (impact < 1 pp). Market enterprises only →
NOGA 84 empty → «Öff. Verwaltung» has no share (shift 0); `abdeckung` = coverage vs. all STATENT
employed (Bildung 29 %, Soziales 59 %, Verwaltung 23 %). Thresholds in `ch_adjustments.py`:
≥0.50 → −1 step, <0.15 → +1 step (until Oct 2026: BZ 2008 establishments ≥250 FTE, 0.40/0.10).

**Cross-border commuters** = **BFS Grenzgängerstatistik (GGS)**, dataflow `CH1.GGS,DF_GGS_4,1.0.0`
«Ausländische Grenzgänger/-innen nach Wirtschaftszweig und Erwerbsstatus» (ZEMIS/AHV, persons,
values from 2024-Q3 provisional). Endpoint
`https://disseminate.stats.swiss/rest/data/CH1.GGS,DF_GGS_4,1.0.0/._T.Q?startPeriod=2022-Q1`
(Accept `application/vnd.sdmx.data+csv;version=1.0.0`; key = NOGA.AUFZW.FREQ). Numerator =
mean of the four quarters of the latest complete year (2025), latest quarter as extra column.
Denominator = STATENT 2024 «Beschäftigte», Switzerland total (workplace-based, AHV, includes
cross-border commuters). Share = Σ GGS / Σ STATENT over the NOGA divisions of a sector
(`NOGA_ZU_BRANCHE` from `fetch_statent.py`); NOGA 97–99 are not in STATENT and are excluded.

**Wage data** = **BFS LSE 2024**, table T17 «Monatlicher Bruttolohn nach Berufsgruppen, Lebensalter
und Geschlecht», private and public sector (asset 36355224, `je-d-03.04.01.02.47.xlsx`, sheet `2024`).
Only 2-digit CH-ISCO-19 groups exist. Standardised monthly wage incl. 1/12 of the 13th salary and of
special payments → annual wage = monthly × 12. Fallback for groups without LSE value (01–03, 63, 95):
1-digit major group (`LSE2024_1d`), else total median (`LSE2024_total`). Heterogeneous groups
(11–14, 22, 24, 26): `lohn_j = LSE_g × 12 × S_j / S̄_g` with `S̄_g = Σ_k∈g w_k·S_k / Σ_k∈g w_k`,
`w_k = beschaeftigte_1000` (from `berufe_ch.csv`), normalised per 2-digit LSE group g (managers per
11/12/13/14) — so the employment-weighted mean wage of each group equals the LSE median × 12.
S = Salarium (LSE-2024 model, private sector) median for the job's profile (mandatory education,
main NOGA division) plus a fixed norm profile (42 y, 8 years tenure, 40 h, no management function),
FTE-weighted over the 7 Grossregionen (STATENT); `lohn_quelle = LSE2024_2d+Salarium`. Jobs without a
Salarium value (1112, NOGA 84) get LSE_g × 12 and are excluded from S̄_g. Top wages (doctors,
management, private banking, law firms) are underestimated.

**Employment data** = **BFS Strukturerhebung (SE)**, *not* SAKE — table «Ausgeübter Beruf (CH-ISCO-19)
nach Geschlecht und Staatsangehörigkeit» (asset 36492006, file `su-d-40.02.03.02.01.03.10.xlsx`),
employed persons aged 15+ of the permanent resident population in private households (no cross-border
commuters), in 1000. Downloaded from:
`https://www.bfs.admin.ch/bfs/de/home/statistiken/kataloge-datenbanken.assetdetail.36492006.html`

The file has one sheet per year (`2024`, `2023`, …, `2010`, `2000`, `1990`) plus pooled sheets
(`2022-2024`, `2021-2023`, …). Columns: 0–4 codes by level (4-digit Berufsgattung = column 3,
5-digit Berufsart = column 4), 5 label, 6 total, 7 men, 8 women; «X» = not published (< 5 obs.),
number format «(##0)» = < 50 obs. Select the sheet with `--blatt` (default `2024`).

**No double counting (Issue #51):** invariant Σ `beschaeftigte_1000` per 4-digit code = SE value
(tested). Mapping `beruf_berufsart_mapping.csv` (columns `beruf, isco_code, ebene, berufsarten,
synonyme, zusammengelegt_aus, text_von, begruendung`):
- `ebene = gattung`: only job of its Berufsgattung → full SE value.
- `ebene = berufsart`: several jobs share a Gattung (2330, 5131, 5223) → sum of the assigned
  5-digit Berufsarten + rest of the Gattung (onA, unpublished) proportionally; every published
  non-onA Berufsart must be assigned exactly once.
- Otherwise jobs are merged (Fallback A): SE label as `beruf`, former CH titles in `synonyme`
  (searchable in Berufssuche, old permalinks resolve); scores = employment-weighted mean of the
  former entries, texts/ESCO from the largest (`text_von`), `scores_gemittelt = True` and empty
  `beschreibung_hash` so `exposure_scorer.py` re-scores them. 22 merges, see `docs/audit_isco_codes.md`.
- SE value from sheet 2024; if a Gattung (or its women count) is «X», the pooled sheet 2022-2024.
- ISCO codes audited against SE labels (`docs/audit_isco_codes.md`): 21 corrected, 15 open.
  A new job/code needs a mapping row; when changing codes, adjust `lohn_profile_salarium.csv`
  (groups 11–14/22/24/26) and run `update_loehne.py --offline`.

### Scoring Pipeline (outputs `data/processed/scores.csv`)

```
berufe_ch_esco_verified.csv
  → exposure_scorer.py      (claude-sonnet-4-6, synchronous, hash-based delta — only changed jobs)
  → adaptability_scorer.py  (rule-based: education, wage, digital affinity, mobility)
  → ch_adjustments.py       (sector/salary deltas, score clipped 0–10)
  → scores.csv
```

`exposure_scorer.py` stores a `beschreibung_hash` (SHA-256[:12] of beruf + description) per job.
On subsequent runs only jobs with changed descriptions are re-scored. Use `--force` to override.

Scoring criteria: digital output (25%), repeatability (25%), physical presence (20% neg.),
creativity (15% neg.), social interaction (15% neg.).

CH sector deltas: Finance +0.3, Insurance +0.4, ICT −0.2, Health −0.3, Education −0.2,
Public admin +0.1, Industry −0.1, Retail +0.2, Legal +0.2.

CH wage deltas: <60k CHF −0.2, 60–100k 0.0, 100–150k +0.2, >150k +0.4.

### Script Reference

| Script | Input | Output | Notes |
|--------|-------|--------|-------|
| `src/data/update_from_bfs.py` | `data/raw/su-d-40.02.03.02.01.03.10.xlsx` (or `se_berufe.csv`), `beruf_berufsart_mapping.csv` | `berufe_ch*.csv`, `scores.csv`, `se_berufe.csv` | BFS SE 2024: Berufsgattung/Berufsart per mapping, sets `beschaeftigte_1000`, `frauen_pct`, `synonyme`; `--blatt`, `--neue-berufe`, `--dry-run` |
| `src/data/berufe_zusammenlegen.py` | `beruf_berufsart_mapping.csv` | `berufe_ch*.csv`, `scores.csv` | One-time #51 migration: ISCO code fixes + merges (weighted-mean scores); idempotent |
| `src/data/enrich_with_esco.py` | `berufe_ch.csv` | `berufe_ch_esco.csv` | **Must run locally** (ESCO API blocked in cloud); 6-stage search with Haiku validation |
| `src/data/verify_esco_matches.py` | `berufe_ch_esco.csv` | `berufe_ch_esco_verified.csv` | Haiku-based match quality scoring 0/1/2 |
| `src/data/patch_unmatched.py` | `berufe_ch_esco_verified.csv` | `berufe_ch_esco_verified.csv` | Manual overrides for known bad matches |
| `src/data/update_loehne.py` | LSE 2024 T17 (raw or `lse2024_monatslohn_isco.csv`), `lohn_profile_salarium.csv`, `lohn_salarium_abfragen.csv`, `statent_vzae_grossregion.csv` | `berufe_ch*.csv`, `scores.csv` | Sets `lohn_median_chf`/`lohn_quelle`; recomputes wage-dependent rule-based columns in scores.csv; `--offline` (no network), `--dry-run` |
| `src/data/fetch_bgs.py` | stats.swiss SDMX `DF_GGS_4` + STATENT PxWeb (online) or `bgs_grenzgaenger_noga.csv` + `statent_beschaeftigte_noga.csv` (`--offline`) | `grenzgaenger_anteil_branche.csv` (+ the two versioned inputs when online) | Cross-border commuter share per sector (annual mean of latest full year, latest quarter extra); reads/writes no scores; `--periode JJJJ\|JJJJ-Qn`, `--dry-run` |
| `src/data/fetch_statent.py` | BFS DAM API `ts-x-06.02.01.01` (online) or `statent_groessenklassen_noga.csv` (`--offline`) | `kmu_anteil_branche.csv` (+ `statent_groessenklassen_noga.csv` when online); with `--apply-scores`: `scores.csv` | Grossfirmen share per sector (enterprises ≥250 employed); `--jahr`, `--dry-run`; `--apply-scores` rewrites only `grossfirmen_anteil`, `zeitrahmen_kmu_delta`, `zeitrahmen` (from `zeitrahmen_roh`) |
| `src/data/branche_neu_zuordnen.py` | `BRANCHE_MAP` | `berufe_ch*.csv`, `scores.csv` | Re-applies ISCO-prefix sector mapping to non-curated jobs |
| `src/scoring/exposure_scorer.py` | `berufe_ch_esco_verified.csv` | `scores.csv` | Synchronous, hash-based delta; `--force [name\|isco]` for selective re-score |
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

Each ESCO URI can only be assigned to one job (deduplication via `blocked_uris`).
`KNOWN_WRONG_MATCHES` lists 25 confirmed bad matches → see `DATA_QUALITY.md`.
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
| `beruf` | BFS SE | German Swiss job title (CH-ISCO-19, 4-digit groups) |
| `isco_code` | BFS SE | ISCO-08 / CH-ISCO-19 code |
| `synonyme` | `beruf_berufsart_mapping.csv` | Former CH titles of merged entries (`; `-separated), searched in Berufssuche |
| `beschaeftigte_1000` | BFS Strukturerhebung (SE) 2024 | Employed persons in thousands — 4-digit Gattung or assigned 5-digit Berufsarten; Σ per code = SE value |
| `frauen_pct` | BFS Strukturerhebung (SE) 2024 | Share of women in percent (0–100); pooled 2022–2024 if 2024 is «X» |
| `branche` | ISCO mapping | Sector (21 categories, manually mapped from ISCO groups) |
| `lohn_median_chf` | BFS LSE 2024 (T17) | Median annual gross salary CHF = 2-digit group monthly median × 12; for groups 11–14/22/24/26 calibrated with Salarium profiles (`update_loehne.py`) |
| `lohn_quelle` | `update_loehne.py` | `LSE2024_2d`, `LSE2024_2d+Salarium`, fallback `LSE2024_1d` / `LSE2024_total` |
| `qualifikation` | Curated list / ISCO major group | Education level: Tertiär / Sekundär II / Keine Ausbildung |
| `esco_uri` | ESCO REST API | ESCO occupation URI — empty for 5 of 179 jobs (fallback description) |
| `esco_titel` | ESCO REST API | ESCO occupation title (German) |
| `esco_beschreibung` | ESCO API or Haiku | ESCO description (174 jobs) or fallback from berufsberatung.ch / Wikipedia / Haiku (5 jobs) |
| `score_gesamt` | Claude Sonnet | Raw AI exposure score 0–10 (Batch API) |
| `score_digital` | Claude Sonnet | Sub-score: digital output (25% weight) |
| `score_wiederholbarkeit` | Claude Sonnet | Sub-score: repeatability (25% weight) |
| `score_physisch` | Claude Sonnet | Sub-score: physical presence (20% weight, inverted) |
| `score_kreativitaet` | Claude Sonnet | Sub-score: creativity (15% weight, inverted) |
| `score_sozial` | Claude Sonnet | Sub-score: social interaction (15% weight, inverted) |
| `haupt_risiko` | Claude Sonnet | Main automation risk description |
| `zeitrahmen_roh` | `exposure_scorer.py` (LLM scoring) | Estimated time horizon from scoring (1-2 / 3-5 / 5-10 / >10 Jahre) |
| `zeitrahmen` | `ch_adjustments.py` | `zeitrahmen_roh` shifted by `zeitrahmen_kmu_delta` (KMU adoption factor) |
| `grossfirmen_anteil` | BFS STATENT 2024 (`fetch_statent.py`) | Share of sector's employed persons in enterprises ≥250 employed; empty for Öff. Verwaltung |
| `zeitrahmen_kmu_delta` | `ch_adjustments.py` | −1 (share ≥50 %), 0, +1 (share <15 %) |
| `begruendung` | Claude Sonnet | 2–3 sentence justification, CH-specific |
| `delta_branche` | `ch_adjustments.py` | CH sector adjustment (rule-based) |
| `delta_lohn` | `ch_adjustments.py` | CH wage-level adjustment (rule-based) |
| `score_ch` | `ch_adjustments.py` | Final score: score_gesamt + delta_branche + delta_lohn, clipped 0–10 |
| `adaptabilitaet` | `adaptability_scorer.py` | Adaptability score 0–10 (rule-based) |
| `scores_gemittelt` | `berufe_zusammenlegen.py` | `True` = merged entry, scores are a provisional employment-weighted mean (re-scoring pending) |

## Datenqualität

Siehe `DATA_QUALITY.md` für ESCO-Abdeckung, bekannte Fehlzuordnungen (25 Einträge),
Korrektur-Historie, Quality Audit Prozess und ESCO API Cloud-Blockierung.

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
