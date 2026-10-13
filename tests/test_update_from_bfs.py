"""Tests für update_from_bfs.py (BFS Strukturerhebung, Blattauswahl)."""

from pathlib import Path

import pandas as pd
import pytest

from update_from_bfs import DEFAULT_BLATT, parse_args, parse_bfs_excel


def _blatt(isco: str, total: float, frauen: float | str) -> pd.DataFrame:
    """Minimales Blatt im Layout der BFS-SE-Tabelle (Spalten 0–4 Codes, 5 Bezeichnung, 6–8 Werte)."""
    rows = [
        ["Ausgeübter Beruf (Nomenklatur: CH-ISCO-19) …", None, None, None, None, None, None, None, None],
        [None, None, None, None, None, None, "Total", "Männer", "Frauen"],
        ["Berufshauptgruppe", "Berufsgruppe", "Berufsuntergruppe", "Berufsgattung", "Berufsart",
         None, 100.0, 50.0, 50.0],
        ["2", None, None, None, None, "Akademische Berufe", total, None, None],
        [None, "24", None, None, None, "Betriebswirtschaftler", total, None, None],
        [None, None, "241", None, None, "Akademische Fachkräfte Finanzen", total, None, None],
        # 4-stellige Berufsgattung → wird übernommen
        [None, None, None, isco, None, "Buchhalter/innen", total, 1.0, frauen],
        # 5-stellige Berufsart → wird ignoriert
        [None, None, None, None, isco + "1", "Buchhalter/innen Detail", total, 1.0, frauen],
        ["© BFS / Quelle: Strukturerhebung (SE)", None, None, None, None, None, None, None, None],
    ]
    return pd.DataFrame(rows)


@pytest.fixture
def bfs_excel(tmp_path: Path) -> Path:
    path = tmp_path / "bfs_se.xlsx"
    with pd.ExcelWriter(path) as writer:
        _blatt("2411", 40.0, 20.0).to_excel(writer, sheet_name="2022-2024", header=False, index=False)
        _blatt("2411", 32.0, 16.0).to_excel(writer, sheet_name="2024", header=False, index=False)
        _blatt("2411", 30.0, "X").to_excel(writer, sheet_name="2023", header=False, index=False)
    return path


class TestParseBfsExcel:
    def test_default_blatt_ist_2024(self, bfs_excel):
        assert DEFAULT_BLATT == "2024"
        bfs = parse_bfs_excel(bfs_excel)
        assert list(bfs["isco_code"]) == ["2411"]
        assert bfs.iloc[0]["beschaeftigte_total"] == pytest.approx(32.0)
        assert bfs.iloc[0]["frauen_pct"] == pytest.approx(50.0)

    def test_anderes_jahr(self, bfs_excel):
        bfs = parse_bfs_excel(bfs_excel, blatt="2023")
        assert bfs.iloc[0]["beschaeftigte_total"] == pytest.approx(30.0)
        # "X" (Datenschutz) → kein Frauenanteil
        assert pd.isna(bfs.iloc[0]["frauen_pct"])

    def test_gepooltes_blatt(self, bfs_excel):
        bfs = parse_bfs_excel(bfs_excel, blatt="2022-2024")
        assert bfs.iloc[0]["beschaeftigte_total"] == pytest.approx(40.0)

    def test_blatt_als_int(self, bfs_excel):
        bfs = parse_bfs_excel(bfs_excel, blatt=2023)
        assert bfs.iloc[0]["beschaeftigte_total"] == pytest.approx(30.0)

    def test_unbekanntes_blatt(self, bfs_excel):
        with pytest.raises(ValueError):
            parse_bfs_excel(bfs_excel, blatt="2025")


class TestParseArgs:
    def test_default(self):
        assert parse_args([]).blatt == "2024"

    def test_blatt_option(self):
        assert parse_args(["--blatt", "2022-2024"]).blatt == "2022-2024"
