"""Shared pytest fixtures."""

import pandas as pd
import pytest


@pytest.fixture
def sample_jobs() -> pd.DataFrame:
    """Minimaler DataFrame mit typischen CH-Berufen für Tests."""
    return pd.DataFrame({
        "beruf": ["Buchhalter/in", "Krankenpfleger/in", "Kassierer/in", "Softwareentwickler/in"],
        "isco_code": ["2411", "2221", "5223", "2512"],
        "beschaeftigte_1000": [32.0, 130.0, 25.0, 95.0],
        "frauen_pct": [57.0, 84.0, 75.0, 16.0],
        "branche": ["Finanzen", "Gesundheit", "Detailhandel", "ICT"],
        "lohn_median_chf": [98000, 82000, 48000, 130000],
        "qualifikation": ["Tertiär", "Tertiär", "Sekundär II", "Tertiär"],
        "score_gesamt": [8.5, 3.2, 8.5, 5.5],
        "adaptabilitaet": [4.5, 6.5, 2.5, 9.2],
    })


@pytest.fixture
def edge_case_jobs() -> pd.DataFrame:
    """Edge-Cases: fehlende Werte, Randwerte der Score-Skala."""
    return pd.DataFrame({
        "beruf": ["Beruf A", "Beruf B", "Beruf C"],
        "branche": ["Finanzen", "Gesundheit", "Unbekannt"],
        "lohn_median_chf": [200000, 30000, 75000],
        "qualifikation": ["Tertiär", "Keine Ausbildung", "Sekundär II"],
        "score_gesamt": [9.8, 0.2, 5.0],
    })
