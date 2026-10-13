# Vergleich aufgabenbasierte Bewertung: Pilot (Abo) vs. API

Rubrik: Pilot v2.1, API v2.2 (v2.2 = v2.1 + Block «zusammenfassung», der nicht in die Kennzahlen einfliesst). ζ-Score = 10·Σ w·1[E1 oder E2]; Zeitersparnis-Score = 10·Σ w·1[E1/E2]·(1 − Restzeit).

Pilot-Läufe: run1_v21, run2_v21 · Einträge mit API-Bewertung: Claude 15, Gemini 13 von 187

## Pilotberufe (15): ζ-Score je Quelle

| ISCO | Beruf | Pilot | Claude | Gemini | kombiniert | Δ Claude−Pilot | Δ Gemini−Pilot | Δ Claude−Gemini | Zeitersparnis P / C / G | Läufe P/C/G |
|---|---|---|---|---|---|---|---|---|---|---|
| 2431 | Fachkräfte in Marketing und Werbung | 7.3 | 6.5 | 8.0 | 7.0 | -0.8 | 0.7 | -1.5 | 4.8 / 4.3 / 5.2 | 2/2/1 |
| 2512 | Softwareentwickler | 7.3 | 7.6 | 8.0 | 7.7 | 0.3 | 0.8 | -0.5 | 5.1 / 5.3 / 5.6 | 2/2/1 |
| 2643 | Übersetzer, Dolmetscher und andere Linguisten | 7.3 | 8.0 | 9.0 | 8.3 | 0.8 | 1.8 | -1.0 | 4.4 / 4.8 / 6.0 | 2/2/1 |
| 4110 | Allgemeine Bürokräfte | 7.0 | 6.7 | 8.5 | 7.3 | -0.3 | 1.5 | -1.8 | 5.2 / 5.0 / 6.4 | 2/2/1 |
| 3353 | Fachkräfte in Sozialverwaltung und -versicherung | 6.7 | 6.3 | 7.0 | 6.5 | -0.4 | 0.4 | -0.8 | 4.8 / 4.4 / 5.1 | 2/2/1 |
| 2642 | Journalisten | 6.1 | 6.0 | 6.5 | 6.1 | -0.1 | 0.4 | -0.5 | 4.0 / 3.9 / 4.5 | 2/3/1 |
| 2411 | Wirtschaftsprüfer, Steuerberater und verwandte Berufe | 6.0 | 8.5 | 9.0 | 8.7 | 2.5 | 3.0 | -0.5 | 3.9 / 5.5 / 5.7 | 2/2/1 |
| 2166 | Grafik- und Multimediadesigner | 4.8 | 5.1 | 6.0 | 5.4 | 0.3 | 1.3 | -1.0 | 3.4 / 3.4 / 3.8 | 2/2/1 |
| 2341 | Primarlehrer/in | 3.0 | 2.5 | 2.6 | 2.5 | -0.5 | -0.4 | -0.1 | 1.9 / 1.6 / 1.6 | 2/2/1 |
| 2221 | Dipl. Pflegefachperson | 2.3 | 2.1 | – | 2.1 | -0.2 | – | – | 1.4 / 1.3 / – | 2/2/0 |
| 2211 | Arzt/Ärztin (Allgemeinmedizin) | 2.3 | 2.7 | 3.0 | 2.8 | 0.5 | 0.8 | -0.3 | 1.4 / 1.6 / 1.8 | 2/2/1 |
| 7411 | Elektriker/in EFZ | 1.0 | 0.9 | 1.0 | 0.9 | -0.2 | 0.0 | -0.2 | 0.6 / 0.5 / 0.6 | 2/2/1 |
| 5223 | Verkäufer in Handelsgeschäften | 0.2 | 0.5 | – | 0.5 | 0.4 | – | – | 0.1 / 0.4 / – | 2/2/0 |
| 8332 | Lastwagenfahrer/in | 0.2 | 0.3 | 0.3 | 0.3 | 0.1 | 0.2 | -0.1 | 0.1 / 0.2 / 0.2 | 2/2/1 |
| 9313 | Hilfsarbeiter im Hochbau | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 / 0.0 / 0.0 | 2/2/1 |

## Übereinstimmung zwischen den Quellen (Pilotberufe)

| Paar | n | Spearman ρ (ζ) | mittlere Differenz | MAE | ρ (Zeitersparnis) |
|---|---|---|---|---|---|
| API Claude – Pilot (Abo) | 15 | 0.89 | 0.16 | 0.48 | 0.90 |
| API Gemini – Pilot (Abo) | 13 | 0.86 | 0.78 | 0.85 | 0.89 |
| API Claude – API Gemini | 13 | 0.98 | -0.62 | 0.62 | 0.95 |
| API kombiniert – Pilot (Abo) | 15 | 0.89 | 0.33 | 0.49 | 0.90 |

## Spearman ρ gegen externe Benchmarks — Pilotberufe

| Benchmark | Pilot (Abo) ζ (n) | API Claude ζ (n) | API Gemini ζ (n) | API kombiniert ζ (n) |
|---|---|---|---|---|
| ILO 2025 (Gmyrek et al.) | 0.88 (15) | 0.86 (15) | 0.89 (13) | 0.86 (15) |
| Eloundou et al. 2024 (β) | 0.87 (15) | 0.89 (15) | 0.85 (13) | 0.89 (15) |
| AEI observed exposure | 0.71 (15) | 0.70 (15) | 0.76 (13) | 0.70 (15) |

## Spearman ρ gegen externe Benchmarks — alle bewerteten Einträge

| Benchmark | API Claude ζ (n) | API Gemini ζ (n) | API kombiniert ζ (n) |
|---|---|---|---|
| ILO 2025 (Gmyrek et al.) | 0.86 (15) | 0.89 (13) | 0.86 (15) |
| Eloundou et al. 2024 (β) | 0.89 (15) | 0.85 (13) | 0.89 (15) |
| AEI observed exposure | 0.70 (15) | 0.76 (13) | 0.70 (15) |

Benchmarks: ILO 2025 (CC BY 4.0), Eloundou et al. 2024 (MIT), Anthropic Economic Index (CC-BY); siehe data/processed/benchmarks_isco4.README.md.

## Warnungen

- gemini/run1/2221_dipl_pflegefachperson.json: fehlgeschlagen — nicht verwendet
