"""
Anpassungsfähigkeits-Score (Brookings-Methode, adaptiert für CH)

Kriterien:
- Qualifikationsniveau  (4 Punkte): höhere Bildung → leichtere Umschulung
- Lohnniveau            (3 Punkte): höherer Lohn → mehr Ressourcen
                                    (feste Skala: 0 bis 50'000 CHF, linear bis 3 bei 150'000 CHF)
- Branchenmobilität     (1 Punkt):  ICT/Finanzen mobilerer als Handwerk
Summe (max. 8) wird auf 0–10 skaliert (× 10/8).

Bis Oktober 2026 gab es zusätzlich «digitale Kompetenz» (2 Punkte) mit dem Teilkriterium
score_digital der früheren Bewertung als Proxy. Es existiert mit der aufgabenbasierten Bewertung
nicht mehr; ein Ersatz durch die KI-Exposition wäre zirkulär (dieselbe Grösse auf beiden Achsen
der Matrix), deshalb entfällt das Kriterium.

Ergebnis: adaptability (0–10), wird in scores.csv gespeichert (auch von apply_task_scores.py
und update_loehne.py neu berechnet).
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


# Feste Lohnskala (CHF/Jahr) statt Min-Max über alle Berufe: 50'000–150'000 CHF umschliesst
# die Spanne der LSE-2024-Mediane der Berufsgruppen (Jahreslohn rund 53'000 CHF
# in Gruppe 94 bis 130'000 CHF in Gruppe 11). Die Punkte eines Berufs hängen so
# nur von seinem eigenen Lohn ab und bleiben stabil, wenn ein Ausreisser-Lohn hinzukommt.
LOHN_PUNKTE_MIN_CHF = 50_000
LOHN_PUNKTE_MAX_CHF = 150_000
LOHN_PUNKTE_MAX = 3.0
MAX_PUNKTE = 4.0 + LOHN_PUNKTE_MAX + 1.0     # Qualifikation + Lohn + Mobilität → auf 10 skaliert


def _lohn_punkte(lohn: float) -> float:
    """Lohn → 0–3 Punkte: 0 bis 50'000 CHF, linear bis 3 bei 150'000 CHF, darüber 3."""
    anteil = (lohn - LOHN_PUNKTE_MIN_CHF) / (LOHN_PUNKTE_MAX_CHF - LOHN_PUNKTE_MIN_CHF)
    return LOHN_PUNKTE_MAX * min(max(anteil, 0.0), 1.0)


def berechne_adaptabilitaet(df: pd.DataFrame) -> pd.Series:
    """Spalten qualification, wage_median_chf, sector → adaptability (0–10, 0.1 gerundet)."""
    qual = df["qualification"].map(QUALIFIKATION_PUNKTE).fillna(1.0)
    lohn = df["wage_median_chf"].apply(_lohn_punkte)
    mobil = df["sector"].map(BRANCHEN_MOBILITAET).fillna(BRANCHEN_MOBILITAET_DEFAULT)

    raw = qual + lohn + mobil  # max = 4 + 3 + 1 = 8
    return (raw * 10 / MAX_PUNKTE).clip(0, 10).round(1)


def setze_adaptabilitaet(text_df: pd.DataFrame) -> pd.DataFrame:
    """adaptability in einer als Text gelesenen Tabelle neu setzen (Kopie).

    Zellen mit numerisch gleichem Wert behalten ihren Text (Formatierung bleibt erhalten, damit
    wiederholte Läufe byte-identisch sind); neue Werte als kürzeste Darstellung («6.4»).
    """
    num = pd.DataFrame({
        "qualification": text_df["qualification"],
        "wage_median_chf": pd.to_numeric(text_df["wage_median_chf"], errors="coerce"),
        "sector": text_df["sector"],
    }, index=text_df.index)
    neu = berechne_adaptabilitaet(num)
    out = text_df.copy()
    text = neu.map(lambda v: "" if pd.isna(v) else repr(round(float(v), 1)))
    if "adaptability" in out.columns:
        alt = pd.to_numeric(out["adaptability"], errors="coerce")
        text = text.where(~(alt.round(6) == neu.round(6)), out["adaptability"])
    out["adaptability"] = text
    return out


def main() -> None:  # pragma: no cover
    df = pd.read_csv(SCORES_PATH, dtype=str, keep_default_na=False)
    df = setze_adaptabilitaet(df)
    df.to_csv(SCORES_PATH, index=False)
    print(f"✓ adaptability berechnet für {len(df)} Berufe")
    top = df.assign(a=pd.to_numeric(df["adaptability"])).sort_values("a", ascending=False)
    print(top[["occupation", "adaptability", "exposure"]].head(10).to_string())


if __name__ == "__main__":  # pragma: no cover
    main()
