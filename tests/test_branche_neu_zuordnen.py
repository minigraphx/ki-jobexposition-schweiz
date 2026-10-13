"""Tests für branche_neu_zuordnen.py (BRANCHE_MAP auf bestehende CSVs anwenden)."""

from pathlib import Path

import pandas as pd

import branche_neu_zuordnen as bnz


def _scores_csv(path: Path) -> Path:
    df = pd.DataFrame({
        "beruf": ["Führungskräfte in der Erbringung von Dienstleistungen im Bereich ICT",
                  "Softwareentwickler/in",  # kuratiert → bleibt
                  "Köche"],
        "isco_code": ["1330", "2512", "5120"],
        "branche": ["Gastgewerbe", "ICT", "Gastgewerbe"],
        "lohn_median_chf": [85000, 130000, 52000],
        "score_gesamt": [4.2, 7.0, 2.6],
        "score_digital": [6.0, 9.0, 1.0],
        "adaptabilitaet": [6.7, 9.0, 3.3],
        "delta_branche": [-0.1, -0.2, -0.1],
        "lohnklasse": ["60k–100k CHF", "100k–150k CHF", "< 60k CHF"],
        "delta_lohn": [0.0, 0.2, -0.2],
        "score_ch": [4.1, 7.0, 2.3],
        "zeitrahmen_roh": ["5-10 Jahre", "3-5 Jahre", "5-10 Jahre"],
        "zeitrahmen": [">10 Jahre", "3-5 Jahre", ">10 Jahre"],
        "grossfirmen_anteil": [0.0238, 0.3063, 0.0238],
        "zeitrahmen_kmu_delta": [1, 0, 1],
        "begruendung": ["Text A", "Text B", "Text C"],
    })
    path.mkdir(parents=True, exist_ok=True)
    df.to_csv(path / "scores.csv", index=False)
    return path / "scores.csv"


def _kmu_csv(path: Path) -> Path:
    kmu = path / "kmu_anteil_branche.csv"
    pd.DataFrame({
        "branche": ["Gastgewerbe", "ICT"],
        "grossfirmen_anteil": [0.0238, 0.3063],
    }).to_csv(kmu, index=False)
    return kmu


class TestNeueBranchen:
    def test_kuratierte_berufe_bleiben(self):
        df = pd.DataFrame({
            "beruf": ["Unternehmensberater/in", "Fachkräfte in Marketing und Werbung"],
            "isco_code": ["2421", "2431"],
            "branche": ["Beratung", "Finanzen"],
        })
        assert bnz.neue_branchen(df).tolist() == ["Beratung", "Medien"]

    def test_unveraendert_wenn_mapping_passt(self):
        df = pd.DataFrame({"beruf": ["Köche"], "isco_code": ["5120"], "branche": ["Gastgewerbe"]})
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
        assert row["branche"] == "ICT"
        assert float(row["delta_branche"]) == -0.2
        assert float(row["score_ch"]) == 4.0          # 4.2 − 0.2 + 0.0
        assert row["zeitrahmen"] == "5-10 Jahre"      # ICT neutral → Rohwert
        assert row["zeitrahmen_roh"] == "5-10 Jahre"
        assert row["zeitrahmen_kmu_delta"] == "0"
        assert float(row["grossfirmen_anteil"]) == 0.3063
        assert float(row["adaptabilitaet"]) == 7.4    # 6.7 − 0.3 (Gastgewerbe) + 1.0 (ICT)
        # Rohscore und Texte unverändert
        for col in ["score_gesamt", "score_digital", "begruendung", "delta_lohn", "lohnklasse"]:
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
