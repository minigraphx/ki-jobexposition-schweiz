"""Unit Tests für src/scoring/exposure_scorer.py

Alle Anthropic-API-Calls werden gemockt — kein echter API-Key nötig.
"""

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "scoring"))
from exposure_scorer import (
    SCORING_PROMPT,
    build_batch_requests,
    collect_results,
    parse_result,
    score_all_jobs,
    submit_batch,
    wait_for_batch,
)


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_jobs_df() -> pd.DataFrame:
    return pd.DataFrame({
        "beruf": ["Buchhalter/in", "Krankenpfleger/in"],
        "esco_beschreibung": ["Erfasst Finanzdaten.", "Pflegt Patienten."],
    })


@pytest.fixture
def mock_client() -> MagicMock:
    return MagicMock()


def _make_score_payload(**overrides) -> dict:
    base = {
        "score_gesamt": 7.5,
        "score_digital": 8.0,
        "score_wiederholbarkeit": 7.0,
        "score_physisch": 2.0,
        "score_kreativitaet": 3.0,
        "score_sozial": 2.0,
        "haupt_risiko": "Automatisierung der Buchführung",
        "zeitrahmen": "3-5 Jahre",
        "begruendung": "Digitaler Beruf mit hoher Wiederholbarkeit.",
    }
    return {**base, **overrides}


# ── parse_result ───────────────────────────────────────────────────────────────

class TestParseResult:
    def test_plain_json(self):
        payload = _make_score_payload()
        result = parse_result(json.dumps(payload))
        assert result["score_gesamt"] == 7.5

    def test_json_in_markdown_json_block(self):
        payload = _make_score_payload()
        raw = f"```json\n{json.dumps(payload)}\n```"
        result = parse_result(raw)
        assert result["score_digital"] == 8.0

    def test_json_in_plain_code_block(self):
        payload = _make_score_payload()
        raw = f"```\n{json.dumps(payload)}\n```"
        result = parse_result(raw)
        assert result["zeitrahmen"] == "3-5 Jahre"

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            parse_result("das ist kein JSON")

    def test_alle_felder_vorhanden(self):
        payload = _make_score_payload()
        result = parse_result(json.dumps(payload))
        for key in ["score_gesamt", "score_digital", "score_wiederholbarkeit",
                    "score_physisch", "score_kreativitaet", "score_sozial",
                    "haupt_risiko", "zeitrahmen", "begruendung"]:
            assert key in result


# ── build_batch_requests ───────────────────────────────────────────────────────

class TestBuildBatchRequests:
    def test_anzahl_requests_stimmt(self, sample_jobs_df):
        reqs = build_batch_requests(sample_jobs_df)
        assert len(reqs) == 2

    def test_custom_id_entspricht_index(self, sample_jobs_df):
        reqs = build_batch_requests(sample_jobs_df)
        ids = [int(r["custom_id"]) for r in reqs]
        assert ids == list(sample_jobs_df.index)

    def test_model_gesetzt(self, sample_jobs_df):
        reqs = build_batch_requests(sample_jobs_df)
        for req in reqs:
            assert req["params"]["model"] == "claude-sonnet-4-6"

    def test_max_tokens_gesetzt(self, sample_jobs_df):
        reqs = build_batch_requests(sample_jobs_df)
        for req in reqs:
            assert req["params"]["max_tokens"] == 512

    def test_beruf_im_prompt(self, sample_jobs_df):
        reqs = build_batch_requests(sample_jobs_df)
        assert "Buchhalter/in" in reqs[0]["params"]["messages"][0]["content"]
        assert "Krankenpfleger/in" in reqs[1]["params"]["messages"][0]["content"]

    def test_beschreibung_im_prompt(self, sample_jobs_df):
        reqs = build_batch_requests(sample_jobs_df)
        assert "Erfasst Finanzdaten." in reqs[0]["params"]["messages"][0]["content"]

    def test_fehlende_beschreibung_fallback(self):
        df = pd.DataFrame({
            "beruf": ["Testberuf"],
            "esco_beschreibung": [None],
        })
        reqs = build_batch_requests(df)
        assert "Keine Beschreibung verfügbar." in reqs[0]["params"]["messages"][0]["content"]

    def test_leerer_dataframe(self):
        df = pd.DataFrame(columns=["beruf", "esco_beschreibung"])
        reqs = build_batch_requests(df)
        assert reqs == []

    def test_message_rolle_ist_user(self, sample_jobs_df):
        reqs = build_batch_requests(sample_jobs_df)
        assert reqs[0]["params"]["messages"][0]["role"] == "user"


# ── submit_batch ───────────────────────────────────────────────────────────────

class TestSubmitBatch:
    def test_gibt_batch_id_zurueck(self, sample_jobs_df, mock_client, tmp_path):
        mock_client.beta.messages.batches.create.return_value = SimpleNamespace(id="batch_abc123")
        with patch("exposure_scorer.BATCH_ID_FILE", tmp_path / ".batch_id"):
            result = submit_batch(mock_client, sample_jobs_df)
        assert result == "batch_abc123"

    def test_schreibt_batch_id_in_datei(self, sample_jobs_df, mock_client, tmp_path):
        mock_client.beta.messages.batches.create.return_value = SimpleNamespace(id="batch_xyz")
        batch_id_file = tmp_path / ".batch_id"
        with patch("exposure_scorer.BATCH_ID_FILE", batch_id_file):
            submit_batch(mock_client, sample_jobs_df)
        assert batch_id_file.read_text() == "batch_xyz"

    def test_ruft_create_mit_requests_auf(self, sample_jobs_df, mock_client, tmp_path):
        mock_client.beta.messages.batches.create.return_value = SimpleNamespace(id="b1")
        with patch("exposure_scorer.BATCH_ID_FILE", tmp_path / ".batch_id"):
            submit_batch(mock_client, sample_jobs_df)
        mock_client.beta.messages.batches.create.assert_called_once()
        kwargs = mock_client.beta.messages.batches.create.call_args
        assert len(kwargs[1]["requests"]) == 2


# ── wait_for_batch ─────────────────────────────────────────────────────────────

class TestWaitForBatch:
    def test_beendet_schleife_bei_ended(self, mock_client):
        ended = SimpleNamespace(
            processing_status="ended",
            request_counts=SimpleNamespace(succeeded=2, errored=0, processing=0),
        )
        mock_client.beta.messages.batches.retrieve.return_value = ended
        with patch("exposure_scorer.time.sleep") as mock_sleep:
            wait_for_batch(mock_client, "batch_123")
        mock_sleep.assert_not_called()

    def test_pollt_bis_ended(self, mock_client):
        processing = SimpleNamespace(
            processing_status="in_progress",
            request_counts=SimpleNamespace(succeeded=0, errored=0, processing=2),
        )
        ended = SimpleNamespace(
            processing_status="ended",
            request_counts=SimpleNamespace(succeeded=2, errored=0, processing=0),
        )
        mock_client.beta.messages.batches.retrieve.side_effect = [processing, processing, ended]
        with patch("exposure_scorer.time.sleep"):
            wait_for_batch(mock_client, "batch_123")
        assert mock_client.beta.messages.batches.retrieve.call_count == 3


# ── collect_results ────────────────────────────────────────────────────────────

def _make_api_result(custom_id: str, beruf: str, payload: dict | None = None, failed: bool = False):
    if failed:
        return SimpleNamespace(
            custom_id=custom_id,
            result=SimpleNamespace(type="errored"),
        )
    text = json.dumps(payload or _make_score_payload())
    return SimpleNamespace(
        custom_id=custom_id,
        result=SimpleNamespace(
            type="succeeded",
            message=SimpleNamespace(
                content=[SimpleNamespace(text=text)]
            ),
        ),
    )


class TestCollectResults:
    def test_merged_dataframe_hat_score_spalten(self, mock_client, sample_jobs_df):
        results = [
            _make_api_result("0", "Buchhalter/in"),
            _make_api_result("1", "Krankenpfleger/in", _make_score_payload(score_gesamt=3.0)),
        ]
        mock_client.beta.messages.batches.results.return_value = iter(results)
        merged = collect_results(mock_client, "batch_123", sample_jobs_df)
        assert "score_gesamt" in merged.columns
        assert len(merged) == 2

    def test_fehlgeschlagene_results_werden_uebersprungen(self, mock_client, sample_jobs_df):
        results = [
            _make_api_result("0", "Buchhalter/in"),
            _make_api_result("1", "Krankenpfleger/in", failed=True),
        ]
        mock_client.beta.messages.batches.results.return_value = iter(results)
        merged = collect_results(mock_client, "batch_123", sample_jobs_df)
        # Buchhalter hat Score, Krankenpfleger nicht (NaN nach left merge)
        assert merged.loc[merged["beruf"] == "Buchhalter/in", "score_gesamt"].notna().all()

    def test_ungültiges_json_wird_uebersprungen(self, mock_client, sample_jobs_df):
        bad_result = SimpleNamespace(
            custom_id="0",
            result=SimpleNamespace(
                type="succeeded",
                message=SimpleNamespace(content=[SimpleNamespace(text="kein json!")]),
            ),
        )
        good_result = _make_api_result("1", "Krankenpfleger/in")
        mock_client.beta.messages.batches.results.return_value = iter([bad_result, good_result])
        merged = collect_results(mock_client, "batch_123", sample_jobs_df)
        assert len(merged) == 2  # left merge behält alle Zeilen


# ── score_all_jobs ─────────────────────────────────────────────────────────────

class TestScoreAllJobs:
    def _setup_client_mock(self, mock_client, sample_jobs_df):
        mock_client.beta.messages.batches.create.return_value = SimpleNamespace(id="batch_new")
        mock_client.beta.messages.batches.retrieve.return_value = SimpleNamespace(
            processing_status="ended",
            request_counts=SimpleNamespace(succeeded=2, errored=0, processing=0),
        )
        api_results = [
            _make_api_result("0", "Buchhalter/in"),
            _make_api_result("1", "Krankenpfleger/in", _make_score_payload(score_gesamt=3.0)),
        ]
        mock_client.beta.messages.batches.results.return_value = iter(api_results)

    def test_gibt_dataframe_mit_scores_zurueck(self, sample_jobs_df, tmp_path):
        with patch("exposure_scorer.anthropic.Anthropic") as MockAnthropic, \
             patch("exposure_scorer.BATCH_ID_FILE", tmp_path / ".batch_id"), \
             patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            mock_client = MagicMock()
            MockAnthropic.return_value = mock_client
            self._setup_client_mock(mock_client, sample_jobs_df)
            result = score_all_jobs(sample_jobs_df)
        assert "score_gesamt" in result.columns
        assert len(result) == 2

    def test_verwendet_gespeicherte_batch_id(self, sample_jobs_df, tmp_path):
        batch_id_file = tmp_path / ".batch_id"
        batch_id_file.write_text("batch_existing")
        with patch("exposure_scorer.anthropic.Anthropic") as MockAnthropic, \
             patch("exposure_scorer.BATCH_ID_FILE", batch_id_file), \
             patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            mock_client = MagicMock()
            MockAnthropic.return_value = mock_client
            mock_client.beta.messages.batches.retrieve.return_value = SimpleNamespace(
                processing_status="ended",
                request_counts=SimpleNamespace(succeeded=2, errored=0, processing=0),
            )
            api_results = [
                _make_api_result("0", "Buchhalter/in"),
                _make_api_result("1", "Krankenpfleger/in"),
            ]
            mock_client.beta.messages.batches.results.return_value = iter(api_results)
            score_all_jobs(sample_jobs_df)
        # create darf nicht aufgerufen worden sein
        mock_client.beta.messages.batches.create.assert_not_called()

    def test_loescht_batch_id_datei_nach_abschluss(self, sample_jobs_df, tmp_path):
        batch_id_file = tmp_path / ".batch_id"
        with patch("exposure_scorer.anthropic.Anthropic") as MockAnthropic, \
             patch("exposure_scorer.BATCH_ID_FILE", batch_id_file), \
             patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            mock_client = MagicMock()
            MockAnthropic.return_value = mock_client
            self._setup_client_mock(mock_client, sample_jobs_df)
            score_all_jobs(sample_jobs_df)
        assert not batch_id_file.exists()

    def test_explizite_batch_id_ueberspringt_submit(self, sample_jobs_df, tmp_path):
        with patch("exposure_scorer.anthropic.Anthropic") as MockAnthropic, \
             patch("exposure_scorer.BATCH_ID_FILE", tmp_path / ".batch_id"), \
             patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            mock_client = MagicMock()
            MockAnthropic.return_value = mock_client
            mock_client.beta.messages.batches.retrieve.return_value = SimpleNamespace(
                processing_status="ended",
                request_counts=SimpleNamespace(succeeded=2, errored=0, processing=0),
            )
            api_results = [
                _make_api_result("0", "Buchhalter/in"),
                _make_api_result("1", "Krankenpfleger/in"),
            ]
            mock_client.beta.messages.batches.results.return_value = iter(api_results)
            score_all_jobs(sample_jobs_df, batch_id="batch_explicit")
        mock_client.beta.messages.batches.create.assert_not_called()
        mock_client.beta.messages.batches.retrieve.assert_called_with("batch_explicit")
