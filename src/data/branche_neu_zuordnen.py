"""
Branchen-Zuordnung (BRANCHE_MAP aus update_from_bfs.py) auf die bestehenden CSVs anwenden —
ohne ESCO- oder Bewertungs-Pipeline erneut laufen zu lassen.

Betroffen sind nur automatisch ergänzte BFS-SE-Berufe; die kuratierten Berufe aus
build_berufeliste.py behalten ihre manuell gesetzte Branche.

Aktualisiert wird die Spalte `sector` in:
    berufe_ch.csv, berufe_ch_esco.csv, berufe_ch_esco_verified.csv, scores.csv

In scores.csv werden zusätzlich — nur für die Zeilen mit geänderter Branche — die
regelbasierten, branchenabhängigen Spalten neu berechnet:
    timeframe, timeframe_sme_shift, large_firm_share
                                     (KMU-Faktor, ausgehend von timeframe_raw; kmu_faktor.py)
    adaptability                     (nur der Branchenmobilitäts-Anteil wird ersetzt)
Die aufgabenbasierten Scores (exposure usw.) und Texte bleiben unverändert — die Branche
wirkt nur über den Zeitrahmen. Alle übrigen Zellen werden byte-identisch zurückgeschrieben.

Aufruf:
    python src/data/branche_neu_zuordnen.py            # anwenden
    python src/data/branche_neu_zuordnen.py --dry-run  # nur anzeigen
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "scoring"))

from adaptability_scorer import BRANCHEN_MOBILITAET, BRANCHEN_MOBILITAET_DEFAULT  # noqa: E402
from build_berufeliste import BERUFE_CH  # noqa: E402
from kmu_faktor import adjust_zeitrahmen_fuer_kmu  # noqa: E402
from update_from_bfs import PROCESSED_PATH, branche_fuer_isco  # noqa: E402

BASIS_DATEIEN = ["berufe_ch.csv", "berufe_ch_esco.csv", "berufe_ch_esco_verified.csv"]
SCORES_DATEI = "scores.csv"
KURATIERTE_BERUFE: frozenset[str] = frozenset(b[0] for b in BERUFE_CH)


def _lesen(path: Path) -> pd.DataFrame:
    """CSV als Text lesen, damit unveränderte Zellen exakt erhalten bleiben."""
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def neue_branchen(df: pd.DataFrame) -> pd.Series:
    """Ziel-Branche je Zeile: kuratierte Berufe unverändert, übrige per ISCO-Präfix."""
    auto = ~df["occupation"].isin(KURATIERTE_BERUFE)
    neu = df["sector"].copy()
    neu[auto] = df.loc[auto, "isco_code"].map(branche_fuer_isco)
    return neu


def _mobilitaet(branche: str) -> float:
    return BRANCHEN_MOBILITAET.get(branche, BRANCHEN_MOBILITAET_DEFAULT)


def scores_neu_berechnen(text_df: pd.DataFrame, alt_branche: pd.Series, geaendert: pd.Series) -> pd.DataFrame:
    """Regelbasierte Folgespalten für geänderte Zeilen neu berechnen.

    text_df:     scores.csv als Text (mit bereits neuer Branche)
    alt_branche: bisherige Branche je Zeile (gleicher Index)
    """
    out = text_df.copy()
    if not geaendert.any():
        return out

    spalten = [s for s in ("sector", "timeframe_raw", "timeframe") if s in text_df.columns]
    if len(spalten) > 1:
        res = adjust_zeitrahmen_fuer_kmu(text_df[spalten])
        if "large_firm_share" in res.columns:
            # NaN (z. B. large_firm_share der Öff. Verwaltung) als leere Zelle schreiben
            out.loc[geaendert, "large_firm_share"] = res.loc[geaendert, "large_firm_share"].map(
                lambda v: "" if pd.isna(v) else repr(float(v)))
            out.loc[geaendert, "timeframe_sme_shift"] = (
                res.loc[geaendert, "timeframe_sme_shift"].astype(int).astype(str))
            for spalte in ("timeframe", "timeframe_raw"):
                out.loc[geaendert, spalte] = res.loc[geaendert, spalte].fillna("")

    if "adaptability" in out.columns:
        for idx in text_df.index[geaendert]:
            alt = pd.to_numeric(text_df.at[idx, "adaptability"], errors="coerce")
            if pd.isna(alt):
                continue
            neu = float(alt) - _mobilitaet(alt_branche[idx]) + _mobilitaet(text_df.at[idx, "sector"])
            out.at[idx, "adaptability"] = repr(round(min(max(neu, 0.0), 10.0), 1))
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dry-run", action="store_true", help="Änderungen nur anzeigen")
    parser.add_argument("--data-dir", dest="pfad", metavar="DIR", type=Path, default=PROCESSED_PATH,
                        help="Verzeichnis der CSVs")
    args = parser.parse_args(argv)

    for name in BASIS_DATEIEN + [SCORES_DATEI]:
        path = args.pfad / name
        if not path.exists():
            print(f"– {name}: nicht vorhanden, übersprungen")
            continue
        df = _lesen(path)
        neu = neue_branchen(df)
        geaendert = neu != df["sector"]
        print(f"✓ {name}: {int(geaendert.sum())} Zeilen mit neuer Branche")
        for idx in df.index[geaendert]:
            print(f"    {df.at[idx, 'isco_code']} {df.at[idx, 'occupation'][:60]}: "
                  f"{df.at[idx, 'sector']} → {neu[idx]}")
        if args.dry_run or not geaendert.any():
            continue

        alt_branche = df["sector"].copy()
        df["sector"] = neu
        if name == SCORES_DATEI:
            df = scores_neu_berechnen(df, alt_branche, geaendert)
        df.to_csv(path, index=False)


if __name__ == "__main__":  # pragma: no cover
    main()
