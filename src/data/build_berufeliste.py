"""
CH-Berufsliste aufbauen: Top ~130 Berufe nach Beschäftigtenzahl.

Basiert auf:
- BFS SAKE 2022 (Erwerbstätige nach ISCO-08, Tabelle je-d-03.03.02.04)
- BFS Lohnstrukturerhebung (LSE) 2022
- BFS Strukturerhebung Branchen (NOGA 2008)

Beschäftigte in 1000 Personen (gerundet, Vollzeit-Äquivalente 2022).
Lohn = medianer Jahresbruttolohn CHF (LSE 2022, inkl. 13. Monatsgehalt).

Hinweis Löhne: Die Lohnwerte in BERUFE_CH sind historische Schätzungen je 4-stelligem
Beruf — die LSE publiziert keine 4-stelligen Werte, sie sind also nicht belegbar. Sie
werden durch src/data/update_loehne.py ersetzt (LSE 2024, 2-stellige Gruppe × 12,
Salarium-Profile für heterogene Gruppen; Spalte lohn_quelle).

Hinweis Beschäftigte (Issue #51): Beschäftigte und Frauenanteil in BERUFE_CH sind ebenfalls
historische Platzhalter. Massgebend ist die BFS Strukturerhebung (SE) 2024 über die
Zuordnung in data/processed/beruf_berufsart_mapping.csv (src/data/update_from_bfs.py).
ISCO-Codes sind nach dem Audit in docs/audit_isco_codes.md korrigiert («# #51: ISCO …»).
Berufe, die sich eine Berufsgattung teilten und mit den SE-Berufsarten nicht trennbar sind,
sind zu einem Eintrag mit der SE-Bezeichnung zusammengelegt («# #51: zusammengelegt»;
bisherige Titel in der Spalte synonyme, siehe src/data/berufe_zusammenlegen.py).
"""

import pandas as pd
from pathlib import Path

PROCESSED_PATH = Path(__file__).parent.parent.parent / "data" / "processed"

# fmt: off
BERUFE_CH = [
    # occupation, isco_code, employed_k, women_pct, sector, wage_median_chf, qualification
    # --- Gesundheit & Soziales ---
    ("Dipl. Pflegefachperson", "2221", 130, 84, "Gesundheit", 82000, "Tertiär"),
    ("Fachperson Gesundheit EFZ (FaGe)", "3221", 80, 88, "Gesundheit", 62000, "Sekundär II"),
    ("Arzt/Ärztin (Allgemeinmedizin)", "2211", 22, 47, "Gesundheit", 165000, "Tertiär"),
    ("Zahnarzt/-ärztin", "2261", 12, 48, "Gesundheit", 160000, "Tertiär"),
    ("Apotheker/in", "2262", 14, 72, "Gesundheit", 110000, "Tertiär"),
    ("Physiotherapeut/in", "2264", 18, 75, "Gesundheit", 78000, "Tertiär"),
    ("Pflegeassistent/in", "5321", 35, 87, "Gesundheit", 55000, "Sekundär II"),
    ("Sozialarbeiter", "2635", 19.5, 72, "Soziales", 95900, "Tertiär"),  # #51: zusammengelegt
    ("Arztpraxisassistent/in", "3256", 25, 95, "Gesundheit", 60000, "Sekundär II"),
    ("Spitex-Mitarbeiter/in", "5322", 30, 89, "Gesundheit", 58000, "Sekundär II"),

    # --- Bildung ---
    ("Primarlehrer/in", "2341", 55, 72, "Bildung", 102000, "Tertiär"),
    ("Kindergärtnerin/-gärtner", "2342", 22, 96, "Bildung", 95000, "Tertiär"),
    ("Sekundarlehrer/in", "2330", 38, 55, "Bildung", 110000, "Tertiär"),
    ("Gymnasiallehrer/in", "2330", 18, 46, "Bildung", 120000, "Tertiär"),
    ("Berufsschullehrer/in", "2320", 15, 35, "Bildung", 115000, "Tertiär"),
    ("Hochschuldozent/in", "2310", 30, 37, "Bildung", 130000, "Tertiär"),

    # --- Kaufmännisch / Verwaltung ---
    ("Allgemeine Bürokräfte", "4110", 224.3, 75, "Verwaltung", 79644, "Sekundär II"),  # #51: zusammengelegt
    ("Sachbearbeiter/in HR", "4416", 18, 72, "Verwaltung", 82000, "Sekundär II"),
    ("Sachbearbeiter/in Buchhaltung", "4311", 25, 65, "Finanzen", 75000, "Sekundär II"),
    ("Sekretär/in / Assistent/in", "4120", 45, 88, "Verwaltung", 70000, "Sekundär II"),
    ("Posthalter/in / Logistiker/in Post", "4415", 15, 42, "Transport", 68000, "Sekundär II"),

    # --- Finanzen & Versicherungen ---
    ("Schalterbedienstete und Fachkräfte im Bereich Finanzdienstleistungen", "4211", 39.8, 49, "Finanzen", 71580, "Sekundär II"),  # #51: zusammengelegt
    ("Fachkräfte im Rechnungswesen", "3313", 36.2, 59, "Finanzen", 94800, "Sekundär II"),  # #51: zusammengelegt
    ("Finanzanalyst/in", "2413", 18, 33, "Finanzen", 140000, "Tertiär"),
    ("Versicherungskaufmann/-frau", "3312", 28, 50, "Versicherungen", 88000, "Sekundär II"),
    ("Wirtschaftsprüfer, Steuerberater und verwandte Berufe", "2411", 32.9, 41, "Finanzen", 108100, "Tertiär"),  # #51: zusammengelegt
    ("Finanz- und Anlageberater", "2412", 20.8, 30, "Finanzen", 122900, "Tertiär"),  # #51: zusammengelegt
    ("Versicherungsexperte/-expertin", "2422", 10, 38, "Versicherungen", 115000, "Tertiär"),

    # --- ICT ---
    ("Softwareentwickler", "2512", 71.4, 13, "ICT", 119388, "Tertiär"),  # #51: zusammengelegt
    ("Systemadministrator/in", "2522", 22, 12, "ICT", 110000, "Tertiär"),
    ("IT-Projektleiter/in", "2511", 18, 18, "ICT", 130000, "Tertiär"),
    ("Datenwissenschaftler/in / Data Scientist", "2514", 12, 22, "ICT", 135000, "Tertiär"),
    ("IT-Sicherheitsspezialist/in", "2529", 8, 14, "ICT", 135000, "Tertiär"),
    ("Grafik- und Multimediadesigner", "2166", 13.7, 52, "Medien", 104760, "Tertiär"),  # #51: zusammengelegt
    ("ICT-Supporter/in", "3512", 15, 15, "ICT", 80000, "Sekundär II"),

    # --- Detailhandel ---
    ("Verkäufer in Handelsgeschäften", "5223", 136.7, 75, "Detailhandel", 59640, "Sekundär II"),  # #51: zusammengelegt
    ("Kassierer und Kartenverkäufer", "5230", 8.8, 85, "Detailhandel", 59640, "Sekundär II"),  # #51: zusammengelegt
    ("Filialleiter/in (Detailhandel)", "1420", 15, 55, "Detailhandel", 78000, "Sekundär II"),
    ("Drogist/in", "5223", 8, 75, "Detailhandel", 62000, "Sekundär II"),  # #51: ISCO 3256 → 5223

    # --- Gastronomie & Hotellerie ---
    ("Köche", "5120", 48.9, 35, "Gastgewerbe", 59124, "Sekundär II"),  # #51: zusammengelegt
    ("Restaurantfachmann/-frau EFZ", "5131", 22, 62, "Gastgewerbe", 52000, "Sekundär II"),
    ("Reinigungs- und Hauswirtschaftleiter und -kräfte in Büros, Hotels und anderen Einrichtungen", "5151", 29.4, 87, "Dienstleistungen", 59124, "Sekundär II"),  # #51: zusammengelegt
    ("Küchenhilfe", "9412", 20, 60, "Gastgewerbe", 44000, "Keine Ausbildung"),
    ("Servicemitarbeiter/in", "5131", 18, 58, "Gastgewerbe", 48000, "Sekundär II"),

    # --- Bau & Handwerk ---
    ("Technische Zeichner", "3118", 28.3, 26, "Industrie", 90084, "Sekundär II"),  # #51: zusammengelegt
    ("Maurer/in EFZ", "7112", 30, 2, "Bau", 72000, "Sekundär II"),
    ("Zimmermann/-frau EFZ", "7115", 18, 2, "Bau", 76000, "Sekundär II"),
    ("Sanitärinstallateur/in EFZ", "7126", 15, 2, "Bau", 78000, "Sekundär II"),
    ("Elektriker/in EFZ", "7411", 30, 3, "Bau", 80000, "Sekundär II"),
    ("Maler/in und Gipser/in EFZ", "7131", 12, 5, "Bau", 68000, "Sekundär II"),
    ("Bauführer/in", "3112", 10, 8, "Bau", 105000, "Tertiär"),  # #51: ISCO 3123 → 3112
    ("Architekt/in", "2161", 18, 38, "Bau", 110000, "Tertiär"),
    ("Bauingenieur/in", "2142", 14, 18, "Bau", 115000, "Tertiär"),

    # --- Industrie & Produktion ---
    ("Polymechaniker/in EFZ", "7200", 22, 5, "Industrie", 78000, "Sekundär II"),  # #51: ISCO 7223 → 7200
    ("Automatiker und verwandte Berufe", "7412", 13.2, 4, "Industrie", 77184, "Sekundär II"),  # #51: zusammengelegt
    ("Chemo- und Physikotechniker", "3111", 8.4, 56, "Industrie", 90084, "Sekundär II"),  # #51: zusammengelegt
    ("Fachkräfte in der Lagerwirtschaft", "4321", 28.6, 20, "Transport", 72420, "Sekundär II"),  # #51: zusammengelegt
    ("Maschinenführer/in", "8211", 15, 15, "Industrie", 62000, "Sekundär II"),
    ("Bediener von Anlagen und Maschinen für chemische Erzeugnisse", "8131", 6.7, 23, "Industrie", 69336, "Sekundär II"),  # #51: zusammengelegt
    ("Mechatroniker/in EFZ", "7421", 10, 4, "Industrie", 85000, "Sekundär II"),

    # --- Transport & Logistik ---
    ("Lastwagenfahrer/in", "8332", 35, 2, "Transport", 62000, "Sekundär II"),
    ("Lieferwagenfahrer/in", "8322", 18, 5, "Transport", 55000, "Sekundär II"),
    ("ÖV-Fahrer/in (Bus/Tram)", "8331", 15, 12, "Transport", 65000, "Sekundär II"),
    ("Zugbegleiter/in / Lokführer/in", "8311", 12, 18, "Transport", 80000, "Sekundär II"),

    # --- Ingenieurwesen & Technik ---
    ("Maschinenbauingenieur/in", "2144", 20, 12, "Industrie", 120000, "Tertiär"),
    ("Elektroingenieur/in", "2151", 15, 10, "Industrie", 122000, "Tertiär"),
    ("Chemieingenieur/in / Verfahrenstechniker/in", "2145", 10, 25, "Industrie", 118000, "Tertiär"),
    ("Projektleiter/in (Technik)", "2149", 22, 18, "Industrie", 125000, "Tertiär"),
    ("Qualitätsmanager/in", "2146", 12, 35, "Industrie", 110000, "Tertiär"),
    ("Umweltingenieur/in", "2143", 6, 35, "Umwelt", 105000, "Tertiär"),

    # --- Management & Führung ---
    ("Geschäftsführer/in (KMU)", "1120", 35, 22, "Verwaltung", 160000, "Tertiär"),
    ("HR-Manager/in", "1212", 12, 68, "Verwaltung", 115000, "Tertiär"),
    ("Marketing-/Kommunikationsleiter/in", "1222", 10, 52, "Verwaltung", 120000, "Tertiär"),
    ("Spezialisten im Bereich Management- und Organisationsanalyse", "2421", 25, 30, "Verwaltung", 121200, "Tertiär"),  # #51: zusammengelegt

    # --- Recht & Beratung ---
    ("Rechtsanwalt/-anwältin", "2611", 20, 35, "Recht", 155000, "Tertiär"),
    ("Notar/in", "2619", 4, 30, "Recht", 145000, "Tertiär"),

    # --- Medien, Kommunikation, Kreativ ---
    ("Journalisten", "2642", 10.2, 48, "Medien", 96900, "Tertiär"),  # #51: zusammengelegt
    ("PR-Spezialist/in", "2432", 6, 62, "Medien", 95000, "Tertiär"),

    # --- Landwirtschaft ---
    ("Landwirte mit Ackerbau und Tierhaltung (ohne ausgeprägten Schwerpunkt)", "6130", 46.6, 20, "Landwirtschaft", 67464, "Sekundär II"),  # #51: zusammengelegt
    ("Gärtner/in EFZ", "6113", 15, 35, "Landwirtschaft", 56000, "Sekundär II"),

    # --- Sicherheit & Schutz ---
    ("Polizisten (ohne Polizeikommissare)", "5412", 20.5, 23, "Öff. Verwaltung", 78336, "Sekundär II"),  # #51: zusammengelegt
    ("Feuerwehrmann/-frau", "5411", 5, 8, "Öff. Verwaltung", 88000, "Sekundär II"),
    ("Sicherheitsbeauftragter/-beauftragte", "5414", 12, 15, "Sicherheit", 65000, "Sekundär II"),

    # --- Weitere Dienstleistungen ---
    ("Coiffeur/Coiffeuse EFZ", "5141", 18, 88, "Dienstleistungen", 48000, "Sekundär II"),
    ("Reinigungskraft / Hauswart", "9112", 50, 72, "Dienstleistungen", 46000, "Keine Ausbildung"),
    ("Kinderbetreuerin/-betreuer", "5311", 25, 93, "Soziales", 58000, "Sekundär II"),
    ("Elektroplaner/in EFZ", "3113", 6, 8, "Bau", 85000, "Sekundär II"),

    # --- Wissenschaft & Forschung ---
    ("Naturwissenschaftler/in (Biologie/Chemie)", "2113", 12, 45, "Industrie", 105000, "Tertiär"),
    ("Ökonom/in / Volkswirt/in", "2631", 8, 40, "Finanzen", 120000, "Tertiär"),
    ("Psychologe/-pädagogin", "2634", 12, 72, "Gesundheit", 90000, "Tertiär"),
    ("Statistiker/in / Aktuar/in", "2120", 6, 38, "Finanzen", 125000, "Tertiär"),

    # --- Telekommunikation ---
    ("Telematiker/in EFZ", "3522", 8, 5, "ICT", 80000, "Sekundär II"),
    ("Netzwerkingenieur/in", "2523", 8, 8, "ICT", 115000, "Tertiär"),

    # --- Immobilien ---
    ("Immobilienmakler und -verwalter", "3334", 24.2, 48, "Immobilien", 94800, "Sekundär II"),  # #51: zusammengelegt
]
# fmt: on

# Spaltennamen wie in berufe_ch.csv (englisch seit #53, siehe column_mapping.py)
COLUMNS = ["occupation", "isco_code", "employed_k", "women_pct",
           "sector", "wage_median_chf", "qualification"]


def build_berufeliste() -> pd.DataFrame:
    df = pd.DataFrame(BERUFE_CH, columns=COLUMNS)
    df = df.sort_values("employed_k", ascending=False).reset_index(drop=True)
    return df


def save_berufeliste(df: pd.DataFrame) -> None:
    PROCESSED_PATH.mkdir(parents=True, exist_ok=True)
    out = PROCESSED_PATH / "berufe_ch.csv"
    df.to_csv(out, index=False)
    print(f"Berufsliste gespeichert: {out} ({len(df)} Berufe)")


if __name__ == "__main__":
    df = build_berufeliste()
    print(df.to_string())
    save_berufeliste(df)
