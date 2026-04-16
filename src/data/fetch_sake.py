"""
BFS SAKE (Schweizerische Arbeitskräfteerhebung) – Daten laden und aufbereiten.

Manuelle Download-Schritte (API nicht öffentlich verfügbar):
1. https://www.bfs.admin.ch/bfs/de/home/statistiken/arbeit-erwerb/erhebungen/sake.html
2. Tabelle: "Erwerbstätige nach Beruf (ISCO-08)" → Excel herunterladen
3. Datei unter data/raw/sake_berufe.xlsx ablegen

Diese Datei liest das Excel und bereitet es auf.
"""

import pandas as pd
from pathlib import Path

RAW_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "raw"
PROCESSED_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "processed"


def load_sake_data(filepath: str | None = None) -> pd.DataFrame:
    """
    SAKE Excel-Datei laden. Erwartet Spalten:
    - Berufsbezeichnung (ISCO-08 Bezeichnung)
    - ISCO-Code
    - Beschäftigte Total (in 1000)
    - davon Frauen (%)
    """
    if filepath is None:
        filepath = RAW_DATA_PATH / "sake_berufe.xlsx"

    df = pd.read_excel(filepath, skiprows=3)  # BFS-Dateien haben oft Header-Zeilen

    # Spalten umbenennen (anpassen nach tatsächlicher Datei)
    df = df.rename(columns={
        df.columns[0]: "beruf",
        df.columns[1]: "isco_code",
        df.columns[2]: "beschaeftigte_1000",
        df.columns[3]: "frauen_anteil_pct",
    })

    df = df.dropna(subset=["beruf", "beschaeftigte_1000"])
    df["beschaeftigte_1000"] = pd.to_numeric(df["beschaeftigte_1000"], errors="coerce")
    df = df[df["beschaeftigte_1000"] > 0]
    df = df.sort_values("beschaeftigte_1000", ascending=False)

    return df


def get_top_jobs(n: int = 150) -> pd.DataFrame:
    """Top N Berufe nach Beschäftigtenzahl zurückgeben."""
    df = load_sake_data()
    return df.head(n).reset_index(drop=True)


def save_processed(df: pd.DataFrame, filename: str = "berufe_ch.csv") -> None:
    PROCESSED_DATA_PATH.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED_DATA_PATH / filename, index=False)
    print(f"Gespeichert: {PROCESSED_DATA_PATH / filename}")


if __name__ == "__main__":
    # Für Tests: Platzhalter-Daten generieren bis echte SAKE-Daten vorliegen
    placeholder = pd.DataFrame({
        "beruf": [
            "Buchhalter/in", "Softwareentwickler/in", "Krankenpfleger/in",
            "Verkäufer/in", "Sekretär/in", "LKW-Fahrer/in", "Lehrer/in (Sek)",
            "Rechtsanwalt/-anwältin", "Arzt/Ärztin", "Bankkaufmann/-frau",
        ],
        "isco_code": ["2411", "2512", "3221", "5223", "4120", "8322", "2330", "2611", "2211", "3311"],
        "beschaeftigte_1000": [85, 120, 95, 140, 60, 45, 110, 30, 50, 40],
        "frauen_anteil_pct": [58, 22, 78, 65, 82, 3, 65, 35, 45, 55],
        "branche": [
            "Finanzen", "ICT", "Gesundheit", "Detailhandel", "Verwaltung",
            "Transport", "Bildung", "Recht", "Gesundheit", "Finanzen"
        ],
    })
    save_processed(placeholder, "berufe_ch_placeholder.csv")
    print(placeholder.to_string())
