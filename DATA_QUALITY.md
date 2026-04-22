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
