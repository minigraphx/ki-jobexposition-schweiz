"""Unit Tests für src/scoring/generate_demo_scores.py"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "scoring"))
from generate_demo_scores import apply_demo_scores, SCORE_LOOKUP


class TestApplyDemoScores:
    def test_bekannter_beruf_gemapped(self):
        df = pd.DataFrame({
            "beruf": ["Buchhalter/in"],
            "branche": ["Finanzen"],
            "qualifikation": ["Tertiär"],
        })
        result = apply_demo_scores(df)
        assert "score_gesamt" in result.columns
        assert result["score_gesamt"].iloc[0] > 0

    def test_unbekannter_beruf_fallback(self):
        """Beruf nicht in SCORE_LOOKUP → Fallback-Score aus Branche/Qualifikation."""
        df = pd.DataFrame({
            "beruf": ["Quantenphysiker XYZ"],
            "branche": ["Finanzen"],
            "qualifikation": ["Tertiär"],
        })
        result = apply_demo_scores(df)
        assert result["score_gesamt"].iloc[0] is not None
        assert not pd.isna(result["score_gesamt"].iloc[0])

    def test_alle_pflichtfelder_vorhanden(self, sample_jobs):
        result = apply_demo_scores(sample_jobs)
        for col in ["score_gesamt", "adaptabilitaet", "haupt_risiko", "zeitrahmen", "begruendung"]:
            assert col in result.columns, f"Spalte '{col}' fehlt"

    def test_score_range(self, sample_jobs):
        result = apply_demo_scores(sample_jobs)
        assert (result["score_gesamt"] >= 0).all()
        assert (result["score_gesamt"] <= 10).all()

    def test_immutability(self, sample_jobs):
        """Eingabe-DataFrame nicht verändern."""
        original_cols = set(sample_jobs.columns)
        apply_demo_scores(sample_jobs)
        assert set(sample_jobs.columns) == original_cols

    def test_score_lookup_struktur(self):
        """Alle SCORE_LOOKUP-Einträge haben korrekte Struktur."""
        for key, val in SCORE_LOOKUP.items():
            assert isinstance(key, str), f"Key '{key}' ist kein String"
            assert len(val) == 5, f"'{key}': erwartet 5 Werte, got {len(val)}"
            score, adapt, risiko, zeitrahmen, begruendung = val
            assert 0 <= score <= 10, f"'{key}': score_gesamt={score} ausserhalb 0–10"
            assert 0 <= adapt <= 10, f"'{key}': adaptabilitaet={adapt} ausserhalb 0–10"
            assert isinstance(risiko, str)
            assert isinstance(begruendung, str)

    def test_kassierer_hoher_score(self):
        """Kassierer/in sollte als hoch exponiert eingestuft werden."""
        df = pd.DataFrame({
            "beruf": ["Kassierer/in"],
            "branche": ["Detailhandel"],
            "qualifikation": ["Sekundär II"],
        })
        result = apply_demo_scores(df)
        assert result["score_gesamt"].iloc[0] >= 7.0

    def test_physiotherapeut_tiefer_score(self):
        """Physiotherapeut/in sollte tief exponiert sein."""
        df = pd.DataFrame({
            "beruf": ["Physiotherapeut/in"],
            "branche": ["Gesundheit"],
            "qualifikation": ["Tertiär"],
        })
        result = apply_demo_scores(df)
        assert result["score_gesamt"].iloc[0] <= 5.0
