"""Tests für fetch_bgs.py"""

import pandas as pd
import pytest

from fetch_bgs import BRANCHE_FALLBACK_ANTEIL, compute_grenzgaenger_anteil


class TestMappingVollstaendigkeit:
    def test_alle_21_branchen_abgedeckt(self):
        """Alle 21 internen Branchen müssen einen Grenzgänger-Anteil haben."""
        expected = {
            "Bau", "Industrie", "Gastgewerbe", "Transport", "Gesundheit",
            "Detailhandel", "ICT", "Finanzen", "Versicherungen", "Recht",
            "Bildung", "Verwaltung", "Öff. Verwaltung", "Soziales",
            "Landwirtschaft", "Umwelt", "Sicherheit", "Dienstleistungen",
            "Immobilien", "Medien", "Beratung",
        }
        assert set(BRANCHE_FALLBACK_ANTEIL.keys()) == expected


class TestAnteilBerechnung:
    def test_anteil_zwischen_0_und_1(self):
        df = compute_grenzgaenger_anteil(use_fallback=True)
        assert (df["grenzgaenger_anteil"] >= 0).all()
        assert (df["grenzgaenger_anteil"] <= 1).all()

    def test_berechnung_korrekt(self):
        # grenzgaenger_anteil = grenzgaenger / beschaeftigte_total
        df = compute_grenzgaenger_anteil(use_fallback=True)
        # Only check rows where beschaeftigte_total > 0
        valid = df[df["beschaeftigte_total"] > 0].copy()
        calc = valid["grenzgaenger"] / valid["beschaeftigte_total"]
        pd.testing.assert_series_equal(
            valid["grenzgaenger_anteil"].round(6).reset_index(drop=True),
            calc.round(6).reset_index(drop=True),
            check_names=False,
        )

    def test_output_spalten(self):
        df = compute_grenzgaenger_anteil(use_fallback=True)
        assert set(df.columns) >= {"branche", "grenzgaenger", "beschaeftigte_total", "grenzgaenger_anteil"}

    def test_alle_branchen_im_output(self):
        """Alle 21 Branchen sind im Output enthalten."""
        df = compute_grenzgaenger_anteil(use_fallback=True)
        expected = set(BRANCHE_FALLBACK_ANTEIL.keys())
        assert set(df["branche"]) == expected

    def test_grenzgaenger_nicht_negativ(self):
        df = compute_grenzgaenger_anteil(use_fallback=True)
        assert (df["grenzgaenger"] >= 0).all()

    def test_beschaeftigte_total_nicht_negativ(self):
        df = compute_grenzgaenger_anteil(use_fallback=True)
        assert (df["beschaeftigte_total"] >= 0).all()
