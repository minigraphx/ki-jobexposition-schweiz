"""
CSV-Spalten in data/processed/ auf englische Namen umstellen (Issue #53).

Die Zuordnung alt → neu steht zentral in column_mapping.py. Je CSV-Datei:

- alle Spalten neu (bzw. Namen ohne Änderung) → «bereits migriert», Datei bleibt unangetastet
- alle Spalten alt → umbenennen; in scores.csv zusätzlich die Spalten der früheren Methode
  entfernen (column_mapping.ENTFERNT). Bei reiner Umbenennung wird nur die Kopfzeile neu
  geschrieben, der Rest der Datei bleibt byte-identisch.
- unbekannte Spalten, gemischte alte/neue Namen oder Dateien ohne Mapping → Abbruch, bevor
  irgendeine Datei geschrieben wird

Nach dem Schreiben wird jede Datei neu gelesen und Zelle für Zelle mit dem Original
verglichen (gleiche Zeilen, gleiche Werte je umbenannter Spalte); bei Abweichung wird das
Original wiederhergestellt und abgebrochen.

Aufruf:
    python src/data/migrate_columns.py --dry-run     # Plan anzeigen, nichts schreiben
    python src/data/migrate_columns.py               # migrieren (idempotent)
    python src/data/migrate_columns.py --data-dir PFAD
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import column_mapping as cm  # noqa: E402

PROCESSED_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "processed"

BEREITS = "bereits migriert"
MIGRIEREN = "migrieren"


class MigrationsFehler(RuntimeError):
    """Datei passt nicht zum Mapping oder Zellwerte weichen nach dem Schreiben ab."""


@dataclass
class Plan:
    datei: str
    status: str
    kopf: list[str]
    umbenennen: dict[str, str] = field(default_factory=dict)
    entfernen: list[str] = field(default_factory=list)

    @property
    def neuer_kopf(self) -> list[str]:
        return [self.umbenennen.get(s, s) for s in self.kopf if s not in self.entfernen]


def lies_kopf(path: Path) -> list[str]:
    with path.open(encoding="utf-8", newline="") as f:
        return next(csv.reader(f), [])


def plane(path: Path) -> Plan:
    """Plan für eine Datei; MigrationsFehler bei unbekannter Datei oder unbekannten Spalten."""
    name = path.name
    if name not in cm.SPALTEN:
        raise MigrationsFehler(f"{name}: keine Zuordnung in column_mapping.py")
    kopf = lies_kopf(path)
    if len(set(kopf)) != len(kopf):
        raise MigrationsFehler(f"{name}: doppelte Spaltennamen {kopf}")
    neu, alt, nur_alt = cm.neue_spalten(name), cm.alte_spalten(name), cm.nur_alt(name)
    if set(kopf) <= neu and not set(kopf) & nur_alt:
        return Plan(name, BEREITS, kopf)
    unbekannt = [s for s in kopf if s not in alt]
    if unbekannt:
        art = "gemischte alte und neue Namen" if set(unbekannt) <= neu else "unbekannte Spalten"
        raise MigrationsFehler(f"{name}: {art}: {unbekannt}")
    entfernen = [s for s in kopf if s in cm.ENTFERNT.get(name, ())]
    umbenennen = {s: cm.SPALTEN[name][s] for s in kopf if s not in entfernen and cm.SPALTEN[name][s] != s}
    plan = Plan(name, MIGRIEREN, kopf, umbenennen, entfernen)
    if len(set(plan.neuer_kopf)) != len(plan.neuer_kopf):
        raise MigrationsFehler(f"{name}: Umbenennung ergibt doppelte Spalten {plan.neuer_kopf}")
    return plan


def _lesen(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _kopfzeile(spalten: list[str]) -> str:
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerow(spalten)
    return buf.getvalue()


def schreibe(path: Path, plan: Plan) -> None:
    """Datei gemäss Plan schreiben und gegen das Original prüfen (bei Fehler zurücksetzen)."""
    original = path.read_bytes()
    alt = _lesen(path)
    if plan.entfernen:
        alt.drop(columns=plan.entfernen).rename(columns=plan.umbenennen).to_csv(path, index=False)
    else:
        text = original.decode("utf-8")
        ende = text.index("\n") + 1 if "\n" in text else len(text)
        path.write_bytes((_kopfzeile(plan.neuer_kopf) + text[ende:]).encode("utf-8"))
    try:
        pruefe(path, alt, plan)
    except MigrationsFehler:
        path.write_bytes(original)
        raise


def pruefe(path: Path, alt: pd.DataFrame, plan: Plan) -> None:
    """Gleiche Zeilenzahl und Zellwerte je (umbenannter) Spalte wie im Original."""
    neu = _lesen(path)
    if list(neu.columns) != plan.neuer_kopf:
        raise MigrationsFehler(f"{plan.datei}: Kopfzeile nach dem Schreiben {list(neu.columns)}")
    if len(neu) != len(alt):
        raise MigrationsFehler(f"{plan.datei}: {len(alt)} → {len(neu)} Zeilen")
    for s in plan.kopf:
        if s in plan.entfernen:
            continue
        if not neu[plan.umbenennen.get(s, s)].equals(alt[s]):
            raise MigrationsFehler(f"{plan.datei}: Werte der Spalte {s} verändert")


def migriere(pfad: Path, dry_run: bool = False) -> list[Plan]:
    """Alle CSVs im Verzeichnis planen; nur wenn alle zulässig sind, schreiben."""
    plaene = [plane(p) for p in sorted(pfad.glob("*.csv"))]
    for plan in plaene:
        if plan.status == BEREITS:
            print(f"= {plan.datei}: {BEREITS} ({len(plan.kopf)} Spalten)")
            continue
        teile = [f"{a} → {n}" for a, n in plan.umbenennen.items()]
        print(f"→ {plan.datei}: {len(plan.umbenennen)} umbenennen, {len(plan.entfernen)} entfernen")
        for t in teile:
            print(f"    {t}")
        if plan.entfernen:
            print(f"    entfernt: {', '.join(plan.entfernen)}")
    if not dry_run:
        for plan in plaene:
            if plan.status == MIGRIEREN:
                schreibe(pfad / plan.datei, plan)
        n = sum(p.status == MIGRIEREN for p in plaene)
        print(f"✓ {n} Dateien migriert, Zellwerte geprüft")
    else:
        print("--dry-run: nichts geschrieben")
    return plaene


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="Plan anzeigen, nichts schreiben")
    ap.add_argument("--data-dir", dest="pfad", type=Path, default=PROCESSED_PATH, help="Verzeichnis der CSVs")
    a = ap.parse_args(argv)
    try:
        migriere(a.pfad, a.dry_run)
    except MigrationsFehler as exc:
        print(f"FEHLER: {exc} — abgebrochen (betroffene Datei unverändert)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
