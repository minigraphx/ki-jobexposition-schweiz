# benchmarks_isco4.csv — externe Vergleichswerte je ISCO-08-4-Steller

Nur für den Vergleich in `src/scoring/task_vergleich.py` (Spearman-Rangkorrelation); die Werte
fliessen in keinen Score der App ein. Eine Zeile je ISCO-Code (184 Codes; 178 der 179 Einträge
in `scores.csv` abgedeckt — CH-ISCO `7200` hat keinen 4-stelligen ISCO-08-Gegenwert).

| Spalte | Quelle | Mass | Lizenz |
|---|---|---|---|
| `ilo25_mean` | ILO, Gmyrek et al. (2025), Working Paper 140, «Refined Global Index» — [github.com/pgmyrek/2025_GenAI_scores_ISCO08](https://github.com/pgmyrek/2025_GenAI_scores_ISCO08) | mittlerer Task-Score 0–1, ISCO-08 4-stellig nativ | CC BY 4.0 (Quellenangabe ILO; die Übernahme ist eine Adaption, nicht von der ILO geprüft) |
| `eloundou_gpt4_beta` | Eloundou, Manning, Mishkin & Rock (2024), «GPTs are GPTs», *Science* — [github.com/openai/GPTs-are-GPTs](https://github.com/openai/GPTs-are-GPTs) (`occ_level.csv`) | GPT-4-Rating β = E1 + 0.5·E2, O*NET-SOC → ISCO-08 über BLS-Crosswalk (beschäftigungsgewichtet) | MIT (Repository); Crosswalk BLS: US-Government, public domain |
| `aei_observed_exposure` | Anthropic Economic Index, «observed exposure» (Massenkoff & McCrory, März 2026) — [huggingface.co/datasets/Anthropic/EconomicIndex](https://huggingface.co/datasets/Anthropic/EconomicIndex) | beobachtete Nutzung (automatisiert = 1, augmentativ = 0.5), SOC 2018 → ISCO-08; 3 Codes ohne Wert | Daten CC-BY |

Mehrere Berufe mit gleichem ISCO-Code teilen sich die Werte. Weitere im Projekt geprüfte
Benchmarks (u. a. einstAIn / jobs.einstain.ch, «All rights reserved») sind bewusst **nicht**
übernommen.
