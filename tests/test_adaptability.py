"""Unit Tests für src/scoring/adaptability_scorer.py"""

import pandas as pd
import pytest

from adaptability_scorer import (
    LOHN_PUNKTE_MAX_CHF,
    LOHN_PUNKTE_MIN_CHF,
    _lohn_punkte,
    berechne_adaptabilitaet,
    setze_adaptabilitaet,
)


class TestBerechneAdaptabilitaet:
    def test_tertiär_hat_hohen_score(self):
        df = pd.DataFrame({
            "qualification": ["Tertiär"],
            "wage_median_chf": [120000],
            "exposure": [8.0],
            "sector": ["ICT"],
        })
        result = df.copy()
        result["adaptability"] = berechne_adaptabilitaet(df)
        assert result["adaptability"].iloc[0] >= 7.0

    def test_keine_ausbildung_hat_tiefen_score(self):
        df = pd.DataFrame({
            "qualification": ["Keine Ausbildung"],
            "wage_median_chf": [40000],
            "exposure": [1.0],
            "sector": ["Gastgewerbe"],
        })
        result = df.copy()
        result["adaptability"] = berechne_adaptabilitaet(df)
        assert result["adaptability"].iloc[0] <= 4.0

    def test_score_range_0_bis_10(self, sample_jobs):
        df = sample_jobs.copy()
        if "exposure" not in df.columns:
            df["exposure"] = 5.0
        scores = berechne_adaptabilitaet(df)
        assert (scores >= 0).all()
        assert (scores <= 10).all()

    def test_immutability(self, sample_jobs):
        """Original-DataFrame nicht verändern."""
        df = sample_jobs.copy()
        if "exposure" not in df.columns:
            df["exposure"] = 5.0
        original_vals = df["qualification"].copy()
        berechne_adaptabilitaet(df)
        pd.testing.assert_series_equal(df["qualification"], original_vals)

    def test_gibt_series_zurueck(self, sample_jobs):
        df = sample_jobs.copy()
        if "exposure" not in df.columns:
            df["exposure"] = 5.0
        result = berechne_adaptabilitaet(df)
        assert isinstance(result, pd.Series)

    def test_leerer_dataframe_kein_absturz(self):
        df = pd.DataFrame(columns=["qualification", "wage_median_chf", "exposure", "sector"])
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
            "qualification": ["Sekundär II", "Tertiär"],
            "wage_median_chf": [70_000, 110_000],
            "exposure": [5.0, 7.0],
            "sector": ["Industrie", "Finanzen"],
        })
        ausreisser = pd.DataFrame({
            "qualification": ["Tertiär"],
            "wage_median_chf": [400_000],
            "exposure": [6.0],
            "sector": ["Gesundheit"],
        })
        allein = berechne_adaptabilitaet(basis)
        zusammen = berechne_adaptabilitaet(pd.concat([basis, ausreisser], ignore_index=True))
        pd.testing.assert_series_equal(allein, zusammen.iloc[:2])
        # Ein einzelner Beruf ergibt denselben Wert wie innerhalb der Gruppe
        assert berechne_adaptabilitaet(basis.iloc[[0]]).iloc[0] == allein.iloc[0]

    def test_lohnanteil_im_score(self):
        df = pd.DataFrame({
            "qualification": ["Sekundär II"] * 2,
            "wage_median_chf": [50_000, 150_000],
            "exposure": [0.0, 0.0],
            "sector": ["ICT", "ICT"],
        })
        # 3 (Qualifikation) + 0 bzw. 3 (Lohn) + 0 (Digital-Proxy exposure) + 1 (ICT)
        assert berechne_adaptabilitaet(df).tolist() == [4.0, 7.0]


class TestDigitalProxy:
    """Digitale Affinität (2 Punkte) = 2 × exposure / 10 (seit der aufgabenbasierten Bewertung)."""

    def test_exposure_anteil(self):
        df = pd.DataFrame({"qualification": ["Sekundär II"] * 2, "wage_median_chf": [50_000] * 2,
                           "exposure": [0.0, 10.0], "sector": ["ICT", "ICT"]})
        assert berechne_adaptabilitaet(df).tolist() == [4.0, 6.0]

    def test_setze_text_erhaelt_gleiche_werte(self):
        text = pd.DataFrame({"qualification": ["Tertiär", "Sekundär II", "Tertiär"],
                             "wage_median_chf": ["100000", "50000", "100000"],
                             "exposure": ["5.0", "", "5.0"], "sector": ["ICT", "Bau", "ICT"],
                             "adaptability": ["7.50", "3.3", "1.0"]})
        out = setze_adaptabilitaet(text)
        # 4 + 1.5 + 1.0 + 1.0 = 7.5 → Text «7.50» bleibt; ohne exposure → leer; sonst neu
        assert out["adaptability"].tolist() == ["7.50", "", "7.5"]
        assert text["adaptability"].tolist() == ["7.50", "3.3", "1.0"]   # Original unverändert
