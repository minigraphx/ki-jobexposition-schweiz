"""Unit Tests für src/scoring/adaptability_scorer.py"""

import pandas as pd
import pytest

from adaptability_scorer import berechne_adaptabilitaet


class TestBerechneAdaptabilitaet:
    def test_tertiär_hat_hohen_score(self):
        df = pd.DataFrame({
            "qualifikation": ["Tertiär"],
            "lohn_median_chf": [120000],
            "score_digital": [8.0],
            "branche": ["ICT"],
        })
        result = df.copy()
        result["adaptabilitaet"] = berechne_adaptabilitaet(df)
        assert result["adaptabilitaet"].iloc[0] >= 7.0

    def test_keine_ausbildung_hat_tiefen_score(self):
        df = pd.DataFrame({
            "qualifikation": ["Keine Ausbildung"],
            "lohn_median_chf": [40000],
            "score_digital": [1.0],
            "branche": ["Gastgewerbe"],
        })
        result = df.copy()
        result["adaptabilitaet"] = berechne_adaptabilitaet(df)
        assert result["adaptabilitaet"].iloc[0] <= 4.0

    def test_score_range_0_bis_10(self, sample_jobs):
        df = sample_jobs.copy()
        if "score_digital" not in df.columns:
            df["score_digital"] = 5.0
        scores = berechne_adaptabilitaet(df)
        assert (scores >= 0).all()
        assert (scores <= 10).all()

    def test_immutability(self, sample_jobs):
        """Original-DataFrame nicht verändern."""
        df = sample_jobs.copy()
        if "score_digital" not in df.columns:
            df["score_digital"] = 5.0
        original_vals = df["qualifikation"].copy()
        berechne_adaptabilitaet(df)
        pd.testing.assert_series_equal(df["qualifikation"], original_vals)

    def test_gibt_series_zurueck(self, sample_jobs):
        df = sample_jobs.copy()
        if "score_digital" not in df.columns:
            df["score_digital"] = 5.0
        result = berechne_adaptabilitaet(df)
        assert isinstance(result, pd.Series)

    def test_leerer_dataframe_kein_absturz(self):
        df = pd.DataFrame(columns=["qualifikation", "lohn_median_chf", "score_digital", "branche"])
        result = berechne_adaptabilitaet(df)
        assert len(result) == 0
