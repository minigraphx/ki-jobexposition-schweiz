"""Unit Tests für src/scoring/ch_adjustments.py"""

import pandas as pd
import pytest

from ch_adjustments import (
    apply_ch_adjustments,
    classify_lohn,
    BRANCHENEFFEKTE,
    LOHNEFFEKTE,
    PHARMA_MEDTECH_ISCO_WHITELIST,
)


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

    def test_unbekannte_branche_wirft_valueerror(self):
        """Unbekannte Branche (non-NaN) ist ein Datenfehler → ValueError."""
        df = pd.DataFrame({
            "branche": ["Raumfahrt"],
            "lohn_median_chf": [80000],
            "score_gesamt": [5.0],
        })
        with pytest.raises(ValueError, match="Branchen ohne Delta-Mapping"):
            apply_ch_adjustments(df)

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


class TestPharmaOverride:
    def test_industrie_pharma_isco_override_zu_null(self):
        """Industrie + ISCO 2145 (Pharma/Medtech) → delta_branche == 0.0 statt -0.1."""
        df = pd.DataFrame({
            "branche": ["Industrie"],
            "isco_code": ["2145"],
            "lohn_median_chf": [110_000],
            "score_gesamt": [5.0],
        })
        result = apply_ch_adjustments(df)
        assert result["delta_branche"].iloc[0] == 0.0

    def test_industrie_nicht_pharma_isco_bleibt_negativ(self):
        """Industrie + ISCO 7212 (nicht in Whitelist) → delta_branche == -0.1."""
        df = pd.DataFrame({
            "branche": ["Industrie"],
            "isco_code": ["7212"],
            "lohn_median_chf": [80_000],
            "score_gesamt": [5.0],
        })
        result = apply_ch_adjustments(df)
        assert result["delta_branche"].iloc[0] == pytest.approx(-0.1)

    def test_nicht_industrie_pharma_isco_unveraendert(self):
        """Finanzen + ISCO 2145 → Pharma-Override greift nicht, Finanzen-Delta bleibt."""
        df = pd.DataFrame({
            "branche": ["Finanzen"],
            "isco_code": ["2145"],
            "lohn_median_chf": [100_000],
            "score_gesamt": [5.0],
        })
        result = apply_ch_adjustments(df)
        assert result["delta_branche"].iloc[0] == pytest.approx(BRANCHENEFFEKTE["Finanzen"])

    def test_ohne_isco_code_spalte_kein_absturz(self):
        """DataFrame ohne isco_code-Spalte → Pharma-Override wird übersprungen, kein Fehler."""
        df = pd.DataFrame({
            "branche": ["Industrie"],
            "lohn_median_chf": [80_000],
            "score_gesamt": [5.0],
        })
        result = apply_ch_adjustments(df)
        assert result["delta_branche"].iloc[0] == pytest.approx(BRANCHENEFFEKTE["Industrie"])

    def test_pharma_whitelist_enthaelt_erwartete_codes(self):
        """PHARMA_MEDTECH_ISCO_WHITELIST enthält die spezifizierten ISCO-Codes."""
        expected = {"2131", "2145", "2212", "3141", "3212"}
        assert expected == PHARMA_MEDTECH_ISCO_WHITELIST
