"""
HISTORISCH — nicht mehr verwenden (Stand Oktober 2026).

Qualitätsprüfung der früheren Methode: Haiku prüfte, ob haupt_risiko/begruendung zum
Berufstitel passen, generierte Beschreibungen und liess Sonnet neu scoren
(Ergebnis data/processed/audit_report.json, versioniert als Referenz).

Die aufgabenbasierte Bewertung validiert jede Antwort gegen das Rubrik-Schema
(task_rubrik.pruefe_bewertung), bewertet mit zwei Modellen und markiert Abweichungen
(uncertain); die Spalten der früheren Methode existieren nicht mehr.

Der frühere Code ist in der Git-Historie erhalten (letzte Fassung vor der Umstellung auf die
aufgabenbasierten Scores und englische Spaltennamen, Issue #53).
"""
import sys

MELDUNG = ("full_quality_audit.py ist historisch — Qualitätssicherung über Schema-Validierung und zwei Modelle: python src/scoring/task_scorer.py → src/scoring/task_aggregate.py → src/scoring/apply_task_scores.py (siehe docs/neubewertung_lokal.md)")

if __name__ == "__main__":
    sys.exit(MELDUNG)
