"""Tests für src/scoring/apply_task_scores.py (aufgabenbasierte Scores → scores.csv)."""
import shutil
from pathlib import Path

import pandas as pd
import pytest

import apply_task_scores as ats
import column_mapping as cm
import kmu_faktor as kf

PROC = Path(__file__).parent.parent / "data" / "processed"


def _lesen(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


# --------------------------------------------------------------------------- synthetisch

def _scores() -> pd.DataFrame:
    zeilen = []
    for occ, isco, sektor, lohn in [("A", "1111", "Finanzen", "100000"), ("B", "2222", "Gastgewerbe", "50000")]:
        z = {s: "" for s in cm.SCORES_STAMMDATEN}
        z.update(occupation=occ, isco_code=isco, sector=sektor, wage_median_chf=lohn, qualification="Tertiär")
        zeilen.append(z)
    df = pd.DataFrame(zeilen)
    df["adaptability"] = ["1.0", ""]
    df["legacy_score"] = ["5.3", ""]
    df["large_firm_share"] = ["", ""]          # Spalten aus der Migration, werden neu gesetzt
    return df


def _aufgaben() -> pd.DataFrame:
    zeilen = []
    for occ, isco, expo, tf in [("A", "1111", "6.0", "3-5 Jahre"), ("B", "2222", "0.5", "5-10 Jahre")]:
        z = {s: "x" for s in cm.SCORES_AUFGABEN.values()}
        z.update(occupation=occ, isco_code=isco, exposure=expo, timeframe=tf, uncertain="False",
                 uncertain_reason="", n_runs_claude="2", n_runs_gemini="2")
        zeilen.append(z)
    return pd.DataFrame(zeilen)


KMU = pd.DataFrame({"sector": ["Finanzen", "Gastgewerbe"], "large_firm_share": [0.6, 0.02]})


class TestUebernehmen:
    def test_schema_und_werte(self):
        out = ats.uebernehmen(_scores(), _aufgaben(), KMU)
        assert list(out.columns) == cm.SCORES_SCHEMA
        assert out["exposure"].tolist() == ["6.0", "0.5"]           # Zellen unverändert übernommen
        assert out["timeframe_raw"].tolist() == ["3-5 Jahre", "5-10 Jahre"]
        assert out["timeframe_sme_shift"].tolist() == ["-1", "1"]
        assert out["timeframe"].tolist() == ["1-2 Jahre", ">10 Jahre"]
        assert out["large_firm_share"].tolist() == ["0.6", "0.02"]
        assert out["legacy_score"].tolist() == ["5.3", ""]
        # 4 + 1.5 + 2·0.6 + 0.9 (Finanzen) = 7.6; 4 + 0 + 0.1 + 0.3 (Gastgewerbe) = 4.4
        assert out["adaptability"].tolist() == ["8.0", "5.4"]   # (Qualifikation + Lohn + Mobilität) × 10/8

    def test_reihenfolge_folgt_scores_csv(self):
        out = ats.uebernehmen(_scores(), _aufgaben().iloc[::-1].reset_index(drop=True), KMU)
        assert out["occupation"].tolist() == ["A", "B"] and out["exposure"].tolist() == ["6.0", "0.5"]

    def test_fehlende_bewertung_bricht_ab(self):
        with pytest.raises(ats.FehlendeBewertung, match="ohne aufgabenbasierte Bewertung.*2222 B"):
            ats.uebernehmen(_scores(), _aufgaben().iloc[[0]], KMU)

    def test_leere_exposition_bricht_ab(self):
        a = _aufgaben()
        a.loc[1, "exposure"] = ""
        with pytest.raises(ats.FehlendeBewertung, match="2222 B"):
            ats.uebernehmen(_scores(), a, KMU)

    def test_fremder_eintrag_bricht_ab(self):
        a = pd.concat([_aufgaben(), _aufgaben().iloc[[0]].assign(occupation="C")], ignore_index=True)
        with pytest.raises(ats.FehlendeBewertung, match="nicht in scores.csv"):
            ats.uebernehmen(_scores(), a, KMU)

    def test_doppelte_eintraege(self):
        s = pd.concat([_scores(), _scores().iloc[[0]]], ignore_index=True)
        with pytest.raises(ValueError, match="doppelte"):
            ats.uebernehmen(s, _aufgaben(), KMU)

    def test_unbekannte_branche(self):
        s = _scores()
        s.loc[0, "sector"] = "Raumfahrt"
        with pytest.raises(ValueError, match="Raumfahrt"):
            ats.uebernehmen(s, _aufgaben(), KMU)

    def test_fehlende_spalten(self):
        with pytest.raises(ValueError, match="Stammdaten"):
            ats.uebernehmen(_scores().drop(columns="sector"), _aufgaben(), KMU)
        with pytest.raises(ValueError, match="scores_aufgaben.csv"):
            ats.uebernehmen(_scores(), _aufgaben().drop(columns="main_risk"), KMU)


class TestMain:
    def _dateien(self, tmp_path: Path) -> list[str]:
        _scores().to_csv(tmp_path / "scores.csv", index=False)
        _aufgaben().to_csv(tmp_path / "scores_aufgaben.csv", index=False)
        KMU.to_csv(tmp_path / "kmu.csv", index=False)
        return ["--scores", str(tmp_path / "scores.csv"), "--aufgaben", str(tmp_path / "scores_aufgaben.csv"),
                "--kmu", str(tmp_path / "kmu.csv")]

    def test_dry_run_und_idempotent(self, tmp_path):
        argv = self._dateien(tmp_path)
        vorher = (tmp_path / "scores.csv").read_bytes()
        assert ats.main(argv + ["--dry-run"]) == 0
        assert (tmp_path / "scores.csv").read_bytes() == vorher
        assert ats.main(argv) == 0
        einmal = (tmp_path / "scores.csv").read_bytes()
        assert einmal != vorher
        assert ats.main(argv) == 0
        assert (tmp_path / "scores.csv").read_bytes() == einmal
        assert list(_lesen(tmp_path / "scores.csv").columns) == cm.SCORES_SCHEMA

    def test_fehler_ohne_schreiben(self, tmp_path, capsys):
        argv = self._dateien(tmp_path)
        _aufgaben().iloc[[0]].to_csv(tmp_path / "scores_aufgaben.csv", index=False)
        vorher = (tmp_path / "scores.csv").read_bytes()
        assert ats.main(argv) == 1
        assert "ohne aufgabenbasierte Bewertung" in capsys.readouterr().err
        assert (tmp_path / "scores.csv").read_bytes() == vorher

    def test_ohne_kmu_datei(self, tmp_path):
        argv = self._dateien(tmp_path)
        (tmp_path / "kmu.csv").unlink()
        assert ats.main(argv) == 1


# --------------------------------------------------------------------------- versionierte Daten

@pytest.fixture(scope="module")
def scores() -> pd.DataFrame:
    return _lesen(PROC / "scores.csv")


def test_scores_schema(scores):
    assert list(scores.columns) == cm.SCORES_SCHEMA
    assert (scores["exposure"] != "").all() and (scores["text_source"] != "").all()


def test_scores_entsprechen_scores_aufgaben(scores):
    a = _lesen(PROC / "scores_aufgaben.csv").set_index(["isco_code", "occupation"])
    s = scores.set_index(["isco_code", "occupation"])
    assert set(a.index) == set(s.index)
    for spalte in cm.SCORES_EXPOSITION:
        assert s[spalte].equals(a.loc[s.index, spalte]), spalte
    assert s["timeframe_raw"].equals(a.loc[s.index, "timeframe"])


def test_zeitrahmen_kmu_verschoben(scores):
    kmu = dict(zip(*[pd.read_csv(PROC / "kmu_anteil_branche.csv")[c] for c in ("sector", "large_firm_share")]))
    for _, r in scores.iterrows():
        d = kf.kmu_verschiebung(kmu.get(r["sector"]))
        assert r["timeframe_sme_shift"] == str(d)
        assert r["timeframe"] == kf.verschiebe_zeitrahmen(r["timeframe_raw"], d)


def test_versionierte_daten_reproduzierbar(tmp_path):
    """apply_task_scores.py erzeugt die committete scores.csv byte-identisch."""
    ziel = tmp_path / "scores.csv"
    shutil.copy(PROC / "scores.csv", ziel)
    assert ats.main(["--scores", str(ziel)]) == 0
    assert ziel.read_bytes() == (PROC / "scores.csv").read_bytes()
