"""Vergleichsbericht: Pilot (Abo-Läufe, Rubrik v2.1) vs. API-Claude vs. API-Gemini (Rubrik v2.2).

- 15 Pilotberufe: ζ-Score (10·ζ), Zeitersparnis und Δ je Quelle, Spearman ρ zwischen den Quellen
- Spearman ρ gegen externe Benchmarks (data/processed/benchmarks_isco4.csv: ILO 2025,
  Eloundou et al. β, AEI observed exposure) — für die Pilotberufe und für alle bewerteten Einträge

v2.2 unterscheidet sich von v2.1 nur durch den Block «zusammenfassung», der nicht in die
Kennzahlen einfliesst; die ζ-Scores sind daher direkt vergleichbar.

Aufruf:
    python src/scoring/task_vergleich.py
    python src/scoring/task_vergleich.py --pilot-runs pfad/run1_v21 pfad/run2_v21 --out bericht.md
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import task_aggregate as ta  # noqa: E402
import task_inputs as ti  # noqa: E402
import task_rubrik as tr  # noqa: E402

PILOT_DIR = tr.BEWERTUNGEN_DIR / "pilot_abo"
PILOT_RUNS = [PILOT_DIR / "run1_v21", PILOT_DIR / "run2_v21"]
BENCHMARKS = {"ilo25_mean": "ILO 2025 (Gmyrek et al.)", "eloundou_gpt4_beta": "Eloundou et al. 2024 (β)",
              "aei_observed_exposure": "AEI observed exposure"}
QUELLEN = {"pilot": "Pilot (Abo)", "claude": "API Claude", "gemini": "API Gemini", "kombiniert": "API kombiniert"}


def lade_pilot(runs: list[Path], eintraege: list[ti.Eintrag], warnungen: list[str]) -> dict[str, list[ta.Lauf]]:
    """Pilot-Bewertungen (rohe v2.1-JSON-Dateien) je Eintrag; Zuordnung über Name/Synonym/ISCO."""
    df = ti.lade_eintraege()
    nach_index = {(e.isco_code, e.beruf): e for e in eintraege}
    res: dict[str, list[ta.Lauf]] = {}
    for nr, rdir in enumerate(runs, 1):
        if not rdir.is_dir():
            warnungen.append(f"Pilot-Lauf fehlt: {rdir}")
            continue
        for f in sorted(rdir.glob("*.json")):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                warnungen.append(f"{rdir.name}/{f.name}: nicht lesbar ({exc})")
                continue
            version = tr.version_aus_bewertung(d)
            probleme = tr.pruefe_bewertung(d, None, version)
            if probleme:
                warnungen.append(f"{rdir.name}/{f.name}: ungültig ({probleme[0]})")
                continue
            idx, art = ti.ordne_zu(df, d["isco_code"], d["beruf"])
            if idx is None:
                warnungen.append(f"{rdir.name}/{f.name}: kein Eintrag in scores.csv für {d['isco_code']} {d['beruf']}")
                continue
            e = nach_index.get((df.at[idx, "isco_code"], df.at[idx, "beruf"]))
            if e is None:
                continue
            res.setdefault(e.schluessel, []).append(
                ta.Lauf("pilot", nr, d, tr.kennzahlen(tr.normiere(d, warnungen, f.name))))
    return res


def _m(laeufe: list[ta.Lauf], k: str) -> float:
    return ta._mittel([x.kz[k] for x in laeufe])


def tabelle(eintraege: list[ti.Eintrag], pilot: dict, api: dict[str, dict]) -> pd.DataFrame:
    zeilen = []
    for e in eintraege:
        p = pilot.get(e.schluessel, [])
        c = api.get("claude", {}).get(e.schluessel, [])
        g = api.get("gemini", {}).get(e.schluessel, [])
        z = {"isco_code": e.isco_code, "beruf": e.beruf, "n_pilot": len(p), "n_claude": len(c), "n_gemini": len(g)}
        for name, l in (("pilot", p), ("claude", c), ("gemini", g), ("kombiniert", c + g)):
            z[f"zeta_{name}"] = _m(l, "score_aufgaben")
            z[f"ersparnis_{name}"] = _m(l, "score_zeitersparnis")
            z[f"ersetzend_{name}"] = _m(l, "anteil_ersetzend")
        zeilen.append(z)
    return pd.DataFrame(zeilen)


def _f(x: float, nd: int = 1) -> str:
    return "–" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{nd}f}"


def _rho(df: pd.DataFrame, a: str, b: str) -> tuple[float, int]:
    if a not in df or b not in df:
        return math.nan, 0
    d = df[[a, b]].dropna()
    if len(d) < 3:
        return math.nan, len(d)
    # Spearman = Pearson auf Rängen (ohne scipy-Abhängigkeit)
    return float(d[a].rank().corr(d[b].rank())), len(d)


def _diff(df: pd.DataFrame, a: str, b: str) -> tuple[float, float]:
    d = (df[a] - df[b]).dropna()
    return (float(d.mean()), float(d.abs().mean())) if len(d) else (math.nan, math.nan)


def bericht(pilot_df: pd.DataFrame, alle_df: pd.DataFrame, bench: pd.DataFrame | None,
            warnungen: list[str], pilot_quellen: list[Path]) -> str:
    z = ["# Vergleich aufgabenbasierte Bewertung: Pilot (Abo) vs. API", "",
         f"Rubrik: Pilot v2.1, API v{tr.RUBRIK_VERSION} (v2.2 = v2.1 + Block «zusammenfassung», der nicht in die "
         "Kennzahlen einfliesst). ζ-Score = 10·Σ w·1[E1 oder E2]; Zeitersparnis-Score = 10·Σ w·1[E1/E2]·(1 − Restzeit).",
         "", f"Pilot-Läufe: {', '.join(p.name for p in pilot_quellen) or '–'} · "
         f"Einträge mit API-Bewertung: Claude {int((alle_df['n_claude'] > 0).sum())}, "
         f"Gemini {int((alle_df['n_gemini'] > 0).sum())} von {len(alle_df)}", ""]

    z += ["## Pilotberufe (15): ζ-Score je Quelle", "",
          "| ISCO | Beruf | Pilot | Claude | Gemini | kombiniert | Δ Claude−Pilot | Δ Gemini−Pilot | Δ Claude−Gemini | "
          "Zeitersparnis P / C / G | Läufe P/C/G |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in pilot_df.sort_values("zeta_pilot", ascending=False, na_position="last").iterrows():
        z.append(f"| {r.isco_code} | {r.beruf} | {_f(r.zeta_pilot)} | {_f(r.zeta_claude)} | {_f(r.zeta_gemini)} | "
                 f"{_f(r.zeta_kombiniert)} | {_f(r.zeta_claude - r.zeta_pilot)} | {_f(r.zeta_gemini - r.zeta_pilot)} | "
                 f"{_f(r.zeta_claude - r.zeta_gemini)} | {_f(r.ersparnis_pilot)} / {_f(r.ersparnis_claude)} / "
                 f"{_f(r.ersparnis_gemini)} | {r.n_pilot}/{r.n_claude}/{r.n_gemini} |")
    z.append("")

    z += ["## Übereinstimmung zwischen den Quellen (Pilotberufe)", "",
          "| Paar | n | Spearman ρ (ζ) | mittlere Differenz | MAE | ρ (Zeitersparnis) |", "|---|---|---|---|---|---|"]
    for a, b in (("claude", "pilot"), ("gemini", "pilot"), ("claude", "gemini"), ("kombiniert", "pilot")):
        rz, n = _rho(pilot_df, f"zeta_{a}", f"zeta_{b}")
        md, mae = _diff(pilot_df, f"zeta_{a}", f"zeta_{b}")
        re_, _ = _rho(pilot_df, f"ersparnis_{a}", f"ersparnis_{b}")
        z.append(f"| {QUELLEN[a]} – {QUELLEN[b]} | {n} | {_f(rz, 2)} | {_f(md, 2)} | {_f(mae, 2)} | {_f(re_, 2)} |")
    z.append("")

    if bench is not None:
        for titel, df, quellen in (("Pilotberufe", pilot_df, ("pilot", "claude", "gemini", "kombiniert")),
                                   ("alle bewerteten Einträge", alle_df, ("claude", "gemini", "kombiniert"))):
            d = df.merge(bench, on="isco_code", how="left")
            z += [f"## Spearman ρ gegen externe Benchmarks — {titel}", "",
                  "| Benchmark | " + " | ".join(f"{QUELLEN[q]} ζ (n)" for q in quellen) + " |",
                  "|---|" + "---|" * len(quellen)]
            for col, name in BENCHMARKS.items():
                zellen = []
                for q in quellen:
                    r, n = _rho(d, f"zeta_{q}", col)
                    zellen.append(f"{_f(r, 2)} ({n})")
                z.append(f"| {name} | " + " | ".join(zellen) + " |")
            z.append("")
        z += ["Benchmarks: ILO 2025 (CC BY 4.0), Eloundou et al. 2024 (MIT), Anthropic Economic Index (CC-BY); "
              "siehe data/processed/benchmarks_isco4.README.md.", ""]

    if warnungen:
        z += ["## Warnungen", ""] + [f"- {w}" for w in warnungen] + [""]
    return "\n".join(z)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pilot-runs", nargs="*", default=[str(p) for p in PILOT_RUNS],
                    help="Verzeichnisse der Pilot-Abo-Läufe (leer = ohne Pilot)")
    ap.add_argument("--basis", default=str(tr.BEWERTUNGEN_DIR))
    ap.add_argument("--benchmark", default=str(tr.BENCHMARK_PATH), help="'' = ohne Benchmark-Vergleich")
    ap.add_argument("--out", default=str(tr.BEWERTUNGEN_DIR / "vergleich.md"))
    ap.add_argument("--auch-veraltet", action="store_true")
    a = ap.parse_args(argv)

    warnungen: list[str] = []
    eintraege = ti.baue_eintraege()
    pilot_e = ti.baue_eintraege(pilot=True)
    runs = [Path(p) for p in a.pilot_runs if p]
    pilot = lade_pilot(runs, eintraege, warnungen)
    api = {p: ta.lade_laeufe(Path(a.basis), p, eintraege, warnungen, a.auch_veraltet) for p in ta.PROVIDER}
    alle_df = tabelle(eintraege, pilot, api)
    pilot_keys = {e.schluessel for e in pilot_e}
    pilot_df = alle_df[[ti.Eintrag(r.isco_code, r.beruf, {}, "").schluessel in pilot_keys
                        for r in alle_df.itertuples()]]
    bench = None
    if a.benchmark and Path(a.benchmark).is_file():
        bench = pd.read_csv(a.benchmark, dtype={"isco_code": str})
    elif a.benchmark:
        warnungen.append(f"Benchmark-Datei fehlt: {a.benchmark}")
    text = bericht(pilot_df, alle_df, bench, warnungen, [p for p in runs if p.is_dir()])
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"Vergleich → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
