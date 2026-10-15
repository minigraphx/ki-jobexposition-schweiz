"""Tests für branche_neu_zuordnen.py (BRANCHE_MAP auf bestehende CSVs anwenden)."""

from pathlib import Path

import pandas as pd

import branche_neu_zuordnen as bnz


def _scores_csv(path: Path) -> Path:
    df = pd.DataFrame({
        "occupation": ["Führungskräfte in der Erbringung von Dienstleistungen im Bereich ICT",
                       "Softwareentwickler/in",  # kuratiert → bleibt
                       "Köche"],
        "isco_code": ["1330", "2512", "5120"],
        "sector": ["Gastgewerbe", "ICT", "Gastgewerbe"],
        "wage_median_chf": [85000, 130000, 52000],
        "exposure": [4.2, 7.0, 0.8],
        "rationale": ["Text A", "Text B", "Text C"],
        "timeframe_raw": ["5-10 Jahre", "3-5 Jahre", "5-10 Jahre"],
        "large_firm_share": [0.0238, 0.3063, 0.0238],
        "timeframe_sme_shift": [1, 0, 1],
        "timeframe": [">10 Jahre", "3-5 Jahre", ">10 Jahre"],
        "adaptability": [6.7, 9.0, 3.3],
        "legacy_score": [4.1, 7.0, 2.3],
    })
    path.mkdir(parents=True, exist_ok=True)
    df.to_csv(path / "scores.csv", index=False)
    return path / "scores.csv"


def _kmu_csv(path: Path) -> Path:
    kmu = path / "kmu_anteil_branche.csv"
    pd.DataFrame({
        "sector": ["Gastgewerbe", "ICT"],
        "large_firm_share": [0.0238, 0.3063],
    }).to_csv(kmu, index=False)
    return kmu


class TestNeueBranchen:
    def test_kuratierte_berufe_bleiben(self):
        df = pd.DataFrame({
            "occupation": ["Unternehmensberater/in", "Fachkräfte in Marketing und Werbung"],
            "isco_code": ["2421", "2431"],
            "sector": ["Beratung", "Finanzen"],
        })
        assert bnz.neue_branchen(df).tolist() == ["Beratung", "Medien"]

    def test_unveraendert_wenn_mapping_passt(self):
        df = pd.DataFrame({"occupation": ["Köche"], "isco_code": ["5120"], "sector": ["Gastgewerbe"]})
        assert bnz.neue_branchen(df).tolist() == ["Gastgewerbe"]


class TestMain:
    def _setup(self, tmp_path, monkeypatch) -> Path:
        path = _scores_csv(tmp_path)
        kmu = _kmu_csv(tmp_path)
        monkeypatch.setattr(bnz, "BASIS_DATEIEN", [])
        orig = bnz.adjust_zeitrahmen_fuer_kmu
        monkeypatch.setattr(bnz, "adjust_zeitrahmen_fuer_kmu", lambda df: orig(df, kmu_path=kmu))
        return path

    def test_nur_geaenderte_zeilen_und_folgespalten(self, tmp_path, monkeypatch):
        path = self._setup(tmp_path, monkeypatch)
        original = pd.read_csv(path, dtype=str, keep_default_na=False)

        bnz.main(["--data-dir", str(tmp_path)])
        result = pd.read_csv(path, dtype=str, keep_default_na=False)

        # Nur die erste Zeile (1330) ist betroffen
        assert result.loc[1:].equals(original.loc[1:])
        row = result.iloc[0]
        assert row["sector"] == "ICT"
        assert row["timeframe"] == "5-10 Jahre"      # ICT neutral → Rohwert
        assert row["timeframe_raw"] == "5-10 Jahre"
        assert row["timeframe_sme_shift"] == "0"
        assert float(row["large_firm_share"]) == 0.3063
        assert float(row["adaptability"]) == 7.4    # 6.7 − 0.3 (Gastgewerbe) + 1.0 (ICT)
        # Exposition, Texte und alter Score unverändert: die Branche wirkt nur auf den Zeitrahmen
        for col in ["exposure", "rationale", "legacy_score", "wage_median_chf"]:
            assert row[col] == original.iloc[0][col]

    def test_idempotent(self, tmp_path, monkeypatch):
        path = self._setup(tmp_path, monkeypatch)
        bnz.main(["--data-dir", str(tmp_path)])
        erster_lauf = path.read_bytes()
        bnz.main(["--data-dir", str(tmp_path)])
        assert path.read_bytes() == erster_lauf

    def test_dry_run_schreibt_nicht(self, tmp_path, monkeypatch):
        path = self._setup(tmp_path, monkeypatch)
        vorher = path.read_bytes()
        bnz.main(["--data-dir", str(tmp_path), "--dry-run"])
        assert path.read_bytes() == vorher

    def test_fehlende_datei_wird_uebersprungen(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(bnz, "BASIS_DATEIEN", ["gibt_es_nicht.csv"])
        bnz.main(["--data-dir", str(tmp_path)])
        assert "übersprungen" in capsys.readouterr().out
