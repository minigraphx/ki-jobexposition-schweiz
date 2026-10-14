"""Shared pytest fixtures."""

import pandas as pd
import pytest


@pytest.fixture
def sample_jobs() -> pd.DataFrame:
    """Minimaler DataFrame mit typischen CH-Berufen für Tests (Spaltennamen wie scores.csv)."""
    return pd.DataFrame({
        "occupation": ["Buchhalter/in", "Krankenpfleger/in", "Kassierer/in", "Softwareentwickler/in"],
        "isco_code": ["2411", "2221", "5223", "2512"],
        "employed_k": [32.0, 130.0, 25.0, 95.0],
        "women_pct": [57.0, 84.0, 75.0, 16.0],
        "sector": ["Finanzen", "Gesundheit", "Detailhandel", "ICT"],
        "wage_median_chf": [98000, 82000, 48000, 130000],
        "qualification": ["Tertiär", "Tertiär", "Sekundär II", "Tertiär"],
        "exposure": [8.5, 2.2, 0.1, 7.8],
        "adaptability": [4.5, 6.5, 2.5, 9.2],
    })
