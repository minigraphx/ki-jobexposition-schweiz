"""Unit Tests für src/scoring/adaptability_scorer.py"""

import pandas as pd
import pytest

from adaptability_scorer import (
    LOHN_PUNKTE_MAX_CHF,
    LOHN_PUNKTE_MIN_CHF,
    _lohn_punkte,
    berechne_adaptabilitaet,
)


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


class TestLohnPunkte:
    """Feste Lohnskala: 0 bis 50'000 CHF, linear bis 3 bei 150'000 CHF, darüber 3."""

    @pytest.mark.parametrize("lohn, erwartet", [
        (40_000, 0.0),
        (50_000, 0.0),
        (75_000, 0.75),
        (100_000, 1.5),
        (150_000, 3.0),
        (200_000, 3.0),
    ])
    def test_raender_und_mitte(self, lohn, erwartet):
        assert _lohn_punkte(lohn) == pytest.approx(erwartet)

    def test_konstanten(self):
        assert LOHN_PUNKTE_MIN_CHF == 50_000
        assert LOHN_PUNKTE_MAX_CHF == 150_000

    def test_unabhaengig_von_anderen_berufen(self):
        """Ein neuer Höchstlohn darf die Werte der übrigen Berufe nicht verschieben."""
        basis = pd.DataFrame({
            "qualifikation": ["Sekundär II", "Tertiär"],
            "lohn_median_chf": [70_000, 110_000],
            "score_digital": [5.0, 7.0],
            "branche": ["Industrie", "Finanzen"],
        })
        ausreisser = pd.DataFrame({
            "qualifikation": ["Tertiär"],
            "lohn_median_chf": [400_000],
            "score_digital": [6.0],
            "branche": ["Gesundheit"],
        })
        allein = berechne_adaptabilitaet(basis)
        zusammen = berechne_adaptabilitaet(pd.concat([basis, ausreisser], ignore_index=True))
        pd.testing.assert_series_equal(allein, zusammen.iloc[:2])
        # Ein einzelner Beruf ergibt denselben Wert wie innerhalb der Gruppe
        assert berechne_adaptabilitaet(basis.iloc[[0]]).iloc[0] == allein.iloc[0]

    def test_lohnanteil_im_score(self):
        df = pd.DataFrame({
            "qualifikation": ["Sekundär II"] * 2,
            "lohn_median_chf": [50_000, 150_000],
            "score_digital": [0.0, 0.0],
            "branche": ["ICT", "ICT"],
        })
        # 3 (Qualifikation) + 0 bzw. 3 (Lohn) + 0 (digital) + 1 (ICT)
        assert berechne_adaptabilitaet(df).tolist() == [4.0, 7.0]
