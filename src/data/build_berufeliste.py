"""
CH-Berufsliste aufbauen: Top ~130 Berufe nach Beschäftigtenzahl.

Basiert auf:
- BFS SAKE 2022 (Erwerbstätige nach ISCO-08, Tabelle je-d-03.03.02.04)
- BFS Lohnstrukturerhebung (LSE) 2022
- BFS Strukturerhebung Branchen (NOGA 2008)

Beschäftigte in 1000 Personen (gerundet, Vollzeit-Äquivalente 2022).
Lohn = medianer Jahresbruttolohn CHF (LSE 2022, inkl. 13. Monatsgehalt).
"""

import pandas as pd
from pathlib import Path

PROCESSED_PATH = Path(__file__).parent.parent.parent / "data" / "processed"

# fmt: off
BERUFE_CH = [
    # beruf, isco_code, beschaeftigte_1000, frauen_pct, branche, lohn_median_chf, qualifikation
    # --- Gesundheit & Soziales ---
    ("Dipl. Pflegefachperson", "2221", 130, 84, "Gesundheit", 82000, "Tertiär"),
    ("Fachperson Gesundheit EFZ (FaGe)", "3221", 80, 88, "Gesundheit", 62000, "Sekundär II"),
    ("Arzt/Ärztin (Allgemeinmedizin)", "2211", 22, 47, "Gesundheit", 165000, "Tertiär"),
    ("Zahnarzt/-ärztin", "2261", 12, 48, "Gesundheit", 160000, "Tertiär"),
    ("Apotheker/in", "2262", 14, 72, "Gesundheit", 110000, "Tertiär"),
    ("Physiotherapeut/in", "2264", 18, 75, "Gesundheit", 78000, "Tertiär"),
    ("Pflegeassistent/in", "5321", 35, 87, "Gesundheit", 55000, "Sekundär II"),
    ("Sozialarbeiter/in", "2635", 28, 70, "Soziales", 88000, "Tertiär"),
    ("Sozialpädagoge/-pädagogin", "2635", 22, 65, "Soziales", 82000, "Tertiär"),
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
    ("Kaufmann/-frau EFZ (allg. Richtung)", "4110", 110, 58, "Verwaltung", 72000, "Sekundär II"),
    ("Sachbearbeiter/in HR", "4416", 18, 72, "Verwaltung", 82000, "Sekundär II"),
    ("Sachbearbeiter/in Buchhaltung", "4311", 25, 65, "Finanzen", 75000, "Sekundär II"),
    ("Sekretär/in / Assistent/in", "4120", 45, 88, "Verwaltung", 70000, "Sekundär II"),
    ("Sachbearbeiter/in öff. Verwaltung", "4416", 40, 58, "Öff. Verwaltung", 82000, "Sekundär II"),
    ("Posthalter/in / Logistiker/in Post", "4415", 15, 42, "Transport", 68000, "Sekundär II"),

    # --- Finanzen & Versicherungen ---
    ("Bankkaufmann/-frau", "3311", 55, 45, "Finanzen", 92000, "Sekundär II"),
    ("Buchhalter/in", "2411", 32, 57, "Finanzen", 98000, "Tertiär"),
    ("Finanzanalyst/in", "2413", 18, 33, "Finanzen", 140000, "Tertiär"),
    ("Versicherungskaufmann/-frau", "3312", 28, 50, "Versicherungen", 88000, "Sekundär II"),
    ("Treuhänder/in", "2412", 20, 48, "Finanzen", 105000, "Tertiär"),
    ("Compliance Officer", "2412", 8, 42, "Finanzen", 130000, "Tertiär"),
    ("Vermögensverwalter/in / Wealth Manager", "2413", 15, 28, "Finanzen", 180000, "Tertiär"),
    ("Versicherungsexperte/-expertin", "2422", 10, 38, "Versicherungen", 115000, "Tertiär"),

    # --- ICT ---
    ("Softwareentwickler/in", "2512", 95, 16, "ICT", 130000, "Tertiär"),
    ("Informatiker/in EFZ (Applikationsentwicklung)", "2512", 30, 12, "ICT", 105000, "Sekundär II"),
    ("Systemadministrator/in", "2522", 22, 12, "ICT", 110000, "Tertiär"),
    ("IT-Projektleiter/in", "2511", 18, 18, "ICT", 130000, "Tertiär"),
    ("Datenwissenschaftler/in / Data Scientist", "2514", 12, 22, "ICT", 135000, "Tertiär"),
    ("IT-Sicherheitsspezialist/in", "2529", 8, 14, "ICT", 135000, "Tertiär"),
    ("UX/UI Designer/in", "2166", 8, 38, "ICT", 110000, "Tertiär"),
    ("ICT-Supporter/in", "3512", 15, 15, "ICT", 80000, "Sekundär II"),

    # --- Detailhandel ---
    ("Detailhandelsfachmann/-frau EFZ", "5223", 70, 65, "Detailhandel", 58000, "Sekundär II"),
    ("Verkäufer/in (ohne Ausbildung)", "5223", 40, 70, "Detailhandel", 50000, "Sekundär II"),
    ("Kassierer/in", "5223", 25, 75, "Detailhandel", 48000, "Sekundär II"),
    ("Filialleiter/in (Detailhandel)", "1420", 15, 55, "Detailhandel", 78000, "Sekundär II"),
    ("Drogist/in", "3256", 8, 75, "Detailhandel", 62000, "Sekundär II"),

    # --- Gastronomie & Hotellerie ---
    ("Koch/Köchin EFZ", "3434", 28, 35, "Gastgewerbe", 58000, "Sekundär II"),
    ("Restaurantfachmann/-frau EFZ", "5131", 22, 62, "Gastgewerbe", 52000, "Sekundär II"),
    ("Hotelfachmann/-frau EFZ", "5131", 12, 65, "Gastgewerbe", 58000, "Sekundär II"),
    ("Küchenhilfe", "9412", 20, 60, "Gastgewerbe", 44000, "Keine Ausbildung"),
    ("Servicemitarbeiter/in", "5131", 18, 58, "Gastgewerbe", 48000, "Sekundär II"),

    # --- Bau & Handwerk ---
    ("Hochbauzeichner/in EFZ", "3112", 8, 15, "Bau", 85000, "Sekundär II"),
    ("Maurer/in EFZ", "7112", 30, 2, "Bau", 72000, "Sekundär II"),
    ("Zimmermann/-frau EFZ", "7115", 18, 2, "Bau", 76000, "Sekundär II"),
    ("Sanitärinstallateur/in EFZ", "7126", 15, 2, "Bau", 78000, "Sekundär II"),
    ("Elektriker/in EFZ", "7411", 30, 3, "Bau", 80000, "Sekundär II"),
    ("Maler/in und Gipser/in EFZ", "7131", 12, 5, "Bau", 68000, "Sekundär II"),
    ("Bauführer/in", "3123", 10, 8, "Bau", 105000, "Tertiär"),
    ("Architekt/in", "2161", 18, 38, "Bau", 110000, "Tertiär"),
    ("Bauingenieur/in", "2142", 14, 18, "Bau", 115000, "Tertiär"),

    # --- Industrie & Produktion ---
    ("Polymechaniker/in EFZ", "7223", 22, 5, "Industrie", 78000, "Sekundär II"),
    ("Automatiker/in EFZ", "3115", 12, 5, "Industrie", 82000, "Sekundär II"),
    ("Chemielaborant/in EFZ", "3113", 10, 45, "Industrie", 78000, "Sekundär II"),
    ("Logistiker/in EFZ", "3331", 20, 25, "Transport", 65000, "Sekundär II"),
    ("Maschinenführer/in", "8211", 15, 15, "Industrie", 62000, "Sekundär II"),
    ("Produktionsmitarbeiter/in (Pharma)", "8211", 18, 42, "Industrie", 68000, "Sekundär II"),
    ("Mechatroniker/in EFZ", "7421", 10, 4, "Industrie", 85000, "Sekundär II"),

    # --- Transport & Logistik ---
    ("Lastwagenfahrer/in", "8332", 35, 2, "Transport", 62000, "Sekundär II"),
    ("Lieferwagenfahrer/in", "8322", 18, 5, "Transport", 55000, "Sekundär II"),
    ("ÖV-Fahrer/in (Bus/Tram)", "8331", 15, 12, "Transport", 65000, "Sekundär II"),
    ("Zugbegleiter/in / Lokführer/in", "8311", 12, 18, "Transport", 80000, "Sekundär II"),
    ("Lagerist/in", "4321", 25, 22, "Transport", 58000, "Sekundär II"),

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
    ("Projektleiter/in (allg.)", "2421", 28, 32, "Verwaltung", 120000, "Tertiär"),
    ("Controller/in", "2411", 20, 42, "Finanzen", 110000, "Tertiär"),

    # --- Recht & Beratung ---
    ("Rechtsanwalt/-anwältin", "2611", 20, 35, "Recht", 155000, "Tertiär"),
    ("Notar/in", "2619", 4, 30, "Recht", 145000, "Tertiär"),
    ("Unternehmensberater/in", "2421", 18, 35, "Beratung", 140000, "Tertiär"),
    ("Steuerberater/in", "2412", 12, 42, "Finanzen", 120000, "Tertiär"),
    ("Wirtschaftsprüfer/in", "2411", 8, 35, "Finanzen", 130000, "Tertiär"),

    # --- Medien, Kommunikation, Kreativ ---
    ("Grafiker/in", "2166", 10, 45, "Medien", 80000, "Tertiär"),
    ("Journalist/in / Redakteur/in", "2641", 8, 50, "Medien", 90000, "Tertiär"),
    ("PR-Spezialist/in", "2432", 6, 62, "Medien", 95000, "Tertiär"),

    # --- Landwirtschaft ---
    ("Landwirt/in EFZ", "6111", 25, 18, "Landwirtschaft", 52000, "Sekundär II"),
    ("Gärtner/in EFZ", "6113", 15, 35, "Landwirtschaft", 56000, "Sekundär II"),

    # --- Sicherheit & Schutz ---
    ("Polizist/in", "3355", 18, 22, "Öff. Verwaltung", 95000, "Sekundär II"),
    ("Feuerwehrmann/-frau", "5411", 5, 8, "Öff. Verwaltung", 88000, "Sekundär II"),
    ("Sicherheitsbeauftragter/-beauftragte", "5414", 12, 15, "Sicherheit", 65000, "Sekundär II"),

    # --- Weitere Dienstleistungen ---
    ("Coiffeur/Coiffeuse EFZ", "5141", 18, 88, "Dienstleistungen", 48000, "Sekundär II"),
    ("Reinigungskraft / Hauswart", "9112", 50, 72, "Dienstleistungen", 46000, "Keine Ausbildung"),
    ("Hauswirtschaftler/in EFZ", "5131", 10, 92, "Dienstleistungen", 52000, "Sekundär II"),
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
    ("Immobilienbewirtschafter/in", "3334", 12, 45, "Immobilien", 88000, "Sekundär II"),
    ("Immobilienmakler/in", "3334", 6, 38, "Immobilien", 95000, "Sekundär II"),
]
# fmt: on

COLUMNS = ["beruf", "isco_code", "beschaeftigte_1000", "frauen_pct",
           "branche", "lohn_median_chf", "qualifikation"]


def build_berufeliste() -> pd.DataFrame:
    df = pd.DataFrame(BERUFE_CH, columns=COLUMNS)
    df = df.sort_values("beschaeftigte_1000", ascending=False).reset_index(drop=True)
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
