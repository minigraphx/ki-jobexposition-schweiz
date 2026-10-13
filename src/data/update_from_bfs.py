"""
BFS CH-ISCO-19 Daten einlesen und berufe_ch.csv aktualisieren.

Quelle: BFS Strukturerhebung (SE) — «Ausgeübter Beruf (CH-ISCO-19) nach Geschlecht
und Staatsangehörigkeit», Erwerbstätige ab 15 Jahren, in 1000.
Asset 36492006, Datei su-d-40.02.03.02.01.03.10.xlsx (manueller Download nach data/raw/):
https://www.bfs.admin.ch/bfs/de/home/statistiken/kataloge-datenbanken.assetdetail.36492006.html

Hinweis: Es handelt sich um die Strukturerhebung (SE), nicht um die SAKE. Die Datei enthält
ein Blatt pro Jahr («2024», «2023», …) sowie gepoolte Mehrjahresblätter («2022-2024», …).

Schritte:
1. BFS Excel parsen (Blatt per --blatt wählbar, Default "2024"; 4-stellige Berufsgattungen)
2. Beschäftigte + Frauen% der bestehenden 107 Einträge aktualisieren
3. Neue Berufe (>= 5000 Beschäftigte, noch nicht in scores.csv) hinzufügen
4. Branche / Lohn / Qualifikation per ISCO-Gruppe automatisch zuweisen
   (Lohn = LSE 2024, 2-stellige Gruppe × 12; danach update_loehne.py für alle Berufe
   inkl. Salarium-Profile ausführen)
5. berufe_ch.csv speichern
"""

import argparse
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from update_loehne import lade_lse, lse_basislohn

RAW_PATH = Path(__file__).parent.parent.parent / "data" / "raw"
PROCESSED_PATH = Path(__file__).parent.parent.parent / "data" / "processed"
BFS_FILE = RAW_PATH / "su-d-40.02.03.02.01.03.10.xlsx"  # BFS Strukturerhebung (SE)
DEFAULT_BLATT = "2024"

# ISCO-Hauptgruppe → Qualifikation
QUALIFIKATION_MAP = {
    "1": "Tertiär",
    "2": "Tertiär",
    "3": "Sekundär II",
    "4": "Sekundär II",
    "5": "Sekundär II",
    "6": "Sekundär II",
    "7": "Sekundär II",
    "8": "Sekundär II",
    "9": "Keine Ausbildung",
    "0": "Sekundär II",
}

# ISCO-Präfix (2-, 3- oder 4-stellig) → Branche
#
# Auflösung über den längsten passenden Präfix (siehe branche_fuer_isco): ein 4-stelliger
# Eintrag schlägt einen 3-stelligen, dieser einen 2-stelligen. So lassen sich heterogene
# Untergruppen (z. B. 13 «Führungskräfte in Produktion und spezialisierten Dienstleistungen»)
# sauber nach Wirtschaftszweig aufteilen. Branchennamen = die 21 Branchen aus
# ch_adjustments.BRANCHENEFFEKTE; die Abgrenzung folgt, wo möglich, der NOGA-Zuordnung in
# fetch_bgs.py / fetch_statent.py (z. B. NOGA 46 Grosshandel → Dienstleistungen,
# NOGA 87 Heime → Soziales, NOGA 81 Gebäudebetreuung → Dienstleistungen).
# Gilt nur für automatisch ergänzte Berufe; die kuratierte Liste in build_berufeliste.py
# hat eigene, manuell gesetzte Branchen.
BRANCHE_MAP = {
    # --- 2-stellige Untergruppen (Grundzuordnung) ---
    "11": "Verwaltung", "12": "Verwaltung",
    "13": "Dienstleistungen",  # nur Fallback; alle Gattungen unten nach Branche aufgeteilt
    "14": "Dienstleistungen",  # nur Fallback; 141/142/143 unten
    "21": "Industrie", "22": "Gesundheit", "23": "Bildung", "24": "Finanzen",
    "25": "ICT", "26": "Medien",
    "31": "Industrie", "32": "Gesundheit", "33": "Finanzen", "34": "Soziales",
    "35": "ICT",
    "41": "Verwaltung", "42": "Verwaltung", "43": "Verwaltung", "44": "Verwaltung",
    "51": "Gastgewerbe", "52": "Detailhandel", "53": "Soziales", "54": "Öff. Verwaltung",
    "61": "Landwirtschaft", "62": "Landwirtschaft", "63": "Landwirtschaft",
    "71": "Bau", "72": "Industrie", "73": "Industrie", "74": "Industrie",
    "75": "Industrie",  # Nahrungsmittel-, Holz-, Textilverarbeitung = verarb. Gewerbe (NOGA 10–16)
    "81": "Industrie", "82": "Industrie", "83": "Transport",
    "91": "Dienstleistungen",
    "92": "Landwirtschaft",  # Hilfsarbeitskräfte in Land-/Forstwirtschaft, Fischerei
    "93": "Industrie", "94": "Gastgewerbe",
    "95": "Dienstleistungen", "96": "Dienstleistungen",
    "01": "Öff. Verwaltung", "02": "Öff. Verwaltung", "03": "Öff. Verwaltung",  # Armee

    # --- 1: Führungskräfte ---
    "111": "Öff. Verwaltung",   # Legislative, leitende Verwaltungsbedienstete (NOGA 84)
    "1114": "Verwaltung",       # Leitende Funktionäre von Interessenverbänden (NOGA 94)
    "131": "Landwirtschaft",    # Produktionsleiter Land-/Forstwirtschaft, Fischerei
    "1321": "Industrie",        # Produktion von Waren
    "1322": "Industrie",        # Bergbau (NOGA 05–09 → Industrie)
    "1323": "Bau",              # Produktion im Bau
    "1324": "Transport",        # Beschaffung, Logistik, Distribution
    "133": "ICT",               # Dienstleistungen der Informations- und Kommunikationstechnologie
    "1341": "Soziales",         # Kinderbetreuung
    "1342": "Gesundheit",       # Gesundheitswesen
    "1343": "Soziales",         # Altenbetreuung (Heime, NOGA 87 → Soziales)
    "1344": "Soziales",         # Sozialwesen
    "1345": "Bildung",          # Bildungswesen
    "1346": "Finanzen",         # Finanz- und Versicherungsdienstleistungen (Filialleitung)
    "1349": "Dienstleistungen", # sonstige spezialisierte Dienstleistungen
    "141": "Gastgewerbe",       # Hotels und Restaurants
    "142": "Detailhandel",      # Gross- und Einzelhandel
    "143": "Dienstleistungen",  # Sport-, Freizeit-, Kultureinrichtungen, sonstige Dienstleistungen

    # --- 2: Akademische Berufe ---
    "2132": "Landwirtschaft",   # Agrar-, Forst-, Fischereiwissenschaftler
    "2133": "Umwelt",           # Umweltschutzfachleute
    "2142": "Bau",              # Bauingenieure
    "2143": "Umwelt",           # Umweltingenieure
    "2161": "Bau", "2162": "Bau", "2164": "Bau", "2165": "Bau",  # Architektur, Raumplanung, Vermessung
    "2166": "Medien",           # Grafik- und Multimediadesigner
    "2421": "Beratung",         # Management- und Organisationsanalytiker (NOGA 70)
    "2422": "Öff. Verwaltung",  # Fachkräfte in der Politikverwaltung
    "2423": "Verwaltung",       # Personalwesen und Berufsberatung (HR-Funktion)
    "2424": "Verwaltung",       # Personalschulung und -entwicklung (HR-Funktion)
    "243": "Medien",            # Marketing, Werbung, PR (NOGA 73 → Medien)
    "2433": "Dienstleistungen", # Technische Verkaufsfachkräfte (Grosshandel, NOGA 46)
    "2434": "ICT",              # ICT-Verkaufsfachkräfte
    "261": "Recht",             # Juristen
    "2634": "Gesundheit",       # Psychologen
    "2635": "Soziales",         # Sozialarbeit
    "2636": "Dienstleistungen", # Geistliche, Seelsorger

    # --- 3: Techniker und gleichrangige Berufe ---
    "3112": "Bau",              # Bautechniker
    "3123": "Bau",              # Bauführer, Aufsichtskräfte im Bau
    "315": "Transport",         # Schiffs-/Luftfahrzeugführer, Fluglotsen
    "332": "Dienstleistungen",  # Ein-/Verkaufsagenten, Handelsmakler (Grosshandel, NOGA 46)
    "3321": "Versicherungen",   # Versicherungsvertreter
    "333": "Dienstleistungen",  # Unternehmensbezogene Dienstleistungen (Veranstaltungen, Vermittlung)
    "3331": "Transport",        # Speditions- und Zollagenten
    "3334": "Immobilien",       # Immobilienmakler und -verwalter
    "334": "Verwaltung",        # Sekretariatsfachkräfte, Büroleitung
    "3342": "Recht",            # Sekretariatsfachkräfte im Rechtswesen
    "3344": "Gesundheit",       # Sekretariatsfachkräfte im Gesundheitswesen
    "335": "Öff. Verwaltung",   # Verwaltungsfachkräfte der öffentlichen Hand (Zoll, Steuer, Sozialversicherung, Polizei)
    "3411": "Recht",            # Fachkräfte für Rechtsangelegenheiten
    "3413": "Dienstleistungen", # Nicht akademische Fachkräfte im religiösen Bereich
    "342": "Dienstleistungen",  # Sport und Fitness (NOGA 93)
    "343": "Medien",            # Künstlerische und kulturelle Fachkräfte (NOGA 90)
    "3432": "Dienstleistungen", # Raumgestalter, Dekorateure (Design, NOGA 74)
    "3434": "Gastgewerbe",      # Küchenchefs

    # --- 4: Bürokräfte ---
    "4211": "Finanzen",         # Bankschalter, Finanzdienstleistungen (NOGA 64)
    "4412": "Transport",        # Postverteiler und -sortierer (NOGA 53, wie Posthalter/in)

    # --- 5: Dienstleistungs- und Verkaufsberufe ---
    "511": "Transport",         # Flugbegleiter, Zugbegleiter, Schaffner
    "5113": "Gastgewerbe",      # Reiseleiter (Tourismus, NOGA 79)
    "514": "Dienstleistungen",  # Coiffeure, Kosmetiker (NOGA 96)
    "515": "Dienstleistungen",  # Hauswarte, Reinigungs-/Hauswirtschaftsleitung (NOGA 81)
    "516": "Dienstleistungen",  # sonstige personenbezogene Dienstleistungen
    "532": "Gesundheit",        # Betreuungsberufe im Gesundheitswesen (Pflegehilfe, Spitex)
    "5414": "Sicherheit",       # Wachpersonal (NOGA 80)

    # --- 7/8: Handwerk, Anlagen- und Maschinenbedienung ---
    "7411": "Bau",              # Elektroinstallateure (Gebäude)
    "8341": "Landwirtschaft",   # Führer land- und forstwirtschaftlicher Maschinen
    "8342": "Bau",              # Erdbewegungs- und Strassenbaumaschinen

    # --- 9: Hilfsarbeitskräfte ---
    "931": "Bau",               # Hilfsarbeiter im Hoch- und Tiefbau
    "9311": "Industrie",        # Hilfsarbeiter im Bergbau
    "933": "Transport",         # Hilfsarbeiter in Transport und Lagerei
    "961": "Umwelt",            # Abfallentsorgung (NOGA 38)
}
BRANCHE_DEFAULT = "Dienstleistungen"

# Löhne: BFS LSE 2024 (2-stellige Gruppe × 12, Fallback 1-stellig/Total) aus
# update_loehne.py. Die frühere, geschätzte LOHN_MAP («LSE 2022, geschätzt») ist entfernt.
# Salarium-Profile für heterogene Gruppen setzt erst update_loehne.py.


def parse_bfs_excel(filepath: Path, blatt: str = DEFAULT_BLATT) -> pd.DataFrame:
    """BFS-SE-Excel einlesen, 4-stellige Berufsgattungen extrahieren.

    Args:
        filepath: Pfad zur BFS-Excel-Datei (su-d-40.02.03.02.01.03.10.xlsx).
        blatt: Name des Tabellenblatts, z. B. "2024" (Einzeljahr) oder
               "2022-2024" (gepoolte Mehrjahresauswertung).
    """
    df = pd.read_excel(filepath, sheet_name=str(blatt), header=None)
    mask = df[3].notna() & df[4].isna()
    bfs = df[mask][[3, 5, 6, 7, 8]].copy()
    bfs.columns = ["isco_code", "beruf_bfs", "beschaeftigte_total", "maenner", "frauen"]
    bfs = bfs.replace("X", np.nan)
    bfs["beschaeftigte_total"] = pd.to_numeric(bfs["beschaeftigte_total"], errors="coerce")
    bfs["frauen"] = pd.to_numeric(bfs["frauen"], errors="coerce")
    bfs["frauen_pct"] = (bfs["frauen"] / bfs["beschaeftigte_total"] * 100).round(1)
    bfs["isco_code"] = bfs["isco_code"].astype(str)
    return bfs.dropna(subset=["beschaeftigte_total"])


def branche_fuer_isco(isco_code: str) -> str:
    """Branche über den längsten passenden ISCO-Präfix (4 → 3 → 2 Stellen) bestimmen."""
    code = str(isco_code).strip()
    for laenge in (4, 3, 2):
        if len(code) >= laenge and code[:laenge] in BRANCHE_MAP:
            return BRANCHE_MAP[code[:laenge]]
    return BRANCHE_DEFAULT


def assign_metadata(isco_code: str) -> tuple[str, str, int]:
    """Branche, Qualifikation, Lohn (LSE 2024, siehe update_loehne.py) aus ISCO-Code ableiten."""
    major = isco_code[0] if isco_code else "9"
    branche = branche_fuer_isco(isco_code)
    qualifikation = QUALIFIKATION_MAP.get(major, "Sekundär II")
    lohn, _ = lse_basislohn(isco_code, _lse())
    return branche, qualifikation, lohn


@lru_cache(maxsize=1)
def _lse() -> dict[str, int]:
    return lade_lse(schreiben=False)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="BFS Strukturerhebung (SE) einlesen und berufe_ch.csv aktualisieren."
    )
    parser.add_argument(
        "--blatt",
        default=DEFAULT_BLATT,
        help=f'Tabellenblatt der BFS-Datei, z. B. "2024" oder "2022-2024" (Default: "{DEFAULT_BLATT}")',
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    bfs = parse_bfs_excel(BFS_FILE, blatt=args.blatt)
    print(f"✓ BFS Strukturerhebung (SE), Blatt «{args.blatt}»: {len(bfs)} Berufsgattungen gelesen")
    existing = pd.read_csv(PROCESSED_PATH / "berufe_ch.csv")
    existing["beschaeftigte_1000"] = existing["beschaeftigte_1000"].astype(float)
    existing["frauen_pct"] = existing["frauen_pct"].astype(float)

    # Bestehende Beschäftigte/Frauen% mit BFS-Daten aktualisieren
    bfs_lookup = bfs.set_index("isco_code")[["beschaeftigte_total", "frauen_pct"]]
    updated = 0
    for idx, row in existing.iterrows():
        code = str(row["isco_code"])
        if code in bfs_lookup.index:
            real_beschaeftigte = bfs_lookup.loc[code, "beschaeftigte_total"]
            real_frauen = bfs_lookup.loc[code, "frauen_pct"]
            existing.at[idx, "beschaeftigte_1000"] = round(real_beschaeftigte, 1)
            if not np.isnan(real_frauen):
                existing.at[idx, "frauen_pct"] = real_frauen
            updated += 1
    print(f"✓ {updated} bestehende Einträge mit BFS-SE-Daten aktualisiert")

    # Neue Berufe (>= 5000, nicht vorhanden)
    existing_isco = set(existing["isco_code"].astype(str))
    exclude_terms = ["onA", "anderweitig nicht genannt", "ohne nähere Angabe"]
    new_candidates = bfs[
        (bfs["beschaeftigte_total"] >= 5.0)
        & (~bfs["isco_code"].isin(existing_isco))
        & (~bfs["beruf_bfs"].str.contains("|".join(exclude_terms), na=False))
    ].copy()

    new_rows = []
    for _, row in new_candidates.iterrows():
        branche, qualifikation, lohn = assign_metadata(str(row["isco_code"]))
        new_rows.append({
            "beruf": row["beruf_bfs"],
            "isco_code": row["isco_code"],
            "beschaeftigte_1000": round(row["beschaeftigte_total"], 1),
            "frauen_pct": row["frauen_pct"],
            "branche": branche,
            "lohn_median_chf": lohn,
            "lohn_quelle": lse_basislohn(str(row["isco_code"]), _lse())[1],
            "qualifikation": qualifikation,
        })

    new_df = pd.DataFrame(new_rows)
    combined = pd.concat([existing, new_df], ignore_index=True)
    combined = combined.sort_values("beschaeftigte_1000", ascending=False).reset_index(drop=True)

    combined.to_csv(PROCESSED_PATH / "berufe_ch.csv", index=False)
    print(f"✓ {len(new_df)} neue Berufe hinzugefügt")
    print(f"✓ berufe_ch.csv gespeichert: {len(combined)} Berufe total")
    print("→ Löhne inkl. Salarium-Profile: python src/data/update_loehne.py --offline")


if __name__ == "__main__":
    main()
