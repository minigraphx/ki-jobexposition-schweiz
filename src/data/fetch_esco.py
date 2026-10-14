"""
HISTORISCH — nicht mehr verwenden (Stand Oktober 2026).

Erster Prototyp der ESCO-Abfrage (nur Titelsuche, englische Beschreibung, ohne
ISCO-Prüfung und ohne feste ESCO-Version).

Ersetzt durch src/data/enrich_with_esco.py (sechs Stufen, ESCO v1.2.1, harte
ISCO-Konsistenzprüfung, ESCO-Audit #52).

Der frühere Code ist in der Git-Historie erhalten (letzte Fassung vor der Umstellung auf die
aufgabenbasierten Scores und englische Spaltennamen, Issue #53).
"""
import sys

MELDUNG = ("fetch_esco.py ist historisch — ESCO-Zuordnung: python src/data/enrich_with_esco.py")

if __name__ == "__main__":
    sys.exit(MELDUNG)
