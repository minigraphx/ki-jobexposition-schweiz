"""Historische Skripte brechen sofort mit einem Hinweis auf die aktuelle Pipeline ab."""
import runpy
from pathlib import Path

import pytest

SRC = Path(__file__).parent.parent / "src"

HISTORISCH = {
    "scoring/exposure_scorer.py": "task_scorer.py",
    "scoring/ch_adjustments.py": "kmu_faktor.py",
    "scoring/generate_demo_scores.py": "task_scorer.py",
    "scoring/fix_brennschneider_contamination.py": "apply_task_scores.py",
    "data/full_quality_audit.py": "task_scorer.py",
    "data/berufe_zusammenlegen.py": "beruf_berufsart_mapping.csv",
    "data/fetch_esco.py": "enrich_with_esco.py",
    "data/fetch_sake.py": "update_from_bfs.py",
    "data/verify_esco_matches.py": "esco_match_qualitaet",
    "data/patch_unmatched.py": "enrich_with_esco.py",
}


@pytest.mark.parametrize("pfad, hinweis", HISTORISCH.items())
def test_bricht_mit_hinweis_ab(pfad, hinweis):
    with pytest.raises(SystemExit) as ex:
        runpy.run_path(str(SRC / pfad), run_name="__main__")
    assert "historisch" in str(ex.value.code) and hinweis in str(ex.value.code)
