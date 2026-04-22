"""Unit Tests für src/scoring/ch_adjustments.py"""

import pandas as pd
import pytest

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

    def test_alle_21_branchen_abgedeckt(self):
        """BRANCHENEFFEKTE muss alle 21 Branchen aus scores.csv enthalten."""
        expected_branches = {
            "Industrie", "Finanzen", "Verwaltung", "Gastgewerbe", "Gesundheit",
            "ICT", "Bau", "Bildung", "Soziales", "Transport", "Detailhandel",
            "Medien", "Dienstleistungen", "Landwirtschaft", "Öff. Verwaltung",
            "Versicherungen", "Recht", "Immobilien", "Beratung", "Sicherheit",
            "Umwelt",
        }
        assert expected_branches == set(BRANCHENEFFEKTE.keys()), (
            f"Fehlende Branchen: {expected_branches - set(BRANCHENEFFEKTE.keys())}"
        )

    def test_verwaltung_und_oeff_verwaltung_verschieden(self):
        """'Verwaltung' (privat, +0.1) und 'Öff. Verwaltung' (öffentl., -0.1) haben verschiedene Deltas."""
        assert BRANCHENEFFEKTE["Verwaltung"] != BRANCHENEFFEKTE["Öff. Verwaltung"]
        assert BRANCHENEFFEKTE["Verwaltung"] > 0
        assert BRANCHENEFFEKTE["Öff. Verwaltung"] < 0

    def test_neue_branchen_soziales(self):
        """Soziales erhält negativen Delta (wie Gesundheit)."""
        df = pd.DataFrame({
            "branche": ["Soziales"],
            "lohn_median_chf": [70000],
            "score_gesamt": [5.0],
        })
        result = apply_ch_adjustments(df)
        assert result["delta_branche"].iloc[0] < 0

    def test_neue_branchen_bau(self):
        """Bau erhält negativen Delta (physische Arbeit)."""
        df = pd.DataFrame({
            "branche": ["Bau"],
            "lohn_median_chf": [80000],
            "score_gesamt": [5.0],
        })
        result = apply_ch_adjustments(df)
        assert result["delta_branche"].iloc[0] < 0

    def test_neue_branchen_beratung(self):
        """Beratung erhält positiven Delta (Wissensarbeit, KI-augmentierbar)."""
        df = pd.DataFrame({
            "branche": ["Beratung"],
            "lohn_median_chf": [120000],
            "score_gesamt": [5.0],
        })
        result = apply_ch_adjustments(df)
        assert result["delta_branche"].iloc[0] > 0

    def test_alle_branchen_kein_fehler(self):
        """Alle 21 bekannten Branchen erzeugen keinen Fehler und haben delta != None."""
        branches = list(BRANCHENEFFEKTE.keys())
        df = pd.DataFrame({
            "branche": branches,
            "lohn_median_chf": [80000] * len(branches),
            "score_gesamt": [5.0] * len(branches),
        })
        result = apply_ch_adjustments(df)
        assert result["delta_branche"].notna().all()
        assert (result["score_ch"] >= 0).all()
        assert (result["score_ch"] <= 10).all()

    def test_alle_lohn_effekte_definiert(self):
        """Alle LOHNEFFEKTE-Werte sind numerisch."""
        for klasse, delta in LOHNEFFEKTE.items():
            assert isinstance(delta, float), f"{klasse}: {delta} ist kein float"

    def test_mit_jahresbruttolohn_spalte(self):
        """Wenn jahresbruttolohn vorhanden, wird delta_lohn berechnet."""
        df = pd.DataFrame({
            "branche": ["Finanzen"],
            "jahresbruttolohn": [130_000],
            "score_gesamt": [5.0],
        })
        result = apply_ch_adjustments(df)
        assert result["delta_lohn"].iloc[0] == LOHNEFFEKTE["100k–150k CHF"]
        assert result["score_ch"].iloc[0] > 5.0

    def test_lohnklasse_spalte_wird_erstellt(self):
        """Mit jahresbruttolohn entsteht eine lohnklasse-Spalte."""
        df = pd.DataFrame({
            "branche": ["ICT"],
            "jahresbruttolohn": [80_000],
            "score_gesamt": [5.0],
        })
        result = apply_ch_adjustments(df)
        assert "lohnklasse" in result.columns
        assert result["lohnklasse"].iloc[0] == "60k–100k CHF"

    def test_mit_lohn_median_chf_spalte(self):
        """lohn_median_chf (scores.csv-Spaltenname) wird korrekt verarbeitet."""
        df = pd.DataFrame({
            "branche": ["Finanzen"],
            "lohn_median_chf": [160_000],
            "score_gesamt": [5.0],
        })
        result = apply_ch_adjustments(df)
        assert result["delta_lohn"].iloc[0] == LOHNEFFEKTE["> 150k CHF"]
        assert result["score_ch"].iloc[0] > 5.0

    def test_lohn_median_chf_hat_vorrang_vor_jahresbruttolohn(self):
        """lohn_median_chf hat Vorrang wenn beide Spalten vorhanden."""
        df = pd.DataFrame({
            "branche": ["ICT"],
            "lohn_median_chf": [200_000],   # > 150k → +0.4
            "jahresbruttolohn": [50_000],    # < 60k  → -0.2
            "score_gesamt": [5.0],
        })
        result = apply_ch_adjustments(df)
        assert result["delta_lohn"].iloc[0] == LOHNEFFEKTE["> 150k CHF"]
