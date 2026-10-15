"""Unit Tests für src/scoring/kmu_faktor.py (KMU-Adoptions-Faktor, früher in ch_adjustments.py)."""

from pathlib import Path

import pandas as pd
import pytest

from kmu_faktor import (
    BRANCHEN,
    GROSSFIRMEN_SCHWELLE_HOCH,
    GROSSFIRMEN_SCHWELLE_TIEF,
    ZEITRAHMEN_STUFEN,
    adjust_zeitrahmen_fuer_kmu,
    kmu_verschiebung,
    pruefe_branchen,
    verschiebe_zeitrahmen,
)
import task_rubrik as tr


def _make_kmu_csv(tmp_path: Path, rows: list[dict]) -> Path:
    """Hilfsfunktion: schreibt eine temporäre kmu_anteil_branche.csv."""
    path = tmp_path / "kmu_anteil_branche.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


class TestBranchen:
    def test_alle_21_branchen(self):
        assert BRANCHEN == {
            "Industrie", "Finanzen", "Verwaltung", "Gastgewerbe", "Gesundheit",
            "ICT", "Bau", "Bildung", "Soziales", "Transport", "Detailhandel",
            "Medien", "Dienstleistungen", "Landwirtschaft", "Öff. Verwaltung",
            "Versicherungen", "Recht", "Immobilien", "Beratung", "Sicherheit",
            "Umwelt",
        }

    def test_unbekannte_branche_wirft_valueerror(self):
        with pytest.raises(ValueError, match="Raumfahrt"):
            pruefe_branchen(["Finanzen", "Raumfahrt"])

    def test_leer_und_nan_erlaubt(self):
        pruefe_branchen(["Finanzen", "", float("nan"), None])


class TestShiftZeitrahmen:
    def test_kein_shift(self):
        assert verschiebe_zeitrahmen("3-5 Jahre", 0) == "3-5 Jahre"

    def test_frueher(self):
        assert verschiebe_zeitrahmen("5-10 Jahre", -1) == "3-5 Jahre"

    def test_spaeter(self):
        assert verschiebe_zeitrahmen("3-5 Jahre", +1) == "5-10 Jahre"

    def test_clip_unten(self):
        """Kann nicht über '1-2 Jahre' hinaus früher werden."""
        assert verschiebe_zeitrahmen("1-2 Jahre", -1) == "1-2 Jahre"

    def test_clip_oben(self):
        """Kann nicht über '>10 Jahre' hinaus später werden."""
        assert verschiebe_zeitrahmen(">10 Jahre", +1) == ">10 Jahre"

    def test_unbekannter_wert_unveraendert(self):
        assert verschiebe_zeitrahmen("unbekannt", -1) == "unbekannt"

    def test_stufen_wie_rubrik(self):
        assert ZEITRAHMEN_STUFEN == tr.ZEITRAHMEN


class TestAdjustZeitrahmenFuerKmu:
    def test_ohne_kmu_datei_unveraendert(self, tmp_path):
        """Fehlende kmu_anteil_branche.csv → kein Fehler, kein Shift."""
        df = pd.DataFrame({"occupation": ["Beruf A"], "sector": ["Finanzen"], "timeframe_raw": ["3-5 Jahre"]})
        result = adjust_zeitrahmen_fuer_kmu(df, kmu_path=tmp_path / "nicht_vorhanden.csv")
        assert result.equals(df)

    def test_rohwert_aus_timeframe_wird_gespeichert(self, tmp_path):
        kmu_path = _make_kmu_csv(tmp_path, [{"sector": "Finanzen", "large_firm_share": 0.28}])
        df = pd.DataFrame({"occupation": ["Bankfachmann"], "sector": ["Finanzen"], "timeframe": ["3-5 Jahre"]})
        result = adjust_zeitrahmen_fuer_kmu(df, kmu_path=kmu_path)
        assert result["timeframe_raw"].iloc[0] == "3-5 Jahre"

    def test_immutabilitaet(self, tmp_path):
        """Original-DataFrame darf nicht verändert werden."""
        kmu_path = _make_kmu_csv(tmp_path, [{"sector": "Gastgewerbe", "large_firm_share": 0.02}])
        df = pd.DataFrame({"occupation": ["Koch"], "sector": ["Gastgewerbe"], "timeframe_raw": ["3-5 Jahre"]})
        adjust_zeitrahmen_fuer_kmu(df, kmu_path=kmu_path)
        assert list(df.columns) == ["occupation", "sector", "timeframe_raw"]
        assert df["timeframe_raw"].iloc[0] == "3-5 Jahre"

    def test_anteil_tief_spaeter(self, tmp_path):
        """Anteil <15 % → +1 Stufe (später)."""
        kmu_path = _make_kmu_csv(tmp_path, [{"sector": "Gastgewerbe", "large_firm_share": 0.02}])
        df = pd.DataFrame({"occupation": ["Koch"], "sector": ["Gastgewerbe"], "timeframe_raw": ["3-5 Jahre"]})
        result = adjust_zeitrahmen_fuer_kmu(df, kmu_path=kmu_path)
        assert result["timeframe"].iloc[0] == "5-10 Jahre"
        assert result["timeframe_sme_shift"].iloc[0] == +1

    def test_anteil_hoch_frueher(self, tmp_path):
        """Anteil ≥50 % → −1 Stufe (früher)."""
        kmu_path = _make_kmu_csv(tmp_path, [{"sector": "Versicherungen", "large_firm_share": 0.82}])
        df = pd.DataFrame({"occupation": ["Versicherungsexperte"], "sector": ["Versicherungen"],
                           "timeframe_raw": ["5-10 Jahre"]})
        result = adjust_zeitrahmen_fuer_kmu(df, kmu_path=kmu_path)
        assert result["timeframe"].iloc[0] == "3-5 Jahre"
        assert result["timeframe_sme_shift"].iloc[0] == -1

    def test_neutral_bereich(self, tmp_path):
        """Anteil 15–50 % → kein Shift."""
        kmu_path = _make_kmu_csv(tmp_path, [{"sector": "ICT", "large_firm_share": 0.45}])
        df = pd.DataFrame({"occupation": ["Softwareentwickler"], "sector": ["ICT"], "timeframe_raw": ["3-5 Jahre"]})
        result = adjust_zeitrahmen_fuer_kmu(df, kmu_path=kmu_path)
        assert result["timeframe"].iloc[0] == "3-5 Jahre"
        assert result["timeframe_sme_shift"].iloc[0] == 0

    def test_clip_bei_maximum(self, tmp_path):
        """Kein Shift über '>10 Jahre' hinaus."""
        kmu_path = _make_kmu_csv(tmp_path, [{"sector": "Gastgewerbe", "large_firm_share": 0.02}])
        df = pd.DataFrame({"occupation": ["Koch"], "sector": ["Gastgewerbe"], "timeframe_raw": [">10 Jahre"]})
        result = adjust_zeitrahmen_fuer_kmu(df, kmu_path=kmu_path)
        assert result["timeframe"].iloc[0] == ">10 Jahre"

    def test_unbekannte_branche_kein_shift(self, tmp_path):
        """Branche nicht in kmu_anteil_branche.csv → delta = 0."""
        kmu_path = _make_kmu_csv(tmp_path, [{"sector": "Finanzen", "large_firm_share": 0.28}])
        df = pd.DataFrame({"occupation": ["X"], "sector": ["Raumfahrt"], "timeframe_raw": ["3-5 Jahre"]})
        result = adjust_zeitrahmen_fuer_kmu(df, kmu_path=kmu_path)
        assert result["timeframe"].iloc[0] == "3-5 Jahre"
        assert result["timeframe_sme_shift"].iloc[0] == 0

    def test_ohne_zeitrahmen_spalte(self, tmp_path):
        """Weder timeframe_raw noch timeframe → DataFrame unverändert zurück."""
        kmu_path = _make_kmu_csv(tmp_path, [{"sector": "ICT", "large_firm_share": 0.31}])
        df = pd.DataFrame({"occupation": ["X"], "sector": ["ICT"]})
        result = adjust_zeitrahmen_fuer_kmu(df, kmu_path=kmu_path)
        assert "timeframe" not in result.columns

    def test_large_firm_share_spalte_vorhanden(self, tmp_path):
        kmu_path = _make_kmu_csv(tmp_path, [{"sector": "Finanzen", "large_firm_share": 0.28}])
        df = pd.DataFrame({"occupation": ["Banker"], "sector": ["Finanzen"], "timeframe_raw": ["3-5 Jahre"]})
        result = adjust_zeitrahmen_fuer_kmu(df, kmu_path=kmu_path)
        assert result["large_firm_share"].iloc[0] == pytest.approx(0.28)

    def test_schwellen(self):
        """Schwellen STATENT (Unternehmen ≥250 Beschäftigte): oberes/unteres Segment."""
        assert GROSSFIRMEN_SCHWELLE_HOCH == pytest.approx(0.50)
        assert GROSSFIRMEN_SCHWELLE_TIEF == pytest.approx(0.15)

    @pytest.mark.parametrize("anteil, delta", [
        (GROSSFIRMEN_SCHWELLE_HOCH, -1),           # Grenze gehört zum oberen Segment
        (GROSSFIRMEN_SCHWELLE_HOCH - 0.0001, 0),
        (GROSSFIRMEN_SCHWELLE_TIEF, 0),            # Grenze gehört zum neutralen Bereich
        (GROSSFIRMEN_SCHWELLE_TIEF - 0.0001, +1),
        (0.0, +1),
        (1.0, -1),
    ])
    def test_raender(self, anteil, delta):
        kmu = pd.DataFrame({"sector": ["X"], "large_firm_share": [anteil]})
        df = pd.DataFrame({"occupation": ["B"], "sector": ["X"], "timeframe_raw": ["3-5 Jahre"]})
        result = adjust_zeitrahmen_fuer_kmu(df, kmu_df=kmu)
        assert result["timeframe_sme_shift"].iloc[0] == delta
        assert kmu_verschiebung(anteil) == delta

    def test_anteil_nan_neutral(self):
        """Branche ohne Anteil (Öff. Verwaltung: keine marktwirtschaftl. Unternehmen) → 0."""
        kmu = pd.DataFrame({"sector": ["Öff. Verwaltung"], "large_firm_share": [float("nan")]})
        df = pd.DataFrame({"occupation": ["B"], "sector": ["Öff. Verwaltung"], "timeframe_raw": ["5-10 Jahre"]})
        result = adjust_zeitrahmen_fuer_kmu(df, kmu_df=kmu)
        assert result["timeframe"].iloc[0] == "5-10 Jahre"
        assert result["timeframe_sme_shift"].iloc[0] == 0

    def test_kmu_df_hat_vorrang(self, tmp_path):
        """kmu_df wird statt der Datei verwendet."""
        kmu_path = _make_kmu_csv(tmp_path, [{"sector": "Finanzen", "large_firm_share": 0.02}])
        kmu = pd.DataFrame({"sector": ["Finanzen"], "large_firm_share": [0.6]})
        df = pd.DataFrame({"occupation": ["B"], "sector": ["Finanzen"], "timeframe_raw": ["3-5 Jahre"]})
        result = adjust_zeitrahmen_fuer_kmu(df, kmu_path=kmu_path, kmu_df=kmu)
        assert result["timeframe"].iloc[0] == "1-2 Jahre"


class TestZeitrahmenIdempotenz:
    def test_zweimal_anwenden_verschiebt_nur_einmal(self, tmp_path):
        """Bereits adjustierte Zeilen (mit timeframe_raw) dürfen nicht doppelt verschoben werden."""
        kmu_path = _make_kmu_csv(tmp_path, [{"sector": "Gastgewerbe", "large_firm_share": 0.02}])
        df = pd.DataFrame({"occupation": ["Koch"], "sector": ["Gastgewerbe"], "timeframe": ["3-5 Jahre"]})
        einmal = adjust_zeitrahmen_fuer_kmu(df, kmu_path=kmu_path)
        zweimal = adjust_zeitrahmen_fuer_kmu(einmal, kmu_path=kmu_path)
        assert einmal["timeframe"].iloc[0] == "5-10 Jahre"
        assert zweimal["timeframe"].iloc[0] == "5-10 Jahre"
        assert zweimal["timeframe_raw"].iloc[0] == "3-5 Jahre"

    def test_fehlender_rohwert_nutzt_timeframe(self, tmp_path):
        """Zeilen ohne timeframe_raw (leer oder NaN) nutzen timeframe als Rohwert."""
        kmu_path = _make_kmu_csv(tmp_path, [{"sector": "Gastgewerbe", "large_firm_share": 0.02}])
        df = pd.DataFrame({
            "occupation": ["Koch", "Kellner", "Hilfe"], "sector": ["Gastgewerbe"] * 3,
            "timeframe": ["5-10 Jahre", "1-2 Jahre", "3-5 Jahre"],
            "timeframe_raw": ["3-5 Jahre", None, ""],
        })
        result = adjust_zeitrahmen_fuer_kmu(df, kmu_path=kmu_path)
        assert result["timeframe"].tolist() == ["5-10 Jahre", "3-5 Jahre", "5-10 Jahre"]
        assert result["timeframe_raw"].tolist() == ["3-5 Jahre", "1-2 Jahre", "3-5 Jahre"]
