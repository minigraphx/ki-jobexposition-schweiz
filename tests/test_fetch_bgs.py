"""Tests für fetch_bgs.py (BFS Grenzgängerstatistik DF_GGS_4 + STATENT-Nenner)."""

import io
from pathlib import Path

import pandas as pd
import pytest

import fetch_bgs
from fetch_bgs import (
    NOGA_OHNE_BRANCHE,
    NOGA_ZU_BRANCHE,
    aggregiere_nach_branche,
    compute_grenzgaenger_anteil,
    parse_bgs_sdmx_csv,
    parse_statent_pxweb,
    waehle_periode,
)

PROCESSED = Path(__file__).parent.parent / "data" / "processed"

ALLE_BRANCHEN = {
    "Bau", "Industrie", "Gastgewerbe", "Transport", "Gesundheit",
    "Detailhandel", "ICT", "Finanzen", "Versicherungen", "Recht",
    "Bildung", "Verwaltung", "Öff. Verwaltung", "Soziales",
    "Landwirtschaft", "Umwelt", "Sicherheit", "Dienstleistungen",
    "Immobilien", "Medien", "Beratung",
}

# Kleiner Ausschnitt im Format des stats.swiss-SDMX-CSV-Exports (Codes ohne Labels)
SDMX_FIXTURE = """DATAFLOW,NOGA,AUFZW,FREQ,TIME_PERIOD,OBS_VALUE,OBS_STATUS,DECIMALS
CH1.GGS:DF_GGS_4(1.0.0),_T,_T,Q,2025-Q4,1000.0,P,1
CH1.GGS:DF_GGS_4(1.0.0),C,_T,Q,2025-Q4,300.0,P,1
CH1.GGS:DF_GGS_4(1.0.0),2,_T,Q,2025-Q4,300.0,P,1
CH1.GGS:DF_GGS_4(1.0.0),-9,_T,Q,2025-Q4,0,P,1
CH1.GGS:DF_GGS_4(1.0.0),21,1,Q,2025-Q4,99.0,P,1
CH1.GGS:DF_GGS_4(1.0.0),21,_T,Q,2025-Q1,80.0,P,1
CH1.GGS:DF_GGS_4(1.0.0),21,_T,Q,2025-Q2,90.0,P,1
CH1.GGS:DF_GGS_4(1.0.0),21,_T,Q,2025-Q3,110.0,P,1
CH1.GGS:DF_GGS_4(1.0.0),21,_T,Q,2025-Q4,120.0,P,1
CH1.GGS:DF_GGS_4(1.0.0),21,_T,Q,2026-Q1,130.0,P,1
CH1.GGS:DF_GGS_4(1.0.0),69,_T,Q,2025-Q1,10.0,P,1
CH1.GGS:DF_GGS_4(1.0.0),69,_T,Q,2025-Q2,10.0,P,1
CH1.GGS:DF_GGS_4(1.0.0),69,_T,Q,2025-Q3,10.0,P,1
CH1.GGS:DF_GGS_4(1.0.0),69,_T,Q,2025-Q4,10.0,P,1
CH1.GGS:DF_GGS_4(1.0.0),69,_T,Q,2026-Q1,14.0,P,1
CH1.GGS:DF_GGS_4(1.0.0),97,_T,Q,2025-Q1,5.0,P,1
CH1.GGS:DF_GGS_4(1.0.0),97,_T,Q,2025-Q2,5.0,P,1
CH1.GGS:DF_GGS_4(1.0.0),97,_T,Q,2025-Q3,5.0,P,1
CH1.GGS:DF_GGS_4(1.0.0),97,_T,Q,2025-Q4,5.0,P,1
CH1.GGS:DF_GGS_4(1.0.0),97,_T,Q,2026-Q1,5.0,P,1
"""


@pytest.fixture
def bgs() -> pd.DataFrame:
    return parse_bgs_sdmx_csv(io.StringIO(SDMX_FIXTURE))


@pytest.fixture
def statent() -> pd.DataFrame:
    """Nenner: jede gemappte NOGA-Abteilung mit 1000 Beschäftigten (älteres Jahr 2023 zum Ignorieren)."""
    zeilen = [{"year": 2024, "noga": n, "employed": 1000, "fte": 800} for n in NOGA_ZU_BRANCHE]
    zeilen.append({"year": 2023, "noga": "21", "employed": 1, "fte": 1})
    return pd.DataFrame(zeilen)


class TestParsing:
    def test_nur_abteilungen_und_total_status(self, bgs):
        assert set(bgs["noga"]) == {"21", "69", "97"}
        assert list(bgs.columns) == ["noga", "period", "cross_border", "obs_status"]
        # AUFZW=1 (99.0) darf nicht enthalten sein
        q4 = bgs[(bgs["noga"] == "21") & (bgs["period"] == "2025-Q4")]
        assert q4["cross_border"].tolist() == [120.0]

    def test_labels_both_format(self):
        text = SDMX_FIXTURE.replace(",21,_T,", ",21: Pharma,_T: Total,")
        df = parse_bgs_sdmx_csv(io.StringIO(text))
        assert "21" in set(df["noga"])

    def test_fehlende_spalte(self):
        with pytest.raises(ValueError, match="fehlende Spalten"):
            parse_bgs_sdmx_csv(io.StringIO("NOGA,TIME_PERIOD,OBS_VALUE\n21,2025-Q1,1\n"))

    def test_ohne_verwertbare_zeilen(self):
        with pytest.raises(ValueError):
            parse_bgs_sdmx_csv(io.StringIO("NOGA,AUFZW,TIME_PERIOD,OBS_VALUE\n_T,_T,2025-Q1,1\n"))

    def test_statent_pxweb(self):
        antwort = {"data": [
            {"key": ["2024", "999", "999", "2"], "values": ["100"]},
            {"key": ["2024", "999", "1", "2"], "values": ["60"]},
            {"key": ["2024", "999", "1", "5"], "values": ["40.4"]},
            {"key": ["2024", "999", "86", "2"], "values": ["X"]},
            {"key": ["2024", "999", "86", "5"], "values": ["..."]},
        ]}
        df = parse_statent_pxweb(antwort)
        assert list(df.columns) == ["year", "noga", "employed", "fte"]
        assert df.set_index("noga").loc["01", "employed"] == 60
        assert df.set_index("noga").loc["01", "fte"] == 40
        assert df.set_index("noga").loc["86", "employed"] == 0
        assert "999" not in set(df["noga"])


class TestPeriode:
    def test_default_ist_neuestes_volles_jahr(self, bgs):
        werte, label = waehle_periode(bgs)
        assert label == "2025"
        assert werte["21"] == pytest.approx(100.0)  # (80+90+110+120)/4

    def test_quartal(self, bgs):
        werte, label = waehle_periode(bgs, "2026-Q1")
        assert label == "2026-Q1"
        assert werte["69"] == 14.0

    def test_unvollstaendiges_jahr(self, bgs):
        with pytest.raises(ValueError, match="vier"):
            waehle_periode(bgs, "2026")

    def test_ungueltig(self, bgs):
        with pytest.raises(ValueError):
            waehle_periode(bgs, "Q3/2025")


class TestMapping:
    def test_alle_abteilungen_der_ggs_codeliste_zugeordnet(self):
        """Jede 2-stellige NOGA-Abteilung (01–99) ist gemappt oder bewusst ausgeschlossen."""
        nogas = {"01", "02", "03"} | {f"{i:02d}" for i in range(5, 100)}
        nicht_existent = {"04", "34", "40", "44", "48", "54", "57", "67", "76", "83", "89"}
        erwartet = nogas - nicht_existent
        assert erwartet <= set(NOGA_ZU_BRANCHE) | set(NOGA_OHNE_BRANCHE)
        assert not set(NOGA_ZU_BRANCHE) & set(NOGA_OHNE_BRANCHE)

    def test_21_branchen(self):
        assert set(NOGA_ZU_BRANCHE.values()) == ALLE_BRANCHEN

    def test_aggregation_und_ausschluss(self):
        werte = pd.Series({"21": 5.0, "20": 3.0, "69": 2.0, "97": 7.0})
        summe, ausgeschlossen = aggregiere_nach_branche(werte)
        assert summe["Industrie"] == 8.0
        assert summe["Recht"] == 2.0
        assert summe["Bau"] == 0.0
        assert ausgeschlossen == 7.0
        assert set(summe.index) == ALLE_BRANCHEN

    def test_unbekannte_noga(self):
        with pytest.raises(ValueError, match="ohne Branchen-Zuordnung"):
            aggregiere_nach_branche(pd.Series({"00": 1.0}))


class TestAnteil:
    def test_berechnung(self, bgs, statent):
        df = compute_grenzgaenger_anteil(bgs, statent).set_index("sector")
        n_industrie = sum(1 for b in NOGA_ZU_BRANCHE.values() if b == "Industrie")
        assert df.loc["Industrie", "employed_total"] == 1000 * n_industrie
        assert df.loc["Industrie", "cross_border"] == 100
        assert df.loc["Industrie", "cross_border_share"] == pytest.approx(100 / (1000 * n_industrie), abs=1e-4)
        assert df.loc["Recht", "cross_border_share"] == pytest.approx(0.01)
        assert df.loc["Recht", "cross_border_quarter"] == 14
        assert df.loc["Recht", "ggs_quarter"] == "2026-Q1"
        assert df.loc["Recht", "statent_year"] == 2024
        assert set(df.index) == ALLE_BRANCHEN

    def test_anteil_ueber_1_wird_abgelehnt(self, bgs, statent):
        klein = statent.assign(employed=1)
        with pytest.raises(ValueError, match="0–1"):
            compute_grenzgaenger_anteil(bgs, klein)

    def test_fehlender_nenner(self, bgs, statent):
        ohne_bau = statent[~statent["noga"].isin(["41", "42", "43"])]
        with pytest.raises(ValueError, match="Nenner"):
            compute_grenzgaenger_anteil(bgs, ohne_bau)


class TestVersionierteDaten:
    """Prüft die committeten CSVs (Offline-Modus der App/Pipeline)."""

    @pytest.fixture
    def ergebnis(self) -> pd.DataFrame:
        return pd.read_csv(PROCESSED / "grenzgaenger_anteil_branche.csv")

    def test_alle_branchen_anteil_0_bis_1(self, ergebnis):
        assert set(ergebnis["sector"]) == ALLE_BRANCHEN
        assert ergebnis["cross_border_share"].between(0, 1).all()
        assert ergebnis["cross_border_share_quarter"].between(0, 1).all()
        assert (ergebnis["cross_border"] >= 0).all()
        assert (ergebnis["employed_total"] > 0).all()

    def test_anteil_konsistent(self, ergebnis):
        calc = ergebnis["cross_border"] / ergebnis["employed_total"]
        assert ((ergebnis["cross_border_share"] - calc).abs() < 1e-3).all()

    def test_offline_reproduzierbar(self, ergebnis):
        bgs = pd.read_csv(fetch_bgs.BGS_CSV, dtype={"noga": str, "period": str, "obs_status": str},
                          keep_default_na=False)
        statent = pd.read_csv(fetch_bgs.STATENT_CSV, dtype={"noga": str})
        neu = compute_grenzgaenger_anteil(bgs, statent, str(ergebnis["ggs_period"].iloc[0]))
        pd.testing.assert_frame_equal(
            neu.sort_values("sector").reset_index(drop=True)[["sector", "cross_border", "cross_border_share"]],
            ergebnis.sort_values("sector").reset_index(drop=True)[["sector", "cross_border", "cross_border_share"]],
        )

    def test_gesamtanteil_plausibel(self, ergebnis):
        gesamt = ergebnis["cross_border"].sum() / ergebnis["employed_total"].sum()
        assert 0.04 < gesamt < 0.12
