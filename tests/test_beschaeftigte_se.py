"""Tests Issue #51: Beschäftigte aus BFS SE (Berufsgattung/Berufsart), Mapping, Zusammenlegungen."""

import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import berufe_zusammenlegen as bz
import update_from_bfs as ub
import update_loehne as ul

P = ub.PROCESSED_PATH


# ---------------------------------------------------------------------------
# Hilfsfunktionen mit synthetischen Daten
# ---------------------------------------------------------------------------

def _se(rows: list[tuple], blatt: str = "2024") -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=["ebene", "code", "bezeichnung", "total", "frauen"])
    df["maenner"] = df["total"] - df["frauen"]
    df["total_lt50"] = False
    df.insert(0, "blatt", blatt)
    return df


def _mapping(rows: list[tuple]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["beruf", "isco_code", "ebene", "berufsarten"]).assign(
        synonyme="", zusammengelegt_aus="", text_von="", begruendung="")


SE = pd.concat([
    _se([
        (4, "2330", "Lehrkräfte Sekundarbereich", 50.2, 28.6),
        (5, "23300", "Lehrkräfte Sekundarbereich onA", 7.0, 5.4),
        (5, "23301", "Sekundarstufe II", 17.4, 8.7),
        (5, "23302", "Sekundarstufe I", 25.8, 14.5),
        (4, "2146", "Bergbauingenieure", np.nan, np.nan),
        (5, "21460", "Bergbauingenieure", np.nan, np.nan),
        (4, "7112", "Maurer", 18.9, np.nan),
        (4, "5223", "Verkäufer", 3.0, 2.0),
        (5, "52230", "Verkäufer", 2.0, 1.0),
        (5, "52231", "Drogisten", 1.0, 1.0),
    ]),
    _se([
        (4, "2146", "Bergbauingenieure", 0.1, np.nan),
        (4, "7112", "Maurer", 20.4, 0.4),
    ], blatt="2022-2024"),
], ignore_index=True)


class TestRundeMitSumme:
    @pytest.mark.parametrize("werte", [[1.04, 1.04, 1.04], [20.31, 29.89], [0.05, 0.05], [7.0]])
    def test_summe_exakt(self, werte):
        res = ub.runde_mit_summe(werte, sum(werte))
        assert sum(res) == pytest.approx(round(sum(werte), 1), abs=1e-9)
        assert all(abs(a - b) < 0.1 + 1e-9 for a, b in zip(res, werte))


class TestBeschaeftigteBerechnen:
    def test_berufsarten_mit_proportionalem_rest(self):
        m = _mapping([("Gymnasiallehrer/in", "2330", "berufsart", "23301"),
                      ("Sekundarlehrer/in", "2330", "berufsart", "23302")])
        res = ub.beschaeftigte_berechnen(m, SE).set_index("beruf")
        # onA (7.0) proportional zu 17.4 : 25.8
        assert res.at["Gymnasiallehrer/in", "beschaeftigte_1000"] == pytest.approx(
            round(50.2 * 17.4 / 43.2, 1), abs=0.1)
        assert res["beschaeftigte_1000"].sum() == pytest.approx(50.2)
        assert res.at["Gymnasiallehrer/in", "frauen_pct"] == pytest.approx(50.0)

    def test_mehrere_berufsarten_je_beruf(self):
        m = _mapping([("Verkauf gesamt", "5223", "berufsart", "52230; 52231")])
        res = ub.beschaeftigte_berechnen(m, SE)
        assert res.iloc[0]["beschaeftigte_1000"] == pytest.approx(3.0)

    def test_gattung_voller_wert_und_frauen_aus_pool(self):
        m = _mapping([("Maurer/in", "7112", "gattung", "")])
        res = ub.beschaeftigte_berechnen(m, SE).iloc[0]
        assert res["beschaeftigte_1000"] == pytest.approx(18.9)       # Jahresblatt
        assert res["frauen_pct"] == pytest.approx(round(0.4 / 20.4 * 100, 1))  # Frauen «X» → gepoolt
        assert res["se_blatt"] == "2024"

    def test_nicht_publizierte_gattung_aus_pool(self):
        m = _mapping([("Qualitätsmanager/in", "2146", "gattung", "")])
        res = ub.beschaeftigte_berechnen(m, SE).iloc[0]
        assert res["beschaeftigte_1000"] == pytest.approx(0.1)
        assert pd.isna(res["frauen_pct"])
        assert res["se_blatt"] == "2022-2024"

    def test_geteilte_gattung_ohne_berufsart_fehler(self):
        m = _mapping([("A", "2330", "gattung", ""), ("B", "2330", "gattung", "")])
        with pytest.raises(ValueError, match="ebene=berufsart"):
            ub.beschaeftigte_berechnen(m, SE)

    def test_offene_berufsart_fehler(self):
        m = _mapping([("Gymnasiallehrer/in", "2330", "berufsart", "23301")])
        with pytest.raises(ValueError, match="ohne Beruf.*23302"):
            ub.beschaeftigte_berechnen(m, SE)

    def test_berufsart_doppelt_oder_fremd(self):
        m = _mapping([("A", "2330", "berufsart", "23301; 23302"), ("B", "2330", "berufsart", "23302")])
        with pytest.raises(ValueError, match="doppelt"):
            ub.beschaeftigte_berechnen(m, SE)
        m = _mapping([("A", "2330", "berufsart", "23301; 23302; 52231")])
        with pytest.raises(ValueError, match="gehört nicht"):
            ub.beschaeftigte_berechnen(m, SE)

    def test_unbekannte_gattung(self):
        with pytest.raises(ValueError, match="nicht in der SE"):
            ub.beschaeftigte_berechnen(_mapping([("X", "9999", "gattung", "")]), SE)


class TestParseSeExcel:
    def test_ebenen_x_und_klammerformat(self, tmp_path):
        import openpyxl

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "2024"
        ws.append(["Titel"])
        ws.append(["Berufshauptgruppe", "Berufsgruppe", "Berufsuntergruppe", "Berufsgattung", "Berufsart"])
        ws.append([None, None, None, "5223", None, "Verkäufer", 140.3, 35.0, 105.3])
        ws.append([None, None, None, None, "52230", "Verkäufer", 136.7, 34.7, 102.0])
        ws.append([None, None, None, None, "52231", "Drogisten", 3.6, "X", 3.2])
        ws.cell(row=5, column=7).number_format = r"\(##0\)"
        ws.append(["X", "X", "X", "X", "X", "Ausgeübter Beruf unbekannt", 98.9, 50.5, 48.4])
        path = tmp_path / "se.xlsx"
        wb.save(path)
        se = ub.parse_se_excel(path, "2024")
        assert se["code"].tolist() == ["5223", "52230", "52231"]
        assert se["ebene"].tolist() == [4, 5, 5]
        assert se["total_lt50"].tolist() == [False, False, True]
        assert pd.isna(se.iloc[2]["maenner"])
        with pytest.raises(ValueError, match="2025"):
            ub.parse_se_excel(path, "2025")

    def test_lade_se_ohne_rohdatei_aus_csv(self):
        se = ub.lade_se(raw=Path("/nicht/vorhanden.xlsx"), schreiben=False)
        assert set(se["blatt"]) == set(ub.SE_CSV_BLAETTER)
        g = se[(se["blatt"] == "2024") & (se["ebene"] == 4)].set_index("code")
        assert g.at["5223", "total"] == pytest.approx(140.3, abs=0.05)
        with pytest.raises(SystemExit):
            ub.lade_se(("2019",), raw=Path("/nicht/vorhanden.xlsx"), schreiben=False)

    @pytest.mark.skipif(not ub.BFS_FILE.exists(), reason="BFS-Rohdatei nur lokal vorhanden")
    def test_versionierte_csv_entspricht_rohdatei(self):
        roh = ub.lade_se(schreiben=False)
        csv = ub.lade_se(raw=Path("/nicht/vorhanden.xlsx"), schreiben=False)
        pd.testing.assert_frame_equal(roh.reset_index(drop=True), csv.reset_index(drop=True),
                                      check_dtype=False)


# ---------------------------------------------------------------------------
# Versionierte Daten
# ---------------------------------------------------------------------------

def _csv(name: str) -> pd.DataFrame:
    return pd.read_csv(P / name, dtype={"isco_code": str}, keep_default_na=False)


@pytest.fixture(scope="module")
def se_csv() -> pd.DataFrame:
    return ub.lade_se(raw=Path("/nicht/vorhanden.xlsx"), schreiben=False)


@pytest.fixture(scope="module")
def mapping() -> pd.DataFrame:
    return ub.lade_mapping()


class TestInvariante:
    def test_summe_je_gattung_gleich_se(self, se_csv):
        """Keine Doppelzählung: Σ beschaeftigte_1000 je 4-stelligem Code = SE-Wert."""
        scores = _csv("scores.csv")
        scores["b"] = scores["beschaeftigte_1000"].astype(float)
        for code, summe in scores.groupby("isco_code")["b"].sum().items():
            assert summe == pytest.approx(ub.se_gattungswert(se_csv, code), abs=1e-9), code

    def test_frauenanteil_aus_se(self, mapping, se_csv):
        werte = ub.beschaeftigte_berechnen(mapping, se_csv).set_index("beruf")
        scores = _csv("scores.csv").set_index("beruf")
        neu = pd.to_numeric(scores["frauen_pct"], errors="coerce")
        assert np.allclose(neu, werte.loc[neu.index, "frauen_pct"], equal_nan=True)

    def test_keine_doppelten_berufe(self):
        for name in ub.CSV_DATEIEN:
            df = _csv(name)
            assert not df.duplicated(["beruf", "isco_code"]).any(), name
            assert not df["beruf"].duplicated().any(), name

    def test_alle_csvs_konsistent(self):
        spalten = ["isco_code", "beschaeftigte_1000", "frauen_pct", "synonyme", "branche",
                   "lohn_median_chf", "qualifikation"]
        ref = _csv("scores.csv").set_index("beruf")[spalten].sort_index()
        for name in ub.CSV_DATEIEN[:-1]:
            df = _csv(name).set_index("beruf")[spalten].sort_index()
            pd.testing.assert_frame_equal(df, ref, obj=name)

    def test_summe_gesamt_plausibel(self):
        total = _csv("scores.csv")["beschaeftigte_1000"].astype(float).sum()
        assert 3000 < total < 4584  # SE 2024 total 4'583.7 Tsd.


class TestMapping:
    def test_vollstaendig(self, mapping):
        for name in ub.CSV_DATEIEN:
            df = _csv(name)
            assert set(df["beruf"]) == set(mapping["beruf"]), name
            codes = mapping.set_index("beruf")["isco_code"]
            assert (df["isco_code"] == df["beruf"].map(codes)).all(), name

    def test_spalten_und_begruendung(self, mapping):
        assert list(mapping.columns) == ["beruf", "isco_code", "ebene", "berufsarten", "synonyme",
                                         "zusammengelegt_aus", "text_von", "begruendung"]
        assert (mapping["begruendung"].str.len() > 10).all()
        art = mapping["ebene"] == ub.EBENE_BERUFSART
        assert (mapping.loc[art, "berufsarten"] != "").all()
        assert (mapping.loc[~art, "berufsarten"] == "").all()

    def test_geteilte_codes_nur_ueber_berufsarten(self, mapping):
        geteilt = mapping[mapping["isco_code"].duplicated(keep=False)]
        assert (geteilt["ebene"] == ub.EBENE_BERUFSART).all()
        assert set(geteilt["isco_code"]) == {"2330", "5131", "5223"}

    def test_codes_existieren_in_se(self, mapping, se_csv):
        g = se_csv[(se_csv["ebene"] == 4)]["code"]
        assert set(mapping["isco_code"]) <= set(g)

    def test_zusammenlegungen(self, mapping):
        zus = mapping[mapping["zusammengelegt_aus"] != ""]
        assert len(zus) == 22
        for _, r in zus.iterrows():
            teile = ub._liste(r["zusammengelegt_aus"])
            assert len(teile) >= 2
            assert r["text_von"] in teile
            assert set(ub._liste(r["synonyme"])) == set(teile) - {r["beruf"]}
        alle_syn = [s for x in mapping["synonyme"] for s in ub._liste(x)]
        assert len(alle_syn) == len(set(alle_syn))
        assert not set(alle_syn) & set(mapping["beruf"])

    def test_scores_markiert(self, mapping):
        scores = _csv("scores.csv").set_index("beruf")
        zus = set(mapping.loc[mapping["zusammengelegt_aus"] != "", "beruf"])
        markiert = set(scores.index[scores["scores_gemittelt"].astype(str) == "True"])
        assert markiert <= zus
        for beruf in zus:
            # entweder vorläufig gemittelt (ohne Hash) oder inzwischen neu bewertet (mit Hash)
            if beruf in markiert:
                assert scores.at[beruf, "beschreibung_hash"] == ""
            else:
                assert scores.at[beruf, "beschreibung_hash"] != ""

    def test_isco_korrekturen_angewendet(self, mapping):
        scores = _csv("scores.csv")
        for beruf, (alt, neu) in bz.ISCO_KORREKTUREN.items():
            assert not ((scores["beruf"] == beruf) & (scores["isco_code"] == alt)).any(), beruf
            if beruf in set(scores["beruf"]):
                assert scores.loc[scores["beruf"] == beruf, "isco_code"].iloc[0] == neu
            else:  # zusammengelegt: Zieleintrag hat den neuen Code
                ziel = mapping[mapping["zusammengelegt_aus"].map(lambda t: beruf in ub._liste(t))]
                assert ziel["isco_code"].tolist() == [neu], beruf

    def test_kuratierte_liste_passt(self):
        from build_berufeliste import BERUFE_CH

        scores = _csv("scores.csv").set_index("beruf")
        for beruf, code, _, _, branche, _, _ in BERUFE_CH:
            assert scores.at[beruf, "isco_code"] == code, beruf
            assert scores.at[beruf, "branche"] == branche, beruf


class TestGewichtetesMittel:
    def test_mittel(self):
        assert bz.gewichtetes_mittel([6.0, 3.0], [30.0, 10.0]) == pytest.approx(5.2)
        assert bz.gewichtetes_mittel([6.0, 3.0], [0.0, 0.0]) == pytest.approx(4.5)

    def test_zusammenlegen_synthetisch(self):
        df = pd.DataFrame({
            "beruf": ["A", "B", "C"], "isco_code": ["1111", "1111", "2222"],
            "beschaeftigte_1000": ["30.0", "10.0", "5.0"], "branche": ["X", "Y", "Z"],
            **{s: ["6.0", "2.0", "1.0"] for s in bz.SCORE_SPALTEN},
            "beschreibung_hash": ["h1", "h2", "h3"], "begruendung": ["Text A", "Text B", "Text C"],
        })
        m = pd.DataFrame([{"beruf": "AB", "isco_code": "1111", "ebene": "gattung", "berufsarten": "",
                           "synonyme": "A; B", "zusammengelegt_aus": "A; B", "text_von": "A",
                           "begruendung": "test"}])
        bz.zusammenlegen(df, m, scores=True)
        assert df["beruf"].tolist() == ["AB", "C"]
        ab = df.iloc[0]
        assert ab["score_gesamt"] == "5.0" and ab["begruendung"] == "Text A" and ab["branche"] == "X"
        assert ab["beschreibung_hash"] == "" and ab[bz.MARKER] == "True"
        assert df.iloc[1][bz.MARKER] == "False"
        # idempotent
        vorher = df.copy()
        bz.zusammenlegen(df, m, scores=True)
        pd.testing.assert_frame_equal(df, vorher)


# ---------------------------------------------------------------------------
# Idempotenz der Pipeline-Schritte auf einer Kopie der Daten
# ---------------------------------------------------------------------------

class TestIdempotenz:
    @pytest.fixture
    def kopie(self, tmp_path, monkeypatch) -> Path:
        ziel = tmp_path / "processed"
        shutil.copytree(P, ziel)
        monkeypatch.setattr(ub, "BFS_FILE", tmp_path / "fehlt.xlsx")
        monkeypatch.setattr(ul, "LSE_RAW", tmp_path / "fehlt_lse.xlsx")
        return ziel

    def _inhalte(self, pfad: Path) -> dict[str, str]:
        return {p.name: p.read_text(encoding="utf-8") for p in sorted(pfad.glob("*.csv"))}

    def test_update_from_bfs(self, kopie):
        vorher = self._inhalte(kopie)
        ub.main(["--data-dir", str(kopie)])
        assert self._inhalte(kopie) == vorher

    def test_update_loehne_offline(self, kopie):
        vorher = self._inhalte(kopie)
        ul.main(["--offline", "--data-dir", str(kopie)])
        assert self._inhalte(kopie) == vorher

    def test_berufe_zusammenlegen(self, kopie):
        vorher = self._inhalte(kopie)
        bz.main(["--data-dir", str(kopie)])
        assert self._inhalte(kopie) == vorher

    def test_mapping_fehlt_beruf(self, kopie):
        m = pd.read_csv(kopie / ub.MAPPING_CSV.name, dtype=str, keep_default_na=False)
        m.iloc[1:].to_csv(kopie / ub.MAPPING_CSV.name, index=False)
        with pytest.raises(SystemExit, match="ohne Eintrag"):
            ub.main(["--data-dir", str(kopie), "--dry-run"])

    def test_neue_berufe_ohne_kandidaten(self, kopie):
        vorher = self._inhalte(kopie)
        ub.main(["--data-dir", str(kopie), "--add-new"])
        assert self._inhalte(kopie) == vorher


# ---------------------------------------------------------------------------
# Neue Berufsgattungen (--add-new)
# ---------------------------------------------------------------------------

NEUE_CODES = {"3115", "3123", "3311", "3355", "3434", "4419", "7223", "9329"}


class TestNeueBerufe:
    def test_kandidaten_synthetisch(self, monkeypatch):
        se = _se([
            (4, "3123", "Poliere und Vorarbeiter", 28.8, 0.9),
            (4, "3000", "Techniker, onA", 64.5, 24.2),                            # Restgruppe
            (4, "9329", "Hilfsarbeiter, anderweitig nicht genannt", 38.9, 18.9),  # Ausnahme
            (4, "3119", "Fachkräfte, anderweitig nicht genannt", 18.9, 5.1),      # Restgruppe
            (4, "7112", "Maurer", 18.9, 0.4),                                     # schon erfasst
            (4, "6111", "Gemüseanbauer", 4.9, 1.0),                               # < 5000
            (4, "3434", "Küchenchefs", 5.0, 1.5),                                 # genau 5000
        ])
        m = _mapping([("Maurer/in", "7112", "gattung", "")])
        monkeypatch.setattr(ub, "RESTGRUPPEN_AUSNAHMEN", {"9329": "Begründung"})
        assert ub.neue_kandidaten(se, m)["code"].tolist() == ["3123", "3434", "9329"]

    def test_restgruppe(self):
        assert ub.ist_restgruppe("Führungskräfte, onA")
        assert ub.ist_restgruppe("Juristen, anderweitig nicht genannt")
        assert not ub.ist_restgruppe("Poliere und Vorarbeiter")

    def test_alle_grossen_gattungen_erfasst(self, mapping, se_csv):
        """Vollständigkeit: keine SE-Gattung >= 5000 (Blatt 2024) fehlt, ausser Restgruppen."""
        assert ub.neue_kandidaten(se_csv, mapping).empty
        g = se_csv[(se_csv["blatt"] == "2024") & (se_csv["ebene"] == 4)]
        fehlend = g[(g["total"] >= ub.NEUE_BERUFE_SCHWELLE) & ~g["code"].isin(set(mapping["isco_code"]))]
        assert fehlend["bezeichnung"].map(ub.ist_restgruppe).all(), fehlend["code"].tolist()
        assert not set(ub.RESTGRUPPEN_AUSNAHMEN) & set(fehlend["code"])

    def test_neue_eintraege_in_daten(self, mapping, se_csv):
        m = mapping.set_index("isco_code")
        scores = _csv("scores.csv").set_index("isco_code")
        g = se_csv[(se_csv["blatt"] == "2024") & (se_csv["ebene"] == 4)].set_index("code")
        lse = ul.lade_lse(schreiben=False)
        for code in NEUE_CODES:
            assert m.at[code, "beruf"] == g.at[code, "bezeichnung"]  # SE-Bezeichnung als Titel
            assert m.at[code, "ebene"] == ub.EBENE_GATTUNG
            r = scores.loc[code]
            assert float(r["beschaeftigte_1000"]) == pytest.approx(round(g.at[code, "total"], 1))
            assert r["branche"] == ub.branche_fuer_isco(code)
            assert int(r["lohn_median_chf"]) == ul.lse_basislohn(code, lse)[0]
            # nicht bewertet, bis die Neubewertung läuft
            assert r["beschreibung_hash"] == "" and r["score_gesamt"] == "" and r["score_ch"] == ""
        for code in ub.RESTGRUPPEN_AUSNAHMEN:
            assert "Restgruppe" in m.at[code, "begruendung"]

    def test_aufnahme_auf_kopie(self, tmp_path, monkeypatch):
        """Eintrag entfernen → --add-new nimmt ihn mit SE-Wert, Branche und Lohn wieder auf."""
        ziel = tmp_path / "processed"
        shutil.copytree(P, ziel)
        monkeypatch.setattr(ub, "BFS_FILE", tmp_path / "fehlt.xlsx")
        beruf = "Poliere und Vorarbeiter"
        for name in ub.CSV_DATEIEN + [ub.MAPPING_CSV.name]:
            df = pd.read_csv(ziel / name, dtype=str, keep_default_na=False)
            df[df["beruf"] != beruf].to_csv(ziel / name, index=False)
        ub.main(["--data-dir", str(ziel), "--add-new"])
        for name in ub.CSV_DATEIEN:
            df = pd.read_csv(ziel / name, dtype=str, keep_default_na=False).set_index("beruf")
            r = df.loc[beruf]
            assert r["isco_code"] == "3123" and r["beschaeftigte_1000"] == "28.8", name
            assert r["branche"] == "Bau" and r["lohn_quelle"] == "LSE2024_2d", name
            if "score_gesamt" in df.columns:
                assert r["score_gesamt"] == "" and r["beschreibung_hash"] == ""
                assert r["scores_gemittelt"] == "False"
        m = ub.lade_mapping(ziel / ub.MAPPING_CSV.name).set_index("beruf")
        assert m.at[beruf, "isco_code"] == "3123" and m.at[beruf, "ebene"] == ub.EBENE_GATTUNG
        # zweiter Lauf: nichts mehr zu ergänzen
        vorher = {p.name: p.read_text(encoding="utf-8") for p in ziel.glob("*.csv")}
        ub.main(["--data-dir", str(ziel), "--add-new"])
        assert {p.name: p.read_text(encoding="utf-8") for p in ziel.glob("*.csv")} == vorher
