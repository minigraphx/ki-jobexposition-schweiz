"""
CH-spezifische Adjustierungen der KI-Expositions-Scores.

Die Rohscores aus dem LLM-Scoring werden mit Schweizer Faktoren gewichtet,
die den Strukturwandel beschleunigen oder verlangsamen.
"""

import pandas as pd


# Branchenspezifische Adjustierungen (Deltaswert zum Rohscore)
BRANCHENEFFEKTE = {
    "Finanzen": +0.3,        # Bankplatz CH: hoher Automatisierungsdruck
    "Versicherungen": +0.4,  # Sehr hoher Automatisierungsdruck
    "ICT": -0.2,             # Adaptiv, aber selbst treibend
    "Gesundheit": -0.3,      # Regulierung + Pflegemangel als Bremse
    "Bildung": -0.2,         # Langsame Adoption
    "Verwaltung": +0.1,      # CH-Verwaltung digitalisiert langsam
    "Industrie": -0.1,       # MEM/Pharma: Fachkräftemangel als Puffer
    "Detailhandel": +0.2,    # E-Commerce-Druck
    "Transport": 0.0,        # Physisch, aber autonomes Fahren mittelfristig
    "Recht": +0.2,           # LegalTech wächst
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


def apply_ch_adjustments(df: pd.DataFrame) -> pd.DataFrame:
    """
    CH-Faktoren auf Rohscores anwenden.

    Erwartet Spalten: score_gesamt, branche, jahresbruttolohn (optional)
    Gibt DataFrame mit score_ch (adjustierter Score) zurück.
    """
    df = df.copy()

    # Brancheneffekt
    df["delta_branche"] = df["branche"].map(BRANCHENEFFEKTE).fillna(0.0)

    # Lohneffekt (falls vorhanden)
    if "jahresbruttolohn" in df.columns:
        df["lohnklasse"] = df["jahresbruttolohn"].apply(classify_lohn)
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
