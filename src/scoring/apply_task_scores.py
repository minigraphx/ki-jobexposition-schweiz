"""
Aufgabenbasierte Scores in scores.csv übernehmen (letzter Schritt vor der App).

Liest data/processed/scores_aufgaben.csv (task_aggregate.py) und schreibt scores.csv mit genau
dem Schema column_mapping.SCORES_SCHEMA:

    Stammdaten | Expositions-Block (aus scores_aufgaben.csv, Zellen unverändert übernommen)
    | timeframe_raw, large_firm_share, timeframe_sme_shift, timeframe | adaptability | legacy_score

- Zuordnung über (isco_code, occupation). Fehlt für einen Eintrag von scores.csv eine Bewertung
  (keine Zeile oder leeres exposure) oder enthält scores_aufgaben.csv Einträge, die es in
  scores.csv nicht gibt, bricht das Skript ab (erst task_scorer.py / task_aggregate.py laufen
  lassen).
- timeframe_raw = aggregierter Zeitrahmen der Bewertungen (Median über alle Läufe);
  timeframe = timeframe_raw, um den KMU-Adoptions-Faktor der Branche verschoben
  (kmu_faktor.adjust_zeitrahmen_fuer_kmu, Daten kmu_anteil_branche.csv).
- adaptability wird neu berechnet (adaptability_scorer: Qualifikation, Lohn, exposure als
  Digital-Proxy, Branchenmobilität).
- legacy_score = Endscore der früheren Methode (nur für den Vergleich alt/neu auf der
  Methodik-Seite); bleibt, wie er ist.
Die Branche wirkt nur über den Zeitrahmen; einen Lohn- oder Branchenzuschlag auf den Score gibt
es nicht mehr.

Idempotent: ein zweiter Lauf schreibt dieselben Bytes.

Aufruf:
    python src/scoring/apply_task_scores.py             # scores.csv schreiben
    python src/scoring/apply_task_scores.py --dry-run   # nur prüfen und Änderungen zählen
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
import column_mapping as cm  # noqa: E402
import kmu_faktor as kf  # noqa: E402
from adaptability_scorer import setze_adaptabilitaet  # noqa: E402

PROCESSED_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "processed"
SCORES_CSV = PROCESSED_PATH / "scores.csv"
AUFGABEN_CSV = PROCESSED_PATH / "scores_aufgaben.csv"
KMU_CSV = PROCESSED_PATH / "kmu_anteil_branche.csv"
SCHLUESSEL = ["isco_code", "occupation"]


class FehlendeBewertung(ValueError):
    """Ein Eintrag von scores.csv hat keine aufgabenbasierte Bewertung (oder umgekehrt)."""


def _lesen(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _fmt_anteil(v) -> str:
    return "" if v is None or pd.isna(v) else repr(float(v))


def uebernehmen(scores: pd.DataFrame, aufgaben: pd.DataFrame, kmu: pd.DataFrame) -> pd.DataFrame:
    """scores.csv (Text) + scores_aufgaben.csv (Text) + KMU-Tabelle → neue scores.csv (Text)."""
    fehlend = [s for s in cm.SCORES_STAMMDATEN if s not in scores.columns]
    if fehlend:
        raise ValueError(f"scores.csv: Stammdaten-Spalten fehlen: {fehlend}")
    fehlend = [s for s in SCHLUESSEL + cm.SCORES_EXPOSITION + ["timeframe"] if s not in aufgaben.columns]
    if fehlend:
        raise ValueError(f"scores_aufgaben.csv: Spalten fehlen: {fehlend}")
    for name, df in (("scores.csv", scores), ("scores_aufgaben.csv", aufgaben)):
        doppelt = df[df.duplicated(SCHLUESSEL, keep=False)]
        if not doppelt.empty:
            raise ValueError(f"{name}: doppelte Einträge {doppelt[SCHLUESSEL].values.tolist()}")
    kf.pruefe_branchen(scores["sector"])

    a = aufgaben.set_index(SCHLUESSEL)
    s_keys = pd.MultiIndex.from_frame(scores[SCHLUESSEL])
    ohne = [k for k in s_keys if k not in a.index or a.at[k, "exposure"] == ""]
    if ohne:
        raise FehlendeBewertung(
            f"{len(ohne)} Einträge ohne aufgabenbasierte Bewertung (erst task_scorer.py und "
            f"task_aggregate.py ausführen): {[' '.join(k) for k in ohne[:10]]}")
    bekannt = set(s_keys)
    fremd = [k for k in a.index if k not in bekannt]
    if fremd:
        raise FehlendeBewertung(
            f"scores_aufgaben.csv enthält {len(fremd)} Einträge, die nicht in scores.csv stehen "
            f"(task_aggregate.py neu ausführen): {[' '.join(k) for k in fremd[:10]]}")

    out = scores[cm.SCORES_STAMMDATEN].copy()
    zeilen = a.loc[s_keys]
    for s in cm.SCORES_EXPOSITION:
        out[s] = zeilen[s].to_numpy()
    zeit = kf.adjust_zeitrahmen_fuer_kmu(
        pd.DataFrame({"sector": out["sector"], "timeframe_raw": zeilen["timeframe"].to_numpy()},
                     index=out.index), kmu_df=kmu)
    out["timeframe_raw"] = zeit["timeframe_raw"]
    out["large_firm_share"] = zeit["large_firm_share"].map(_fmt_anteil)
    out["timeframe_sme_shift"] = zeit["timeframe_sme_shift"].astype(int).astype(str)
    out["timeframe"] = zeit["timeframe"]
    if "adaptability" in scores.columns:
        out["adaptability"] = scores["adaptability"]
    out = setze_adaptabilitaet(out)
    out["legacy_score"] = scores["legacy_score"] if "legacy_score" in scores.columns else ""
    return out[cm.SCORES_SCHEMA]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scores", type=Path, default=SCORES_CSV)
    ap.add_argument("--aufgaben", type=Path, default=AUFGABEN_CSV, help="scores_aufgaben.csv")
    ap.add_argument("--kmu", type=Path, default=KMU_CSV, help="kmu_anteil_branche.csv")
    ap.add_argument("--dry-run", action="store_true", help="nichts schreiben")
    a = ap.parse_args(argv)

    scores, aufgaben = _lesen(a.scores), _lesen(a.aufgaben)
    kmu = kf.lade_kmu(a.kmu)
    if kmu is None:
        print(f"FEHLER: {a.kmu} fehlt (python src/data/fetch_statent.py --offline)", file=sys.stderr)
        return 1
    try:
        neu = uebernehmen(scores, aufgaben, kmu)
    except ValueError as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 1
    alt_text = a.scores.read_text(encoding="utf-8")
    neu_text = neu.to_csv(index=False)
    gleich = alt_text == neu_text
    print(f"✓ {len(neu)} Einträge, {len(neu.columns)} Spalten; exposure Ø {pd.to_numeric(neu['exposure']).mean():.2f}, "
          f"uncertain {int((neu['uncertain'] == 'True').sum())}; "
          f"Zeitrahmen verschoben: {int((neu['timeframe_sme_shift'] != '0').sum())}")
    if gleich:
        print("= scores.csv unverändert")
    elif a.dry_run:
        print("--dry-run: scores.csv würde sich ändern, nicht geschrieben")
    else:
        a.scores.write_text(neu_text, encoding="utf-8")
        print(f"Gespeichert: {a.scores}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
