"""Tests für update_loehne.py (LSE 2024 + Salarium-Profilmethode)."""

from pathlib import Path

import pandas as pd
import pytest

import update_loehne as ul

LSE = {"": 7024, "1": 10208, "13": 9594, "2": 9027, "22": 8000, "24": 9509,
       "6": 5670, "61": 5622, "9": 5120, "91": 4549, "52": 4970}


# ---------------------------------------------------------------------------
# LSE-Basis und Fallbacks
# ---------------------------------------------------------------------------

class TestLseBasislohn:
    def test_2_stellig_mal_12(self):
        assert ul.lse_basislohn("2221", LSE) == (8000 * 12, ul.QUELLE_2D)

    def test_praefix_ist_massgebend(self):
        assert ul.lse_basislohn("5223", LSE)[0] == ul.lse_basislohn("5230", LSE)[0] == 4970 * 12

    def test_fallback_1_stellig(self):
        """Gruppe 63 (Selbstversorgung) und 95 fehlen in der LSE → Hauptgruppe."""
        assert ul.lse_basislohn("6310", LSE) == (5670 * 12, ul.QUELLE_1D)
        assert ul.lse_basislohn("9510", LSE) == (5120 * 12, ul.QUELLE_1D)

    def test_fallback_total_fuer_armee(self):
        for code in ("0110", "0210", "0310"):
            assert ul.lse_basislohn(code, LSE) == (7024 * 12, ul.QUELLE_TOTAL)

    def test_code_mit_leerzeichen(self):
        assert ul.lse_basislohn(" 2221 ", LSE)[1] == ul.QUELLE_2D


class TestParseLseExcel:
    def test_total_1_und_2_stellig(self, tmp_path):
        rows = [
            ["Monatlicher Bruttolohn …", None, None, None],
            [None, None, None, " Total "],
            ["  ", "TOTAL", None, 7024],
            ["1", "Führungskräfte", None, 10208],
            ["11", "Geschäftsführer/innen", None, 10831],
            ["92", "Hilfskräfte Landwirtschaft", None, "[4919]"],
            [" Zeichenerklärung:", None, "« - » keine Daten", None],
        ]
        path = tmp_path / "t17.xlsx"
        pd.DataFrame(rows).to_excel(path, sheet_name="2024", header=False, index=False)
        tab = ul.parse_lse_excel(path)
        assert tab["isco_prefix"].tolist() == ["", "1", "11", "92"]
        assert tab["ebene"].tolist() == [0, 1, 2, 2]
        assert tab["median_monat"].tolist() == [7024, 10208, 10831, 4919]

    def test_versionierte_csv_vollstaendig(self):
        """Die committete LSE-CSV deckt alle 2-stelligen Gruppen der App ab."""
        lse = ul.lade_lse(raw=Path("/nicht/vorhanden.xlsx"), schreiben=False)
        assert lse[""] == 7024
        scores = pd.read_csv(ul.PROCESSED_PATH / "scores.csv", dtype={"isco_code": str})
        assert set(scores["isco_code"].str[:2]) <= set(lse)
        assert not {"63", "95", "01", "02", "03"} & set(lse)


# ---------------------------------------------------------------------------
# Salarium-Kalibrierung
# ---------------------------------------------------------------------------

class TestKalibrierung:
    def test_formel(self):
        # LSE 22 × 12 × S_beruf / S_referenz, auf 100 CHF gerundet
        assert ul.kalibrierter_lohn(8000, 9641, 7876) == round(8000 * 12 * 9641 / 7876, -2)

    def test_referenzprofil_ergibt_lse_wert(self):
        assert ul.kalibrierter_lohn(9509, 8500.0, 8500.0) == 9509 * 12 // 100 * 100

    def test_rundung_auf_100(self):
        assert ul.kalibrierter_lohn(8000, 1.0, 1.0) % 100 == 0

    def test_salarium_gruppe(self):
        assert [ul.salarium_gruppe(c) for c in ("1120", "1345", "1420", "2212", "2611")] == [10, 10, 10, 22, 26]


def _abfragen(werte: dict[tuple[int, int, str, int], float | None]) -> pd.DataFrame:
    return pd.DataFrame([
        {"salarium_gruppe": g, "noga": n, "ausbildung": a, "region": r, "median_monat": v}
        for (g, n, a, r), v in werte.items()
    ])


GEWICHTE = pd.DataFrame({"noga": [86, 86, 47, 47], "region": [1, 2, 1, 2], "vzae": [300, 100, 100, 100]})


class TestGewichteterWert:
    def test_vzae_gewichtet(self):
        abf = _abfragen({(22, 86, "UNI", 1): 10000, (22, 86, "UNI", 2): 6000})
        assert ul.gewichteter_salarium_wert(abf, GEWICHTE, 22, 86, "UNI") == pytest.approx(9000)

    def test_nicht_konsistente_region_wird_ignoriert(self):
        abf = _abfragen({(22, 86, "UNI", 1): 10000, (22, 86, "UNI", 2): None})
        assert ul.gewichteter_salarium_wert(abf, GEWICHTE, 22, 86, "UNI") == pytest.approx(10000)

    def test_ohne_wert(self):
        abf = _abfragen({(22, 86, "UNI", 1): None})
        assert ul.gewichteter_salarium_wert(abf, GEWICHTE, 22, 86, "UNI") is None

    def test_ohne_gewichte_ungewichtet(self):
        abf = _abfragen({(22, 90, "FH", 1): 5000, (22, 90, "FH", 2): 7000})
        assert ul.gewichteter_salarium_wert(abf, GEWICHTE, 22, 90, "FH") == pytest.approx(6000)


def _profile() -> pd.DataFrame:
    return pd.DataFrame({
        "isco_code": ["2212", "2262"], "beruf": ["Fachärzte", "Apotheker/in"],
        "salarium_gruppe": [22, 22], "noga": [86, 47], "ausbildung": ["UNI", "UNI"],
        "begruendung": ["", ""],
    })


ABFRAGEN = _abfragen({
    (22, 86, "UNI", 1): 12000, (22, 86, "UNI", 2): 12000,
    (22, 86, ul.STANDARD, 1): 8000, (22, 86, ul.STANDARD, 2): 8000,
    (22, 47, "UNI", 1): 10000, (22, 47, "UNI", 2): None,
})


class TestBerechneLoehne:
    def _df(self) -> pd.DataFrame:
        return pd.DataFrame({
            "beruf": ["Fachärzte", "Apotheker/in", "Physiotherapeut/in", "Kassierer/in", "Selbstversorger"],
            "isco_code": ["2212", "2262", "2264", "5223", "6310"],
        })

    def test_quellen_und_werte(self, capsys):
        res = ul.berechne_loehne(self._df(), LSE, _profile(), ABFRAGEN, GEWICHTE)
        assert res["lohn_quelle"].tolist() == [ul.QUELLE_SALARIUM, ul.QUELLE_SALARIUM,
                                               ul.QUELLE_2D, ul.QUELLE_2D, ul.QUELLE_1D]
        assert res["lohn_median_chf"].tolist() == [144000, 120000, 96000, 4970 * 12, 5670 * 12]
        # heterogene Gruppe ohne Profil → Warnung, LSE-Gruppenwert
        assert "Kein Salarium-Profil für 2264" in capsys.readouterr().out

    def test_ohne_salarium_daten_lse(self):
        res = ul.berechne_loehne(self._df(), LSE, _profile(), None, None)
        assert set(res["lohn_quelle"]) == {ul.QUELLE_2D, ul.QUELLE_1D}

    def test_profil_ohne_wert_faellt_zurueck(self, capsys):
        abf = ABFRAGEN[ABFRAGEN["noga"] != 47]
        res = ul.berechne_loehne(self._df(), LSE, _profile(), abf, GEWICHTE)
        assert res.loc[1, "lohn_quelle"] == ul.QUELLE_2D
        assert "Kein Salarium-Wert für 2262" in capsys.readouterr().out


class FakeClient:
    """Salarium-Ersatz ohne Netz: Region 7 nicht konsistent, Standardausbildung = HF (3)."""

    def __init__(self):
        self.bodies = []

    def konsistent(self, noga, region, gruppe):
        return region != 7

    def standard(self, noga, region, gruppe):
        return {"educationLevelCode": 3}

    def median(self, body):
        self.bodies.append(body)
        return 1000 * body["educationLevelCode"] + body["regionCode"], 4


class TestAbfragen:
    def test_benoetigte_abfragen_enthalten_referenz(self):
        specs = ul.benoetigte_abfragen(_profile())
        assert (22, 86, ul.STANDARD) in specs
        assert (22, 47, "UNI") in specs and len(specs) == len(set(specs))

    def test_abfragen_mit_normprofil(self):
        client = FakeClient()
        df = ul.abfragen_salarium([(22, 86, "UNI"), (22, 86, ul.STANDARD)], client)
        assert len(df) == 14
        assert df[df["region"] == 7]["median_monat"].isna().all()
        std = df[(df["ausbildung"] == ul.STANDARD) & (df["region"] == 1)].iloc[0]
        assert std["ausbildung_code"] == 3 and std["median_monat"] == 3001
        for body in client.bodies:
            for key, wert in ul.NORMPROFIL.items():
                assert body[key] == wert


# ---------------------------------------------------------------------------
# Versionierte Daten
# ---------------------------------------------------------------------------

class TestProfilTabelle:
    def test_alle_heterogenen_berufe_haben_profil(self):
        prof = ul.lade_profile()
        scores = pd.read_csv(ul.PROCESSED_PATH / "scores.csv", dtype={"isco_code": str})
        het = scores[scores["isco_code"].str[:2].isin(ul.HETEROGENE_GRUPPEN)]
        keys = set(zip(prof["isco_code"], prof["beruf"]))
        assert set(zip(het["isco_code"], het["beruf"])) == keys

    def test_referenz_noga_folgt_regel(self):
        """REFERENZ_NOGA = NOGA mit den meisten Beschäftigten unter den Profilen der Gruppe."""
        prof = ul.lade_profile()
        scores = pd.read_csv(ul.PROCESSED_PATH / "scores.csv", dtype={"isco_code": str})
        assert ul.referenz_noga_aus_profilen(prof, scores) == ul.REFERENZ_NOGA

    def test_ungueltige_ausbildung(self, tmp_path):
        p = _profile().assign(ausbildung=["UNI", "Doktorat"])
        p.to_csv(tmp_path / "p.csv", index=False)
        with pytest.raises(ValueError, match="Doktorat"):
            ul.lade_profile(tmp_path / "p.csv")

    def test_falsche_salarium_gruppe(self, tmp_path):
        p = _profile().assign(salarium_gruppe=[22, 10])
        p.to_csv(tmp_path / "p.csv", index=False)
        with pytest.raises(ValueError, match="salarium_gruppe"):
            ul.lade_profile(tmp_path / "p.csv")

    def test_salarium_werte_fuer_alle_profile(self):
        """Gespeicherte Abfragen decken alle Profile ab — ausser Führungskräfte der
        öffentlichen Verwaltung (NOGA 84), die Salarium (Privatsektor) nicht modelliert."""
        prof = ul.lade_profile()
        abf = pd.read_csv(ul.SALARIUM_CSV)
        gew = pd.read_csv(ul.STATENT_CSV)
        ohne = [s for s in ul.benoetigte_abfragen(prof) if not ul.gewichteter_salarium_wert(abf, gew, *s)]
        assert ohne == [(10, 84, ul.STANDARD)]
        assert set(abf["normprofil_id"]) == {ul.normprofil_id()}

    def test_scores_quellen(self):
        scores = pd.read_csv(ul.PROCESSED_PATH / "scores.csv", dtype={"isco_code": str})
        het = scores["isco_code"].str[:2].isin(ul.HETEROGENE_GRUPPEN) & (scores["isco_code"] != "1112")
        assert (scores.loc[het, "lohn_quelle"] == ul.QUELLE_SALARIUM).all()
        assert (scores.loc[~het, "lohn_quelle"] == ul.QUELLE_2D).all()
        assert scores["lohn_median_chf"].between(40_000, 200_000).all()

    def test_normprofil_id_aendert_sich_mit_profil(self):
        assert ul.normprofil_id() != ul.normprofil_id(dict(ul.NORMPROFIL, ageCode=30))


# ---------------------------------------------------------------------------
# main --offline
# ---------------------------------------------------------------------------

class TestMainOffline:
    def _setup(self, tmp_path: Path, monkeypatch) -> Path:
        monkeypatch.setattr(ul, "BASIS_DATEIEN", ["berufe_ch.csv"])
        monkeypatch.setattr(ul, "LSE_RAW", tmp_path / "fehlt.xlsx")
        pd.DataFrame({"isco_prefix": list(LSE), "ebene": [len(k) for k in LSE],
                      "bezeichnung": "", "median_monat": list(LSE.values())}
                     ).to_csv(tmp_path / ul.LSE_CSV.name, index=False)
        _profile().to_csv(tmp_path / ul.PROFILE_CSV.name, index=False)
        ABFRAGEN.to_csv(tmp_path / ul.SALARIUM_CSV.name, index=False)
        GEWICHTE.to_csv(tmp_path / ul.STATENT_CSV.name, index=False)
        pd.DataFrame({"beruf": ["Fachärzte", "Kassierer/in"], "isco_code": ["2212", "5223"],
                      "lohn_median_chf": ["90000", "48000"], "qualifikation": ["Tertiär", "Sekundär II"]}
                     ).to_csv(tmp_path / "berufe_ch.csv", index=False)
        pd.DataFrame({
            "beruf": ["Fachärzte", "Kassierer/in"], "isco_code": ["2212", "5223"],
            "branche": ["Gesundheit", "Detailhandel"], "lohn_median_chf": [90000, 48000],
            "qualifikation": ["Tertiär", "Sekundär II"], "score_gesamt": [4.2, 6.4],
            "score_digital": [5.0, 3.0], "begruendung": ["Text A", "Text B"],
            "adaptabilitaet": [7.0, None], "delta_branche": [-0.3, 0.2],
            "lohnklasse": ["60k–100k CHF", "< 60k CHF"], "delta_lohn": [0.0, -0.2],
            "score_ch": [3.9, 6.4], "zeitrahmen_roh": ["5-10 Jahre", "3-5 Jahre"],
        }).to_csv(tmp_path / "scores.csv", index=False)
        return tmp_path

    def test_offline_lauf(self, tmp_path, monkeypatch):
        pfad = self._setup(tmp_path, monkeypatch)
        alt = pd.read_csv(pfad / "scores.csv", dtype=str, keep_default_na=False)
        ul.main(["--offline", "--pfad", str(pfad)])

        basis = pd.read_csv(pfad / "berufe_ch.csv", dtype=str, keep_default_na=False)
        assert basis.columns.tolist()[:4] == ["beruf", "isco_code", "lohn_median_chf", "lohn_quelle"]
        assert basis["lohn_median_chf"].tolist() == ["144000", str(4970 * 12)]

        neu = pd.read_csv(pfad / "scores.csv", dtype=str, keep_default_na=False)
        for spalte in ["score_gesamt", "score_digital", "begruendung", "zeitrahmen_roh", "branche"]:
            assert neu[spalte].equals(alt[spalte])
        # 144'000 → 100k–150k; Verkauf 4970 × 12 = 59'640 → < 60k
        assert neu["lohnklasse"].tolist() == ["100k–150k CHF", "< 60k CHF"]
        assert neu["delta_lohn"].astype(float).tolist() == [0.2, -0.2]
        assert neu["score_ch"].astype(float).tolist() == pytest.approx([4.1, 6.4])
        assert neu.loc[1, "score_ch"] == alt.loc[1, "score_ch"]  # gleicher Wert → Text unverändert
        assert neu["adaptabilitaet"].ne("").all()  # fehlende Werte werden berechnet

    def test_dry_run_schreibt_nichts(self, tmp_path, monkeypatch):
        pfad = self._setup(tmp_path, monkeypatch)
        vorher = (pfad / "scores.csv").read_text(encoding="utf-8")
        ul.main(["--offline", "--dry-run", "--pfad", str(pfad)])
        assert (pfad / "scores.csv").read_text(encoding="utf-8") == vorher
