"""
KMU-Adoptions-Faktor: Zeitrahmen je Branche um ±1 Stufe verschieben (gemeinsame Logik).

Grossunternehmen führen KI in der Regel früher ein als KMU. Der vom Scoring geschätzte
Zeitrahmen (`timeframe_raw`, Median der aufgabenbasierten Bewertungen) wird deshalb je
Branche nach dem Grossfirmen-Anteil verschoben. Der Faktor wirkt nur auf das «Wann», nicht
auf die Höhe der Exposition.

Datenquelle: BFS STATENT (ts-x-06.02.01.01, marktwirtschaftliche Unternehmen nach
Wirtschaftsabteilung und Grössenklasse), aufbereitet durch `src/data/fetch_statent.py` in
`data/processed/kmu_anteil_branche.csv` (Spalten sector, large_firm_share, …).

Verwendet von `src/scoring/apply_task_scores.py`, `src/data/fetch_statent.py --apply-scores`
und `src/data/branche_neu_zuordnen.py` (früher in ch_adjustments.py).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

KMU_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "kmu_anteil_branche.csv"

# Die 21 internen Branchen (Zellwerte der Spalte sector in allen CSVs)
BRANCHEN: frozenset[str] = frozenset({
    "Bau", "Beratung", "Bildung", "Detailhandel", "Dienstleistungen", "Finanzen", "Gastgewerbe",
    "Gesundheit", "ICT", "Immobilien", "Industrie", "Landwirtschaft", "Medien", "Recht", "Sicherheit",
    "Soziales", "Transport", "Umwelt", "Versicherungen", "Verwaltung", "Öff. Verwaltung",
})

# Zeitrahmen-Leiter (aufsteigend = weiter in der Zukunft); gleiche Werte wie task_rubrik.ZEITRAHMEN
ZEITRAHMEN_STUFEN: list[str] = ["1-2 Jahre", "3-5 Jahre", "5-10 Jahre", ">10 Jahre"]

# Schwellenwerte für den Grossfirmen-Anteil (STATENT, Anteil der Beschäftigten in
# Unternehmen mit ≥250 Beschäftigten; schweizweit 2024: 34 %).
# Oberes Segment: Mehrheit der Beschäftigten arbeitet in Grossunternehmen (≥50 %).
# Unteres Segment: mindestens 85 % der Beschäftigten in KMU (<15 %), d. h. weniger als
# rund die Hälfte des Landesmittels. Bis Oktober 2026 galten 0.40 / 0.10, kalibriert auf die
# Betriebszählung 2008 (Arbeitsstätten ≥250 VZÄ, max. ~49 %); der Unternehmensbegriff
# liefert deutlich höhere Anteile (Filialnetze zählen als ein Unternehmen), daher die
# Anpassung — siehe Methodik-Seite.
GROSSFIRMEN_SCHWELLE_HOCH = 0.50   # ≥50 % → −1 Stufe (frühere Adoption)
GROSSFIRMEN_SCHWELLE_TIEF = 0.15   # <15 % → +1 Stufe (spätere Adoption)


def pruefe_branchen(branchen) -> None:
    """Fail-fast: unbekannte Branchen (nicht leer) sind ein Datenfehler."""
    unbekannt = sorted({b for b in branchen if isinstance(b, str) and b} - BRANCHEN)
    if unbekannt:
        raise ValueError(f"Unbekannte Branchen: {unbekannt}. Ergänze BRANCHEN in kmu_faktor.py.")


def verschiebe_zeitrahmen(wert, delta: int):
    """Verschiebt einen Zeitrahmen um delta Stufen (−1 = früher, +1 = später), begrenzt auf die Leiter."""
    if wert not in ZEITRAHMEN_STUFEN:
        return wert  # unbekannter oder leerer Wert bleibt unverändert
    idx = ZEITRAHMEN_STUFEN.index(wert)
    return ZEITRAHMEN_STUFEN[max(0, min(len(ZEITRAHMEN_STUFEN) - 1, idx + delta))]


def kmu_verschiebung(anteil) -> int:
    """Grossfirmen-Anteil → Verschiebung: ≥50 % −1, 15–50 % 0, <15 % +1, kein Wert 0."""
    if anteil is None or pd.isna(anteil):
        return 0
    if anteil >= GROSSFIRMEN_SCHWELLE_HOCH:
        return -1
    if anteil < GROSSFIRMEN_SCHWELLE_TIEF:
        return +1
    return 0


def lade_kmu(kmu_path: Path | None = None) -> pd.DataFrame | None:
    """kmu_anteil_branche.csv (sector, large_firm_share); fehlt die Datei → None."""
    path = kmu_path or KMU_PATH
    return pd.read_csv(path) if path.exists() else None


def adjust_zeitrahmen_fuer_kmu(df: pd.DataFrame, kmu_path: Path | None = None,
                               kmu_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """
    Setzt large_firm_share, timeframe_sme_shift und timeframe (= timeframe_raw verschoben).

    Logik (BFS STATENT, Beschäftigte in Unternehmen ≥250 Beschäftigte):
      ≥50 % Grossfirmen → −1 Stufe (grosse Firmen adoptieren KI früher)
      15–50 %           →  0 Stufen (neutral)
      <15 %             → +1 Stufe  (KMU-dominierte Branchen adoptieren später)
      kein Wert (NaN)   →  0 Stufen (z. B. Öff. Verwaltung: keine marktwirtschaftlichen
                                     Unternehmen in der STATENT-Tabelle)

    Erwartet Spalten sector und timeframe_raw (Rohwert des Scorings). Fehlt timeframe_raw oder
    ist er leer, gilt timeframe als Rohwert und wird als timeframe_raw gespeichert — so bleibt
    die Funktion idempotent (es wird immer vom Rohwert aus verschoben).

    Args:
        kmu_path: Pfad zu kmu_anteil_branche.csv (Standard: data/processed/).
        kmu_df: alternativ die Tabelle direkt (Spalten sector, large_firm_share); hat Vorrang.
    Returns:
        Kopie von df; unverändert, wenn es weder timeframe_raw noch timeframe gibt oder die
        KMU-Tabelle fehlt.
    """
    if "timeframe_raw" not in df.columns and "timeframe" not in df.columns:
        return df
    if kmu_df is None:
        kmu_df = lade_kmu(kmu_path)
        if kmu_df is None:
            return df  # Datei fehlt → keine Anpassung, keine Ausnahme
    anteile = dict(zip(kmu_df["sector"], kmu_df["large_firm_share"]))

    df = df.copy()
    roh = df["timeframe_raw"] if "timeframe_raw" in df.columns else pd.Series(pd.NA, index=df.index)
    roh = roh.replace("", pd.NA)
    if "timeframe" in df.columns:
        roh = roh.where(roh.notna(), df["timeframe"])
    df["timeframe_raw"] = roh
    df["large_firm_share"] = df["sector"].map(anteile)
    df["timeframe_sme_shift"] = df["large_firm_share"].apply(kmu_verschiebung)
    df["timeframe"] = [verschiebe_zeitrahmen(z, d) for z, d in zip(df["timeframe_raw"], df["timeframe_sme_shift"])]
    return df
