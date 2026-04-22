"""
fetch_statent.py — Grossfirmen-Anteil pro Branche aus BFS BZ/STATENT

Quelle: BFS Betriebszählung 2008 (BZ), Tabelle px-x-0602050000_102
        "Arbeitsstätten und Beschäftigte nach Kanton, Wirtschaftsabteilung und Grössenklasse"
Hinweis: STATENT (ab 2011) publiziert kein Kreuztab Wirtschaftsabteilung × Grössenklasse
         mit der ≥250-Klasse via öffentlicher API. Strukturmuster (Grossfirmen-Anteil pro
         Branche) gelten als langfristig stabil und rechtfertigen die BZ-2008-Basis.

Output: data/processed/kmu_anteil_branche.csv
Spalten: branche, beschaeftigte_total, beschaeftigte_gross, grossfirmen_anteil
"""

from __future__ import annotations

import json
import logging
import urllib.request
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PXWEB_URL = (
    "https://www.pxweb.bfs.admin.ch/api/v1/de/"
    "px-x-0602050000_102/px-x-0602050000_102.px"
)

PROCESSED_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "processed"

# NOGA-Abteilung (2-stellig) → interne Branche
# Alle 85 in der BZ-Tabelle enthaltenen Abteilungen sind gemappt.
# Abteilungen die mehreren internen Branchen zuzuordnen wären, erhalten
# die dominante Branche nach Beschäftigtenzahl.
NOGA_ZU_BRANCHE: dict[str, str] = {
    # Landwirtschaft / Forstwirtschaft / Fischerei
    "01": "Landwirtschaft",
    "02": "Landwirtschaft",
    "03": "Landwirtschaft",
    # Bergbau → Industrie (klein, aber Rohstoffgewinnung)
    "05": "Industrie",
    "06": "Industrie",
    "07": "Industrie",
    "08": "Umwelt",
    "09": "Industrie",
    # Verarbeitendes Gewerbe (MEM, Pharma, Chemie, Nahrungsmittel …)
    "10": "Industrie",
    "11": "Industrie",
    "12": "Industrie",
    "13": "Industrie",
    "14": "Industrie",
    "15": "Industrie",
    "16": "Industrie",
    "17": "Industrie",
    "18": "Medien",       # Druck / Vervielfältigung → Medien
    "19": "Industrie",
    "20": "Industrie",
    "21": "Industrie",    # Pharma → Industrie (Roche, Novartis)
    "22": "Industrie",
    "23": "Industrie",
    "24": "Industrie",
    "25": "Industrie",
    "26": "ICT",          # Elektronik/Optik → ICT-nah
    "27": "Industrie",
    "28": "Industrie",
    "29": "Industrie",
    "30": "Industrie",
    "31": "Industrie",
    "32": "Industrie",
    "33": "Industrie",
    # Energie / Wasser / Abfall
    "35": "Umwelt",
    "36": "Umwelt",
    "37": "Umwelt",
    "38": "Umwelt",
    "39": "Umwelt",
    # Bau
    "41": "Bau",
    "42": "Bau",
    "43": "Bau",
    # Handel
    "45": "Detailhandel",  # Autohandel
    "46": "Dienstleistungen",  # Grosshandel → Dienstleistungen
    "47": "Detailhandel",
    # Transport / Logistik
    "49": "Transport",
    "50": "Transport",
    "51": "Transport",
    "52": "Transport",
    "53": "Transport",
    # Gastgewerbe
    "55": "Gastgewerbe",
    "56": "Gastgewerbe",
    # Medien / ICT
    "58": "Medien",
    "59": "Medien",
    "60": "Medien",
    "61": "ICT",
    "62": "ICT",
    "63": "ICT",
    # Finanz- und Versicherungsdienstleistungen
    "64": "Finanzen",
    "65": "Versicherungen",
    "66": "Finanzen",
    # Immobilien
    "68": "Immobilien",
    # Freiberufliche / wissenschaftliche / technische Tätigkeiten
    "69": "Recht",
    "70": "Beratung",
    "71": "Beratung",
    "72": "Dienstleistungen",  # Forschung & Entwicklung
    "73": "Medien",            # Werbung
    "74": "Dienstleistungen",
    "75": "Gesundheit",        # Veterinärwesen
    # Sonstige wirtschaftliche Dienstleistungen
    "77": "Dienstleistungen",
    "78": "Dienstleistungen",
    "79": "Gastgewerbe",       # Reisebüros → Gastgewerbe-nah
    "80": "Sicherheit",
    "81": "Dienstleistungen",
    "82": "Dienstleistungen",
    # Öffentliche Verwaltung
    "84": "Öff. Verwaltung",
    # Bildung
    "85": "Bildung",
    # Gesundheit / Soziales
    "86": "Gesundheit",
    "87": "Soziales",
    "88": "Soziales",
    # Kultur / Sport / Unterhaltung
    "90": "Medien",
    "91": "Bildung",
    "92": "Dienstleistungen",
    "93": "Dienstleistungen",
    # Interessenvertretungen / persönliche Dienstleistungen
    "94": "Verwaltung",
    "95": "Dienstleistungen",
    "96": "Dienstleistungen",
}

# NOGA-Codes für Grössenklasse-Werte (aus PxWeb-Metadaten)
GROSSFIRMEN_KEY = "4"   # "250 Vollzeitäquivalente und mehr"
SCHWEIZ_KANTON = "0"
JAHR_2008 = "3"         # Schlüssel für 2008 in der PxWeb-Tabelle
BESCHAEFTIGTE_TOTAL = "1"  # Variable-Code


def _fetch_bz_data() -> list[dict]:
    """Lädt BZ-2008-Daten (Wirtschaftsabteilung × Grössenklasse) via PxWeb-API."""
    query = {
        "query": [
            {"code": "Jahr", "selection": {"filter": "item", "values": [JAHR_2008]}},
            {"code": "Kanton", "selection": {"filter": "item", "values": [SCHWEIZ_KANTON]}},
            {"code": "Wirtschaftsabteilung", "selection": {"filter": "all", "values": ["*"]}},
            {"code": "Grössenklasse", "selection": {"filter": "all", "values": ["*"]}},
            {"code": "Variable", "selection": {"filter": "item", "values": [BESCHAEFTIGTE_TOTAL]}},
        ],
        "response": {"format": "json"},
    }
    payload = json.dumps(query).encode()
    req = urllib.request.Request(
        PXWEB_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())["data"]


def build_kmu_table(raw_rows: list[dict]) -> pd.DataFrame:
    """
    Berechnet Grossfirmen-Anteil (≥250 VZÄ) pro interner Branche.

    Args:
        raw_rows: Rohdaten aus PxWeb-API (key: [Jahr, Kanton, WirtAbt, Grössenklasse, Variable])

    Returns:
        DataFrame mit Spalten: branche, beschaeftigte_total, beschaeftigte_gross,
                               grossfirmen_anteil
    """
    records: list[dict] = []
    for row in raw_rows:
        noga = row["key"][2]          # Wirtschaftsabteilung
        groesse = row["key"][3]       # Grössenklasse (1-4)
        beschaeftigte = int(row["values"][0]) if row["values"][0] else 0
        branche = NOGA_ZU_BRANCHE.get(noga)
        if branche is None:
            logger.warning(f"NOGA {noga} nicht gemappt — übersprungen")
            continue
        records.append({
            "noga": noga,
            "branche": branche,
            "groesse": groesse,
            "beschaeftigte": beschaeftigte,
        })

    df = pd.DataFrame(records)
    total = df.groupby("branche")["beschaeftigte"].sum().rename("beschaeftigte_total")
    gross = (
        df[df["groesse"] == GROSSFIRMEN_KEY]
        .groupby("branche")["beschaeftigte"]
        .sum()
        .rename("beschaeftigte_gross")
    )
    result = pd.concat([total, gross], axis=1).fillna(0)
    result["grossfirmen_anteil"] = (
        result["beschaeftigte_gross"] / result["beschaeftigte_total"]
    ).round(4)
    return result.reset_index()


def main() -> None:
    logger.info("Lade BZ-2008-Daten von PxWeb …")
    raw = _fetch_bz_data()
    logger.info(f"  {len(raw)} Datenpunkte empfangen.")

    kmu_df = build_kmu_table(raw)

    # Vollständigkeit prüfen
    expected = set(NOGA_ZU_BRANCHE.values())
    found = set(kmu_df["branche"])
    if missing := expected - found:
        logger.warning(f"Keine Daten für Branchen: {missing}")

    out_path = PROCESSED_DATA_PATH / "kmu_anteil_branche.csv"
    kmu_df.to_csv(out_path, index=False)
    logger.info(f"Gespeichert: {out_path}")

    logger.info("\nGrossfirmen-Anteil (≥250 VZÄ) pro Branche (BZ 2008):")
    for _, row in kmu_df.sort_values("grossfirmen_anteil", ascending=False).iterrows():
        bar = "█" * int(row["grossfirmen_anteil"] * 20)
        logger.info(
            f"  {row['branche']:20s} {row['grossfirmen_anteil']:5.1%}  {bar}"
        )


if __name__ == "__main__":
    main()
