"""Alle gespeicherten Bewertungen bleiben gültig: Input-Hash = heute berechneter Hash.

Eine Bewertung unter data/processed/bewertungen/<provider>/run<N>/ gilt nur dann als aktuell,
wenn meta.input_hash dem Hash entspricht, den task_inputs.py heute aus scores.csv und
esco_kompetenzen.csv berechnet (Rubrik-Version, Schema, Input-Datensatz). Ändert sich etwas an
den Stammdaten, den Spaltennamen-Zuordnungen in task_inputs.py oder am Schema, schlägt dieser
Test fehl — bevor die rund 800 Bewertungen unbemerkt veralten.

pilot_abo/ ist ausgenommen (Rubrik v2.1, Zuordnung über den Namen, kein Hash).
"""
import json
from pathlib import Path

import pytest

import task_inputs as ti

BEWERTUNGEN = Path(__file__).parent.parent / "data" / "processed" / "bewertungen"
PROVIDER = ("claude", "claude-cli", "gemini")


def _ok_dateien() -> list[Path]:
    res = []
    for p in PROVIDER:
        for f in sorted((BEWERTUNGEN / p).glob("run*/*.json")):
            meta = json.loads(f.read_text(encoding="utf-8")).get("meta") or {}
            if meta.get("status") == "ok":
                res.append(f)
    return res


@pytest.fixture(scope="module")
def hashes() -> dict[str, str]:
    return {e.datei: e.input_hash for e in ti.baue_eintraege()}


def test_bewertungen_vorhanden():
    dateien = _ok_dateien()
    assert len(dateien) >= 750
    assert {f.parent.parent.name for f in dateien} == set(PROVIDER)


def test_alle_ok_bewertungen_haben_aktuellen_input_hash(hashes):
    veraltet, unbekannt = [], []
    for f in _ok_dateien():
        meta = json.loads(f.read_text(encoding="utf-8"))["meta"]
        if f.name not in hashes:
            unbekannt.append(str(f.relative_to(BEWERTUNGEN)))
        elif meta["input_hash"] != hashes[f.name]:
            veraltet.append(str(f.relative_to(BEWERTUNGEN)))
    assert not unbekannt, f"kein Eintrag in scores.csv: {unbekannt[:10]}"
    assert not veraltet, f"{len(veraltet)} Bewertungen veraltet, z. B. {veraltet[:10]}"
