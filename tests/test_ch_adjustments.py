"""Unit Tests für src/scoring/ch_adjustments.py"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "scoring"))
from ch_adjustments import apply_ch_adjustments, classify_lohn, BRANCHENEFFEKTE, LOHNEFFEKTE


class TestClassifyLohn:
    def test_niedrig(self):
        assert classify_lohn(45000) == "< 60k CHF"

    def test_mittel(self):
        assert classify_lohn(80000) == "60k–100k CHF"

    def test_hoch(self):
        assert classify_lohn(120000) == "100k–150k CHF"

    def test_sehr_hoch(self):
        assert classify_lohn(200000) == "> 150k CHF"

    def test_grenzwert_60k(self):
        assert classify_lohn(60000) == "60k–100k CHF"

    def test_grenzwert_100k(self):
        assert classify_lohn(100000) == "100k–150k CHF"

    def test_grenzwert_150k(self):
        assert classify_lohn(150000) == "> 150k CHF"


class TestApplyCHAdjustments:
    def test_score_ch_berechnet(self, sample_jobs):
        result = apply_ch_adjustments(sample_jobs)
        assert "score_ch" in result.columns

    def test_score_unveraendert_original(self, sample_jobs):
        """Immutability: Original-DataFrame darf nicht verändert werden."""
        original_scores = sample_jobs["score_gesamt"].copy()
        apply_ch_adjustments(sample_jobs)
        pd.testing.assert_series_equal(sample_jobs["score_gesamt"], original_scores)

    def test_score_clipping_max(self, edge_case_jobs):
        """Score darf 10 nicht überschreiten."""
        result = apply_ch_adjustments(edge_case_jobs)
        assert (result["score_ch"] <= 10).all()

    def test_score_clipping_min(self, edge_case_jobs):
        """Score darf 0 nicht unterschreiten."""
        result = apply_ch_adjustments(edge_case_jobs)
        assert (result["score_ch"] >= 0).all()

    def test_finanzen_erhoehung(self):
        """Finanzbranche erhält positiven Delta."""
        df = pd.DataFrame({
            "branche": ["Finanzen"],
            "lohn_median_chf": [80000],
            "score_gesamt": [5.0],
        })
        result = apply_ch_adjustments(df)
        assert result["score_ch"].iloc[0] > 5.0

    def test_gesundheit_senkung(self):
        """Gesundheitsbranche erhält negativen Delta."""
        df = pd.DataFrame({
            "branche": ["Gesundheit"],
            "lohn_median_chf": [80000],
            "score_gesamt": [5.0],
        })
        result = apply_ch_adjustments(df)
        assert result["score_ch"].iloc[0] < 5.0

    def test_unbekannte_branche_kein_fehler(self):
        """Unbekannte Branche → delta_branche = 0.0, kein Absturz."""
        df = pd.DataFrame({
            "branche": ["Raumfahrt"],
            "lohn_median_chf": [80000],
            "score_gesamt": [5.0],
        })
        result = apply_ch_adjustments(df)
        assert result["delta_branche"].iloc[0] == 0.0

    def test_ohne_lohn_spalte(self):
        """Fehlende lohn_median_chf-Spalte → delta_lohn = 0.0."""
        df = pd.DataFrame({
            "branche": ["Finanzen"],
            "score_gesamt": [5.0],
        })
        result = apply_ch_adjustments(df)
        assert "delta_lohn" in result.columns
        assert result["delta_lohn"].iloc[0] == 0.0

    def test_delta_spalten_vorhanden(self, sample_jobs):
        result = apply_ch_adjustments(sample_jobs)
        assert "delta_branche" in result.columns
        assert "delta_lohn" in result.columns

    def test_alle_branchen_effekte_definiert(self):
        """Alle BRANCHENEFFEKTE-Werte sind numerisch."""
        for branche, delta in BRANCHENEFFEKTE.items():
            assert isinstance(delta, float), f"{branche}: {delta} ist kein float"

    def test_alle_lohn_effekte_definiert(self):
        """Alle LOHNEFFEKTE-Werte sind numerisch."""
        for klasse, delta in LOHNEFFEKTE.items():
            assert isinstance(delta, float), f"{klasse}: {delta} ist kein float"
