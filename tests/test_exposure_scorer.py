"""Unit Tests für src/scoring/exposure_scorer.py

Alle Anthropic-API-Calls werden gemockt — kein echter API-Key nötig.
"""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from exposure_scorer import (
    compute_hash,
    find_jobs_to_score,
    get_beschreibung,
    parse_result,
    score_changed_jobs,
    score_single_job,
)


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def jobs_df() -> pd.DataFrame:
    return pd.DataFrame({
        "beruf": ["Buchhalter/in", "Krankenpfleger/in"],
        "isco_code": [2411, 2221],
        "esco_beschreibung": ["Erfasst Finanzdaten.", "Pflegt Patienten."],
    })


@pytest.fixture
def mock_client() -> MagicMock:
    return MagicMock()


def _score_payload(**overrides) -> dict:
    base = {
        "score_gesamt": 7.5, "score_digital": 8.0,
        "score_wiederholbarkeit": 7.0, "score_physisch": 2.0,
        "score_kreativitaet": 3.0, "score_sozial": 2.0,
        "haupt_risiko": "Automatisierung", "zeitrahmen": "3-5 Jahre",
        "begruendung": "Digitaler Beruf.",
    }
    return {**base, **overrides}


def _mock_response(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.content = [SimpleNamespace(text=json.dumps(payload))]
    return resp


# ── compute_hash ───────────────────────────────────────────────────────────────

class TestComputeHash:
    def test_gibt_string_zurueck(self):
        assert isinstance(compute_hash("Buchhalter/in", "Finanzdaten"), str)

    def test_laenge_12_zeichen(self):
        assert len(compute_hash("Buchhalter/in", "Finanzdaten")) == 12

    def test_gleiche_eingabe_gleicher_hash(self):
        assert compute_hash("A", "B") == compute_hash("A", "B")

    def test_unterschiedliche_beschreibung_anderer_hash(self):
        assert compute_hash("A", "alt") != compute_hash("A", "neu")

    def test_unterschiedlicher_beruf_anderer_hash(self):
        assert compute_hash("Arzt", "X") != compute_hash("Ärztin", "X")


# ── get_beschreibung ───────────────────────────────────────────────────────────

class TestGetBeschreibung:
    def test_gibt_beschreibung_zurueck(self):
        row = pd.Series({"esco_beschreibung": "Meine Beschreibung"})
        assert get_beschreibung(row) == "Meine Beschreibung"

    def test_none_gibt_fallback(self):
        row = pd.Series({"esco_beschreibung": None})
        assert get_beschreibung(row) == "Keine Beschreibung verfügbar."

    def test_nan_gibt_fallback(self):
        row = pd.Series({"esco_beschreibung": float("nan")})
        assert get_beschreibung(row) == "Keine Beschreibung verfügbar."

    def test_fehlende_spalte_gibt_fallback(self):
        row = pd.Series({"beruf": "Test"})
        assert get_beschreibung(row) == "Keine Beschreibung verfügbar."


# ── parse_result ───────────────────────────────────────────────────────────────

class TestParseResult:
    def test_plain_json(self):
        assert parse_result(json.dumps(_score_payload()))["score_gesamt"] == 7.5

    def test_markdown_json_block(self):
        raw = f"```json\n{json.dumps(_score_payload())}\n```"
        assert parse_result(raw)["score_digital"] == 8.0

    def test_plain_code_block(self):
        raw = f"```\n{json.dumps(_score_payload())}\n```"
        assert parse_result(raw)["zeitrahmen"] == "3-5 Jahre"

    def test_ungültiges_json_wirft_fehler(self):
        with pytest.raises(json.JSONDecodeError):
            parse_result("kein json")


# ── find_jobs_to_score ─────────────────────────────────────────────────────────

class TestFindJobsToScore:
    def test_keine_scores_csv_gibt_alle_zurueck(self, jobs_df, tmp_path):
        result = find_jobs_to_score(jobs_df, tmp_path / "scores.csv")
        assert len(result) == 2

    def test_kein_hash_in_csv_gibt_alle_zurueck(self, jobs_df, tmp_path):
        scores_path = tmp_path / "scores.csv"
        pd.DataFrame({"beruf": ["Buchhalter/in"]}).to_csv(scores_path, index=False)
        result = find_jobs_to_score(jobs_df, scores_path)
        assert len(result) == 2

    def test_unveraenderte_hashes_geben_leeres_result(self, jobs_df, tmp_path):
        scores_path = tmp_path / "scores.csv"
        # Aktuelle Hashes in scores.csv schreiben
        df = jobs_df.copy()
        df["beschreibung_hash"] = df.apply(
            lambda r: compute_hash(r["beruf"], r["esco_beschreibung"]), axis=1
        )
        df.to_csv(scores_path, index=False)
        result = find_jobs_to_score(jobs_df, scores_path)
        assert len(result) == 0

    def test_geaenderte_beschreibung_wird_erkannt(self, jobs_df, tmp_path):
        scores_path = tmp_path / "scores.csv"
        df = jobs_df.copy()
        df["beschreibung_hash"] = "alter_hash"
        df.to_csv(scores_path, index=False)
        result = find_jobs_to_score(jobs_df, scores_path)
        assert len(result) == 2

    def test_force_leer_gibt_alle_zurueck(self, jobs_df, tmp_path):
        result = find_jobs_to_score(jobs_df, tmp_path / "scores.csv", force=[])
        assert len(result) == 2

    def test_force_nach_name(self, jobs_df, tmp_path):
        result = find_jobs_to_score(
            jobs_df, tmp_path / "scores.csv", force=["Buchhalter/in"]
        )
        assert len(result) == 1
        assert result.iloc[0]["beruf"] == "Buchhalter/in"

    def test_force_case_insensitive(self, jobs_df, tmp_path):
        result = find_jobs_to_score(
            jobs_df, tmp_path / "scores.csv", force=["buchhalter/in"]
        )
        assert len(result) == 1

    def test_force_nach_isco_code(self, jobs_df, tmp_path):
        result = find_jobs_to_score(
            jobs_df, tmp_path / "scores.csv", force=["2411"]
        )
        assert len(result) == 1
        assert result.iloc[0]["beruf"] == "Buchhalter/in"

    def test_force_isco_praeffix(self, jobs_df, tmp_path):
        """ISCO-Präfix '2' trifft beide Berufe (2411 und 2221)."""
        result = find_jobs_to_score(
            jobs_df, tmp_path / "scores.csv", force=["2"]
        )
        assert len(result) == 2

    def test_force_unbekannter_term_gibt_leeres_result(self, jobs_df, tmp_path):
        result = find_jobs_to_score(
            jobs_df, tmp_path / "scores.csv", force=["Unbekannter Beruf"]
        )
        assert len(result) == 0

    def test_hash_spalte_in_result(self, jobs_df, tmp_path):
        result = find_jobs_to_score(jobs_df, tmp_path / "scores.csv")
        assert "_hash" in result.columns


# ── score_single_job ───────────────────────────────────────────────────────────

class TestScoreSingleJob:
    def test_gibt_dict_mit_scores_zurueck(self, jobs_df, mock_client):
        row = jobs_df.iloc[0]
        mock_client.messages.create.return_value = _mock_response(_score_payload())
        result = score_single_job(mock_client, row)
        assert result["score_gesamt"] == 7.5

    def test_prompt_enthaelt_beruf(self, jobs_df, mock_client):
        row = jobs_df.iloc[0]
        mock_client.messages.create.return_value = _mock_response(_score_payload())
        score_single_job(mock_client, row)
        call_content = mock_client.messages.create.call_args[1]["messages"][0]["content"]
        assert "Buchhalter/in" in call_content

    def test_prompt_enthaelt_beschreibung(self, jobs_df, mock_client):
        row = jobs_df.iloc[0]
        mock_client.messages.create.return_value = _mock_response(_score_payload())
        score_single_job(mock_client, row)
        call_content = mock_client.messages.create.call_args[1]["messages"][0]["content"]
        assert "Erfasst Finanzdaten." in call_content

    def test_model_korrekt(self, jobs_df, mock_client):
        row = jobs_df.iloc[0]
        mock_client.messages.create.return_value = _mock_response(_score_payload())
        score_single_job(mock_client, row)
        assert mock_client.messages.create.call_args[1]["model"] == "claude-sonnet-4-6"


# ── score_changed_jobs ─────────────────────────────────────────────────────────

class TestScoreChangedJobs:
    def _setup_mock(self, mock_client, payload=None):
        mock_client.messages.create.return_value = _mock_response(payload or _score_payload())

    def test_gibt_dataframe_mit_score_spalten(self, jobs_df, tmp_path):
        with patch("exposure_scorer.anthropic.Anthropic") as MockAnthropic, \
             patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test"}):
            mc = MagicMock()
            MockAnthropic.return_value = mc
            self._setup_mock(mc)
            result = score_changed_jobs(jobs_df, scores_path=tmp_path / "scores.csv")
        assert "score_gesamt" in result.columns

    def test_hash_wird_gespeichert(self, jobs_df, tmp_path):
        scores_path = tmp_path / "scores.csv"
        with patch("exposure_scorer.anthropic.Anthropic") as MockAnthropic, \
             patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test"}):
            mc = MagicMock()
            MockAnthropic.return_value = mc
            self._setup_mock(mc)
            result = score_changed_jobs(jobs_df, scores_path=scores_path)
        assert "beschreibung_hash" in result.columns
        assert result["beschreibung_hash"].notna().all()

    def test_keine_aenderung_gibt_bestehende_csv(self, jobs_df, tmp_path):
        scores_path = tmp_path / "scores.csv"
        # scores.csv mit aktuellen Hashes erstellen
        df = jobs_df.copy()
        df["beschreibung_hash"] = df.apply(
            lambda r: compute_hash(r["beruf"], r["esco_beschreibung"]), axis=1
        )
        df["score_gesamt"] = 5.0
        df.to_csv(scores_path, index=False)
        with patch("exposure_scorer.anthropic.Anthropic") as MockAnthropic, \
             patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test"}):
            mc = MagicMock()
            MockAnthropic.return_value = mc
            result = score_changed_jobs(jobs_df, scores_path=scores_path)
        mc.messages.create.assert_not_called()
        assert len(result) == 2

    def test_force_leer_scored_alle(self, jobs_df, tmp_path):
        with patch("exposure_scorer.anthropic.Anthropic") as MockAnthropic, \
             patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test"}):
            mc = MagicMock()
            MockAnthropic.return_value = mc
            self._setup_mock(mc)
            score_changed_jobs(jobs_df, scores_path=tmp_path / "scores.csv", force=[])
        assert mc.messages.create.call_count == 2

    def test_force_name_scored_nur_diesen(self, jobs_df, tmp_path):
        with patch("exposure_scorer.anthropic.Anthropic") as MockAnthropic, \
             patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test"}):
            mc = MagicMock()
            MockAnthropic.return_value = mc
            self._setup_mock(mc)
            score_changed_jobs(
                jobs_df, scores_path=tmp_path / "scores.csv",
                force=["Buchhalter/in"]
            )
        assert mc.messages.create.call_count == 1

    def test_neugesorter_beruf_ersetzt_alten(self, jobs_df, tmp_path):
        scores_path = tmp_path / "scores.csv"
        df = jobs_df.copy()
        df["beschreibung_hash"] = "alter_hash"
        df["score_gesamt"] = 3.0
        df.to_csv(scores_path, index=False)
        with patch("exposure_scorer.anthropic.Anthropic") as MockAnthropic, \
             patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test"}):
            mc = MagicMock()
            MockAnthropic.return_value = mc
            self._setup_mock(mc, _score_payload(score_gesamt=9.0))
            result = score_changed_jobs(jobs_df, scores_path=scores_path)
        assert (result["score_gesamt"] == 9.0).all()
        assert len(result) == 2
