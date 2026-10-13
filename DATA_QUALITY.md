# Datenqualität & Korrektur-Historie

## ESCO-Abdeckung und Match-Qualität (Stand 2026-10, nach #52)

Referenz: **ESCO v1.2.1** (API mit `selectedVersion=v1.2.1`, CSV-Download de/en), © Europäische
Union, CC BY 4.0; Beschreibungen ggf. gekürzt/angepasst. Entscheid und Begründung je Eintrag:
`docs/audit_esco_zuordnungen.md`.

| `esco_match_qualitaet` | Einträge | Beschäftigte (Tsd.) | Bedeutung |
|---|---|---|---|
| korrekt | 158 | 3'287.9 | ESCO-ISCO-4-Steller = `isco_code`, Tätigkeit abgedeckt |
| plausibel | 18 | 252.9 | gleiche 3-stellige Gruppe, dokumentierte Ausnahme (`ISCO_AUSNAHMEN`) oder Teilgebiet |
| fallback | 3 | 26.1 | kein passender ESCO-Beruf: Drogist/in, Gymnasiallehrer/in, Maschinenführer/in (`KI-generiert`) |

- **176 / 179** Einträge mit ESCO-URI, jede URI genau einmal; `esco_isco_code` = ISCO-Gruppe des
  ESCO-Berufs; Titel deutsch aus der API. `beschreibung_quelle = ESCO` genau dann, wenn eine URI
  gesetzt ist (Tests in `tests/test_esco_zuordnung.py`).
- Vorher (Audit der bisherigen Zuordnungen auf die 179 Einträge übertragen): 96 korrekt,
  45 plausibel-generisch, **33 falsch (950 Tsd. Beschäftigte)**, 5 ohne URI — davon 4 mit
  `beschreibung_quelle = ESCO`. Auf den 204 Berufen vor #51: 107 / 51 / 39 falsch (987 Tsd., ~26 %) / 7.
- **ESCO-Kompetenzen** je Eintrag (wesentlich/optional, skill/knowledge, deutsch):
  `data/processed/esco_kompetenzen.csv` (10'032 Zeilen, aus dem CSV v1.2.1; mit der API abgeglichen).
- `beschreibung_hash` wurde nicht neu berechnet → `exposure_scorer.py` bewertet die 89 Einträge mit
  neuer Beschreibung beim nächsten Lauf neu (zusammen mit den 22 zusammengelegten: 101 Einträge).
  Bis dahin beruhen deren Scores auf der alten (teils falschen) Beschreibung.
- Offen: Fälle mit offenem ISCO-Code aus #51 (3312, 2422, 4415, 7421, 2146, 8211, 3522) nach
  Klärung des Codes neu zuordnen; berufsberatung.ch-Scraper an die neu aufgebaute Website
  anpassen (liefert derzeit nichts).

## ESCO-Fehlzuordnungen: Ursache und Behebung (#52, #48)

1. **Stufe 3 von `enrich_with_esco.py`** suchte mit `iscoGroup=…`; die ESCO-API ignoriert diesen
   Parameter und liefert alle Berufe alphabetisch («3D-Animationstechniker, 3D-Artist,
   Abfallbeauftragter …») — daher u. a. die früheren Abfallmakler- und 3D-Druck-Treffer.
   Jetzt: Concept-Endpunkt `/resource/concept?uri=http://data.europa.eu/esco/isco/C{code}` →
   `narrowerOccupation` (rekursiv über `narrowerConcept`).
2. **Keine ISCO-Prüfung:** Ein Sprachmodell bewertete nur Titel und Beschreibung (z. B. Textsuche
   «Dipl.» → Diplomat/in für die Dipl. Pflegefachperson, #48; Kameramann/-frau für Detailhandel,
   Restaurant- und Hotelfach). Jetzt harte Prüfung `isco_konsistenz()` vor der inhaltlichen Prüfung;
   32 der 39 Fehler wären so abgefangen worden.
3. **Version nicht fixiert:** Die Standardversion der API weicht von v1.2.1 ab (andere Texte, z. B.
   PTA unter 3213 statt 2262; zwei URIs mit HTTP 500). Jetzt `selectedVersion=v1.2.1` überall.
4. **Mehrfach vergebene URIs** (13 URIs für 30 Berufe) durch Teil-Läufe und Handkorrekturen.
   Jetzt Test auf Eindeutigkeit.
5. `verify_esco_matches.py` / `patch_unmatched.py` akzeptierten Treffer schon bei gleicher
   2-stelliger ISCO-Gruppe und waren nicht mehr lauffähig → als historisch markiert.

`KNOWN_WRONG_MATCHES` ist seit #52 leer (die früheren 25 Einträge — Abfallmakler-, Brennschneider-
und 3D-Druck-Kontamination — sind behoben; 13 davon waren schon korrekt, viele Titel sind seit #51
zusammengelegt). Neue bestätigte Fehlzuordnungen dort mit dem aktuellen `beruf`-Titel eintragen und
`enrich_with_esco.py --fix-wrong` ausführen. «Dipl.»-Titel: nur Dipl. Pflegefachperson (geprüft).

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
| 2026-10 | Beschäftigte ohne Doppelzählung, ISCO-Audit (#51) | 21 ISCO-Codes korrigiert, 22 Zusammenlegungen (204 → 179 Berufe), 2330/5131/5223 über SE-Berufsarten aufgeteilt; `beschaeftigte_1000`/`frauen_pct` in allen CSVs aus SE 2024; Löhne mit neuen Gewichten neu berechnet; Details `docs/audit_isco_codes.md` |
| 2026-10 | ESCO-Audit und Neuzuordnung (#52, #48) | 83 URIs geändert, 89 Beschreibungen (v1.2.1), deutsche Titel, `beschreibung_quelle` korrigiert; neu `esco_isco_code`, `esco_match_qualitaet`, `esco_kompetenzen.csv`; Stufe 3 + ISCO-Prüfung in `enrich_with_esco.py`; Details `docs/audit_esco_zuordnungen.md` |

## Löhne (LSE 2024)

`lohn_median_chf` stammt seit Issue #45 aus der **BFS LSE 2024** (T17, Asset 36355224, nur
2-stellige CH-ISCO-19-Gruppen, Monatsmedian × 12) statt aus der geschätzten `LOHN_MAP`
(«LSE 2022, geschätzt») bzw. den nicht belegbaren 4-stelligen Werten aus `build_berufeliste.py`.
Herkunft je Beruf in `lohn_quelle`:

- `LSE2024_2d` — Gruppenmedian (136 Berufe, inkl. Leitende Verwaltungsbedienstete 1112:
  Salarium hat für Führungskräfte der öffentlichen Verwaltung, NOGA 84, keine konsistenten Werte)
- `LSE2024_2d+Salarium` — Gruppen 11–14, 22, 24, 26: Gruppenmedian × S_j / S̄_g, wobei S̄_g
  das beschäftigungsgewichtete Mittel der Salarium-Werte der Gruppe ist (gewichtetes Mittel der
  Löhne = LSE-Gruppenmedian; 43 Berufe; Profile in `lohn_profile_salarium.csv`, Antworten in
  `lohn_salarium_abfragen.csv`) — **Modellschätzung**
- `LSE2024_1d` / `LSE2024_total` — Fallback für Gruppen ohne LSE-Wert (01–03, 63, 95; derzeit 0 Berufe)

Bekannte Schwächen: Berufe derselben 2-stelligen Gruppe ausserhalb der Salarium-Gruppen haben
identische Löhne (z. B. Informatiker/in EFZ = Softwareentwickler/in, Kassierer/in = Detailhandel);
die Normierung hängt von den Beschäftigtenzahlen der App-Berufe ab (nicht von der vollen Gruppe);
die Gewichte sind seit #51 in allen CSVs gleich (SE 2024, ohne Doppelzählung);
Salarium (Privatsektor, ohne Kader im Normprofil) unterschätzt Spitzenlöhne, v. a. Fachärzte.
Saubere Alternative: BFS-Sonderauswertung 3-/4-stellig (lohn@bfs.admin.ch).

## Beschäftigtenzahlen und ISCO-Codes (#51)

Bis #51 teilten sich 35 handgepflegte Berufe 15 Berufsgattungen; `berufe_ch.csv` setzte für jeden
den vollen SE-Wert (Doppelzählung, Σ 4'488.5 Tsd.), `scores.csv` enthielt eine unbelegte Aufteilung
(Σ 3'880.8 Tsd.). Jetzt:

- **Quelle:** BFS SE 2024, Berufsgattung (4-stellig) bzw. Berufsart (5-stellig); versionierter Auszug
  `data/processed/se_berufe.csv` (Blätter 2024 und 2022-2024).
- **Zuordnung:** `data/processed/beruf_berufsart_mapping.csv` (eine Zeile je Beruf, mit Begründung).
  Option B (Berufsarten) für 2330 Sekundar-/Gymnasiallehrer, 5131 Restaurantfachleute /
  Servicemitarbeitende, 5223 Verkäufer / Drogisten; sonst Fallback A (Zusammenlegung, 22 Einträge).
- **Invariante:** Σ `beschaeftigte_1000` je 4-stelligem Code = SE-Wert (Test). Σ App 3'566.9 Tsd.
  (SE total 4'583.7 Tsd.).
- **Zusammengelegte Einträge:** SE-Bezeichnung als `beruf`, bisherige Titel in `synonyme`;
  Scores vorläufig beschäftigungsgewichtetes Mittel (`scores_gemittelt = True`, leerer
  `beschreibung_hash` → Neubewertung beim nächsten `exposure_scorer.py`-Lauf).
- **ISCO-Audit:** `docs/audit_isco_codes.md` — 21 Korrekturen (hoch), 15 offene Fälle (mittel), u. a.
  Qualitätsmanager/in (2146, SE 2024 nicht publiziert → 0.1 Tsd. aus 2022–2024),
  Versicherungskaufmann/-frau (3312), Maschinenführer/in (8211), Posthalter/in (4415).
- **Bekannte Grenzen:** Titel teils enger als die Gattung (Notar/in = alle «Juristen a. n. g.»,
  Zimmermann/-frau inkl. Schreiner); durch Code-Korrekturen frei gewordene Gattungen ≥ 5 Tsd.
  (3123 Poliere 28.8, 3115 Maschinenbau-/Systemtechniker 12.0, 3434 Küchenchefs 9.6,
  7223 Werkzeugmaschineneinrichter 8.6, 3311 Wertpapierhändler 8.5, 3355 Polizeikommissare 8.5 Tsd.)
  sind nicht mehr abgedeckt — Aufnahme über
  `update_from_bfs.py --neue-berufe` plus ESCO-Anreicherung und Scoring möglich.

## Quality Audit Prozess

`full_quality_audit.py` prüft ob `haupt_risiko`/`begruendung` zum Berufstitel passt:

1. **Phase 1 (Haiku)**: Prüft alle 204 Beschreibungen auf inhaltliche Korrektheit
2. **Phase 2 (Haiku)**: Generiert korrekte Berufsbeschreibung für fehlerhafte Jobs
3. **Phase 3 (Sonnet)**: Re-Scoring mit korrigierten Beschreibungen

Wann ausführen: nach `--fix-wrong`-Läufen oder bei Verdacht auf neue Artefakte.
Report: `data/processed/audit_report.json`

## ESCO API — Hinweis

Die ESCO REST API ist aus der Cloud **erreichbar** (Stand Okt. 2026; früher als blockiert
dokumentiert). Abfragen sequentiell mit ~0.5 s Pause und immer mit `selectedVersion=v1.2.1`.
Für Massenabfragen (Kompetenzen) ist der CSV-Download v1.2.1 konsistenter und schneller.
