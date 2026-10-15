"""Input-Builder für die aufgabenbasierte Bewertung (Rubrik v2.2).

Erzeugt je Eintrag in ``data/processed/scores.csv`` die Input-Datei im Format des Pilots
(Stammdaten, ESCO-Beschreibung, wesentliche Kompetenzen mit Typ skill/knowledge, optionale
Skills, Datenlage-Hinweis). Aus scores.csv werden nur Stammdaten gelesen, keine Scores.
Kompetenzen stammen aus ``data/processed/esco_kompetenzen.csv`` (kein Netzzugriff).

Aufruf (optional, zur Ansicht — der Scorer baut die Inputs selbst):
    python src/scoring/task_inputs.py                       # alle → data/processed/bewertungen/input/
    python src/scoring/task_inputs.py --pilot               # nur die 15 Pilotberufe
    python src/scoring/task_inputs.py --only 2411 2512 --out /tmp/inputs
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import task_rubrik as tr  # noqa: E402

# Spalte in scores.csv → interner Schlüssel. Die internen (deutschen) Schlüssel bilden den
# Input-Datensatz und gehen in den Input-Hash ein; sie dürfen sich nicht ändern, sonst veralten
# alle gespeicherten Bewertungen (tests/test_input_hash.py). Die CSV-Spalten heissen seit #53
# englisch (src/data/column_mapping.py); die Zuordnung hier ist bewusst ausgeschrieben.
STAMMDATEN_SPALTEN: dict[str, str] = {
    "occupation": "beruf", "isco_code": "isco_code", "synonyms": "synonyme", "qualification": "qualifikation",
    "sector": "branche", "esco_uri": "esco_uri", "esco_title": "esco_titel",
    "esco_description": "esco_beschreibung", "description_source": "beschreibung_quelle",
    "esco_match_quality": "esco_match_qualitaet", "esco_isco_code": "esco_isco_code",
}
STAMMDATEN = list(STAMMDATEN_SPALTEN.values())
# esco_kompetenzen.csv: Spalte → interner Schlüssel
KOMPETENZ_SPALTEN: dict[str, str] = {
    "occupation": "beruf", "isco_code": "isco_code", "esco_uri": "esco_uri", "competence": "kompetenz",
    "relation": "relation", "type": "typ", "competence_uri": "kompetenz_uri",
}

# Die 15 Berufe des Pilots (isco_code, Berufsname im Pilot). Mehrere Namen wurden nach dem
# Pilot umbenannt; die Zuordnung zu scores.csv erfolgt über Name → Synonym → einziger ISCO-Eintrag.
PILOT_BERUFE: list[tuple[str, str]] = [
    ("2166", "Grafiker/in"),
    ("2211", "Arzt/Ärztin (Allgemeinmedizin)"),
    ("2221", "Dipl. Pflegefachperson"),
    ("2341", "Primarlehrer/in"),
    ("2411", "Buchhalter/in"),
    ("2431", "Fachkräfte in Marketing und Werbung"),
    ("2512", "Softwareentwickler/in"),
    ("2642", "Journalisten"),
    ("2643", "Übersetzer, Dolmetscher und andere Linguisten"),
    ("3353", "Fachkräfte in Sozialverwaltung und -versicherung"),
    ("4110", "Kaufmann/-frau EFZ (allg. Richtung)"),
    ("5223", "Detailhandelsfachmann/-frau EFZ"),
    ("7411", "Elektriker/in EFZ"),
    ("8332", "Lastwagenfahrer/in"),
    ("9313", "Hilfsarbeiter im Hochbau"),
]

# Kuratierte Hinweise zur Datenlage (aus dem Pilot übernommen, soweit für den heutigen Eintrag gültig)
MANUELLE_HINWEISE: dict[str, str] = {
    "Wirtschaftsprüfer, Steuerberater und verwandte Berufe":
        "ESCO-Titel «Controller/Controllerin» ist das deutsche Label der ESCO-Occupation «accountant» "
        "(2411.1), nicht Controlling im CH-Sinn. Die Kompetenzliste (Buchführung, Abschlüsse, Prüfung) "
        "deckt Buchhaltung, Treuhand und Revision ab.",
    "Arzt/Ärztin (Allgemeinmedizin)":
        "Tätigkeiten aus Beschreibung, optionalen Kompetenzen und Berufswissen zur CH-Hausarztpraxis ableiten.",
    "Verkäufer in Handelsgeschäften":
        "CH-Detailhandel (EFZ) umfasst Beratung, Verkauf, Kasse und Warenbewirtschaftung.",
    "Softwareentwickler":
        "Kompetenzliste enthält ESCO-Rauschen (z. B. «Bauprojekte leiten», «Software für technisches "
        "Zeichnen verwenden») — nicht als Kerntätigkeit übernehmen.",
}
KURZE_BESCHREIBUNG = 200   # Zeichen; darunter gilt die Beschreibung als knapp
WENIG_SKILLS = 2           # höchstens so viele wesentliche Skills → Hinweis


def _text(x) -> str | None:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    s = str(x).strip()
    return s or None


def lade_eintraege(scores_path: Path = tr.SCORES_PATH) -> pd.DataFrame:
    """Stammdaten aller Einträge (eine Zeile je Eintrag in scores.csv), mit internen Schlüsseln."""
    df = pd.read_csv(scores_path, dtype={"isco_code": str, "esco_isco_code": str})
    fehlend = [c for c in ["occupation", "isco_code", "esco_description"] if c not in df.columns]
    if fehlend:
        raise ValueError(f"scores.csv: Spalten fehlen: {fehlend}")
    df = df[[c for c in STAMMDATEN_SPALTEN if c in df.columns]].rename(columns=STAMMDATEN_SPALTEN)
    for c in STAMMDATEN:
        if c not in df.columns:
            df[c] = None
    df["isco_code"] = df["isco_code"].str.strip().str.zfill(4)
    doppelt = df.duplicated(["isco_code", "beruf"])
    if doppelt.any():
        raise ValueError(f"scores.csv: doppelte Einträge {df.loc[doppelt, ['isco_code', 'beruf']].values.tolist()}")
    return df[STAMMDATEN].reset_index(drop=True)


def lade_kompetenzen(pfad: Path = tr.KOMPETENZEN_PATH) -> pd.DataFrame:
    k = pd.read_csv(pfad, dtype={"isco_code": str})
    fehlend = [c for c in KOMPETENZ_SPALTEN if c not in k.columns]
    if fehlend:
        raise ValueError(f"{Path(pfad).name}: Spalten fehlen: {fehlend}")
    k = k[list(KOMPETENZ_SPALTEN)].rename(columns=KOMPETENZ_SPALTEN)
    k["isco_code"] = k["isco_code"].str.strip().str.zfill(4)
    k["typ"] = k["typ"].fillna("unbekannt")
    return k


def _kompetenzen(k: pd.DataFrame, beruf: str, isco: str, uri: str | None) -> tuple[list[dict], list[str]]:
    sel = k[(k["beruf"] == beruf) & (k["isco_code"] == isco)]
    if uri:
        sel = sel[sel["esco_uri"] == uri]
    wes = (sel[sel["relation"] == "essential"]
           .drop_duplicates(["kompetenz", "typ"])
           .sort_values("kompetenz", key=lambda s: s.str.lower()))
    wesentlich = [{"titel": r.kompetenz.strip(), "typ": r.typ, "uri": _text(r.kompetenz_uri)}
                  for r in wes.itertuples()]
    wesentlich.sort(key=lambda x: (x["typ"] != "skill", x["titel"].lower()))
    opt = sel[(sel["relation"] == "optional") & (sel["typ"] == "skill")]
    optional = sorted({str(t).strip() for t in opt["kompetenz"]}, key=str.lower)
    return wesentlich, optional


def datenlage_hinweis(row: dict, wesentlich: list[dict]) -> str | None:
    teile = []
    quelle = _text(row.get("beschreibung_quelle")) or "unbekannt"
    beschr = _text(row.get("esco_beschreibung")) or ""
    n_skill = sum(1 for s in wesentlich if s["typ"] == "skill")
    if quelle != "ESCO" or not _text(row.get("esco_uri")):
        teile.append(f"Keine ESCO-Zuordnung: Die Beschreibung stammt aus Quelle «{quelle}», es gibt keine "
                     "ESCO-Kompetenzliste. Tätigkeiten aus Beschreibung und Berufswissen zur "
                     "CH-Berufsausübung ableiten.")
    else:
        if _text(row.get("esco_match_qualitaet")) == "plausibel":
            teile.append(f"Die ESCO-Zuordnung «{_text(row.get('esco_titel'))}» passt nur teilweise "
                         "(Qualität «plausibel»): Kompetenzen kritisch prüfen und mit Berufswissen zur "
                         "CH-Berufsausübung ergänzen.")
        esco_isco = (_text(row.get("esco_isco_code")) or "")[:4]
        if esco_isco and esco_isco != row["isco_code"]:
            teile.append(f"Die ESCO-Occupation gehört zur ISCO-Gruppe {esco_isco}, der CH-Eintrag zu "
                         f"{row['isco_code']}; massgebend ist der CH-Beruf.")
        if n_skill <= WENIG_SKILLS:
            teile.append(f"ESCO führt nur {n_skill} wesentliche Kompetenz(en) vom Typ «skill»; Tätigkeiten "
                         "zusätzlich aus Beschreibung, optionalen Kompetenzen und Berufswissen ableiten.")
        if len(beschr) < KURZE_BESCHREIBUNG:
            teile.append("ESCO-Beschreibung sehr knapp; Kompetenzliste nutzen.")
    manuell = MANUELLE_HINWEISE.get(row["beruf"])
    if manuell:
        teile.append(manuell)
    return " ".join(teile) or None


def baue_input(row: dict, kompetenzen: pd.DataFrame) -> dict:
    """Input-Datensatz eines Eintrags (Format wie pilot/input/*.json, ohne Abrufdatum)."""
    beruf, isco = row["beruf"], row["isco_code"]
    uri = _text(row.get("esco_uri"))
    wesentlich, optional = _kompetenzen(kompetenzen, beruf, isco, uri)
    syn = _text(row.get("synonyme"))
    return {
        "beruf": beruf,
        "isco_code": isco,
        "synonyme": [s.strip() for s in syn.split(";") if s.strip()] if syn else [],
        "ch_kontext": {"qualifikation": _text(row.get("qualifikation")), "branche": _text(row.get("branche"))},
        "esco_uri": uri,
        "esco_titel": _text(row.get("esco_titel")),
        "esco_beschreibung": _text(row.get("esco_beschreibung")),
        "beschreibung_quelle": _text(row.get("beschreibung_quelle")),
        "esco_match_qualitaet": _text(row.get("esco_match_qualitaet")),
        "wesentliche_kompetenzen": wesentlich,
        "anzahl_kompetenzen": {"skill": sum(1 for s in wesentlich if s["typ"] == "skill"),
                               "knowledge": sum(1 for s in wesentlich if s["typ"] == "knowledge")},
        "optionale_kompetenzen_skills": optional,
        "datenlage_hinweis": datenlage_hinweis(row, wesentlich),
    }


@dataclass
class Eintrag:
    """Ein zu bewertender Eintrag mit Input und Hash."""
    isco_code: str
    beruf: str
    input: dict
    input_hash: str

    @property
    def datei(self) -> str:
        return tr.dateiname(self.isco_code, self.beruf)

    @property
    def schluessel(self) -> str:
        return self.datei[:-5]


def ordne_zu(df: pd.DataFrame, isco: str, beruf: str) -> tuple[int | None, str | None]:
    """Index des passenden Eintrags in df: exakter Name → Synonym (gleicher ISCO) → einziger ISCO-Eintrag."""
    gleiche = df[df["isco_code"] == isco]
    treffer = gleiche[gleiche["beruf"] == beruf]
    if len(treffer):
        return int(treffer.index[0]), "exakt"
    syn = gleiche["synonyme"].fillna("").astype(str)
    treffer = gleiche[syn.apply(lambda s: beruf in [x.strip() for x in s.split(";")])]
    if len(treffer):
        return int(treffer.index[0]), "synonym"
    if len(gleiche) == 1:
        return int(gleiche.index[0]), "isco"
    return None, None


def pilot_indizes(df: pd.DataFrame) -> list[int]:
    res = []
    for isco, beruf in PILOT_BERUFE:
        idx, _ = ordne_zu(df, isco, beruf)
        if idx is None:
            raise ValueError(f"Pilotberuf nicht in scores.csv: {isco} {beruf}")
        res.append(idx)
    return res


def baue_eintraege(nur: list[str] | None = None, pilot: bool = False,
                   scores_path: Path = tr.SCORES_PATH,
                   kompetenzen_path: Path = tr.KOMPETENZEN_PATH) -> list[Eintrag]:
    """Alle (bzw. gefilterten) Einträge mit Input und Input-Hash, in der Reihenfolge von scores.csv.

    ``nur``: ISCO-Codes oder -Präfixe; ``pilot``: die 15 Pilotberufe.
    """
    df = lade_eintraege(scores_path)
    k = lade_kompetenzen(kompetenzen_path)
    idx = list(df.index)
    if pilot:
        auswahl = set(pilot_indizes(df))
        idx = [i for i in idx if i in auswahl]
    if nur:
        idx = [i for i in idx if any(df.at[i, "isco_code"].startswith(p) for p in nur)]
    schema = tr.lade_schema()
    res = []
    for i in idx:
        rec = baue_input(df.loc[i].to_dict(), k)
        res.append(Eintrag(rec["isco_code"], rec["beruf"], rec, tr.input_hash(rec, schema)))
    namen = [e.datei for e in res]
    if len(set(namen)) != len(namen):
        raise ValueError("Dateinamen (isco_slug) nicht eindeutig")
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="+", metavar="ISCO", help="nur diese ISCO-Codes/-Präfixe")
    ap.add_argument("--pilot", action="store_true", help="nur die 15 Pilotberufe")
    ap.add_argument("--out", default=str(tr.BEWERTUNGEN_DIR / "input"))
    a = ap.parse_args(argv)
    eintraege = baue_eintraege(a.only, a.pilot)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for e in eintraege:
        (out / e.datei).write_text(json.dumps(e.input, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(eintraege)} Input-Dateien → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
