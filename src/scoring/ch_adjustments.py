"""
CH-spezifische Adjustierungen der KI-Expositions-Scores.

Die Rohscores aus dem LLM-Scoring werden mit Schweizer Faktoren gewichtet,
die den Strukturwandel beschleunigen oder verlangsamen.
"""

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
