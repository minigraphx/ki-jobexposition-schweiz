"""
HISTORISCH — nicht mehr verwenden (Stand Oktober 2026).

Demo-Scores der Anfangsphase (Literaturwerte je Beruf, Fallback nach Branche/Qualifikation)
für die Entwicklung, bevor das Sprachmodell-Scoring lief.

Alle Einträge sind inzwischen aufgabenbasiert bewertet; Demo-Werte würden scores.csv mit
Platzhaltern überschreiben.

Der frühere Code ist in der Git-Historie erhalten (letzte Fassung vor der Umstellung auf die
aufgabenbasierten Scores und englische Spaltennamen, Issue #53).
"""
import sys

MELDUNG = ("generate_demo_scores.py ist historisch — echte Scores: python src/scoring/task_scorer.py → src/scoring/task_aggregate.py → src/scoring/apply_task_scores.py (siehe docs/neubewertung_lokal.md)")

if __name__ == "__main__":
    sys.exit(MELDUNG)
