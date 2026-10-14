# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

**KI-Jobexpositions-Analyse Schweiz** — A Streamlit webapp that visualizes the exposure of
**187 Swiss occupations** to generative AI. Exposure is rated **task by task** (Eloundou et al. /
ILO-style rubric v2.2): each occupation's 8–12 core activities are rated by two models
(Claude Opus 5.5 via the user's subscription, Gemini 4 Argon), 2–3 runs each; the score is the share
of working time in activities that generative AI can speed up by ≥ 50 %. Swiss data: BFS SE, LSE,
STATENT, GGS; ESCO v1.2.1. Deployed on **HuggingFace Spaces**.

- HuggingFace: `https://huggingface.co/spaces/AndyWHV/ki-jobexposition-schweiz`
- GitHub: `https://github.com/minigraphx/ki-jobexposition-schweiz`

## Commands

```bash
# Use the project's virtual environment
source .venv/bin/activate   # or: .venv/bin/python for one-off calls

# Run the Streamlit app (from repo root)
streamlit run src/app/app.py

# --- Column migration (Issue #53, one-time, idempotent) ---
python src/data/migrate_columns.py --dry-run   # plan: old → new column names per CSV (column_mapping.py)
python src/data/migrate_columns.py             # rename (refuses unknown/mixed columns; verifies cell values)

# --- Data Pipeline (run as needed, in order) ---
python src/data/update_from_bfs.py          # BFS SE → employed_k/women_pct/synonyms in all 4 CSVs (via mapping)
python src/data/update_from_bfs.py --sheet 2023        # other year sheet (default "2024"; needs data/raw file)
python src/data/update_from_bfs.py --add-new           # also add new SE Berufsgattungen >= 5000 to berufe_ch.csv + mapping
python src/data/update_from_bfs.py --dry-run           # works without the raw xlsx (versioned se_berufe.csv)
python src/data/enrich_with_esco.py         # ESCO v1.2.1 → berufe_ch_esco.csv + _verified.csv (only jobs without assignment)
python src/data/update_loehne.py --offline  # LSE 2024 wages (+ stored Salarium profiles) → all CSVs, recomputes adaptability
python src/data/update_loehne.py            # same, but re-queries Salarium + STATENT online (~15 min, polite)
python src/data/fetch_bgs.py                # BFS GGS (stats.swiss SDMX) + STATENT online → grenzgaenger_anteil_branche.csv
python src/data/fetch_bgs.py --offline      # same from the versioned CSVs (no network); --period 2026-Q2, --dry-run
python src/data/fetch_statent.py            # BFS STATENT ts-x-06.02.01.01 (DAM API) → statent_groessenklassen_noga.csv + kmu_anteil_branche.csv
python src/data/fetch_statent.py --offline --apply-scores --dry-run  # preview new timeframe in scores.csv (writes nothing)
python src/data/fetch_statent.py --offline --apply-scores            # write kmu_anteil_branche.csv + recompute large_firm_share/timeframe_sme_shift/timeframe
python src/data/branche_neu_zuordnen.py --dry-run  # re-apply ISCO-prefix sector mapping (non-curated jobs)

# Re-match entries listed in KNOWN_WRONG_MATCHES (currently empty, all known errors fixed in #52):
python src/data/enrich_with_esco.py --fix-wrong
# Single job / all jobs (--all overwrites the curated #52 assignments!):
python src/data/enrich_with_esco.py --job "Grafik- und Multimediadesigner"
python src/data/enrich_with_esco.py --all

# --- Task-based scoring, Rubrik v2.2 (LOCAL ONLY, own keys/subscription; see docs/neubewertung_lokal.md) ---
pip install -r requirements-dev.txt         # includes requirements-scoring.txt (anthropic, google-genai, jsonschema)
python src/scoring/task_scorer.py --provider claude --pilot --runs 2 --dry-run   # calls + token/cost estimate (sync + batch), no API call
python src/scoring/task_scorer.py --provider claude --pilot --runs 2 --dry-run --count-tokens  # exact input tokens (free, needs key)
python src/scoring/task_scorer.py --provider claude --only 2512 --runs 1   # synchronous probe (schema check), 1 call
python src/scoring/task_scorer.py --provider claude --pilot --runs 2   # 15 pilot jobs, 2 runs (+ auto run 3 if |Δζ| > 1)
python src/scoring/task_scorer.py --provider gemini --pilot --runs 2
python src/scoring/task_scorer.py --provider claude --only 2411 2512 --force   # selected ISCO codes/prefixes, re-ask
# Claude via own subscription (Claude Code `claude -p`, no API key; results in bewertungen/claude-cli/) — used for the app
python src/scoring/task_scorer.py --provider claude-cli --runs 2
# Batch mode (API; 50 % cheaper, up to 24 h; state in bewertungen/<provider>/batches/)
python src/scoring/task_scorer.py --provider gemini --runs 2 --batch submit --dry-run   # requests + batch cost
python src/scoring/task_scorer.py --provider gemini --runs 2 --batch submit --no-response-schema   # all entries (delta: skips current + open)
python src/scoring/task_scorer.py --provider gemini --batch status            # open batches, status/counts
python src/scoring/task_scorer.py --provider gemini --batch collect           # fetch finished, validate, write run<N>/ (idempotent)
python src/scoring/task_scorer.py --provider claude --runs 2 --batch followup --refusal-sync  # retries/corrections + run 3 as new batch; refusals sync with fallback
python src/scoring/task_aggregate.py        # → scores_aufgaben.csv (default --claude-source claude-cli; `claude` = API runs)
python src/scoring/apply_task_scores.py --dry-run   # check: every entry rated? what would change?
python src/scoring/apply_task_scores.py     # → scores.csv (exposure block + SME timeframe + adaptability) — the app's data
python src/scoring/task_vergleich.py        # → data/processed/bewertungen/vergleich.md (pilot vs. API, benchmarks)
python src/scoring/task_inputs.py --pilot   # optional: write input JSONs for inspection (gitignored)
python src/scoring/adaptability_scorer.py   # recompute adaptability only (also done by apply_task_scores/update_loehne)

# --- Tests ---
pytest tests/ -v
pytest tests/ --cov=src/scoring --cov-report=term-missing   # CI: coverage ≥ 80 %, no scipy
```

Historical scripts exit immediately with a pointer to the current pipeline (code in git history):
`src/scoring/exposure_scorer.py`, `ch_adjustments.py`, `generate_demo_scores.py`,
`fix_brennschneider_contamination.py`; `src/data/full_quality_audit.py`, `berufe_zusammenlegen.py`
(keeps `ISCO_KORREKTUREN` as reference data), `fetch_esco.py`, `fetch_sake.py`,
`verify_esco_matches.py`, `patch_unmatched.py`.

## Architecture

### Column names (Issue #53)

All CSV column names in `data/processed/` are English snake_case ASCII; **cell values stay German**
(sector names «Öff. Verwaltung», timeframes «3-5 Jahre», mapping levels «gattung»/«berufsart») because
they are shown in the app. The central mapping old → new per file is `src/data/column_mapping.py`
(`SPALTEN`, `ENTFERNT`, `SCORES_SCHEMA`); `src/data/migrate_columns.py` applies it idempotently
(header-only rewrite unless columns are dropped; cell-by-cell check). Code identifiers may stay German.
The **input records of the task rubric keep their German keys** (`beruf`, `synonyme`, `ch_kontext`,
`esco_titel`, …): they are hashed (`input_hash`). `task_inputs.STAMMDATEN_SPALTEN` /
`KOMPETENZ_SPALTEN` map the English CSV columns back to these keys; `tests/test_input_hash.py` checks
that every stored ok rating still has the current hash. Do not rename keys of the rating JSONs
(`taetigkeiten`, `zeitanteil_pct`, …) or touch `src/scoring/rubrik/` — they are part of the hashed schema.

### Data Pipeline (outputs to `data/processed/`)

```
data/raw/su-d-40.02.03.02.01.03.10.xlsx   (BFS Strukturerhebung, manually downloaded from bfs.admin.ch)
  → src/data/update_from_bfs.py
  + data/processed/beruf_berufsart_mapping.csv  (occupation → 4-digit Berufsgattung or 5-digit Berufsart(en), versioned)
  → data/processed/se_berufe.csv          (versioned SE extract: sheets 2024 + 2022-2024, both levels)
  → employed_k, women_pct, synonyms in berufe_ch*.csv and scores.csv (187 jobs)

berufe_ch.csv
  → src/data/enrich_with_esco.py          (ESCO REST API, selectedVersion=v1.2.1; reachable from the cloud)
  → data/processed/berufe_ch_esco.csv + berufe_ch_esco_verified.csv (identical ESCO columns:
    esco_uri, esco_title, esco_description, description_source, esco_isco_code, esco_match_quality)
  note: 3 of 187 jobs have no ESCO URI (fallback description); every URI is used once
  curated in #52: docs/audit_esco_zuordnungen.md (decision + reason per entry)

data/processed/esco_kompetenzen.csv       (versioned; ESCO v1.2.1 CSV download, de)
  occupation, isco_code, esco_uri, competence, relation (essential/optional), type (skill/knowledge), competence_uri
  → input of the task-based rating; regenerate when an esco_uri changes (changes the input hash!)

data/raw/je-d-03.04.01.02.47.xlsx         (BFS LSE 2024 T17, optional — parsed copy is versioned)
data/processed/lohn_profile_salarium.csv  (curated Salarium profile per job, groups 11–14/22/24/26)
data/processed/lohn_verhaeltnisse.csv     (documented ratio factors to the LSE group median, group 22)
  → src/data/update_loehne.py             (--offline: uses stored Salarium/STATENT values)
  → wage_median_chf + wage_source + wage_uncertain in berufe_ch*.csv and scores.csv;
    scores.csv: adaptability recomputed (no wage delta on the score any more)
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
  → data/processed/kmu_anteil_branche.csv (large_firm_share per sector)
  → --apply-scores: scores.csv large_firm_share, timeframe_sme_shift, timeframe (from timeframe_raw)
```

**KMU adoption factor** = **BFS STATENT 2024**, table `ts-x-06.02.01.01` «Marktwirtschaftliche
Unternehmen nach Wirtschaftsabteilungen und Grössenklasse» (asset 36734598, OGD CSV, status
20.08.2026; columns PERIOD, NOGA, SIZE 1–4/999, INDICATOR 1 = enterprises / 2 = employed persons,
VALUE, STATUS A/Q). Unit = **enterprise** (not establishment), size class and count = employed
persons (headcount; no FTE variant exists per division × size class). `large_firm_share` = employed
in enterprises ≥250 / all employed of the sector's NOGA divisions (`NOGA_ZU_BRANCHE`). Suppressed
cells (Q): residual total − known classes split equally (impact < 1 pp). Market enterprises only →
NOGA 84 empty → «Öff. Verwaltung» has no share (shift 0); `coverage` = coverage vs. all STATENT
employed (Bildung 29 %, Soziales 59 %, Verwaltung 23 %). Logic and thresholds in
`src/scoring/kmu_faktor.py` (shared by `apply_task_scores.py`, `fetch_statent.py --apply-scores`,
`branche_neu_zuordnen.py`): ≥0.50 → −1 step, <0.15 → +1 step (until Oct 2026: BZ 2008 establishments
≥250 FTE, 0.40/0.10). The sector acts **only** on the adoption timeframe, not on the score.

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
`w_k = employed_k` (from `berufe_ch.csv`), normalised per 2-digit LSE group g (managers per
11/12/13/14) — so the employment-weighted mean wage of each group equals the LSE median × 12.
S = Salarium (LSE-2024 model, private sector) median for the job's profile (mandatory education,
main NOGA division) plus a fixed norm profile (42 y, 8 years tenure, 40 h, no management function),
FTE-weighted over the 7 Grossregionen (STATENT); `wage_source = LSE2024_2d+Salarium`. Jobs without a
Salarium value (1112, NOGA 84) get LSE_g × 12 and are excluded from S̄_g. Top wages (management,
private banking, law firms) are underestimated.
**Ratio overrides** (`data/processed/lohn_verhaeltnisse.csv`, applied *after* the Salarium calibration):
`lohn_j = f_j × LSE_g × 12`, `wage_source = LSE2024_2d+Verhaeltnis`; override jobs are excluded from
S̄_g (the remaining Salarium jobs of the group are normalised among themselves). Group 22 (estimates,
band in the table): dipl. Pflege 2221 = 0.987 (BFS LSE 2018 special evaluation for the FOPH, asset
19087994: 7429/7526); doctors overall = 1.6 × Pflege (band 1.3–1.9; BFS hospital statistics 2018–2022
wage cost per FTE doctors/nursing 2.03–2.07, converted to 40 h/median/dipl. nursing → 1.53–1.77; LSE-2024
percentile decomposition 1.57–1.87), split 2211/2212 with ratio 0.85 (BASS 2018: 0.69, weakened —
assumption) and SE-2024 weights → 2211 = 1.375 (1.117–1.633), 2212 = 1.617 (1.314–1.921). Rows without
factor (2261 dentists, 2262 pharmacists: no documented ratio) keep the Salarium value and get
`wage_uncertain = True`. The wage only enters `adaptability` (fixed wage scale `LOHN_PUNKTE_MIN_CHF` /
`LOHN_PUNKTE_MAX_CHF` in `adaptability_scorer.py`: 0 points up to 50k CHF, linear to 3 points at
150k CHF, constant above), so a job's wage points depend only on its own wage.

**Employment data** = **BFS Strukturerhebung (SE)**, *not* SAKE — table «Ausgeübter Beruf (CH-ISCO-19)
nach Geschlecht und Staatsangehörigkeit» (asset 36492006, file `su-d-40.02.03.02.01.03.10.xlsx`),
employed persons aged 15+ of the permanent resident population in private households (no cross-border
commuters), in 1000. Downloaded from:
`https://www.bfs.admin.ch/bfs/de/home/statistiken/kataloge-datenbanken.assetdetail.36492006.html`

The file has one sheet per year (`2024`, `2023`, …, `2010`, `2000`, `1990`) plus pooled sheets
(`2022-2024`, `2021-2023`, …). Columns: 0–4 codes by level (4-digit Berufsgattung = column 3,
5-digit Berufsart = column 4), 5 label, 6 total, 7 men, 8 women; «X» = not published (< 5 obs.),
number format «(##0)» = < 50 obs. Select the sheet with `--sheet` (default `2024`).

**No double counting (Issue #51):** invariant Σ `employed_k` per 4-digit code = SE value
(tested). Mapping `beruf_berufsart_mapping.csv` (columns `occupation, isco_code, level, se_types,
synonyms, merged_from, text_from, rationale`):
- `level = gattung`: only job of its Berufsgattung → full SE value.
- `level = berufsart`: several jobs share a Gattung (2330, 5131, 5223) → sum of the assigned
  5-digit Berufsarten (`se_types`) + rest of the Gattung (onA, unpublished) proportionally; every
  published non-onA Berufsart must be assigned exactly once.
- Otherwise jobs are merged (Fallback A): SE label as `occupation`, former CH titles in `synonyms`
  (searchable in Berufssuche, old permalinks resolve); ESCO from the largest former entry
  (`text_from`). Merged entries are rated as a whole by the task pipeline. 22 merges, see
  `docs/audit_isco_codes.md`.
- SE value from sheet 2024; if a Gattung (or its women count) is «X», the pooled sheet 2022-2024.
- ISCO codes audited against SE labels (`docs/audit_isco_codes.md`): 21 corrected, 15 open.
  A new job/code needs a mapping row; when changing codes, adjust `lohn_profile_salarium.csv`
  (groups 11–14/22/24/26), run `update_loehne.py --offline`, then rate the entry (task pipeline).

### Task-based Exposure Pipeline (Rubrik v2.2) → `scores_aufgaben.csv` → `scores.csv`

Run **locally** (own subscription/keys). The app shows the result after `apply_task_scores.py`.

```
scores.csv (master data only: occupation, isco_code, synonyms, qualification, sector, esco_*)
  + esco_kompetenzen.csv (essential/optional, skill/knowledge)
  → task_inputs.py      input JSON per entry (German keys, pilot format) + input_hash = SHA-256(rubrik version, schema, input)
  → task_scorer.py      --provider claude|claude-cli|gemini, --runs 2 (seeded shuffle of the job order per run),
                        validation + 1 correction retry, auto run 3 if |Δ ζ-score| run1↔run2 > 1.0 (DRITTER_LAUF_SCHWELLE)
                        --batch submit|status|collect|followup → task_batch.py (Message Batches API / Gemini
                        Batch Mode; same prompts/schemas/validation; state bewertungen/<provider>/batches/<id>.json)
  → data/processed/bewertungen/<provider>/run<N>/<isco>_<slug>.json   {meta, bewertung[, rohantwort]}
    data/processed/bewertungen/<provider>/protokoll.jsonl            one line per call (status, usage)
  → task_aggregate.py   ζ, β, time savings, mode shares, P scores; per provider + combined; uncertainty flag
  → data/processed/scores_aufgaben.csv      (English columns, column_mapping.SCORES_AUFGABEN)
  → apply_task_scores.py  merge by (isco_code, occupation); fails if an entry has no rating (or vice versa);
                          timeframe_raw = aggregated timeframe, shifted by the SME factor (kmu_faktor.py);
                          adaptability recomputed; legacy_score kept → scores.csv (column_mapping.SCORES_SCHEMA)
  → task_vergleich.py   pilot (Abo runs, v2.1) vs. API Claude vs. API Gemini + Spearman vs. benchmarks
  → data/processed/bewertungen/vergleich.md
```

- **Rubric:** `src/scoring/rubrik/rubrik_aufgaben_v2_2.md` + `schema_v2_2.json` (`RUBRIK_VERSION = "2.2"`
  in `task_rubrik.py`). v2.2 = v2.1 (pilot, kept unchanged as `*_v2_1.*`) **plus** the block
  `zusammenfassung` (`haupt_risiko`, `begruendung`, `zeitrahmen` = adoption horizon in ≥ ~1/3 of CH
  firms); the block does not enter ζ/β/time savings. System prompt: `rubrik/bewerter_system_v2_2.md`
  + full rubric + schema (identical for every call → prompt cache). Levels: E0 not exposed, E1 chat LLM
  suffices, E2 needs LLM-based tools; threshold = time for the task cut by ≥ 50 % at equal quality.
- **Providers / settings** (constants in `task_scorer.py`, overridable via CLI):
  `claude-opus-5-5`, adaptive thinking, `output_config.effort="high"`, structured output via
  `output_config.format` (schema derived by `schema_fuer_claude()`: conditionals and type lists rewritten,
  then `anthropic.transform_schema`), streaming + `get_final_message()`, `max_tokens=64000`, server-side
  refusal fallback (`fallbacks="default"`, beta `server-side-fallback-2026-07-01`); the serving model is
  logged in `meta.model_served` / `meta.fallback`.
  `gemini-4-argon` via `models.generate_content`, `response_mime_type="application/json"` +
  `response_json_schema` (`schema_fuer_gemini()`: $refs inlined), `thinking_level="high"`,
  `max_output_tokens=65536` (batch: 32768, API limit), no temperature (ignored by the model), automatic function calling disabled;
  `--no-response-schema` = JSON mode only (schema is in the system prompt) — the batch API with `response_json_schema`
  returned 182/182 structurally broken answers on 14.10.2026 (sync 31/31 valid).
  `claude-cli`: Claude Code print mode (`claude -p --model claude-opus-5-5 --effort high --output-format json
  --tools "" --strict-mcp-config --no-session-persistence --setting-sources "" --system-prompt-file … --json-schema …`)
  with the user's own subscription; same prompt/schema/validation, empty temp cwd, `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1`,
  `ANTHROPIC_API_KEY`/`ANTHROPIC_AUTH_TOKEN` removed from the subprocess env (else billed via API); no fallback,
  no batch; correction turn sent as one prompt (original + previous answer + errors); subscription limit →
  `FatalerFehler` (re-run later, delta skips finished entries). Results in `bewertungen/claude-cli/`.
  **The app uses the claude-cli runs** (`task_aggregate.py` default `--claude-source claude-cli`).
  Before any call the provider SDK import is checked (`pruefe_pakete`, clear message + pip hint).
  Dry-run uses measured means from existing result files (`meta.usage`), else estimates
  (1.8 chars/token, `AUSGABE_TOKENS`, calibrated on the first Claude probe).
- **Validation:** every answer is checked against the original JSON schema (Draft 2020-12, incl.
  if/then rules) plus sum of time shares = 100 and isco_code/beruf = input (`task_rubrik.pruefe_bewertung`);
  mode × residual-time contradictions are only `meta.hinweise`.
- **Batch mode** (`task_batch.py`): custom_id `r<run>-<isco>_<slug>` (`^[a-zA-Z0-9_-]{1,64}$`), results
  matched strictly by custom_id (Gemini: `metadata.custom_id`, positional only if no response carries it).
  Claude batch requests omit `fallbacks` (rejected by the Batches API) → refusals logged
  (`meta.fehler_art = "refusal"`) and re-run synchronously with fallback via `followup --refusal-sync`;
  system prompt cached (`--cache-ttl 5m|1h`, default 5m). Gemini inline batches are split to stay < 20 MB.
  Results get `meta.modus = "batch"`, `batch_id`, `custom_id`; `collect` never overwrites a current valid
  file and skips already collected batches. `followup`: correction turn for invalid answers, retry for
  errored/expired/missing, run 3 for |Δζ| > threshold; entries in open batches are never re-submitted.
- **Delta:** a result is current if `status == ok`, same `input_hash`, same `rubrik_version`, same
  `model_requested` → skipped unless `--force`.
- **Aggregation** (`scores_aufgaben.csv`): `exposure` = 10·ζ (mean over all valid runs of both providers),
  `exposure_beta` = 10·β, `time_savings` = 10·Σ w·1[E1/E2]·(1 − residual), `share_*` = mode shares of the
  exposed time, `replaceable_time` = Σ w·1[ersetzend]·(1 − residual), `physical_automation` /
  `software_automation` = 10·Σ w·1[P1, p_art physisch|software]; `delta_provider` = |ζ Claude − ζ Gemini|;
  `uncertain` if delta_provider > 1.0, run spread > 1.0 or < 2 valid runs (`uncertain_reason`);
  `timeframe` = median over runs (tie → later); `main_risk`/`rationale` from the run closest to mean ζ
  (`text_source` = `<provider dir>/run<N>`, used by the Berufssuche to load the activity list).
- **Pilot results** (subagent runs, rubric v2.1) are versioned in `data/processed/bewertungen/pilot_abo/`.
- **Benchmarks:** `data/processed/benchmarks_isco4.csv` (ILO 2025 CC BY 4.0, Eloundou MIT, AEI CC-BY;
  see `benchmarks_isco4.README.md`). einstAIn values are deliberately not included (all rights reserved).
  The Methodik page computes Spearman ρ at runtime (employment-weighted per ISCO-4 code).

### Script Reference

| Script | Input | Output | Notes |
|--------|-------|--------|-------|
| `src/data/column_mapping.py` | — | — | Central old → new column mapping per CSV, dropped columns, final `SCORES_SCHEMA` |
| `src/data/migrate_columns.py` | `data/processed/*.csv` | same files | Idempotent rename (#53); `--dry-run`, `--data-dir`; refuses unknown/mixed columns or unmapped files; verifies cell values |
| `src/data/update_from_bfs.py` | `data/raw/su-d-40.02.03.02.01.03.10.xlsx` (or `se_berufe.csv`), `beruf_berufsart_mapping.csv` | `berufe_ch*.csv`, `scores.csv`, `se_berufe.csv` | BFS SE 2024: Berufsgattung/Berufsart per mapping, sets `employed_k`, `women_pct`, `synonyms`; `--sheet`, `--add-new`, `--dry-run` |
| `src/data/enrich_with_esco.py` | `berufe_ch.csv`, `berufe_ch_esco.csv` | `berufe_ch_esco.csv`, `berufe_ch_esco_verified.csv` | 6-stage search, hard ISCO consistency check + LLM validation; default: only jobs without `esco_match_quality`; `--job`, `--fix-wrong`, `--all` |
| `src/data/update_loehne.py` | LSE 2024 T17 (raw or `lse2024_monatslohn_isco.csv`), `lohn_profile_salarium.csv`, `lohn_salarium_abfragen.csv`, `statent_vzae_grossregion.csv`, `lohn_verhaeltnisse.csv` | `berufe_ch*.csv`, `scores.csv` | Sets `wage_median_chf`/`wage_source`/`wage_uncertain`; ratio overrides after Salarium; recomputes `adaptability` in scores.csv; `--offline` (no network), `--dry-run` |
| `src/data/fetch_bgs.py` | stats.swiss SDMX `DF_GGS_4` + STATENT PxWeb (online) or `bgs_grenzgaenger_noga.csv` + `statent_beschaeftigte_noga.csv` (`--offline`) | `grenzgaenger_anteil_branche.csv` (+ the two versioned inputs when online) | Cross-border commuter share per sector (annual mean of latest full year, latest quarter extra); reads/writes no scores; `--period YYYY\|YYYY-Qn`, `--dry-run` |
| `src/data/fetch_statent.py` | BFS DAM API `ts-x-06.02.01.01` (online) or `statent_groessenklassen_noga.csv` (`--offline`) | `kmu_anteil_branche.csv` (+ `statent_groessenklassen_noga.csv` when online); with `--apply-scores`: `scores.csv` | Large-firm share per sector (enterprises ≥250 employed); `--year`, `--dry-run`; `--apply-scores` rewrites only `large_firm_share`, `timeframe_sme_shift`, `timeframe` (from `timeframe_raw`) |
| `src/data/branche_neu_zuordnen.py` | `BRANCHE_MAP` | `berufe_ch*.csv`, `scores.csv` | Re-applies ISCO-prefix sector mapping to non-curated jobs; for changed rows recomputes SME timeframe columns and the mobility part of `adaptability` |
| `src/scoring/task_rubrik.py` | `rubrik/*_v2_1.*`, `rubrik/*_v2_2.*` | — | Shared: rubric version, system prompt, validation, provider schemas, metrics (ζ, β, Zeitersparnis, …) |
| `src/scoring/task_inputs.py` | `scores.csv` (master data), `esco_kompetenzen.csv` | (optional) `bewertungen/input/*.json` | Input per entry + input hash (English columns → German record keys); `PILOT_BERUFE` (15); `--pilot`, `--only` |
| `src/scoring/task_scorer.py` | inputs (in memory), `.env` keys / subscription | `bewertungen/<provider>/run<N>/*.json`, `protokoll.jsonl` | **Local only**; `--provider claude\|claude-cli\|gemini`, `--runs`, `--pilot`/`--only`, `--force`, `--dry-run [--count-tokens]`, `--max-parallel`, `--effort`/`--thinking-level`, `--model`, `--no-fallback`, `--no-third-run`, `--threshold`, `--no-response-schema`; batch: `--batch submit\|status\|collect\|followup`, `--batch-id`, `--refusal-sync`, `--cache-ttl` |
| `src/scoring/task_batch.py` | via `task_scorer.py --batch …` | `bewertungen/<provider>/batches/*.json`, `run<N>/*.json`, `protokoll.jsonl` | Batch mode for both providers (submit/status/collect/followup) |
| `src/scoring/task_aggregate.py` | `bewertungen/<provider>/run*/` | `scores_aufgaben.csv` | Per provider + combined; `--base-dir`, `--include-stale`, `--claude-source claude-cli\|claude` (default `claude-cli`) |
| `src/scoring/apply_task_scores.py` | `scores_aufgaben.csv`, `scores.csv`, `kmu_anteil_branche.csv` | `scores.csv` | Writes exactly `SCORES_SCHEMA`; fails loudly on missing/extra ratings or unknown sectors; idempotent; `--dry-run`, `--scores`, `--aufgaben`, `--kmu` |
| `src/scoring/kmu_faktor.py` | `kmu_anteil_branche.csv` | — | Shared SME timeframe shift (thresholds, `verschiebe_zeitrahmen`, `adjust_zeitrahmen_fuer_kmu`), list of the 21 sectors (`BRANCHEN`) |
| `src/scoring/adaptability_scorer.py` | `scores.csv` | `scores.csv` | Rule-based: (education 4 + wage 3 + sector mobility 1) × 10/8; no digital-affinity criterion since Oct 2026 (exposure as proxy would be circular); `setze_adaptabilitaet()` keeps numerically equal cells |
| `src/scoring/task_vergleich.py` | `bewertungen/pilot_abo/`, API runs, `benchmarks_isco4.csv` | `bewertungen/vergleich.md` | 15 pilot jobs + Spearman vs. benchmarks; `--pilot-runs`, `--base-dir`, `--include-stale` |
| historical (see Commands) | — | — | Exit immediately with a pointer to the current pipeline |

### ESCO Search Strategy (`enrich_with_esco.py`)

Six stages, first valid match wins. All ESCO requests use `selectedVersion=v1.2.1` (the API's
default version differs; two URIs return HTTP 500 without it).

1. ESCO REST API — direct German title search
2. ESCO REST API — LLM-generated alternative terms (4 synonyms/broader terms, DE/EN)
3. ESCO REST API — occupations of the ISCO group via `/resource/concept?uri=http://data.europa.eu/esco/isco/C{code}`
   → `_links.narrowerOccupation`, recursing through `narrowerConcept` (e.g. CH code 7200 → group 72).
   The search parameter `iscoGroup` is **ignored** by the API (returned all occupations
   alphabetically → e.g. the old Abfallmakler/3D-Druck contamination).
4. berufsberatung.ch — HTML scrape (site rebuilt, currently returns nothing)
5. Wikipedia DE — API search
6. LLM-generated description from job title + ISCO context (`description_source = KI-generiert`)

ESCO candidates must pass `isco_konsistenz()` **before** the LLM check: ESCO ISCO-4 == `isco_code`
→ `korrekt`; same 3-digit group or an entry of `ISCO_AUSNAHMEN` (documented ESCO conventions, e.g.
3221 FaGe → 5321, plus open #51 codes) → `plausibel`; otherwise rejected. Each URI is assigned to
one job only (`blocked_uris`; tested in `tests/test_esco_zuordnung.py`). `KNOWN_WRONG_MATCHES` is
empty since #52 — add current `occupation` titles there for `--fix-wrong`. A changed ESCO
assignment changes the task input hash → the entry must be re-rated.

### Streamlit App (`src/app/`)

Entry point: `src/app/app.py` — uses `st.navigation()` for multi-page routing. Shared helpers
(paths, loading, labels, colours, Spearman, rating-file lookup) in `src/app/gemeinsam.py`; the app
does not import `src/scoring` (no jsonschema in `requirements.txt`). Pages in `src/app/pages/`:

| File | Menu Title | Content |
|------|-----------|---------|
| `0_Startseite.py` | Startseite | Method intro, key metrics (weighted exposure, critical zone = exposure > 6 and adaptability below the employment-weighted median), women share highlight |
| `1_Treemap.py` | Treemap | Size = `employed_k`, colour selectable: exposure / time_savings / physical_automation |
| `2_Matrix.py` | Matrix | X = adaptability, Y = exposure or physical_automation; uncertain entries as diamonds; hover with Claude/Gemini values |
| `3_Branchen.py` | Branchen | Employment-weighted exposure per sector, cross-border context, convergence heatmap from task metrics |
| `4_Berufssuche.py` | Berufssuche | Search (occupation, synonyms, ESCO title), metrics, mode split, both model values if uncertain, activity list from the rating JSON (`text_source`) |
| `5_Methodik.py` | Methodik & Quellen | Rubric, metrics, models/runs, uncertainty, SME factor, validation (Spearman at runtime), old vs. new, data sources, limitations |

All charts use **Plotly** (sequential blue ramp for 0–10 values, fixed categorical slots).
App reads `data/processed/scores.csv`, `kmu_anteil_branche.csv`, `grenzgaenger_anteil_branche.csv`,
`benchmarks_isco4.csv` and the rating JSONs under `data/processed/bewertungen/`.

### Key Data Columns in `scores.csv` (schema `column_mapping.SCORES_SCHEMA`, in this order)

| Column | Source | Description |
|--------|--------|-------------|
| `occupation` | BFS SE | German Swiss job title (CH-ISCO-19, 4-digit groups) |
| `synonyms` | `beruf_berufsart_mapping.csv` | Former CH titles of merged entries (`; `-separated), searched in Berufssuche |
| `isco_code` | BFS SE | ISCO-08 / CH-ISCO-19 code |
| `employed_k` | BFS Strukturerhebung (SE) 2024 | Employed persons in thousands — 4-digit Gattung or assigned 5-digit Berufsarten; Σ per code = SE value |
| `women_pct` | BFS Strukturerhebung (SE) 2024 | Share of women in percent (0–100); pooled 2022–2024 if 2024 is «X» |
| `sector` | ISCO mapping | Sector (21 categories, `kmu_faktor.BRANCHEN`; values German) |
| `wage_median_chf` | BFS LSE 2024 (T17) | Median annual gross salary CHF = 2-digit group monthly median × 12; for groups 11–14/22/24/26 calibrated with Salarium profiles, for 2211/2212/2221 documented ratio factors (`update_loehne.py`) |
| `wage_source` | `update_loehne.py` | `LSE2024_2d`, `LSE2024_2d+Salarium`, `LSE2024_2d+Verhaeltnis`, fallback `LSE2024_1d` / `LSE2024_total` |
| `wage_uncertain` | `lohn_verhaeltnisse.csv` | `True` = no documented wage relation (2261 dentists, 2262 pharmacists) |
| `qualification` | Curated list / ISCO major group | Education level: Tertiär / Sekundär II / Keine Ausbildung |
| `esco_uri` | ESCO v1.2.1 | ESCO occupation URI — empty for 3 of 187 jobs (fallback description); unique |
| `esco_title` | ESCO v1.2.1 | ESCO occupation title (German, from the API); job title for fallbacks |
| `esco_description` | ESCO v1.2.1 or fallback | ESCO description (184 jobs) or fallback text (3 jobs) |
| `description_source` | `enrich_with_esco.py` | `ESCO` (iff `esco_uri` set), `berufsberatung.ch`, `Wikipedia`, `KI-generiert` |
| `esco_isco_code` | ESCO v1.2.1 | ISCO-4 group of the ESCO occupation (empty for fallbacks) |
| `esco_match_quality` | #52 audit / `enrich_with_esco.py` | `korrekt` (same ISCO-4, fits), `plausibel` (same ISCO-3, documented exception or partial match), `fallback` (no URI) |
| `exposure` | task pipeline | **Main score** 0–10 = 10·ζ, share of working time in E1/E2 tasks; mean over all valid runs of both models |
| `exposure_beta` | task pipeline | 10·β (E2 counted half) |
| `time_savings` | task pipeline | 10·Σ w·1[E1/E2]·(1 − residual human time) |
| `share_replacing` / `share_delegating` / `share_assisting` | task pipeline | Mode shares of the exposed time (0–1; empty if exposure = 0) |
| `replaceable_time` | task pipeline | Share of total time saved in «ersetzend» tasks (0–1) |
| `physical_automation` / `software_automation` | task pipeline | 10·Σ w·1[P1] by type (non-generative technology; not in `exposure`) |
| `low_confidence_share` | task pipeline | Time share of tasks rated with confidence «tief» |
| `main_risk`, `rationale` | task pipeline | Texts from the run closest to the mean ζ (`text_source`) |
| `exposure_claude`, `exposure_gemini` | task pipeline | Mean 10·ζ per model (Claude = subscription runs) |
| `delta_provider`, `spread_runs` | task pipeline | \|Claude − Gemini\|; max. run spread within a model |
| `uncertain`, `uncertain_reason` | task pipeline | `True` if delta_provider > 1.0, spread > 1.0 or < 2 valid runs; reason text |
| `n_runs_claude`, `n_runs_gemini` | task pipeline | Number of valid runs per model |
| `text_source` | task pipeline | `<provider dir>/run<N>` of the text run → `bewertungen/<text_source>/<isco>_<slug>.json` |
| `timeframe_raw` | task pipeline | Median adoption timeframe of all runs (1-2 / 3-5 / 5-10 / >10 Jahre) |
| `large_firm_share` | BFS STATENT 2024 (`kmu_faktor.py`) | Share of sector's employed persons in enterprises ≥250 employed; empty for Öff. Verwaltung |
| `timeframe_sme_shift` | `kmu_faktor.py` | −1 (share ≥50 %), 0, +1 (share <15 %) |
| `timeframe` | `kmu_faktor.py` | `timeframe_raw` shifted by `timeframe_sme_shift` |
| `adaptability` | `adaptability_scorer.py` | Adaptability 0–10 (rule-based: education, wage points on a fixed 50k–150k CHF scale, sector mobility; scaled × 10/8; independent of exposure). App critical zone = exposure > 6 and adaptability below the employment-weighted median (`gemeinsam.schwelle_anpassung`) |
| `legacy_score` | former method | Old final score (`score_ch`, Karpathy-style holistic rating + sector/wage deltas); only for the old-vs-new comparison on the Methodik page; empty for the 8 entries added later |

## Datenqualität

Siehe `DATA_QUALITY.md` für ESCO-Abdeckung und Match-Qualität, Korrektur-Historie und
Quality-Prozess; ESCO-Audit #52 mit Entscheid je Eintrag in `docs/audit_esco_zuordnungen.md`.

## Deployment (HuggingFace Spaces)

```bash
# Push to HuggingFace (Streamlit Space)
git push hf main

# The HF remote URL contains credentials — do NOT display or log it
# Remote is named 'hf', see: git remote -v
```

HuggingFace Spaces runs `streamlit run src/app/app.py` automatically.
`data/processed/scores.csv` and the rating JSONs are committed and available at runtime (no DB needed).

## Security Notes

- `.env` is in `.gitignore` — never commit it
- `ANTHROPIC_API_KEY` is only needed for API rating (`--provider claude`), not for running the app
- `GEMINI_API_KEY` (or `GOOGLE_API_KEY`, which wins if both are set) only for `task_scorer.py --provider gemini`
- HF token is embedded in the `hf` remote URL — do not echo `git remote -v` in logs
