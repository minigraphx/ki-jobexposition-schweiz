# ISCO-Code-Audit und Beschäftigtenzahlen (Issue #51)

Stand: 2026-10. Prüfung aller 204 bisherigen Berufe in `data/processed/scores.csv`: Passt der
`isco_code` zur Berufsbezeichnung? Referenz sind die CH-ISCO-19-Bezeichnungen der BFS
Strukturerhebung (SE) 2024 (Asset 36492006, Spalten 3–5: Berufsgattung, Berufsart, Bezeichnung).
Zusätzlich wurde die ISCO-08-Gruppe des jeweiligen ESCO-Matches abgefragt (ESCO-API, nur als
Hinweis — viele ESCO-Matches sind selbst fehlerhaft, separates Audit).

**Regel:** Korrigiert wurden nur Fälle mit hoher Sicherheit (SE-Bezeichnung des alten Codes passt
eindeutig nicht, Ziel-Gattung eindeutig). Fälle mit mittlerer Sicherheit sind unten als offen
dokumentiert und unverändert.

## Ergebnis in Kürze

- **21 ISCO-Codes korrigiert** (hohe Sicherheit), **15 offen** (mittlere Sicherheit).
- **22 Zusammenlegungen** (Fallback A), **3 Aufteilungen** über Berufsarten (Option B: 2330, 5131, 5223).
- Berufe: **204 → 179**.
- Summe Beschäftigte (`scores.csv`, App): **3,880.8 → 3,566.9 Tsd.**; `berufe_ch.csv` vorher 4,488.5 Tsd. (Doppelzählung). SE 2024 total: 4'583.7 Tsd.
- Invariante (Test `tests/test_beschaeftigte_se.py`): Σ `beschaeftigte_1000` je 4-stelligem Code = SE-Wert.
- **Nachtrag:** 8 fehlende SE-Berufsgattungen ≥ 5'000 Erwerbstätige aufgenommen (u. a. die durch
  Code-Korrekturen frei gewordenen 3123, 3115, 3434, 7223, 3311, 3355): Berufe **179 → 187**,
  Σ **3'566.9 → 3'723.8 Tsd.**, Abdeckung der SE-Erwerbstätigen **77.8 % → 81.2 %** — siehe
  [Neu aufgenommene Berufsgattungen](#neu-aufgenommene-berufsgattungen-nachtrag). Die neuen
  Einträge sind noch nicht bewertet.

## Korrigierte ISCO-Codes (hohe Sicherheit)

| Beruf | alter Code | SE-Bezeichnung alt | neuer Code | SE-Bezeichnung neu | Begründung | ESCO-Match (ISCO) | Sicherheit |
|---|---|---|---|---|---|---|---|
| Koch/Köchin EFZ | 3434 | Küchenchefs, stv. Küchenchefs und Souschefs | 5120 | Köche | 3434 = Küchenchefs/Souschefs (Kaderstufe); Koch/Köchin EFZ ist die Grundbildung → 5120 Köche | 3434 private chef | hoch |
| Chemielaborant/in EFZ | 3113 | Elektrotechniker | 3111 | Chemo- und Physikotechniker | 3113 = Elektrotechniker; Laborant/in EFZ Chemie gehört zu 3111 Chemo- und Physikotechniker (Berufsart 31111 Chemotechniker) | 3111 chemistry technician ✓ | hoch |
| Drogist/in | 3256 | Medizinische Assistenten | 5223 | Verkäufer in Handelsgeschäften | 3256 = Medizinische Assistenten (MPA); die SE führt Drogisten als eigene Berufsart 52231 unter 5223 | – | hoch |
| Hauswirtschaftler/in EFZ | 5131 | Chefs de service, Servicefach- und Servicehilfskräfte in Restaurants | 5151 | Reinigungs- und Hauswirtschaftleiter und -kräfte in Büros, Hotels und anderen Einrichtungen | 5131 = Service in Restaurants; Fachmann/-frau Hauswirtschaft EFZ arbeitet in Heimen, Spitälern, Hotels → 5151 Reinigungs- und Hauswirtschaftsleiter und -kräfte | – | hoch |
| Hotelfachmann/-frau EFZ | 5131 | Chefs de service, Servicefach- und Servicehilfskräfte in Restaurants | 5151 | Reinigungs- und Hauswirtschaftleiter und -kräfte in Büros, Hotels und anderen Einrichtungen | Bildungsplan Hotelfachfrau/-mann EFZ: Kern ist Hauswirtschaft (Zimmer, Lingerie, Reinigung), Service nur ergänzend → 5151 (Bezeichnung nennt Hotels ausdrücklich) | 2166 director of photography | hoch |
| Buchhalter/in | 2411 | Wirtschaftsprüfer, Steuerberater und verwandte Berufe | 3313 | Fachkräfte im Rechnungswesen | 2411 = akademische Wirtschaftsprüfer/Steuerberater; ISCO-08 ordnet Buchhalter (bookkeeper) 3313 zu (Fachkräfte im Rechnungswesen) | 2411 accountant | hoch |
| Treuhänder/in | 2412 | Finanz- und Anlageberater | 2411 | Wirtschaftsprüfer, Steuerberater und verwandte Berufe | 2412 = Finanz- und Anlageberater; Treuhand (Buchführung, Steuern, Revision) = «verwandte Berufe» von 2411 Wirtschaftsprüfer, Steuerberater | 2412 personal trust officer | hoch |
| Steuerberater/in | 2412 | Finanz- und Anlageberater | 2411 | Wirtschaftsprüfer, Steuerberater und verwandte Berufe | SE-Bezeichnung von 2411 nennt Steuerberater ausdrücklich | 2412 business valuer | hoch |
| Vermögensverwalter/in / Wealth Manager | 2413 | Finanzanalysten | 2412 | Finanz- und Anlageberater | 2413 = Finanzanalysten (Analyse); ISCO-08 2412 «Financial and investment advisers … invest and manage funds on their behalf» = Vermögensverwaltung/Kundenberatung | 3311 asset manager | hoch |
| Bankkaufmann/-frau | 3311 | Wertpapierhändler, -makler und Finanzmakler | 4211 | Schalterbedienstete und Fachkräfte im Bereich Finanzdienstleistungen | 3311 = Wertpapierhändler/-makler; Bankangestellte mit kaufm. Grundbildung → 4211, Berufsart 42112 Fachkräfte im Bereich Finanzdienstleistungen | 4211 bank teller ✓ | hoch |
| Logistiker/in EFZ | 3331 | Fachkräfte für Abrechnungs- und Speditionsdienstleistungen | 4321 | Fachkräfte in der Lagerwirtschaft | 3331 = Abrechnungs- und Speditionsfachleute; Logistiker/in EFZ (Lager) → 4321 Fachkräfte in der Lagerwirtschaft | – | hoch |
| Polizist/in | 3355 | Polizeikommissare und Kriminalbeamte | 5412 | Polizisten (ohne Polizeikommissare) | 3355 = Polizeikommissare und Kriminalbeamte; uniformierte Polizei → 5412 Polizisten (ohne Polizeikommissare) | 5412 police officer ✓ | hoch |
| Bauführer/in | 3123 | Poliere und Vorarbeiter | 3112 | Bauführer und Bautechniker | 3123 = Poliere und Vorarbeiter; SE-Gattung 3112 «Bauführer und Bautechniker» (Berufsarten 31121/31122 Bauführer) | 3123 construction general supervisor | hoch |
| Hochbauzeichner/in EFZ | 3112 | Bauführer und Bautechniker | 3118 | Technische Zeichner | 3112 = Bauführer; Zeichner/in EFZ Architektur → 3118 Technische Zeichner (Berufsart 31182 Technische Zeichner, Bau) | 3118 architectural drafter ✓ | hoch |
| Polymechaniker/in EFZ | 7223 | Werkzeugmaschineneinrichter und -bediener | 7200 | Metallarbeiter, Mechaniker, Polymechaniker, Produktionsmechaniker und verwandte Berufe, onA | 7223 = Werkzeugmaschineneinrichter; CH-ISCO-19 führt Polymechaniker als eigene Berufsart 72001 (Gattung 7200) | 7233 industrial machinery mechanic | hoch |
| Automatiker/in EFZ | 3115 | Maschinenbautechniker, Techniker im Bereich Systemtechnik, Automation und Unternehmensprozesse | 7412 | Automatiker und verwandte Berufe | 3115 = Maschinenbau-/Systemtechniker (Stufe Techniker HF); Automatiker/in EFZ → 7412 Automatiker und verwandte Berufe | 3119 automation engineering technician | hoch |
| Landwirt/in EFZ | 6111 | Gemüseanbauer | 6130 | Landwirte mit Ackerbau und Tierhaltung (ohne ausgeprägten Schwerpunkt) | 6111 = Gemüseanbauer; Landwirt/in EFZ (gemischter Betrieb) → 6130 Landwirte mit Ackerbau und Tierhaltung | 6130 mixed farmer ✓ | hoch |
| Journalist/in / Redakteur/in | 2641 | Autoren und verwandte schriftstellerische Berufe | 2642 | Journalisten | 2641 = Autoren und schriftstellerische Berufe; Journalisten/Redaktoren → 2642 Journalisten | 2642 business journalist ✓ | hoch |
| Kassierer/in | 5223 | Verkäufer in Handelsgeschäften | 5230 | Kassierer und Kartenverkäufer | 5223 = Verkäufer; Kassierer/innen haben eine eigene Gattung 5230 Kassierer und Kartenverkäufer | 5222 checkout supervisor | hoch |
| Sachbearbeiter/in öff. Verwaltung | 4416 | Bürokräfte im Personalwesen | 4110 | Allgemeine Bürokräfte | 4416 = Bürokräfte im Personalwesen; allgemeine Sachbearbeitung (auch in der Verwaltung) → 4110 Allgemeine Bürokräfte (ISCO ist tätigkeits-, nicht branchenbezogen) | 4416 human resources assistant | hoch |
| Produktionsmitarbeiter/in (Pharma) | 8211 | Berufe der Montage von mechanischen Bauteilen | 8131 | Bediener von Anlagen und Maschinen für chemische Erzeugnisse | 8211 = Montage mechanischer Bauteile; Pharmaproduktion → 8131 Bediener von Anlagen und Maschinen für chemische (inkl. pharmazeutische) Erzeugnisse | 8131 fermenter operator ✓ | hoch |

✓ = ISCO-Gruppe des ESCO-Matches bestätigt den neuen Code.

## Offene Fälle (mittlere Sicherheit, Code unverändert)

| Beruf | Code | SE-Bezeichnung | Vorschlag | SE-Bezeichnung Vorschlag | Begründung | Sicherheit |
|---|---|---|---|---|---|---|
| Qualitätsmanager/in | 2146 | Bergbauingenieure, Metallurgen und verwandte Berufe | 2141 oder 1321 | Prozess- und Produktionsingenieure | 2146 = Bergbauingenieure/Metallurgen (SE 2024 nicht publiziert) ist sicher falsch; ESCO-Match «industrial quality manager» = 1321, Qualitätsingenieure = 2141 — Ziel unklar | mittel |
| Versicherungsexperte/-expertin | 2422 | Spezialisten in der strategischen Planung in Politik und Wirtschaft | 3321 oder 2120 | Versicherungsvertreter | 2422 = strategische Planung in Politik/Wirtschaft passt nicht; Versicherungsexperte HFP (Underwriting, Schaden) eher 3321, Aktuare 2120 | mittel |
| Versicherungskaufmann/-frau | 3312 | Fachkräfte im Bereich Kredit und Darlehen | 4312 oder 3321 | Bürokräfte in der Statistik, im Finanz- und Versicherungswesen | 3312 = Kredit und Darlehen passt nicht; Sachbearbeitung Versicherung 4312 oder Aussendienst 3321 | mittel |
| Maschinenführer/in | 8211 | Berufe der Montage von mechanischen Bauteilen | 8100 (onA) / 8189 | Bediener stationärer Anlagen und Maschinen, onA | 8211 = Montage mechanischer Bauteile passt nicht; Maschinenführer ohne Branchenangabe codiert die SE unter 8100 «onA» | mittel |
| Posthalter/in / Logistiker/in Post | 4415 | Bürokräfte für Registratur und Dokumentation | 4211 (42111) oder 4412 | Schalterbedienstete und Fachkräfte im Bereich Finanzdienstleistungen | 4415 = Registratur/Dokumentation passt nicht; Poststellen = 42111 Schalterbedienstete Post, Zustellung = 4412 Postverteiler — Titel umfasst beides | mittel |
| Filialleiter/in (Detailhandel) | 1420 | Führungskräfte in Gross- und Einzelhandel | 5221 | Leiter eines Einzelhandelsgeschäftes | 1420 = Führungskräfte Gross-/Einzelhandel (SE 3.2k) vs. 5221 «Leiter eines Einzelhandelsgeschäftes» (7.1k) — CH-Codierpraxis unklar | mittel |
| Telematiker/in EFZ | 3522 | Telekommunikationstechniker | 7422 | Installateure und Servicetechniker im Bereich Informations- und Kommunikationstechnik | 3522 = Telekommunikationstechniker (Techniker-Stufe); Telematiker/in EFZ eher 7422 Installateure/Servicetechniker IKT | mittel |
| Mechatroniker/in EFZ | 7421 | Elektroniker und Elektronik-Servicetechniker | 7231 / 7412 | Kraftfahrzeugmechaniker und -schlosser | Kein CH-Beruf «Mechatroniker/in EFZ»; je nach Gemeintem Automobil-Mechatroniker (7231) oder Automatiker (7412) | mittel |
| Datenwissenschaftler/in / Data Scientist | 2514 | Anwendungsprogrammierer | 2529 (25291) oder 2120 | Fachkräfte für Datenbanken und Netzwerke, anderweitig nicht genannt. | 2514 = Anwendungsprogrammierer; CH-ISCO-19 führt «Data Mining» in Berufsart 25291 | mittel |
| IT-Projektleiter/in | 2511 | Systemanalytiker | 2512 (25124) | Softwareentwickler | CH-ISCO-19 hat die Berufsart 25124 «Softwareentwickler, Projektmanagement»; 2511 würde dann ohne Beruf bleiben | mittel |
| Projektleiter/in (allg.) | 2421 | Spezialisten im Bereich Management- und Organisationsanalyse | 3000 (30001) | Techniker und gleichrangige nichttechnische Berufe, onA | Die SE codiert unspezifische Projektleiter als 30001 «Projektleiter, onA» (43.6k); 3000 enthält aber auch Gruppenleiter onA | mittel |
| Projektleiter/in (Technik) | 2149 | Ingenieure, anderweitig nicht genannt | 3000 (30001) | Techniker und gleichrangige nichttechnische Berufe, onA | wie Projektleiter/in (allg.) | mittel |
| Compliance Officer | 2412 | Finanz- und Anlageberater | 2619 / 2411 / 3359 | Juristen, anderweitig nicht genannt | keine eindeutige ISCO-Stelle für Compliance; 2412 (Finanz-/Anlageberater) nur bedingt passend | mittel |
| Sozialpädagoge/-pädagogin | 2635 | Sozialarbeiter | 3412 | Soziale Fachkräfte | Sozialpädagogik HF könnte als 3412 Soziale Fachkräfte codiert sein; FH-Abschluss 2635 | mittel |
| Marketing-/Kommunikationsleiter/in | 1222 | Führungskräfte in Werbung und Öffentlichkeitsarbeit | 1221 (12212) | Führungskräfte in Vertrieb und Marketing | 1222 = Werbung/Öffentlichkeitsarbeit; Marketingleitung = Berufsart 12212 Führungskräfte in Marketing | mittel |

Folgen für die Beschäftigten: Ein offener Fall trägt den SE-Wert seines (vermutlich falschen)
Codes, z. B. Qualitätsmanager/in 2146 = 0.1 Tsd. (2024 nicht publiziert, Wert 2022–2024),
Maschinenführer/in 8211 = 2.2 Tsd., Posthalter/in 4415 = 1.5 Tsd., Versicherungskaufmann/-frau 3312 = 2.1 Tsd.

## Titel enger als die Berufsgattung (kein Fehler, Hinweis)

Diese Berufe sind die einzigen ihrer Gattung und tragen deren vollen SE-Wert:

- **Notar/in**: Gattung 2619 «Juristen, anderweitig nicht genannt» (13.4k); Notare allein (26191) nur 0.8k (< 50 Beobachtungen)
- **Zimmermann/-frau EFZ**: Gattung 7115 umfasst auch Schreiner (71152, 24.8k) und Storenmonteure
- **Sanitärinstallateur/in EFZ**: Gattung 7126 umfasst auch Heizungsinstallateure und Bauspengler
- **Reinigungskraft / Hauswart**: Titel nennt Hauswart; Hauswarte sind eigene Gattung 5153
- **Maler/in und Gipser/in EFZ**: Titel nennt Gipser; Gipser sind eigene Gattung 7123
- **Zugbegleiter/in / Lokführer/in**: Gattung 8311 = Lokomotivführer; Zugbegleiter wären 5112 Schaffner
- **Naturwissenschaftler/in (Biologie/Chemie)**: Gattung 2113 = Chemiker; Biologen sind eigene Gattung 2131
- **Kindergärtnerin/-gärtner**: Gattung 2342 umfasst auch Erzieher im Vorschulbereich (23421, 11.3k)
- **Geschäftsführer/in (KMU)**: Gattung 1120 umfasst alle Geschäftsführer und Vorstände, nicht nur KMU

## Aufteilungen über Berufsarten (Option B)

Wert = Σ zugeordnete Berufsarten + Rest der Gattung (Berufsart «onA», nicht publizierte Werte)
proportional. Jede publizierte Berufsart der Gattung ist genau einem Beruf zugeordnet.

| Gattung | Beruf | Berufsart(en) | SE 2024 (Tsd.) | SE 2022–2024 (Tsd.) | Wert inkl. Rest | Begründung |
|---|---|---|---|---|---|---|
| 2330 Lehrkräfte im Sekundarbereich | Sekundarlehrer/in | 23302 | 25.7 | 24.6 | 29.9 | Berufsart 23302 Lehrkräfte Sekundarstufe I |
| 2330 Lehrkräfte im Sekundarbereich | Gymnasiallehrer/in | 23301 | 17.4 | 15.6 | 20.3 | Berufsart 23301 Lehrkräfte Sekundarstufe II – Allgemeinbildung |
| 5131 Chefs de service, Servicefach- und Servicehilfskräfte in Restaurants | Restaurantfachmann/-frau EFZ | 51311, 51312 | 36.5 | 36.5 | 36.5 | Berufsarten 51312 Servicefachkräfte + 51311 Chefs de Service (Karrierestufe der Restaurantfachleute) |
| 5131 Chefs de service, Servicefach- und Servicehilfskräfte in Restaurants | Servicemitarbeiter/in | 51313 | 29.2 | 29.0 | 29.2 | Berufsart 51313 Servicehilfskräfte (ohne Fachausbildung) |
| 5223 Verkäufer in Handelsgeschäften | Drogist/in | 52231 | 3.6 | 3.7 | 3.6 | Berufsart 52231 Drogisten |
| 5223 Verkäufer in Handelsgeschäften | Verkäufer in Handelsgeschäften | 52230 | 136.7 | 138.9 | 136.7 | Berufsart 52230 Verkäufer in Handelsgeschäften (ohne Drogisten) |

**Blattwahl:** Alle verwendeten Berufsarten-Totale beruhen 2024 auf ≥ 50 Beobachtungen (keine
Klammer im BFS-Blatt) und weichen vom gepoolten Blatt 2022–2024 um höchstens ~11 % ab
(Sekundarstufe II 17.4 vs. 15.6). Deshalb gilt einheitlich das Jahresblatt **2024** — konsistent mit
den Gattungswerten. Das gepoolte Blatt dient nur als Fallback, wo 2024 nicht publiziert ist
(Gattung 2146; Frauenanteil bei «X», z. B. Bauberufe).

## Zusammenlegungen (Fallback A)

Wo die SE die Berufe nicht trennt, gilt ein Eintrag je Gattung (bzw. Berufsart 52230) mit der
SE-Bezeichnung als `beruf`; die bisherigen CH-Titel stehen in `synonyme` (Berufssuche, alte
Permalinks). Scores = beschäftigungsgewichtetes Mittel der bisherigen Einträge (Gewichte = bisherige
`beschaeftigte_1000` in `scores.csv`, auf 0.1 gerundet); Texte, ESCO-Felder, Branche, Qualifikation
und Zeitrahmen vom grössten Teilberuf (`text_von`). Markiert mit `scores_gemittelt = True` und
leerem `beschreibung_hash` → `exposure_scorer.py` bewertet diese Einträge beim nächsten Lauf neu.

| Code | Neuer Eintrag | bisherige Einträge (Beschäftigte alt) | Texte von | score_gesamt alt → neu | Beschäftigte neu | Begründung |
|---|---|---|---|---|---|---|
| 2166 | Grafik- und Multimediadesigner | Grafiker/in (10), UX/UI Designer/in (8) | Grafiker/in | 6.2 / 5.1 → 5.7 | 13.7 | 2166 hat nur eine Berufsart (21660) |
| 2411 | Wirtschaftsprüfer, Steuerberater und verwandte Berufe | Controller/in (20), Wirtschaftsprüfer/in (8), Treuhänder/in (20), Steuerberater/in (12) | Controller/in | 6.8 / 6.8 / 6.2 / 6.4 → 6.5 | 32.9 | 2411 hat nur eine Berufsart (24110); Texte: Gleichstand Controller/in und Treuhänder/in (je 20), Controller/in wegen passendem ESCO-Match |
| 2412 | Finanz- und Anlageberater | Vermögensverwalter/in / Wealth Manager (15), Compliance Officer (8) | Vermögensverwalter/in / Wealth Manager | 6.2 / 6.2 → 6.2 | 20.8 | 2412 hat nur eine Berufsart (24120) |
| 2421 | Spezialisten im Bereich Management- und Organisationsanalyse | Projektleiter/in (allg.) (28), Unternehmensberater/in (18) | Projektleiter/in (allg.) | 4.8 / 5.2 → 5 | 25.0 | 2421 hat nur eine Berufsart (24210) |
| 2512 | Softwareentwickler | Softwareentwickler/in (95), Informatiker/in EFZ (Applikationsentwicklung) (30) | Softwareentwickler/in | 6.8 / 6.2 → 6.7 | 71.4 | Berufsarten 25121–25124 trennen nach Fachgebiet, nicht nach Ausbildungsstufe (EFZ vs. Hochschule) |
| 2635 | Sozialarbeiter | Sozialarbeiter/in (28), Sozialpädagoge/-pädagogin (22) | Sozialarbeiter/in | 2.8 / 2.1 → 2.5 | 19.5 | 2635 hat nur eine Berufsart (26350) |
| 2642 | Journalisten | Journalisten (10.2), Journalist/in / Redakteur/in (8) | Journalisten | 5.8 / 5.8 → 5.8 | 10.2 | Journalist/in / Redakteur/in nach Code-Korrektur in 2642; nur eine Berufsart (26420) |
| 3111 | Chemo- und Physikotechniker | Chemo- und Physikotechniker (8.4), Chemielaborant/in EFZ (10) | Chemielaborant/in EFZ | 4.7 / 4.8 → 4.8 | 8.4 | Chemielaborant/in EFZ nach Code-Korrektur in 3111; der bestehende Gattungs-Eintrag umfasst die ganze Gattung |
| 3118 | Technische Zeichner | Technische Zeichner (28.3), Hochbauzeichner/in EFZ (8) | Technische Zeichner | 6.8 / 6.8 → 6.8 | 28.3 | Hochbauzeichner/in EFZ nach Code-Korrektur in 3118; der bestehende Gattungs-Eintrag umfasst die ganze Gattung |
| 3313 | Fachkräfte im Rechnungswesen | Fachkräfte im Rechnungswesen (36.2), Buchhalter/in (32) | Fachkräfte im Rechnungswesen | 6.8 / 7.2 → 7 | 36.2 | Buchhalter/in nach Code-Korrektur in 3313; nur eine Berufsart (33130) |
| 3334 | Immobilienmakler und -verwalter | Immobilienbewirtschafter/in (12), Immobilienmakler/in (6) | Immobilienbewirtschafter/in | 4.8 / 4.8 → 4.8 | 24.2 | 3334 hat nur eine Berufsart (33340) |
| 4110 | Allgemeine Bürokräfte | Kaufmann/-frau EFZ (allg. Richtung) (110), Sachbearbeiter/in öff. Verwaltung (40) | Kaufmann/-frau EFZ (allg. Richtung) | 4.2 / 6.8 → 4.9 | 224.3 | Sachbearbeiter/in öff. Verwaltung nach Code-Korrektur in 4110; nur eine Berufsart (41100) |
| 4211 | Schalterbedienstete und Fachkräfte im Bereich Finanzdienstleistungen | Schalterbedienstete und Fachkräfte im Bereich Finanzdienstleistungen (39.8), Bankkaufmann/-frau (55) | Bankkaufmann/-frau | 5.8 / 6.4 → 6.1 | 39.8 | Bankkaufmann/-frau nach Code-Korrektur in 4211; der bestehende Gattungs-Eintrag umfasst die ganze Gattung (inkl. 42111 Post) |
| 4321 | Fachkräfte in der Lagerwirtschaft | Lagerist/in (25), Logistiker/in EFZ (20) | Lagerist/in | 6.2 / 5.5 → 5.9 | 28.6 | Logistiker/in EFZ nach Code-Korrektur in 4321; nur eine Berufsart (43210) |
| 5120 | Köche | Köche (48.9), Koch/Köchin EFZ (28) | Köche | 2.8 / 2.1 → 2.5 | 48.9 | Koch/Köchin EFZ nach Code-Korrektur in 5120; nur eine Berufsart (51200) |
| 5151 | Reinigungs- und Hauswirtschaftleiter und -kräfte in Büros, Hotels und anderen Einrichtungen | Reinigungs- und Hauswirtschaftleiter und -kräfte in Büros, Hotels und anderen Einrichtungen (29.4), Hotelfachmann/-frau EFZ (12), Hauswirtschaftler/in EFZ (10) | Reinigungs- und Hauswirtschaftleiter und -kräfte in Büros, Hotels und anderen Einrichtungen | 3.2 / 3.2 / 2.8 → 3.1 | 29.4 | Hotelfachmann/-frau EFZ und Hauswirtschaftler/in EFZ nach Code-Korrektur in 5151; Berufsarten 51511 (Leitung) / 51512 (Kräfte) trennen nach Funktion, nicht nach Ausbildung |
| 5223 | Verkäufer in Handelsgeschäften | Detailhandelsfachmann/-frau EFZ (70), Verkäufer/in (ohne Ausbildung) (40) | Detailhandelsfachmann/-frau EFZ | 3.2 / 4.2 → 3.6 | 136.7 | Berufsart 52230 trennt nicht nach Ausbildung (EFZ vs. ohne); Drogisten (52231) bleiben eigener Beruf |
| 5230 | Kassierer und Kartenverkäufer | Kassierer und Kartenverkäufer (8.8), Kassierer/in (25) | Kassierer/in | 7.2 / 6.4 → 6.6 | 8.8 | Kassierer/in nach Code-Korrektur in 5230; nur eine Berufsart (52300) |
| 5412 | Polizisten (ohne Polizeikommissare) | Polizisten (ohne Polizeikommissare) (20.5), Polizist/in (18) | Polizisten (ohne Polizeikommissare) | 3.2 / 3.2 → 3.2 | 20.5 | Polizist/in nach Code-Korrektur in 5412; nur eine Berufsart (54120) |
| 6130 | Landwirte mit Ackerbau und Tierhaltung (ohne ausgeprägten Schwerpunkt) | Landwirte mit Ackerbau und Tierhaltung (ohne ausgeprägten Schwerpunkt) (46.6), Landwirt/in EFZ (25) | Landwirte mit Ackerbau und Tierhaltung (ohne ausgeprägten Schwerpunkt) | 2.8 / 2.8 → 2.8 | 46.6 | Landwirt/in EFZ nach Code-Korrektur in 6130; nur eine Berufsart (61300) |
| 7412 | Automatiker und verwandte Berufe | Automatiker und verwandte Berufe (13.2), Automatiker/in EFZ (12) | Automatiker und verwandte Berufe | 3.2 / 4.2 → 3.7 | 13.2 | Automatiker/in EFZ nach Code-Korrektur in 7412; nur eine Berufsart (74120) |
| 8131 | Bediener von Anlagen und Maschinen für chemische Erzeugnisse | Bediener von Anlagen und Maschinen für chemische Erzeugnisse (6.7), Produktionsmitarbeiter/in (Pharma) (18) | Produktionsmitarbeiter/in (Pharma) | 5.2 / 4.8 → 4.9 | 6.7 | Produktionsmitarbeiter/in (Pharma) nach Code-Korrektur in 8131; nur eine Berufsart (81310) |

## Beschäftigte vorher / nachher je Branche (App, `scores.csv`)

| Branche | Berufe vorher | Tsd. vorher | Berufe nachher | Tsd. nachher | Δ Tsd. |
|---|---|---|---|---|---|
| Verwaltung | 20 | 485.0 | 20 | 662.4 | +177.4 |
| Gesundheit | 18 | 490.8 | 18 | 411.7 | -79.1 |
| Dienstleistungen | 16 | 299.3 | 15 | 330.0 | +30.7 |
| Industrie | 29 | 429.0 | 26 | 318.6 | -110.4 |
| Bau | 17 | 232.1 | 16 | 299.7 | +67.6 |
| Bildung | 11 | 229.4 | 11 | 220.3 | -9.1 |
| Finanzen | 15 | 309.5 | 9 | 194.7 | -114.8 |
| ICT | 14 | 255.7 | 12 | 181.3 | -74.4 |
| Detailhandel | 8 | 186.1 | 6 | 171.6 | -14.5 |
| Gastgewerbe | 9 | 183.8 | 7 | 169.9 | -13.9 |
| Transport | 12 | 196.3 | 11 | 161.6 | -34.7 |
| Soziales | 5 | 137.5 | 4 | 118.2 | -19.3 |
| Medien | 8 | 97.9 | 7 | 92.6 | -5.3 |
| Landwirtschaft | 5 | 99.5 | 4 | 85.2 | -14.3 |
| Öff. Verwaltung | 6 | 104.5 | 4 | 43.6 | -60.9 |
| Recht | 3 | 36.1 | 3 | 42.1 | +6.0 |
| Immobilien | 2 | 18.0 | 1 | 24.2 | +6.2 |
| Versicherungen | 3 | 54.3 | 3 | 23.5 | -30.8 |
| Sicherheit | 1 | 12.0 | 1 | 14.0 | +2.0 |
| Umwelt | 1 | 6.0 | 1 | 1.7 | -4.3 |
| Beratung | 1 | 18.0 | 0 | 0.0 | -18.0 |
| **Total** | 204 | 3,880.8 | 179 | 3,566.9 | -313.9 |

Die Abnahme stammt aus der aufgelösten Doppelzählung (in `berufe_ch.csv` z. B. drei 5223-Berufe mit
je 140.3 Tsd.; doppelt belegte Gattungen wie 3112/3113/8211) und aus nicht belegten, zu hohen Handlisten-Werten (z. B.
Dipl. Pflegefachperson 130 → 96.5, Bankkaufmann/-frau 55 → Gattung 4211 = 39.8). Zunahmen gibt es,
wo Gattungen bisher zu klein angesetzt waren (z. B. Geschäftsführer/in 35 → 137.2, Kaufmann/-frau
EFZ + Sachbearbeiter/in öff. Verwaltung 150 → Allgemeine Bürokräfte 224.3).

## Abgleich mit dem parallelen ESCO-Audit (#52)

Die Einschätzungen aus dem ESCO-Audit wurden gegen die SE-Bezeichnungen geprüft:

| Fall | ESCO-Audit | Entscheid hier | Begründung |
|---|---|---|---|
| Koch/Köchin EFZ 3434 → 5120, Chemielaborant/in EFZ 3113 → 3111 | bestätigt | korrigiert | SE-Bezeichnungen eindeutig |
| Pharma 8211 → 8131, Sachbearbeiter/in öff. Verwaltung 4416 → 4110, Kassierer/in 5223 → 5230, Hochbauzeichner/in 3112 → 3118, Steuerberater/in 2412 → 2411, Landwirt/in EFZ 6111 → 6130, Journalist/in 2641 → 2642, Logistiker/in EFZ 3331 → 4321 | Verdacht | korrigiert (hoch) | deckt sich mit diesem Audit |
| Bankkaufmann/-frau 3311 → 3312/4211 | Verdacht | 4211 (hoch) | 3312 = Kredit und Darlehen; Bankangestellte = Berufsart 42112 |
| Hauswirtschaftler/in EFZ 5131 → 5152/5151 | Verdacht | 5151 (hoch) | 5152 = Hauswirtschafter in Privathaushalten (0.9k); Fachleute Hauswirtschaft EFZ arbeiten in Heimen, Spitälern, Hotels |
| Versicherungskaufmann/-frau 3312 → 4312 | Verdacht | offen (mittel) | 3312 sicher falsch, ESCO-Match «insurance clerk» = 4312; Kaufleute EFZ Versicherung könnten aber wie Kaufleute EFZ allgemein unter 4110 codiert sein |
| Qualitätsmanager/in 2146 | falsch | offen (mittel) | Code sicher falsch, Ziel unklar (1321 / 2141) |
| Posthalter/in 4415 → 4211/4412 | Verdacht | offen (mittel) | Titel umfasst Poststelle (42111) und Zustellung (4412) |
| Drogist/in 3256 | fraglich | 5223 (hoch) | SE führt Drogisten ausdrücklich als Berufsart 52231 |
| Hotelfachmann/-frau EFZ 5131 | fraglich | 5151 (hoch, Ermessensentscheid) | Bildungsplan mit Schwerpunkt Hauswirtschaft; als einziger der Fälle nicht durch ESCO gestützt (ESCO-Match fehlerhaft) |
| Polizist/in 3355 (doppelt mit Polizisten 5412) | fraglich | 5412, zusammengelegt | 3355 = Kommissare/Kriminalbeamte |
| Versicherungsexperte/-expertin, Maschinenführer/in, Data Scientist, Mechatroniker/in EFZ | fraglich | offen (mittel) | siehe Tabelle oben |
| Doppel Gymnasiallehrer/in / Sekundarlehrer/in | zusammenlegen? | getrennt (Option B) | SE-Berufsarten 23301/23302 erlauben saubere Trennung |
| Doppel Projektleiter/in (allg.) / (Technik) | zusammenlegen? | unverändert | verschiedene Codes (2421 / 2149), kein Doppel in der SE; beide offen (Vorschlag 30001) |
| Doppel Köche / Koch EFZ, Kassierer / Kassierer/in, Polizisten / Polizist/in | zusammenlegen? | zusammengelegt | nur eine Berufsart je Gattung |

## Berufe mit geändertem ISCO-Code — ESCO-Match neu prüfen

ESCO-Zuordnung und -Beschreibung wurden nicht verändert (separates Audit). Neu zu prüfen:

- Koch/Köchin EFZ (3434 → 5120) — jetzt Teil von «Köche»
- Chemielaborant/in EFZ (3113 → 3111) — jetzt Teil von «Chemo- und Physikotechniker»
- Drogist/in (3256 → 5223)
- Hauswirtschaftler/in EFZ (5131 → 5151) — jetzt Teil von «Reinigungs- und Hauswirtschaftleiter und -kräfte in Büros, Hotels und anderen Einrichtungen»
- Hotelfachmann/-frau EFZ (5131 → 5151) — jetzt Teil von «Reinigungs- und Hauswirtschaftleiter und -kräfte in Büros, Hotels und anderen Einrichtungen»
- Buchhalter/in (2411 → 3313) — jetzt Teil von «Fachkräfte im Rechnungswesen»
- Treuhänder/in (2412 → 2411) — jetzt Teil von «Wirtschaftsprüfer, Steuerberater und verwandte Berufe»
- Steuerberater/in (2412 → 2411) — jetzt Teil von «Wirtschaftsprüfer, Steuerberater und verwandte Berufe»
- Vermögensverwalter/in / Wealth Manager (2413 → 2412) — jetzt Teil von «Finanz- und Anlageberater»
- Bankkaufmann/-frau (3311 → 4211) — jetzt Teil von «Schalterbedienstete und Fachkräfte im Bereich Finanzdienstleistungen»
- Logistiker/in EFZ (3331 → 4321) — jetzt Teil von «Fachkräfte in der Lagerwirtschaft»
- Polizist/in (3355 → 5412) — jetzt Teil von «Polizisten (ohne Polizeikommissare)»
- Bauführer/in (3123 → 3112)
- Hochbauzeichner/in EFZ (3112 → 3118) — jetzt Teil von «Technische Zeichner»
- Polymechaniker/in EFZ (7223 → 7200)
- Automatiker/in EFZ (3115 → 7412) — jetzt Teil von «Automatiker und verwandte Berufe»
- Landwirt/in EFZ (6111 → 6130) — jetzt Teil von «Landwirte mit Ackerbau und Tierhaltung (ohne ausgeprägten Schwerpunkt)»
- Journalist/in / Redakteur/in (2641 → 2642) — jetzt Teil von «Journalisten»
- Kassierer/in (5223 → 5230) — jetzt Teil von «Kassierer und Kartenverkäufer»
- Sachbearbeiter/in öff. Verwaltung (4416 → 4110) — jetzt Teil von «Allgemeine Bürokräfte»
- Produktionsmitarbeiter/in (Pharma) (8211 → 8131) — jetzt Teil von «Bediener von Anlagen und Maschinen für chemische Erzeugnisse»

## Neu aufgenommene Berufsgattungen (Nachtrag)

Nach den Korrekturen oben fehlten SE-Gattungen ganz, deren bisheriger (falscher) Beruf in eine
andere Gattung verschoben wurde (z. B. 3123 Poliere: Bauführer/in → 3112). Aufgenommen wurden
alle 4-stelligen SE-Berufsgattungen mit **≥ 5'000 Erwerbstätigen im Blatt 2024**, die noch keinen
Eintrag hatten (`python src/data/update_from_bfs.py --neue-berufe`). Titel = SE-Bezeichnung,
ebene «gattung» (voller SE-Wert), Branche über `branche_fuer_isco()`, Lohn = LSE 2024 der
2-stelligen Gruppe × 12 (keine der neuen Gattungen liegt in den Salarium-Gruppen 11–14/22/24/26),
Qualifikation über die ISCO-Hauptgruppe. ESCO-Zuordnung siehe `docs/audit_esco_zuordnungen.md`.

| Code | Beruf (SE-Bezeichnung) | Tsd. | Frauen % | Branche | Lohn CHF/Jahr | ESCO-Beruf (ESCO-ISCO) | Match |
|---|---|---|---|---|---|---|---|
| 3115 | Maschinenbautechniker, Techniker im Bereich Systemtechnik, Automation und Unternehmensprozesse | 12.0 | 8.8 | Industrie | 90'084 | Maschinenbautechniker/in (3115) | korrekt |
| 3123 | Poliere und Vorarbeiter | 28.8 | 3.2 | Bau | 90'084 | Maurerpolier/in (3123) | plausibel |
| 3311 | Wertpapierhändler, -makler und Finanzmakler | 8.5 | 24.7 | Finanzen | 94'800 | Trader/in am Finanzmarkt (3311) | korrekt |
| 3355 | Polizeikommissare und Kriminalbeamte | 8.5 | 19.9 | Öff. Verwaltung | 94'800 | Kriminalbeamter/-beamtin (3355) | korrekt |
| 3434 | Küchenchefs, stv. Küchenchefs und Souschefs | 9.6 | 15.4 | Gastgewerbe | 84'936 | Chefkoch/Chefköchin (3434) | korrekt |
| 4419 | Bürokräfte und verwandte Berufe, anderweitig nicht genannt | 42.0 | 57.2 | Verwaltung | 76'272 | Verkaufssachbearbeiter/in (4311) | plausibel |
| 7223 | Werkzeugmaschineneinrichter und -bediener | 8.6 | 10.9 | Industrie | 76'728 | CNC-Anwendungsfachkraft (7223) | korrekt |
| 9329 | Hilfsarbeiter bei der Herstellung von Waren, anderweitig nicht genannt | 38.9 | 48.6 | Industrie | 66'492 | Fabrikhilfsarbeiter/in (9329) | korrekt |
| | **Total** | **156.9** | | | | | |

**Abdeckung** (Σ `beschaeftigte_1000` in `scores.csv` / SE 2024 total 4'583.7 Tsd.):

| | Berufe | Tsd. | Abdeckung |
|---|---|---|---|
| vorher | 179 | 3'566.9 | 77.8 % |
| nachher | 187 | 3'723.8 | 81.2 % |
| davon bewertet | 179 | 3'566.9 | 77.8 % |

**Restgruppen-Regel:** Gattungen mit «onA» (ohne nähere Angaben), «anderweitig nicht genannt» oder
«ohne nähere Angabe» in der Bezeichnung werden nicht aufgenommen — sie bündeln heterogene oder
nicht zuordenbare Angaben. Ausnahme (`RESTGRUPPEN_AUSNAHMEN` in `update_from_bfs.py`), wenn die
Gruppe gross **und** inhaltlich klar ist und kein bestehender Eintrag die Tätigkeit abdeckt:

- **4419 Bürokräfte a.n.g. (42.0 Tsd.):** 84 % Berufsart 44192 «Bürokräfte und verwandte Berufe,
  Verkauf» (Verkaufsinnendienst, 35.4 Tsd.), dazu 44191 Marketing und Werbung (4.1) und onA (2.5).
  3322 Verkaufsfachkräfte (Aussendienst) ist ein eigener Eintrag.
- **9329 Hilfsarbeiter Herstellung von Waren a.n.g. (38.9 Tsd.):** einzige Berufsart 93290; die
  ISCO-Untergruppe 932 hat sonst nur 9321 Verpackung — 9329 ist faktisch die Gattung der
  Produktionshelfer/innen.

Nicht aufgenommen (Restgruppen ≥ 5'000, zusammen 376.1 Tsd.):

| Code | Bezeichnung | Tsd. | Grund |
|---|---|---|---|
| 3000 | Techniker und gleichrangige nichttechnische Berufe, onA | 64.5 | 68 % Projektleiter onA, 30 % Gruppenleiter onA — Funktion ohne Fachgebiet; hängt am offenen Fall Projektleiter/in (allg./Technik) |
| 4320 | Bürokräfte Materialwirtschaft und Transport, onA | 41.0 | Rest der Untergruppe 432; 4321/4322/4323 sind eigene Einträge |
| 2000 | Intellektuelle und wissenschaftliche Berufe, onA | 39.8 | ohne Fachgebiet |
| 1000 | Führungskräfte, onA | 24.6 | ohne Bereich |
| 8100 | Bediener stationärer Anlagen und Maschinen, onA | 22.6 | hängt am offenen Fall Maschinenführer/in (8211 → 8100?) |
| 1210 | Führungskräfte betriebliche Administration, onA | 21.8 | Rest der Untergruppe 121 (1211–1213 eigene Einträge) |
| 3119 | Material- und ingenieurtechnische Fachkräfte a.n.g. | 18.9 | heterogen (verschiedene Fachgebiete) |
| 2269 | Spezialisten in Gesundheitsberufen a.n.g. | 16.2 | 71 % onA; Ergotherapeuten (22691) nur 4.7 Tsd. |
| 9000 | Hilfsarbeitskräfte, onA | 14.5 | ohne Bereich |
| 2500 | Spezialisten ICT, onA | 14.0 | ohne Fachgebiet |
| 1219 | Führungskräfte betriebliche Administration a.n.g. | 13.2 | heterogen |
| 2210 | Ärzte, onA | 11.2 | Ärzte ohne Fachrichtung; überschneidet sich mit 2211/2212 (eigener Eintrag wäre ein Duplikat) |
| 2140 | Ingenieurwissenschaftler, onA | 10.9 | ohne Fachgebiet |
| 3100 | Ingenieurtechnische Fachkräfte, onA | 10.6 | ohne Fachgebiet |
| 1349 | Führungskräfte spezialisierte Dienstleistungen a.n.g. | 8.6 | heterogen |
| 2300 | Lehrkräfte, onA | 8.1 | ohne Stufe; überschneidet sich mit den Lehrkräfte-Einträgen |
| 8300 | Fahrzeugführer und Bediener mobiler Anlagen, onA | 6.7 | ohne Fahrzeugart |
| 2510 | Entwickler und Analytiker Software, onA | 6.6 | 99 % Informatikingenieure (Ausbildungs-, keine Tätigkeitsangabe); überschneidet sich mit 2511/2512 |
| 8210 | Montageberufe, onA | 5.8 | ohne Produkt |
| 7549 | Handwerks- und verwandte Berufe a.n.g. | 5.7 | heterogen |
| 2610 | Juristen, onA | 5.7 | überschneidet sich mit 2611/2619 |
| 7119 | Baukonstruktions- und verwandte Berufe a.n.g. | 5.3 | heterogen |

**Bewertung:** Die neuen Einträge haben noch keine Exposure-Bewertung (`score_*`, `haupt_risiko`,
`zeitrahmen`, `begruendung`, `adaptabilitaet`, `score_ch` leer; `beschreibung_hash` leer →
`exposure_scorer.py` bewertet sie beim nächsten Lauf). Regelbasierte Spalten (`delta_branche`,
`lohnklasse`, `delta_lohn`) sind gesetzt. Die App führt sie in der Berufssuche als «noch nicht
bewertet» und blendet sie in Treemap, Matrix, Branchenanalyse und den Kennzahlen der Startseite
aus (mit Hinweis auf Anzahl und Beschäftigte).

## Vollständige Audit-Tabelle (alle 204 bisherigen Einträge)

Status: korrekt = Code passt zur Bezeichnung; korrigiert; offen = mittlere Sicherheit; Hinweis =
Titel enger als Gattung. Automatisch ergänzte Einträge tragen die SE-Bezeichnung ihres Codes.

| Beruf | alter Code | SE-Bezeichnung alt | neuer Code | SE-Bezeichnung neu | Status | Sicherheit | jetzt Eintrag |
|---|---|---|---|---|---|---|---|
| Leitende Verwaltungsbedienstete | 1112 | Leitende Verwaltungsbedienstete | 1112 | Leitende Verwaltungsbedienstete | korrekt (SE-Bezeichnung) | hoch | Leitende Verwaltungsbedienstete |
| Geschäftsführer/in (KMU) | 1120 | Geschäftsführer und Vorstände | 1120 | Geschäftsführer und Vorstände | korrekt, Hinweis | hoch | Geschäftsführer/in (KMU) |
| Führungskräfte im Bereich Finanzen | 1211 | Führungskräfte im Bereich Finanzen | 1211 | Führungskräfte im Bereich Finanzen | korrekt (SE-Bezeichnung) | hoch | Führungskräfte im Bereich Finanzen |
| HR-Manager/in | 1212 | Führungskräfte im Personalwesen | 1212 | Führungskräfte im Personalwesen | korrekt | hoch | HR-Manager/in |
| Führungskräfte in Unternehmenspolitik und -planung | 1213 | Führungskräfte in Unternehmenspolitik und -planung | 1213 | Führungskräfte in Unternehmenspolitik und -planung | korrekt (SE-Bezeichnung) | hoch | Führungskräfte in Unternehmenspolitik und -planung |
| Führungskräfte in Vertrieb und Marketing | 1221 | Führungskräfte in Vertrieb und Marketing | 1221 | Führungskräfte in Vertrieb und Marketing | korrekt (SE-Bezeichnung) | hoch | Führungskräfte in Vertrieb und Marketing |
| Marketing-/Kommunikationsleiter/in | 1222 | Führungskräfte in Werbung und Öffentlichkeitsarbeit | 1222 | Führungskräfte in Werbung und Öffentlichkeitsarbeit | offen (Vorschlag 1221 (12212)) | mittel | Marketing-/Kommunikationsleiter/in |
| Führungskräfte in Forschung und Entwicklung | 1223 | Führungskräfte in Forschung und Entwicklung | 1223 | Führungskräfte in Forschung und Entwicklung | korrekt (SE-Bezeichnung) | hoch | Führungskräfte in Forschung und Entwicklung |
| Führungskräfte in der Produktion von Waren | 1321 | Führungskräfte in der Produktion von Waren | 1321 | Führungskräfte in der Produktion von Waren | korrekt (SE-Bezeichnung) | hoch | Führungskräfte in der Produktion von Waren |
| Führungskräfte in der Produktion im Bau | 1323 | Führungskräfte in der Produktion im Bau | 1323 | Führungskräfte in der Produktion im Bau | korrekt (SE-Bezeichnung) | hoch | Führungskräfte in der Produktion im Bau |
| Führungskräfte in der Beschaffung, Logistik und in verwandten Bereichen | 1324 | Führungskräfte in der Beschaffung, Logistik und in verwandten Bereichen | 1324 | Führungskräfte in der Beschaffung, Logistik und in verwandten Bereichen | korrekt (SE-Bezeichnung) | hoch | Führungskräfte in der Beschaffung, Logistik und in verwandten Bereichen |
| Führungskräfte in der Erbringung von Dienstleistungen im Bereich Informations- und Kommunikationstechnologie | 1330 | Führungskräfte in der Erbringung von Dienstleistungen im Bereich Informations- und Kommunikationstechnologie | 1330 | Führungskräfte in der Erbringung von Dienstleistungen im Bereich Informations- und Kommunikationstechnologie | korrekt (SE-Bezeichnung) | hoch | Führungskräfte in der Erbringung von Dienstleistungen im Bereich Informations- und Kommunikationstechnologie |
| Führungskräfte in der Erbringung von Dienstleistungen des Bildungswesens | 1345 | Führungskräfte in der Erbringung von Dienstleistungen des Bildungswesens | 1345 | Führungskräfte in der Erbringung von Dienstleistungen des Bildungswesens | korrekt (SE-Bezeichnung) | hoch | Führungskräfte in der Erbringung von Dienstleistungen des Bildungswesens |
| Führungskräfte in der Erbringung von Finanz- und Versicherungsdienstleistungen | 1346 | Führungskräfte in der Erbringung von Finanz- und Versicherungsdienstleistungen | 1346 | Führungskräfte in der Erbringung von Finanz- und Versicherungsdienstleistungen | korrekt (SE-Bezeichnung) | hoch | Führungskräfte in der Erbringung von Finanz- und Versicherungsdienstleistungen |
| Führungskräfte in Hotels | 1411 | Führungskräfte in Hotels | 1411 | Führungskräfte in Hotels | korrekt (SE-Bezeichnung) | hoch | Führungskräfte in Hotels |
| Führungskräfte in Restaurants | 1412 | Führungskräfte in Restaurants | 1412 | Führungskräfte in Restaurants | korrekt (SE-Bezeichnung) | hoch | Führungskräfte in Restaurants |
| Filialleiter/in (Detailhandel) | 1420 | Führungskräfte in Gross- und Einzelhandel | 1420 | Führungskräfte in Gross- und Einzelhandel | offen (Vorschlag 5221) | mittel | Filialleiter/in (Detailhandel) |
| Naturwissenschaftler/in (Biologie/Chemie) | 2113 | Chemiker | 2113 | Chemiker | korrekt, Hinweis | hoch | Naturwissenschaftler/in (Biologie/Chemie) |
| Statistiker/in / Aktuar/in | 2120 | Mathematiker, Aktuare und Statistiker | 2120 | Mathematiker, Aktuare und Statistiker | korrekt | hoch | Statistiker/in / Aktuar/in |
| Biologen, Botaniker, Zoologen und verwandte Berufe | 2131 | Biologen, Botaniker, Zoologen und verwandte Berufe | 2131 | Biologen, Botaniker, Zoologen und verwandte Berufe | korrekt (SE-Bezeichnung) | hoch | Biologen, Botaniker, Zoologen und verwandte Berufe |
| Prozess- und Produktionsingenieure | 2141 | Prozess- und Produktionsingenieure | 2141 | Prozess- und Produktionsingenieure | korrekt (SE-Bezeichnung) | hoch | Prozess- und Produktionsingenieure |
| Bauingenieur/in | 2142 | Bauingenieure | 2142 | Bauingenieure | korrekt | hoch | Bauingenieur/in |
| Umweltingenieur/in | 2143 | Umweltschutzingenieure | 2143 | Umweltschutzingenieure | korrekt | hoch | Umweltingenieur/in |
| Maschinenbauingenieur/in | 2144 | Maschinenbau- , Mechatronik- und Systemtechnikingenieure | 2144 | Maschinenbau- , Mechatronik- und Systemtechnikingenieure | korrekt | hoch | Maschinenbauingenieur/in |
| Chemieingenieur/in / Verfahrenstechniker/in | 2145 | Chemieingenieure | 2145 | Chemieingenieure | korrekt | hoch | Chemieingenieur/in / Verfahrenstechniker/in |
| Qualitätsmanager/in | 2146 | Bergbauingenieure, Metallurgen und verwandte Berufe | 2146 | Bergbauingenieure, Metallurgen und verwandte Berufe | offen (Vorschlag 2141 oder 1321) | mittel | Qualitätsmanager/in |
| Projektleiter/in (Technik) | 2149 | Ingenieure, anderweitig nicht genannt | 2149 | Ingenieure, anderweitig nicht genannt | offen (Vorschlag 3000 (30001)) | mittel | Projektleiter/in (Technik) |
| Elektroingenieur/in | 2151 | Ingenieure im Bereich Elektrotechnik | 2151 | Ingenieure im Bereich Elektrotechnik | korrekt | hoch | Elektroingenieur/in |
| Architekt/in | 2161 | Architekten | 2161 | Architekten | korrekt | hoch | Architekt/in |
| Produkt- und Textildesigner | 2163 | Produkt- und Textildesigner | 2163 | Produkt- und Textildesigner | korrekt (SE-Bezeichnung) | hoch | Produkt- und Textildesigner |
| Grafiker/in | 2166 | Grafik- und Multimediadesigner | 2166 | Grafik- und Multimediadesigner | korrekt | hoch | Grafik- und Multimediadesigner |
| UX/UI Designer/in | 2166 | Grafik- und Multimediadesigner | 2166 | Grafik- und Multimediadesigner | korrekt | hoch | Grafik- und Multimediadesigner |
| Arzt/Ärztin (Allgemeinmedizin) | 2211 | Allgemeinärzte | 2211 | Allgemeinärzte | korrekt | hoch | Arzt/Ärztin (Allgemeinmedizin) |
| Fachärzte | 2212 | Fachärzte | 2212 | Fachärzte | korrekt (SE-Bezeichnung) | hoch | Fachärzte |
| Dipl. Pflegefachperson | 2221 | Pflegedienstleiter und Pflegefachkräfte | 2221 | Pflegedienstleiter und Pflegefachkräfte | korrekt | hoch | Dipl. Pflegefachperson |
| Spezialisten der traditionellen und komplementären Medizin | 2230 | Spezialisten der traditionellen und komplementären Medizin | 2230 | Spezialisten der traditionellen und komplementären Medizin | korrekt (SE-Bezeichnung) | hoch | Spezialisten der traditionellen und komplementären Medizin |
| Zahnarzt/-ärztin | 2261 | Zahnärzte | 2261 | Zahnärzte | korrekt | hoch | Zahnarzt/-ärztin |
| Apotheker/in | 2262 | Apotheker | 2262 | Apotheker | korrekt | hoch | Apotheker/in |
| Physiotherapeut/in | 2264 | Physiotherapeuten | 2264 | Physiotherapeuten | korrekt | hoch | Physiotherapeut/in |
| Hochschuldozent/in | 2310 | Universitäts- und Hochschullehrer | 2310 | Universitäts- und Hochschullehrer | korrekt | hoch | Hochschuldozent/in |
| Berufsschullehrer/in | 2320 | Lehrkräfte im Bereich Berufsbildung | 2320 | Lehrkräfte im Bereich Berufsbildung | korrekt | hoch | Berufsschullehrer/in |
| Gymnasiallehrer/in | 2330 | Lehrkräfte im Sekundarbereich | 2330 | Lehrkräfte im Sekundarbereich | korrekt | hoch | Gymnasiallehrer/in |
| Sekundarlehrer/in | 2330 | Lehrkräfte im Sekundarbereich | 2330 | Lehrkräfte im Sekundarbereich | korrekt | hoch | Sekundarlehrer/in |
| Primarlehrer/in | 2341 | Lehrkräfte im Primarbereich | 2341 | Lehrkräfte im Primarbereich | korrekt | hoch | Primarlehrer/in |
| Kindergärtnerin/-gärtner | 2342 | Lehrkräfte und Erzieher im Vorschulbereich | 2342 | Lehrkräfte und Erzieher im Vorschulbereich | korrekt, Hinweis | hoch | Kindergärtnerin/-gärtner |
| Pädagogik- und Didaktikspezialisten | 2351 | Pädagogik- und Didaktikspezialisten | 2351 | Pädagogik- und Didaktikspezialisten | korrekt (SE-Bezeichnung) | hoch | Pädagogik- und Didaktikspezialisten |
| Lehrkräfte im Bereich Sonderpädagogik | 2352 | Lehrkräfte im Bereich Sonderpädagogik | 2352 | Lehrkräfte im Bereich Sonderpädagogik | korrekt (SE-Bezeichnung) | hoch | Lehrkräfte im Bereich Sonderpädagogik |
| Sprachlehrer | 2353 | Sprachlehrer | 2353 | Sprachlehrer | korrekt (SE-Bezeichnung) | hoch | Sprachlehrer |
| Musiklehrer | 2354 | Musiklehrer | 2354 | Musiklehrer | korrekt (SE-Bezeichnung) | hoch | Musiklehrer |
| Buchhalter/in | 2411 | Wirtschaftsprüfer, Steuerberater und verwandte Berufe | 3313 | Fachkräfte im Rechnungswesen | korrigiert | hoch | Fachkräfte im Rechnungswesen |
| Controller/in | 2411 | Wirtschaftsprüfer, Steuerberater und verwandte Berufe | 2411 | Wirtschaftsprüfer, Steuerberater und verwandte Berufe | korrekt | hoch | Wirtschaftsprüfer, Steuerberater und verwandte Berufe |
| Wirtschaftsprüfer/in | 2411 | Wirtschaftsprüfer, Steuerberater und verwandte Berufe | 2411 | Wirtschaftsprüfer, Steuerberater und verwandte Berufe | korrekt | hoch | Wirtschaftsprüfer, Steuerberater und verwandte Berufe |
| Compliance Officer | 2412 | Finanz- und Anlageberater | 2412 | Finanz- und Anlageberater | offen (Vorschlag 2619 / 2411 / 3359) | mittel | Finanz- und Anlageberater |
| Steuerberater/in | 2412 | Finanz- und Anlageberater | 2411 | Wirtschaftsprüfer, Steuerberater und verwandte Berufe | korrigiert | hoch | Wirtschaftsprüfer, Steuerberater und verwandte Berufe |
| Treuhänder/in | 2412 | Finanz- und Anlageberater | 2411 | Wirtschaftsprüfer, Steuerberater und verwandte Berufe | korrigiert | hoch | Wirtschaftsprüfer, Steuerberater und verwandte Berufe |
| Finanzanalyst/in | 2413 | Finanzanalysten | 2413 | Finanzanalysten | korrekt | hoch | Finanzanalyst/in |
| Vermögensverwalter/in / Wealth Manager | 2413 | Finanzanalysten | 2412 | Finanz- und Anlageberater | korrigiert | hoch | Finanz- und Anlageberater |
| Projektleiter/in (allg.) | 2421 | Spezialisten im Bereich Management- und Organisationsanalyse | 2421 | Spezialisten im Bereich Management- und Organisationsanalyse | offen (Vorschlag 3000 (30001)) | mittel | Spezialisten im Bereich Management- und Organisationsanalyse |
| Unternehmensberater/in | 2421 | Spezialisten im Bereich Management- und Organisationsanalyse | 2421 | Spezialisten im Bereich Management- und Organisationsanalyse | korrekt | hoch | Spezialisten im Bereich Management- und Organisationsanalyse |
| Versicherungsexperte/-expertin | 2422 | Spezialisten in der strategischen Planung in Politik und Wirtschaft | 2422 | Spezialisten in der strategischen Planung in Politik und Wirtschaft | offen (Vorschlag 3321 oder 2120) | mittel | Versicherungsexperte/-expertin |
| Berufsberater und -analytiker und vergleichbare Spezialisten der Personalwesen | 2423 | Berufsberater und -analytiker und vergleichbare Spezialisten der Personalwesen | 2423 | Berufsberater und -analytiker und vergleichbare Spezialisten der Personalwesen | korrekt (SE-Bezeichnung) | hoch | Berufsberater und -analytiker und vergleichbare Spezialisten der Personalwesen |
| Fachkräfte in Personalschulung und -entwicklung | 2424 | Fachkräfte in Personalschulung und -entwicklung | 2424 | Fachkräfte in Personalschulung und -entwicklung | korrekt (SE-Bezeichnung) | hoch | Fachkräfte in Personalschulung und -entwicklung |
| Fachkräfte in Marketing und Werbung | 2431 | Fachkräfte in Marketing und Werbung | 2431 | Fachkräfte in Marketing und Werbung | korrekt (SE-Bezeichnung) | hoch | Fachkräfte in Marketing und Werbung |
| PR-Spezialist/in | 2432 | Fachkräfte in der Öffentlichkeitsarbeit | 2432 | Fachkräfte in der Öffentlichkeitsarbeit | korrekt | hoch | PR-Spezialist/in |
| Technische Verkaufsfachkräfte (ohne Informations- und Kommunikationstechnologie) | 2433 | Technische Verkaufsfachkräfte (ohne Informations- und Kommunikationstechnologie) | 2433 | Technische Verkaufsfachkräfte (ohne Informations- und Kommunikationstechnologie) | korrekt (SE-Bezeichnung) | hoch | Technische Verkaufsfachkräfte (ohne Informations- und Kommunikationstechnologie) |
| IT-Projektleiter/in | 2511 | Systemanalytiker | 2511 | Systemanalytiker | offen (Vorschlag 2512 (25124)) | mittel | IT-Projektleiter/in |
| Informatiker/in EFZ (Applikationsentwicklung) | 2512 | Softwareentwickler | 2512 | Softwareentwickler | korrekt | hoch | Softwareentwickler |
| Softwareentwickler/in | 2512 | Softwareentwickler | 2512 | Softwareentwickler | korrekt | hoch | Softwareentwickler |
| Datenwissenschaftler/in / Data Scientist | 2514 | Anwendungsprogrammierer | 2514 | Anwendungsprogrammierer | offen (Vorschlag 2529 (25291) oder 2120) | mittel | Datenwissenschaftler/in / Data Scientist |
| Datenbankentwickler und -administratoren | 2521 | Datenbankentwickler und -administratoren | 2521 | Datenbankentwickler und -administratoren | korrekt (SE-Bezeichnung) | hoch | Datenbankentwickler und -administratoren |
| Systemadministrator/in | 2522 | Systemadministratoren | 2522 | Systemadministratoren | korrekt | hoch | Systemadministrator/in |
| Netzwerkingenieur/in | 2523 | Fachkräfte für Computernetzwerke | 2523 | Fachkräfte für Computernetzwerke | korrekt | hoch | Netzwerkingenieur/in |
| IT-Sicherheitsspezialist/in | 2529 | Fachkräfte für Datenbanken und Netzwerke, anderweitig nicht genannt. | 2529 | Fachkräfte für Datenbanken und Netzwerke, anderweitig nicht genannt. | korrekt | hoch | IT-Sicherheitsspezialist/in |
| Rechtsanwalt/-anwältin | 2611 | Anwälte | 2611 | Anwälte | korrekt | hoch | Rechtsanwalt/-anwältin |
| Notar/in | 2619 | Juristen, anderweitig nicht genannt | 2619 | Juristen, anderweitig nicht genannt | korrekt, Hinweis | hoch | Notar/in |
| Ökonom/in / Volkswirt/in | 2631 | Volkswirtschaftler | 2631 | Volkswirtschaftler | korrekt | hoch | Ökonom/in / Volkswirt/in |
| Psychologe/-pädagogin | 2634 | Psychologen | 2634 | Psychologen | korrekt | hoch | Psychologe/-pädagogin |
| Sozialarbeiter/in | 2635 | Sozialarbeiter | 2635 | Sozialarbeiter | korrekt | hoch | Sozialarbeiter |
| Sozialpädagoge/-pädagogin | 2635 | Sozialarbeiter | 2635 | Sozialarbeiter | offen (Vorschlag 3412) | mittel | Sozialarbeiter |
| Geistliche Seelsorger | 2636 | Geistliche Seelsorger | 2636 | Geistliche Seelsorger | korrekt (SE-Bezeichnung) | hoch | Geistliche Seelsorger |
| Journalist/in / Redakteur/in | 2641 | Autoren und verwandte schriftstellerische Berufe | 2642 | Journalisten | korrigiert | hoch | Journalisten |
| Journalisten | 2642 | Journalisten | 2642 | Journalisten | korrekt (SE-Bezeichnung) | hoch | Journalisten |
| Übersetzer, Dolmetscher und andere Linguisten | 2643 | Übersetzer, Dolmetscher und andere Linguisten | 2643 | Übersetzer, Dolmetscher und andere Linguisten | korrekt (SE-Bezeichnung) | hoch | Übersetzer, Dolmetscher und andere Linguisten |
| Musiker, Sänger und Komponisten | 2652 | Musiker, Sänger und Komponisten | 2652 | Musiker, Sänger und Komponisten | korrekt (SE-Bezeichnung) | hoch | Musiker, Sänger und Komponisten |
| Regisseure und Produzenten im Film- und Bühnenbereich sowie in verwandten Bereichen | 2654 | Regisseure und Produzenten im Film- und Bühnenbereich sowie in verwandten Bereichen | 2654 | Regisseure und Produzenten im Film- und Bühnenbereich sowie in verwandten Bereichen | korrekt (SE-Bezeichnung) | hoch | Regisseure und Produzenten im Film- und Bühnenbereich sowie in verwandten Bereichen |
| Chemo- und Physikotechniker | 3111 | Chemo- und Physikotechniker | 3111 | Chemo- und Physikotechniker | korrekt (SE-Bezeichnung) | hoch | Chemo- und Physikotechniker |
| Hochbauzeichner/in EFZ | 3112 | Bauführer und Bautechniker | 3118 | Technische Zeichner | korrigiert | hoch | Technische Zeichner |
| Chemielaborant/in EFZ | 3113 | Elektrotechniker | 3111 | Chemo- und Physikotechniker | korrigiert | hoch | Chemo- und Physikotechniker |
| Elektroplaner/in EFZ | 3113 | Elektrotechniker | 3113 | Elektrotechniker | korrekt | hoch | Elektroplaner/in EFZ |
| Automatiker/in EFZ | 3115 | Maschinenbautechniker, Techniker im Bereich Systemtechnik, Automation und Unternehmensprozesse | 7412 | Automatiker und verwandte Berufe | korrigiert | hoch | Automatiker und verwandte Berufe |
| Technische Zeichner | 3118 | Technische Zeichner | 3118 | Technische Zeichner | korrekt (SE-Bezeichnung) | hoch | Technische Zeichner |
| Produktionsleiter bei der Herstellung von Waren | 3122 | Produktionsleiter bei der Herstellung von Waren | 3122 | Produktionsleiter bei der Herstellung von Waren | korrekt (SE-Bezeichnung) | hoch | Produktionsleiter bei der Herstellung von Waren |
| Bauführer/in | 3123 | Poliere und Vorarbeiter | 3112 | Bauführer und Bautechniker | korrigiert | hoch | Bauführer/in |
| Medizintechniker im Bereich bildgebende Verfahren und Therapiegeräte | 3211 | Medizintechniker im Bereich bildgebende Verfahren und Therapiegeräte | 3211 | Medizintechniker im Bereich bildgebende Verfahren und Therapiegeräte | korrekt (SE-Bezeichnung) | hoch | Medizintechniker im Bereich bildgebende Verfahren und Therapiegeräte |
| Medizintechniker im Bereich Labor und Pathologie | 3212 | Medizintechniker im Bereich Labor und Pathologie | 3212 | Medizintechniker im Bereich Labor und Pathologie | korrekt (SE-Bezeichnung) | hoch | Medizintechniker im Bereich Labor und Pathologie |
| Pharmazeutische Techniker und Assistenten | 3213 | Pharmazeutische Techniker und Assistenten | 3213 | Pharmazeutische Techniker und Assistenten | korrekt (SE-Bezeichnung) | hoch | Pharmazeutische Techniker und Assistenten |
| Fachperson Gesundheit EFZ (FaGe) | 3221 | Fachkräfte Gesundheit und Pflege (mittlere Stufe) | 3221 | Fachkräfte Gesundheit und Pflege (mittlere Stufe) | korrekt | hoch | Fachperson Gesundheit EFZ (FaGe) |
| Zahnmedizinische Assistenten und Dentalhygieniker | 3251 | Zahnmedizinische Assistenten und Dentalhygieniker | 3251 | Zahnmedizinische Assistenten und Dentalhygieniker | korrekt (SE-Bezeichnung) | hoch | Zahnmedizinische Assistenten und Dentalhygieniker |
| Physiotherapeutische Techniker und Assistenten | 3255 | Physiotherapeutische Techniker und Assistenten | 3255 | Physiotherapeutische Techniker und Assistenten | korrekt (SE-Bezeichnung) | hoch | Physiotherapeutische Techniker und Assistenten |
| Arztpraxisassistent/in | 3256 | Medizinische Assistenten | 3256 | Medizinische Assistenten | korrekt | hoch | Arztpraxisassistent/in |
| Drogist/in | 3256 | Medizinische Assistenten | 5223 | Verkäufer in Handelsgeschäften | korrigiert | hoch | Drogist/in |
| Bankkaufmann/-frau | 3311 | Wertpapierhändler, -makler und Finanzmakler | 4211 | Schalterbedienstete und Fachkräfte im Bereich Finanzdienstleistungen | korrigiert | hoch | Schalterbedienstete und Fachkräfte im Bereich Finanzdienstleistungen |
| Versicherungskaufmann/-frau | 3312 | Fachkräfte im Bereich Kredit und Darlehen | 3312 | Fachkräfte im Bereich Kredit und Darlehen | offen (Vorschlag 4312 oder 3321) | mittel | Versicherungskaufmann/-frau |
| Fachkräfte im Rechnungswesen | 3313 | Fachkräfte im Rechnungswesen | 3313 | Fachkräfte im Rechnungswesen | korrekt (SE-Bezeichnung) | hoch | Fachkräfte im Rechnungswesen |
| Versicherungsvertreter | 3321 | Versicherungsvertreter | 3321 | Versicherungsvertreter | korrekt (SE-Bezeichnung) | hoch | Versicherungsvertreter |
| Verkaufsfachkräfte | 3322 | Verkaufsfachkräfte | 3322 | Verkaufsfachkräfte | korrekt (SE-Bezeichnung) | hoch | Verkaufsfachkräfte |
| Einkäufer | 3323 | Einkäufer | 3323 | Einkäufer | korrekt (SE-Bezeichnung) | hoch | Einkäufer |
| Handelsmakler | 3324 | Handelsmakler | 3324 | Handelsmakler | korrekt (SE-Bezeichnung) | hoch | Handelsmakler |
| Logistiker/in EFZ | 3331 | Fachkräfte für Abrechnungs- und Speditionsdienstleistungen | 4321 | Fachkräfte in der Lagerwirtschaft | korrigiert | hoch | Fachkräfte in der Lagerwirtschaft |
| Konferenz- und Veranstaltungsplaner | 3332 | Konferenz- und Veranstaltungsplaner | 3332 | Konferenz- und Veranstaltungsplaner | korrekt (SE-Bezeichnung) | hoch | Konferenz- und Veranstaltungsplaner |
| Immobilienbewirtschafter/in | 3334 | Immobilienmakler und -verwalter | 3334 | Immobilienmakler und -verwalter | korrekt | hoch | Immobilienmakler und -verwalter |
| Immobilienmakler/in | 3334 | Immobilienmakler und -verwalter | 3334 | Immobilienmakler und -verwalter | korrekt | hoch | Immobilienmakler und -verwalter |
| Sekretariatsleiter | 3341 | Sekretariatsleiter | 3341 | Sekretariatsleiter | korrekt (SE-Bezeichnung) | hoch | Sekretariatsleiter |
| Sekretariatsfachkräfte in Verwaltung und Geschäftsleitung | 3343 | Sekretariatsfachkräfte in Verwaltung und Geschäftsleitung | 3343 | Sekretariatsfachkräfte in Verwaltung und Geschäftsleitung | korrekt (SE-Bezeichnung) | hoch | Sekretariatsfachkräfte in Verwaltung und Geschäftsleitung |
| Sekretariatsfachkräfte im Gesundheitswesen | 3344 | Sekretariatsfachkräfte im Gesundheitswesen | 3344 | Sekretariatsfachkräfte im Gesundheitswesen | korrekt (SE-Bezeichnung) | hoch | Sekretariatsfachkräfte im Gesundheitswesen |
| Fachkräfte in Sozialverwaltung und -versicherung | 3353 | Fachkräfte in Sozialverwaltung und -versicherung | 3353 | Fachkräfte in Sozialverwaltung und -versicherung | korrekt (SE-Bezeichnung) | hoch | Fachkräfte in Sozialverwaltung und -versicherung |
| Polizist/in | 3355 | Polizeikommissare und Kriminalbeamte | 5412 | Polizisten (ohne Polizeikommissare) | korrigiert | hoch | Polizisten (ohne Polizeikommissare) |
| Fachkräfte für Rechts- und verwandte Angelegenheiten | 3411 | Fachkräfte für Rechts- und verwandte Angelegenheiten | 3411 | Fachkräfte für Rechts- und verwandte Angelegenheiten | korrekt (SE-Bezeichnung) | hoch | Fachkräfte für Rechts- und verwandte Angelegenheiten |
| Soziale Fachkräfte | 3412 | Soziale Fachkräfte | 3412 | Soziale Fachkräfte | korrekt (SE-Bezeichnung) | hoch | Soziale Fachkräfte |
| Sportlehrer, Sporttrainer und Sportfunktionäre | 3422 | Sportlehrer, Sporttrainer und Sportfunktionäre | 3422 | Sportlehrer, Sporttrainer und Sportfunktionäre | korrekt (SE-Bezeichnung) | hoch | Sportlehrer, Sporttrainer und Sportfunktionäre |
| Trainer und Betreuer im Bereich Fitness und Erholung | 3423 | Trainer und Betreuer im Bereich Fitness und Erholung | 3423 | Trainer und Betreuer im Bereich Fitness und Erholung | korrekt (SE-Bezeichnung) | hoch | Trainer und Betreuer im Bereich Fitness und Erholung |
| Raumgestalter und Dekorateure | 3432 | Raumgestalter und Dekorateure | 3432 | Raumgestalter und Dekorateure | korrekt (SE-Bezeichnung) | hoch | Raumgestalter und Dekorateure |
| Koch/Köchin EFZ | 3434 | Küchenchefs, stv. Küchenchefs und Souschefs | 5120 | Köche | korrigiert | hoch | Köche |
| Techniker für den Betrieb von Informations- und Kommunikationstechnologie | 3511 | Techniker für den Betrieb von Informations- und Kommunikationstechnologie | 3511 | Techniker für den Betrieb von Informations- und Kommunikationstechnologie | korrekt (SE-Bezeichnung) | hoch | Techniker für den Betrieb von Informations- und Kommunikationstechnologie |
| ICT-Supporter/in | 3512 | Techniker für die Anwenderbetreuung in der Informations- und Kommunikationstechnologie | 3512 | Techniker für die Anwenderbetreuung in der Informations- und Kommunikationstechnologie | korrekt | hoch | ICT-Supporter/in |
| Techniker für Rundfunk und audiovisuelle Medien | 3521 | Techniker für Rundfunk und audiovisuelle Medien | 3521 | Techniker für Rundfunk und audiovisuelle Medien | korrekt (SE-Bezeichnung) | hoch | Techniker für Rundfunk und audiovisuelle Medien |
| Telematiker/in EFZ | 3522 | Telekommunikationstechniker | 3522 | Telekommunikationstechniker | offen (Vorschlag 7422) | mittel | Telematiker/in EFZ |
| Kaufmann/-frau EFZ (allg. Richtung) | 4110 | Allgemeine Bürokräfte | 4110 | Allgemeine Bürokräfte | korrekt | hoch | Allgemeine Bürokräfte |
| Sekretär/in / Assistent/in | 4120 | Sekretariatskräfte (allgemein) | 4120 | Sekretariatskräfte (allgemein) | korrekt | hoch | Sekretär/in / Assistent/in |
| Schalterbedienstete und Fachkräfte im Bereich Finanzdienstleistungen | 4211 | Schalterbedienstete und Fachkräfte im Bereich Finanzdienstleistungen | 4211 | Schalterbedienstete und Fachkräfte im Bereich Finanzdienstleistungen | korrekt (SE-Bezeichnung) | hoch | Schalterbedienstete und Fachkräfte im Bereich Finanzdienstleistungen |
| Reiseverkehrsfachkräfte | 4221 | Reiseverkehrsfachkräfte | 4221 | Reiseverkehrsfachkräfte | korrekt (SE-Bezeichnung) | hoch | Reiseverkehrsfachkräfte |
| Empfangskräfte (allgemein) | 4226 | Empfangskräfte (allgemein) | 4226 | Empfangskräfte (allgemein) | korrekt (SE-Bezeichnung) | hoch | Empfangskräfte (allgemein) |
| Sachbearbeiter/in Buchhaltung | 4311 | Bürokräfte im Rechnungswesen und in der Buchhaltung | 4311 | Bürokräfte im Rechnungswesen und in der Buchhaltung | korrekt | hoch | Sachbearbeiter/in Buchhaltung |
| Bürokräfte in der Statistik, im Finanz- und Versicherungswesen | 4312 | Bürokräfte in der Statistik, im Finanz- und Versicherungswesen | 4312 | Bürokräfte in der Statistik, im Finanz- und Versicherungswesen | korrekt (SE-Bezeichnung) | hoch | Bürokräfte in der Statistik, im Finanz- und Versicherungswesen |
| Lagerist/in | 4321 | Fachkräfte in der Lagerwirtschaft | 4321 | Fachkräfte in der Lagerwirtschaft | korrekt | hoch | Fachkräfte in der Lagerwirtschaft |
| Bürokräfte in der Material- und Fertigungsplanung und verwandte Berufe | 4322 | Bürokräfte in der Material- und Fertigungsplanung und verwandte Berufe | 4322 | Bürokräfte in der Material- und Fertigungsplanung und verwandte Berufe | korrekt (SE-Bezeichnung) | hoch | Bürokräfte in der Material- und Fertigungsplanung und verwandte Berufe |
| Bürokräfte in der Transportwirtschaft und verwandte Berufe | 4323 | Bürokräfte in der Transportwirtschaft und verwandte Berufe | 4323 | Bürokräfte in der Transportwirtschaft und verwandte Berufe | korrekt (SE-Bezeichnung) | hoch | Bürokräfte in der Transportwirtschaft und verwandte Berufe |
| Postverteiler und -sortierer | 4412 | Postverteiler und -sortierer | 4412 | Postverteiler und -sortierer | korrekt (SE-Bezeichnung) | hoch | Postverteiler und -sortierer |
| Posthalter/in / Logistiker/in Post | 4415 | Bürokräfte für Registratur und Dokumentation | 4415 | Bürokräfte für Registratur und Dokumentation | offen (Vorschlag 4211 (42111) oder 4412) | mittel | Posthalter/in / Logistiker/in Post |
| Sachbearbeiter/in HR | 4416 | Bürokräfte im Personalwesen | 4416 | Bürokräfte im Personalwesen | korrekt | hoch | Sachbearbeiter/in HR |
| Sachbearbeiter/in öff. Verwaltung | 4416 | Bürokräfte im Personalwesen | 4110 | Allgemeine Bürokräfte | korrigiert | hoch | Allgemeine Bürokräfte |
| Reisebegleiter und Stewards | 5111 | Reisebegleiter und Stewards | 5111 | Reisebegleiter und Stewards | korrekt (SE-Bezeichnung) | hoch | Reisebegleiter und Stewards |
| Köche | 5120 | Köche | 5120 | Köche | korrekt (SE-Bezeichnung) | hoch | Köche |
| Hauswirtschaftler/in EFZ | 5131 | Chefs de service, Servicefach- und Servicehilfskräfte in Restaurants | 5151 | Reinigungs- und Hauswirtschaftleiter und -kräfte in Büros, Hotels und anderen Einrichtungen | korrigiert | hoch | Reinigungs- und Hauswirtschaftleiter und -kräfte in Büros, Hotels und anderen Einrichtungen |
| Hotelfachmann/-frau EFZ | 5131 | Chefs de service, Servicefach- und Servicehilfskräfte in Restaurants | 5151 | Reinigungs- und Hauswirtschaftleiter und -kräfte in Büros, Hotels und anderen Einrichtungen | korrigiert | hoch | Reinigungs- und Hauswirtschaftleiter und -kräfte in Büros, Hotels und anderen Einrichtungen |
| Restaurantfachmann/-frau EFZ | 5131 | Chefs de service, Servicefach- und Servicehilfskräfte in Restaurants | 5131 | Chefs de service, Servicefach- und Servicehilfskräfte in Restaurants | korrekt | hoch | Restaurantfachmann/-frau EFZ |
| Servicemitarbeiter/in | 5131 | Chefs de service, Servicefach- und Servicehilfskräfte in Restaurants | 5131 | Chefs de service, Servicefach- und Servicehilfskräfte in Restaurants | korrekt | hoch | Servicemitarbeiter/in |
| Barkeeper | 5132 | Barkeeper | 5132 | Barkeeper | korrekt (SE-Bezeichnung) | hoch | Barkeeper |
| Coiffeur/Coiffeuse EFZ | 5141 | Coiffeurs | 5141 | Coiffeurs | korrekt | hoch | Coiffeur/Coiffeuse EFZ |
| Kosmetiker und verwandte Berufe | 5142 | Kosmetiker und verwandte Berufe | 5142 | Kosmetiker und verwandte Berufe | korrekt (SE-Bezeichnung) | hoch | Kosmetiker und verwandte Berufe |
| Reinigungs- und Hauswirtschaftleiter und -kräfte in Büros, Hotels und anderen Einrichtungen | 5151 | Reinigungs- und Hauswirtschaftleiter und -kräfte in Büros, Hotels und anderen Einrichtungen | 5151 | Reinigungs- und Hauswirtschaftleiter und -kräfte in Büros, Hotels und anderen Einrichtungen | korrekt (SE-Bezeichnung) | hoch | Reinigungs- und Hauswirtschaftleiter und -kräfte in Büros, Hotels und anderen Einrichtungen |
| Hauswarte | 5153 | Hauswarte | 5153 | Hauswarte | korrekt (SE-Bezeichnung) | hoch | Hauswarte |
| Leiter eines Einzelhandelsgeschäftes | 5221 | Leiter eines Einzelhandelsgeschäftes | 5221 | Leiter eines Einzelhandelsgeschäftes | korrekt (SE-Bezeichnung) | hoch | Leiter eines Einzelhandelsgeschäftes |
| Verkaufsaufsichtskräfte in Handelsgeschäften | 5222 | Verkaufsaufsichtskräfte in Handelsgeschäften | 5222 | Verkaufsaufsichtskräfte in Handelsgeschäften | korrekt (SE-Bezeichnung) | hoch | Verkaufsaufsichtskräfte in Handelsgeschäften |
| Detailhandelsfachmann/-frau EFZ | 5223 | Verkäufer in Handelsgeschäften | 5223 | Verkäufer in Handelsgeschäften | korrekt | hoch | Verkäufer in Handelsgeschäften |
| Kassierer/in | 5223 | Verkäufer in Handelsgeschäften | 5230 | Kassierer und Kartenverkäufer | korrigiert | hoch | Kassierer und Kartenverkäufer |
| Verkäufer/in (ohne Ausbildung) | 5223 | Verkäufer in Handelsgeschäften | 5223 | Verkäufer in Handelsgeschäften | korrekt | hoch | Verkäufer in Handelsgeschäften |
| Kassierer und Kartenverkäufer | 5230 | Kassierer und Kartenverkäufer | 5230 | Kassierer und Kartenverkäufer | korrekt (SE-Bezeichnung) | hoch | Kassierer und Kartenverkäufer |
| Kinderbetreuerin/-betreuer | 5311 | Kinderbetreuer | 5311 | Kinderbetreuer | korrekt | hoch | Kinderbetreuerin/-betreuer |
| Lernbetreuer | 5312 | Lernbetreuer | 5312 | Lernbetreuer | korrekt (SE-Bezeichnung) | hoch | Lernbetreuer |
| Pflegeassistent/in | 5321 | Pflegehelfer in Institutionen | 5321 | Pflegehelfer in Institutionen | korrekt | hoch | Pflegeassistent/in |
| Spitex-Mitarbeiter/in | 5322 | Haus- und Familienpfleger und -betreuer | 5322 | Haus- und Familienpfleger und -betreuer | korrekt | hoch | Spitex-Mitarbeiter/in |
| Feuerwehrmann/-frau | 5411 | Feuerwehrleute | 5411 | Feuerwehrleute | korrekt | hoch | Feuerwehrmann/-frau |
| Polizisten (ohne Polizeikommissare) | 5412 | Polizisten (ohne Polizeikommissare) | 5412 | Polizisten (ohne Polizeikommissare) | korrekt (SE-Bezeichnung) | hoch | Polizisten (ohne Polizeikommissare) |
| Sicherheitsbeauftragter/-beauftragte | 5414 | Sicherheitsdienstleistungspersonal | 5414 | Sicherheitsdienstleistungspersonal | korrekt | hoch | Sicherheitsbeauftragter/-beauftragte |
| Landwirt/in EFZ | 6111 | Gemüseanbauer | 6130 | Landwirte mit Ackerbau und Tierhaltung (ohne ausgeprägten Schwerpunkt) | korrigiert | hoch | Landwirte mit Ackerbau und Tierhaltung (ohne ausgeprägten Schwerpunkt) |
| Gärtner/in EFZ | 6113 | Gärtner, Gartenbau und Pflanzenproduktion | 6113 | Gärtner, Gartenbau und Pflanzenproduktion | korrekt | hoch | Gärtner/in EFZ |
| Landwirte mit Ackerbau und Tierhaltung (ohne ausgeprägten Schwerpunkt) | 6130 | Landwirte mit Ackerbau und Tierhaltung (ohne ausgeprägten Schwerpunkt) | 6130 | Landwirte mit Ackerbau und Tierhaltung (ohne ausgeprägten Schwerpunkt) | korrekt (SE-Bezeichnung) | hoch | Landwirte mit Ackerbau und Tierhaltung (ohne ausgeprägten Schwerpunkt) |
| Maurer/in EFZ | 7112 | Maurer und verwandte Berufe | 7112 | Maurer und verwandte Berufe | korrekt | hoch | Maurer/in EFZ |
| Zimmermann/-frau EFZ | 7115 | Zimmerleute, Bautischler, Storenmonteure, Bootbauer | 7115 | Zimmerleute, Bautischler, Storenmonteure, Bootbauer | korrekt, Hinweis | hoch | Zimmermann/-frau EFZ |
| Boden- und Fliesenleger | 7122 | Boden- und Fliesenleger | 7122 | Boden- und Fliesenleger | korrekt (SE-Bezeichnung) | hoch | Boden- und Fliesenleger |
| Gipser, Trockenbauer | 7123 | Gipser, Trockenbauer | 7123 | Gipser, Trockenbauer | korrekt (SE-Bezeichnung) | hoch | Gipser, Trockenbauer |
| Isolierer | 7124 | Isolierer | 7124 | Isolierer | korrekt (SE-Bezeichnung) | hoch | Isolierer |
| Sanitärinstallateur/in EFZ | 7126 | Bauspengler und Sanitär- und Heizungsinstallateure | 7126 | Bauspengler und Sanitär- und Heizungsinstallateure | korrekt, Hinweis | hoch | Sanitärinstallateur/in EFZ |
| Maler/in und Gipser/in EFZ | 7131 | Maler und verwandte Berufe | 7131 | Maler und verwandte Berufe | korrekt, Hinweis | hoch | Maler/in und Gipser/in EFZ |
| Baumetallverformer und Metallbauer | 7214 | Baumetallverformer und Metallbauer | 7214 | Baumetallverformer und Metallbauer | korrekt (SE-Bezeichnung) | hoch | Baumetallverformer und Metallbauer |
| Polymechaniker/in EFZ | 7223 | Werkzeugmaschineneinrichter und -bediener | 7200 | Metallarbeiter, Mechaniker, Polymechaniker, Produktionsmechaniker und verwandte Berufe, onA | korrigiert | hoch | Polymechaniker/in EFZ |
| Kraftfahrzeugmechaniker und -schlosser | 7231 | Kraftfahrzeugmechaniker und -schlosser | 7231 | Kraftfahrzeugmechaniker und -schlosser | korrekt (SE-Bezeichnung) | hoch | Kraftfahrzeugmechaniker und -schlosser |
| Landmaschinen- und Industriemaschinenmechaniker und -schlosser | 7233 | Landmaschinen- und Industriemaschinenmechaniker und -schlosser | 7233 | Landmaschinen- und Industriemaschinenmechaniker und -schlosser | korrekt (SE-Bezeichnung) | hoch | Landmaschinen- und Industriemaschinenmechaniker und -schlosser |
| Uhrmacher, Uhrenarbeiter, Mikromechaniker | 7311 | Uhrmacher, Uhrenarbeiter, Mikromechaniker | 7311 | Uhrmacher, Uhrenarbeiter, Mikromechaniker | korrekt (SE-Bezeichnung) | hoch | Uhrmacher, Uhrenarbeiter, Mikromechaniker |
| Elektriker/in EFZ | 7411 | Bauelektriker und verwandte Berufe | 7411 | Bauelektriker und verwandte Berufe | korrekt | hoch | Elektriker/in EFZ |
| Automatiker und verwandte Berufe | 7412 | Automatiker und verwandte Berufe | 7412 | Automatiker und verwandte Berufe | korrekt (SE-Bezeichnung) | hoch | Automatiker und verwandte Berufe |
| Mechatroniker/in EFZ | 7421 | Elektroniker und Elektronik-Servicetechniker | 7421 | Elektroniker und Elektronik-Servicetechniker | offen (Vorschlag 7231 / 7412) | mittel | Mechatroniker/in EFZ |
| Metzger, Fischhändler und -verarbeiter und verwandte Berufe | 7511 | Metzger, Fischhändler und -verarbeiter und verwandte Berufe | 7511 | Metzger, Fischhändler und -verarbeiter und verwandte Berufe | korrekt (SE-Bezeichnung) | hoch | Metzger, Fischhändler und -verarbeiter und verwandte Berufe |
| Bäcker, Konditoren und Konfektmacher | 7512 | Bäcker, Konditoren und Konfektmacher | 7512 | Bäcker, Konditoren und Konfektmacher | korrekt (SE-Bezeichnung) | hoch | Bäcker, Konditoren und Konfektmacher |
| Produkttester und -klassierer (ohne Nahrungsmittel und Getränke) | 7543 | Produkttester und -klassierer (ohne Nahrungsmittel und Getränke) | 7543 | Produkttester und -klassierer (ohne Nahrungsmittel und Getränke) | korrekt (SE-Bezeichnung) | hoch | Produkttester und -klassierer (ohne Nahrungsmittel und Getränke) |
| Bediener von Anlagen und Maschinen für chemische Erzeugnisse | 8131 | Bediener von Anlagen und Maschinen für chemische Erzeugnisse | 8131 | Bediener von Anlagen und Maschinen für chemische Erzeugnisse | korrekt (SE-Bezeichnung) | hoch | Bediener von Anlagen und Maschinen für chemische Erzeugnisse |
| Bediener von Maschinen zur Herstellung von Nahrungs- und Genussmitteln | 8160 | Bediener von Maschinen zur Herstellung von Nahrungs- und Genussmitteln | 8160 | Bediener von Maschinen zur Herstellung von Nahrungs- und Genussmitteln | korrekt (SE-Bezeichnung) | hoch | Bediener von Maschinen zur Herstellung von Nahrungs- und Genussmitteln |
| Maschinenführer/in | 8211 | Berufe der Montage von mechanischen Bauteilen | 8211 | Berufe der Montage von mechanischen Bauteilen | offen (Vorschlag 8100 (onA) / 8189) | mittel | Maschinenführer/in |
| Produktionsmitarbeiter/in (Pharma) | 8211 | Berufe der Montage von mechanischen Bauteilen | 8131 | Bediener von Anlagen und Maschinen für chemische Erzeugnisse | korrigiert | hoch | Bediener von Anlagen und Maschinen für chemische Erzeugnisse |
| Zugbegleiter/in / Lokführer/in | 8311 | Lokomotivführer | 8311 | Lokomotivführer | korrekt, Hinweis | hoch | Zugbegleiter/in / Lokführer/in |
| Lieferwagenfahrer/in | 8322 | Personenkraftwagen-, Taxi-, Kleintransporter- und Kleinbusfahrer | 8322 | Personenkraftwagen-, Taxi-, Kleintransporter- und Kleinbusfahrer | korrekt | hoch | Lieferwagenfahrer/in |
| ÖV-Fahrer/in (Bus/Tram) | 8331 | Busfahrer und Strassenbahnführer | 8331 | Busfahrer und Strassenbahnführer | korrekt | hoch | ÖV-Fahrer/in (Bus/Tram) |
| Lastwagenfahrer/in | 8332 | Fahrer schwerer Lastkraftwagen | 8332 | Fahrer schwerer Lastkraftwagen | korrekt | hoch | Lastwagenfahrer/in |
| Führer von Erdbewegungs- und verwandten Maschinen, Strassenbau und Baumaschinen | 8342 | Führer von Erdbewegungs- und verwandten Maschinen, Strassenbau und Baumaschinen | 8342 | Führer von Erdbewegungs- und verwandten Maschinen, Strassenbau und Baumaschinen | korrekt (SE-Bezeichnung) | hoch | Führer von Erdbewegungs- und verwandten Maschinen, Strassenbau und Baumaschinen |
| Kranführer, Aufzugmaschinisten und Bediener verwandter Hebeeinrichtungen | 8343 | Kranführer, Aufzugmaschinisten und Bediener verwandter Hebeeinrichtungen | 8343 | Kranführer, Aufzugmaschinisten und Bediener verwandter Hebeeinrichtungen | korrekt (SE-Bezeichnung) | hoch | Kranführer, Aufzugmaschinisten und Bediener verwandter Hebeeinrichtungen |
| Reinigungspersonal und Hilfskräfte in Privathaushalten | 9111 | Reinigungspersonal und Hilfskräfte in Privathaushalten | 9111 | Reinigungspersonal und Hilfskräfte in Privathaushalten | korrekt (SE-Bezeichnung) | hoch | Reinigungspersonal und Hilfskräfte in Privathaushalten |
| Reinigungskraft / Hauswart | 9112 | Reinigungspersonal und Hilfskräfte in Büros, Hotels und anderen Einrichtungen | 9112 | Reinigungspersonal und Hilfskräfte in Büros, Hotels und anderen Einrichtungen | korrekt, Hinweis | hoch | Reinigungskraft / Hauswart |
| Hilfsarbeiter in Ackerbau und Tierhaltung (ohne ausgeprägten Schwerpunkt) | 9213 | Hilfsarbeiter in Ackerbau und Tierhaltung (ohne ausgeprägten Schwerpunkt) | 9213 | Hilfsarbeiter in Ackerbau und Tierhaltung (ohne ausgeprägten Schwerpunkt) | korrekt (SE-Bezeichnung) | hoch | Hilfsarbeiter in Ackerbau und Tierhaltung (ohne ausgeprägten Schwerpunkt) |
| Hilfsarbeiter im Gartenbau | 9214 | Hilfsarbeiter im Gartenbau | 9214 | Hilfsarbeiter im Gartenbau | korrekt (SE-Bezeichnung) | hoch | Hilfsarbeiter im Gartenbau |
| Hilfsarbeiter im Tiefbau | 9312 | Hilfsarbeiter im Tiefbau | 9312 | Hilfsarbeiter im Tiefbau | korrekt (SE-Bezeichnung) | hoch | Hilfsarbeiter im Tiefbau |
| Hilfsarbeiter im Hochbau | 9313 | Hilfsarbeiter im Hochbau | 9313 | Hilfsarbeiter im Hochbau | korrekt (SE-Bezeichnung) | hoch | Hilfsarbeiter im Hochbau |
| Frachtarbeiter und verwandte Berufe | 9333 | Frachtarbeiter und verwandte Berufe | 9333 | Frachtarbeiter und verwandte Berufe | korrekt (SE-Bezeichnung) | hoch | Frachtarbeiter und verwandte Berufe |
| Küchenhilfe | 9412 | Hilfsköche und Küchengehilfen | 9412 | Hilfsköche und Küchengehilfen | korrekt | hoch | Küchenhilfe |

