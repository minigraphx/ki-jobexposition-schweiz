"""
HISTORISCH — nicht mehr verwenden (Stand Oktober 2026).

Erster Prototyp für Beschäftigtenzahlen aus der SAKE (manueller Excel-Download,
Platzhalterdaten).

Beschäftigte und Frauenanteil stammen aus der BFS Strukturerhebung (SE) 2024 über
src/data/update_from_bfs.py und data/processed/beruf_berufsart_mapping.csv (#51).

Der frühere Code ist in der Git-Historie erhalten (letzte Fassung vor der Umstellung auf die
aufgabenbasierten Scores und englische Spaltennamen, Issue #53).
"""
import sys

MELDUNG = ("fetch_sake.py ist historisch — Beschäftigte: python src/data/update_from_bfs.py")

if __name__ == "__main__":
    sys.exit(MELDUNG)
