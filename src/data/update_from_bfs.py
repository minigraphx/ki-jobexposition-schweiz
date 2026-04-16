"""
BFS CH-ISCO-19 Daten einlesen und berufe_ch.csv aktualisieren.

Schritte:
1. BFS Excel parsen (Sheet "2024", 4-stellige Berufsgattungen)
2. Beschäftigte + Frauen% der bestehenden 107 Einträge aktualisieren
3. Neue Berufe (>= 5000 Beschäftigte, noch nicht in scores.csv) hinzufügen
4. Branche / Lohn / Qualifikation per ISCO-Gruppe automatisch zuweisen
5. berufe_ch.csv speichern
"""

from pathlib import Path

import numpy as np
import pandas as pd

RAW_PATH = Path(__file__).parent.parent.parent / "data" / "raw"
PROCESSED_PATH = Path(__file__).parent.parent.parent / "data" / "processed"
BFS_FILE = RAW_PATH / "su-d-40.02.03.02.01.03.10.xlsx"

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

# ISCO-Untergruppe (2-stellig) → Branche
BRANCHE_MAP = {
    "11": "Verwaltung", "12": "Verwaltung", "13": "Gastgewerbe", "14": "Gastgewerbe",
    "21": "Industrie", "22": "Gesundheit", "23": "Bildung", "24": "Finanzen",
    "25": "ICT", "26": "Medien", "27": "Industrie", "28": "Industrie", "29": "Industrie",
    "31": "Industrie", "32": "Gesundheit", "33": "Finanzen", "34": "Soziales",
    "35": "ICT",
    "41": "Verwaltung", "42": "Verwaltung", "43": "Verwaltung", "44": "Verwaltung",
    "51": "Gastgewerbe", "52": "Detailhandel", "53": "Soziales", "54": "Öff. Verwaltung",
    "61": "Landwirtschaft", "62": "Landwirtschaft", "63": "Landwirtschaft",
    "71": "Bau", "72": "Industrie", "73": "Industrie", "74": "Industrie", "75": "Landwirtschaft",
    "81": "Industrie", "82": "Industrie", "83": "Transport",
    "91": "Dienstleistungen", "92": "Dienstleistungen", "93": "Industrie", "94": "Gastgewerbe",
    "95": "Dienstleistungen", "96": "Dienstleistungen",
    "01": "Öff. Verwaltung",
}

# ISCO-Untergruppe (2-stellig) → medianer Jahreslohn CHF (LSE 2022, geschätzt)
LOHN_MAP = {
    "11": 150000, "12": 120000, "13": 85000, "14": 75000,
    "21": 115000, "22": 90000, "23": 108000, "24": 115000,
    "25": 120000, "26": 88000, "27": 105000, "28": 105000, "29": 100000,
    "31": 88000, "32": 68000, "33": 82000, "34": 72000,
    "35": 85000,
    "41": 70000, "42": 68000, "43": 65000, "44": 62000,
    "51": 52000, "52": 56000, "53": 58000, "54": 88000,
    "61": 52000, "62": 50000, "63": 48000,
    "71": 74000, "72": 78000, "73": 76000, "74": 72000, "75": 54000,
    "81": 64000, "82": 60000, "83": 62000,
    "91": 46000, "92": 44000, "93": 54000, "94": 44000,
    "95": 48000, "96": 46000,
    "01": 85000,
}


def parse_bfs_excel(filepath: Path) -> pd.DataFrame:
    """BFS Excel einlesen, 4-stellige Berufsgattungen extrahieren."""
    df = pd.read_excel(filepath, sheet_name="2024", header=None)
    mask = df[3].notna() & df[4].isna()
    bfs = df[mask][[3, 5, 6, 7, 8]].copy()
    bfs.columns = ["isco_code", "beruf_bfs", "beschaeftigte_total", "maenner", "frauen"]
    bfs = bfs.replace("X", np.nan)
    bfs["beschaeftigte_total"] = pd.to_numeric(bfs["beschaeftigte_total"], errors="coerce")
    bfs["frauen"] = pd.to_numeric(bfs["frauen"], errors="coerce")
    bfs["frauen_pct"] = (bfs["frauen"] / bfs["beschaeftigte_total"] * 100).round(1)
    bfs["isco_code"] = bfs["isco_code"].astype(str)
    return bfs.dropna(subset=["beschaeftigte_total"])


def assign_metadata(isco_code: str) -> tuple[str, str, int]:
    """Branche, Qualifikation, Lohn aus ISCO-Code ableiten."""
    major = isco_code[0] if isco_code else "9"
    sub = isco_code[:2] if len(isco_code) >= 2 else major
    branche = BRANCHE_MAP.get(sub, "Dienstleistungen")
    qualifikation = QUALIFIKATION_MAP.get(major, "Sekundär II")
    lohn = LOHN_MAP.get(sub, 70000)
    return branche, qualifikation, lohn


def main() -> None:
    bfs = parse_bfs_excel(BFS_FILE)
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
    print(f"✓ {updated} bestehende Einträge mit BFS-Daten aktualisiert")

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
            "qualifikation": qualifikation,
        })

    new_df = pd.DataFrame(new_rows)
    combined = pd.concat([existing, new_df], ignore_index=True)
    combined = combined.sort_values("beschaeftigte_1000", ascending=False).reset_index(drop=True)

    combined.to_csv(PROCESSED_PATH / "berufe_ch.csv", index=False)
    print(f"✓ {len(new_df)} neue Berufe hinzugefügt")
    print(f"✓ berufe_ch.csv gespeichert: {len(combined)} Berufe total")


if __name__ == "__main__":
    main()
