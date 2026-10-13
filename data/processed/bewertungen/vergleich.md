# Vergleich aufgabenbasierte Bewertung: Pilot (Abo) vs. API

Rubrik: Pilot v2.1, API v2.2 (v2.2 = v2.1 + Block «zusammenfassung», der nicht in die Kennzahlen einfliesst). ζ-Score = 10·Σ w·1[E1 oder E2]; Zeitersparnis-Score = 10·Σ w·1[E1/E2]·(1 − Restzeit).

Pilot-Läufe: run1_v21, run2_v21 · Einträge mit API-Bewertung: Claude 15, Gemini 15 von 187

## Pilotberufe (15): ζ-Score je Quelle

| ISCO | Beruf | Pilot | Claude | Gemini | kombiniert | Δ Claude−Pilot | Δ Gemini−Pilot | Δ Claude−Gemini | Zeitersparnis P / C / G | Läufe P/C/G |
|---|---|---|---|---|---|---|---|---|---|---|
| 2431 | Fachkräfte in Marketing und Werbung | 7.3 | 6.5 | 7.8 | 7.1 | -0.8 | 0.5 | -1.3 | 4.8 / 4.3 / 4.9 | 2/2/2 |
| 2512 | Softwareentwickler | 7.3 | 7.6 | 8.3 | 7.9 | 0.3 | 1.0 | -0.7 | 5.1 / 5.3 / 5.9 | 2/2/2 |
| 2643 | Übersetzer, Dolmetscher und andere Linguisten | 7.3 | 8.0 | 9.0 | 8.5 | 0.8 | 1.8 | -1.0 | 4.4 / 4.8 / 5.9 | 2/2/2 |
| 4110 | Allgemeine Bürokräfte | 7.0 | 6.7 | 8.3 | 7.5 | -0.3 | 1.3 | -1.6 | 5.2 / 5.0 / 6.3 | 2/2/2 |
| 3353 | Fachkräfte in Sozialverwaltung und -versicherung | 6.7 | 6.3 | 7.3 | 6.8 | -0.4 | 0.6 | -1.0 | 4.8 / 4.4 / 5.3 | 2/2/2 |
| 2642 | Journalisten | 6.1 | 6.0 | 7.2 | 6.6 | -0.1 | 1.1 | -1.2 | 4.0 / 3.9 / 4.8 | 2/3/3 |
| 2411 | Wirtschaftsprüfer, Steuerberater und verwandte Berufe | 6.0 | 8.5 | 8.8 | 8.6 | 2.5 | 2.8 | -0.3 | 3.9 / 5.5 / 5.5 | 2/2/2 |
| 2166 | Grafik- und Multimediadesigner | 4.8 | 5.1 | 6.0 | 5.5 | 0.3 | 1.3 | -1.0 | 3.4 / 3.4 / 4.0 | 2/2/2 |
| 2341 | Primarlehrer/in | 3.0 | 2.5 | 2.5 | 2.5 | -0.5 | -0.6 | 0.1 | 1.9 / 1.6 / 1.5 | 2/2/2 |
| 2211 | Arzt/Ärztin (Allgemeinmedizin) | 2.3 | 2.7 | 3.2 | 2.9 | 0.5 | 0.9 | -0.5 | 1.4 / 1.6 / 1.9 | 2/2/2 |
| 2221 | Dipl. Pflegefachperson | 2.3 | 2.1 | 2.3 | 2.2 | -0.2 | 0.0 | -0.2 | 1.4 / 1.3 / 1.4 | 2/2/2 |
| 7411 | Elektriker/in EFZ | 1.0 | 0.9 | 1.0 | 0.9 | -0.2 | 0.0 | -0.2 | 0.6 / 0.5 / 0.6 | 2/2/2 |
| 5223 | Verkäufer in Handelsgeschäften | 0.2 | 0.5 | 0.5 | 0.5 | 0.4 | 0.4 | 0.0 | 0.1 / 0.4 / 0.4 | 2/2/2 |
| 8332 | Lastwagenfahrer/in | 0.2 | 0.3 | 0.4 | 0.3 | 0.1 | 0.2 | -0.1 | 0.1 / 0.2 / 0.2 | 2/2/2 |
| 9313 | Hilfsarbeiter im Hochbau | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 / 0.0 / 0.0 | 2/2/2 |

## Übereinstimmung zwischen den Quellen (Pilotberufe)

| Paar | n | Spearman ρ (ζ) | mittlere Differenz | MAE | ρ (Zeitersparnis) |
|---|---|---|---|---|---|
| API Claude – Pilot (Abo) | 15 | 0.90 | 0.16 | 0.48 | 0.90 |
| API Gemini – Pilot (Abo) | 15 | 0.91 | 0.73 | 0.81 | 0.95 |
| API Claude – API Gemini | 15 | 1.00 | -0.58 | 0.58 | 0.98 |
| API kombiniert – Pilot (Abo) | 15 | 0.90 | 0.45 | 0.56 | 0.94 |

## Claude über das Abo (claude -p) vs. API (Pilotberufe)

Gleicher System-Prompt, gleiches Schema und gleiche Validierung; Abo-Läufe unter bewertungen/claude-cli/.

| ISCO | Beruf | API Claude | Abo-CLI | Δ CLI−API | Pilot | Δ CLI−Pilot | Zeitersparnis API / CLI | Läufe API/CLI |
|---|---|---|---|---|---|---|---|---|
| 2411 | Wirtschaftsprüfer, Steuerberater und verwandte Berufe | 8.5 | 8.8 | 0.3 | 6.0 | 2.8 | 5.5 / 5.7 | 2/2 |
| 2643 | Übersetzer, Dolmetscher und andere Linguisten | 8.0 | 8.0 | 0.0 | 7.3 | 0.8 | 4.8 / 5.0 | 2/2 |
| 2512 | Softwareentwickler | 7.6 | 7.5 | -0.0 | 7.3 | 0.3 | 5.3 / 5.3 | 2/3 |
| 4110 | Allgemeine Bürokräfte | 6.7 | 6.7 | -0.1 | 7.0 | -0.4 | 5.0 / 5.0 | 2/2 |
| 2431 | Fachkräfte in Marketing und Werbung | 6.5 | 7.3 | 0.8 | 7.3 | -0.1 | 4.3 / 4.9 | 2/2 |
| 3353 | Fachkräfte in Sozialverwaltung und -versicherung | 6.3 | 7.0 | 0.8 | 6.7 | 0.4 | 4.4 / 5.0 | 2/2 |
| 2642 | Journalisten | 6.0 | 6.4 | 0.4 | 6.1 | 0.3 | 3.9 / 4.3 | 3/3 |
| 2166 | Grafik- und Multimediadesigner | 5.1 | 5.0 | -0.1 | 4.8 | 0.3 | 3.4 / 3.5 | 2/2 |
| 2211 | Arzt/Ärztin (Allgemeinmedizin) | 2.7 | 2.1 | -0.6 | 2.3 | -0.2 | 1.6 / 1.3 | 2/2 |
| 2341 | Primarlehrer/in | 2.5 | 2.4 | -0.1 | 3.0 | -0.6 | 1.6 / 1.5 | 2/2 |
| 2221 | Dipl. Pflegefachperson | 2.1 | 2.2 | 0.1 | 2.3 | -0.1 | 1.3 / 1.3 | 2/2 |
| 7411 | Elektriker/in EFZ | 0.9 | 0.9 | 0.1 | 1.0 | -0.1 | 0.5 / 0.5 | 2/2 |
| 5223 | Verkäufer in Handelsgeschäften | 0.5 | 0.6 | 0.1 | 0.2 | 0.4 | 0.4 / 0.4 | 2/2 |
| 8332 | Lastwagenfahrer/in | 0.3 | 0.3 | 0.1 | 0.2 | 0.2 | 0.2 / 0.2 | 2/2 |
| 9313 | Hilfsarbeiter im Hochbau | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 / 0.0 | 2/2 |

| Paar | n | Spearman ρ (ζ) | mittlere Differenz | MAE | ρ (Zeitersparnis) |
|---|---|---|---|---|---|
| Abo-CLI Claude – API Claude | 15 | 0.98 | 0.10 | 0.21 | 0.99 |
| Abo-CLI Claude – Pilot (Abo) | 15 | 0.91 | 0.26 | 0.44 | 0.91 |
| Abo-CLI Claude – API Gemini | 15 | 0.97 | -0.47 | 0.48 | 0.96 |

## Spearman ρ gegen externe Benchmarks — Pilotberufe

| Benchmark | Pilot (Abo) ζ (n) | API Claude ζ (n) | API Gemini ζ (n) | API kombiniert ζ (n) |
|---|---|---|---|---|
| ILO 2025 (Gmyrek et al.) | 0.88 (15) | 0.86 (15) | 0.88 (15) | 0.86 (15) |
| Eloundou et al. 2024 (β) | 0.87 (15) | 0.89 (15) | 0.90 (15) | 0.89 (15) |
| AEI observed exposure | 0.71 (15) | 0.70 (15) | 0.69 (15) | 0.70 (15) |

## Spearman ρ gegen externe Benchmarks — alle bewerteten Einträge

| Benchmark | API Claude ζ (n) | API Gemini ζ (n) | API kombiniert ζ (n) |
|---|---|---|---|
| ILO 2025 (Gmyrek et al.) | 0.86 (15) | 0.88 (15) | 0.86 (15) |
| Eloundou et al. 2024 (β) | 0.89 (15) | 0.90 (15) | 0.89 (15) |
| AEI observed exposure | 0.70 (15) | 0.69 (15) | 0.70 (15) |

Benchmarks: ILO 2025 (CC BY 4.0), Eloundou et al. 2024 (MIT), Anthropic Economic Index (CC-BY); siehe data/processed/benchmarks_isco4.README.md.
