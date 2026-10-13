"""Tests für update_from_bfs.py (BFS Strukturerhebung, Blattauswahl)."""

from pathlib import Path

import pandas as pd
import pytest

from ch_adjustments import BRANCHENEFFEKTE
from update_from_bfs import (
    BRANCHE_DEFAULT,
    BRANCHE_MAP,
    DEFAULT_BLATT,
    assign_metadata,
    branche_fuer_isco,
    parse_args,
    parse_bfs_excel,
)


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


class TestBrancheFuerIsco:
    @pytest.mark.parametrize("isco, erwartet", [
        ("1321", "Industrie"),
        ("1322", "Industrie"),
        ("1323", "Bau"),
        ("1324", "Transport"),
        ("1330", "ICT"),
        ("1341", "Soziales"),
        ("1342", "Gesundheit"),
        ("1343", "Soziales"),
        ("1344", "Soziales"),
        ("1345", "Bildung"),
        ("1346", "Finanzen"),
        ("1311", "Landwirtschaft"),
    ])
    def test_gruppe_13_nach_wirtschaftszweig(self, isco, erwartet):
        assert branche_fuer_isco(isco) == erwartet

    @pytest.mark.parametrize("isco, erwartet", [
        ("1411", "Gastgewerbe"),
        ("1412", "Gastgewerbe"),
        ("1420", "Detailhandel"),
        ("1431", "Dienstleistungen"),
        ("1439", "Dienstleistungen"),
    ])
    def test_gruppe_14_nach_wirtschaftszweig(self, isco, erwartet):
        assert branche_fuer_isco(isco) == erwartet

    def test_keine_fuehrungskraft_13_14_im_gastgewerbe(self):
        """Regression #50: 13xx/142x/143x dürfen nicht pauschal im Gastgewerbe landen."""
        for isco in ["1321", "1322", "1323", "1324", "1330", "1341", "1342",
                     "1343", "1344", "1345", "1346", "1349", "1420", "1431", "1439"]:
            assert branche_fuer_isco(isco) != "Gastgewerbe", isco

    def test_4_stellig_vor_3_stellig_vor_2_stellig(self):
        # 2-stellig "33" → Finanzen, 3-stellig "332" → Dienstleistungen, 4-stellig "3321" → Versicherungen
        assert BRANCHE_MAP["33"] == "Finanzen"
        assert branche_fuer_isco("3311") == "Finanzen"
        assert branche_fuer_isco("3322") == "Dienstleistungen"
        assert branche_fuer_isco("3321") == "Versicherungen"
        # 3-stellig "343" → Medien, 4-stellig "3434" → Gastgewerbe
        assert branche_fuer_isco("3431") == "Medien"
        assert branche_fuer_isco("3434") == "Gastgewerbe"

    def test_unbekannter_code_default(self):
        assert branche_fuer_isco("") == BRANCHE_DEFAULT
        assert branche_fuer_isco("9") == BRANCHE_DEFAULT
        assert branche_fuer_isco("0") == BRANCHE_DEFAULT

    def test_code_als_int_und_mit_leerzeichen(self):
        assert branche_fuer_isco(1330) == "ICT"
        assert branche_fuer_isco(" 1323 ") == "Bau"

    def test_weitere_korrekturen(self):
        assert branche_fuer_isco("1112") == "Öff. Verwaltung"
        assert branche_fuer_isco("1114") == "Verwaltung"
        assert branche_fuer_isco("7512") == "Industrie"      # Bäcker: verarbeitendes Gewerbe
        assert branche_fuer_isco("9214") == "Landwirtschaft"
        assert branche_fuer_isco("9313") == "Bau"
        assert branche_fuer_isco("9333") == "Transport"
        assert branche_fuer_isco("8342") == "Bau"
        assert branche_fuer_isco("3344") == "Gesundheit"
        assert branche_fuer_isco("2636") != "Medien"

    def test_alle_branchen_haben_delta(self):
        """Jede Ziel-Branche muss in ch_adjustments.BRANCHENEFFEKTE existieren."""
        assert set(BRANCHE_MAP.values()) | {BRANCHE_DEFAULT} <= set(BRANCHENEFFEKTE)

    def test_schluessel_sind_2_bis_4_stellige_ziffern(self):
        for key in BRANCHE_MAP:
            assert key.isdigit() and 2 <= len(key) <= 4, key

    def test_assign_metadata_nutzt_praefix_aufloesung(self):
        branche, qualifikation, lohn = assign_metadata("1330")
        assert branche == "ICT"
        assert qualifikation == "Tertiär"
        assert lohn == 9594 * 12  # LSE 2024, Gruppe 13 (2-stellig) × 12

    def test_keine_toten_isco_gruppen_27_bis_29(self):
        """ISCO-08 kennt keine Untergruppen 27–29."""
        assert not {"27", "28", "29"} & set(BRANCHE_MAP)

    def test_assign_metadata_lohn_fallback(self):
        """Gruppen ohne LSE-Wert: 63 → Hauptgruppe 6, 01 (Armee) → Gesamtmedian."""
        assert assign_metadata("6310")[2] == 5670 * 12
        assert assign_metadata("0110")[2] == 7024 * 12
