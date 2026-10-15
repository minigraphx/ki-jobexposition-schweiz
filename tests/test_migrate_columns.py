"""Tests für column_mapping.py und migrate_columns.py (Issue #53: englische Spaltennamen)."""
import re
import shutil
from pathlib import Path

import pandas as pd
import pytest

import column_mapping as cm
import migrate_columns as mc

PROC = Path(__file__).parent.parent / "data" / "processed"
SNAKE = re.compile(r"^[a-z][a-z0-9_]*$")


class TestMapping:
    def test_neue_namen_snake_case_ascii(self):
        for datei, m in cm.SPALTEN.items():
            for neu in m.values():
                assert SNAKE.match(neu), (datei, neu)
        assert all(SNAKE.match(s) for s in cm.SCORES_SCHEMA)

    def test_eindeutig_je_datei(self):
        for datei, m in cm.SPALTEN.items():
            assert len(set(m.values())) == len(m), datei
        assert len(set(cm.SCORES_SCHEMA)) == len(cm.SCORES_SCHEMA)

    def test_entfernte_spalten_nicht_umbenannt(self):
        for datei, weg in cm.ENTFERNT.items():
            assert not set(weg) & set(cm.SPALTEN[datei]), datei

    def test_alte_namen_kollidieren_nicht_mit_neuen(self):
        """Ein alter Name darf in derselben Datei nicht zugleich ein neuer Name einer anderen Spalte sein."""
        for datei, m in cm.SPALTEN.items():
            for alt, neu in m.items():
                if alt != neu:
                    assert alt not in cm.neue_spalten(datei), (datei, alt)

    def test_scores_schema_bloecke(self):
        assert cm.SCORES_SCHEMA[:len(cm.STAMMDATEN)] == list(cm.STAMMDATEN.values())
        assert cm.SCORES_SCHEMA[-2:] == ["adaptability", "legacy_score"]
        for s in cm.SCORES_EXPOSITION:   # Expositions-Block stammt aus scores_aufgaben.csv
            assert s in cm.SCORES_AUFGABEN.values(), s

    def test_versionierte_csvs_haben_mapping(self):
        assert {p.name for p in PROC.glob("*.csv")} <= set(cm.SPALTEN)


def _schreibe(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


class TestMigration:
    def test_kopf_neu_rest_byte_gleich(self, tmp_path):
        p = _schreibe(tmp_path / "statent_beschaeftigte_noga.csv",
                      'jahr,noga,beschaeftigte,vzae\n2024,01,3,"1,5"\n2024,02,"x\ny",7.0\n')
        mc.migriere(tmp_path)
        assert p.read_text(encoding="utf-8") == 'year,noga,employed,fte\n2024,01,3,"1,5"\n2024,02,"x\ny",7.0\n'

    def test_idempotent_und_dry_run(self, tmp_path):
        p = _schreibe(tmp_path / "statent_vzae_grossregion.csv", "jahr,noga,region,vzae\n2024,01,1,5\n")
        mc.migriere(tmp_path, dry_run=True)
        assert p.read_text(encoding="utf-8").startswith("jahr,")
        mc.migriere(tmp_path)
        einmal = p.read_bytes()
        plaene = mc.migriere(tmp_path)
        assert p.read_bytes() == einmal and plaene[0].status == mc.BEREITS

    def test_scores_entfernt_alte_methode(self, tmp_path):
        df = pd.DataFrame({"beruf": ["A"], "isco_code": ["0110"], "score_gesamt": ["5.0"],
                           "adaptabilitaet": ["6.1"], "score_ch": ["5.2"], "begruendung": ["Text, mit Komma"]})
        df.to_csv(tmp_path / "scores.csv", index=False)
        mc.migriere(tmp_path)
        neu = pd.read_csv(tmp_path / "scores.csv", dtype=str, keep_default_na=False)
        assert list(neu.columns) == ["occupation", "isco_code", "adaptability", "legacy_score"]
        assert neu.iloc[0].tolist() == ["A", "0110", "6.1", "5.2"]

    @pytest.mark.parametrize("kopf, meldung", [
        ("jahr,noga,vzae,extra", "unbekannte Spalten"),
        ("jahr,noga,region,fte", "gemischte"),
    ])
    def test_verweigert_unbekannte_spalten(self, tmp_path, kopf, meldung):
        ok = _schreibe(tmp_path / "se_berufe.csv", "blatt,ebene,code\n2024,4,1111\n")
        _schreibe(tmp_path / "statent_vzae_grossregion.csv", kopf + "\n1,2,3,4\n")
        with pytest.raises(mc.MigrationsFehler, match=meldung):
            mc.migriere(tmp_path)
        assert ok.read_text(encoding="utf-8").startswith("blatt,")   # nichts geschrieben
        assert mc.main(["--data-dir", str(tmp_path)]) == 1

    def test_verweigert_unbekannte_datei(self, tmp_path):
        _schreibe(tmp_path / "neu.csv", "a,b\n1,2\n")
        with pytest.raises(mc.MigrationsFehler, match="keine Zuordnung"):
            mc.migriere(tmp_path)

    def test_pruefung_erkennt_veraenderte_werte(self, tmp_path, monkeypatch):
        p = _schreibe(tmp_path / "statent_vzae_grossregion.csv", "jahr,noga,region,vzae\n2024,01,1,5\n")
        original = p.read_bytes()
        echt = mc._lesen

        def kaputt(path):
            df = echt(path)
            if "fte" in df.columns:
                df.loc[0, "fte"] = "6"
            return df
        monkeypatch.setattr(mc, "_lesen", kaputt)
        with pytest.raises(mc.MigrationsFehler, match="Werte der Spalte vzae"):
            mc.migriere(tmp_path)
        assert p.read_bytes() == original   # zurückgesetzt


def test_versionierte_daten_migriert(tmp_path):
    """Alle versionierten CSVs sind migriert: ein weiterer Lauf ändert nichts."""
    ziel = tmp_path / "processed"
    shutil.copytree(PROC, ziel, ignore=shutil.ignore_patterns("bewertungen"))
    vorher = {p.name: p.read_bytes() for p in ziel.glob("*.csv")}
    plaene = mc.migriere(ziel)
    assert {p.status for p in plaene} == {mc.BEREITS}
    assert {p.name: p.read_bytes() for p in ziel.glob("*.csv")} == vorher
    for p in plaene:
        assert not set(p.kopf) & cm.nur_alt(p.datei), p.datei
