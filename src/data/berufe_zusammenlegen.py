"""
ISCO-Code-Korrekturen und Zusammenlegungen (Issue #51) auf die CSVs anwenden.

Einmalige Migration, als Referenz versioniert (wie fix_brennschneider_contamination.py).
Quelle der Zusammenlegungen ist data/processed/beruf_berufsart_mapping.csv
(Spalten zusammengelegt_aus, text_von); die Code-Korrekturen stehen in ISCO_KORREKTUREN,
Begründungen in docs/audit_isco_codes.md.

1. ISCO-Code-Korrekturen (nur hohe Sicherheit) in allen vier CSVs.
2. Zusammenlegungen: Berufe, die nach der Korrektur dieselbe Berufsgattung bzw. Berufsart
   belegen und sich mit den SE-Berufsarten nicht trennen lassen, werden zu einem Eintrag:
   - beruf = SE-Bezeichnung, bisherige CH-Titel → Spalte synonyme (setzt update_from_bfs.py)
   - Texte, ESCO-Felder, Branche, Qualifikation, Zeitrahmen: vom Teilberuf `text_von`
     (grösster Teilberuf nach bisheriger beschaeftigte_1000 in scores.csv)
   - scores.csv: score_gesamt und die fünf Teil-Scores = beschäftigungsgewichtetes Mittel der
     Teilberufe (Gewichte = bisherige beschaeftigte_1000 in scores.csv), auf 0.1 gerundet —
     vorläufig: scores_gemittelt = True und beschreibung_hash leer, damit
     exposure_scorer.py den Eintrag beim nächsten Lauf neu bewertet.
   Regelbasierte Folgespalten (delta_branche, delta_lohn, score_ch, adaptabilitaet) berechnet
   danach update_loehne.py neu.
Idempotent: bereits angewendete Korrekturen/Zusammenlegungen werden übersprungen.

Danach:
    python src/data/update_from_bfs.py          # Beschäftigte, Frauenanteil, Synonyme
    python src/data/update_loehne.py --offline  # Löhne (neue Gewichte) + Folgespalten

Aufruf:
    python src/data/berufe_zusammenlegen.py [--dry-run]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from update_from_bfs import CSV_DATEIEN, MAPPING_CSV, PROCESSED_PATH, _liste, lade_mapping

# beruf → (alter Code, neuer Code)
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

SCORE_SPALTEN = ["score_gesamt", "score_digital", "score_wiederholbarkeit",
                 "score_physisch", "score_kreativitaet", "score_sozial"]
SCORES_DATEI = "scores.csv"
MARKER = "scores_gemittelt"


def _lesen(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def codes_korrigieren(df: pd.DataFrame) -> int:
    n = 0
    for beruf, (alt, neu) in ISCO_KORREKTUREN.items():
        sel = (df["beruf"] == beruf) & (df["isco_code"].str.strip() == alt)
        df.loc[sel, "isco_code"] = neu
        n += int(sel.sum())
    return n


def gewichtetes_mittel(werte: list[float], gewichte: list[float]) -> float:
    summe = sum(gewichte)
    if summe <= 0:
        return round(sum(werte) / len(werte), 1)
    return round(sum(w * g for w, g in zip(werte, gewichte)) / summe, 1)


def zusammenlegen(df: pd.DataFrame, mapping: pd.DataFrame, scores: bool) -> list[str]:
    """Zusammenlegungen aus dem Mapping anwenden; gibt die Protokollzeilen zurück."""
    log = []
    if scores and MARKER not in df.columns:
        df[MARKER] = "False"
    for _, m in mapping[mapping["zusammengelegt_aus"] != ""].iterrows():
        teile = _liste(m["zusammengelegt_aus"])
        vorhanden = [t for t in teile if t in set(df["beruf"])]
        if set(vorhanden) <= {m["beruf"]}:
            continue  # bereits zusammengelegt (nur noch der Zieleintrag vorhanden)
        if m["text_von"] not in vorhanden:
            raise ValueError(f"{m['beruf']}: text_von «{m['text_von']}» fehlt")
        idx_text = df.index[df["beruf"] == m["text_von"]][0]
        neu = df.loc[idx_text].copy()
        neu["beruf"], neu["isco_code"] = m["beruf"], m["isco_code"]
        teil_df = df[df["beruf"].isin(vorhanden)]
        if scores:
            gew = pd.to_numeric(teil_df["beschaeftigte_1000"], errors="coerce").fillna(0.0).tolist()
            for spalte in SCORE_SPALTEN:
                werte = pd.to_numeric(teil_df[spalte], errors="coerce").tolist()
                neu[spalte] = repr(gewichtetes_mittel(werte, gew))
            neu["beschreibung_hash"] = ""
            neu[MARKER] = "True"
            details = ", ".join(f"{b} ({g:g})" for b, g in zip(teil_df["beruf"], gew))
            log.append(f"{m['isco_code']} {m['beruf']} ← {details}; "
                       f"score_gesamt {neu['score_gesamt']}")
        df.loc[idx_text] = neu
        df.drop(index=[i for i in teil_df.index if i != idx_text], inplace=True)
    df.reset_index(drop=True, inplace=True)
    return log


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dry-run", action="store_true", help="Änderungen nur anzeigen")
    parser.add_argument("--pfad", type=Path, default=PROCESSED_PATH, help="Verzeichnis der CSVs")
    args = parser.parse_args(argv)
    mapping = lade_mapping(args.pfad / MAPPING_CSV.name)
    for name in CSV_DATEIEN:
        path = args.pfad / name
        if not path.exists():
            print(f"– {name}: nicht vorhanden, übersprungen")
            continue
        df = _lesen(path)
        n_vorher = len(df)
        n_codes = codes_korrigieren(df)
        log = zusammenlegen(df, mapping, scores=(name == SCORES_DATEI))
        print(f"✓ {name}: {n_codes} ISCO-Codes korrigiert, {n_vorher} → {len(df)} Berufe")
        for zeile in log:
            print(f"    {zeile}")
        if not args.dry_run:
            df.to_csv(path, index=False)


if __name__ == "__main__":  # pragma: no cover
    main()
