# Datenqualität & Korrektur-Historie

## ESCO-Abdeckung (Stand 2026-04)

- **197 / 204** Berufe mit ESCO-URI (offizielle EU-Klassifikation)
- **7 Berufe** ohne ESCO-URI (Fallback-Beschreibung aus Stufe 4–6):
  Logistiker/in EFZ, Hauswirtschaftler/in EFZ, Telematiker/in EFZ, Drogist/in,
  Handelsmakler, Isolierer, Reiseverkehrsfachkräfte
- Genaue Fallback-Stufe (berufsberatung.ch / Wikipedia / Haiku) nicht persistiert — Issue #24

## Bekannte ESCO-Fehlzuordnungen (`KNOWN_WRONG_MATCHES`)

25 Berufe mit bestätigten Fehlmatches; werden via `--fix-wrong` repariert:

```
# Gruppe 1: verifizierte Fehlmatches
Bankkaufmann/-frau              → Abfallmakler (korrekt: Bankbediensteter)
Polymechaniker/in EFZ           → Brennschneider (korrekt: Industriemechaniker)
Logistiker/in EFZ               → Abfallmakler
Immobilienbewirtschafter/in     → Abfallmakler
Automatiker/in EFZ              → 3D-Druck-Techniker
Bauführer/in                    → 3D-Druck-Techniker
Grafiker/in                     → Kartograf
Hochbauzeichner/in EFZ          → 3D-Druck-Techniker
Elektroplaner/in EFZ            → 3D-Druck-Techniker

# Gruppe 1b: Brennschneider-URI (5d46e448) fälschlicherweise zugewiesen
Primarlehrer/in
Sekundarlehrer/in
Pflegeassistent/in
Lastwagenfahrer/in
Arztpraxisassistent/in
Lieferwagenfahrer/in
Hauswirtschaftler/in EFZ
Telematiker/in EFZ
Drogist/in

# Gruppe 2: Fehlmatches in berufe_ch_esco.csv (unverifiziert)
PR-Spezialist/in                → Preiskalkulation
Reinigungspersonal...           → Netzverankerung Aquakultur
Leitende Verwaltungsbedienstete → Leitender Hauswirtschafter
Technische Verkaufsfachkräfte   → Experte Geoinformationssysteme
Bürokräfte Transportwirtschaft  → Lebensmitteltechniker
Physiotherapeut. Techniker...   → Anästhesietechn. Assistent
Fachkräfte Personal & Schulung  → Hydraulik-Fachkraft
```

## Korrektur-Historie

| Datum | Korrektur | Betroffene Berufe |
|-------|-----------|-------------------|
| 2026-04 | Brennschneider-Kontamination (Batch API Artefakt) | 14 Berufe via `fix_brennschneider_contamination.py` |
| 2026-04 | Vollständiges Quality Audit | 12 weitere Berufe via `full_quality_audit.py` |
| 2026-04 | Manuelle Korrektur | Grafiker/in (Score 3.2 → 6.2, war Graveur-Beschreibung) |
| 2026-04 | Refactor Batch API → synchron + Hash-Delta | Alle 204 Berufe neu gescort; `beschreibung_hash` eingeführt |
| 2026-04 | Brennschneider-Kontamination (ESCO-Metadaten) | 9 Berufe in `berufe_ch_esco_verified.csv` + `scores.csv` bereinigt |
| 2026-04 | URI-Duplikat-Schutz | `enrich_with_esco.py`: `blocked_uris` verhindert Kreuz-Kontamination |
| 2026-10 | Löhne auf LSE 2024 umgestellt (#45), `update_loehne.py` | Alle 204 Berufe: `lohn_median_chf`, `lohn_quelle`; regelbasiert neu: `lohnklasse`, `delta_lohn`, `score_ch`, `adaptabilitaet` (inkl. Altlasten), `delta_branche` (Pharma-Ausnahme 2131/2145) |

## Löhne (LSE 2024)

`lohn_median_chf` stammt seit Issue #45 aus der **BFS LSE 2024** (T17, Asset 36355224, nur
2-stellige CH-ISCO-19-Gruppen, Monatsmedian × 12) statt aus der geschätzten `LOHN_MAP`
(«LSE 2022, geschätzt») bzw. den nicht belegbaren 4-stelligen Werten aus `build_berufeliste.py`.
Herkunft je Beruf in `lohn_quelle`:

- `LSE2024_2d` — Gruppenmedian (153 Berufe, inkl. Leitende Verwaltungsbedienstete 1112:
  Salarium hat für Führungskräfte der öffentlichen Verwaltung, NOGA 84, keine konsistenten Werte)
- `LSE2024_2d+Salarium` — Gruppen 11–14, 22, 24, 26: Gruppenmedian × S_j / S̄_g, wobei S̄_g
  das beschäftigungsgewichtete Mittel der Salarium-Werte der Gruppe ist (gewichtetes Mittel der
  Löhne = LSE-Gruppenmedian; 51 Berufe; Profile in `lohn_profile_salarium.csv`, Antworten in
  `lohn_salarium_abfragen.csv`) — **Modellschätzung**
- `LSE2024_1d` / `LSE2024_total` — Fallback für Gruppen ohne LSE-Wert (01–03, 63, 95; derzeit 0 Berufe)

Bekannte Schwächen: Berufe derselben 2-stelligen Gruppe ausserhalb der Salarium-Gruppen haben
identische Löhne (z. B. Informatiker/in EFZ = Softwareentwickler/in, Kassierer/in = Detailhandel);
die Normierung hängt von den Beschäftigtenzahlen der App-Berufe ab (nicht von der vollen Gruppe);
`beschaeftigte_1000` in `scores.csv` weicht bei 104 Berufen von `berufe_ch.csv` (SE 2024) ab —
für die Gewichte wird `berufe_ch.csv` verwendet;
Salarium (Privatsektor, ohne Kader im Normprofil) unterschätzt Spitzenlöhne, v. a. Fachärzte.
Saubere Alternative: BFS-Sonderauswertung 3-/4-stellig (lohn@bfs.admin.ch).

## Quality Audit Prozess

`full_quality_audit.py` prüft ob `haupt_risiko`/`begruendung` zum Berufstitel passt:

1. **Phase 1 (Haiku)**: Prüft alle 204 Beschreibungen auf inhaltliche Korrektheit
2. **Phase 2 (Haiku)**: Generiert korrekte Berufsbeschreibung für fehlerhafte Jobs
3. **Phase 3 (Sonnet)**: Re-Scoring mit korrigierten Beschreibungen

Wann ausführen: nach `--fix-wrong`-Läufen oder bei Verdacht auf neue Artefakte.
Report: `data/processed/audit_report.json`

## ESCO API — Hinweis

Die ESCO REST API ist im **Anthropic Cloud-Environment geblockt**. Folgende Skripte
müssen **lokal** ausgeführt werden:
`enrich_with_esco.py`, `verify_esco_matches.py`, `patch_unmatched.py`
