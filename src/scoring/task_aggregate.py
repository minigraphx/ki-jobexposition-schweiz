"""Aggregation der API-Bewertungen (Rubrik v2.2) → data/processed/scores_aufgaben.csv.

Liest je Provider alle Läufe ``data/processed/bewertungen/<provider>/run*/*.json``, verwendet nur
gültige Bewertungen (Status ok, Schema + Plausibilität, aktueller Input-Hash) und berechnet je
Lauf die Kennzahlen (task_rubrik.kennzahlen; Logik wie Pilot-Auswertung v2.1). Danach:

- je Provider: Mittel über dessen Läufe, Spannweite des ζ-Scores (spread_runs_<provider>)
- kombiniert: Mittel über alle gültigen Läufe beider Provider (exposure = 10·ζ usw.)
- delta_provider = |ζ-Score Claude − ζ-Score Gemini|
- uncertain, wenn delta_provider > PROVIDER_SCHWELLE, eine Läufe-Spannweite > LAEUFE_SCHWELLE
  oder insgesamt weniger als 2 gültige Läufe vorliegen (Grund in uncertain_reason)
- timeframe = Median über alle Läufe (bei Gleichstand der spätere Wert); haupt_risiko und
  begruendung aus dem Lauf, dessen ζ dem kombinierten Mittel am nächsten liegt (bei Gleichstand
  der erste: Claude vor Gemini, tiefere Laufnummer zuerst). Die Texte fliessen nicht in ζ/β ein.

Spalten «physical_automation» = 10·Σ w·1[P1, p_art physisch], «software_automation» = dasselbe für
p_art software (Pilot: score_p_physisch / score_p_software). Die Spaltennamen der CSV sind englisch
(src/data/column_mapping.SCORES_AUFGABEN); intern rechnet das Skript mit den deutschen Kennzahl-Namen
aus task_rubrik.kennzahlen.

Aufruf:  python src/scoring/task_aggregate.py [--provider claude gemini] [--out PFAD] [--include-stale] [--base-dir PFAD]
                                             [--claude-source claude-cli|claude]
Standard ``--claude-source claude-cli``: Claude-Läufe aus dem Abo (bewertungen/claude-cli/); ``claude`` nimmt
die API-Läufe (bewertungen/claude/). Die Spalten heissen in beiden Fällen *_claude, die Herkunft steht in
claude_source und text_source. scores.csv und die App übernehmen die Werte erst mit
src/scoring/apply_task_scores.py.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
import column_mapping as cm  # noqa: E402
import task_inputs as ti  # noqa: E402
import task_rubrik as tr  # noqa: E402

PROVIDER = ("claude", "gemini")
PROVIDER_SCHWELLE = 1.0     # |Δ ζ-Score| Claude − Gemini, ab der ein Eintrag als unsicher gilt
LAEUFE_SCHWELLE = 1.0       # Spannweite des ζ-Scores innerhalb eines Providers (nach allen Läufen)

MITTEL = ["score_aufgaben", "score_aufgaben_beta", "score_zeitersparnis", "anteil_ersetzend",
          "anteil_delegierend", "anteil_unterstuetzend", "ersetzbare_zeit", "score_physisch_auto",
          "score_software_auto", "sicherheit_tief_anteil"]
SPALTEN_INTERN = (["isco_code", "beruf"] + MITTEL
           + ["zeitrahmen", "haupt_risiko", "begruendung",
              "n_laeufe_claude", "n_laeufe_gemini", "score_aufgaben_claude", "score_aufgaben_gemini",
              "score_zeitersparnis_claude", "score_zeitersparnis_gemini",
              "delta_laeufe_claude", "delta_laeufe_gemini", "delta_laeufe", "delta_provider",
              "flag_unsicher", "flag_grund", "zeitrahmen_claude", "zeitrahmen_gemini", "text_quelle",
              "claude_quelle", "rubrik_version"])
SPALTEN = [cm.SCORES_AUFGABEN[s] for s in SPALTEN_INTERN]     # Spalten von scores_aufgaben.csv
CLAUDE_QUELLEN = ("claude-cli", "claude")     # Verzeichnis der Claude-Läufe: Abo (claude -p, Standard) bzw. API


@dataclass
class Lauf:
    """Eine gültige Bewertung eines Eintrags (ein Provider, ein Lauf)."""
    provider: str
    lauf: int
    bewertung: dict
    kz: dict

    @property
    def quelle(self) -> str:
        return f"{self.provider}/run{self.lauf}"


def _lauf_nr(name: str) -> int | None:
    try:
        return int(name.removeprefix("run").split("_")[0])
    except ValueError:
        return None


def lade_laeufe(basis: Path, provider: str, eintraege: list[ti.Eintrag], warnungen: list[str],
                auch_veraltet: bool = False) -> dict[str, list[Lauf]]:
    """Gültige Läufe je Eintrag (Schlüssel = Dateiname ohne .json)."""
    nach_datei = {e.datei: e for e in eintraege}
    res: dict[str, list[Lauf]] = {e.schluessel: [] for e in eintraege}
    pdir = basis / provider
    if not pdir.is_dir():
        return res
    for rdir in sorted(p for p in pdir.glob("run*") if p.is_dir()):
        nr = _lauf_nr(rdir.name)
        if nr is None:
            continue
        for f in sorted(rdir.glob("*.json")):
            e = nach_datei.get(f.name)
            if e is None:
                continue
            q = f"{provider}/{rdir.name}/{f.name}"
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                warnungen.append(f"{q}: nicht lesbar ({exc})")
                continue
            meta, bew = d.get("meta") or {}, d.get("bewertung")
            if meta.get("status") != "ok" or bew is None:
                warnungen.append(f"{q}: fehlgeschlagen — nicht verwendet")
                continue
            version = meta.get("rubrik_version") or tr.version_aus_bewertung(bew)
            if version not in tr.RUBRIKEN:
                warnungen.append(f"{q}: unbekannte Rubrik-Version {version}")
                continue
            if meta.get("input_hash") != e.input_hash and not auch_veraltet:
                warnungen.append(f"{q}: veraltet (Input-Hash/Rubrik geändert) — nicht verwendet")
                continue
            probleme = tr.pruefe_bewertung(bew, e.input, version)
            if probleme:
                warnungen.append(f"{q}: ungültig ({probleme[0]}) — nicht verwendet")
                continue
            res[e.schluessel].append(Lauf(provider, nr, bew, tr.kennzahlen(tr.normiere(bew, warnungen, q))))
    return res


def _mittel(werte: list[float]) -> float:
    v = [x for x in werte if x is not None and not (isinstance(x, float) and math.isnan(x))]
    return sum(v) / len(v) if v else math.nan


def _spannweite(laeufe: list[Lauf]) -> float:
    s = [x.kz["score_aufgaben"] for x in laeufe]
    return (max(s) - min(s)) if len(s) >= 2 else math.nan


def zeitrahmen_median(werte: list[str]) -> str | None:
    """Median auf der geordneten Skala; bei geradem n (Gleichstand) der spätere Wert."""
    o = sorted(tr.ZEITRAHMEN.index(w) for w in werte if w in tr.ZEITRAHMEN)
    return tr.ZEITRAHMEN[o[len(o) // 2]] if o else None


def _zeitrahmen(laeufe: list[Lauf]) -> str | None:
    return zeitrahmen_median([x.bewertung["zusammenfassung"]["zeitrahmen"]
                              for x in laeufe if "zusammenfassung" in x.bewertung])


def text_lauf(laeufe: list[Lauf], ziel: float) -> Lauf | None:
    """Lauf mit Zusammenfassung, dessen ζ-Score dem Mittel am nächsten liegt (stabil: erster gewinnt)."""
    mit = [x for x in laeufe if "zusammenfassung" in x.bewertung]
    if not mit or math.isnan(ziel):
        return None
    return min(mit, key=lambda x: abs(x.kz["score_aufgaben"] - ziel))


def zeile(e: ti.Eintrag, je_provider: dict[str, list[Lauf]]) -> dict:
    alle = [x for p in PROVIDER for x in sorted(je_provider.get(p, []), key=lambda x: x.lauf)]
    z: dict = {"isco_code": e.isco_code, "beruf": e.beruf}
    for m in MITTEL:
        z[m] = _mittel([x.kz[m] for x in alle])
    for p in PROVIDER:
        lp = je_provider.get(p, [])
        z[f"n_laeufe_{p}"] = len(lp)
        z[f"score_aufgaben_{p}"] = _mittel([x.kz["score_aufgaben"] for x in lp])
        z[f"score_zeitersparnis_{p}"] = _mittel([x.kz["score_zeitersparnis"] for x in lp])
        z[f"delta_laeufe_{p}"] = _spannweite(lp)
        z[f"zeitrahmen_{p}"] = _zeitrahmen(lp)
    spannen = [z[f"delta_laeufe_{p}"] for p in PROVIDER if not math.isnan(z[f"delta_laeufe_{p}"])]
    z["delta_laeufe"] = max(spannen) if spannen else math.nan
    a, b = z["score_aufgaben_claude"], z["score_aufgaben_gemini"]
    z["delta_provider"] = abs(a - b) if not (math.isnan(a) or math.isnan(b)) else math.nan
    gruende = []
    if len(alle) < 2:
        gruende.append(f"nur {len(alle)} gültige(r) Lauf/Läufe")
    if not math.isnan(z["delta_provider"]) and tr.ueber_schwelle(z["delta_provider"], PROVIDER_SCHWELLE):
        gruende.append(f"Provider-Abweichung {z['delta_provider']:.1f} > {PROVIDER_SCHWELLE:g}")
    if not math.isnan(z["delta_laeufe"]) and tr.ueber_schwelle(z["delta_laeufe"], LAEUFE_SCHWELLE):
        gruende.append(f"Läufe-Spannweite {z['delta_laeufe']:.1f} > {LAEUFE_SCHWELLE:g}")
    z["flag_unsicher"] = bool(gruende)
    z["flag_grund"] = "; ".join(gruende) or None
    z["zeitrahmen"] = _zeitrahmen(alle)
    t = text_lauf(alle, z["score_aufgaben"])
    z["haupt_risiko"] = t.bewertung["zusammenfassung"]["haupt_risiko"] if t else None
    z["begruendung"] = t.bewertung["zusammenfassung"]["begruendung"] if t else None
    z["text_quelle"] = t.quelle if t else None
    z["rubrik_version"] = tr.RUBRIK_VERSION
    return z


def aggregiere(eintraege: list[ti.Eintrag], laeufe: dict[str, dict[str, list[Lauf]]],
               claude_quelle: str = "claude-cli") -> pd.DataFrame:
    """laeufe: provider → (Schlüssel → Läufe). Eine Zeile je Eintrag (auch ohne Bewertung); Spalten SPALTEN."""
    zeilen = [zeile(e, {p: laeufe.get(p, {}).get(e.schluessel, []) for p in PROVIDER}) for e in eintraege]
    df = pd.DataFrame(zeilen, columns=SPALTEN_INTERN)
    df["claude_quelle"] = [claude_quelle if n else None for n in df["n_laeufe_claude"]]
    return df.rename(columns=cm.SCORES_AUFGABEN)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--provider", nargs="+", choices=PROVIDER, default=list(PROVIDER))
    ap.add_argument("--base-dir", default=str(tr.BEWERTUNGEN_DIR))
    ap.add_argument("--out", default=str(tr.SCORES_AUFGABEN_PATH))
    ap.add_argument("--include-stale", action="store_true",
                    help="auch Bewertungen mit altem Input-Hash verwenden (z. B. nach Datenkorrekturen)")
    ap.add_argument("--claude-source", choices=CLAUDE_QUELLEN, default="claude-cli",
                    help="Claude-Läufe aus dem Abo (claude-cli, Standard) oder aus der API (claude)")
    a = ap.parse_args(argv)
    eintraege = ti.baue_eintraege()
    warnungen: list[str] = []
    verzeichnis = {"claude": a.claude_source, "gemini": "gemini"}
    laeufe = {p: lade_laeufe(Path(a.base_dir), verzeichnis[p], eintraege, warnungen, a.include_stale)
              for p in a.provider}
    df = aggregiere(eintraege, laeufe, a.claude_source)
    df.round(4).to_csv(a.out, index=False)
    bewertet = df["n_runs_claude"] + df["n_runs_gemini"] > 0
    print(f"{len(df)} Einträge ({int(bewertet.sum())} mit mindestens einer gültigen Bewertung) → {a.out}")
    print(f"uncertain: {int(df.loc[bewertet, 'uncertain'].sum())}")
    for w in warnungen:
        print(f"WARNUNG: {w}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
