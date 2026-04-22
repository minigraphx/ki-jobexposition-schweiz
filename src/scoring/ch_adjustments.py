"""
CH-spezifische Adjustierungen der KI-Expositions-Scores.

Die Rohscores aus dem LLM-Scoring werden mit Schweizer Faktoren gewichtet,
die den Strukturwandel beschleunigen oder verlangsamen.

Zusätzlich wird der LLM-generierte `zeitrahmen` um ±1 Stufe verschoben,
abhängig vom Grossfirmen-Anteil in der jeweiligen Branche (KMU-Adoptions-Faktor).
Datenquelle: BFS Betriebszählung 2008, `data/processed/kmu_anteil_branche.csv`.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


# Branchenspezifische Adjustierungen (Deltawert zum Rohscore)
# Abdeckung: alle 21 Branchen aus scores.csv
BRANCHENEFFEKTE: dict[str, float] = {
    # Erhöhter Automatisierungsdruck
    "Versicherungen": +0.4,   # Sehr standardisierte Prozesse, hoher Digitalisierungsgrad
    "Finanzen": +0.3,         # Bankplatz CH: hoher Automatisierungsdruck
    "Beratung": +0.2,         # Wissensarbeit: KI augmentiert Analyse & Strategie
    "Detailhandel": +0.2,     # E-Commerce-Druck, Self-Checkout, Logistikautomation
    "Recht": +0.2,            # LegalTech wächst; Dokumentenanalyse automatisierbar
    "Immobilien": +0.1,       # PropTech, Bewertungs-KI, digitale Plattformen
    "Medien": +0.1,           # KI-generierte Inhalte, aber Kreativität dämpft
    "Verwaltung": +0.1,       # Private Administration: strukturierte Büroprozesse

    # Neutral (Sektor zu heterogen oder Effekte gleichen sich aus)
    "Dienstleistungen": 0.0,  # Zu heterogen für einheitlichen Effekt
    "Transport": 0.0,         # Physisch, aber autonomes Fahren mittelfristig
    "Umwelt": 0.0,            # Spezialisiert; Monitoring-KI vs. Feldarbeit neutral

    # Gebremste Automatisierung
    "Gastgewerbe": -0.1,      # Serviceorientiert, Kundenkontakt; Buchungs-KI marginal
    "Industrie": -0.1,        # MEM/Pharma: Fachkräftemangel als Puffer
    "Landwirtschaft": -0.1,   # Precision Farming wächst, aber physische Arbeit dominiert
    "Öff. Verwaltung": -0.1,  # Öffentl. Sektor: langsame Adoption, polit. Rahmenbedingungen
    "Sicherheit": -0.1,       # Physische Präsenz erforderlich; Überwachungs-KI ergänzt nur
    "Bau": -0.2,              # Stark physisch, handwerklich; Digitalisierung langsam
    "Bildung": -0.2,          # Gesellschaftlicher Konsens über menschliche Lehrvermittlung
    "ICT": -0.2,              # KI-Fachkräfte adaptiv; treiben Wandel selbst
    "Gesundheit": -0.3,       # Regulierung, Fachkräftemangel, Pflegekomponente als Bremse
    "Soziales": -0.3,         # Hoher Empathiebedarf, Schutzinteressen; ähnlich Gesundheit
}

# Lohnklassen-Effekt: Höhere Löhne = stärkerer Automatisierungsdruck
LOHNEFFEKTE = {
    "< 60k CHF": -0.2,
    "60k–100k CHF": 0.0,
    "100k–150k CHF": +0.2,
    "> 150k CHF": +0.4,
}


def classify_lohn(jahresbruttolohn: float) -> str:
    if jahresbruttolohn < 60_000:
        return "< 60k CHF"
    elif jahresbruttolohn < 100_000:
        return "60k–100k CHF"
    elif jahresbruttolohn < 150_000:
        return "100k–150k CHF"
    else:
        return "> 150k CHF"


_PROCESSED_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "processed"

# Zeitrahmen-Leiter (aufsteigend = weiter in der Zukunft)
ZEITRAHMEN_STUFEN: list[str] = ["1-2 Jahre", "3-5 Jahre", "5-10 Jahre", ">10 Jahre"]

# Schwellenwerte für Grossfirmen-Anteil (BZ 2008, ≥250 VZÄ)
# Kalibriert auf tatsächliche Datenlage (max. ~49 % in CH-Branchen)
GROSSFIRMEN_SCHWELLE_HOCH = 0.40   # ≥40 % → −1 Stufe (frühere Adoption)
GROSSFIRMEN_SCHWELLE_TIEF = 0.10   # <10 % → +1 Stufe (spätere Adoption)


def _shift_zeitrahmen(wert: str, delta: int) -> str:
    """Verschiebt einen Zeitrahmen-String um delta Stufen (−1 = früher, +1 = später)."""
    if wert not in ZEITRAHMEN_STUFEN:
        return wert  # Unbekannter Wert bleibt unverändert
    idx = ZEITRAHMEN_STUFEN.index(wert)
    new_idx = max(0, min(len(ZEITRAHMEN_STUFEN) - 1, idx + delta))
    return ZEITRAHMEN_STUFEN[new_idx]


def adjust_zeitrahmen_fuer_kmu(
    df: pd.DataFrame,
    kmu_path: Path | None = None,
) -> pd.DataFrame:
    """
    Verschiebt `zeitrahmen` um ±1 Stufe basierend auf dem Grossfirmen-Anteil pro Branche.

    Logik (basierend auf BFS BZ 2008, Betriebe ≥250 VZÄ):
      ≥40 % Grossfirmen → −1 Stufe (grosse Firmen adoptieren KI früher)
      10–40 %           →  0 Stufen (neutral)
      <10 %             → +1 Stufe  (KMU-dominierte Branchen adoptieren später)

    Erwartet Spalten: zeitrahmen, branche
    Gibt DataFrame zurück mit:
      - zeitrahmen_roh: originaler LLM-Wert
      - zeitrahmen: adjustierter Wert
      - zeitrahmen_kmu_delta: angewendete Verschiebung (−1 / 0 / +1)
      - grossfirmen_anteil: Anteil Beschäftigte in Betrieben ≥250 VZÄ (BZ 2008)
    """
    if "zeitrahmen" not in df.columns:
        return df

    resolved_path = kmu_path or (_PROCESSED_DATA_PATH / "kmu_anteil_branche.csv")
    if not resolved_path.exists():
        return df  # Datei fehlt → keine Anpassung, keine Ausnahme

    kmu_df = pd.read_csv(resolved_path)[["branche", "grossfirmen_anteil"]]
    kmu_map: dict[str, float] = dict(zip(kmu_df["branche"], kmu_df["grossfirmen_anteil"]))

    df = df.copy()
    df["zeitrahmen_roh"] = df["zeitrahmen"]
    df["grossfirmen_anteil"] = df["branche"].map(kmu_map)

    def _delta(anteil: float | None) -> int:
        if anteil is None or pd.isna(anteil):
            return 0
        if anteil >= GROSSFIRMEN_SCHWELLE_HOCH:
            return -1
        if anteil < GROSSFIRMEN_SCHWELLE_TIEF:
            return +1
        return 0

    df["zeitrahmen_kmu_delta"] = df["grossfirmen_anteil"].apply(_delta)
    df["zeitrahmen"] = [
        _shift_zeitrahmen(z, d)
        for z, d in zip(df["zeitrahmen_roh"], df["zeitrahmen_kmu_delta"])
    ]

    return df


def apply_ch_adjustments(df: pd.DataFrame) -> pd.DataFrame:
    """
    CH-Faktoren auf Rohscores anwenden.

    Erwartet Spalten: score_gesamt, branche
    Optional: lohn_median_chf oder jahresbruttolohn (beide Spaltennamen akzeptiert)
    Gibt DataFrame mit score_ch (adjustierter Score) zurück.
    """
    df = df.copy()

    # Brancheneffekt
    df["delta_branche"] = df["branche"].map(BRANCHENEFFEKTE).fillna(0.0)

    # Lohneffekt — beide Spaltennamen akzeptieren (scores.csv: lohn_median_chf)
    lohn_col = next(
        (c for c in ["lohn_median_chf", "jahresbruttolohn"] if c in df.columns), None
    )
    if lohn_col:
        df["lohnklasse"] = df[lohn_col].apply(classify_lohn)
        df["delta_lohn"] = df["lohnklasse"].map(LOHNEFFEKTE).fillna(0.0)
    else:
        df["delta_lohn"] = 0.0

    # Adjustierten Score berechnen, Bereich 0–10 einhalten
    df["score_ch"] = (df["score_gesamt"] + df["delta_branche"] + df["delta_lohn"]).clip(0, 10)

    return df


if __name__ == "__main__":  # pragma: no cover
    test = pd.DataFrame({
        "beruf": ["Buchhalter/in", "Krankenpfleger/in", "Softwareentwickler/in"],
        "branche": ["Finanzen", "Gesundheit", "ICT"],
        "score_gesamt": [7.5, 3.2, 5.0],
        "jahresbruttolohn": [95_000, 75_000, 130_000],
    })
    result = apply_ch_adjustments(test)
    print(result[["beruf", "score_gesamt", "delta_branche", "delta_lohn", "score_ch"]].to_string())
