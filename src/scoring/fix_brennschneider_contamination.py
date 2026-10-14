"""
HISTORISCH — nicht mehr verwenden (Stand Oktober 2026).

Einmalige Korrektur (April 2026) von 14 Berufen, deren haupt_risiko/begruendung
Brennschneider-Texte enthielten (Artefakt der früheren Batch-Bewertung).

Die betroffenen Spalten der früheren Methode gibt es nicht mehr; die Texte stammen aus der
aufgabenbasierten Bewertung (Spalten main_risk, rationale).

Der frühere Code ist in der Git-Historie erhalten (letzte Fassung vor der Umstellung auf die
aufgabenbasierten Scores und englische Spaltennamen, Issue #53).
"""
import sys

MELDUNG = ("fix_brennschneider_contamination.py ist historisch — Scores und Texte: python src/scoring/task_scorer.py → src/scoring/task_aggregate.py → src/scoring/apply_task_scores.py (siehe docs/neubewertung_lokal.md)")

if __name__ == "__main__":
    sys.exit(MELDUNG)
