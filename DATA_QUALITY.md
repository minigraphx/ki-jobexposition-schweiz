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
| 2026-10 | Gruppe 22: Verhältniszahlen statt Salarium-Normierung, `lohn_verhaeltnisse.csv` | 2221/2211/2212 `LSE2024_2d+Verhaeltnis` (94'800 / 132'000 / 155'200 CHF); neue Spalte `lohn_unsicher` (2261, 2262); `score_ch` 2212; `adaptabilitaet` 163 Berufe (Min-Max-Skalierung) |

## Löhne (LSE 2024)

`lohn_median_chf` stammt seit Issue #45 aus der **BFS LSE 2024** (T17, Asset 36355224, nur
2-stellige CH-ISCO-19-Gruppen, Monatsmedian × 12) statt aus der geschätzten `LOHN_MAP`
(«LSE 2022, geschätzt») bzw. den nicht belegbaren 4-stelligen Werten aus `build_berufeliste.py`.
Herkunft je Beruf in `lohn_quelle`:

- `LSE2024_2d` — Gruppenmedian (136 Berufe, inkl. Leitende Verwaltungsbedienstete 1112:
  Salarium hat für Führungskräfte der öffentlichen Verwaltung, NOGA 84, keine konsistenten Werte)
- `LSE2024_2d+Salarium` — Gruppen 11–14, 22, 24, 26: Gruppenmedian × S_j / S̄_g, wobei S̄_g
  das beschäftigungsgewichtete Mittel der Salarium-Werte der Gruppe ist (gewichtetes Mittel der
  Löhne = LSE-Gruppenmedian; 40 Berufe; Profile in `lohn_profile_salarium.csv`, Antworten in
  `lohn_salarium_abfragen.csv`) — **Modellschätzung**
- `LSE2024_2d+Verhaeltnis` — belegte bzw. hergeleitete Verhältniszahl zum LSE-Gruppenmedian
  aus `lohn_verhaeltnisse.csv` (nach der Salarium-Kalibrierung angewendet; 3 Berufe der Gruppe 22)
  — **Schätzung mit Band**, siehe unten
- `LSE2024_1d` / `LSE2024_total` — Fallback für Gruppen ohne LSE-Wert (01–03, 63, 95; derzeit 0 Berufe)
- Spalte `lohn_unsicher` = `True`: keine belegte Relation, Lohn nur Salarium-Modell (Zahnärzte 2261,
  Apotheker 2262)

### Gruppe 22: Verhältniszahlen statt Salarium-Normierung (2026-10)

Problem: Die Normierung «beschäftigungsgewichtetes Mittel = LSE-Median» drückt in der stark
rechtsschiefen Gruppe 22 (LSE 2024: P50 8'000, P90 14'238 CHF/Monat) alle Werte nach unten:
Pflege 89'800 CHF, Ärzte 109'900 CHF (Ärzte/Pflege 1.22).

| ISCO | Beruf | vorher | neu | Faktor (Band) | Beleg |
|------|-------|-------:|----:|---------------|-------|
| 2221 | Dipl. Pflegefachperson | 89'800 | 94'800 | 0.987 | gut: LSE-2018-Spezialauswertung BAG (Asset 19087994), 7'429 / 7'526 |
| 2211 | Allgemeinmedizin | 109'900 | 132'000 | 1.375 (1.117–1.633 → 107k–157k) | mittel/schwach: R = 1.6 × Pflege, Aufteilung angenommen |
| 2212 | Fachärzte | 109'900 | 155'200 | 1.617 (1.314–1.921 → 126k–184k) | mittel/schwach: wie 2211; Band überspannt 150k |
| 2261 | Zahnarzt/-ärztin | 109'900 | 109'900 | – (unsicher) | keine freie Quelle |
| 2262 | Apotheker/in | 98'400 | 98'400 | – (unsicher) | keine freie Quelle |
| 2230, 2264 | Komplementärmedizin, Physio | 89'800, 93'300 | unverändert | Salarium | normiert ohne 2211/2212/2221 |

Herleitung Ärzte/dipl. Pflege R (LSE-kompatibel: Median, 40 h): BFS Krankenhausstatistik
2018–2022, Lohnaufwand pro VZÄ Ärzteschaft ÷ Pflegepersonal 2.03–2.07 (Mittelwerte, Spitäler) ×
1.058 (ohne Unterassistent/innen, Lohnanteil 10–20 % angenommen) × 0.915 (Pflegemix → dipl. Pflege,
BFS je-d-14.04.08.03 + LSE-2018-Relationen) × 0.897 (Sollstunden 2'100/2'340, BFS-Medienmitteilung
25.11.2025) ÷ Mittelwert/Median 1.0–1.15 (BASS) = **1.53–1.77**; unabhängig: Mischungszerlegung der
LSE-2024-Perzentile Gruppe 22 = 1.57–1.87; Untergrenze aus einer Spital-Lohnskala AA/OA 1.13–1.31.
Gewählt **R = 1.6 (Band 1.3–1.9)**. Aufteilung: 2211/2212 = 0.85 (BASS 2018, Fachärzt/innen 2014:
Grundversorgung/Spezialisten 0.69, wegen Assistenzärzten abgeschwächt — **Annahme**), sodass das
mit SE-2024-Beschäftigten gewichtete Mittel der beiden Faktoren 0.987 × 1.6 ergibt.

Prüfung der Recherche (2026-10): Pflegeanker, Methode A (1.529 / 1.642 / 1.772) und BASS-Relation
(0.689) nachgerechnet und bestätigt. **Abweichung:** Die Recherche gewichtete 2211 mit 22 Tsd.
Beschäftigten; die SE 2024 (Berufsgattung 2211, wie in `berufe_ch.csv`) hat 6.7 Tsd. Mit den
Projektgewichten (6.7 / 36.0) ergeben sich 2211 = 1.375 statt 1.42 und 2212 = 1.617 statt 1.68
(zentral 132'000 / 155'200 statt 136'700 / 160'800 CHF). Übernommen wurden die korrigierten Werte.

Normierung: Override-Berufe zählen nicht in S̄_22; die übrigen Salarium-Berufe (2230, 2261, 2262,
2264) werden unter sich normiert (gewichtetes Mittel = 96'000 CHF). Ihre Löhne bleiben dadurch
(zufällig, auf 100 CHF gerundet) gleich. Folge: Komplementärmedizin (2230) hat dasselbe Salarium-
Profil (HF, NOGA 86) wie die Pflege, aber 89'800 statt 94'800 CHF — die Pflege ist belegt, 2230 nur
modelliert. Alternative (nicht umgesetzt): übrige Berufe relativ zum Pflegeanker setzen
(lohn = 94'800 × S_j / S_Pflege) → 2230 94'800, 2264 98'500, 2262 103'900, 2261 116'000.

Folgen in `scores.csv`: Lohnklasse nur bei 2212 (100–150k → >150k, `delta_lohn` +0.2 → +0.4,
`score_ch` 4.1 → 4.3). `adaptabilitaet` skaliert den Lohn min-max über alle Berufe; das neue
Maximum (2212, 155'200 statt 131'700 CHF) senkt die Lohnpunkte fast aller Berufe: 163 von 179 Werten
ändern sich (−0.7 bis +0.8, Mittel 6.37 → 6.06), 8 Berufe fallen unter 5.0 (Matrix-Quadrant).
Unverändert: alle LLM-Scores, Texte, ESCO-Spalten, `zeitrahmen`, `delta_branche`.
Präzise wäre nur eine LSE-Sonderauswertung der 3-Steller 221/222/226 (lohn@bfs.admin.ch).

Bekannte Schwächen: Berufe derselben 2-stelligen Gruppe ausserhalb der Salarium-Gruppen haben
identische Löhne (z. B. Informatiker/in EFZ = Softwareentwickler/in, Kassierer/in = Detailhandel);
die Normierung hängt von den Beschäftigtenzahlen der App-Berufe ab (nicht von der vollen Gruppe);
die Gewichte sind seit #51 in allen CSVs gleich (SE 2024, ohne Doppelzählung);
Salarium (Privatsektor, ohne Kader im Normprofil) unterschätzt Spitzenlöhne (Fachärzte seit
2026-10 über Verhältniszahlen, siehe oben).
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
