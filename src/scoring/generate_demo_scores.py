"""
Generiert Demo-Scores basierend auf Forschungsliteratur (Karpathy, Brookings, GovAI).
Wird für Entwicklung/Testing verwendet bis echtes Claude-API-Scoring läuft.

Scores basieren auf:
- Karpathy (2024): US-Berufs-Scores als Referenz
- Brookings/GovAI (2024): Exposition + Anpassungsfähigkeit
- WEF Future of Jobs (2025)
- Eigene Einschätzung für CH-spezifische Berufe
"""

import pandas as pd
from pathlib import Path

PROCESSED_PATH = Path(__file__).parent.parent.parent / "data" / "processed"

# fmt: off
# (beruf_fragment, score_gesamt, adaptabilitaet, haupt_risiko, zeitrahmen, begruendung_kurz)
SCORE_LOOKUP = {
    # Finanzen / sehr hoch exponiert
    "Buchhalter": (8.5, 4.5, "Automatische Buchführung (SAP AI, DATEV)", "2-4 Jahre",
        "Buchhalterische Routineaufgaben sind hochgradig strukturiert und regelbasiert. KI-Tools übernehmen bereits heute wesentliche Teile der Belegerfassung und -prüfung. Schweizer Spezifika (MWST, OR) sind lernbar."),
    "Finanzanalyst": (7.8, 6.5, "KI-gestützte Marktanalyse und Reportgenerierung", "3-5 Jahre",
        "Standardisierte Analysen und Reports sind stark automatisierbar. Komplexe Kundenberatung und strategische Einschätzungen bleiben beim Menschen. Am Bankplatz Schweiz hoher Automatisierungsdruck durch Kosteneffizienz."),
    "Sachbearbeiter/in Buchhaltung": (8.2, 3.8, "Automatische Belegverarbeitung und Abstimmung", "1-3 Jahre",
        "Hohe Exposition durch sehr strukturierte, regelbasierte Tätigkeiten. Tiefe Anpassungsfähigkeit da oft enge Spezialisierung. In CH-KMU verzögerter Wandel durch Investitionszurückhaltung."),
    "Bankkaufmann": (7.5, 5.5, "Beratungs-KI, automatisierte Kreditvergabe", "3-5 Jahre",
        "Standardprodukte und Routineberatung werden zunehmend digitalisiert. Komplexe Vermögensberatung und Kundenbeziehung bleiben. Schweizer Bankensektor investiert stark in Automatisierung."),
    "Versicherungskaufmann": (7.8, 4.8, "Automatisierte Schadensabwicklung und Risikobewertung", "2-4 Jahre",
        "Schadenmeldungen, Standardverträge und Risikobewertungen sind gut automatisierbar. Swiss-Re und Zurich investieren massiv in KI."),
    "Treuhänder": (7.0, 6.0, "KI-Steuerplanung und automatisierte Abschlüsse", "3-5 Jahre",
        "Standardaufgaben wie Steuerdeklarationen und Jahresabschlüsse werden zunehmend KI-unterstützt. Beratungsleistung und Kundenvertrauen bleiben wichtig."),
    "Compliance Officer": (6.5, 7.0, "Automatisiertes Transaktionsmonitoring und Regelprüfung", "3-6 Jahre",
        "Regelüberprüfungen und Monitoring stark automatisierbar, aber regulatorische Interpretation und Verantwortung bleiben beim Menschen. Hohe Anpassungsfähigkeit durch Bildungsniveau."),
    "Wirtschaftsprüfer": (7.2, 6.5, "KI-gestützte Prüfungstools und Stichprobenanalyse", "3-5 Jahre",
        "Stichprobenprüfungen und Anomalieerkennung werden durch KI massiv effizienter. Urteilsvermögen, Verantwortung und Regulierung schützen den Kern des Berufs."),
    "Vermögensverwalter": (6.8, 7.2, "Robo-Advisory für Standardportfolios", "3-6 Jahre",
        "Mass-Customization durch Robo-Advisor, aber UHNWI-Beratung (Ultra High Net Worth) bleibt stark menschlich. CH-Finanzplatz mit hohem Wohlstandsniveau bietet Puffer."),
    "Steuerberater": (7.0, 6.5, "KI-Steueroptimierung und automatisierte Deklarationen", "3-5 Jahre",
        "Standarddeklarationen werden weitgehend automatisiert. Komplexe internationale Steuerplanung und Beratung bei Unternehmensstrukturierung bleiben hochwertig."),
    "Controller": (7.5, 6.0, "Automatisiertes Reporting und Abweichungsanalyse", "2-4 Jahre",
        "Standardberichte, Dashboards und Abweichungsanalysen sind gut automatisierbar. Strategische Steuerung und Geschäftspartner-Rolle bleiben menschlich."),
    "Statistiker": (6.0, 8.5, "Automatisierte statistische Analysen", "4-7 Jahre",
        "Sehr hohe Anpassungsfähigkeit durch MINT-Ausbildung. KI unterstützt, ersetzt aber nicht die methodische Kompetenz und Interpretation komplexer Daten."),

    # Verwaltung / mittel-hoch exponiert
    "Sachbearbeiter/in öff. Verwaltung": (7.2, 3.5, "Automatisierte Antragsverarbeitung und Entscheidungen", "3-6 Jahre",
        "Standardisierte Verwaltungsakte sind gut automatisierbar. CH-öffentliche Verwaltung digitalisiert langsam aber stetig (eGov). Mitbestimmung und Beamtenrecht verlangsamen Wandel."),
    "Sekretär/in": (7.8, 4.2, "KI-Terminplanung, E-Mail-Management und Dokumentenverwaltung", "1-3 Jahre",
        "Typische Assistenzaufgaben sind sehr gut durch KI automatisierbar. Kritische Gruppe: hohe Exposition, mehrheitlich Frauen, mittlere Anpassungsfähigkeit."),
    "Sachbearbeiter/in HR": (6.8, 5.5, "Automatisierte CV-Selektion und Onboarding", "3-5 Jahre",
        "Administrative HR-Aufgaben stark automatisierbar. Beziehungsaspekte und kulturelle Passung bleiben menschlich. KI kann Bias verstärken – regulatorischer Rahmen in CH relevant."),
    "Posthalter/in": (8.0, 3.0, "Automatisierte Paketsortierung und Zustellung", "2-4 Jahre",
        "Hochgradig strukturierte, wiederholbare Tätigkeiten. Post CH investiert massiv in Automatisierung. Tiefe Anpassungsfähigkeit durch begrenzte Qualifikation."),

    # ICT / hoch exponiert aber sehr anpassungsfähig
    "Softwareentwickler": (5.5, 9.2, "KI-Codegenerierung (GitHub Copilot, Cursor)", "laufend",
        "Paradox: Softwareentwickler sind stark von KI betroffen, aber auch am anpassungsfähigsten. Fokus verschiebt sich von Code schreiben zu Architektur, Prompt Engineering und Qualitätssicherung."),
    "Informatiker/in EFZ": (5.8, 8.0, "KI-Codegenerierung und automatisiertes Testing", "laufend",
        "KI verändert die Tätigkeit fundamental, macht aber nicht obsolet. Umschulung und Upskilling in KI-nahe Bereiche gut möglich."),
    "IT-Projektleiter": (5.0, 8.5, "KI-unterstütztes Projektmanagement", "4-6 Jahre",
        "Führung, Stakeholdermanagement und Komplexitätsbewältigung schützen diesen Beruf. KI übernimmt administrative Projektaufgaben."),
    "Data Scientist": (5.2, 9.0, "Automatisierte ML-Pipelines (AutoML)", "4-7 Jahre",
        "AutoML vereinfacht Standard-Analysen, aber Domänenexpertise, Problemdefinition und kritische Beurteilung bleiben hochwertig. Sehr gute Anpassungsfähigkeit."),
    "IT-Sicherheitsspezialist": (4.2, 9.0, "KI-gestützte Angriffe erfordern KI-Abwehr", "laufend",
        "Cybersicherheit ist ein Wachstumsfeld – KI erhöht Bedrohungen und schafft gleichzeitig neue Verteidigungstools. Stark steigende Nachfrage in CH."),
    "Systemadministrator": (5.5, 8.0, "Automatisiertes IT-Ops und AIOps", "3-5 Jahre",
        "Routinewartung und Monitoring werden automatisiert. Architektur und Sicherheit bleiben. CloudOps wächst."),
    "ICT-Supporter": (6.5, 7.0, "KI-Chatbots für L1/L2 Support", "2-4 Jahre",
        "First-Level-Support wird weitgehend automatisiert. Komplexe technische Probleme und persönlicher Service bleiben."),
    "UX/UI Designer": (5.0, 8.5, "KI-Design-Tools (Figma AI, Midjourney)", "3-5 Jahre",
        "KI beschleunigt Designprozesse stark. Menschliches Urteil für Nutzererfahrung und Markenidentität bleibt essenziell. Sehr hohe Anpassungsfähigkeit."),
    "Netzwerkingenieur": (5.0, 8.5, "Software-defined Networking und AIOps", "3-6 Jahre",
        "Netzwerkautomatisierung schreitet voran, aber Architektur und Sicherheit bleiben komplex. Gute Anpassungsfähigkeit."),
    "Telematiker/in EFZ": (5.8, 7.0, "Automatisierte Netzwerküberwachung", "3-5 Jahre",
        "Installation und Wartung physischer Infrastruktur bleibt. Konfiguration und Monitoring werden zunehmend automatisiert."),

    # Gesundheit / tief bis mittel exponiert
    "Pflegefachperson": (3.2, 6.5, "KI-Diagnoseunterstützung, Pflegeroboter", "6-10 Jahre",
        "Physische Pflege, Empathie und Patientenbeziehung sind schwer automatisierbar. KI unterstützt Dokumentation und Diagnose. Massiver Fachkräftemangel in CH schützt Beschäftigung."),
    "Arzt/Ärztin": (4.5, 8.5, "KI-Bilddiagnostik, automatisierte Anamnese", "5-10 Jahre",
        "KI übernimmt Bildauswertung und Dokumentation. Diagnose, Therapieentscheidung und Arzt-Patienten-Beziehung bleiben zentral. Sehr hohe Anpassungsfähigkeit durch Bildungsniveau."),
    "Fachperson Gesundheit": (3.5, 5.5, "Pflegedokumentation, Pflegeroboter", "6-10 Jahre",
        "Direktpflege kaum automatisierbar. Dokumentationsaufgaben werden durch KI vereinfacht. Fachkräftemangel in CH ist akut."),
    "Zahnarzt": (3.8, 8.0, "Roboterchirurgie, KI-Diagnose", "7-12 Jahre",
        "Physische Feinarbeit und Patientenvertrauen schützen. KI-Diagnostik (Röntgenauswertung) bereits im Einsatz."),
    "Apotheker": (5.5, 7.5, "Automatisierte Medikamentenausgabe, KI-Beratung", "4-7 Jahre",
        "Medikamentenabgabe wird automatisiert, aber Beratung und Interaktionsprüfung bei komplexen Fällen bleibt wichtig."),
    "Physiotherapeut": (2.8, 7.0, "KI-Bewegungsanalyse, Therapieroboter", "7-12 Jahre",
        "Physische Präsenz und manueller Kontakt nicht automatisierbar. KI unterstützt Diagnose und Therapieplanung. Tiefer Score, sehr sicher."),
    "Arztpraxisassistent": (6.5, 4.8, "Terminmanagement, automatisierte Triage, Dokumentation", "2-4 Jahre",
        "Administrative Aufgaben stark automatisierbar. Direkte Patientenbetreuung schützt. Kritische Gruppe: v.a. Frauen, mittlere Anpassungsfähigkeit."),
    "Spitex-Mitarbeiter": (2.5, 4.5, "Pflegeroboter, Fernmonitoring", "8-15 Jahre",
        "Häusliche Pflege erfordert physische Präsenz, Flexibilität und menschliche Wärme. Langfristig Assistenztechnologien möglich, aber nicht in naher Zukunft."),
    "Psychologe": (3.5, 8.0, "KI-Therapieunterstützung, Chatbots für psychische Gesundheit", "6-10 Jahre",
        "Menschliche Beziehung und Empathie sind Kern der Therapie. KI-Apps für leichte Fälle, aber Fachtherapie bleibt menschlich. Steigende Nachfrage in CH."),
    "Pflegeassistent": (3.8, 3.5, "Pflegeroboter für Routinetätigkeiten", "7-12 Jahre",
        "Körperliche Pflege und menschliche Zuwendung schützen. Tiefe Anpassungsfähigkeit durch geringe Qualifikation ist ein Risikofaktor langfristig."),

    # Bildung / tief bis mittel exponiert
    "Primarlehrer": (3.8, 7.0, "KI-Tutoring, personalisiertes Lernen", "5-8 Jahre",
        "Soziale und emotionale Entwicklung von Kindern erfordert menschliche Lehrpersonen. KI wird Unterrichtsvorbereitung und Differenzierung unterstützen. Hohe gesellschaftliche Wertschätzung."),
    "Kindergärtnerin": (2.2, 6.5, "KI in Frühförderung", "8-15 Jahre",
        "Frühkindliche Betreuung ist zutiefst menschlich. Kaum automatisierbar. Sehr sicherer Beruf."),
    "Sekundarlehrer": (4.0, 7.5, "KI-Tutoring, automatisierte Bewertung", "5-8 Jahre",
        "Wissensvermittlung wird durch KI ergänzt, aber pädagogische Beziehung und Klassenführung bleiben menschlich."),
    "Gymnasiallehrer": (4.2, 8.0, "KI-Tutoring, Forschungsunterstützung", "5-8 Jahre",
        "Höherer Anteil an Wissensvermittlung macht Exposition etwas höher, aber Anpassungsfähigkeit durch Fachexpertise sehr hoch."),
    "Berufsschullehrer": (4.5, 8.0, "Lernplattformen, KI-Tutoring", "4-7 Jahre",
        "Praktische Ausbildungsanteile schützen. Theoretischer Unterricht wird durch KI ergänzt."),
    "Hochschuldozent": (4.8, 9.0, "KI-Forschungsassistenz, automatisierte Bewertung", "4-7 Jahre",
        "Forschung, kritisches Denken und akademische Gemeinschaft schützen. Sehr hohe Anpassungsfähigkeit."),

    # Detailhandel / mittel-hoch exponiert
    "Detailhandelsfachmann": (6.8, 5.2, "Selbstbedienungskassen, KI-Beratung, E-Commerce", "2-4 Jahre",
        "Kassiertätigkeiten werden automatisiert, Beratung bleibt. E-Commerce-Druck auf stationären Handel. CH-Lohnstruktur macht Automatisierung attraktiv."),
    "Kassierer": (8.5, 2.5, "Selbstbedienungskassen und kassenlose Läden", "1-3 Jahre",
        "Höchste Exposition unter Dienstleistungsberufen. Amazon Go-Konzept skaliert. Sehr tiefe Anpassungsfähigkeit, da eng spezialisiert. Migros/Coop investieren in Self-Checkout."),
    "Verkäufer/in (ohne Ausbildung)": (7.5, 3.0, "Automatisierter Checkout, KI-Empfehlung", "2-4 Jahre",
        "Routineaufgaben im Verkauf werden automatisiert. Niedrige Qualifikation erschwert Umschulung. Beratungsintensiver Verkauf schützt mehr."),
    "Filialleiter": (5.5, 6.5, "KI-Inventarmanagement, automatisiertes Reporting", "3-6 Jahre",
        "Führungsaufgaben und Personalverantwortung schützen. Administrative Aufgaben werden KI-unterstützt."),
    "Drogist": (5.8, 6.0, "Automatisierte Beratungstools, Online-Apotheken", "4-7 Jahre",
        "Fachberatung schützt, aber Online-Konkurrenz und KI-Beratungstools erhöhen Druck."),

    # Gastronomie / mittel exponiert
    "Koch": (4.5, 5.5, "Kochroboter, automatisierte Küchen", "5-8 Jahre",
        "Kreatives Kochen und Qualitätsküche sind schwer automatisierbar. Fast Food und Standardküche sind exponierter. CH-Gastronomie mit hohem Qualitätsanspruch bietet Puffer."),
    "Restaurantfachmann": (5.2, 4.8, "Service-Roboter, digitale Bestellung", "4-7 Jahre",
        "Direkten Kundenkontakt und persönlichen Service können Roboter nur eingeschränkt ersetzen. In CH weniger Automatisierungsdruck als in USA."),
    "Küchenhilfe": (7.5, 2.2, "Küchenautomation für einfache Aufgaben", "3-6 Jahre",
        "Einfache, repetitive Küchenaufgaben gut automatisierbar. Tiefe Qualifikation erschwert Umschulung erheblich."),
    "Servicemitarbeiter": (5.5, 4.5, "Service-Roboter, Tablet-Bestellung", "4-7 Jahre",
        "Persönlicher Service und menschliche Atmosphäre schützen in der Qualitätsgastronomie. Kaffeehäuser und Hotels weniger exponiert als Fast Food."),
    "Hotelfachmann/-frau EFZ": (5.0, 6.0, "KI-Concierge, automatisiertes Check-in", "4-7 Jahre",
        "Gastfreundschaft und persönliche Betreuung schützen. Administrative Aufgaben werden KI-unterstützt."),

    # Bau & Handwerk / tief exponiert
    "Maurer": (2.5, 4.5, "Mauerroboter (SAM100), 3D-Betondruck", "8-15 Jahre",
        "Physische Arbeit in variablen Umgebungen schützt. Fachkräftemangel in CH ist akut. Langfristig Baurobotik möglich."),
    "Elektriker": (2.8, 5.5, "Automatisiertes Installationsassistenzsystem", "8-15 Jahre",
        "Handwerkliche Feinarbeit und Sicherheitsverantwortung schützen. Steigende Nachfrage durch Energiewende (Solar, E-Mobilität)."),
    "Zimmermann": (2.5, 5.0, "Abbundanlagen, CNC-Holzverarbeitung", "8-15 Jahre",
        "CNC-Bearbeitung bereits verbreitet, aber Montage bleibt manuell. Nachhaltiges Bauen treibt Nachfrage."),
    "Sanitärinstallateur": (2.5, 5.0, "Roboter für einfache Rohrleitungen", "10-15 Jahre",
        "Sanitäre Installation in bestehenden Gebäuden kaum automatisierbar. Fachkräftemangel in CH sehr ausgeprägt."),
    "Maler/in und Gipser/in EFZ": (4.5, 4.0, "Malerroboter für ebene Flächen", "6-10 Jahre",
        "Einfache Flächen können automatisiert werden, komplexe Renovationen bleiben manuell."),
    "Architekt": (5.5, 8.5, "KI-Generativdesign (Autodesk), automatisierte Planung", "4-7 Jahre",
        "Kreative Planung und Kundenkommunikation schützen. KI übernimmt Routinezeichnungen und Normenprüfungen. Sehr hohe Anpassungsfähigkeit."),
    "Bauingenieur": (5.2, 8.5, "KI-Tragwerksplanung, automatisierte Berechnungen", "4-7 Jahre",
        "Strukturberechnungen werden KI-unterstützt. Verantwortung und komplexe Einzelfälle bleiben. Sehr hohe Anpassungsfähigkeit."),
    "Bauführer": (4.5, 7.0, "KI-Baustellen-Management, Drohnenüberwachung", "5-8 Jahre",
        "Koordination und Führung auf der Baustelle schützt. Planung und Reporting werden KI-unterstützt."),
    "Hochbauzeichner": (5.8, 7.5, "KI-gestütztes CAD, automatisierte Pläne", "3-6 Jahre",
        "Standard-CAD-Aufgaben werden automatisiert. Komplexe Planung und Kundenkommunikation bleiben."),

    # Industrie / mittel exponiert
    "Polymechaniker": (4.5, 6.5, "CNC-Automatisierung, kollaborative Roboter", "5-8 Jahre",
        "Präzisionsfertigung zunehmend automatisiert, aber komplexe Einrichteaufgaben bleiben. Gute Anpassungsfähigkeit durch MEM-Ausbildung."),
    "Maschinenführer": (6.5, 4.0, "Vollautomatische Produktionslinien", "3-6 Jahre",
        "Maschinenüberwachung und -bedienung gut automatisierbar. Einrichten und Fehlerdiagnose schützen noch. Pharma-CH mit hohem Automatisierungsgrad."),
    "Produktionsmitarbeiter (Pharma)": (6.0, 4.5, "Robotergestützte Produktion, automatisierte QS", "4-7 Jahre",
        "Pharmaproduktion wird weiter automatisiert. Strenge Regulierung (GMP) verlangsamt Wandel. CH-Pharmaindustrie weltführend."),
    "Chemielaborant": (5.0, 7.0, "Labor-Robotik, automatisierte Analysen", "4-7 Jahre",
        "Routineanalysen werden automatisiert. Methodenentwicklung und komplexe Forschung bleiben menschlich."),
    "Automatiker/in EFZ": (4.5, 7.5, "KI-Automatisierungstools", "5-8 Jahre",
        "Automatisierung von Automatisierungstechnikern – Paradox. Anpassungsfähigkeit durch technische Ausbildung hoch."),
    "Mechatroniker": (4.0, 7.5, "Intelligente Wartungssysteme, Predictive Maintenance", "5-8 Jahre",
        "Komplexe Systeme und variable Umgebungen schützen. Predictive Maintenance verändert aber nicht eliminiert den Beruf."),
    "Maschinenbauingenieur": (5.0, 8.5, "KI-Konstruktion, Generative Design", "4-7 Jahre",
        "KI-Tools beschleunigen Konstruktion stark. Systemdenken und Kundenkommunikation bleiben. Sehr hohe Anpassungsfähigkeit."),
    "Elektroingenieur": (5.2, 8.5, "KI-Schaltungsdesign, automatisierte Tests", "4-7 Jahre",
        "Routinetätigkeiten werden KI-unterstützt. Systemarchitektur und Innovation schützen."),
    "Chemieingenieur": (5.0, 8.5, "Prozesssimulation, automatisierte Optimierung", "4-7 Jahre",
        "Prozessoptimierung wird KI-unterstützt. Sicherheitsverantwortung und Forschung schützen."),
    "Qualitätsmanager": (5.8, 7.5, "Automatisierte Qualitätskontrolle, KI-Anomalieerkennung", "3-6 Jahre",
        "Visuelle Inspektion und Standardprüfungen stark automatisierbar. Systemverantwortung bleibt."),
    "Umweltingenieur": (4.5, 8.5, "KI-Umweltmonitoring, automatisierte Messungen", "5-8 Jahre",
        "Wachsendes Berufsfeld durch Klimawandel. KI unterstützt, ersetzt aber nicht die fachliche Beurteilung."),
    "Naturwissenschaftler": (4.5, 9.0, "KI in der Forschung (AlphaFold etc.)", "4-7 Jahre",
        "KI revolutioniert Forschung, aber Hypothesenbildung und Interpretation bleiben menschlich. Sehr hohe Anpassungsfähigkeit."),

    # Transport / mittel-hoch exponiert
    "Lastwagenfahrer": (6.5, 3.5, "Autonomes Fahren (Level 4/5)", "5-10 Jahre",
        "Autonomes Fahren auf Autobahnen kommt. Letzte Meile und komplexe Manöver dauern länger. CH-Gelände mit Bergen erschwert Automatisierung. Massiver Fahrermangel als Puffer."),
    "Lieferwagenfahrer": (7.0, 3.0, "Lieferroboter, Drohnen, autonome Fahrzeuge", "4-8 Jahre",
        "Last-Mile-Delivery wird durch Roboter und Drohnen ergänzt. Feinzustellung und Service bleiben zunächst manuell."),
    "ÖV-Fahrer": (5.5, 4.5, "Autonome Busse und Trams", "6-10 Jahre",
        "Pilotprojekte autonomer Busse laufen in CH (PostAuto, Sion). Volle Automatisierung dauert durch Komplexität des Stadtverkehrs."),
    "Zugbegleiter/in": (5.8, 6.0, "Autonome Züge, KI-Kundendienst", "6-10 Jahre",
        "SBB automatisiert schrittweise. Sicherheitsaufgaben und Kundenservice bleiben vorerst menschlich."),
    "Logistiker": (6.5, 5.5, "Lageroboter (Goods-to-Person), automatisiertes Kommissionieren", "3-6 Jahre",
        "Amazon/DHL-Style Lagerhaltung weitgehend automatisierbar. Manuelle Tätigkeiten in Kleinbetrieben dauern länger."),
    "Lagerist": (7.0, 3.5, "Lagervollautomatisierung, AMR-Roboter", "3-6 Jahre",
        "Repetitive Lagertätigkeiten stark exponiert. Tiefe Anpassungsfähigkeit problematisch. Mehrere CH-Logistikzentren bereits stark automatisiert."),

    # Recht & Beratung / mittel exponiert
    "Rechtsanwalt": (6.0, 7.5, "KI-Dokumentenanalyse, Legal Research Automation", "3-6 Jahre",
        "Dokumentenprüfung und Recherche werden durch LegalTech stark automatisiert. Argumentation, Verhandlung und strategische Beratung bleiben menschlich."),
    "Unternehmensberater": (5.8, 8.0, "KI-Analyse und automatisierte Berichte", "3-6 Jahre",
        "Datenanalysen und Standardempfehlungen werden KI-unterstützt. Kundenbeziehung und komplexe Problemlösung schützen."),

    # Management / mittel exponiert
    "Geschäftsführer (KMU)": (4.0, 8.5, "KI-Entscheidungsunterstützung, automatisiertes Reporting", "4-7 Jahre",
        "Führung, Verantwortung und Netzwerk schützen stark. KI-Tools werden zu Produktivitätshebel. Sehr hohe Anpassungsfähigkeit."),
    "HR-Manager": (5.5, 7.5, "KI-Recruiting, automatisierte Onboarding-Prozesse", "3-6 Jahre",
        "Administrative HR-Aufgaben stark automatisierbar. Kulturelle Entwicklung und Führungskräfteentwicklung bleiben menschlich."),
    "Marketing-/Kommunikationsleiter": (5.2, 8.0, "KI-Content-Generierung, automatisiertes Marketing", "3-5 Jahre",
        "Content-Erstellung und A/B-Tests werden KI-unterstützt. Kreativstrategie und Markenidentität bleiben menschlich."),
    "Projektleiter (allg.)": (5.0, 8.0, "KI-Projektplanung und Ressourcenoptimierung", "4-6 Jahre",
        "Planung und Reporting werden KI-unterstützt. Stakeholdermanagement und Führung schützen."),

    # Kreativ / tief bis mittel exponiert
    "Grafiker": (5.5, 7.5, "KI-Bildgenerierung (Midjourney, DALL-E)", "2-4 Jahre",
        "Standardgrafiken stark automatisierbar. Kreative Konzeption und Markenidentität schützen. Branche im Umbruch – Anpassung notwendig und möglich."),
    "Journalist": (5.5, 7.5, "KI-Textgenerierung, automatisierte Nachrichten", "2-4 Jahre",
        "Nachrichtenmeldungen und Standardberichte werden automatisiert. Investigativer Journalismus, Analyse und Einordnung bleiben menschlich."),
    "PR-Spezialist": (5.8, 7.5, "KI-Content und automatisiertes Social Media", "3-5 Jahre",
        "Content-Erstellung wird KI-unterstützt. Beziehungsmanagement und Krisenkomm. bleiben menschlich."),

    # Landwirtschaft / tief exponiert
    "Landwirt": (4.0, 5.0, "Präzisionslandwirtschaft, autonome Erntemaschinen", "6-10 Jahre",
        "Technisierung in der Landwirtschaft läuft bereits. CH-Berglandwirtschaft und Direktzahlungssystem schützen. Viele Nischenprodukte bleiben manuell."),
    "Gärtner": (3.5, 5.0, "Mähroboter, Bewässerungsautomation", "6-10 Jahre",
        "Kreative Gartengestaltung und Pflanzenpflege schützen. Rasen mähen und Standardpflege werden automatisiert."),

    # Sicherheit & Soziales / tief exponiert
    "Polizist": (3.5, 6.0, "Überwachungstechnologie, Predictive Policing", "6-10 Jahre",
        "Physische Intervention und menschliches Ermessen schützen stark. KI unterstützt Fahndung und Prävention, ersetzt aber nicht."),
    "Sozialarbeiter": (3.0, 7.0, "KI-Case-Management, Diagnoseunterstützung", "6-10 Jahre",
        "Menschliche Beziehung und Vertrauen sind Kern der Sozialarbeit. KI unterstützt Verwaltungsaufgaben. Steigende Nachfrage in CH."),
    "Sozialpädagoge": (2.8, 7.0, "KI in der Förderdiagnostik", "7-12 Jahre",
        "Pädagogische Beziehungsarbeit kaum automatisierbar. Wachsendes Berufsfeld."),
    "Kinderbetreuerin": (2.5, 5.5, "Roboter-Assistenz in Kitas", "8-15 Jahre",
        "Frühkindliche Betreuung erfordert menschliche Zuwendung und Empathie. Sehr sicherer Beruf. Akuter Fachkräftemangel in CH."),
    "Feuerwehrmann/-frau": (2.5, 6.0, "Löschroboter, Drohnen", "10-15 Jahre",
        "Physische Rettungseinsätze kaum automatisierbar. Sehr sicherer Beruf mit hohem gesellschaftlichem Wert."),

    # Dienstleistungen / tief bis mittel
    "Coiffeur": (3.2, 4.5, "Haarstyling-Roboter (experimentell)", "10+ Jahre",
        "Manuelles Handwerk und Kundenbeziehung schützen stark. Technische Automatisierung noch weit entfernt."),
    "Reinigungskraft": (5.8, 2.5, "Reinigungsroboter (Saugroboter, Fensterputzroboter)", "5-10 Jahre",
        "Einfache Bodenreinigung wird automatisiert. Komplexe Reinigung (Badezimmer, unregelmässige Flächen) dauert länger. Tiefe Anpassungsfähigkeit problematisch."),
    "Hauswirtschaftler": (4.5, 4.0, "Haushaltsroboter", "7-12 Jahre",
        "Komplexe Haushaltsaufgaben kaum automatisierbar. Persönliche Betreuung schützt."),
    "Sicherheitsbeauftragter": (5.5, 5.0, "KI-Videoüberwachung, automatisierte Zutrittskontrolle", "4-8 Jahre",
        "Überwachungsaufgaben werden KI-unterstützt. Physische Präsenz und Entscheidungsfähigkeit schützen."),

    # Immobilien
    "Immobilienbewirtschafter": (6.2, 6.5, "Automatisiertes Property Management, KI-Mieterscreening", "3-6 Jahre",
        "Administrative Aufgaben gut automatisierbar. CH-Immobilienmarkt mit hoher Komplexität schützt fachliche Beratung."),
    "Immobilienmakler": (6.0, 6.5, "KI-Bewertung, automatisiertes Matching", "3-6 Jahre",
        "KI-Plattformen übernehmen Matching und Bewertung. Verhandlungsführung und Vertrauen schützen."),

    # Wissenschaft
    "Ökonom/in": (5.5, 9.0, "KI-Wirtschaftsmodellierung, automatisierte Prognosen", "4-7 Jahre",
        "Standardmodelle und Prognosen werden KI-unterstützt. Politikberatung und kritische Analyse schützen. Sehr hohe Anpassungsfähigkeit."),
}
# fmt: on


def apply_demo_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Fügt Demo-Scores zur Berufsliste hinzu."""
    df = df.copy()

    scores_gesamt, adaptabilitaet_list = [], []
    haupt_risiko_list, zeitrahmen_list, begruendung_list = [], [], []

    for _, row in df.iterrows():
        beruf = row["beruf"]
        # Fuzzy-Match: schaue ob Berufsname einen Schlüssel enthält
        match = None
        for key, vals in SCORE_LOOKUP.items():
            if key.lower() in beruf.lower() or beruf.lower().startswith(key.lower()[:8]):
                match = vals
                break

        if match:
            scores_gesamt.append(match[0])
            adaptabilitaet_list.append(match[1])
            haupt_risiko_list.append(match[2])
            zeitrahmen_list.append(match[3])
            begruendung_list.append(match[4])
        else:
            # Fallback-Score basierend auf Branche und Qualifikation
            branche_scores = {
                "Finanzen": 7.5, "Versicherungen": 7.5, "ICT": 5.5, "Verwaltung": 6.5,
                "Gesundheit": 4.0, "Soziales": 3.5, "Bildung": 4.0, "Detailhandel": 7.0,
                "Gastgewerbe": 5.5, "Bau": 3.5, "Industrie": 5.0, "Transport": 6.5,
                "Recht": 6.0, "Beratung": 5.5, "Medien": 5.5, "Landwirtschaft": 4.0,
                "Öff. Verwaltung": 6.0, "Dienstleistungen": 5.0, "Immobilien": 6.0,
                "Sicherheit": 5.0, "Umwelt": 4.5,
            }
            qual_adapt = {"Tertiär": 8.0, "Sekundär II": 5.5, "Keine Ausbildung": 2.5}

            score = branche_scores.get(row.get("branche", ""), 5.5)
            adapt = qual_adapt.get(row.get("qualifikation", ""), 5.0)
            scores_gesamt.append(round(score + 0.3, 1))
            adaptabilitaet_list.append(adapt)
            haupt_risiko_list.append("Automatisierung von Routinetätigkeiten")
            zeitrahmen_list.append("3-7 Jahre")
            begruendung_list.append("Schätzung basierend auf Branche und Qualifikationsprofil.")

    df["score_gesamt"] = scores_gesamt
    df["adaptabilitaet"] = adaptabilitaet_list
    df["haupt_risiko"] = haupt_risiko_list
    df["zeitrahmen"] = zeitrahmen_list
    df["begruendung"] = begruendung_list
    return df


if __name__ == "__main__":  # pragma: no cover
    from ch_adjustments import apply_ch_adjustments

    df = pd.read_csv(PROCESSED_PATH / "berufe_ch_esco.csv")
    df = apply_demo_scores(df)
    df = apply_ch_adjustments(df)

    out = PROCESSED_PATH / "scores.csv"
    df.to_csv(out, index=False)
    print(f"Demo-Scores gespeichert: {out}")
    print(f"\nTop 10 exponierte Berufe:")
    print(df.nlargest(10, "score_ch")[["beruf", "score_ch", "adaptabilitaet", "zeitrahmen"]].to_string())
    print(f"\nTop 10 sicherste Berufe:")
    print(df.nsmallest(10, "score_ch")[["beruf", "score_ch", "adaptabilitaet", "zeitrahmen"]].to_string())
