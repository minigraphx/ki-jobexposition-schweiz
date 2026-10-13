"""
Branchen-Zuordnung (BRANCHE_MAP aus update_from_bfs.py) auf die bestehenden CSVs anwenden —
ohne ESCO- oder LLM-Pipeline erneut laufen zu lassen.

Betroffen sind nur automatisch ergänzte BFS-SE-Berufe; die kuratierten Berufe aus
build_berufeliste.py behalten ihre manuell gesetzte Branche.

Aktualisiert wird die Spalte `branche` in:
    berufe_ch.csv, berufe_ch_esco.csv, berufe_ch_esco_verified.csv, scores.csv

In scores.csv werden zusätzlich — nur für die Zeilen mit geänderter Branche — die
regelbasierten, branchenabhängigen Spalten neu berechnet:
    delta_branche, score_ch                          (ch_adjustments.apply_ch_adjustments)
    zeitrahmen, zeitrahmen_kmu_delta, grossfirmen_anteil
                                                     (KMU-Faktor, ausgehend von zeitrahmen_roh)
    adaptabilitaet                                   (nur der Branchenmobilitäts-Anteil wird ersetzt)
score_gesamt, Sub-Scores und Begründungstexte bleiben unverändert. Alle übrigen Zellen
werden byte-identisch zurückgeschrieben.

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
from ch_adjustments import adjust_zeitrahmen_fuer_kmu, apply_ch_adjustments  # noqa: E402
from update_from_bfs import PROCESSED_PATH, branche_fuer_isco  # noqa: E402

BASIS_DATEIEN = ["berufe_ch.csv", "berufe_ch_esco.csv", "berufe_ch_esco_verified.csv"]
SCORES_DATEI = "scores.csv"
KURATIERTE_BERUFE: frozenset[str] = frozenset(b[0] for b in BERUFE_CH)


def _lesen(path: Path) -> pd.DataFrame:
    """CSV als Text lesen, damit unveränderte Zellen exakt erhalten bleiben."""
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def neue_branchen(df: pd.DataFrame) -> pd.Series:
    """Ziel-Branche je Zeile: kuratierte Berufe unverändert, übrige per ISCO-Präfix."""
    auto = ~df["beruf"].isin(KURATIERTE_BERUFE)
    neu = df["branche"].copy()
    neu[auto] = df.loc[auto, "isco_code"].map(branche_fuer_isco)
    return neu


def _mobilitaet(branche: str) -> float:
    return BRANCHEN_MOBILITAET.get(branche, BRANCHEN_MOBILITAET_DEFAULT)


def scores_neu_berechnen(text_df: pd.DataFrame, num_df: pd.DataFrame, geaendert: pd.Series) -> pd.DataFrame:
    """Regelbasierte Folgespalten für geänderte Zeilen neu berechnen.

    text_df: scores.csv als Text (mit bereits neuer Branche)
    num_df:  scores.csv mit numerischen Typen (gleiche Zeilenreihenfolge)
    """
    out = text_df.copy()
    if not geaendert.any():
        return out

    alt_branche = num_df.loc[geaendert, "branche"]
    num = num_df.copy()
    num["branche"] = text_df["branche"]
    res = adjust_zeitrahmen_fuer_kmu(apply_ch_adjustments(num))

    for spalte in ["delta_branche", "score_ch", "grossfirmen_anteil"]:
        if spalte in out.columns:
            # NaN (z. B. grossfirmen_anteil der Öff. Verwaltung) als leere Zelle schreiben
            out.loc[geaendert, spalte] = res.loc[geaendert, spalte].map(
                lambda v: "" if pd.isna(v) else repr(float(v)))
    for spalte in ["zeitrahmen", "zeitrahmen_roh"]:
        if spalte in out.columns:
            out.loc[geaendert, spalte] = res.loc[geaendert, spalte]
    if "zeitrahmen_kmu_delta" in out.columns:
        out.loc[geaendert, "zeitrahmen_kmu_delta"] = res.loc[geaendert, "zeitrahmen_kmu_delta"].astype(int).astype(str)

    if "adaptabilitaet" in out.columns:
        for idx in num_df.index[geaendert]:
            alt = num_df.at[idx, "adaptabilitaet"]
            if pd.isna(alt):
                continue
            neu = float(alt) - _mobilitaet(alt_branche[idx]) + _mobilitaet(text_df.at[idx, "branche"])
            out.at[idx, "adaptabilitaet"] = repr(round(min(max(neu, 0.0), 10.0), 1))
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dry-run", action="store_true", help="Änderungen nur anzeigen")
    parser.add_argument("--pfad", type=Path, default=PROCESSED_PATH, help="Verzeichnis der CSVs")
    args = parser.parse_args(argv)

    for name in BASIS_DATEIEN + [SCORES_DATEI]:
        path = args.pfad / name
        if not path.exists():
            print(f"– {name}: nicht vorhanden, übersprungen")
            continue
        df = _lesen(path)
        neu = neue_branchen(df)
        geaendert = neu != df["branche"]
        print(f"✓ {name}: {int(geaendert.sum())} Zeilen mit neuer Branche")
        for idx in df.index[geaendert]:
            print(f"    {df.at[idx, 'isco_code']} {df.at[idx, 'beruf'][:60]}: "
                  f"{df.at[idx, 'branche']} → {neu[idx]}")
        if args.dry_run or not geaendert.any():
            continue

        num_df = pd.read_csv(path) if name == SCORES_DATEI else None
        df["branche"] = neu
        if num_df is not None:
            df = scores_neu_berechnen(df, num_df, geaendert)
        df.to_csv(path, index=False)


if __name__ == "__main__":  # pragma: no cover
    main()
