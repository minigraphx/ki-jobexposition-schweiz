"""
Anpassungsfähigkeits-Score (Brookings-Methode, adaptiert für CH)

Kriterien:
- Qualifikationsniveau  (4 Punkte): höhere Bildung → leichtere Umschulung
- Lohnniveau            (3 Punkte): höherer Lohn → mehr Ressourcen
- Digitale Kompetenz    (2 Punkte): score_digital als Proxy
- Branchenmobilität     (1 Punkt):  ICT/Finanzen mobilerer als Handwerk

Ergebnis: adaptabilitaet (0–10), wird in scores.csv gespeichert.
"""

from pathlib import Path

import pandas as pd

SCORES_PATH = Path(__file__).parent.parent.parent / "data" / "processed" / "scores.csv"

QUALIFIKATION_PUNKTE = {
    "Tertiär": 4.0,
    # CH-EFZ grants higher labour-market mobility than US high school; Brookings parametrisation not directly transferable
    "Sekundär II": 3.0,
    "Keine Ausbildung": 1.0,
}

BRANCHEN_MOBILITAET = {
    "ICT": 1.0,
    "Finanzen": 0.9,
    "Bildung": 0.8,
    "Verwaltung": 0.7,
    "Industrie": 0.6,
    "Gesundheit": 0.5,
    "Dienstleistungen": 0.5,
    "Detailhandel": 0.4,
    "Bau": 0.3,
    "Gastgewerbe": 0.3,
}
BRANCHEN_MOBILITAET_DEFAULT = 0.5


def _lohn_punkte(lohn: float, lohn_min: float, lohn_max: float) -> float:
    """Normalisiert den Lohn auf 0–3 Punkte."""
    if lohn_max == lohn_min:
        return 1.5
    return 3.0 * (lohn - lohn_min) / (lohn_max - lohn_min)


def _digital_punkte(score_digital: float) -> float:
    """score_digital (0–10) → 0–2 Punkte (höhere Digitalaffinität = anpassungsfähiger)."""
    return 2.0 * score_digital / 10.0


def berechne_adaptabilitaet(df: pd.DataFrame) -> pd.Series:
    lohn_min = df["lohn_median_chf"].min()
    lohn_max = df["lohn_median_chf"].max()

    qual = df["qualifikation"].map(QUALIFIKATION_PUNKTE).fillna(1.0)
    lohn = df["lohn_median_chf"].apply(lambda x: _lohn_punkte(x, lohn_min, lohn_max))
    digital = df["score_digital"].apply(_digital_punkte)
    mobil = df["branche"].map(BRANCHEN_MOBILITAET).fillna(BRANCHEN_MOBILITAET_DEFAULT)

    raw = qual + lohn + digital + mobil  # max = 4 + 3 + 2 + 1 = 10
    return raw.clip(0, 10).round(1)


def main() -> None:  # pragma: no cover
    df = pd.read_csv(SCORES_PATH)

    df = df.assign(adaptabilitaet=berechne_adaptabilitaet(df))

    df.to_csv(SCORES_PATH, index=False)
    print(f"✓ adaptabilitaet berechnet für {len(df)} Berufe")
    print(df[["beruf", "adaptabilitaet", "score_ch"]].sort_values("adaptabilitaet", ascending=False).head(10).to_string())


if __name__ == "__main__":  # pragma: no cover
    main()
