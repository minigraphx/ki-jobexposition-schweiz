"""
HISTORISCH — einmalige Migration (Issue #51, Oktober 2026), bereits angewendet.

Das Skript korrigierte ISCO-Codes (ISCO_KORREKTUREN, unten als Referenz erhalten — ein Test
prüft, dass die Korrekturen in den Daten stehen) und legte Berufe zusammen, die die
Strukturerhebung nicht trennt (Spalten merged_from / text_from in
data/processed/beruf_berufsart_mapping.csv). Für zusammengelegte Einträge bildete es die Scores
der früheren Methode als beschäftigungsgewichtetes Mittel (Spalten score_gesamt …,
scores_gemittelt, beschreibung_hash).

Diese Spalten gibt es seit der Umstellung auf die aufgabenbasierten Scores nicht mehr: alle
Einträge, auch die zusammengelegten, sind als Ganzes neu bewertet (task_scorer.py →
task_aggregate.py → apply_task_scores.py). Der Migrationscode ist in der Versionsgeschichte
des Repositorys erhalten. Neue Zusammenlegungen: Mapping-Zeile pflegen, update_from_bfs.py,
update_loehne.py --offline, danach aufgabenbasiert bewerten.
"""

import sys

# occupation (Titel vor #51) → (alter Code, neuer Code); Begründungen in docs/audit_isco_codes.md
ISCO_KORREKTUREN: dict[str, tuple[str, str]] = {
    "Koch/Köchin EFZ": ("3434", "5120"),
    "Chemielaborant/in EFZ": ("3113", "3111"),
    "Drogist/in": ("3256", "5223"),
    "Hauswirtschaftler/in EFZ": ("5131", "5151"),
    "Hotelfachmann/-frau EFZ": ("5131", "5151"),
    "Buchhalter/in": ("2411", "3313"),
    "Treuhänder/in": ("2412", "2411"),
    "Steuerberater/in": ("2412", "2411"),
    "Vermögensverwalter/in / Wealth Manager": ("2413", "2412"),
    "Bankkaufmann/-frau": ("3311", "4211"),
    "Logistiker/in EFZ": ("3331", "4321"),
    "Polizist/in": ("3355", "5412"),
    "Bauführer/in": ("3123", "3112"),
    "Hochbauzeichner/in EFZ": ("3112", "3118"),
    "Polymechaniker/in EFZ": ("7223", "7200"),
    "Automatiker/in EFZ": ("3115", "7412"),
    "Landwirt/in EFZ": ("6111", "6130"),
    "Journalist/in / Redakteur/in": ("2641", "2642"),
    "Kassierer/in": ("5223", "5230"),
    "Sachbearbeiter/in öff. Verwaltung": ("4416", "4110"),
    "Produktionsmitarbeiter/in (Pharma)": ("8211", "8131"),
}

MELDUNG = ("berufe_zusammenlegen.py ist historisch (Migration #51 bereits angewendet) — Mapping in "
           "data/processed/beruf_berufsart_mapping.csv pflegen, dann update_from_bfs.py und die "
           "aufgabenbasierte Bewertung (docs/neubewertung_lokal.md).")

if __name__ == "__main__":
    sys.exit(MELDUNG)
