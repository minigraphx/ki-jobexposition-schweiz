# Rubrik: Aufgabenbasierte KI-Exposition von Berufen (Schweiz, Stand Oktober 2026)

Version 2.1 · Methode angelehnt an Eloundou, Manning, Mishkin & Rock (2023/2024),
«GPTs are GPTs», angepasst an die heute verfügbare Technik (Oktober 2026) und den Schweizer
Arbeitsmarkt.

Diese Rubrik ist vollständig: Sie brauchen keine weiteren Unterlagen ausser der Input-Datei
des Berufs und dem Ausgabeschema `schema_v2_1.json`.

**Neu in Version 2.1** (gegenüber 2.0; alles andere ist unverändert, insbesondere die Stufen
E0/E1/E2, die 50 %-Schwelle und das Feld P):
1. Der **Modus** ist dreistufig: «ersetzend» / «delegierend» / «unterstützend» (Abschnitt 3.1).
   Er trennt zwei Fragen, die bisher vermischt waren: *Wer führt die Tätigkeit aus?* und
   *Wird jede Ausgabe fachlich geprüft?*
2. Neues Feld **`restzeit_mensch`** (Abschnitt 3.2): verbleibender menschlicher Zeitaufwand
   als Band «<10» / «10-30» / «30-50» (% der heutigen Zeit).

---

## 0. Worum es geht

Sie bewerten einen Beruf in vier Schritten:

1. **Tätigkeiten ableiten**: 8–12 Kerntätigkeiten mit Zeitanteilen (Summe 100 %).
2. **KI-Exposition je Tätigkeit**: Stufe E0 / E1 / E2, bei E1/E2 zusätzlich der **Modus**
   «ersetzend», «delegierend» oder «unterstützend» und die **Restzeit** des Menschen
   («<10», «10-30», «30-50»); dazu Ihre **Sicherheit** (hoch/mittel/tief).
3. **Automatisierung ohne generative KI** je Tätigkeit: P0 / P1 (separate Kennzahl).
4. **CH-Hemmnisse** je exponierter Tätigkeit (optional) und eine Gesamt-Unsicherheit.

Sie berechnen **keinen** Gesamtscore. Die Kennzahlen werden später im Code aus Ihren Angaben
gebildet:

- Hauptmass **ζ = Σ Zeitanteil · 1[E1 oder E2]** (E1 und E2 zählen gleich);
- vorsichtige Variante **β = Σ Zeitanteil · (1[E1] + 0.5 · 1[E2])**;
- **Zeitersparnis = Σ Zeitanteil · 1[E1 oder E2] · (1 − Restzeit)**, Restzeit als Bandmitte
  (0.05 / 0.20 / 0.40);
- **ersetzbare Zeit = Σ Zeitanteil · 1[ersetzend] · (1 − Restzeit)**;
- separat **P = Σ Zeitanteil · 1[P1]** (nicht im Hauptscore).

Bewerten Sie deshalb jede Tätigkeit für sich und versuchen Sie nicht, auf ein bestimmtes
Gesamtergebnis hinzuarbeiten.

### Grundsatz: beste Einschätzung statt Vorsichtsregel
Geben Sie für jede Tätigkeit Ihre **beste Einschätzung** ab — die Stufe, die Sie für am
wahrscheinlichsten zutreffend halten. Es gibt **keine** Regel «im Zweifel die niedrigere
Stufe». Unsicherheit drücken Sie im Feld `sicherheit` aus, **nicht** durch eine tiefere
Stufe. Eine Tätigkeit, die Sie zu 60 % für E1 und zu 40 % für E0 halten, ist E1 mit
Sicherheit «mittel» (oder «tief» mit Begründung). Dasselbe gilt für Modus und Restzeit: Es
gibt keine Regel «im Zweifel der schwächere Modus» oder «im Zweifel das höhere Restzeit-Band».

### Was gemessen wird
**Stufe E (Hauptmass)**: technische Exposition gegenüber **Sprachmodellen (LLMs) und darauf
aufbauender Software** (generative KI). Nicht gemessen: ob Betriebe die Technik schon
einsetzen, ob Stellen abgebaut werden.

**Klassische, nicht-generative Technik zählt für die Stufe E nicht** — weder Robotik,
Selbstbedienungskassen, autonomes Fahren noch klassische Software (Lohnlauf, Mahnlauf,
regelbasierte Leistungsberechnung, Barcode, Navigationssoftware, Regel-Workflows ohne LLM).
Solche Technik erfassen Sie **ausschliesslich im Feld `physisch_automatisierbar`** (Abschnitt 4).

**Bezugsperson**: eine typische, voll ausgebildete Erwerbsperson dieses Berufs in der Schweiz
2026, in einem typischen Betrieb (oft KMU), über ein ganzes Arbeitsjahr gemittelt. Wenn der
Beruf sehr heterogen ist, wählen Sie das häufigste Setting und nennen es im `kommentar`
(z. B. «Pflegefachperson HF im Akutspital, Bettenstation»).

---

## 1. Schritt 1 — Kerntätigkeiten ableiten

### Quellen
- **Primär**: `esco_beschreibung` und `wesentliche_kompetenzen` mit `typ: "skill"`.
- **Ignorieren als Tätigkeit**: Kompetenzen mit `typ: "knowledge"` (z. B. «Anatomie»,
  «Steuerrecht») — das sind Wissensgebiete, keine Tätigkeiten. Sie dürfen sie nur als
  Hinweis nutzen, *wofür* das Wissen angewendet wird.
- **Sekundär**: `optionale_kompetenzen_skills`, nur wenn die wesentlichen Kompetenzen die
  Arbeit offensichtlich nicht abdecken; und eigenes Berufswissen zur Schweizer
  Berufsausübung (z. B. Bildungsverordnung EFZ, typischer Arbeitsalltag). Beachten Sie
  `datenlage_hinweis`, `ch_kontext` und `esco_korrektur` im Input.
- **ESCO-Rauschen** (Kompetenzen, die zum Beruf offensichtlich nicht passen) nicht übernehmen.

### Regeln für Tätigkeiten
- **8–12 Tätigkeiten**, zusammen ≥ 90 % der tatsächlichen Arbeitszeit abdeckend.
- **Konkret und beobachtbar**: *Verb + Objekt + Kontext*. Ein Beobachter müsste sehen
  können, dass die Person das gerade tut.
  - gut: «Kreditorenrechnungen kontieren und im ERP verbuchen»
  - gut: «Wunden versorgen und Verbände wechseln»
  - schlecht: «Kommunikationsfähigkeit», «Verantwortung übernehmen», «Fachwissen anwenden»
    (Eigenschaften/Kompetenzen, keine Tätigkeiten)
  - schlecht: «Administration» (zu grob — aufteilen in z. B. «Termine koordinieren» und
    «Leistungen in der Praxissoftware erfassen»)
- **Homogen bezüglich Exposition**: Wenn ein Teil einer Tätigkeit physisch und ein Teil
  Schreibarbeit ist, **teilen** Sie sie auf (z. B. «Elektroinstallation montieren» vs.
  «Mess- und Abnahmeprotokolle erstellen»). Ebenso, wenn ein Teil Routine und ein Teil
  Ermessensentscheid ist (z. B. «Deckung vorprüfen» vs. «Kulanzentscheid treffen»). Jede
  Tätigkeit soll *eine* Stufe sinnvoll tragen.
- **Keine Doppelzählung**, keine Sammelposten wie «Sonstiges». Allgemeine Posten wie
  «Weiterbildung» nur, wenn sie wirklich ≥ 5 % der Zeit ausmachen. Sehr kleine Routinen
  (< 3 %, z. B. Stunden eintragen) mit einer verwandten Tätigkeit zusammenlegen.
- **Zeitanteil** (`zeitanteil_pct`): ganze Zahl, bevorzugt in 5er-Schritten, je Tätigkeit
  2–60 % (Ausnahmen bis 80 % nur, wenn eine Tätigkeit den Beruf dominiert, z. B. Fahren
  beim Lastwagenfahrer). **Summe exakt 100.** Schätzen Sie die *heutige* Zeitverteilung,
  nicht eine zukünftige. Was in typischen Betrieben bereits vollständig von Software oder
  Maschinen erledigt wird, kostet die Person keine Zeit mehr und ist keine Tätigkeit.

---

## 2. Schritt 2 — KI-Expositionsstufe je Tätigkeit

### Die Schwelle (gilt für E1 und E2)
> Die Technik **reduziert die Zeit, die die Bezugsperson für diese Tätigkeit braucht, um
> mindestens 50 %, bei gleicher Qualität.**

- **Zeit** = gesamte Arbeitszeit der Person für die Tätigkeit *mit* Technik: Kontext
  zusammenstellen, Prompt formulieren, Ergebnis prüfen, korrigieren, nacharbeiten.
  Prüfaufwand ist **immer** einzurechnen.
- **Gleiche Qualität** = das Ergebnis würde vom üblichen Empfänger (Vorgesetzte, Kundin,
  Behörde, Patient) ohne Abstriche akzeptiert. Fehlerraten, die bei der Tätigkeit nicht
  tolerierbar sind (z. B. Medikamentendosierung, Rechtsfristen), müssen durch die Prüfung
  abgefangen werden — und diese Prüfung zählt zur Zeit.
- Gemeint ist die **typische** Ausführung der Tätigkeit, nicht der einfachste Spezialfall.
  Wenn nur ein kleiner Teil der Fälle die Schwelle erreicht, ist die Schwelle nicht erreicht
  (ggf. Tätigkeit aufteilen).
- **Prüf- und Revisionstätigkeiten** (Code-Review, Revision fremder Übersetzungen,
  Gegenlesen, Kontrolle von Abrechnungen) sind normal zu bewerten: Wenn eine KI-Vorprüfung
  den Grossteil der Fehler markiert und die Person gezielt die markierten Stellen und die
  Gesamtlogik prüft, kann die Schwelle erreicht sein. Die Verantwortung für die Freigabe
  allein spricht nicht gegen E1/E2 — sie betrifft den Modus.
- **Technisch machbar heute zählt** — nicht ob der Betrieb die Technik schon nutzt. Kosten
  müssen für einen Schweizer KMU-Betrieb vertretbar sein (Abo/Lizenz, keine
  Eigenentwicklung).
- Die Schwelle und das Feld `restzeit_mensch` (Abschnitt 3.2) hängen zusammen: Eine
  Tätigkeit ist genau dann E1/E2, wenn die Restzeit **höchstens 50 %** beträgt. Schätzen Sie
  mehr als 50 % Restzeit, ist die Tätigkeit E0.

### Prüfreihenfolge
1. Ist die Tätigkeit überwiegend **physisch / an Ort und Stelle mit Körper oder Händen**
   oder überwiegend **unmittelbare zwischenmenschliche Präsenz** (Pflege am Bett,
   Unterricht im Klassenzimmer, Beruhigen, Verhandeln von Angesicht zu Angesicht)?
   → **E0**. (Weiter mit Abschnitt 4, Feld P.)
2. Reicht ein **reines Chat-LLM** mit **vom Menschen bereitgestelltem Text-Kontext**, um
   die Schwelle zu erreichen? → **E1**.
3. Wird die Schwelle erst mit **Werkzeugen, Integration oder Multimodalität** erreicht
   (siehe E2)? → **E2**.
4. Die Schwelle wird mit keiner heute verfügbaren LLM-Technik erreicht → **E0**.

**E1 und E2 sind keine Rangfolge** («stärker/schwächer exponiert»), sondern beschreiben,
**welche Technik nötig ist**, um die Schwelle zu erreichen. Im Hauptmass ζ zählen beide
gleich. Wählen Sie E1, wenn das Chat-LLM allein reicht (auch wenn E2-Software noch mehr
bringen würde), und E2, wenn es erst mit Zusatzsoftware reicht. Die eigentliche
Entscheidung mit Gewicht ist **exponiert (E1/E2) oder nicht (E0)**.

Für Modus und Restzeit gilt die **beste verfügbare Technik** (auch wenn die Stufe E1 ist,
weil schon das Chat-LLM die Schwelle erreicht): Bewerten Sie Modus und Restzeit für die
Ausführung, die mit heute verfügbarer Technik in typischer CH-Praxis realistisch ist.

### E0 — keine relevante Exposition
Die Schwelle wird weder mit E1 noch mit E2 erreicht, insbesondere:
- **physische Tätigkeiten** (Montieren, Mauern, Fahren, Pflegen am Körper, Reinigen,
  Bedienen von Maschinen, Waren räumen) — Robotik und autonome Technik werden separat im
  Feld P erfasst, nicht hier;
- **Präsenz- und Beziehungstätigkeiten**, deren Wert in der persönlichen Anwesenheit liegt
  (Unterrichten im Klassenzimmer, Trösten, Patientengespräch, Kundenberatung von Angesicht
  zu Angesicht, Führen von Mitarbeitenden);
- **kognitive Tätigkeiten**, bei denen generative KI nach Ihrer besten Einschätzung weniger
  als 50 % Zeit spart oder die gleiche Qualität nicht erreicht;
- **Tätigkeiten, die klassische Software erledigt oder erledigen könnte** (Lohnlauf,
  Mahnlauf, Zahlungsabgleich per QR-Referenz, regelbasierte Renten-/Leistungsberechnung,
  automatische Disposition, Preflight): E0, Hinweis im Feld P. Nur der Anteil, der eine
  LLM-Leistung braucht (z. B. unklare Fälle beurteilen, Mutationen aus Freitext-E-Mails
  erfassen), kann E1/E2 sein — dann ggf. als eigene Tätigkeit erfassen.

### E1 — direkte Exposition (reines Chat-LLM)
Ein **Sprachmodell allein über eine Chat- oder API-Schnittstelle** erreicht die Schwelle.
Erlaubt ist nur:
- Text rein, Text raus (inkl. Code, Tabellen als Text, strukturierte Daten);
- der Mensch liefert den Kontext selbst: abtippen, kopieren/einfügen, Text- oder
  Office-Datei mit Text hochladen, **Text aus einem Fachsystem exportieren oder kopieren**
  (siehe Klärung D);
- das allgemeine Wissen und die Sprach-, Schreib-, Übersetzungs-, Zusammenfassungs-,
  Analyse- und Programmierfähigkeit eines aktuellen Frontier-Modells.

Nicht E1 (sondern ggf. E2): Websuche, Code-Ausführung, direkter Zugriff auf Firmensysteme
(E-Mail, ERP, CRM, Ticketsystem, Patientendossier), Erkennen gescannter Dokumente/Fotos/
Handschrift, Bild- oder Spracheingabe/-ausgabe, eigenständig handelnde Agenten.

Typisch E1: Texte entwerfen, umformulieren, übersetzen, zusammenfassen; Standardbriefe;
Code für klar beschriebene Funktionen schreiben und erklären; Formeln/Abfragen formulieren;
Fragen auf Basis eingefügter Regeltexte beantworten; Gliederungen, Konzepte, Unterrichts-
material in Textform; Textvergleich Ausgangs-/Zieltext.

### E2 — Exposition mit LLM-basierter Zusatzsoftware
Die Schwelle wird erst erreicht mit **heute (Okt. 2026) am Markt verfügbarer** Software, die
auf LLMs bzw. generativer KI aufbaut, z. B.:
- **Agenten mit Werkzeugen**: Websuche/Recherche-Agenten, Code-Ausführung und
  Datenanalyse, Coding-Agenten, die in einem Code-Repository selbständig Änderungen über
  mehrere Dateien vornehmen und Tests laufen lassen, KI-Review-Bots in Git-Plattformen,
  Computer-Use-Agenten (nur wo heute verlässlich);
- **Dokumentenverarbeitung**: Erkennen und Extrahieren aus Scans, PDFs, Rechnungen, Belegen,
  Formularen, Handschrift; Abgleich mit Stammdaten;
- **Bild und Sprache**: Bildverständnis (Fotos, Pläne, Screenshots), Bilderzeugung und
  -bearbeitung, generative Layout- und Designfunktionen, Spracherkennung/Transkription,
  Sprachausgabe, Voicebots, automatische Protokolle aus Gesprächen;
- **Integration in Fachsoftware**: KI-Funktionen in Office-Suiten, ERP/Buchhaltung, CRM,
  Ticket-/Kundendienstsystemen, Praxis-/Klinikinformationssystemen, Grafik- und
  CAD-Software, Übersetzungsumgebungen (CAT mit LLM) — sofern als Produktfunktion oder
  Standard-Integration verfügbar.

Nicht E2 (sondern E0): Software, die erst entwickelt werden müsste; Forschungsprototypen;
nicht-generative Technik (siehe Feld P).

### Klärungen zu Fragen aus dem Pilot

**A. E1 oder E2?** E1, wenn ein reines Chat-LLM mit vom Menschen bereitgestelltem
Text-Kontext die Schwelle erreicht; E2, wenn erst Werkzeuge, Systemintegration oder
Multimodalität (Bild, Ton, Scans) die Schwelle erreichen. Keine «niedrigere-Stufe»-Logik
zwischen E1 und E2 — es geht nur um die benötigte Technik.

**B. Schweizerdeutsch, Dialekt, Mehrsprachigkeit — eine Regel:**
- Die **technische Qualität der heutigen KI** (z. B. Transkription von Dialekt, Erkennung bei
  Lärm oder Akzent, Qualität in Italienisch oder Rätoromanisch) **geht in die Stufe ein**.
  Erreicht die Technik wegen Dialekt die Schwelle nicht, ist die Tätigkeit E0; erreicht sie
  sie trotzdem, E2. Unsicherheit über die Dialektqualität → `sicherheit`, nicht Hemmnis.
  Zusätzlicher Korrekturaufwand wegen Dialekt geht in die **Restzeit** ein.
- Das Hemmnis `mehrsprachigkeit` ist **nur für organisatorische oder kulturelle Hürden**:
  Kundschaft oder Patienten erwarten ein Gespräch in ihrer Sprache bzw. Mundart mit einem
  Menschen; Dokumente müssen parallel in mehreren Landessprachen geführt und abgestimmt
  werden; mehrsprachige Teams erschweren die Einführung.
- Nie denselben Grund doppelt verwenden (einmal in der Stufe, einmal als Hemmnis).
- Stand Okt. 2026 (beste Einschätzung): Einzeldiktat in Schweizerdeutsch → hochdeutscher Text
  ist in ruhiger Umgebung brauchbar; Gespräche mehrerer Personen, starker Dialekt, Lärm
  (Baustelle, Fahrerkabine) und Fachjargon sind deutlich fehleranfälliger.

**C. Rechtsverbindliche Entscheide (Behörden, Sozialversicherung, Gerichte):**
- **Stufe nach technischer Machbarkeit**: Kann KI den Entscheid samt Begründung in gleicher
  Qualität vorbereiten bzw. entwerfen und spart das ≥ 50 % der Zeit inkl. Prüfung → E1/E2.
- **Rechtliche Anforderungen** (Verfügung, rechtliches Gehör, Begründungspflicht,
  Rechtsmittel, Amtsgeheimnis) → Hemmnis `regulatorisch`, nicht tiefere Stufe.
- **Modus höchstens «delegierend»**, wenn rechtlich eine menschliche Einzelfallentscheidung
  vorgeschrieben ist: «ersetzend» ist dann ausgeschlossen. Ob «delegierend» oder
  «unterstützend», entscheidet die normale Modus-Regel (wer erstellt das Ergebnis?).
  Ohne solche Vorschrift gilt die normale Modus-Definition.

**D. Kontext aus Fachsystemen (Krankengeschichte, KIS, ERP, Fachapplikation):**
- Wenn die Person den nötigen Kontext mit vertretbarem Aufwand als **Text kopieren/einfügen
  oder exportieren** kann (Verlaufseinträge, Saldenliste, Falldaten) und dieser Aufwand in
  der Zeitrechnung die Schwelle nicht verhindert → **E1** zulässig.
- Wenn das **ohne Systemintegration praktisch nicht machbar** ist (grosse Datenmengen, viele
  Quellen, Bilder/Scans, proprietäre Formate) → **E2** (mit KI-Funktion im Fachsystem).
- Datenschutzbedenken beim Kopieren (Patientendaten, Amtsgeheimnis) sind Hemmnis
  `regulatorisch`, nicht Stufe.

**E. Klassische (nicht-LLM-)Software** (Lohnlauf, Mahnlauf, regelbasierte Berechnung,
Selbstbedienungskasse, Barcode, Navigationssoftware) zählt **nicht** als KI-Exposition →
E0 für diesen Teil; Hinweis über `physisch_automatisierbar` = P1 mit `p_art: "software"`
bzw. `"physisch"` (Abschnitt 4).

### Stand der Technik Oktober 2026 — Leitplanken
- **Stark**: Schreiben, Übersetzen (DE/FR/IT/EN auf hohem Niveau), Zusammenfassen,
  Programmieren (inkl. Coding-Agenten in Repositories), Code-Review-Vorschläge,
  strukturierte Extraktion aus Dokumenten, Erklären von Regeltexten, Bildbeschreibung,
  Bildbearbeitung (Freistellen, Erweitern, Retusche), Transkription von Hochdeutsch.
- **Eingeschränkt**: lange, mehrschrittige Agentenabläufe ohne menschliche Kontrolle;
  Fakten ohne Quelle (Halluzinationen → Prüfaufwand!); Schweizerdeutsch in Gesprächen und
  bei Lärm; Rätoromanisch; präzises Layout nach strengem CI; Aufgaben, deren Kontext nur im
  Kopf der Person oder auf Papier existiert.
- **Nicht verfügbar** (zählt nicht): KI, die selbständig rechtlich verbindlich handelt;
  allgemein einsetzbare Roboter (für P relevant, siehe Abschnitt 4).

### Grenzfälle (Beispiele, beste Einschätzung)

Spalte «Restzeit» = `restzeit_mensch` in % der heutigen Zeit (Abschnitt 3.2).

| Tätigkeit | Stufe | Modus | Restzeit | Begründung |
|---|---|---|---|---|
| Kundenbrief aus Stichworten verfassen | E1 | ersetzend | 10-30 | Reiner Text; Stichworte geben, Entwurf kurz sichten, freigeben. |
| Eingangsrechnungen (PDF/Papier) erfassen und kontieren | E2 | ersetzend | 10-30 | Dokumentenerkennung + Buchhaltungsintegration; Mensch bearbeitet markierte Ausnahmen. |
| Neues Feature in bestehender Codebasis mit Coding-Agent umsetzen | E2 | delegierend | 10-30 | Agent schreibt Code und Tests über mehrere Dateien; Entwicklerin spezifiziert, steuert und reviewt jede Änderung. |
| Einzelne Funktion nach Spezifikation programmieren | E1 | delegierend | 30-50 | Code-Erzeugung im Chat; Entwickler kopiert Kontext, prüft und testet jede Änderung, integriert selbst. |
| Bug in grossem Code-Repository finden und beheben, inkl. Tests | E2 | delegierend | 30-50 | Erst mit Coding-Agent (Repo-Zugriff, Ausführung) ≥ 50 %; Entwickler steuert die Fehlersuche und prüft den Fix. |
| Pull Requests von Kolleg/innen reviewen | E2 | unterstützend | 30-50 | Reviewer führt das Review selbst; Review-Bot fasst zusammen und markiert Probleme. Sicherheit meist «mittel». |
| Fachtext DE→FR übersetzen (zur Publikation) | E1 | delegierend | 30-50 | LLM übersetzt; Fachperson revidiert jede Übersetzung vollständig. |
| Interne Mitteilung übersetzen (nicht publiziert, nicht haftungsrelevant) | E1 | ersetzend | <10 | Maschinelle Übersetzung ohne Revision ausreichend. |
| Fremde Übersetzung revidieren (Vier-Augen-Prinzip) | E1 | unterstützend | 30-50 | Revisorin revidiert selbst; LLM-Abgleich Ausgangs-/Zieltext markiert Auslassungen, Sinn- und Terminologiefehler. Sicherheit meist «mittel». |
| Konferenzdolmetschen (simultan) bei Verhandlungen | E0 | – | – | Echtzeit-Sprach-KI erreicht die geforderte Qualität bei hohem Risiko nicht. |
| Telefonische Standardauskünfte (Öffnungszeiten, Fallstatus) | E2 | ersetzend | 10-30 | Voicebot mit Systemzugriff; Menschen übernehmen weitergeleitete Spezialfälle. Dialektqualität fliesst in Stufe/Sicherheit ein (Klärung B). |
| Sitzungsprotokoll aus Aufnahme erstellen | E2 | ersetzend | 10-30 | Transkription und Zusammenfassung; protokollführende Person liest gegen und gibt frei. |
| Pflegedokumentation nach der Visite | E2 | delegierend | 30-50 | Spracheingabe/ambiente Dokumentation erstellt den Eintrag im KIS; jeder Eintrag wird fachlich geprüft und verantwortet. |
| Verlaufsnotizen aus kopierten KIS-Einträgen zu einem Austrittsbericht zusammenfassen | E1 | delegierend | 30-50 | Kontext als Text kopierbar (Klärung D); KI entwirft, Arzt prüft und verantwortet jeden Bericht. |
| Verfügung über Leistungsanspruch mit Begründung verfassen | E1 | delegierend | 30-50 | KI entwirft aus Falldaten und Rechtsgrundlagen; menschlicher Einzelfallentscheid vorgeschrieben → höchstens delegierend; Hemmnis «regulatorisch». |
| Renten-/Leistungsberechnung in der Fachapplikation | E0 | – | – | Regelbasierte Berechnung ist klassische Software → E0; ggf. P1 (software). |
| Lohnlauf durchführen | E0 | – | – | Klassische Lohnsoftware → E0, P1 (software). Mutationen aus Freitext-Meldungen erfassen ggf. separat (E2). |
| Monatsabschluss: Abgrenzungen/Rückstellungen ermitteln und buchen | E1 oder E2 | unterstützend | 30-50 | Berechnung und Buchungsvorschläge aus exportierter Saldenliste/Belegliste = E1; erst mit Abgleich direkt im ERP über viele Konten = E2. Buchhalterin beurteilt jede Position selbst (Ermessen) → unterstützend. |
| Patientin mobilisieren, Körperpflege | E0 | – | – | Physisch. |
| Unterrichten vor der Klasse | E0 | – | – | Präsenz- und Beziehungstätigkeit. |
| Arbeitsblätter und Prüfungen erstellen | E1 | delegierend | 30-50 | KI erstellt das Blatt; Lehrperson prüft und passt an die Klasse an. Baut sie das Blatt selbst und holt nur Ideen/Aufgaben → unterstützend. |
| Handschriftliche Schülerarbeiten korrigieren | E2 oder E0 | unterstützend | 30-50 | Handschrifterkennung + Fehlermarkierung; Lehrperson liest und bewertet jede Arbeit selbst. Beste Einschätzung je nach Arbeitstyp (Rechnen/Diktat eher E2, freie Texte von Unterstufenkindern eher E0), Sicherheit angeben. |
| Mess- und Abnahmeprotokoll schreiben | E2 | delegierend | 30-50 | Messwerte/Fotos per Spracheingabe, Bild, Formular-App; App erstellt das Protokoll, Elektriker prüft und unterschreibt. |
| Regierapport mit Arbeitsbeschrieb und Material erstellen | E2 | delegierend | 30-50 | Spracheingabe in Rapport-App erstellt den Rapport; Polier prüft. |
| Nur Stunden und Baustelle auf Zettel/App eintragen (wenige Minuten pro Woche) | E0 | – | – | Reine Zahlen, kaum Zeit; KI spart nichts Relevantes. Mit verwandter Tätigkeit zusammenlegen. |
| Ware an der Kasse scannen | E0 | – | – | Physisch; Selbstbedienungskasse ist keine LLM-Technik → P1 (physisch). |
| Lastwagen fahren | E0 | – | – | Physisch; P0 (fahrerloser Lkw-Verkehr in CH nicht zugelassen/verfügbar). |
| Tourenplanung/Routenwahl am Morgen | E0 oder E2 | – / delegierend | – / 30-50 | Meist durch Disposition/Navigationssoftware (kein LLM) vorgegeben → E0, ggf. P1 (software); nur wenn die Person selbst plant und ein LLM-Agent ≥ 50 % spart → E2 (Agent schlägt Tour vor, Person prüft jede). |
| Entscheid über komplexen Einzelfall (Kulanz, Diagnose, Strategie) | meist E0 | – | – | Vorbereitung (Fakten zusammentragen) separat als E1/E2-Tätigkeit erfassen; der Entscheid selbst spart selten 50 %. |
| Social-Media-Post mit Bild erstellen | E2 | delegierend | 30-50 | Text wäre E1, Bilderzeugung/-bearbeitung braucht Zusatzsoftware; KI erstellt Text und Bild, Person wählt aus und prüft jeden Post. |
| Moodboards, Varianten und Scribbles für ein Konzept erstellen | E2 | delegierend | 30-50 | Bildgeneratoren liefern Varianten in einem Bruchteil der Zeit; Idee, Steuerung und Auswahl bleiben beim Menschen. Sicherheit meist «mittel». |
| Logo/Corporate Design im Kundenprozess entwickeln | E0 | – | – | Ideenfindung und Abstimmung mit Kundschaft dominieren; Varianten-Produktion separat erfassen. |
| Bestehendes Layout in weitere Formate/Sprachen adaptieren | E2 | delegierend | 10-30 | Generative Layout- und Übersetzungsfunktionen in der Grafiksoftware erstellen die Fassungen; Kontrolle jeder Fassung. |
| Neues Layout nach strengem CI im Detail gestalten | E0 oder E2 | – / unterstützend | – / 30-50 | Beste Einschätzung je nach Produkt; bei Unsicherheit Sicherheit «tief» mit Begründung statt automatisch E0. |

---

## 3. Modus und Restzeit (nur bei E1 und E2)

Bei **E0** sind `modus` und `restzeit_mensch` immer `null`. Bei **E1/E2** sind beide Pflicht.
Beide gelten **unabhängig davon, ob E1 oder E2**.

### 3.1 Modus — wer führt aus, und wird jede Ausgabe geprüft?

Der Modus beantwortet nacheinander zwei Fragen:

**Frage 1 — Wer erstellt das Ergebnis der Tätigkeit?** (Ergebnis = der Arbeitsoutput:
Text, Code, Buchung, Bericht, Übersetzung, Antwort an die Kundin, Bild.)
- Erarbeitet **der Mensch** das Ergebnis weiterhin selbst, und die KI liefert Teilergebnisse,
  Vorschläge, Recherche, Markierungen oder Formulierungshilfe → **«unterstützend»**.
- Erstellt **die KI** das Ergebnis (ganz oder bis auf Korrekturen) → weiter mit Frage 2.

**Frage 2 — Wird jede einzelne Ausgabe fachlich geprüft?**
- **Ja**: Der Mensch spezifiziert und steuert die KI und **prüft jede Ausgabe inhaltlich**
  (gegen Quellen, Fachwissen oder den Einzelfall, oft mit Korrekturen) → **«delegierend»**.
- **Nein**: Der Mensch **gibt höchstens frei oder prüft stichprobenartig**; er bearbeitet
  allenfalls von der Software markierte Ausnahmen → **«ersetzend»**.

Definitionen:
- **ersetzend**: Die KI führt die Tätigkeit aus; der Mensch gibt höchstens frei, prüft
  stichprobenartig oder bearbeitet markierte Ausnahmen. *Freigeben* heisst: kurze
  Plausibilitätssichtung ohne Nachrecherche, Korrektur nur in Ausnahmefällen. (Entspricht
  dem v2-Modus «automatisierend».)
- **delegierend**: Die KI führt die Tätigkeit aus (erstellt das Ergebnis); der Mensch
  **steuert/spezifiziert** (Auftrag beschreiben, Kontext und Unterlagen geben, Rückfragen
  beantworten, Korrekturanweisungen geben) und **prüft jede Ausgabe fachlich**. Die
  fachliche Verantwortung bleibt beim Menschen.
- **unterstützend**: Der Mensch **führt die Tätigkeit weiterhin selbst aus**; die KI liefert
  Teilergebnisse, Vorschläge, Recherche, Markierungen oder Formulierungshilfe und macht den
  Menschen schneller oder besser.

**Abgrenzungsregeln**
1. **Ergebnis-Test (unterstützend vs. delegierend/ersetzend)**: Stammt der Grossteil des
   fertigen Ergebnisses (Wortlaut, Code, Buchungen, Bild) typischerweise von der KI, und
   besteht die menschliche Arbeit vor allem aus Spezifizieren, Steuern, Prüfen und
   punktuellem Korrigieren? → delegierend oder ersetzend. Schreibt oder erarbeitet der
   Mensch den Grossteil selbst (auch wenn er KI-Bausteine übernimmt) → unterstützend.
2. **Prüf-Test (delegierend vs. ersetzend)**: Würde ein Betrieb, der die Technik voll
   einsetzt, die Ausgabe **in der Regel ohne inhaltliche Einzelprüfung** weiterverwenden
   (höchstens Stichprobe, Klick-Freigabe oder Bearbeitung markierter Ausnahmen)?
   → ersetzend. Wird jede Ausgabe inhaltlich geprüft → delegierend.
3. **Prüfen jeder Ausgabe macht eine Tätigkeit nicht «unterstützend».** Entscheidend für
   «unterstützend» ist allein, dass der Mensch die Tätigkeit selbst ausführt. Ein
   Coding-Agent, dessen Änderungen die Entwicklerin einzeln reviewt, ist «delegierend».
4. **Kontext bereitstellen** (Kopieren, Hochladen) und Ergebnis übernehmen gilt **nicht** als
   Ausführung; Steuern und Spezifizieren auch nicht.
5. **Rechtlich vorgeschriebener menschlicher Einzelfallentscheid** (Verfügung, Diagnose mit
   Vorbehaltstätigkeit, Unterschriftspflicht mit inhaltlicher Verantwortung) → höchstens
   «delegierend» (Klärung C).
6. **Prüf- und Revisionstätigkeiten** (Review, Revision, Kontrolle): Ist die Prüfung selbst
   die Tätigkeit und führt der Mensch sie mit KI-Markierungen durch → «unterstützend».
   Erstellt die KI den Prüfbericht und der Mensch sichtet nur → «delegierend» oder
   «ersetzend» nach Regel 2.
7. Gemischte Fälle: Massgebend ist der **typische Fall** (zeitgewichtet). Unterscheiden sich
   Fälle stark (z. B. Standardfälle ersetzend, Spezialfälle unterstützend), Tätigkeit
   aufteilen oder den zeitlich überwiegenden Modus wählen.

**Beispiele «ersetzend»**
1. Eingangsrechnungen erfassen und kontieren (E2): KI-Erfassung im Buchhaltungssystem; die
   Person bearbeitet nur markierte Ausnahmen und Stichproben. Restzeit 10-30.
2. Standardkorrespondenz (Eingangsbestätigung, Unterlagen nachfordern, Terminbestätigung)
   aus Falldaten erstellen (E1/E2): Freigabe per Klick. Restzeit <10.
3. Telefonische Standardauskünfte (Öffnungszeiten, Fallstatus, fehlende Unterlagen) per
   Voicebot (E2): Menschen übernehmen nur weitergeleitete Spezialfälle. Restzeit 10-30.
4. Interne Mitteilungen, Produktdatenblätter oder Informationstexte übersetzen, die nicht
   publiziert/haftungsrelevant sind (E1): maschinelle Übersetzung ohne Revision ausreichend.
   Restzeit <10.

**Beispiele «delegierend»**
1. Neues Feature in einer bestehenden Codebasis umsetzen (E2): Ein Coding-Agent schreibt
   Code und Tests über mehrere Dateien; die Entwicklerin spezifiziert, steuert bei
   Rückfragen und reviewt jede Änderung, bevor sie gemergt wird. Restzeit 10-30.
2. Gutachten oder Bericht (z. B. ärztlicher Austrittsbericht aus kopierten KIS-Einträgen)
   entwerfen (E1): Die KI erstellt den Entwurf, die Fachperson prüft ihn inhaltlich gegen
   die Akte und verantwortet ihn. Restzeit 30-50.
3. Verfügung über einen Leistungsanspruch verfassen (E1): Die KI entwirft Verfügung und
   Begründung; ein menschlicher Einzelfallentscheid ist rechtlich vorgeschrieben →
   höchstens delegierend. Restzeit 30-50.
4. Fachübersetzung zur Publikation (E1): Das LLM übersetzt, die Fachperson revidiert jede
   Übersetzung vollständig. Restzeit 30-50.

**Beispiele «unterstützend»**
1. Zeitungsartikel recherchieren und schreiben (E2): Die Journalistin recherchiert und
   schreibt weiterhin selbst; ein Recherche-Agent fasst Quellen zusammen, die KI schlägt
   Titel und Kürzungen vor; Fakten werden einzeln verifiziert. Restzeit 30-50.
2. Pull Requests von Kolleg/innen reviewen (E2): Der Reviewer führt das Review selbst; der
   Review-Bot fasst die Änderung zusammen und markiert mögliche Probleme. Restzeit 30-50.
3. Monatsabschluss: Abgrenzungen und Rückstellungen (E1/E2): Die Buchhalterin beurteilt
   jede Position selbst (Ermessen); die KI liefert Berechnungen und Buchungsvorschläge.
   Restzeit 30-50.
4. Fremde Übersetzung revidieren (E1): Die Revisorin revidiert selbst; der LLM-Abgleich
   markiert Auslassungen und Terminologiefehler. Restzeit 30-50.

**Kontrastpaare** (gleiches Thema, verschiedener Modus)
- *Code*: Agent setzt um, Entwicklerin reviewt jede Änderung → delegierend · Entwickler
  schreibt den Code selbst und holt sich nur Snippets/Erklärungen → unterstützend (erreicht
  dann oft die 50 %-Schwelle nicht → E0) · Agent setzt um und merged nach automatischen Tests
  ohne menschliches Review → ersetzend (in typischer CH-Praxis 2026 selten verlässlich).
- *Übersetzung*: interne Mitteilung ohne Revision → ersetzend · Publikation mit Revision →
  delegierend · Revision einer fremden Übersetzung mit KI-Markierungen → unterstützend.

### 3.2 Restzeit des Menschen (`restzeit_mensch`)

> Geschätzter **verbleibender menschlicher Zeitaufwand** für diese Tätigkeit, in **% der
> heutigen Zeit** (heutige Zeit ohne generative KI = 100 %), bei voller Nutzung heute
> verfügbarer Technik in typischer Schweizer Praxis und bei gleicher Qualität.

Bänder (genau einen Wert wählen):

| Wert | Bedeutung | Bandmitte (für die Kennzahl) |
|---|---|---|
| `"<10"` | unter 10 % der heutigen Zeit bleiben beim Menschen | 0.05 |
| `"10-30"` | 10 % bis unter 30 % | 0.20 |
| `"30-50"` | 30 % bis 50 % | 0.40 |

Wegen der 50 %-Schwelle gibt es **kein Band über 50 %**: Bleiben mehr als 50 %, ist die
Tätigkeit E0 (Modus und Restzeit `null`).

**Was zählt zur Restzeit** (alles, was die Person für diese Tätigkeit noch selbst tut):
- Kontext zusammenstellen, Unterlagen hochladen/kopieren, **Spezifizieren** und Prompten;
- **Steuern**: Rückfragen beantworten, Zwischenergebnisse beurteilen, Korrekturanweisungen,
  Iterationen; Wartezeit nur, wenn die Person währenddessen nichts anderes tun kann;
- **Prüfen**, **Korrigieren**, Nacharbeiten, **Freigeben**, Unterschreiben;
- Ausnahmen und Spezialfälle, die die Technik nicht löst (zeitgewichtet über alle Fälle).

**Wie schätzen**
- **Heute verfügbare Technik** (Okt. 2026), die beste realistische Lösung für einen
  Schweizer Betrieb (Abo/Standardprodukt), wie bei der Schwelle; **typische CH-Praxis**
  (übliche Qualitätsanforderungen, Vier-Augen-Prinzip, Dokumentationspflichten).
- **Zeitgewichtet über die Fälle mitteln**: z. B. 80 % Standardfälle mit 5 % Restzeit und
  20 % Ausnahmen mit 60 % Restzeit → 0.8 · 5 + 0.2 · 60 = 16 % → «10-30».
- Regulatorische Pflichten, die Zeit kosten (z. B. inhaltliche Prüfung vor Unterschrift),
  zählen zur Restzeit; ein Hemmnis ohne Zeitwirkung (z. B. Datenschutzbedenken) nicht —
  dafür gibt es `ch_hemmnis`.
- Bei Unsicherheit zwischen zwei Bändern: beste Einschätzung wählen; die Unsicherheit geht
  in `sicherheit` (bei «tief» in der `sicherheit_begruendung` erwähnen).

**Beispiele**
- Standardbrief aus Falldaten, Freigabe per Klick: früher 10 Min., heute 30 Sek. → «<10».
- Eingangsrechnungen im Buchhaltungssystem: Standardbelege laufen durch, Ausnahmen
  (unbekannte Lieferanten, Kontierungsfragen) bleiben → ≈ 15–25 % → «10-30».
- Feature mit Coding-Agent: Spezifizieren, Steuern, Review jeder Änderung, Nacharbeit
  → ≈ 20–30 % → «10-30» (bei unklaren Anforderungen oder heikler Altlast-Codebasis eher
  «30-50»).
- Austrittsbericht aus KIS-Einträgen: Kontext kopieren, Entwurf gegen die Akte prüfen,
  korrigieren, visieren → ≈ 35–45 % → «30-50».
- Fachübersetzung zur Publikation mit vollständiger Revision (Post-Editing) → «30-50».
- Review mit KI-Markierungen (unterstützend): Reviewer liest weiterhin selbst, aber gezielter
  → «30-50»; nur in sehr standardisierten Fällen «10-30».

**Plausibilität Modus × Restzeit** (Hinweis, kein Verbot):
- «ersetzend» passt zu «<10» oder «10-30». «ersetzend» mit «30-50» ist widersprüchlich
  (wer höchstens freigibt, braucht kaum 30–50 % der Zeit) → Modus oder Band überdenken.
- «delegierend» liegt typischerweise bei «10-30» oder «30-50».
- «unterstützend» liegt typischerweise bei «30-50», seltener «10-30». «unterstützend» mit
  «<10» ist widersprüchlich (wer selbst ausführt, braucht mehr als 10 %).

---

## 4. Automatisierung ohne generative KI (`physisch_automatisierbar`, separate Kennzahl)

Für **jede** Tätigkeit (auch E1/E2) zusätzlich:

- **P1** = Die Tätigkeit kann mit **heute in der Schweiz kommerziell verfügbarer
  nicht-generativer Technik** — Automatisierung, Robotik, Automaten, Selbstbedienung,
  autonome Technik oder klassische (regelbasierte) Software — **in relevantem Umfang**
  übernommen werden: **≥ 50 % der heutigen Zeit** der Bezugsperson für diese Tätigkeit, bei
  gleicher Qualität, zu für Betriebe der Branche vertretbaren Kosten.
- **P0** = sonst.

Regeln:
- **Nicht spekulativ, kein «in Zukunft»**: Die Technik muss heute gekauft werden können und
  in der Schweiz oder vergleichbaren Ländern im regulären Einsatz sein; zulassungspflichtige
  Technik muss in der Schweiz zugelassen sein. Prototypen und Pilotprojekte zählen nicht.
- Bezug ist die **heutige** Ausführung: Was die typische Person heute noch selbst tut, obwohl
  verfügbare Technik es übernehmen könnte (weil viele Betriebe sie noch nicht einsetzen),
  ist P1. Was bereits vollständig automatisiert ist, ist keine Tätigkeit mehr.
- P ist **unabhängig von E** zu bewerten. Eine Tätigkeit kann E2 und P1 sein (z. B.
  Belegerfassung: LLM-Extraktion und klassische Formularerkennung). P geht **nicht** in ζ,
  β oder die Zeitersparnis ein; `restzeit_mensch` bezieht sich nur auf generative KI.
- Bei P1 zusätzlich `p_art`: `"physisch"` (Robotik, Automaten, Selbstbedienung, autonome
  Technik) oder `"software"` (klassische Software ohne generative KI). Bei P0: `p_art` =
  `null`. Nennen Sie die Technik in der `begruendung`.

| Tätigkeit | P | p_art | Begründung |
|---|---|---|---|
| Ware an der Kasse scannen und kassieren | P1 | physisch | Selbstbedienungs- und Self-Scanning-Kassen sind im CH-Detailhandel verbreitet. |
| Waren im Lager kommissionieren | P1 | physisch | Lagerroboter/automatische Kleinteilelager (z. B. Behälter-Robotersysteme) kommerziell verfügbar. |
| Kühe melken | P1 | physisch | Melkroboter sind auf Schweizer Betrieben im Einsatz. |
| Bodenreinigung grosser freier Flächen (Hallen, Gänge) | P1 | physisch | Autonome Scheuersaugmaschinen verfügbar. |
| Billette verkaufen, Standardauskünfte am Schalter | P1 | physisch | Automaten und Apps (Selbstbedienung). |
| Lohnlauf, Mahnlauf, Zahlungsabgleich per QR-Referenz | P1 | software | Standard-Lohn-/Buchhaltungssoftware. |
| Lastwagen im regulären Strassennetz fahren | P0 | – | Fahrerloser Lkw-Verkehr ist in der Schweiz 2026 weder zugelassen noch verfügbar; Assistenzsysteme ersetzen die Fahrperson nicht. |
| Mauerwerk erstellen | P0 | – | Mauerroboter nur in Pilotprojekten, nicht im regulären CH-Baustellenbetrieb. |
| Büros mit Möbeln und Sanitäranlagen reinigen | P0 | – | Roboter übernehmen keine 50 % dieser Arbeit. |
| Elektroinstallation montieren, Patienten pflegen | P0 | – | Keine verfügbare Robotik in relevantem Umfang. |

---

## 5. Sicherheit je Tätigkeit

Feld `sicherheit` — wie sicher sind Sie bei **Stufe, Modus, Restzeit und P** dieser
Tätigkeit?

- **hoch** — eindeutig; sachkundige Bewerter kämen praktisch sicher zum gleichen Ergebnis.
- **mittel** — begründete Einschätzung, aber nahe der 50 %-Schwelle, an einer Bandgrenze der
  Restzeit, oder Technikstand für diesen Anwendungsfall teilweise unklar.
- **tief** — echte Unsicherheit; eine andere Stufe (oder ein anderer Modus/Restzeit-Band/
  P-Wert) ist fast ebenso plausibel. **Pflicht**: `sicherheit_begruendung` mit 1 Satz — was
  ist unsicher und welche Alternative kommt in Frage (z. B. «Dialekterkennung am Telefon
  wenig belegt; E0 ebenso plausibel»).

Bei «hoch» und «mittel»: `sicherheit_begruendung` = `null`.

---

## 6. CH-Hemmnis (optional, nur bei E1/E2)

Liste `ch_hemmnis` mit 0–3 Werten. Nur bei **exponierten Tätigkeiten (E1/E2)** und nur, wenn
das Hemmnis **für diese Tätigkeit in der Schweiz wesentlich** ist — nicht pauschal. Bei E0
immer `[]`. **Die Stufe wird dadurch NICHT verändert**; das Hemmnis wird separat ausgewiesen.

| Wert | Wann |
|---|---|
| `regulatorisch` | Berufszulassung/Vorbehaltstätigkeit (z. B. Medizinalberufe, Anwaltsmonopol, Notariat), Haftung, Unterschriftspflicht, Verfügungs- und Begründungspflicht, Rechtsmittel, Berufs- und Amtsgeheimnis, Datenschutz (revDSG) und Cloud-Restriktionen in Verwaltung, Spital, Bank; kantonal unterschiedliche Vorschriften. |
| `mehrsprachigkeit` | Nur organisatorische/kulturelle Hürden: Kundschaft erwartet ein Gespräch mit einem Menschen in ihrer Sprache bzw. Mundart; Dokumente parallel in mehreren Landessprachen; mehrsprachige Teams erschweren die Einführung. **Nicht** für die technische Qualität der Dialekterkennung (→ Stufe/Sicherheit, Klärung B). |
| `vertrauen` | Kundschaft erwartet persönliche Beziehung/Kundennähe (Hausbank, Hausarzt, Lehrperson-Eltern), Akzeptanzprobleme bei KI-Kontakt, Reputationsrisiko. |

---

## 7. Gesamt-Unsicherheit und Kommentar

- `unsicherheit` (Beruf als Ganzes — **Achtung: umgekehrte Richtung als `sicherheit`**):
  - **niedrig** — Input passt gut, Tätigkeiten klar, Stufen meist eindeutig;
  - **mittel** — einzelne Stufen sind Grenzfälle oder Zeitanteile grob geschätzt;
  - **hoch** — Input dünn/unpassend, Beruf sehr heterogen, oder mehrere zentrale
    Tätigkeiten liegen genau an der 50 %-Schwelle.
- `kommentar` (1–4 Sätze): angenommenes Setting, Probleme mit dem Input (z. B. ESCO passt
  nur teilweise), wichtigste Grenzfälle.

---

## 8. Kalibrierungsbeispiele

Die Beispiele zeigen das Niveau. Sie sind bewusst knapp; die Zeitanteile sind plausible
Schätzungen. (Kennzahlen nur zur Orientierung — Sie berechnen sie nicht.)
Spalten: Stufe · Modus · Restzeit (R, % der heutigen Zeit) · P · Sicherheit (S) · Hemmnis.

### 8.1 Sachbearbeiter/in Schadenabteilung (Sachversicherung) — eher hoch exponiert

| # | Tätigkeit | % | Stufe | Modus | R | P | S | Hemmnis | Kurzbegründung |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Schadenmeldungen und Belege (Rechnungen, Fotos, Rapporte) sichten und Daten ins Schadensystem übertragen | 20 | E2 | ersetzend | 10-30 | P0 | hoch | – | Dokumenten-/Bilderkennung mit Systemintegration; Mensch bearbeitet markierte Ausnahmen. Heterogene Belege → klassische Formularerkennung allein reicht nicht. |
| 2 | Deckung anhand Police und AVB vorprüfen | 15 | E1 | delegierend | 30-50 | P0 | mittel | – | AVB und Fall einfügen, LLM erstellt die Deckungsbeurteilung; jede wird fachlich kontrolliert. |
| 3 | Kostenvoranschläge und Schadenhöhe plausibilisieren | 10 | E2 | unterstützend | 30-50 | P0 | mittel | – | Fachperson beurteilt jeden Fall selbst; Analysewerkzeug gleicht Dokumente/Tabellen ab und markiert Abweichungen. |
| 4 | Standardkorrespondenz schreiben (Eingangsbestätigung, Unterlagen nachfordern) | 15 | E1 | ersetzend | <10 | P0 | hoch | – | Standardtexte aus Falldaten; Freigabe per Klick. |
| 5 | Telefonische Standardauskünfte an Versicherte (Fallstatus, fehlende Unterlagen) | 10 | E2 | ersetzend | 10-30 | P0 | tief | vertrauen | Voicebot mit Zugriff aufs Schadensystem; Spezialfälle werden weitergeleitet. *sicherheit_begruendung*: Qualität bei Schweizerdeutsch am Telefon wenig belegt; E0 ebenso plausibel. |
| 6 | Zahlungen nach Freigaberegeln auslösen | 5 | E0 | – | – | P1 (software) | hoch | – | Regelbasierte Dunkelverarbeitung im Schadensystem (klassische Software) — keine KI-Exposition. |
| 7 | Komplexe Fälle mit Gutachtern/Anwälten besprechen und entscheiden (Kulanz, Ablehnung) | 15 | E0 | – | – | P0 | hoch | – | Verhandlung, Ermessen, Verantwortung. |
| 8 | Aktennotizen und Falldokumentation verfassen | 5 | E1 | delegierend | 30-50 | P0 | mittel | – | KI formuliert die Notiz aus Stichworten; sie enthält eine fachliche Einschätzung, die die Person jedes Mal prüft. |
| 9 | Fallbesprechungen im Team | 5 | E0 | – | – | P0 | hoch | – | Präsenz/Abstimmung. |

→ E1 = 35 %, E2 = 40 % → **ζ = 0.75** (Score 7.5), β = 0.35 + 0.20 = 0.55;
Modus (ζ-gewichtet): ersetzend 60 % (45 % der Zeit), delegierend 27 % (20 %), unterstützend
13 % (10 %); Zeitersparnis = 0.20·0.80 + 0.15·0.60 + 0.10·0.60 + 0.15·0.95 + 0.10·0.80 +
0.05·0.60 = 0.5625 (Score 5.6); ersetzbare Zeit = 0.16 + 0.1425 + 0.08 = 0.3825;
P1 = 5 % (Score 0.5).

### 8.2 Physiotherapeut/in (ambulante Praxis) — gering exponiert

| # | Tätigkeit | % | Stufe | Modus | R | P | S | Hemmnis | Kurzbegründung |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Befund erheben: Anamnesegespräch, manuelle Untersuchung, Funktionstests | 15 | E0 | – | – | P0 | hoch | – | Körperliche Untersuchung, persönliches Gespräch. |
| 2 | Manuelle Therapie, Mobilisation, Massage durchführen | 35 | E0 | – | – | P0 | hoch | – | Physisch; keine Robotik in relevantem Umfang. |
| 3 | Übungen anleiten und Ausführung korrigieren | 20 | E0 | – | – | P0 | hoch | – | Präsenz, physisch. |
| 4 | Behandlungsplan erstellen und anpassen | 5 | E1 | unterstützend | 30-50 | P0 | mittel | – | Therapeutin plant und entscheidet je Patient selbst; LLM schlägt Übungsprogression vor. |
| 5 | Verlaufsdokumentation und Berichte an Ärzte/Versicherer verfassen | 10 | E2 | delegierend | 30-50 | P0 | mittel | regulatorisch | Diktat (auch Schweizerdeutsch, Einzelperson) → KI erstellt hochdeutschen Bericht; jeder Bericht fachlich geprüft. Hemmnis: Berufsgeheimnis/Datenschutz. |
| 6 | Heimprogramme und Patienteninformationen zusammenstellen | 5 | E1 | delegierend | 10-30 | P0 | mittel | – | KI erstellt Übungsblatt und Erklärtexte nach Vorgabe; Therapeutin prüft die patientenspezifische Auswahl. |
| 7 | Termine verwalten und Leistungen nach Tarif abrechnen | 5 | E0 | – | – | P1 (software) | mittel | – | Online-Terminbuchung und Tarifabrechnung der Praxissoftware sind klassische Software; kein LLM nötig. |
| 8 | Beratung zu Prävention/Ergonomie, Gespräch mit Angehörigen | 5 | E0 | – | – | P0 | hoch | – | Persönliche Beratung (E0 → kein Hemmnis). |

→ E1 = 10 %, E2 = 10 % → **ζ = 0.20** (Score 2.0), β = 0.10 + 0.05 = 0.15;
Modus (ζ-gewichtet): ersetzend 0 %, delegierend 75 % (15 % der Zeit), unterstützend 25 %
(5 %); Zeitersparnis = 0.05·0.60 + 0.10·0.60 + 0.05·0.80 = 0.13 (Score 1.3); ersetzbare
Zeit 0; P1 = 5 % (Score 0.5).

### 8.3 Maurer/in EFZ — sehr gering exponiert

| # | Tätigkeit | % | Stufe | Modus | R | P | S | Hemmnis | Kurzbegründung |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Mauerwerk aus Backstein/Kalksandstein erstellen | 30 | E0 | – | – | P0 | hoch | – | Physisch; Mauerroboter nur in Pilotprojekten. |
| 2 | Schalungen bauen, Armierung verlegen, betonieren | 25 | E0 | – | – | P0 | hoch | – | Physisch. |
| 3 | Baustelle einrichten, Material transportieren | 10 | E0 | – | – | P0 | hoch | – | Physisch. |
| 4 | Pläne lesen, Masse übertragen, einmessen | 10 | E0 | – | – | P0 | mittel | – | Zeit liegt im Messen vor Ort. |
| 5 | Verputzen, Abdichten, Reparaturen im Umbau | 10 | E0 | – | – | P0 | hoch | – | Physisch. |
| 6 | Material- und Mengenbedarf ermitteln | 5 | E1 | delegierend | 30-50 | P0 | tief | – | Massen eintippen, LLM rechnet; Maurer kontrolliert jedes Ergebnis. *sicherheit_begruendung*: unklar, ob das gegenüber Faustregeln wirklich 50 % spart; E0 ebenso plausibel. |
| 7 | Regierapporte mit Arbeitsbeschrieb und Material sowie Stunden ausfüllen | 5 | E2 | delegierend | 30-50 | P0 | mittel | – | Spracheingabe in Rapport-App erstellt den Rapport; Polier prüft jeden Rapport. Erkennung bei Lärm/Dialekt eingeschränkt → Sicherheit mittel (nicht Hemmnis), Korrekturaufwand in der Restzeit. |
| 8 | Absprachen mit Polier, Lernende anleiten | 5 | E0 | – | – | P0 | hoch | – | Präsenz. |

→ E1 = 5 %, E2 = 5 % → **ζ = 0.10** (Score 1.0), β = 0.05 + 0.025 = 0.075;
Modus (ζ-gewichtet): delegierend 100 % (10 % der Zeit); Zeitersparnis = 0.10·0.60 = 0.06
(Score 0.6); ersetzbare Zeit 0; P1 = 0 %.

---

## 9. Ausgabe

Genau **eine JSON-Datei pro Beruf**, gültig gegen `schema_v2_1.json`. Keine Kommentare, kein
Markdown in der Datei. `isco_code` und `beruf` exakt aus dem Input übernehmen.
Werte exakt so schreiben:

- `stufe`: `"E0"|"E1"|"E2"`;
- `modus`: `"ersetzend"|"delegierend"|"unterstützend"`, bei E0 `null`
  (der v2-Wert `"automatisierend"` ist **nicht mehr zulässig**);
- `restzeit_mensch`: `"<10"|"10-30"|"30-50"`, bei E0 `null`;
- `physisch_automatisierbar`: `"P0"|"P1"`; `p_art`: `"physisch"|"software"` bei P1, `null` bei P0;
- `sicherheit`: `"hoch"|"mittel"|"tief"`; `sicherheit_begruendung`: Text bei «tief», sonst `null`;
- `ch_hemmnis`: Liste aus `"regulatorisch"|"mehrsprachigkeit"|"vertrauen"`, bei E0 `[]`;
- `unsicherheit`: `"niedrig"|"mittel"|"hoch"`.

Beispiel (gekürzt auf 3 von mindestens 8 Tätigkeiten):

```json
{
  "isco_code": "7112",
  "beruf": "Maurer/in EFZ",
  "taetigkeiten": [
    {
      "name": "Mauerwerk aus Backstein und Kalksandstein erstellen",
      "zeitanteil_pct": 30,
      "stufe": "E0",
      "modus": null,
      "restzeit_mensch": null,
      "physisch_automatisierbar": "P0",
      "p_art": null,
      "sicherheit": "hoch",
      "sicherheit_begruendung": null,
      "ch_hemmnis": [],
      "begruendung": "Rein physische Tätigkeit auf der Baustelle; Mauerroboter gibt es nur in Pilotprojekten."
    },
    {
      "name": "Regierapporte mit Arbeitsbeschrieb, Material und Stunden ausfüllen",
      "zeitanteil_pct": 5,
      "stufe": "E2",
      "modus": "delegierend",
      "restzeit_mensch": "30-50",
      "physisch_automatisierbar": "P0",
      "p_art": null,
      "sicherheit": "mittel",
      "sicherheit_begruendung": null,
      "ch_hemmnis": [],
      "begruendung": "Spracheingabe in der Rapport-App erstellt den Rapport; der Polier prüft jeden Rapport. Dialekt und Lärm erhöhen den Korrekturaufwand."
    },
    {
      "name": "Material- und Mengenbedarf für Mauerwerk ermitteln",
      "zeitanteil_pct": 5,
      "stufe": "E1",
      "modus": "delegierend",
      "restzeit_mensch": "30-50",
      "physisch_automatisierbar": "P0",
      "p_art": null,
      "sicherheit": "tief",
      "sicherheit_begruendung": "Unklar, ob die Rechnung im Chat gegenüber Faustregeln wirklich 50 % spart; E0 ebenso plausibel.",
      "ch_hemmnis": [],
      "begruendung": "Massen aus dem Plan eintippen, LLM rechnet Steine, Mörtel und Zuschlag; Maurer kontrolliert jedes Ergebnis."
    }
  ],
  "unsicherheit": "niedrig",
  "kommentar": "Setting: Maurer/in in Bauunternehmung (Hochbau, Neubau und Umbau)."
}
```

## 10. Checkliste vor dem Speichern
- [ ] 8–12 Tätigkeiten, alle konkret (Verb + Objekt), keine Wissensgebiete.
- [ ] Zeitanteile ganze Zahlen, Summe = 100.
- [ ] Prüfreihenfolge eingehalten (physisch/Präsenz → E0; Chat-LLM reicht → E1; erst mit
      Werkzeugen/Integration/Multimodalität → E2; sonst E0); Prüfaufwand eingerechnet.
- [ ] Beste Einschätzung, **keine** Zweifelsregel nach unten; Unsicherheit in `sicherheit`.
- [ ] Nur generative KI für die Stufe E; klassische Software/Robotik nur im Feld P.
- [ ] Dialektqualität → Stufe/Sicherheit/Restzeit; `mehrsprachigkeit` nur organisatorisch/kulturell.
- [ ] Modus nur bei E1/E2; E0 → `null`. Ergebnis-Test (wer erstellt das Ergebnis?) und
      Prüf-Test (jede Ausgabe fachlich geprüft?) angewendet; «Prüfen jeder Ausgabe» allein
      macht nichts «unterstützend». Rechtlich vorgeschriebener Einzelfallentscheid →
      höchstens «delegierend».
- [ ] `restzeit_mensch` bei E1/E2 gesetzt (inkl. Spezifizieren, Steuern, Prüfen, Korrigieren,
      Freigeben, Ausnahmen), bei E0 `null`; Kombination Modus × Restzeit plausibel
      (nicht «ersetzend» + «30-50», nicht «unterstützend» + «<10»).
- [ ] P für jede Tätigkeit; bei P1 `p_art` gesetzt und Technik in der Begründung genannt.
- [ ] Bei `sicherheit` «tief» eine `sicherheit_begruendung`.
- [ ] Hemmnisse nur bei E1/E2 und nur, wo wesentlich; Stufe davon unabhängig.
- [ ] JSON gültig gegen `schema_v2_1.json` (Validierung mit `--schema v2_1`).
