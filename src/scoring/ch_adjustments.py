"""
HISTORISCH — nicht mehr verwenden (Stand Oktober 2026).

CH-Adjustierungen der früheren Methode: Branchen-Delta (BRANCHENEFFEKTE, Pharma-Ausnahme)
und Lohnklassen-Delta (LOHNEFFEKTE) auf score_gesamt → score_ch, dazu der KMU-Faktor auf
den Zeitrahmen.

Entscheid Oktober 2026: Der Lohnzuschlag entfällt ganz, die Branche wirkt nur noch über den
Adoptions-Zeitrahmen. Die KMU-Logik (Schwellen, Verschiebung) liegt jetzt in
src/scoring/kmu_faktor.py und wird von apply_task_scores.py und fetch_statent.py verwendet;
die Liste der 21 Branchen ist kmu_faktor.BRANCHEN.

Der frühere Code ist in der Git-Historie erhalten (letzte Fassung vor der Umstellung auf die
aufgabenbasierten Scores und englische Spaltennamen, Issue #53).
"""
import sys

MELDUNG = ("ch_adjustments.py ist historisch — KMU-Faktor: src/scoring/kmu_faktor.py; Scores: python src/scoring/task_scorer.py → src/scoring/task_aggregate.py → src/scoring/apply_task_scores.py (siehe docs/neubewertung_lokal.md)")

if __name__ == "__main__":
    sys.exit(MELDUNG)
