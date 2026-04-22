"""
fetch_bgs.py — Grenzgänger-Anteil pro Branche aus BFS BGS (Grenzgängerstatistik)

Quelle: BFS Grenzgängerstatistik (BGS), Cube DF_GGS_4
        „Ausländische Grenzgänger/-innen nach Wirtschaftszweig und Erwerbsstatus"
        Manueller Download als CSV von https://stats.swiss
        (Dataflow CH1.GGS,DF_GGS_4,1.0.0+all.csv)

Input:  data/raw/bgs_grenzgaenger_noga.csv  (Rohdaten, 2-stelliger NOGA-Code)
Output: data/processed/grenzgaenger_anteil_branche.csv
Spalten: branche, grenzgaenger, beschaeftigte_total, grenzgaenger_anteil

Berechnung:
    grenzgaenger_anteil = grenzgaenger_in_branche / beschaeftigte_branche_sake

Fallback: Falls die Rohdatei fehlt (z.B. in CI), werden realistische
          Schätzwerte basierend auf bekannten CH-Statistiken verwendet.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROCESSED_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "processed"
RAW_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "raw"
SCORES_PATH = PROCESSED_DATA_PATH / "scores.csv"
KMU_PATH = PROCESSED_DATA_PATH / "kmu_anteil_branche.csv"
BGS_RAW_PATH = RAW_DATA_PATH / "bgs_grenzgaenger_noga.csv"

# NOGA-Abteilung (2-stellig) → interne Branche
# Gleiche Zuordnung wie in fetch_statent.py
NOGA_ZU_BRANCHE: dict[str, str] = {
    # Landwirtschaft / Forstwirtschaft / Fischerei
    "01": "Landwirtschaft",
    "02": "Landwirtschaft",
    "03": "Landwirtschaft",
    # Bergbau → Industrie
    "05": "Industrie",
    "06": "Industrie",
    "07": "Industrie",
    "08": "Umwelt",
    "09": "Industrie",
    # Verarbeitendes Gewerbe
    "10": "Industrie",
    "11": "Industrie",
    "12": "Industrie",
    "13": "Industrie",
    "14": "Industrie",
    "15": "Industrie",
    "16": "Industrie",
    "17": "Industrie",
    "18": "Medien",
    "19": "Industrie",
    "20": "Industrie",
    "21": "Industrie",
    "22": "Industrie",
    "23": "Industrie",
    "24": "Industrie",
    "25": "Industrie",
    "26": "ICT",
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
    "45": "Detailhandel",
    "46": "Dienstleistungen",
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
    "72": "Dienstleistungen",
    "73": "Medien",
    "74": "Dienstleistungen",
    "75": "Gesundheit",
    # Sonstige wirtschaftliche Dienstleistungen
    "77": "Dienstleistungen",
    "78": "Dienstleistungen",
    "79": "Gastgewerbe",
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

# Realistische Grenzgänger-Anteile pro interner Branche
# Basierend auf BFS BGS-Auswertungen (Gesamtbestand ~380'000 Grenzgänger, 2023)
# Anteil = Grenzgänger / Gesamtbeschäftigte in der Branche (SAKE-Basis)
BRANCHE_FALLBACK_ANTEIL: dict[str, float] = {
    "Bau": 0.18,              # Bauhaupt- und Ausbaugewerbe: viele Grenzgänger aus F/I/D
    "Industrie": 0.15,        # MEM, Pharma, Chemie: hoher Grenzgängeranteil (Genf, Basel, Tessin)
    "Gastgewerbe": 0.14,      # Gastronomie/Hotellerie: saisonal, Grenzregionen
    "Transport": 0.11,        # Logistik, Spedition, Strassengüterverkehr
    "Gesundheit": 0.10,       # Spitäler in Grenzregionen (Genf, Basel): hoher Anteil
    "Detailhandel": 0.09,     # Einkaufstourismus-Effekt, Grenznahe Läden
    "Soziales": 0.09,         # Soziale Arbeit, Kinderbetreuung in Grenzregionen
    "ICT": 0.08,              # Tech-Hubs (Zürich, Genf): internationale Fachkräfte
    "Dienstleistungen": 0.08, # Heterogener Bereich, moderater Anteil
    "Landwirtschaft": 0.12,   # Saisonarbeit, v.a. aus Nachbarländern
    "Finanzen": 0.07,         # Bankensektor: v.a. Genf (Frankreich-Grenze)
    "Versicherungen": 0.06,   # Strukturierter Sektor, moderater Grenzgängeranteil
    "Recht": 0.06,            # Anwaltskanzleien, Notariate: eher inländisch
    "Beratung": 0.06,         # Unternehmensberatung: internationale Fachkräfte
    "Bildung": 0.05,          # Schulen: meist mit CH-Abschluss
    "Verwaltung": 0.04,       # Private Verwaltung, Verbände
    "Öff. Verwaltung": 0.04,  # Öffentlicher Dienst: Bürgerschaftspflicht bei Kantonen
    "Immobilien": 0.05,       # Immobilienverwaltung, Makler
    "Umwelt": 0.07,           # Entsorgung, Energie: technische Fachkräfte
    "Sicherheit": 0.05,       # Bewachung, Schutz: teils Grenzgänger
    "Medien": 0.04,           # Verlage, TV, Radio: eher inländisch oder Expatriates
}


def _load_bgs_from_csv(path: Path = BGS_RAW_PATH) -> pd.DataFrame | None:
    """
    Lädt BGS-Rohdaten (Cube DF_GGS_4) aus dem manuellen CSV-Download von stats.swiss
    und aggregiert auf interne Branchen.

    Das Rohformat hat eine Zeile pro (NOGA-Abteilung, Erwerbsstatus, Quartal):
        - NOGA                 2-stelliger Code (z.B. "23"), "_T" = Total
        - AUFZW                Erwerbsstatus ("_T" = Total, sonst Stati)
        - TIME_PERIOD          z.B. "2025-Q4"
        - OBS_VALUE            Anzahl Grenzgänger/-innen (VZÄ-normalisiert, Dezimal)

    Wir filtern auf Erwerbsstatus=Total (_T), aggregieren pro NOGA auf das
    letzte verfügbare Quartal und mappen NOGA → interne Branche.

    Returns:
        DataFrame mit Spalten [branche, grenzgaenger] oder None bei Fehler.
    """
    if not path.exists():
        return None

    try:
        df = pd.read_csv(path, dtype={"NOGA": str, "AUFZW": str}, low_memory=False)
    except Exception as exc:
        logger.warning(f"Konnte BGS-Rohdatei nicht lesen: {path}: {exc}")
        return None

    required_cols = {"NOGA", "AUFZW", "TIME_PERIOD", "OBS_VALUE"}
    missing = required_cols - set(df.columns)
    if missing:
        logger.warning(f"BGS-Rohdatei unvollständig — fehlende Spalten: {missing}")
        return None

    total_mask = (df["AUFZW"] == "_T") & (df["NOGA"] != "_T")
    snapshot = df[total_mask].copy()
    if snapshot.empty:
        logger.warning("BGS-Rohdatei enthält keine Zeilen mit AUFZW=_T.")
        return None

    latest_period = sorted(snapshot["TIME_PERIOD"].unique())[-1]
    latest = snapshot[snapshot["TIME_PERIOD"] == latest_period].copy()
    latest["branche"] = latest["NOGA"].str.zfill(2).map(NOGA_ZU_BRANCHE)
    latest = latest.dropna(subset=["branche"])

    result = (
        latest.groupby("branche", as_index=False)["OBS_VALUE"]
        .sum()
        .rename(columns={"OBS_VALUE": "grenzgaenger"})
    )
    logger.info(
        f"BGS CSV geladen: {len(result)} Branchen aggregiert "
        f"(Quartal {latest_period}, Total: {int(result['grenzgaenger'].sum()):,} Grenzgänger)"
    )
    return result


def _load_sake_beschaeftigte() -> dict[str, float]:
    """
    Lädt die Beschäftigten-Totale pro Branche.

    Bevorzugt STATENT (`kmu_anteil_branche.csv`): sektorweite Gesamtbeschäftigung
    aller Betriebe gemäss BFS BZ/STATENT — korrekter Nenner für den Grenzgänger-Anteil,
    weil BGS ebenfalls sektorweit zählt. Fallback: Summe der Beschäftigten der 204
    Berufe aus `scores.csv` (unvollständig, nur als Notbehelf).

    Returns:
        dict: branche → Gesamtbeschäftigte (absolute Zahl)
    """
    if KMU_PATH.exists():
        df = pd.read_csv(KMU_PATH)
        if "beschaeftigte_total" in df.columns:
            return dict(zip(df["branche"], df["beschaeftigte_total"].astype(float)))
        logger.warning(
            f"{KMU_PATH.name} ohne Spalte 'beschaeftigte_total' — falle auf scores.csv zurück."
        )

    if not SCORES_PATH.exists():
        logger.warning(f"Weder {KMU_PATH.name} noch scores.csv gefunden — Nenner fehlt.")
        return {}

    logger.warning(
        f"{KMU_PATH.name} nicht vorhanden — verwende SAKE-Beschäftigtenzahl aus scores.csv "
        "(unterschätzt Sektorgesamtheit, Anteil wird zu hoch)."
    )
    df = pd.read_csv(SCORES_PATH)
    return (
        df.groupby("branche")["beschaeftigte_1000"]
        .sum()
        .mul(1000)
        .to_dict()
    )


def compute_grenzgaenger_anteil(use_fallback: bool = False) -> pd.DataFrame:
    """
    Berechnet den Grenzgänger-Anteil pro interner Branche.

    Args:
        use_fallback: Wenn True, werden direkt die Fallback-Schätzwerte verwendet
                      (ohne API-Aufruf). Nützlich für Tests.

    Returns:
        DataFrame mit Spalten:
            branche, grenzgaenger, beschaeftigte_total, grenzgaenger_anteil
    """
    # Beschäftigtenzahlen aus SAKE
    sake_beschaeftigte = _load_sake_beschaeftigte()

    # Alle 21 internen Branchen aus NOGA_ZU_BRANCHE
    alle_branchen = sorted(set(NOGA_ZU_BRANCHE.values()))

    bgs_df: pd.DataFrame | None = None
    if not use_fallback:
        bgs_df = _load_bgs_from_csv()

    if bgs_df is not None:
        logger.info("Verwende reale BGS-Daten aus stats.swiss CSV (DF_GGS_4).")
        bgs_map = dict(zip(bgs_df["branche"], bgs_df["grenzgaenger"]))
    else:
        if not use_fallback:
            logger.warning(
                f"BGS-Rohdaten nicht gefunden unter {BGS_RAW_PATH} — verwende FALLBACK-SCHÄTZWERTE. "
                "Diese basieren auf bekannten CH-Statistiken (~380'000 Grenzgänger) "
                "und sind KEINE offiziellen BFS-Zahlen."
            )
        bgs_map = None

    records = []
    for branche in alle_branchen:
        # Beschäftigte aus SAKE (absolute Zahl)
        beschaeftigte_total = sake_beschaeftigte.get(branche, 0.0)

        if bgs_map is not None:
            # Reale Grenzgängerzahl aus PxWeb
            grenzgaenger = float(bgs_map.get(branche, 0))
        else:
            # Fallback: Anteil × Beschäftigte
            anteil_fallback = BRANCHE_FALLBACK_ANTEIL.get(branche, 0.05)
            if beschaeftigte_total > 0:
                grenzgaenger = round(anteil_fallback * beschaeftigte_total)
            else:
                # Keine SAKE-Daten: Schätzwert basierend auf CH-Durchschnitt
                grenzgaenger = 0.0

        if beschaeftigte_total > 0:
            anteil = grenzgaenger / beschaeftigte_total
        else:
            anteil = BRANCHE_FALLBACK_ANTEIL.get(branche, 0.05)

        records.append(
            {
                "branche": branche,
                "grenzgaenger": int(grenzgaenger),
                "beschaeftigte_total": int(beschaeftigte_total) if beschaeftigte_total > 0 else 0,
                "grenzgaenger_anteil": round(anteil, 4),
            }
        )

    df = pd.DataFrame(records)
    return df.sort_values("grenzgaenger_anteil", ascending=False).reset_index(drop=True)


def main() -> None:
    logger.info("Berechne Grenzgänger-Anteil pro Branche …")

    df = compute_grenzgaenger_anteil(use_fallback=False)

    # Vollständigkeitsprüfung
    expected_branchen = set(NOGA_ZU_BRANCHE.values())
    found_branchen = set(df["branche"])
    if missing := expected_branchen - found_branchen:
        logger.warning(f"Keine Daten für Branchen: {missing}")

    out_path = PROCESSED_DATA_PATH / "grenzgaenger_anteil_branche.csv"
    df.to_csv(out_path, index=False)
    logger.info(f"Gespeichert: {out_path}")

    logger.info("\nGrenzgänger-Anteil pro Branche:")
    for _, row in df.iterrows():
        bar = "█" * int(row["grenzgaenger_anteil"] * 50)
        logger.info(
            f"  {row['branche']:20s} {row['grenzgaenger_anteil']:5.1%}  "
            f"({row['grenzgaenger']:>7,.0f} Grenzgänger)  {bar}"
        )


if __name__ == "__main__":
    main()
