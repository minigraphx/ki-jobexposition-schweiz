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
        assert tab["level"].tolist() == [0, 1, 2, 2]
        assert tab["median_monthly"].tolist() == [7024, 10208, 10831, 4919]

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
        # LSE_g × 12 × S_j / S̄_g, auf 100 CHF gerundet
        assert ul.kalibrierter_lohn(8000, 9641, 7876) == round(8000 * 12 * 9641 / 7876, -2)

    def test_mittelwert_profil_ergibt_lse_wert(self):
        assert ul.kalibrierter_lohn(9509, 8500.0, 8500.0) == 9509 * 12 // 100 * 100

    def test_rundung_auf_100(self):
        assert ul.kalibrierter_lohn(8000, 1.0, 1.0) % 100 == 0

    def test_gruppen_mittel_gewichtet(self):
        assert ul.gruppen_mittel([12000, 10000], [30, 10]) == pytest.approx(11500)
        assert ul.gruppen_mittel([12000, 10000], [0, 0]) == pytest.approx(11000)

    @pytest.mark.parametrize("s, w", [
        ([9400, 10039, 8500, 9000], [32, 20, 8, 28]),
        ([7000, 12000], [130, 36]),
        ([5000], [1]),
    ])
    def test_normierung_gewichtetes_mittel_gleich_lse(self, s, w):
        """Σ w·lohn / Σ w = LSE_g × 12 (ungerundet exakt, gerundet auf ±50 CHF)."""
        mittel = ul.gruppen_mittel(s, w)
        exakt = [9509 * 12 * x / mittel for x in s]
        assert sum(a * b for a, b in zip(exakt, w)) / sum(w) == pytest.approx(9509 * 12)
        gerundet = [ul.kalibrierter_lohn(9509, x, mittel) for x in s]
        assert abs(sum(a * b for a, b in zip(gerundet, w)) / sum(w) - 9509 * 12) <= 50

    def test_salarium_gruppe(self):
        assert [ul.salarium_gruppe(c) for c in ("1120", "1345", "1420", "2212", "2611")] == [10, 10, 10, 22, 26]


def _abfragen(werte: dict[tuple[int, int, str, int], float | None]) -> pd.DataFrame:
    return pd.DataFrame([
        {"salarium_group": g, "noga": n, "education": a, "region": r, "median_monthly": v}
        for (g, n, a, r), v in werte.items()
    ])


GEWICHTE = pd.DataFrame({"noga": [86, 86, 47, 47], "region": [1, 2, 1, 2], "fte": [300, 100, 100, 100]})


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
        "isco_code": ["2212", "2262"], "occupation": ["Fachärzte", "Apotheker/in"],
        "salarium_group": [22, 22], "noga": [86, 47], "education": ["UNI", "UNI"],
        "rationale": ["", ""],
    })


ABFRAGEN = _abfragen({
    (22, 86, "UNI", 1): 12000, (22, 86, "UNI", 2): 12000,
    (22, 47, "UNI", 1): 10000, (22, 47, "UNI", 2): None,
})


class TestBerechneLoehne:
    def _df(self) -> pd.DataFrame:
        return pd.DataFrame({
            "occupation": ["Fachärzte", "Apotheker/in", "Physiotherapeut/in", "Kassierer/in", "Selbstversorger"],
            "isco_code": ["2212", "2262", "2264", "5223", "6310"],
            "employed_k": [30.0, 10.0, 5.0, 20.0, 1.0],
        })

    def test_quellen_und_werte(self, capsys):
        res = ul.berechne_loehne(self._df(), LSE, _profile(), ABFRAGEN, GEWICHTE)
        assert res["wage_source"].tolist() == [ul.QUELLE_SALARIUM, ul.QUELLE_SALARIUM,
                                               ul.QUELLE_2D, ul.QUELLE_2D, ul.QUELLE_1D]
        # S̄_22 = (30·12000 + 10·10000) / 40 = 11500
        assert res["wage_median_chf"].tolist() == [round(96000 * 12000 / 11500, -2),
                                                   round(96000 * 10000 / 11500, -2),
                                                   96000, 4970 * 12, 5670 * 12]
        # heterogene Gruppe ohne Profil → Warnung, LSE-Gruppenwert
        assert "Kein Salarium-Profil für 2264" in capsys.readouterr().out

    def test_gruppenmittel_gleich_lse(self):
        df = self._df()
        res = ul.berechne_loehne(df, LSE, _profile(), ABFRAGEN, GEWICHTE)
        sal = res["wage_source"] == ul.QUELLE_SALARIUM
        w = df.loc[sal, "employed_k"]
        assert (res.loc[sal, "wage_median_chf"] * w).sum() / w.sum() == pytest.approx(96000, abs=50)

    def test_externe_gewichte_haben_vorrang(self):
        gew = {("2212", "Fachärzte"): 10.0, ("2262", "Apotheker/in"): 10.0}
        res = ul.berechne_loehne(self._df(), LSE, _profile(), ABFRAGEN, GEWICHTE, gew)
        assert res["wage_median_chf"].tolist()[:2] == [round(96000 * 12000 / 11000, -2),
                                                       round(96000 * 10000 / 11000, -2)]

    def test_einziger_profilberuf_erhaelt_lse(self):
        df = self._df().iloc[[0]]
        res = ul.berechne_loehne(df, LSE, _profile(), ABFRAGEN, GEWICHTE)
        assert res["wage_median_chf"].tolist() == [96000]

    def test_ohne_salarium_daten_lse(self):
        res = ul.berechne_loehne(self._df(), LSE, _profile(), None, None)
        assert set(res["wage_source"]) == {ul.QUELLE_2D, ul.QUELLE_1D}

    def test_profil_ohne_wert_faellt_zurueck_und_zaehlt_nicht(self, capsys):
        """Ohne Salarium-Wert: LSE_g × 12; die übrigen Berufe werden ohne ihn normiert."""
        abf = ABFRAGEN[ABFRAGEN["noga"] != 47]
        res = ul.berechne_loehne(self._df(), LSE, _profile(), abf, GEWICHTE)
        assert res.loc[1, "wage_source"] == ul.QUELLE_2D
        assert res.loc[1, "wage_median_chf"] == 96000
        assert res.loc[0, "wage_median_chf"] == 96000  # einziger Wert in S̄_22
        assert "Kein Salarium-Wert für 2262" in capsys.readouterr().out


def _verhaeltnisse(zeilen: list[dict]) -> pd.DataFrame:
    basis = {"factor_to_lse_group": None, "band_low": None, "band_high": None,
             "wage_uncertain": False, "source": "Testquelle", "method": "", "note": ""}
    tab = pd.DataFrame([dict(basis, **z) for z in zeilen])
    for spalte in ["factor_to_lse_group", "band_low", "band_high"]:
        tab[spalte] = tab[spalte].astype(float)
    return tab


class TestVerhaeltnisse:
    """Verhältnis-Overrides nach der Salarium-Kalibrierung (lohn_verhaeltnisse.csv)."""

    def _df(self) -> pd.DataFrame:
        return TestBerechneLoehne()._df()

    def test_formel(self):
        # Pflege: 0.987 × 8000 × 12 = 94'752 → 94'800
        assert ul.verhaeltnis_lohn(8000, 0.987) == 94800
        assert ul.verhaeltnis_lohn(8000, 1.0) == 96000

    def test_override_und_normierung_ohne_override(self):
        """2212 per Faktor; 2262 wird allein normiert (S̄_22 ohne 2212) → LSE_22 × 12."""
        verh = _verhaeltnisse([{"isco_code": "2212", "occupation": "Fachärzte", "factor_to_lse_group": 1.6}])
        res = ul.berechne_loehne(self._df(), LSE, _profile(), ABFRAGEN, GEWICHTE, verhaeltnisse=verh)
        assert res.loc[0, "wage_source"] == ul.QUELLE_VERHAELTNIS
        assert res.loc[0, "wage_median_chf"] == 153600
        assert res.loc[1, "wage_source"] == ul.QUELLE_SALARIUM
        assert res.loc[1, "wage_median_chf"] == 96000  # ohne Override wäre es 83'500
        assert not res["wage_uncertain"].any()

    def test_gewichtetes_mittel_der_uebrigen_gleich_lse(self):
        df = pd.DataFrame({"occupation": ["A", "B", "C"], "isco_code": ["2211", "2264", "2262"],
                           "employed_k": [10.0, 30.0, 10.0]})
        prof = pd.DataFrame({"isco_code": ["2211", "2264", "2262"], "occupation": ["A", "B", "C"],
                             "salarium_group": [22] * 3, "noga": [86, 86, 47],
                             "education": ["UNI", "FH", "UNI"], "rationale": [""] * 3})
        abf = _abfragen({(22, 86, "UNI", 1): 12000, (22, 86, "FH", 1): 9000, (22, 47, "UNI", 1): 10000})
        verh = _verhaeltnisse([{"isco_code": "2211", "occupation": "A", "factor_to_lse_group": 1.4}])
        res = ul.berechne_loehne(df, LSE, prof, abf, GEWICHTE, verhaeltnisse=verh)
        assert res.loc[0, "wage_median_chf"] == 134400
        rest = res.loc[[1, 2], "wage_median_chf"]
        w = df.loc[[1, 2], "employed_k"]
        assert (rest * w).sum() / w.sum() == pytest.approx(96000, abs=50)
        # S̄ = (30·9000 + 10·10000) / 40 = 9250
        assert rest.tolist() == [round(96000 * 9000 / 9250, -2), round(96000 * 10000 / 9250, -2)]

    def test_ohne_tabelle_wie_bisher(self):
        ohne = ul.berechne_loehne(self._df(), LSE, _profile(), ABFRAGEN, GEWICHTE)
        leer_tab = _verhaeltnisse([{"isco_code": "x", "occupation": "x"}]).iloc[0:0]
        leer = ul.berechne_loehne(self._df(), LSE, _profile(), ABFRAGEN, GEWICHTE, verhaeltnisse=leer_tab)
        assert ohne.equals(leer)
        assert ohne["wage_uncertain"].tolist() == [False] * 5

    def test_unsicher_ohne_faktor_behaelt_salarium(self):
        verh = _verhaeltnisse([{"isco_code": "2262", "occupation": "Apotheker/in", "wage_uncertain": True}])
        ohne = ul.berechne_loehne(self._df(), LSE, _profile(), ABFRAGEN, GEWICHTE)
        res = ul.berechne_loehne(self._df(), LSE, _profile(), ABFRAGEN, GEWICHTE, verhaeltnisse=verh)
        assert res[["wage_median_chf", "wage_source"]].equals(ohne[["wage_median_chf", "wage_source"]])
        assert res["wage_uncertain"].tolist() == [False, True, False, False, False]

    def test_override_ohne_2_stelligen_lse_wird_ignoriert(self, capsys):
        verh = _verhaeltnisse([{"isco_code": "6310", "occupation": "Selbstversorger", "factor_to_lse_group": 2.0}])
        res = ul.berechne_loehne(self._df(), LSE, _profile(), ABFRAGEN, GEWICHTE, verhaeltnisse=verh)
        assert res.loc[4, "wage_median_chf"] == 5670 * 12
        assert res.loc[4, "wage_source"] == ul.QUELLE_1D
        assert "Verhältnis für 6310" in capsys.readouterr().out

    def test_override_ohne_salarium_profil(self):
        """Override gilt auch für Berufe ohne Salarium-Wert (hier 2264 ohne Profil)."""
        verh = _verhaeltnisse([{"isco_code": "2264", "occupation": "Physiotherapeut/in", "factor_to_lse_group": 0.95}])
        res = ul.berechne_loehne(self._df(), LSE, _profile(), ABFRAGEN, GEWICHTE, verhaeltnisse=verh)
        assert res.loc[2, "wage_median_chf"] == 91200
        assert res.loc[2, "wage_source"] == ul.QUELLE_VERHAELTNIS

    def _csv(self, tmp_path, **werte) -> Path:
        zeile = dict(isco_code="2212", occupation="Fachärzte", factor_to_lse_group="1.6", band_low="1.3",
                     band_high="1.9", wage_uncertain="False", source="Q", method="M", note="")
        zeile.update(werte)
        path = tmp_path / "v.csv"
        pd.DataFrame([zeile]).to_csv(path, index=False)
        return path

    def test_laden(self, tmp_path):
        tab = ul.lade_verhaeltnisse(self._csv(tmp_path))
        assert tab.loc[0, "factor_to_lse_group"] == 1.6
        assert tab["wage_uncertain"].tolist() == [False]
        tab = ul.lade_verhaeltnisse(self._csv(tmp_path, factor_to_lse_group="", band_low="",
                                              band_high="", wage_uncertain="True"))
        assert tab["factor_to_lse_group"].isna().all() and tab["wage_uncertain"].tolist() == [True]

    def test_fehlende_datei_leer(self, tmp_path):
        assert ul.lade_verhaeltnisse(tmp_path / "fehlt.csv").empty

    @pytest.mark.parametrize("werte, meldung", [
        ({"band_low": "1.7"}, "Band"),
        ({"band_high": "1.5"}, "Band"),
        ({"factor_to_lse_group": "", "wage_uncertain": "True"}, "Band"),
        ({"factor_to_lse_group": "-1", "band_low": "", "band_high": ""}, "> 0"),
        ({"source": ""}, "Quelle"),
    ])
    def test_validierung(self, tmp_path, werte, meldung):
        with pytest.raises(ValueError, match=meldung):
            ul.lade_verhaeltnisse(self._csv(tmp_path, **werte))


class TestVerhaeltnisTabelle:
    """Versionierte data/processed/lohn_verhaeltnisse.csv und ihre Wirkung in den Daten."""

    def test_eintraege_existieren_und_gruppe_22(self):
        verh = ul.lade_verhaeltnisse()
        scores = pd.read_csv(ul.PROCESSED_PATH / "scores.csv", dtype={"isco_code": str})
        assert set(zip(verh["isco_code"], verh["occupation"])) <= set(zip(scores["isco_code"], scores["occupation"]))
        assert set(verh["isco_code"].str[:2]) == {"22"}
        assert set(verh.loc[verh["factor_to_lse_group"].notna(), "isco_code"]) == {"2211", "2212", "2221"}
        assert set(verh.loc[verh["wage_uncertain"], "isco_code"]) == {"2261", "2262"}

    def test_loehne_in_daten(self):
        lse = ul.lade_lse(raw=Path("/nicht/vorhanden.xlsx"), schreiben=False)
        verh = ul.lade_verhaeltnisse().dropna(subset=["factor_to_lse_group"])
        scores = pd.read_csv(ul.PROCESSED_PATH / "scores.csv", dtype={"isco_code": str}).set_index(
            ["isco_code", "occupation"])
        for r in verh.itertuples():
            assert scores.loc[(r.isco_code, r.occupation), "wage_median_chf"] == ul.verhaeltnis_lohn(
                lse[r.isco_code[:2]], r.factor_to_lse_group)
            assert scores.loc[(r.isco_code, r.occupation), "wage_source"] == ul.QUELLE_VERHAELTNIS

    def test_pflege_anker_und_aerzte(self):
        """Pflege = 0.987 × Gruppenmedian; Ärzte (2211/2212) gewichtet ≈ 1.6 × Pflege."""
        verh = ul.lade_verhaeltnisse().set_index("isco_code")
        assert verh.loc["2221", "factor_to_lse_group"] == pytest.approx(7429 / 7526, abs=5e-4)
        basis = pd.read_csv(ul.PROCESSED_PATH / "berufe_ch.csv", dtype={"isco_code": str}).set_index("isco_code")
        w = basis.loc[["2211", "2212"], "employed_k"]
        f = verh.loc[["2211", "2212"], "factor_to_lse_group"]
        assert (w * f).sum() / w.sum() / verh.loc["2221", "factor_to_lse_group"] == pytest.approx(1.6, abs=0.005)
        assert f["2211"] / f["2212"] == pytest.approx(0.85, abs=0.002)

    def test_lohn_unsicher_spalte_in_allen_csvs(self):
        verh = ul.lade_verhaeltnisse()
        unsicher = set(zip(verh.loc[verh["wage_uncertain"], "isco_code"], verh.loc[verh["wage_uncertain"], "occupation"]))
        for name in ul.BASIS_DATEIEN + [ul.SCORES_DATEI]:
            d = pd.read_csv(ul.PROCESSED_PATH / name, dtype={"isco_code": str})
            assert d["wage_uncertain"].dtype == bool, name
            pos = d.columns.get_loc("wage_source")
            assert d.columns[pos + 1] == "wage_uncertain", name
            assert set(zip(d.loc[d["wage_uncertain"], "isco_code"], d.loc[d["wage_uncertain"], "occupation"])) == unsicher


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
    def test_benoetigte_abfragen(self):
        assert ul.benoetigte_abfragen(_profile()) == [(22, 47, "UNI"), (22, 86, "UNI")]

    def test_abfragen_mit_normprofil(self):
        client = FakeClient()
        df = ul.abfragen_salarium([(22, 86, "UNI"), (22, 86, ul.STANDARD)], client)
        assert len(df) == 14
        assert df[df["region"] == 7]["median_monthly"].isna().all()
        std = df[(df["education"] == ul.STANDARD) & (df["region"] == 1)].iloc[0]
        assert std["education_code"] == 3 and std["median_monthly"] == 3001
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
        keys = set(zip(prof["isco_code"], prof["occupation"]))
        assert set(zip(het["isco_code"], het["occupation"])) == keys

    def test_gruppenmittel_in_daten_gleich_lse(self):
        """In scores.csv: beschäftigungsgewichtetes Mittel (Gewichte berufe_ch.csv) der
        Salarium-Berufe je LSE-Gruppe = LSE-Gruppenmedian × 12."""
        lse = ul.lade_lse(raw=Path("/nicht/vorhanden.xlsx"), schreiben=False)
        scores = pd.read_csv(ul.PROCESSED_PATH / "scores.csv", dtype={"isco_code": str})
        basis = pd.read_csv(ul.PROCESSED_PATH / "berufe_ch.csv", dtype={"isco_code": str})
        m = scores.drop(columns="employed_k").merge(
            basis[["isco_code", "occupation", "employed_k"]], on=["isco_code", "occupation"])
        m = m[m["wage_source"] == ul.QUELLE_SALARIUM]
        m["g"] = m["isco_code"].str[:2]
        assert set(m["g"]) == set(ul.HETEROGENE_GRUPPEN)
        for g, d in m.groupby("g"):
            mittel = (d["wage_median_chf"] * d["employed_k"]).sum() / d["employed_k"].sum()
            assert mittel == pytest.approx(lse[g] * 12, abs=50), g

    def test_alle_csvs_haben_gleiche_loehne(self):
        ref = pd.read_csv(ul.PROCESSED_PATH / "berufe_ch.csv", dtype={"isco_code": str})
        ref = ref.set_index(["isco_code", "occupation"])["wage_median_chf"].sort_index()
        for name in ul.BASIS_DATEIEN[1:] + [ul.SCORES_DATEI]:
            d = pd.read_csv(ul.PROCESSED_PATH / name, dtype={"isco_code": str})
            assert d.set_index(["isco_code", "occupation"])["wage_median_chf"].sort_index().equals(ref), name

    def test_ungueltige_ausbildung(self, tmp_path):
        p = _profile().assign(education=["UNI", "Doktorat"])
        p.to_csv(tmp_path / "p.csv", index=False)
        with pytest.raises(ValueError, match="Doktorat"):
            ul.lade_profile(tmp_path / "p.csv")

    def test_falsche_salarium_gruppe(self, tmp_path):
        p = _profile().assign(salarium_group=[22, 10])
        p.to_csv(tmp_path / "p.csv", index=False)
        with pytest.raises(ValueError, match="salarium_group"):
            ul.lade_profile(tmp_path / "p.csv")

    def test_salarium_werte_fuer_alle_profile(self):
        """Gespeicherte Abfragen decken alle Profile ab — ausser Führungskräfte der
        öffentlichen Verwaltung (NOGA 84), die Salarium (Privatsektor) nicht modelliert."""
        prof = ul.lade_profile()
        abf = pd.read_csv(ul.SALARIUM_CSV)
        gew = pd.read_csv(ul.STATENT_CSV)
        ohne = [s for s in ul.benoetigte_abfragen(prof) if not ul.gewichteter_salarium_wert(abf, gew, *s)]
        assert ohne == [(10, 84, ul.STANDARD)]
        assert set(abf["norm_profile_id"]) == {ul.normprofil_id()}

    def test_scores_quellen(self):
        scores = pd.read_csv(ul.PROCESSED_PATH / "scores.csv", dtype={"isco_code": str})
        verh = ul.lade_verhaeltnisse()
        override = set(zip(verh.loc[verh["factor_to_lse_group"].notna(), "isco_code"],
                           verh.loc[verh["factor_to_lse_group"].notna(), "occupation"]))
        ist_ov = pd.Series([k in override for k in zip(scores["isco_code"], scores["occupation"])],
                           index=scores.index)
        het = scores["isco_code"].str[:2].isin(ul.HETEROGENE_GRUPPEN) & (scores["isco_code"] != "1112")
        assert (scores.loc[ist_ov, "wage_source"] == ul.QUELLE_VERHAELTNIS).all()
        assert (scores.loc[het & ~ist_ov, "wage_source"] == ul.QUELLE_SALARIUM).all()
        assert (scores.loc[~het, "wage_source"] == ul.QUELLE_2D).all()
        assert scores["wage_median_chf"].between(40_000, 200_000).all()

    def test_normprofil_id_aendert_sich_mit_profil(self):
        assert ul.normprofil_id() != ul.normprofil_id(dict(ul.NORMPROFIL, ageCode=30))


# ---------------------------------------------------------------------------
# main --offline
# ---------------------------------------------------------------------------

class TestMainOffline:
    def _setup(self, tmp_path: Path, monkeypatch) -> Path:
        monkeypatch.setattr(ul, "BASIS_DATEIEN", ["berufe_ch.csv"])
        monkeypatch.setattr(ul, "LSE_RAW", tmp_path / "fehlt.xlsx")
        pd.DataFrame({"isco_prefix": list(LSE), "level": [len(k) for k in LSE],
                      "label": "", "median_monthly": list(LSE.values())}
                     ).to_csv(tmp_path / ul.LSE_CSV.name, index=False)
        _profile().to_csv(tmp_path / ul.PROFILE_CSV.name, index=False)
        ABFRAGEN.to_csv(tmp_path / ul.SALARIUM_CSV.name, index=False)
        GEWICHTE.to_csv(tmp_path / ul.STATENT_CSV.name, index=False)
        # Gewichte für S̄_g kommen aus berufe_ch.csv (scores.csv hat absichtlich andere Werte)
        pd.DataFrame({"occupation": ["Fachärzte", "Apotheker/in", "Kassierer/in"],
                      "isco_code": ["2212", "2262", "5223"], "employed_k": ["30.0", "10.0", "20.0"],
                      "wage_median_chf": ["90000", "110000", "48000"],
                      "qualification": ["Tertiär", "Tertiär", "Sekundär II"]}
                     ).to_csv(tmp_path / "berufe_ch.csv", index=False)
        pd.DataFrame({
            "occupation": ["Fachärzte", "Apotheker/in", "Kassierer/in"], "isco_code": ["2212", "2262", "5223"],
            "employed_k": [1.0, 100.0, 20.0],
            "sector": ["Gesundheit", "Gesundheit", "Detailhandel"], "wage_median_chf": [90000, 110000, 48000],
            "qualification": ["Tertiär", "Tertiär", "Sekundär II"], "exposure": [2.5, 5.0, 0.1],
            "rationale": ["Text A", "Text B", "Text C"], "timeframe_raw": ["5-10 Jahre", "3-5 Jahre", "3-5 Jahre"],
            "adaptability": [7.0, 6.5, None], "legacy_score": [3.9, 5.3, 6.4],
        }).to_csv(tmp_path / "scores.csv", index=False)
        return tmp_path

    def test_offline_lauf(self, tmp_path, monkeypatch):
        pfad = self._setup(tmp_path, monkeypatch)
        alt = pd.read_csv(pfad / "scores.csv", dtype=str, keep_default_na=False)
        ul.main(["--offline", "--data-dir", str(pfad)])

        # S̄_22 = (30·12000 + 10·10000) / 40 = 11500
        erwartet = [str(int(round(96000 * 12000 / 11500, -2))), str(int(round(96000 * 10000 / 11500, -2))),
                    str(4970 * 12)]
        basis = pd.read_csv(pfad / "berufe_ch.csv", dtype=str, keep_default_na=False)
        assert basis.columns.tolist()[:5] == ["occupation", "isco_code", "employed_k",
                                              "wage_median_chf", "wage_source"]
        assert basis["wage_median_chf"].tolist() == erwartet

        neu = pd.read_csv(pfad / "scores.csv", dtype=str, keep_default_na=False)
        assert neu["wage_median_chf"].tolist() == erwartet  # gleiche Gewichte wie berufe_ch.csv
        for spalte in ["exposure", "rationale", "timeframe_raw", "sector", "legacy_score"]:
            assert neu[spalte].equals(alt[spalte])   # kein Lohnzuschlag auf den Score
        assert [c for c in neu.columns if c not in ("wage_source", "wage_uncertain")] == list(alt.columns)
        # adaptability = (Qualifikation + Lohnpunkte + Mobilität) × 10/8 (Gesundheit 0.5, Detailhandel 0.4)
        # (4 + 1.506 + 0.5) → 7.5; (4 + 1.005 + 0.5) → 6.9; (3 + 0.289 + 0.4) → 4.6
        assert neu["adaptability"].tolist() == ["7.5", "6.9", "4.6"]
        # ohne lohn_verhaeltnisse.csv: keine Overrides, Spalte wage_uncertain nach wage_source
        assert basis.columns.tolist()[5] == "wage_uncertain"
        assert basis["wage_uncertain"].tolist() == neu["wage_uncertain"].tolist() == ["False"] * 3

    def test_offline_mit_verhaeltnis(self, tmp_path, monkeypatch):
        pfad = self._setup(tmp_path, monkeypatch)
        pd.DataFrame([
            {"isco_code": "2212", "occupation": "Fachärzte", "factor_to_lse_group": 1.6, "band_low": 1.3,
             "band_high": 1.9, "wage_uncertain": False, "source": "Q", "method": "M", "note": ""},
            {"isco_code": "2262", "occupation": "Apotheker/in", "factor_to_lse_group": None, "band_low": None,
             "band_high": None, "wage_uncertain": True, "source": "Q", "method": "M", "note": ""},
        ]).to_csv(pfad / ul.VERHAELTNIS_CSV.name, index=False)
        ul.main(["--offline", "--data-dir", str(pfad)])
        neu = pd.read_csv(pfad / "scores.csv", dtype=str, keep_default_na=False)
        # 2212 = 1.6 × 96'000; 2262 allein normiert → 96'000 (unsicher markiert)
        assert neu["wage_median_chf"].tolist() == ["153600", "96000", str(4970 * 12)]
        assert neu["wage_source"].tolist() == [ul.QUELLE_VERHAELTNIS, ul.QUELLE_SALARIUM, ul.QUELLE_2D]
        assert neu["wage_uncertain"].tolist() == ["False", "True", "False"]
        assert neu["adaptability"].tolist()[0] == "9.4"   # (4 + 3 (≥ 150k) + 0.5) × 10/8

    def test_dry_run_schreibt_nichts(self, tmp_path, monkeypatch):
        pfad = self._setup(tmp_path, monkeypatch)
        vorher = (pfad / "scores.csv").read_text(encoding="utf-8")
        ul.main(["--offline", "--dry-run", "--data-dir", str(pfad)])
        assert (pfad / "scores.csv").read_text(encoding="utf-8") == vorher
