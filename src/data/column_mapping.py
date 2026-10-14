"""Zentrale Zuordnung der CSV-Spaltennamen in data/processed/ (Issue #53): alt (deutsch) → neu.

Alle Spaltennamen sind englisches snake_case-ASCII; Zellwerte (z. B. Branchennamen
«Öff. Verwaltung», Zeitrahmen «3-5 Jahre», Mapping-Ebenen «gattung»/«berufsart») bleiben
unverändert, weil sie in der App sichtbar sind. Dateinamen bleiben gleich.

- ``SPALTEN[datei]``: alt → neu (Identität, wo der Name schon englisch war)
- ``ENTFERNT[datei]``: alte Spalten, die die Migration löscht (nur scores.csv: die Scores der
  früheren Karpathy-Methode; ersetzt durch die aufgabenbasierten Spalten aus scores_aufgaben.csv,
  siehe src/scoring/apply_task_scores.py)
- ``SCORES_SCHEMA``: Spalten und Reihenfolge der fertigen scores.csv (App-Datei)

Verwendet von src/data/migrate_columns.py (einmalige, idempotente Umbenennung) und als
Referenz in den Tests. Die Schlüssel der Input-Datensätze der aufgabenbasierten Bewertung
(task_inputs.py) bleiben deutsch — sie sind Teil des Input-Hashes.
"""
from __future__ import annotations

# Stammdaten-Spalten von berufe_ch*.csv und scores.csv
STAMMDATEN: dict[str, str] = {
    "beruf": "occupation",
    "synonyme": "synonyms",
    "isco_code": "isco_code",
    "beschaeftigte_1000": "employed_k",
    "frauen_pct": "women_pct",
    "branche": "sector",
    "lohn_median_chf": "wage_median_chf",
    "lohn_quelle": "wage_source",
    "lohn_unsicher": "wage_uncertain",
    "qualifikation": "qualification",
    "esco_uri": "esco_uri",
    "esco_titel": "esco_title",
    "esco_beschreibung": "esco_description",
    "beschreibung_quelle": "description_source",
    "esco_isco_code": "esco_isco_code",
    "esco_match_qualitaet": "esco_match_quality",
}

# scores.csv: zusätzlich übernommene Spalten (Werte bleiben bis zum nächsten Pipeline-Schritt gleich)
SCORES_ZUSATZ: dict[str, str] = {
    "adaptabilitaet": "adaptability",
    "score_ch": "legacy_score",                 # alter Endscore, nur für den Vergleich alt/neu
    "grossfirmen_anteil": "large_firm_share",
    "zeitrahmen_kmu_delta": "timeframe_sme_shift",
}

# scores.csv: Spalten der früheren Methode, die die Migration entfernt
SCORES_ENTFERNT: tuple[str, ...] = (
    "score_gesamt", "score_digital", "score_wiederholbarkeit", "score_physisch",
    "score_kreativitaet", "score_sozial", "haupt_risiko", "zeitrahmen", "begruendung",
    "zeitrahmen_roh", "delta_branche", "delta_lohn", "lohnklasse", "beschreibung_hash",
    "scores_gemittelt",
)

# scores_aufgaben.csv (geschrieben von src/scoring/task_aggregate.py)
SCORES_AUFGABEN: dict[str, str] = {
    "isco_code": "isco_code",
    "beruf": "occupation",
    "score_aufgaben": "exposure",
    "score_aufgaben_beta": "exposure_beta",
    "score_zeitersparnis": "time_savings",
    "anteil_ersetzend": "share_replacing",
    "anteil_delegierend": "share_delegating",
    "anteil_unterstuetzend": "share_assisting",
    "ersetzbare_zeit": "replaceable_time",
    "score_physisch_auto": "physical_automation",
    "score_software_auto": "software_automation",
    "sicherheit_tief_anteil": "low_confidence_share",
    "zeitrahmen": "timeframe",
    "haupt_risiko": "main_risk",
    "begruendung": "rationale",
    "n_laeufe_claude": "n_runs_claude",
    "n_laeufe_gemini": "n_runs_gemini",
    "score_aufgaben_claude": "exposure_claude",
    "score_aufgaben_gemini": "exposure_gemini",
    "score_zeitersparnis_claude": "time_savings_claude",
    "score_zeitersparnis_gemini": "time_savings_gemini",
    "delta_laeufe_claude": "spread_runs_claude",
    "delta_laeufe_gemini": "spread_runs_gemini",
    "delta_laeufe": "spread_runs",
    "delta_provider": "delta_provider",
    "flag_unsicher": "uncertain",
    "flag_grund": "uncertain_reason",
    "zeitrahmen_claude": "timeframe_claude",
    "zeitrahmen_gemini": "timeframe_gemini",
    "text_quelle": "text_source",
    "claude_quelle": "claude_source",
    "rubrik_version": "rubric_version",
}

SPALTEN: dict[str, dict[str, str]] = {
    "scores.csv": {**STAMMDATEN, **SCORES_ZUSATZ},
    "berufe_ch.csv": STAMMDATEN,
    "berufe_ch_esco.csv": STAMMDATEN,
    "berufe_ch_esco_verified.csv": STAMMDATEN,
    "beruf_berufsart_mapping.csv": {
        "beruf": "occupation", "isco_code": "isco_code", "ebene": "level", "berufsarten": "se_types",
        "synonyme": "synonyms", "zusammengelegt_aus": "merged_from", "text_von": "text_from",
        "begruendung": "rationale",
    },
    "esco_kompetenzen.csv": {
        "beruf": "occupation", "isco_code": "isco_code", "esco_uri": "esco_uri", "kompetenz": "competence",
        "relation": "relation", "typ": "type", "kompetenz_uri": "competence_uri",
    },
    "grenzgaenger_anteil_branche.csv": {
        "branche": "sector", "grenzgaenger": "cross_border", "beschaeftigte_total": "employed_total",
        "grenzgaenger_anteil": "cross_border_share", "grenzgaenger_quartal": "cross_border_quarter",
        "grenzgaenger_anteil_quartal": "cross_border_share_quarter", "bgs_periode": "ggs_period",
        "bgs_quartal": "ggs_quarter", "statent_jahr": "statent_year",
    },
    "bgs_grenzgaenger_noga.csv": {
        "noga": "noga", "periode": "period", "grenzgaenger": "cross_border", "obs_status": "obs_status",
    },
    "kmu_anteil_branche.csv": {
        "branche": "sector", "beschaeftigte_total": "employed_total", "beschaeftigte_gross": "employed_large",
        "grossfirmen_anteil": "large_firm_share", "quelle": "source", "jahr": "year", "einheit": "unit",
        "abdeckung": "coverage",
    },
    "lohn_profile_salarium.csv": {
        "isco_code": "isco_code", "beruf": "occupation", "salarium_gruppe": "salarium_group", "noga": "noga",
        "ausbildung": "education", "begruendung": "rationale",
    },
    "lohn_salarium_abfragen.csv": {
        "salarium_gruppe": "salarium_group", "noga": "noga", "ausbildung": "education", "region": "region",
        "konsistent": "consistent", "ausbildung_code": "education_code", "median_monat": "median_monthly",
        "qualitaet": "quality", "abfrage_datum": "query_date", "normprofil_id": "norm_profile_id",
    },
    "lohn_verhaeltnisse.csv": {
        "isco_code": "isco_code", "beruf": "occupation", "faktor_zu_lse_gruppe": "factor_to_lse_group",
        "band_unten": "band_low", "band_oben": "band_high", "lohn_unsicher": "wage_uncertain",
        "quelle": "source", "methode": "method", "bemerkung": "note",
    },
    "lse2024_monatslohn_isco.csv": {
        "isco_prefix": "isco_prefix", "ebene": "level", "bezeichnung": "label", "median_monat": "median_monthly",
    },
    "se_berufe.csv": {
        "blatt": "sheet", "ebene": "level", "code": "code", "bezeichnung": "label", "total": "total",
        "maenner": "men", "frauen": "women", "total_lt50": "total_lt50",
    },
    "statent_beschaeftigte_noga.csv": {"jahr": "year", "noga": "noga", "beschaeftigte": "employed", "vzae": "fte"},
    "statent_groessenklassen_noga.csv": {
        "jahr": "year", "noga": "noga", "groessenklasse": "size_class", "unternehmen": "enterprises",
        "unternehmen_status": "enterprises_status", "beschaeftigte": "employed",
        "beschaeftigte_status": "employed_status",
    },
    "statent_vzae_grossregion.csv": {"jahr": "year", "noga": "noga", "region": "region", "vzae": "fte"},
    "benchmarks_isco4.csv": {
        "isco_code": "isco_code", "ilo25_mean": "ilo25_mean", "eloundou_gpt4_beta": "eloundou_gpt4_beta",
        "aei_observed_exposure": "aei_observed_exposure",
    },
    "scores_aufgaben.csv": SCORES_AUFGABEN,
}

ENTFERNT: dict[str, tuple[str, ...]] = {"scores.csv": SCORES_ENTFERNT}

# Fertige scores.csv (App-Datei): Stammdaten, Expositions-Block, Zeitrahmen-Block, Anpassungsfähigkeit,
# alter Score. Geschrieben von src/scoring/apply_task_scores.py.
SCORES_STAMMDATEN: list[str] = list(STAMMDATEN.values())
SCORES_EXPOSITION: list[str] = [
    "exposure", "exposure_beta", "time_savings", "share_replacing", "share_delegating", "share_assisting",
    "replaceable_time", "physical_automation", "software_automation", "low_confidence_share", "main_risk",
    "rationale", "exposure_claude", "exposure_gemini", "delta_provider", "spread_runs", "uncertain",
    "uncertain_reason", "n_runs_claude", "n_runs_gemini", "text_source",
]
SCORES_ZEITRAHMEN: list[str] = ["timeframe_raw", "large_firm_share", "timeframe_sme_shift", "timeframe"]
SCORES_SCHEMA: list[str] = (SCORES_STAMMDATEN + SCORES_EXPOSITION + SCORES_ZEITRAHMEN
                            + ["adaptability", "legacy_score"])

# Spalten, die eine Datei nach der Migration (bzw. nach späteren Pipeline-Schritten) haben darf
ZUSAETZLICH_NEU: dict[str, list[str]] = {"scores.csv": SCORES_SCHEMA}


def neue_spalten(datei: str) -> set[str]:
    """Alle zulässigen neuen Spaltennamen einer Datei."""
    return set(SPALTEN[datei].values()) | set(ZUSAETZLICH_NEU.get(datei, []))


def alte_spalten(datei: str) -> set[str]:
    """Alle bekannten alten Spaltennamen einer Datei (umzubenennen oder zu entfernen)."""
    return set(SPALTEN[datei]) | set(ENTFERNT.get(datei, ()))


def nur_alt(datei: str) -> set[str]:
    """Alte Namen, die es neu nicht gibt (daran erkennt man eine nicht migrierte Datei)."""
    return alte_spalten(datei) - neue_spalten(datei)
