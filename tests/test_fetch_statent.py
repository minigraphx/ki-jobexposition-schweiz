"""Tests für fetch_statent.py (KMU-Adoptions-Faktor aus BFS STATENT ts-x-06.02.01.01)."""

import io
from pathlib import Path

import pandas as pd
import pytest

import fetch_statent
from fetch_statent import (
    NOGA_ZU_BRANCHE,
    compute_kmu_anteil,
    lese_groessenklassen,
    parse_statent_groessenklassen_csv,
    schaetze_gesperrte_werte,
    spannweite_gesperrt,
    vergleich_mit_bisher,
    zeitrahmen_in_scores_neu,
)

PROCESSED = Path(__file__).parent.parent / "data" / "processed"

ALLE_BRANCHEN = {
    "Bau", "Industrie", "Gastgewerbe", "Transport", "Gesundheit",
    "Detailhandel", "ICT", "Finanzen", "Versicherungen", "Recht",
    "Bildung", "Verwaltung", "Öff. Verwaltung", "Soziales",
    "Landwirtschaft", "Umwelt", "Sicherheit", "Dienstleistungen",
    "Immobilien", "Medien", "Beratung",
}


def _zeilen(jahr: str, noga: str, beschaeftigte: dict, unternehmen: dict | None = None) -> list[str]:
    """CSV-Zeilen im BFS-Format; Wert None → STATUS Q (gesperrt)."""
    out = []
    for code, wert in beschaeftigte.items():
        if unternehmen is not None:
            u = unternehmen.get(code)
            out.append(f'"{jahr}","{noga}","{code}","1","{"" if u is None else u}",'
                       f'"{"Q" if u is None else "A"}"')
        out.append(f'"{jahr}","{noga}","{code}","2","{"" if wert is None else wert}",'
                   f'"{"Q" if wert is None else "A"}"')
    return out


# Ausschnitt im Format des OGD-CSV (UTF-8 mit BOM, alle Felder in Anführungszeichen)
FIXTURE_ZEILEN = (
    ['﻿"PERIOD","NOGA","SIZE","INDICATOR","VALUE","STATUS"']
    # Bank (64 → Finanzen): 60 % in Grossunternehmen
    + _zeilen("2024", "64", {"1": 100, "2": 100, "3": 200, "4": 600, "999": 1000},
              {"1": 50, "2": 5, "3": 2, "4": 1, "999": 58})
    # Gastronomie (56 → Gastgewerbe): Klasse 250+ gesperrt, Rest 100 auf 2 Klassen
    + _zeilen("2024", "56", {"1": 500, "2": None, "3": 300, "4": None, "999": 900})
    # Beherbergung (55 → Gastgewerbe)
    + _zeilen("2024", "55", {"1": 100, "2": 0, "3": 0, "4": 0, "999": 100})
    # Bergbau (06 → Industrie): auch Total gesperrt → 0
    + _zeilen("2024", "06", {"1": None, "2": 0, "3": 0, "4": 0, "999": None})
    # Öffentliche Verwaltung (84): keine marktwirtschaftlichen Unternehmen
    + _zeilen("2024", "84", {"1": 0, "2": 0, "3": 0, "4": 0, "999": 0})
    # Total aller Abteilungen
    + _zeilen("2024", "999", {"1": 700, "2": 200, "3": 500, "4": 700, "999": 2100})
    # älteres Jahr, nicht verwendet
    + _zeilen("2023", "64", {"1": 100, "2": 100, "3": 100, "4": 100, "999": 400})
)
FIXTURE_CSV = "\n".join(FIXTURE_ZEILEN) + "\n"


@pytest.fixture
def gk() -> pd.DataFrame:
    return parse_statent_groessenklassen_csv(io.StringIO(FIXTURE_CSV))


class TestParsing:
    def test_spalten_und_klassen(self, gk):
        assert list(gk.columns) == ["year", "noga", "size_class", "enterprises",
                                    "enterprises_status", "employed", "employed_status"]
        assert set(gk["size_class"]) == {"1-9", "10-49", "50-249", "250+", "total"}
        assert set(gk["year"]) == {2023, 2024}

    def test_werte_und_status(self, gk):
        bank = gk[(gk["year"] == 2024) & (gk["noga"] == "64")].set_index("size_class")
        assert bank.at["250+", "employed"] == 600
        assert bank.at["250+", "enterprises"] == 1
        assert bank.at["total", "employed_status"] == "A"

    def test_gesperrt_ist_leer(self, gk):
        gastro = gk[(gk["year"] == 2024) & (gk["noga"] == "56")].set_index("size_class")
        assert pd.isna(gastro.at["250+", "employed"])
        assert gastro.at["250+", "employed_status"] == "Q"

    def test_fehlende_spalte(self):
        with pytest.raises(ValueError, match="fehlende Spalten"):
            parse_statent_groessenklassen_csv(io.StringIO("PERIOD,NOGA,VALUE\n2024,64,1\n"))

    def test_unbekannte_groessenklasse(self):
        text = FIXTURE_CSV.replace('"2024","55","4"', '"2024","55","7"')
        with pytest.raises(ValueError, match="Grössenklassen"):
            parse_statent_groessenklassen_csv(io.StringIO(text))

    def test_roundtrip_csv(self, gk, tmp_path):
        """Versionierte Datei liefert dieselbe Berechnung wie der Rohdownload."""
        pfad = tmp_path / "gk.csv"
        gk.to_csv(pfad, index=False)
        wieder = lese_groessenklassen(pfad)
        pd.testing.assert_frame_equal(compute_kmu_anteil(wieder), compute_kmu_anteil(gk))


class TestGesperrteWerte:
    def test_rest_gleichmaessig_verteilt(self, gk):
        w = schaetze_gesperrte_werte(gk, 2024)
        assert w.at["56", "10-49"] == pytest.approx(50.0)
        assert w.at["56", "250+"] == pytest.approx(50.0)
        assert bool(w.at["56", "gross_gesperrt"])

    def test_total_gesperrt_wird_null(self, gk):
        w = schaetze_gesperrte_werte(gk, 2024)
        assert w.loc["06", ["1-9", "10-49", "50-249", "250+"]].sum() == 0

    def test_spannweite(self, gk):
        sw = spannweite_gesperrt(gk, 2024).set_index("sector")
        # Gastgewerbe: total 1000, ≥250 zwischen 0 und 100
        assert sw.at["Gastgewerbe", "anteil_min"] == pytest.approx(0.0)
        assert sw.at["Gastgewerbe", "anteil_max"] == pytest.approx(0.1)

    def test_unbekanntes_jahr(self, gk):
        with pytest.raises(ValueError, match="1999"):
            schaetze_gesperrte_werte(gk, 1999)


class TestKmuAnteil:
    def test_anteile(self, gk):
        df = compute_kmu_anteil(gk).set_index("sector")
        assert df.at["Finanzen", "large_firm_share"] == pytest.approx(0.6)
        assert df.at["Gastgewerbe", "large_firm_share"] == pytest.approx(0.05)
        assert df.at["Gastgewerbe", "employed_total"] == 1000
        assert df.at["Finanzen", "year"] == 2024

    def test_neuestes_jahr_default_und_wahl(self, gk):
        assert compute_kmu_anteil(gk)["year"].iloc[0] == 2024
        alt = compute_kmu_anteil(gk, 2023).set_index("sector")
        assert alt.at["Finanzen", "large_firm_share"] == pytest.approx(0.25)

    def test_ohne_unternehmen_nan(self, gk):
        df = compute_kmu_anteil(gk).set_index("sector")
        assert pd.isna(df.at["Öff. Verwaltung", "large_firm_share"])
        # Branchen ohne Zeilen in der Fixture ebenfalls ohne Anteil
        assert pd.isna(df.at["ICT", "large_firm_share"])

    def test_format(self, gk):
        df = compute_kmu_anteil(gk)
        assert list(df.columns) == ["sector", "employed_total", "employed_large",
                                    "large_firm_share", "source", "year", "unit", "coverage"]
        assert set(df["sector"]) == ALLE_BRANCHEN
        assert df["large_firm_share"].dropna().between(0, 1).all()

    def test_abdeckung(self, gk):
        statent = pd.DataFrame({"year": [2024, 2024, 2024], "noga": ["64", "55", "56"],
                                "employed": [2000, 100, 900], "fte": [1, 1, 1]})
        df = compute_kmu_anteil(gk, statent_noga=statent).set_index("sector")
        assert df.at["Finanzen", "coverage"] == pytest.approx(0.5)
        assert df.at["Gastgewerbe", "coverage"] == pytest.approx(1.0)

    def test_unbekannte_noga(self):
        text = FIXTURE_CSV.replace('"2024","55",', '"2024","97",')
        with pytest.raises(ValueError, match="97"):
            compute_kmu_anteil(parse_statent_groessenklassen_csv(io.StringIO(text)))

    def test_vergleich(self, gk):
        neu = compute_kmu_anteil(gk)
        alt = pd.DataFrame({"sector": ["Finanzen"], "large_firm_share": [0.28]})
        v = vergleich_mit_bisher(neu, alt).set_index("sector")
        assert v.at["Finanzen", "diff_pp"] == pytest.approx(32.0)
        assert vergleich_mit_bisher(neu, None) is None


class TestMapping:
    def test_alle_abteilungen_der_tabelle_zugeordnet(self):
        """Alle NOGA-Abteilungen 01–96 aus der BFS-Codeliste von ts-x-06.02.01.01 sind gemappt."""
        nogas = {"01", "02", "03"} | {f"{i:02d}" for i in range(5, 97)}
        nicht_existent = {"04", "34", "40", "44", "48", "54", "57", "67", "76", "83", "89"}
        assert nogas - nicht_existent == set(NOGA_ZU_BRANCHE)

    def test_21_branchen(self):
        assert set(NOGA_ZU_BRANCHE.values()) == ALLE_BRANCHEN


class TestScoresAnwenden:
    def _scores(self) -> pd.DataFrame:
        return pd.DataFrame({
            "occupation": ["Banker", "Koch", "Beamter", "Neu"],
            "sector": ["Finanzen", "Gastgewerbe", "Öff. Verwaltung", "Gastgewerbe"],
            "rationale": ["A", "B", "C", "D"],
            "timeframe_raw": ["3-5 Jahre", "3-5 Jahre", "5-10 Jahre", ""],
            "large_firm_share": ["0.28", "0.0238", "0.1507", ""],
            "timeframe_sme_shift": ["0", "1", "0", ""],
            "timeframe": ["3-5 Jahre", "5-10 Jahre", "5-10 Jahre", "1-2 Jahre"],
        }).astype(str)

    def test_nur_kmu_spalten(self):
        kmu = pd.DataFrame({"sector": ["Finanzen", "Gastgewerbe", "Öff. Verwaltung"],
                            "large_firm_share": [0.6, 0.05, float("nan")]})
        text = self._scores()
        out, diff = zeitrahmen_in_scores_neu(text, kmu)
        assert out["timeframe"].tolist() == ["1-2 Jahre", "5-10 Jahre", "5-10 Jahre", "3-5 Jahre"]
        assert out["timeframe_sme_shift"].tolist() == ["-1", "1", "0", "1"]
        assert out["large_firm_share"].tolist() == ["0.6", "0.05", "", "0.05"]
        assert out["timeframe_raw"].tolist() == ["3-5 Jahre", "3-5 Jahre", "5-10 Jahre", "1-2 Jahre"]
        assert out["rationale"].equals(text["rationale"])
        assert list(out.columns) == list(text.columns)
        assert set(diff["occupation"]) == {"Banker", "Koch", "Beamter", "Neu"}

    def test_dry_run_schreibt_nicht(self, gk, tmp_path, monkeypatch):
        scores = tmp_path / "scores.csv"
        self._scores().to_csv(scores, index=False)
        vorher = scores.read_bytes()
        monkeypatch.setattr(fetch_statent, "KMU_CSV", tmp_path / "kmu.csv")
        monkeypatch.setattr(fetch_statent, "lese_groessenklassen", lambda: gk)
        fetch_statent.main(["--offline", "--apply-scores", "--dry-run", "--scores", str(scores)])
        assert scores.read_bytes() == vorher
        assert not (tmp_path / "kmu.csv").exists()

    def test_anwenden_idempotent(self, gk, tmp_path, monkeypatch):
        scores = tmp_path / "scores.csv"
        self._scores().to_csv(scores, index=False)
        monkeypatch.setattr(fetch_statent, "KMU_CSV", tmp_path / "kmu.csv")
        monkeypatch.setattr(fetch_statent, "lese_groessenklassen", lambda: gk)
        argv = ["--offline", "--apply-scores", "--scores", str(scores)]
        fetch_statent.main(argv)
        erster = scores.read_bytes()
        fetch_statent.main(argv)
        assert scores.read_bytes() == erster
        assert (tmp_path / "kmu.csv").exists()


class TestVersionierteDaten:
    def test_groessenklassen_tabelle(self):
        gk = lese_groessenklassen(PROCESSED / "statent_groessenklassen_noga.csv")
        assert gk["year"].max() >= 2024
        neu = gk[gk["year"] == gk["year"].max()]
        assert set(neu["noga"]) - {"999"} == set(NOGA_ZU_BRANCHE)

    def test_kmu_anteil_branche(self):
        df = pd.read_csv(PROCESSED / "kmu_anteil_branche.csv")
        assert set(df["sector"]) == ALLE_BRANCHEN
        assert df["large_firm_share"].dropna().between(0, 1).all()
        assert df["large_firm_share"].notna().sum() == 20  # nur Öff. Verwaltung ohne Wert
        assert {"source", "year", "unit", "coverage"} <= set(df.columns)

    def test_kmu_anteil_reproduzierbar(self):
        """kmu_anteil_branche.csv entspricht der Berechnung aus der versionierten Tabelle."""
        gk = lese_groessenklassen(PROCESSED / "statent_groessenklassen_noga.csv")
        statent = pd.read_csv(PROCESSED / "statent_beschaeftigte_noga.csv", dtype={"noga": str})
        neu = compute_kmu_anteil(gk, None, statent)
        gespeichert = pd.read_csv(PROCESSED / "kmu_anteil_branche.csv")
        pd.testing.assert_series_equal(neu["large_firm_share"], gespeichert["large_firm_share"])
        assert neu["sector"].tolist() == gespeichert["sector"].tolist()
