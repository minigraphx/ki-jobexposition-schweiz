# ESCO-Zuordnungen: Audit und Korrektur (Issue #52, schliesst #48 ein)

Stand: 2026-10. Geprüft wurden zuerst alle 197 ESCO-URIs der damals 204 Berufe. Danach wurden
die Zuordnungen für die heutigen **179 Einträge** (nach #51: 21 ISCO-Codes korrigiert,
22 Zusammenlegungen) neu bestimmt. Referenz ist **ESCO v1.2.1** (API mit
`selectedVersion=v1.2.1` und der gleichnamige CSV-Download, de/en). Titel und Beschreibungen
kommen aus der API, die Kompetenzen aus dem CSV. Für alle gewählten URIs stimmen API und CSV in
Titel, Beschreibung, ISCO-Gruppe und Kompetenzen überein.

Lizenz: ESCO © Europäische Union, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Titel, Beschreibungen und Kompetenzen stammen aus ESCO v1.2.1; Beschreibungen sind ggf. gekürzt
oder angepasst. Einträge ohne ESCO-Beruf tragen eine eigene Beschreibung
(`beschreibung_quelle` ≠ «ESCO»).

## Befund (204 Berufe, vor #51)

| Bewertung | Berufe | Beschäftigte (Tsd., Handliste) |
|---|---|---|
| korrekt | 107 | 2'023 |
| plausibel-generisch (Teilgebiet, zu spezifisch) | 51 | 806 |
| **falsch** | **39** | **987 (~26 %)** |
| ohne ESCO-URI | 7 | – |

Beispiele: Dipl. Pflegefachperson → Diplomat/in (#48), Kaufmann/-frau EFZ → Fachverkäufer/in
für Kraftfahrzeuge, Detailhandel/Restaurantfach/Hotelfach → Kameramann/-frau, Spitex →
Futtermittelherstellung, Automatiker → Gesundheit von Wassertieren. 13 URIs waren 30 Berufen
mehrfach zugeordnet, 4 Berufe ohne URI hatten `beschreibung_quelle = ESCO`, einige Titel waren
englisch. Die falschen Beschreibungen waren Input für das Exposure-Scoring.

## Ursache und Behebung

| Ursache | Wirkung | Behebung |
|---|---|---|
| Stufe 3 (`esco_search_isco`) nutzte den Suchparameter `iscoGroup`, den die ESCO-API **ignoriert**; sie lieferte dann alle Berufe alphabetisch («3D-Animationstechniker, 3D-Artist, Abfallbeauftragter …») | Fehltreffer wie Abfallmakler, 3D-Druck-Techniker | Concept-Endpunkt `/resource/concept?uri=http://data.europa.eu/esco/isco/C{code}` → `_links.narrowerOccupation`, rekursiv über `narrowerConcept` (z. B. CH-Sammelcode 7200 → Gruppe 72) |
| keine ISCO-Prüfung; nur ein Sprachmodell bewertete Titel + Beschreibung | Textsuche «Dipl.» → Diplomat/in, Kameramann ×3, Futtermittel usw. (32 der 39 Fehler hätte eine ISCO-Prüfung abgefangen) | **harte ISCO-Konsistenzprüfung** vor der inhaltlichen Prüfung (`isco_konsistenz`, siehe unten) |
| Abfragen ohne Versionsangabe | die Standardversion der API weicht von v1.2.1 ab (z. B. ISCO-Gruppe der PTA 3213 statt 2262, andere Beschreibungstexte); zwei URIs mit HTTP 500 | `selectedVersion=v1.2.1` in allen Abfragen |
| Dedup nur innerhalb eines Laufs; Teil-Läufe und Handkorrekturen ohne Prüfung | 13 URIs mehrfach vergeben | Test: jede URI nur einmal (`tests/test_esco_zuordnung.py`) |
| `patch_unmatched.py` / `verify_esco_matches.py` akzeptierten Treffer schon bei gleicher **2-stelliger** ISCO-Gruppe | Fehlzuordnungen innerhalb der Hauptgruppe | beide als historisch markiert; Matchqualität in `esco_match_qualitaet` |

## Regeln für die Neuzuordnung

- **korrekt:** ESCO-ISCO-4-Steller = `isco_code`, und der ESCO-Beruf deckt die Tätigkeit ab.
- **plausibel:** gleiche 3-stellige ISCO-Gruppe, eine dokumentierte Ausnahme (unten) oder
  ISCO-gleich, aber nur Teilgebiet/Näherung (z. B. Lernbetreuer → Lehrassistent/in Grundschule).
- **fallback:** kein passender ESCO-Beruf → Beschreibung aus berufsberatung.ch / Wikipedia /
  generiert (`beschreibung_quelle`), `esco_uri` leer.
- Audit «korrekt» bleibt; «falsch» → Audit-Vorschlag (geprüft); «plausibel-generisch» →
  Vorschlag, wenn klar besser und ISCO-konsistent; jede URI nur einmal.
- Zusammengelegte Einträge: ESCO-Beruf, der die SE-Gattung am besten repräsentiert (meist der
  generische Beruf der ISCO-Gruppe, z. B. Allgemeine Bürokräfte → Bürokaufmann/-frau,
  Verkäufer in Handelsgeschäften → Verkäufer/in).
- Einträge mit geändertem ISCO-Code (#51) wurden unter dem neuen Code neu bestimmt (z. B.
  Bauführer/in 3112, Polymechaniker/in 7200, Drogist/in 5223).

### Ausnahmen der ISCO-Prüfung (`ISCO_AUSNAHMEN` in `enrich_with_esco.py`)

| unser Code | zulässige ESCO-Gruppe | Grund |
|---|---|---|
| 3221 | 5321 | ESCO v1.2.1 hat keinen Beruf in 3221; FaGe → «nurse assistant» (dt. Label «Gesundheits- und Krankenpfleger/in») |
| 3211 | 2269 | ESCO führt Radiologiefachpersonal (radiographer) unter 2269 |
| 3112 | 3123 | CH-ISCO-19 führt Bauführer in 3112, ESCO die Bauleitung in 3123 |
| 7200 | 72xx | CH-ISCO-19-Sammelcode (Polymechaniker) ohne ISCO-08-Gruppe |
| 2149, 2511 | 1219, 1330 | ESCO führt (IT-)Projektmanager als Führungskräfte |
| 4419 | 4311 | CH-ISCO-19 führt Bürokräfte Verkauf (Verkaufsinnendienst) als Berufsart 44192, ESCO den Verkaufssachbearbeiter (sales support assistant) unter 4311 |
| 3312, 2422, 4415, 7421 | 4312, 3321, 4211, 3113 | ISCO-Code offen aus #51 (Code vermutlich falsch, ESCO-Beruf passt zum Titel); nach Klärung entfernen |

## Ergebnis (179 Einträge)

| Qualität | vorher (Audit der bisherigen Zuordnung) | Beschäftigte vorher (Tsd.) | nachher | Beschäftigte nachher (Tsd.) |
|---|---|---|---|---|
| korrekt | 96 | 1'850.9 | **158** | **3'287.9** |
| plausibel | 45 | 742.0 | 18 | 252.9 |
| falsch | 33 | 950.2 | 0 | 0 |
| fallback / ohne URI | 5 | 23.8 | 3 | 26.1 |

Wendet man die neue ISCO-Regel auf die bisherigen URIs an, wären 47 Einträge (1'153.7 Tsd.)
ISCO-inkonsistent gewesen. 83 URIs wurden geändert, 89 Beschreibungen (davon 6 bei gleicher URI:
Text der Standardversion bzw. leer → v1.2.1). `beschreibung_quelle` korrigiert: Handelsmakler,
Isolierer, Reiseverkehrsfachkräfte (bisher «ESCO» ohne URI, jetzt mit ESCO-Beruf), Hauswirtschaftler/in
EFZ (seit #51 Teil eines zusammengelegten Eintrags); Telematiker/in EFZ jetzt mit ESCO-Beruf.

**Fallback (3):** Drogist/in (kein ESCO-Beruf; bisherige generierte Beschreibung bleibt),
Gymnasiallehrer/in (ESCO kennt nur «Lehrkraft Sekundarstufe»; die URI bleibt bei
Sekundarlehrer/in), Maschinenführer/in (kein generischer ESCO-Beruf, Code 8211 offen). Die
Beschreibungen der beiden letzten wurden im Audit verfasst (`KI-generiert`), weil
berufsberatung.ch (neu aufgebaut, alte Suche liefert nichts) und die Wikipedia-API (aus der Cloud
rate-limitiert) nicht verfügbar waren. Der frühere Quellenwert für generierte Texte heisst jetzt
«KI-generiert».

**«Dipl.»-Titel (#48):** Dipl. Pflegefachperson ist der einzige Eintrag mit «Dipl.» im Titel
oder in den Synonymen; jetzt «Krankenpfleger/Krankenschwester Allgemeine Krankenpflege»
(nurse responsible for general care, 2221). Die Diplomat-URI ist keinem Eintrag mehr zugeordnet.

## Neubewertung nötig

`beschreibung_hash` wurde bewusst **nicht** neu berechnet: `exposure_scorer.py` erkennt beim
nächsten Lauf alle Einträge mit geänderter Beschreibung (Hash-Delta). Zusammen mit den
22 zusammengelegten Einträgen (leerer Hash, #51) sind das **101 Einträge** (89 mit neuer
Beschreibung, davon 10 zusammengelegt, plus 12 zusammengelegte mit unveränderter Beschreibung).
Scores und Texte (`score_*`, `haupt_risiko`, `begruendung`, `zeitrahmen`) sind unverändert und
beziehen sich bis dahin auf die alte Beschreibung. Welche Einträge betroffen sind, zeigt die
Spalte «Änderung» unten (alles ausser «unverändert»).

## ESCO-Kompetenzen (`data/processed/esco_kompetenzen.csv`)

Für die geplante aufgabenbasierte Neubewertung: je Eintrag mit ESCO-URI (176) alle Kompetenzen
aus ESCO v1.2.1 (CSV `occupationSkillRelations` + deutsche Labels aus `skills`), 10'032 Zeilen
(4'479 wesentlich, 5'553 optional; 7'100 skill, 2'928 knowledge). Spalten: `beruf`, `isco_code`,
`esco_uri`, `kompetenz`, `relation` (essential/optional), `typ` (skill/knowledge; leer bei 4
Kompetenzbereichen ohne Typ, z. B. «digitale Kommunikation und Zusammenarbeit»), `kompetenz_uri`.

## Nachtrag: neu aufgenommene Berufsgattungen (8 Einträge)

Für die 8 neu aufgenommenen SE-Gattungen (`docs/audit_isco_codes.md`, Abschnitt «Neu aufgenommene
Berufsgattungen») wurde die ESCO-Zuordnung nach denselben Regeln bestimmt: Kandidaten über den
ISCO-Concept-Endpunkt (`esco_search_isco`) und die Textsuche, harte ISCO-Prüfung
(`isco_konsistenz`), keine bereits vergebene URI (Dedup gegen alle 179 bestehenden Einträge),
inhaltliche Prüfung manuell (kein Sprachmodell-Aufruf); API mit `selectedVersion=v1.2.1`, Titel,
Beschreibung und ISCO-Gruppe mit dem v1.2.1-CSV abgeglichen. Kein Eintrag braucht eine
Fallback-Beschreibung.

| Code | Beruf | ESCO-Beruf | ESCO-ISCO | Qualität | Begründung |
|---|---|---|---|---|---|
| 3115 | Maschinenbautechniker, Techniker im Bereich Systemtechnik, Automation und Unternehmensprozesse | Maschinenbautechniker/in | 3115 | korrekt | einziger ESCO-Beruf der Gruppe; deckt die grösste Berufsart 31151 (63 %) ab |
| 3123 | Poliere und Vorarbeiter | Maurerpolier/in | 3123 | plausibel | Oberbauleiter/in (generisch, Alternativlabel «Baupolier») ist an Bauführer/in (3112) vergeben; Maurerpolier = Kern des Bauhauptgewerbes, Ausbaugewerbe (31232) nur als Teilgebiet |
| 3311 | Wertpapierhändler, -makler und Finanzmakler | Trader/in am Finanzmarkt | 3311 | korrekt | Oberbegriff von Wertpapier-, Börsen- und Devisenhändler |
| 3355 | Polizeikommissare und Kriminalbeamte | Kriminalbeamter/-beamtin | 3355 | korrekt | Ermittlungsarbeit; Polizeikommissar/in (Leitung) als Alternative verworfen |
| 3434 | Küchenchefs, stv. Küchenchefs und Souschefs | Chefkoch/Chefköchin | 3434 | korrekt | Alternativlabels Küchenchef/in, Küchenmeister/in |
| 4419 | Bürokräfte und verwandte Berufe, anderweitig nicht genannt | Verkaufssachbearbeiter/in | 4311 | plausibel | ESCO 4419 hat nur Fremdsprachenkorrespondent/in und Werbesachbearbeiter/in (passt nur zu 44191, 10 %); Verkaufssachbearbeiter (Verkaufsinnendienst, 44192 = 84 %) über die neue Ausnahme 4419 → 4311 |
| 7223 | Werkzeugmaschineneinrichter und -bediener | CNC-Anwendungsfachkraft | 7223 | korrekt | Einrichten, Programmieren und Bedienen von CNC-Maschinen; die spezialisierten Maschinenbediener-Berufe der Gruppe sind zu eng |
| 9329 | Hilfsarbeiter bei der Herstellung von Waren, anderweitig nicht genannt | Fabrikhilfsarbeiter/in | 9329 | korrekt | Alternativlabels Produktionshelfer/in, Produktionshilfskraft |

Kompetenzen: 415 Zeilen für die 8 Einträge ergänzt (aus dem v1.2.1-CSV, wie oben); die Datei hat
jetzt 10'447 Zeilen für 184 Einträge mit ESCO-URI. Match-Qualität aller 187 Einträge:
korrekt 164 (3'374.0 Tsd.), plausibel 20 (323.7 Tsd.), fallback 3 (26.1 Tsd.).

## Alle Einträge

«vorher» = Audit-Bewertung der bisherigen Zuordnung (bei zusammengelegten Einträgen die des
Teilberufs, von dem ESCO-Felder und Texte stammten).

| Beruf | ISCO | ESCO-Beruf (v1.2.1) | ESCO-ISCO | Qualität | vorher | Änderung / Begründung |
|---|---|---|---|---|---|---|
| Dipl. Pflegefachperson | 2221 | Krankenpfleger Allgemeine Krankenpflege | 2221 | korrekt | falsch | neu (bisher: Diplomat/Diplomatin); «Dipl.» -> Diplomat/in (ISCO 1112); Issue #48 |
| Allgemeine Bürokräfte | 4110 | Bürokaufmann/Bürokauffrau | 4110 | korrekt | falsch | neu (bisher: Fachverkäufer für Kraftfahrzeuge); Bürokaufmann/-frau = ESCO office clerk (4110.1), generischer Beruf der Gattung; bisher Kfz-Fachverkäufer (falsch) |
| Softwareentwickler | 2512 | Softwareentwickler/Softwareentwicklerin | 2512 | korrekt | korrekt | unverändert |
| Fachperson Gesundheit EFZ (FaGe) | 3221 | Gesundheits- und Krankenpfleger | 5321 | plausibel | falsch | neu (bisher: Sozialbetreuer psychische Gesundheit); Sozialbetreuung psych. Gesundheit statt Pflege; Vorschlag = EN «nurse assistant» (dt. Label «Gesundheits- und Krankenpfleger» irreführend), nur Näherung — Ausnahme ISCO: ESCO v1.2.1 hat keinen Beruf in ISCO 3221; Pflege auf mittlerer Stufe (FaGe) steht als «nurse assistant» unter 5321 |
| Verkäufer in Handelsgeschäften | 5223 | Verkäufer/Verkäuferin | 5223 | korrekt | falsch | neu (bisher: Kameramann/Kamerafrau); Verkäufer/in = ESCO sales assistant (5223.4), generischer Beruf der Berufsart 52230; bisher Kameramann (falsch) |
| Führungskräfte in Vertrieb und Marketing | 1221 | Führungskraft im Vertrieb | 1221 | korrekt | korrekt | unverändert |
| Schalterbedienstete und Fachkräfte im Bereich Finanzdienstleistungen | 4211 | Bankbediensteter/Bankbedienstete | 4211 | korrekt | plausibel | unverändert |
| Soziale Fachkräfte | 3412 | Sozialbetreuer/Sozialbetreuerin | 3412 | korrekt | falsch | neu (bisher: Manager im Bereich soziale Dienste); Führungsebene (Manager soziale Dienste, ISCO 1344) statt Fachkraft |
| Reinigungskraft / Hauswart | 9112 | Raumpfleger/Raumpflegerin | 9112 | korrekt | korrekt | unverändert |
| Köche | 5120 | Koch/Köchin | 5120 | korrekt | korrekt | unverändert |
| Landwirte mit Ackerbau und Tierhaltung (ohne ausgeprägten Schwerpunkt) | 6130 | Landwirt/Landwirtin | 6130 | korrekt | korrekt | unverändert |
| Sekretär/in / Assistent/in | 4120 | Sekretär/Sekretärin | 4120 | korrekt | korrekt | unverändert |
| Hauswarte | 5153 | Hauswart/Hauswartin | 5153 | korrekt | korrekt | unverändert |
| Fachkräfte in Marketing und Werbung | 2431 | Marketer | 2431 | korrekt | plausibel | neu (bisher: Mediakäufer/Mediakäuferin); Mediakäufer/in ist Teilgebiet; «Marketer» (alt. Marketingspezialist) generischer |
| Fachkräfte im Rechnungswesen | 3313 | Buchhalter/Buchhalterin | 3313 | korrekt | plausibel | neu (bisher: Controller/Controllerin); Buchhalter/in (bookkeeper 3313.2) statt Controller (2411, akademische Ebene) |
| Fachärzte | 2212 | Facharzt/Fachärztin | 2212 | korrekt | korrekt | unverändert |
| Sekretariatsfachkräfte in Verwaltung und Geschäftsleitung | 3343 | Vorstandsassistent/Vorstandsassistentin | 3343 | korrekt | korrekt | unverändert |
| Geschäftsführer/in (KMU) | 1120 | Geschäftsführer/Geschäftsführerin | 1120 | korrekt | plausibel | neu (bisher: Geschäftsführer eines Flughafens); Geschäftsführer/in eines Flughafens = zu spezifisch; generisch 1120.3 vorhanden |
| Führungskräfte in der Produktion von Waren | 1321 | Führungskraft in der Produktion von Waren | 1321 | korrekt | korrekt | URI unverändert, Text auf v1.2.1 aktualisiert |
| Spitex-Mitarbeiter/in | 5322 | Haus- und Familienpfleger | 5322 | korrekt | falsch | neu (bisher: Mitarbeiter in der Futtermittelherstellung); Futtermittelherstellung statt häusliche Pflege |
| Hochschuldozent/in | 2310 | Hochschullehrkraft | 2310 | korrekt | plausibel | neu (bisher: Hochschullehrkraft für Journalistik); Hochschullehrkraft für Journalistik = Teilgebiet |
| Elektriker/in EFZ | 7411 | Bauelektriker/Bauelektrikerin | 7411 | korrekt | korrekt | unverändert |
| Maurer/in EFZ | 7112 | Maurer/Maurerin | 7112 | korrekt | korrekt | unverändert |
| Reinigungs- und Hauswirtschaftleiter und -kräfte in Büros, Hotels und anderen Einrichtungen | 5151 | Leitender Hauswirtschafter | 5151 | korrekt | falsch | neu (bisher: Gebäudereiniger Innenreinigung); Leitende/r Hauswirtschafter/in (housekeeping supervisor 5151.2) statt Gebäudereiniger/in (9112) |
| Verkaufsfachkräfte | 3322 | Handelsvertreter/Handelsvertreterin | 3322 | korrekt | falsch | neu (bisher: Fachverkäufer/Fachverkäuferin); Fachverkäufer/in (Laden, 5223) statt Handelsvertreter/Aussendienst 3322 |
| Technische Zeichner | 3118 | Technischer Zeichner | 3118 | korrekt | korrekt | unverändert |
| Kraftfahrzeugmechaniker und -schlosser | 7231 | Kraftfahrzeugmechatroniker Schwerpunkt Personenkraftwagentechnik | 7231 | korrekt | falsch | neu (bisher: Schloss- und Schlüsselmacher); Schloss- und Schlüsselmacher/in statt Kfz-Mechaniker/in |
| Spezialisten im Bereich Management- und Organisationsanalyse | 2421 | Unternehmensberater | 2421 | korrekt | korrekt | neu (bisher: Projektmanager/Projektmanagerin); Unternehmensberater/in (2421) statt Projektmanager/in (1219); ISCO-gleich |
| Versicherungskaufmann/-frau | 3312 | Versicherungssachbearbeiter | 4312 | plausibel | korrekt | unverändert — Ausnahme ISCO: Versicherungskaufmann/-frau: Code 3312 offen (#51), ESCO insurance clerk 4312 |
| Sozialarbeiter | 2635 | Sozialarbeiter/Sozialarbeiterin | 2635 | korrekt | plausibel | neu (bisher: Teamleiter im Bereich Sozialarbeit); Sozialarbeiter/in (2635.3, alt. Sozialpädagoge) statt Teamleiter/in Sozialarbeit |
| Berufsberater und -analytiker und vergleichbare Spezialisten der Personalwesen | 2423 | Berufsberater/Berufsberaterin | 2423 | korrekt | korrekt | URI unverändert, Text auf v1.2.1 aktualisiert |
| Reinigungspersonal und Hilfskräfte in Privathaushalten | 9111 | Reinigungskraft in Privathaushalt | 9111 | korrekt | korrekt | unverändert |
| Landmaschinen- und Industriemaschinenmechaniker und -schlosser | 7233 | Servicetechniker für Landmaschinen | 7233 | korrekt | korrekt | unverändert |
| Kassierer und Kartenverkäufer | 5230 | Kassierer/Kassiererin | 5230 | korrekt | falsch | neu (bisher: Kassenaufsichtskraft); Kassierer/in (5230.1) statt Kassenaufsichtskraft (5222) |
| Fachkräfte in der Lagerwirtschaft | 4321 | Warenlagerverwalter | 4321 | korrekt | korrekt | unverändert |
| Kinderbetreuerin/-betreuer | 5311 | Kinderbetreuer/Kinderbetreuerin | 5311 | korrekt | korrekt | unverändert |
| Sachbearbeiter/in Buchhaltung | 4311 | Fakturist/Fakturistin | 4311 | korrekt | korrekt | URI unverändert, Text auf v1.2.1 aktualisiert |
| Restaurantfachmann/-frau EFZ | 5131 | Oberkellner/Oberkellnerin | 5131 | plausibel | falsch | neu (bisher: Kameramann/Kamerafrau); Kameramann/-frau; Kellner/in 5131.2 geht an Servicemitarbeiter/in -> hier Oberkellner/in (Einschätzung, Ebene leicht höher) |
| Kindergärtnerin/-gärtner | 2342 | Lehrkraft für Vorschulerziehung | 2342 | korrekt | korrekt | unverändert |
| Arzt/Ärztin (Allgemeinmedizin) | 2211 | Arzt für Allgemeinmedizin | 2211 | korrekt | korrekt | unverändert |
| Systemadministrator/in | 2522 | IT-Systemadministrator | 2522 | korrekt | korrekt | unverändert |
| Polymechaniker/in EFZ | 7200 | Zerspanungsmechaniker | 7223 | plausibel | plausibel | neu (bisher: Industriemechaniker); Industriemechaniker/in 7233.7; Zerspanungsmechaniker/in 7223.7 (alt. Industriemechaniker) ist ISCO-konsistent — Ausnahme ISCO: CH-ISCO-19-Sammelcode (Polymechaniker) ohne ISCO-08-Gruppe → ESCO-Berufe der Untergruppe 72 |
| Produktionsleiter bei der Herstellung von Waren | 3122 | Produktionsleiter/Produktionsleiterin | 3122 | korrekt | plausibel | neu (bisher: Produktionsleiter Elektronik); Produktionsleiter/in Elektronik = Teilgebiet; generisch 3122.4 |
| Projektleiter/in (Technik) | 2149 | Projektmanager/Projektmanagerin | 1219 | plausibel | plausibel | URI unverändert, Text auf v1.2.1 aktualisiert — Ausnahme ISCO: ESCO führt Projektmanager als Führungskräfte (1219) |
| Führungskräfte in der Beschaffung, Logistik und in verwandten Bereichen | 1324 | Supply-Chain-Manager | 1324 | korrekt | plausibel | neu (bisher: Führungskraft für intermodale Logistik); Supply-Chain-Manager/in (1324.8) statt intermodale Logistik (Teilgebiet) |
| Polizisten (ohne Polizeikommissare) | 5412 | Polizist/Polizistin | 5412 | korrekt | korrekt | unverändert |
| Wirtschaftsprüfer, Steuerberater und verwandte Berufe | 2411 | Controller/Controllerin | 2411 | korrekt | plausibel | unverändert |
| Maschinenbauingenieur/in | 2144 | Maschinenbauingenieur | 2144 | korrekt | korrekt | unverändert |
| Rechtsanwalt/-anwältin | 2611 | Rechtsanwalt/Rechtsanwältin | 2611 | korrekt | korrekt | unverändert |
| Küchenhilfe | 9412 | Küchenhilfe | 9412 | korrekt | korrekt | unverändert |
| Führungskräfte im Bereich Finanzen | 1211 | Finanzmanager/Finanzmanagerin | 1211 | korrekt | falsch | neu (bisher: Führungskraft im Bereich Rohrleitungstransport); Rohrleitungstransport statt Finanzen |
| Sportlehrer, Sporttrainer und Sportfunktionäre | 3422 | Sportlehrer/Sportlehrerin | 3422 | korrekt | korrekt | unverändert |
| Sekretariatsleiter | 3341 | Büroleiter/Büroleiterin | 3341 | korrekt | korrekt | unverändert |
| Führungskräfte in Restaurants | 1412 | Restaurantmanager/Restaurantmanagerin | 1412 | korrekt | falsch | neu (bisher: Führungskraft für intermodale Logistik); intermodale Logistik statt Restaurant |
| Servicemitarbeiter/in | 5131 | Kellner/Kellnerin | 5131 | korrekt | falsch | neu (bisher: Reiseberater der Bahn); Reiseberater/in Bahn statt Service |
| Bediener von Anlagen und Maschinen für chemische Erzeugnisse | 8131 | Pharmatechnologe/Pharmatechnologin | 8131 | plausibel | korrekt | unverändert |
| Architekt/in | 2161 | Architekt/Architektin | 2161 | korrekt | korrekt | unverändert |
| IT-Projektleiter/in | 2511 | IT-Projektmanager/IT-Projektmanagerin | 1330 | plausibel | plausibel | neu (bisher: Projektmanager/Projektmanagerin); Projektmanager-URI 3x vergeben; IT-Projektmanager/in (ESCO 1330.7) — Ausnahme ISCO: ESCO führt IT-Projektmanager als Führungskräfte (1330) |
| Zimmermann/-frau EFZ | 7115 | Zimmerer/Zimmerin | 7115 | korrekt | korrekt | unverändert |
| Finanzanalyst/in | 2413 | Finanzanalyst/Finanzanalystin | 2413 | korrekt | korrekt | unverändert |
| Gymnasiallehrer/in | 2330 | — (KI-generiert) | – | fallback | korrekt | neu (bisher: Lehrkraft Sekundarstufe); ESCO hat nur einen generischen Beruf «Lehrkraft Sekundarstufe»; URI bleibt bei Sekundarlehrer/in (Dedup) |
| Physiotherapeut/in | 2264 | Physiotherapeut/Physiotherapeutin | 2264 | korrekt | korrekt | unverändert |
| Coiffeur/Coiffeuse EFZ | 5141 | Friseur/Friseurin | 5141 | korrekt | korrekt | unverändert |
| Sachbearbeiter/in HR | 4416 | Personalsachbearbeiter | 4416 | korrekt | falsch | neu (bisher: Sachbearbeiter im Investmentbereich); Sachbearbeiter/in Investmentbereich statt HR; Personalsachbearbeiter/in wird bei öff. Verwaltung frei |
| Hilfsarbeiter im Hochbau | 9313 | Hochbauhelfer/Hochbauhelferin | 9313 | korrekt | korrekt | unverändert |
| Lehrkräfte im Bereich Sonderpädagogik | 2352 | Sonderpädagoge/Sonderpädagogin | 2352 | korrekt | falsch | neu (bisher: Lehrassistent Sonderpädagogik); Lehrassistent/in (5312) statt Lehrkraft Sonderpädagogik |
| Versicherungsvertreter | 3321 | Versicherungsmakler | 3321 | korrekt | korrekt | unverändert |
| Kosmetiker und verwandte Berufe | 5142 | Kosmetiker/Kosmetikerin | 5142 | korrekt | korrekt | unverändert |
| Zahnmedizinische Assistenten und Dentalhygieniker | 3251 | Zahnmedizinischer Fachangestellter | 3251 | korrekt | korrekt | unverändert |
| Finanz- und Anlageberater | 2412 | Anlage- und Vermögensberater | 2412 | korrekt | korrekt | neu (bisher: Vermögensverwalter/Vermögensverwalterin); Anlage- und Vermögensberater/in (investment adviser 2412.6) statt Vermögensverwalter (3311) |
| Elektroingenieur/in | 2151 | Ingenieur Elektrotechnik | 2151 | korrekt | plausibel | neu (bisher: Elektroingenieur Bergbau); Elektroingenieur/in Bergbau = Teilgebiet; generisch 2151.1 |
| Berufsschullehrer/in | 2320 | Lehrkraft im Bereich Berufsbildung | 2320 | korrekt | korrekt | unverändert |
| Filialleiter/in (Detailhandel) | 1420 | Ladenmanager/Ladenmanagerin | 1420 | korrekt | falsch | neu (bisher: Verkaufsaufsichtskraft); Verkaufsaufsichtskraft (5222) statt Führungskraft 1420; URI 2x vergeben |
| ÖV-Fahrer/in (Bus/Tram) | 8331 | Omnibusfahrer/Omnibusfahrerin | 8331 | korrekt | plausibel | neu (bisher: Oberleitungsbusfahrer); Oberleitungsbus = Teilgebiet; Omnibusfahrer/in 8331.1 |
| ICT-Supporter/in | 3512 | IT-Helpdesk-Manager | 3512 | korrekt | falsch | neu (bisher: IKT-Sicherheitsberater); IKT-Sicherheitsberater/in statt Support; Vorschlag alt. IT-Support-Techniker |
| Gärtner/in EFZ | 6113 | Landschaftsgärtner/Landschaftsgärtnerin | 6113 | korrekt | plausibel | neu (bisher: Landschaftsgärtner für Innenraumbegrünung); Innenraumbegrünung = Teilgebiet |
| Sanitärinstallateur/in EFZ | 7126 | Gas- und Sanitärinstallateur | 7126 | korrekt | korrekt | unverändert |
| Maschinenführer/in | 8211 | — (KI-generiert) | – | fallback | plausibel | neu (bisher: Maschinenführer in der Papierwarenerzeugung); kein generischer ESCO-Beruf; Papierwaren-Maschinenführer (8171) zu eng und ISCO-inkonsistent; Code 8211 offen (#51) |
| Posthalter/in / Logistiker/in Post | 4415 | Postschalterbediensteter | 4211 | plausibel | falsch | neu (bisher: Haussitter/Haussitterin); Haussitter/in statt Postschalter — Ausnahme ISCO: Posthalter/in: Code 4415 offen (#51), ESCO Postschalter 4211 |
| Leitende Verwaltungsbedienstete | 1112 | Leiter im öffentlichen Dienst | 1112 | korrekt | korrekt | unverändert |
| Bauingenieur/in | 2142 | Bauingenieur/Bauingenieurin | 2142 | korrekt | korrekt | URI unverändert, Text auf v1.2.1 aktualisiert |
| Bäcker, Konditoren und Konfektmacher | 7512 | Bäcker/Bäckerin | 7512 | korrekt | plausibel | neu (bisher: Konfektmacher/Konfektmacherin); Konfektmacher/in = Teilgebiet; Bäcker/in 7512.1 (alt. Konditor) |
| Apotheker/in | 2262 | Apotheker/Apothekerin | 2262 | korrekt | korrekt | unverändert |
| Pharmazeutische Techniker und Assistenten | 3213 | Pharmazeutisch-kaufmännischer Angestellter | 3213 | korrekt | korrekt | neu (bisher: Pharmazeutisch-technische Assistent); Pharmazeutisch-kaufmännische/r Angestellte/r (pharmacy assistant 3213.1); bisherige PTA steht in ESCO v1.2.1 unter 2262 (ISCO inkonsistent) |
| Technische Verkaufsfachkräfte (ohne Informations- und Kommunikationstechnologie) | 2433 | Fachkraft im Bereich Vertrieb | 2433 | korrekt | plausibel | neu (bisher: Verkaufsberater für Solarenergie); Solarenergie = Teilgebiet; Fachkraft im Bereich Vertrieb (alt. technischer Aussendienst) 2433.6 |
| Automatiker und verwandte Berufe | 7412 | Elektromechaniker/Elektromechanikerin | 7412 | korrekt | falsch | neu (bisher: Angehöriger der mit der Gesundheit von Wassertieren befassten Berufe); Elektromechaniker/in (7412.3) statt Gesundheit von Wassertieren (falsch) |
| Uhrmacher, Uhrenarbeiter, Mikromechaniker | 7311 | Uhrmacher/Uhrmacherin | 7311 | korrekt | korrekt | unverändert |
| Bürokräfte in der Transportwirtschaft und verwandte Berufe | 4323 | Frachtdisponent/Frachtdisponentin | 4323 | korrekt | falsch | neu (bisher: Büroassistent/Büroassistentin); Bürokaufmann (4110) statt Transport-Bürokraft; Frachtdisponent/in 4323.6 |
| Sekretariatsfachkräfte im Gesundheitswesen | 3344 | medizinischer Sekretär | 3344 | korrekt | korrekt | unverändert |
| Führungskräfte in der Erbringung von Dienstleistungen im Bereich Informations- und Kommunikationstechnologie | 1330 | IT-Leiter/IT-Leiterin | 1330 | korrekt | plausibel | neu (bisher: Führungskraft für Unternehmensdienstleistungen); Führungskraft Unternehmensdienstleistungen (1219, 3x vergeben) statt IKT-Leitung |
| Verkaufsaufsichtskräfte in Handelsgeschäften | 5222 | Verkaufsaufsichtskraft | 5222 | korrekt | korrekt | unverändert |
| Fachkräfte für Rechts- und verwandte Angelegenheiten | 3411 | Sachbearbeiter für Rechtsangelegenheiten | 3411 | korrekt | korrekt | unverändert |
| Frachtarbeiter und verwandte Berufe | 9333 | Materiallagerarbeiter | 9333 | korrekt | plausibel | neu (bisher: Bediener intermodaler Einrichtungen im Schienenverkehr); intermodaler Schienenverkehr = Teilgebiet; Materiallagerarbeiter/in (alt. Lagerarbeiter, Ladearbeiter) |
| Qualitätsmanager/in | 2146 | Qualitätsingenieur/Qualitätsingenieurin | 2149 | plausibel | plausibel | neu (bisher: Qualitätsbeauftragter in der Industrie); Qualitätsingenieur/in (2149.2.7, gleiche 3-stellige Gruppe 214); Code 2146 offen (#51) |
| Zugbegleiter/in / Lokführer/in | 8311 | Schienenfahrzeugführer | 8311 | plausibel | plausibel | neu (bisher: Zugbegleiter/Zugbegleiterin); nur Zugbegleiter/in (5112); ISCO 8311 -> Schienenfahrzeugführer/in (Lokführer) |
| Maler/in und Gipser/in EFZ | 7131 | Maler/Malerin | 7131 | korrekt | korrekt | unverändert |
| Datenwissenschaftler/in / Data Scientist | 2514 | Datenwissenschaftler | 2511 | plausibel | korrekt | unverändert |
| HR-Manager/in | 1212 | Führungskraft im Personalwesen | 1212 | korrekt | falsch | neu (bisher: Personalberater/Personalberaterin); Personalberater/in (2423) statt HR-Führung 1212 |
| Immobilienmakler und -verwalter | 3334 | Hausverwalter/Hausverwalterin | 3334 | korrekt | korrekt | unverändert |
| Psychologe/-pädagogin | 2634 | Psychologe/Psychologin | 2634 | korrekt | korrekt | unverändert |
| Naturwissenschaftler/in (Biologie/Chemie) | 2113 | Chemiker/Chemikerin | 2113 | korrekt | plausibel | neu (bisher: Applikationsspezialist Chemie); Applikationsspezialist/in Chemie = Teilgebiet; Chemiker/in 2113.1 |
| Sicherheitsbeauftragter/-beauftragte | 5414 | Fachkraft Schutz- und Sicherheit | 5414 | korrekt | falsch | neu (bisher: Sicherheitsbeauftragter Luftverkehr); Sicherheitsbeauftragte/r Luftverkehr (3119) statt Sicherheitsdienst 5414 |
| Zahnarzt/-ärztin | 2261 | Zahnarzt/Zahnärztin | 2261 | korrekt | korrekt | unverändert |
| Lernbetreuer | 5312 | Lehrassistent Grundschule | 5312 | plausibel | plausibel | neu (bisher: Lerncoach); Lehrassistent/in (5312.2) statt Lerncoach (2359, ISCO inkonsistent) |
| Physiotherapeutische Techniker und Assistenten | 3255 | Physiotherapieassistent | 3255 | korrekt | korrekt | unverändert |
| Führer von Erdbewegungs- und verwandten Maschinen, Strassenbau und Baumaschinen | 8342 | Straßenbaumaschinenführer | 8342 | korrekt | korrekt | unverändert |
| Boden- und Fliesenleger | 7122 | Platten- und Fliesenleger | 7122 | korrekt | korrekt | unverändert |
| Führungskräfte in Unternehmenspolitik und -planung | 1213 | Führungskraft im Bereich der Unternehmenspolitik | 1213 | korrekt | korrekt | unverändert |
| Hilfsarbeiter im Tiefbau | 9312 | Tiefbauhelfer/Tiefbauhelferin | 9312 | korrekt | korrekt | unverändert |
| Führungskräfte in der Erbringung von Dienstleistungen des Bildungswesens | 1345 | Leiter einer Schule oder Universität | 1345 | korrekt | plausibel | neu (bisher: Führungskraft für Unternehmensdienstleistungen); Führungskraft Unternehmensdienstleistungen (1219) statt Bildungsleitung |
| Empfangskräfte (allgemein) | 4226 | Empfangssekretär/Empfangssekretärin | 4226 | korrekt | plausibel | neu (bisher: Empfangskraft für Tierarztpraxis); Tierarztpraxis = Teilgebiet; Empfangssekretär/in 4226.1 |
| Einkäufer | 3323 | Einkäufer/Einkäuferin | 3323 | korrekt | korrekt | unverändert |
| Journalisten | 2642 | Journalist/Journalistin | 2642 | korrekt | korrekt | unverändert |
| Baumetallverformer und Metallbauer | 7214 | Metallbauer – Konstruktionstechnik | 7214 | korrekt | korrekt | unverändert |
| Chemieingenieur/in / Verfahrenstechniker/in | 2145 | Chemieingenieur/Chemieingenieurin | 2145 | korrekt | korrekt | unverändert |
| Mechatroniker/in EFZ | 7421 | Elektronikmechaniker | 3113 | plausibel | plausibel | neu (bisher: Kraftfahrzeugmechatroniker in der Fahrzeugmodernisierung); Berufsdefinition unklar; Vorschlag = Elektronikmechaniker/in (alt. Mechatroniker/in) — Ausnahme ISCO: Mechatroniker/in EFZ: Code 7421 offen (#51), ESCO führt «Mechatroniker» als Bezeichnung von Elektronikmechaniker (3113) |
| Marketing-/Kommunikationsleiter/in | 1222 | Kommunikationsmanager | 1222 | korrekt | falsch | neu (bisher: Lehrkraft für Wirtschaft und Marketing); Lehrkraft Wirtschaft/Marketing statt Kommunikations-/Marketingleitung |
| Versicherungsexperte/-expertin | 2422 | Underwriter im Versicherungswesen | 3321 | plausibel | falsch | neu (bisher: Experte für Datenintegration); Experte Datenintegration statt Versicherung; Vorschlag Underwriter/in (Einschätzung, Beruf unscharf) — Ausnahme ISCO: Versicherungsexperte/-expertin: Code 2422 offen (#51), ESCO Underwriter 3321 |
| Chemo- und Physikotechniker | 3111 | Chemielaborant/Chemielaborantin | 3111 | korrekt | korrekt | unverändert |
| Bauführer/in | 3112 | Oberbauleiter/Oberbauleiterin | 3123 | plausibel | korrekt | unverändert — Ausnahme ISCO: CH-ISCO-19 führt Bauführer in 3112, ESCO die Bauleitung (construction general supervisor) in 3123 |
| Grafik- und Multimediadesigner | 2166 | Grafikdesigner/Grafikdesignerin | 2166 | korrekt | plausibel | neu (bisher: Multimedia-Designer); Grafikdesigner/in (2166.9) statt Multimedia-Designer/in (2513) |
| Biologen, Botaniker, Zoologen und verwandte Berufe | 2131 | Biologe/Biologin | 2131 | korrekt | plausibel | neu (bisher: Botaniker/Botanikerin); Botaniker/in = Teilgebiet; Biologe/Biologin 2131.4 |
| Barkeeper | 5132 | Barkeeper/Barkeeperin | 5132 | korrekt | korrekt | unverändert |
| Führungskräfte in Forschung und Entwicklung | 1223 | Forschungs- und Entwicklungsleiter | 1223 | korrekt | korrekt | unverändert |
| Prozess- und Produktionsingenieure | 2141 | Produktionsingenieur | 2141 | korrekt | korrekt | unverändert |
| Musiklehrer | 2354 | Lehrkraft für Musik | 2354 | korrekt | korrekt | unverändert |
| Sprachlehrer | 2353 | Lehrkraft für Sprachschulen | 2353 | korrekt | plausibel | neu (bisher: Lehrkraft für Gebärdensprache); Gebärdensprache = Teilgebiet; Lehrkraft für Sprachschulen 2353.1 |
| Postverteiler und -sortierer | 4412 | Postabfertiger/Postabfertigerin | 4412 | korrekt | korrekt | unverändert |
| Medizintechniker im Bereich bildgebende Verfahren und Therapiegeräte | 3211 | Röntgentechniker/Röntgentechnikerin | 2269 | plausibel | falsch | neu (bisher: Konstruktionsmitarbeiter in der Medizintechnik); Konstruktion Medizintechnik (8219) statt Radiologie; ESCO führt Röntgentechniker/in (EN radiographer) unter 2269, nicht 3211 — Ausnahme ISCO: ESCO führt Radiologiefachpersonal (radiographer) unter 2269 |
| Bürokräfte in der Statistik, im Finanz- und Versicherungswesen | 4312 | Back-Office-Mitarbeiter | 4312 | korrekt | falsch | neu (bisher: Statistiker/Statistikerin); Statistiker/in (2120, akademisch) statt Bürokraft; Back-Office-Mitarbeiter/in 4312.2 |
| Metzger, Fischhändler und -verarbeiter und verwandte Berufe | 7511 | Fleischer/Fleischerin | 7511 | korrekt | plausibel | neu (bisher: Fischverarbeiter/Fischverarbeiterin); Fischverarbeiter/in = Teilgebiet; Fleischer/in 7511.1 |
| Techniker für den Betrieb von Informations- und Kommunikationstechnologie | 3511 | Rechenzentrumsbetreiber | 3511 | korrekt | plausibel | neu (bisher: IKT-Techniker/IKT-Technikerin); Rechenzentrumsbetreiber/in (data centre operator 3511.1) statt IKT-Techniker/in (3512) |
| Netzwerkingenieur/in | 2523 | IT-Netzwerkingenieur | 2523 | korrekt | korrekt | unverändert |
| Ökonom/in / Volkswirt/in | 2631 | Volkswirtschaftler/Volkswirtschaftlerin | 2631 | korrekt | korrekt | unverändert |
| IT-Sicherheitsspezialist/in | 2529 | IT-Sicherheitsadministrator | 2529 | korrekt | korrekt | unverändert |
| Spezialisten der traditionellen und komplementären Medizin | 2230 | Therapeut Komplementärmedizin | 2230 | korrekt | plausibel | neu (bisher: Therapeut Traditionelle Chinesische Medizin); Therapeut/in Komplementärmedizin (2230.2) statt TCM (Teilgebiet) |
| Musiker, Sänger und Komponisten | 2652 | Musiker/Musikerin | 2652 | korrekt | plausibel | neu (bisher: Sänger/Sängerin); Musiker/in (2652.3) statt Sänger/in (Teilgebiet) |
| Führungskräfte in der Produktion im Bau | 1323 | Führungskraft bei Bauprojekten | 1323 | korrekt | falsch | neu (bisher: Führungskraft in der Produktion von Waren); Produktion von Waren (1321) statt Bau 1323; URI 2x vergeben |
| Trainer und Betreuer im Bereich Fitness und Erholung | 3423 | Fitnesstrainer/Fitnesstrainerin | 3423 | korrekt | korrekt | unverändert |
| Handelsmakler | 3324 | Warenmakler/Warenmaklerin | 3324 | korrekt | fallback | neu (bisher: ohne URI); beschreibung_quelle «ESCO» obwohl ohne URI |
| Reisebegleiter und Stewards | 5111 | Steward/Stewardess | 5111 | korrekt | korrekt | unverändert |
| Führungskräfte in Hotels | 1411 | Leiter eines Beherbergungsbetriebs | 1411 | korrekt | falsch | neu (bisher: Sicherheitsbeauftragter des Beherbergungsbetriebs); Sicherheitsbeauftragte/r Beherbergung (5414) statt Hotelleitung |
| Bediener von Maschinen zur Herstellung von Nahrungs- und Genussmitteln | 8160 | Lebensmittelproduktionsmitarbeiter | 8160 | korrekt | plausibel | neu (bisher: Hydriermaschinenbediener); Hydriermaschinen = Nischen-Teilgebiet; Lebensmittelproduktionsmitarbeiter/in 8160.34 |
| Bürokräfte in der Material- und Fertigungsplanung und verwandte Berufe | 4322 | Material- und Produktionskoordinator im Maschinenbau | 4322 | korrekt | falsch | neu (bisher: Zuschneider (Bekleidung)); Zuschneider/in Bekleidung (7532) statt Material-/Fertigungsplanung |
| Leiter eines Einzelhandelsgeschäftes | 5221 | Einzelhändler/Einzelhändlerin | 5221 | korrekt | plausibel | neu (bisher: Leiter eines Bekleidungsgeschäftes); Leiter/in Bekleidungsgeschäft (1420) = Teilgebiet; Einzelhändler/in 5221.1 |
| Medizintechniker im Bereich Labor und Pathologie | 3212 | Medizinisch-technischer Laborassistent | 3212 | korrekt | plausibel | neu (bisher: Pathologieassistent); Pathologieassistent/in = Teilgebiet; Med.-techn. Laborassistent/in 3212.2 |
| Kranführer, Aufzugmaschinisten und Bediener verwandter Hebeeinrichtungen | 8343 | Baukranführer/Baukranführerin | 8343 | korrekt | korrekt | unverändert |
| Raumgestalter und Dekorateure | 3432 | Raumgestalter/Raumgestalterin | 3432 | korrekt | korrekt | unverändert |
| Produkttester und -klassierer (ohne Nahrungsmittel und Getränke) | 7543 | Qualitätsprüfer/Qualitätsprüferin | 7543 | korrekt | plausibel | neu (bisher: Holzwerkstoffplattenklassierer); Holzwerkstoffplatten = Nische; Qualitätsprüfer/in 7543.10 |
| Fachkräfte in Personalschulung und -entwicklung | 2424 | betrieblicher Aus- und Weiterbildner | 2424 | korrekt | plausibel | neu (bisher: Business Coach); Business Coach = Teilgebiet; betriebliche/r Aus- und Weiterbildner/in |
| Gipser, Trockenbauer | 7123 | Stuckateur/Stuckateurin | 7123 | korrekt | korrekt | unverändert |
| Fachkräfte in Sozialverwaltung und -versicherung | 3353 | Sozialversicherungsfachangestellter | 3353 | korrekt | falsch | neu (bisher: Inkassobeauftragter für Versicherungen); Inkasso Versicherungen (4214) statt Sozialversicherung |
| Hilfsarbeiter in Ackerbau und Tierhaltung (ohne ausgeprägten Schwerpunkt) | 9213 | Produktionsarbeiter im Bereich Pflanzenbau | 9213 | plausibel | plausibel | neu (bisher: Fachkraft für Nutztierhaltung); Nutztierhaltung (9212, 2x vergeben); Produktionsarbeiter/in Pflanzenbau 9213.1 |
| Pädagogik- und Didaktikspezialisten | 2351 | Lehrplanforscher/Lehrplanforscherin | 2351 | korrekt | plausibel | neu (bisher: Koordinator für Sonderpädagogik); Sonderpädagogik-Koordination = Teilgebiet; Lehrplanforscher/in (alt. Lehrplanentwickler) |
| Regisseure und Produzenten im Film- und Bühnenbereich sowie in verwandten Bereichen | 2654 | Film- und Fernsehproduzent | 2654 | korrekt | korrekt | unverändert |
| Führungskräfte in der Erbringung von Finanz- und Versicherungsdienstleistungen | 1346 | Bankmanager/Bankmanagerin | 1346 | korrekt | plausibel | neu (bisher: Führungskraft für Unternehmensdienstleistungen); Führungskraft Unternehmensdienstleistungen (1219) statt Finanz/Versicherung 1346 |
| Hilfsarbeiter im Gartenbau | 9214 | Gartenhilfsarbeiter | 9214 | korrekt | korrekt | unverändert |
| Isolierer | 7124 | Isoliermonteur/Isoliermonteurin | 7124 | korrekt | fallback | neu (bisher: ohne URI); beschreibung_quelle «ESCO» obwohl ohne URI |
| Konferenz- und Veranstaltungsplaner | 3332 | Eventmanager/Eventmanagerin | 3332 | korrekt | plausibel | neu (bisher: Manager des Veranstaltungsortes); Manager/in Veranstaltungsort = Teilgebiet; Eventmanager/in 3332.2 |
| PR-Spezialist/in | 2432 | Public-Relations-Fachkraft | 2432 | korrekt | korrekt | unverändert |
| Elektroplaner/in EFZ | 3113 | Elektrotechniker/Elektrotechnikerin | 3113 | korrekt | falsch | neu (bisher: Bauelektriker/Bauelektrikerin); Bauelektriker/in (Installation) statt Planung; URI 2x vergeben |
| Umweltingenieur/in | 2143 | Umweltingenieur/Umweltingenieurin | 2143 | korrekt | korrekt | unverändert |
| Statistiker/in / Aktuar/in | 2120 | Aktuar/Aktuarin | 2120 | korrekt | korrekt | unverändert |
| Geistliche Seelsorger | 2636 | Seelsorger/Seelsorgerin | 2636 | korrekt | korrekt | unverändert |
| Techniker für Rundfunk und audiovisuelle Medien | 3521 | Fachkraft AV-Medientechnik | 3521 | korrekt | falsch | neu (bisher: Auslandskorrespondent); Auslandskorrespondent/in statt AV-Technik |
| Übersetzer, Dolmetscher und andere Linguisten | 2643 | Übersetzer/Übersetzerin | 2643 | korrekt | korrekt | unverändert |
| Datenbankentwickler und -administratoren | 2521 | Datenbankentwickler | 2521 | korrekt | korrekt | unverändert |
| Produkt- und Textildesigner | 2163 | Industriedesigner/Industriedesignerin | 2163 | korrekt | plausibel | neu (bisher: Textildesigner/Textildesignerin); Industriedesigner/in (2163.1) statt Textildesigner/in (Teilgebiet) |
| Reiseverkehrsfachkräfte | 4221 | Reiseberater/Reiseberaterin | 4221 | korrekt | fallback | neu (bisher: ohne URI); beschreibung_quelle «ESCO» obwohl ohne URI; Reiseberater/in (alt. Reiseverkehrskaufmann) |
| Feuerwehrmann/-frau | 5411 | Berufsfeuerwehrmann/Berufsfeuerwehrfrau | 5411 | korrekt | korrekt | unverändert |
| Notar/in | 2619 | Notar/Notarin | 2619 | korrekt | korrekt | unverändert |
| Primarlehrer/in | 2341 | Lehrkraft im Primarbereich | 2341 | korrekt | korrekt | unverändert |
| Sekundarlehrer/in | 2330 | Lehrkraft Sekundarstufe | 2330 | korrekt | korrekt | unverändert |
| Pflegeassistent/in | 5321 | Pflegehelfer/Pflegehelferin | 5321 | korrekt | korrekt | URI unverändert, Text auf v1.2.1 aktualisiert |
| Lastwagenfahrer/in | 8332 | Lastkraftwagenfahrer | 8332 | korrekt | korrekt | unverändert |
| Arztpraxisassistent/in | 3256 | Medizinischer Fachangestellter | 3256 | korrekt | korrekt | unverändert |
| Lieferwagenfahrer/in | 8322 | Pkw- und Kleintransporter-Lieferfahrer | 8322 | korrekt | plausibel | neu (bisher: cargo vehicle driver); Lkw-Fahrer/in (8332) statt Lieferwagen 8322; URI 2x vergeben |
| Telematiker/in EFZ | 3522 | Maschinenbautechniker im Bereich Telekommunikation | 3522 | plausibel | fallback | neu (bisher: ohne URI); Telekommunikationstechnik 3522.1 |
| Drogist/in | 5223 | — (KI-generiert) | – | fallback | fallback | unverändert |
