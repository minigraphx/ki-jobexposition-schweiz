---
title: "Welche Schweizer Berufe trifft die KI-Welle? Warum wir endlich eigene Zahlen brauchen"
date: 2026-04-26
tags: [KI, Arbeitsmarkt, Schweiz, Datenanalyse, Automatisierung]
description: >
  Generative KI verändert die Arbeitswelt — doch fast alle bekannten Studien beziehen
  sich auf die USA. Ein Versuch, die Diskussion mit Schweizer Daten und Schweizer
  Rahmenbedingungen zu unterfüttern. Bewusst als Diskussionsgrundlage, nicht als Prognose.
---

# Welche Schweizer Berufe trifft die KI-Welle?

## Warum wir endlich eigene Zahlen brauchen

Seit dem Aufstieg generativer KI füllt sich die Debatte über die Zukunft der Arbeit
mit grossen Zahlen und noch grösseren Schlagzeilen: «300 Millionen Jobs gefährdet»,
«80 % der Berufe betroffen», «das Ende der Bürotätigkeit». Die Studien dahinter sind
oft seriös — aber sie haben ein gemeinsames Problem: Sie wurden für den **US-Arbeitsmarkt**
geschrieben.

Wer in der Schweiz arbeitet, lebt in einer anderen Wirtschaft. Andere Branchenstruktur.
Andere Lohnniveaus. Ein duales Bildungssystem mit EFZ und Höherer Berufsbildung, das in
keinem amerikanischen Datensatz auftaucht. Und trotzdem werden die US-Zahlen unverändert
in Schweizer Medien zitiert, als wäre der Coiffeur in Bern dieselbe statistische Einheit
wie ein *hairdresser* in Houston.

Genau hier setzt **[KI-Jobexposition Schweiz](https://huggingface.co/spaces/AndyWHV/ki-jobexposition-schweiz)**
an — ein offenes Tool, das für **204 Schweizer Berufe** einen nachvollziehbaren
Anhaltspunkt liefert, wie stark einzelne Tätigkeiten durch generative KI exponiert
sein *könnten*. Es ist ausdrücklich keine Prognose darüber, welche Jobs verschwinden
werden, sondern eine Diskussionsgrundlage.

---

## Die Problematik in vier Punkten

### 1. Niemand spricht über *konkrete* Berufe

Die meisten Diskussionen bleiben abstrakt: «kreative Berufe», «Wissensarbeit»,
«Routine-Tätigkeiten». Das ist analytisch wertlos für eine 24-jährige Kauffrau, die
sich fragt, ob sie sich umorientieren soll, oder für einen Berufsberater, der eine
Lehrstelle empfehlen will. Was diese Menschen brauchen, ist keine Schlagzeile — sie
brauchen eine Antwort auf die Frage: **«Wie sieht es bei *meinem* Beruf aus?»**

### 2. Die Schweizer Wirtschaft folgt nicht dem US-Drehbuch

Ein paar Beispiele, an denen sich die strukturellen Unterschiede zeigen:

- Der Schweizer **Finanzsektor** ist überdurchschnittlich gross und stark digitalisiert —
  was die KI-Exposition tendenziell erhöhen dürfte.
- Bei **ICT-Berufen** ist die häufige These «am stärksten betroffen» mindestens
  diskussionswürdig: Vieles deutet darauf hin, dass sie eher komplementär zur KI
  arbeiten als von ihr ersetzt zu werden — gesichert ist das nicht.
- Im **Gesundheitswesen** und in der **Pflege** dominiert in der Schweiz der demografische
  Druck. Personalmangel und Knappheit sprechen dafür, dass Automatisierung dort eher
  entlastet als verdrängt — die konkrete Wirkung bleibt offen.
- Das **EFZ-System** mit seiner engen Verzahnung von Theorie und Praxis dürfte einige
  Berufe abfedern, die in rein «kognitiven» US-Klassifikationen schlechter wegkommen.

Diese Unterschiede sollten kein Detail sein, das in der Diskussion verloren geht — sie
können das Bild für einzelne Berufsgruppen spürbar verschieben.

### 3. Die rechtlichen Rahmenbedingungen sind andere

KI-Einführung ist nicht nur eine technische Frage, sondern eine regulatorische. Und
auch hier gilt: Was in den USA möglich ist, ist in der Schweiz nicht automatisch erlaubt
— und umgekehrt.

- Die Schweiz übernimmt den **EU AI Act nicht direkt**, ist über ihre Lieferketten und
  Marktzugänge aber faktisch davon betroffen. Wie und wann der Bund eigene Regeln
  schafft, ist offen.
- Das **revidierte DSG** stellt für viele KI-Anwendungen — insbesondere für
  Profiling, automatisierte Einzelfallentscheidungen und Personaldaten — Anforderungen,
  die das Tempo der Einführung beeinflussen.
- In regulierten Branchen wie **Banken, Versicherungen und Gesundheitswesen** kommen
  sektorspezifische Aufsichtsregeln (FINMA, Swissmedic, kantonale Gesundheitsbehörden)
  hinzu, die den Einsatz generativer KI an klare Bedingungen knüpfen.
- Die Schweizer **Sozialpartnerschaft** und die Rolle der Gewerkschaften bei
  Gesamtarbeitsverträgen bedeuten, dass Automatisierungsschritte oft verhandelt
  werden — nicht im Stillen entschieden.

Ein Beruf mit hohem technischem Expositionsscore kann deshalb in der Schweiz langsamer,
anders oder gar nicht von KI verändert werden, weil rechtliche und sozialpartnerschaftliche
Leitplanken im Weg stehen. Das Tool kann diese Faktoren nicht modellieren — aber wer
seine Ergebnisse interpretiert, sollte sie mitdenken.

### 4. Vorhandene Studien sind nicht öffentlich nachvollziehbar

Wer auf eine McKinsey- oder OECD-Studie verweist, bekommt am Ende eine Grafik. Was er
nicht bekommt: die Daten, die Methodik im Detail, eine Möglichkeit, die Annahmen zu
hinterfragen. Genau diese Nachvollziehbarkeit ist aber die Voraussetzung dafür, dass
Politik, Bildungseinrichtungen und Betroffene fundierte Entscheidungen treffen können.

---

## Was das Tool macht

Die Plattform berechnet pro Beruf einen **Expositionsscore von 0 bis 10** auf Basis
einer öffentlich dokumentierten Methodik. Der Score misst, wie stark sich die
*Tätigkeiten* eines Berufs grundsätzlich für generative KI eignen — nicht, ob und
wann der Beruf tatsächlich verändert wird.

1. **Datengrundlage:** 204 Berufe aus der Schweizerischen Arbeitskräfteerhebung
   (BFS SAKE 2024), angereichert mit offiziellen Berufsbeschreibungen aus der
   europäischen ESCO-Klassifikation und Schweizer Lohndaten (BFS LSE 2022).

2. **Bewertung durch ein KI-Sprachmodell** (Claude Sonnet) entlang von fünf Kriterien:
   digitaler Output, Wiederholbarkeit, physische Präsenz, Kreativität und soziale
   Interaktion. Die Methodik orientiert sich an Andrej Karpathys und Michael Webbs
   Arbeit zur Automatisierungsexposition.

3. **Schweiz-spezifische Anpassungen:** Auf den Rohscore werden Korrekturen für
   Branche und Lohnniveau angewendet — basierend auf der Struktur der Schweizer
   Wirtschaft, nicht auf US-Mittelwerten.

4. **Visualisierung:** Eine Treemap zeigt alle 204 Berufe nach Beschäftigtenzahl und
   Risiko. Eine Matrix-Ansicht stellt Exposition gegen Anpassungsfähigkeit. Eine
   Berufssuche liefert für jeden einzelnen Beruf das volle Profil mit Begründung.

Wer will, kann jeden Score nachvollziehen, jeden Datensatz herunterladen und jeden
Schritt der Pipeline auf [GitHub](https://github.com/minigraphx/ki-jobexposition-schweiz)
einsehen.

---

## Was das Tool *nicht* ist

Damit kein falscher Eindruck entsteht: Diese Plattform ist **kein Orakel** und keine
Berufsempfehlung. Ein hoher Score bedeutet nicht, dass ein Beruf in fünf Jahren
verschwindet — er bedeutet, dass viele der heutigen Tätigkeiten technisch grundsätzlich
für KI-Unterstützung geeignet sind. Ob, wann und in welcher Form daraus tatsächlich
Veränderungen am Arbeitsmarkt werden, hängt von Regulierung, Recht, Tarifpartnern,
Kundennachfrage, Investitionsentscheiden und vielen weiteren Faktoren ab, die das
Modell nicht kennt.

Auch das KI-Modell, das hinter den Scores steht, hat blinde Flecken. Es kennt keine
Werkstatt von innen, hat noch nie eine Patientin betreut und versteht den Schweizer
Föderalismus nur über Textquellen. Die Scores sind deshalb mit Begründungen hinterlegt
— so können Leserinnen und Leser selbst prüfen, ob die Argumentation für ihren Beruf
trägt, und im Zweifel der eigenen Erfahrung mehr Gewicht geben als dem Wert.

Niemand sollte aufgrund eines Scores eine Berufswahl, eine Kündigung oder eine
Personalentscheidung treffen. Die Daten sind ein Einstieg in ein Gespräch, kein
Ersatz dafür.

---

## Für wen das Tool ein Ausgangspunkt sein kann

- **Berufstätige**, die für sich selbst eine Diskussionsgrundlage suchen, wie sich
  ihr Tätigkeitsfeld verändern könnte.
- **Berufsberater:innen und Lehrpersonen**, die Jugendlichen ergänzendes Material zur
  Berufswahl an die Hand geben wollen — neben den etablierten Quellen.
- **HR und Strategie**, die ein zusätzliches Datenpuzzlestück für Personalplanung
  und Weiterbildung suchen.
- **Politik und Verbände**, die für ihre Diskussionen über Strukturwandel und
  Weiterbildung neben qualitativen Einschätzungen auch quantitative Anhaltspunkte
  brauchen.
- **Journalist:innen und Forschende**, die für ihre Beiträge nachvollziehbare
  Schweizer Zahlen suchen — inklusive der Möglichkeit, der Methodik zu widersprechen.

---

## Ein Anfang, kein Endpunkt

KI-Jobexposition Schweiz ist ein **offenes Projekt** und ausdrücklich ein Versuch,
keine fertige Antwort. Die Daten und die Methodik sind unter MIT-Lizenz frei
verfügbar, der Code ist öffentlich, jeder Score wird mit Begründung publiziert.
Wo die Methodik Schwächen hat, sollen sie sichtbar sein — Kritik, Korrekturvorschläge
und Branchen-Expertise sind ausdrücklich willkommen, über GitHub-Issues oder direkt
per Mail.

Wir werden uns in den nächsten Jahren intensiv mit der Frage beschäftigen müssen, was
generative KI mit unserem Arbeitsmarkt macht. Diese Diskussion verdient eine bessere
Datenbasis als US-Schlagzeilen — und sie verdient auch ehrlichen Umgang mit dem, was
diese Daten *nicht* leisten können.

**👉 [Tool öffnen](https://huggingface.co/spaces/AndyWHV/ki-jobexposition-schweiz)**
&nbsp;·&nbsp;
**[Code & Methodik auf GitHub](https://github.com/minigraphx/ki-jobexposition-schweiz)**
