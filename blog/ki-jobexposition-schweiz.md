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
mit grossen Zahlen und noch grösseren Schlagzeilen. Bei näherer Betrachtung sind
diese Zahlen meist präziser — und vorsichtiger — formuliert, als sie in den
Medien ankommen:

- Goldman Sachs schreibt von «bis zu **300 Millionen weltweit *exponierten*
  Vollzeitstellen**» — nicht von 300 Millionen wegfallenden Jobs.[^goldman]
- Eloundou et al. (OpenAI / University of Pennsylvania) zeigen, dass rund
  **80 % der US-Beschäftigten in mindestens 10 % ihrer Aufgaben** durch grosse
  Sprachmodelle berührt sein könnten — also kein «80 % der Berufe gehen weg».[^gptsaregpts]
- McKinsey schätzt, dass bis 2030 **rund 30 % der heute geleisteten Arbeitsstunden
  in den USA automatisierbar sein könnten** — wiederum mit grosser Spannweite.[^mckinsey]

Was diesen Studien gemeinsam ist: Sie wurden für den **US-Arbeitsmarkt** gerechnet.

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

- Die Schweiz übernimmt den **[EU AI Act][eu-ai-act]** (Verordnung 2024/1689,
  in Kraft seit 1. August 2024) nicht direkt — ist über Lieferketten und
  Marktzugang aber faktisch davon betroffen. Der Bundesrat hat eine eigene
  KI-Regulierung 2025 in Auftrag gegeben; das konkrete Schweizer Regelwerk steht
  noch aus.[^bundesrat-ki]
- Das **[revidierte Datenschutzgesetz][revdsg]** (revDSG, in Kraft seit 1. September
  2023) stellt für viele KI-Anwendungen Anforderungen — insbesondere Art. 5 lit. f/g
  zum Profiling und Art. 21 zur automatisierten Einzelentscheidung. Das beeinflusst
  Tempo und Form der Einführung.
- In regulierten Branchen kommen sektorspezifische Aufsichtsregeln hinzu: die
  [FINMA][finma] für Finanzdienstleister, [Swissmedic][swissmedic] für Medizinprodukte,
  und die kantonalen Gesundheitsbehörden im Spitalwesen.
- Die Schweizer **Sozialpartnerschaft** und Gesamtarbeitsverträge führen dazu, dass
  Automatisierungsschritte in vielen Branchen verhandelt und nicht einseitig
  entschieden werden.[^seco-sozialpartnerschaft]

Ein Beruf mit hohem technischem Expositionsscore kann deshalb in der Schweiz langsamer,
anders oder gar nicht von KI verändert werden, weil rechtliche und sozialpartnerschaftliche
Leitplanken im Weg stehen. Das Tool kann diese Faktoren nicht modellieren — aber wer
seine Ergebnisse interpretiert, sollte sie mitdenken.

### 4. Detaildaten und Reproduzierbarkeit fehlen häufig

McKinsey, OECD und das ILO-Arbeitsmarktteam dokumentieren ihre Methodik in der Regel
in technischen Anhängen oder Working Papers — das ist anzuerkennen.[^mckinsey] [^oecd]
[^ilo] Was in der Praxis aber häufig fehlt, ist die Ebene darunter: die **Bewertung
pro einzelner Berufsgruppe** in maschinenlesbarer Form, die genauen Coding-Entscheide
und reproduzierbarer Code. Damit bleibt es schwierig, einen einzelnen Beruf
nachzurechnen oder die Annahmen für den eigenen Kontext zu hinterfragen — gerade
diese Ebene ist es aber, die für Berufsberatung, Branchenverbände und Betroffene
relevant ist.

---

## Was das Tool macht

Die Plattform berechnet pro Beruf einen **Expositionsscore von 0 bis 10** auf Basis
einer öffentlich dokumentierten Methodik. Der Score misst, wie stark sich die
*Tätigkeiten* eines Berufs grundsätzlich für generative KI eignen — nicht, ob und
wann der Beruf tatsächlich verändert wird.

1. **Datengrundlage:** 204 Berufe aus der Schweizerischen Arbeitskräfteerhebung
   ([BFS SAKE 2024][bfs-sake]), angereichert mit offiziellen Berufsbeschreibungen
   aus der europäischen [ESCO-Klassifikation][esco] und Schweizer Lohndaten
   ([BFS LSE 2022][bfs-lse]).

2. **Bewertung durch ein KI-Sprachmodell** (Claude Sonnet) entlang von fünf Kriterien:
   digitaler Output, Wiederholbarkeit, physische Präsenz, Kreativität und soziale
   Interaktion. Die Auswahl der Kriterien orientiert sich an Michael Webbs Arbeit
   zur Automatisierungsexposition über Patente[^webb] sowie an Andrej Karpathys
   öffentlichen Analysen, welche Aufgabentypen sich für grosse Sprachmodelle
   eignen.[^karpathy]

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

---

## Quellen und weiterführende Literatur

### Internationale Studien

[^goldman]: Hatzius, J., Briggs, J., Kodnani, D., Pierdomenico, G. (2023):
    *The Potentially Large Effects of Artificial Intelligence on Economic Growth.*
    Goldman Sachs Economics Research, 26. März 2023. — Kernaussage:
    «up to 300 million full-time jobs globally could be exposed to automation by AI».
    Exposition ≠ Wegfall.

[^gptsaregpts]: Eloundou, T., Manning, S., Mishkin, P., Rock, D. (2023):
    *GPTs are GPTs: An Early Look at the Labor Market Impact Potential of Large
    Language Models.* arXiv:2303.10130. <https://arxiv.org/abs/2303.10130> —
    Kernbefund: «around 80 % of the U.S. workforce could have at least 10 % of
    their work tasks affected by the introduction of LLMs».

[^mckinsey]: McKinsey Global Institute (2023): *Generative AI and the future of
    work in America.* Juli 2023. <https://www.mckinsey.com/mgi> — schätzt, dass
    bis 2030 rund 30 % der heute geleisteten Arbeitsstunden in den USA
    automatisierbar sein könnten. Methodik wird im technischen Anhang beschrieben.

[^oecd]: OECD (2023): *OECD Employment Outlook 2023 — Artificial Intelligence
    and the Labour Market.* <https://www.oecd.org/employment-outlook/> — sowie
    Nedelkoska, L., Quintini, G. (2018): *Automation, skills use and training.*
    OECD Social, Employment and Migration Working Papers No. 202.

[^ilo]: International Labour Organization (2023): *Generative AI and Jobs: A
    global analysis of potential effects on job quantity and quality.*
    ILO Working Paper 96. <https://www.ilo.org/publications>

[^webb]: Webb, M. (2020): *The Impact of Artificial Intelligence on the Labor
    Market.* Stanford Working Paper, SSRN.
    <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3482150>

[^karpathy]: Andrej Karpathy: öffentliche Vorträge und Essays zur Frage,
    welche Aufgabentypen für grosse Sprachmodelle geeignet sind, u. a.
    «Intro to Large Language Models» (November 2023). Eine begutachtete
    akademische Publikation existiert hierzu nicht — das Tool übernimmt die
    strukturierende Idee, nicht eine peer-reviewed Methodik.

### Rechtliche Grundlagen

[^bundesrat-ki]: Bundesrat (2025): Auftrag für eine sektorspezifische KI-
    Regulierung in der Schweiz, basierend auf dem Bericht «Übersicht KI-
    Regulierungsansätze und mögliches Vorgehen für die Schweiz» (BAKOM, 2024).
    <https://www.bakom.admin.ch>

[^seco-sozialpartnerschaft]: SECO — Staatssekretariat für Wirtschaft:
    *Sozialpartnerschaft in der Schweiz.* <https://www.seco.admin.ch>

### Schweizer Datenquellen

[bfs-sake]: https://www.bfs.admin.ch/bfs/de/home/statistiken/arbeit-erwerb/erhebungen/sake.html
    "Schweizerische Arbeitskräfteerhebung (SAKE), Bundesamt für Statistik"
[bfs-lse]: https://www.bfs.admin.ch/bfs/de/home/statistiken/arbeit-erwerb/loehne-erwerbseinkommen-arbeitskosten/lohnniveau-schweiz/lohnstrukturerhebung.html
    "Lohnstrukturerhebung (LSE) 2022, Bundesamt für Statistik"
[esco]: https://esco.ec.europa.eu/de
    "European Skills, Competences, Qualifications and Occupations, Europäische Kommission"

### Weitere Verweise im Text

[eu-ai-act]: https://eur-lex.europa.eu/eli/reg/2024/1689/oj
    "Verordnung (EU) 2024/1689 – AI Act"
[revdsg]: https://www.fedlex.admin.ch/eli/cc/2022/491/de
    "Bundesgesetz über den Datenschutz (revDSG), in Kraft seit 1. September 2023"
[finma]: https://www.finma.ch
    "Eidgenössische Finanzmarktaufsicht FINMA"
[swissmedic]: https://www.swissmedic.ch
    "Swissmedic – Schweizerisches Heilmittelinstitut"

### Hinweis zu Interpretationen

Mehrere Aussagen zu Schweizer Spezifika — etwa zur Wirkung des EFZ-Systems, zur
ICT-Komplementarität oder zur demografischen Lage in Pflege und Gesundheitswesen —
sind plausible Interpretationen der allgemein verfügbaren Datenlage (BFS, OBSAN,
SECO), aber nicht Ergebnis einer eigenen empirischen Untersuchung. Wer einzelne
Punkte vertieft prüfen will, findet bei den jeweiligen Bundesämtern detaillierte
Statistiken.
