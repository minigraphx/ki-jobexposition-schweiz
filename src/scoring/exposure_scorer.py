"""
HISTORISCH — nicht mehr verwenden (Stand Oktober 2026).

KI-Expositions-Scoring der früheren Methode (Karpathy-Ansatz: fünf Kriterien je 0–10,
Claude Sonnet, Hash-Delta über die ESCO-Beschreibung; Spalten score_gesamt, score_digital,
score_wiederholbarkeit, score_physisch, score_kreativitaet, score_sozial, haupt_risiko,
zeitrahmen, begruendung, beschreibung_hash).

Die Exposition stammt seit Oktober 2026 aus der aufgabenbasierten Bewertung (Rubrik v2.2,
zwei Modelle, mehrere Läufe); die alten Spalten sind aus scores.csv entfernt, der alte
Endscore steht nur noch als legacy_score für den Vergleich alt/neu.

Der frühere Code ist in der Git-Historie erhalten (letzte Fassung vor der Umstellung auf die
aufgabenbasierten Scores und englische Spaltennamen, Issue #53).
"""
import sys

MELDUNG = ("exposure_scorer.py ist historisch — die Exposition kommt aus der aufgabenbasierten Bewertung: python src/scoring/task_scorer.py → src/scoring/task_aggregate.py → src/scoring/apply_task_scores.py (siehe docs/neubewertung_lokal.md)")

if __name__ == "__main__":
    sys.exit(MELDUNG)
