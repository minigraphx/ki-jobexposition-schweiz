"""
Gemeinsame Bausteine der App-Seiten: Datenpfade, Laden, Beschriftungen, Farben, Hilfsfunktionen.

Die App liest data/processed/scores.csv (Schema: src/data/column_mapping.SCORES_SCHEMA) sowie die
Bewertungsdateien unter data/processed/bewertungen/ (Tätigkeitslisten in der Berufssuche).
Sie importiert bewusst nichts aus src/scoring (dort wird jsonschema benötigt, das die App nicht hat).
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed"
SCORES_PATH = DATA_DIR / "scores.csv"
BEWERTUNGEN_DIR = DATA_DIR / "bewertungen"
BENCHMARK_PATH = DATA_DIR / "benchmarks_isco4.csv"
KMU_PATH = DATA_DIR / "kmu_anteil_branche.csv"
GGS_PATH = DATA_DIR / "grenzgaenger_anteil_branche.csv"

# Kritische Zone (Startseite, Matrix): hoch exponiert und schwer anpassbar. Die Schwelle der
# Anpassungsfähigkeit ist relativ (schwelle_anpassung): eine feste Zahl auf einer Skala, deren Lage
# von der Zusammensetzung der Kriterien abhängt, wäre willkürlicher.
SCHWELLE_EXPOSITION = 6.0
SCHWELLE_ANPASSUNG_FEST = 5.0     # nur für den Sensitivitätsvergleich auf der Methodik-Seite

# Beschriftungen der Kennzahlen (Spalten von scores.csv) in der App
LABELS: dict[str, str] = {
    "exposure": "KI-Exposition",
    "time_savings": "Zeitersparnis",
    "physical_automation": "Physische Automatisierung",
    "software_automation": "Software-Automatisierung",
    "replaceable_time": "Ersetzbare Arbeitszeit",
    "adaptability": "Anpassungsfähigkeit",
    "employed_k": "Erwerbstätige (Tsd.)",
    "women_pct": "Frauenanteil (%)",
    "legacy_score": "Score der früheren Methode",
}
HILFE: dict[str, str] = {
    "exposure": "Anteil der Arbeitszeit (× 10) in Tätigkeiten, die generative KI um mindestens die Hälfte "
                "beschleunigen kann (Stufe E1 oder E2), Mittel über alle Läufe beider Modelle.",
    "time_savings": "Geschätzte eingesparte Arbeitszeit (× 10): exponierte Zeitanteile × (1 − verbleibende "
                    "menschliche Restzeit).",
    "physical_automation": "Anteil der Arbeitszeit (× 10), den heute verfügbare nicht-generative Technik "
                           "physisch übernehmen kann (Robotik, Automaten, Selbstbedienung, autonome Technik).",
    "software_automation": "Anteil der Arbeitszeit (× 10), den klassische Software ohne generative KI "
                           "übernehmen kann (Regel-Workflows, Schnittstellen, Belegerkennung).",
}

MODELLE: dict[str, str] = {
    "claude-cli": "Claude Opus 5.5",
    "claude": "Claude Opus 5.5",
    "gemini": "Gemini 4 Argon",
}

# Farben (Referenzpalette der Datenvisualisierung): Sequenz in einem Blauton für Werte 0–10,
# kategoriale Slots in fester Reihenfolge, Neutralgrau für «nicht exponiert».
BLAU_SEQUENZ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
SKALA_0_10 = [[i / (len(BLAU_SEQUENZ) - 1), c] for i, c in enumerate(BLAU_SEQUENZ)]
DIVERGIEREND = [[0.0, "#2a78d6"], [0.5, "#e1e0d9"], [1.0, "#e34948"]]   # blau ↔ grau ↔ rot
SERIE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
GRAU = "#c3c2b7"
KRITISCH = "#d03b3b"
TEXT_GEDAEMPFT = "#52514e"

MODI = [("ersetzend", "share_replacing", SERIE[0]),
        ("delegierend", "share_delegating", SERIE[1]),
        ("unterstützend", "share_assisting", SERIE[2])]


@st.cache_data
def lade_scores() -> pd.DataFrame | None:
    """scores.csv mit Typen; None, wenn die Datei fehlt."""
    if not SCORES_PATH.exists():
        return None
    df = pd.read_csv(SCORES_PATH, dtype={"isco_code": str, "esco_isco_code": str})
    df["uncertain"] = df["uncertain"].astype(str).str.lower().eq("true")
    return df


@st.cache_data
def lade_csv(pfad: str) -> pd.DataFrame | None:
    p = Path(pfad)
    return pd.read_csv(p, dtype={"isco_code": str}) if p.exists() else None


def text(wert) -> str:
    """Zelle → bereinigter Text («» für leer/NaN)."""
    if wert is None or (isinstance(wert, float) and pd.isna(wert)):
        return ""
    t = str(wert).strip()
    return "" if t.lower() == "nan" else t


def tsd(wert: float) -> str:
    """Zahl mit Schweizer Tausendertrennzeichen (Apostroph)."""
    return f"{wert:,.0f}".replace(",", "'")


def prozent(wert: float, stellen: int = 0) -> str:
    return "–" if wert is None or pd.isna(wert) else f"{wert:.{stellen}f} %".replace(".", ",")


def gewichtet(df: pd.DataFrame, spalte: str, gewicht: str = "employed_k") -> float:
    """Beschäftigungsgewichtetes Mittel (NaN-Werte ausgelassen)."""
    d = df[[spalte, gewicht]].dropna()
    return float((d[spalte] * d[gewicht]).sum() / d[gewicht].sum()) if d[gewicht].sum() > 0 else float("nan")


def spearman(a: pd.Series, b: pd.Series) -> tuple[float, int]:
    """Spearman-Rangkorrelation (Pearson auf Rängen, ohne scipy) und Anzahl Paare."""
    d = pd.DataFrame({"a": a, "b": b}).dropna()
    if len(d) < 3:
        return float("nan"), len(d)
    return float(d["a"].rank().corr(d["b"].rank())), len(d)


def schwelle_anpassung(df: pd.DataFrame) -> float:
    """Beschäftigungsgewichteter Median der Anpassungsfähigkeit: die Hälfte der Erwerbstätigen
    arbeitet in Berufen mit tieferem Wert."""
    d = df[["adaptability", "employed_k"]].dropna().sort_values("adaptability", kind="mergesort")
    if d.empty or d["employed_k"].sum() <= 0:
        return float("nan")
    kumuliert = d["employed_k"].cumsum() / d["employed_k"].sum()
    return float(d.loc[kumuliert >= 0.5, "adaptability"].iloc[0])


def kritische_zone(df: pd.DataFrame, schwelle: float | None = None, spalte: str = "exposure") -> pd.DataFrame:
    """Stark exponiert (> SCHWELLE_EXPOSITION) und nicht überdurchschnittlich anpassungsfähig
    (höchstens der beschäftigungsgewichtete Median aller Berufe, sofern keine Schwelle angegeben).

    «Höchstens» statt «unter»: Die Werte sind auf 0.1 gerundet; auf dem Median liegen oft mehrere
    Berufe, und ein grosser Beruf bestimmt den Median selbst. Mit «unter» hinge die Zugehörigkeit
    dieser Gruppe allein an der Rundung."""
    s = schwelle_anpassung(df) if schwelle is None else schwelle
    return df[(df[spalte] > SCHWELLE_EXPOSITION) & (df["adaptability"] <= s + 1e-9)]


# --------------------------------------------------------------------------- Bewertungsdateien

def slug(text_: str) -> str:
    """Dateinamen-Slug wie task_rubrik.slugify (Umlaute ausschreiben, Klammern entfernen, max. 40 Zeichen)."""
    t = (text_.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("Ä", "Ae")
         .replace("Ö", "Oe").replace("Ü", "Ue").replace("ß", "ss"))
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    t = re.sub(r"\(.*?\)", "", t)
    t = re.sub(r"[^a-zA-Z0-9]+", "_", t).strip("_").lower()
    return t[:40].rstrip("_")


def bewertungsdatei(text_source: str, isco_code: str, occupation: str) -> Path | None:
    """Pfad der Bewertung, aus der die Texte stammen (text_source «<provider>/run<N>»)."""
    quelle = text(text_source)
    if not re.fullmatch(r"[a-z-]+/run\d+", quelle):
        return None
    return BEWERTUNGEN_DIR / quelle / f"{isco_code}_{slug(occupation)}.json"


@st.cache_data
def lade_bewertung(pfad: str) -> dict | None:
    p = Path(pfad)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("bewertung")
    except (OSError, json.JSONDecodeError):
        return None


def _ueber(wert, schwelle: float = 1.0) -> bool:
    """wert > schwelle, ohne Gleitkomma-Rauschen (wie task_rubrik.ueber_schwelle)."""
    try:
        return round(float(wert), 9) > schwelle
    except (TypeError, ValueError):
        return False


CLAUDE_NAME, GEMINI_NAME = "Claude Opus 5.5", "Gemini 4 Argon"


def modellwerte(z) -> str:
    """«Claude Opus 5.5 gibt 6.7 Punkte, Gemini 4 Argon 8.2 Punkte» — Modellversion und Wert nie direkt
    hintereinander (sonst liest man «Opus 5.5 6.7»)."""
    return (f"{CLAUDE_NAME} gibt {z['exposure_claude']:.1f} Punkte, "
            f"{GEMINI_NAME} {z['exposure_gemini']:.1f} Punkte")


def unsicher_gruende(z) -> list[str]:
    """Kurze Gründe der Unsicherheits-Markierung (aus den Zahlen, nicht aus dem technischen uncertain_reason)."""
    gruende = []
    if _ueber(z.get("delta_provider")):
        gruende.append(modellwerte(z))
    if _ueber(z.get("spread_runs")):
        gruende.append(f"Wiederholungen streuen um {z['spread_runs']:.1f} Punkte")
    try:
        n = int(z.get("n_runs_claude") or 0) + int(z.get("n_runs_gemini") or 0)
    except (TypeError, ValueError):
        n = 0
    if n < 2:
        gruende.append("nur eine gültige Bewertung")
    return gruende


def quelle_lesbar(text_source: str) -> str:
    """«claude-cli/run2» → «Claude Opus 5.5, Lauf 2»."""
    q = text(text_source)
    if "/run" not in q:
        return q or "–"
    provider, lauf = q.split("/run", 1)
    return f"{MODELLE.get(provider, provider)}, Lauf {lauf}"
