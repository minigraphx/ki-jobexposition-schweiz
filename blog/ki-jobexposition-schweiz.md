---
title: "Welche Schweizer Berufe trifft die KI-Welle? Warum wir endlich eigene Zahlen brauchen"
date: 2026-04-26
tags: [KI, Arbeitsmarkt, Schweiz, Datenanalyse, Automatisierung]
description: >
  Generative KI verändert die Arbeitswelt schneller, als die Statistik nachkommt — und fast
  alle bekannten Studien beziehen sich auf die USA. Höchste Zeit für eine datengetriebene
  Analyse, die den Schweizer Arbeitsmarkt ernst nimmt.
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
an — ein offenes Tool, das für **204 Schweizer Berufe** transparent zeigt, wie stark sie
durch generative KI exponiert sind.

---

## Die Problematik in drei Punkten

### 1. Niemand spricht über *konkrete* Berufe

Die meisten Diskussionen bleiben abstrakt: «kreative Berufe», «Wissensarbeit»,
«Routine-Tätigkeiten». Das ist analytisch wertlos für eine 24-jährige Kauffrau, die
sich fragt, ob sie sich umorientieren soll, oder für einen Berufsberater, der eine
Lehrstelle empfehlen will. Was diese Menschen brauchen, ist keine Schlagzeile — sie
brauchen eine Antwort auf die Frage: **«Wie sieht es bei *meinem* Beruf aus?»**

### 2. Die Schweizer Wirtschaft folgt nicht dem US-Drehbuch

Ein paar Beispiele, die die nationalen Unterschiede deutlich machen:

- Der Schweizer **Finanzsektor** ist überdurchschnittlich gross und überdurchschnittlich
  digital — was die KI-Exposition tendenziell erhöht.
- **ICT-Berufe** sind in der Schweiz nicht «am stärksten betroffen», wie oft behauptet —
  sie sind selbst die Treiber der Automatisierung und werden eher komplementär als
  ersetzend.
- Im **Gesundheitswesen** und in der **Pflege** schlägt der demografische Druck stärker
  als die Automatisierung — hier herrscht Personalmangel, nicht Überfluss.
- Das **EFZ-System** mit seiner engen Verzahnung von Theorie und Praxis schützt viele
  Berufe, die in den USA als rein «kognitiv» klassifiziert würden.

Diese Differenzen sind nicht kosmetisch. Sie verändern das Ranking ganzer Berufsgruppen.

### 3. Vorhandene Studien sind nicht öffentlich nachvollziehbar

Wer auf eine McKinsey- oder OECD-Studie verweist, bekommt am Ende eine Grafik. Was er
nicht bekommt: die Daten, die Methodik im Detail, eine Möglichkeit, die Annahmen zu
hinterfragen. Genau diese Nachvollziehbarkeit ist aber die Voraussetzung dafür, dass
Politik, Bildungseinrichtungen und Betroffene fundierte Entscheidungen treffen können.

---

## Was das Tool macht

Die Plattform berechnet pro Beruf einen **Expositionsscore von 0 bis 10** — und zwar
auf Basis einer öffentlich dokumentierten Methodik:

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

Damit kein falscher Eindruck entsteht: Diese Plattform ist **kein Orakel**. Ein hoher
Score bedeutet nicht, dass ein Beruf in fünf Jahren verschwindet — er bedeutet, dass
ein grosser Anteil der heutigen Tätigkeiten technisch automatisierbar ist. Ob diese
Automatisierung tatsächlich passiert, hängt von Regulierung, Tarifpartnern, Kundennachfrage,
Arbeitsmarktdynamik und vielen weiteren Faktoren ab.

Auch das KI-Modell, das hinter den Scores steht, hat blinde Flecken. Es kennt keine
Werkstatt von innen, hat noch nie eine Patientin betreut und versteht den Schweizer
Föderalismus nur über Textquellen. Deshalb sind alle Ergebnisse mit konkreten Begründungen
hinterlegt — damit Leserinnen und Leser selbst beurteilen können, ob die Argumentation
trägt.

---

## Für wen das Tool gemacht ist

- **Berufstätige**, die wissen wollen, wie sich ihr Tätigkeitsfeld verändern könnte.
- **Berufsberater:innen und Lehrpersonen**, die Jugendliche bei der Berufswahl begleiten.
- **HR und Strategie**, die Personalplanung jenseits von Schlagzeilen betreiben wollen.
- **Politik und Verbände**, die Weiterbildung, Strukturwandel und Sozialversicherungen
  evidenzbasiert gestalten müssen.
- **Journalist:innen und Forschende**, die für ihre Beiträge nachvollziehbare
  Schweizer Zahlen brauchen.

---

## Ein Anfang, kein Endpunkt

KI-Jobexposition Schweiz ist ein **offenes Projekt**. Die Daten und die Methodik
sind unter MIT-Lizenz frei verfügbar, der Code ist öffentlich, jeder Score wird mit
Begründung publiziert. Kritik, Korrekturvorschläge und Branchen-Expertise sind
ausdrücklich willkommen — über GitHub-Issues oder direkt per Mail.

Wir werden uns in den nächsten Jahren intensiv mit der Frage beschäftigen müssen, was
generative KI mit unserem Arbeitsmarkt macht. Diese Diskussion verdient bessere
Datenbasis als US-Schlagzeilen.

**👉 [Tool öffnen](https://huggingface.co/spaces/AndyWHV/ki-jobexposition-schweiz)**
&nbsp;·&nbsp;
**[Code & Methodik auf GitHub](https://github.com/minigraphx/ki-jobexposition-schweiz)**
