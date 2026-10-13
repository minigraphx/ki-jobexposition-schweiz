"""
BFS Strukturerhebung (SE) einlesen und Beschäftigte / Frauenanteil aller Berufe setzen.

Quelle: BFS Strukturerhebung (SE) — «Ausgeübter Beruf (CH-ISCO-19) nach Geschlecht
und Staatsangehörigkeit», Erwerbstätige ab 15 Jahren, in 1000.
Asset 36492006, Datei su-d-40.02.03.02.01.03.10.xlsx (manueller Download nach data/raw/):
https://www.bfs.admin.ch/bfs/de/home/statistiken/kataloge-datenbanken.assetdetail.36492006.html

Hinweis: Es handelt sich um die Strukturerhebung (SE), nicht um die SAKE. Die Datei enthält
ein Blatt pro Jahr («2024», «2023», …) sowie gepoolte Mehrjahresblätter («2022-2024», …).
Spalten: 0–4 Codes je Ebene (3 = 4-stellige Berufsgattung, 4 = 5-stellige Berufsart),
5 Bezeichnung, 6 Total, 7 Männer, 8 Frauen. «X» = nicht publiziert (< 5 Beobachtungen),
Werte in Klammern (Zahlenformat «(##0)») = < 50 Beobachtungen.

Zuordnung Beruf → SE (Issue #51), versioniert in data/processed/beruf_berufsart_mapping.csv:
- ebene "gattung":   der Beruf ist der einzige Eintrag seiner 4-stelligen Berufsgattung und
                     erhält deren vollen SE-Wert.
- ebene "berufsart": mehrere Berufe teilen sich eine Berufsgattung; jeder Beruf entspricht
                     einer oder mehreren 5-stelligen Berufsarten (Spalte berufsarten). Der Rest
                     der Gattung (Berufsart «onA» und nicht publizierte Werte) wird proportional
                     zu den zugeordneten Berufsarten verteilt. Jede publizierte Berufsart
                     (ohne «onA») der Gattung muss genau einem Beruf zugeordnet sein.
- Wo keine saubere Zuordnung möglich ist, sind die Berufe zusammengelegt (SE-Bezeichnung als
  beruf, bisherige CH-Titel in synonyme; siehe berufe_zusammenlegen.py).
Invariante: Σ beschaeftigte_1000 je 4-stelligem Code = SE-Wert der Berufsgattung
(auf 0.1 gerundet; Rundung je Gattung nach grösstem Rest).

SE-Wert: Blatt «2024» (--blatt). Ist eine Gattung im Jahresblatt nicht publiziert («X»),
gilt das gepoolte Blatt «2022-2024»; ebenso für den Frauenanteil, wenn die Frauenzahl im
Jahresblatt fehlt. Die Blätter «2024» und «2022-2024» liegen als data/processed/se_berufe.csv
versioniert vor, damit die Pipeline ohne Rohdatei läuft.

Schritte:
1. SE-Excel parsen (Berufsgattungen und Berufsarten), versionierte CSV aktualisieren
2. Beschäftigte, Frauenanteil und Synonyme in berufe_ch.csv, berufe_ch_esco.csv,
   berufe_ch_esco_verified.csv und scores.csv setzen (nur diese Spalten; übrige Zellen
   bleiben byte-identisch)
3. Optional (--neue-berufe): neue Berufsgattungen (>= 5000 Erwerbstätige im Jahresblatt,
   noch nicht erfasst; ohne Restgruppen «onA»/«a.n.g.» ausser RESTGRUPPEN_AUSNAHMEN) in die
   Mapping-Tabelle und alle CSVs aufnehmen; Branche / Lohn / Qualifikation per ISCO-Gruppe,
   ESCO-Felder und Scores leer. Danach ESCO-Zuordnung und Scoring nötig.
Danach: python src/data/update_loehne.py --offline (Lohngewichte = neue Beschäftigte).
"""

import argparse
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from update_loehne import lade_lse, lse_basislohn

RAW_PATH = Path(__file__).parent.parent.parent / "data" / "raw"
PROCESSED_PATH = Path(__file__).parent.parent.parent / "data" / "processed"
BFS_FILE = RAW_PATH / "su-d-40.02.03.02.01.03.10.xlsx"  # BFS Strukturerhebung (SE)
DEFAULT_BLATT = "2024"
POOL_BLATT = "2022-2024"
SE_CSV = PROCESSED_PATH / "se_berufe.csv"          # versionierter Auszug (Blätter 2024, 2022-2024)
SE_CSV_BLAETTER = (DEFAULT_BLATT, POOL_BLATT)
MAPPING_CSV = PROCESSED_PATH / "beruf_berufsart_mapping.csv"
CSV_DATEIEN = ["berufe_ch.csv", "berufe_ch_esco.csv", "berufe_ch_esco_verified.csv", "scores.csv"]

EBENE_GATTUNG = "gattung"
EBENE_BERUFSART = "berufsart"
TRENNER = "; "  # Trennzeichen in den Spalten berufsarten, synonyme, zusammengelegt_aus

# ISCO-Hauptgruppe → Qualifikation
QUALIFIKATION_MAP = {
    "1": "Tertiär",
    "2": "Tertiär",
    "3": "Sekundär II",
    "4": "Sekundär II",
    "5": "Sekundär II",
    "6": "Sekundär II",
    "7": "Sekundär II",
    "8": "Sekundär II",
    "9": "Keine Ausbildung",
    "0": "Sekundär II",
}

# ISCO-Präfix (2-, 3- oder 4-stellig) → Branche
#
# Auflösung über den längsten passenden Präfix (siehe branche_fuer_isco): ein 4-stelliger
# Eintrag schlägt einen 3-stelligen, dieser einen 2-stelligen. So lassen sich heterogene
# Untergruppen (z. B. 13 «Führungskräfte in Produktion und spezialisierten Dienstleistungen»)
# sauber nach Wirtschaftszweig aufteilen. Branchennamen = die 21 Branchen aus
# ch_adjustments.BRANCHENEFFEKTE; die Abgrenzung folgt, wo möglich, der NOGA-Zuordnung in
# fetch_bgs.py / fetch_statent.py (z. B. NOGA 46 Grosshandel → Dienstleistungen,
# NOGA 87 Heime → Soziales, NOGA 81 Gebäudebetreuung → Dienstleistungen).
# Gilt nur für automatisch ergänzte Berufe; die kuratierte Liste in build_berufeliste.py
# hat eigene, manuell gesetzte Branchen.
BRANCHE_MAP = {
    # --- 2-stellige Untergruppen (Grundzuordnung) ---
    "11": "Verwaltung", "12": "Verwaltung",
    "13": "Dienstleistungen",  # nur Fallback; alle Gattungen unten nach Branche aufgeteilt
    "14": "Dienstleistungen",  # nur Fallback; 141/142/143 unten
    "21": "Industrie", "22": "Gesundheit", "23": "Bildung", "24": "Finanzen",
    "25": "ICT", "26": "Medien",
    "31": "Industrie", "32": "Gesundheit", "33": "Finanzen", "34": "Soziales",
    "35": "ICT",
    "41": "Verwaltung", "42": "Verwaltung", "43": "Verwaltung", "44": "Verwaltung",
    "51": "Gastgewerbe", "52": "Detailhandel", "53": "Soziales", "54": "Öff. Verwaltung",
    "61": "Landwirtschaft", "62": "Landwirtschaft", "63": "Landwirtschaft",
    "71": "Bau", "72": "Industrie", "73": "Industrie", "74": "Industrie",
    "75": "Industrie",  # Nahrungsmittel-, Holz-, Textilverarbeitung = verarb. Gewerbe (NOGA 10–16)
    "81": "Industrie", "82": "Industrie", "83": "Transport",
    "91": "Dienstleistungen",
    "92": "Landwirtschaft",  # Hilfsarbeitskräfte in Land-/Forstwirtschaft, Fischerei
    "93": "Industrie", "94": "Gastgewerbe",
    "95": "Dienstleistungen", "96": "Dienstleistungen",
    "01": "Öff. Verwaltung", "02": "Öff. Verwaltung", "03": "Öff. Verwaltung",  # Armee

    # --- 1: Führungskräfte ---
    "111": "Öff. Verwaltung",   # Legislative, leitende Verwaltungsbedienstete (NOGA 84)
    "1114": "Verwaltung",       # Leitende Funktionäre von Interessenverbänden (NOGA 94)
    "131": "Landwirtschaft",    # Produktionsleiter Land-/Forstwirtschaft, Fischerei
    "1321": "Industrie",        # Produktion von Waren
    "1322": "Industrie",        # Bergbau (NOGA 05–09 → Industrie)
    "1323": "Bau",              # Produktion im Bau
    "1324": "Transport",        # Beschaffung, Logistik, Distribution
    "133": "ICT",               # Dienstleistungen der Informations- und Kommunikationstechnologie
    "1341": "Soziales",         # Kinderbetreuung
    "1342": "Gesundheit",       # Gesundheitswesen
    "1343": "Soziales",         # Altenbetreuung (Heime, NOGA 87 → Soziales)
    "1344": "Soziales",         # Sozialwesen
    "1345": "Bildung",          # Bildungswesen
    "1346": "Finanzen",         # Finanz- und Versicherungsdienstleistungen (Filialleitung)
    "1349": "Dienstleistungen", # sonstige spezialisierte Dienstleistungen
    "141": "Gastgewerbe",       # Hotels und Restaurants
    "142": "Detailhandel",      # Gross- und Einzelhandel
    "143": "Dienstleistungen",  # Sport-, Freizeit-, Kultureinrichtungen, sonstige Dienstleistungen

    # --- 2: Akademische Berufe ---
    "2132": "Landwirtschaft",   # Agrar-, Forst-, Fischereiwissenschaftler
    "2133": "Umwelt",           # Umweltschutzfachleute
    "2142": "Bau",              # Bauingenieure
    "2143": "Umwelt",           # Umweltingenieure
    "2161": "Bau", "2162": "Bau", "2164": "Bau", "2165": "Bau",  # Architektur, Raumplanung, Vermessung
    "2166": "Medien",           # Grafik- und Multimediadesigner
    "2421": "Beratung",         # Management- und Organisationsanalytiker (NOGA 70)
    "2422": "Öff. Verwaltung",  # Fachkräfte in der Politikverwaltung
    "2423": "Verwaltung",       # Personalwesen und Berufsberatung (HR-Funktion)
    "2424": "Verwaltung",       # Personalschulung und -entwicklung (HR-Funktion)
    "243": "Medien",            # Marketing, Werbung, PR (NOGA 73 → Medien)
    "2433": "Dienstleistungen", # Technische Verkaufsfachkräfte (Grosshandel, NOGA 46)
    "2434": "ICT",              # ICT-Verkaufsfachkräfte
    "261": "Recht",             # Juristen
    "2634": "Gesundheit",       # Psychologen
    "2635": "Soziales",         # Sozialarbeit
    "2636": "Dienstleistungen", # Geistliche, Seelsorger

    # --- 3: Techniker und gleichrangige Berufe ---
    "3112": "Bau",              # Bautechniker
    "3123": "Bau",              # Bauführer, Aufsichtskräfte im Bau
    "315": "Transport",         # Schiffs-/Luftfahrzeugführer, Fluglotsen
    "332": "Dienstleistungen",  # Ein-/Verkaufsagenten, Handelsmakler (Grosshandel, NOGA 46)
    "3321": "Versicherungen",   # Versicherungsvertreter
    "333": "Dienstleistungen",  # Unternehmensbezogene Dienstleistungen (Veranstaltungen, Vermittlung)
    "3331": "Transport",        # Speditions- und Zollagenten
    "3334": "Immobilien",       # Immobilienmakler und -verwalter
    "334": "Verwaltung",        # Sekretariatsfachkräfte, Büroleitung
    "3342": "Recht",            # Sekretariatsfachkräfte im Rechtswesen
    "3344": "Gesundheit",       # Sekretariatsfachkräfte im Gesundheitswesen
    "335": "Öff. Verwaltung",   # Verwaltungsfachkräfte der öffentlichen Hand (Zoll, Steuer, Sozialversicherung, Polizei)
    "3411": "Recht",            # Fachkräfte für Rechtsangelegenheiten
    "3413": "Dienstleistungen", # Nicht akademische Fachkräfte im religiösen Bereich
    "342": "Dienstleistungen",  # Sport und Fitness (NOGA 93)
    "343": "Medien",            # Künstlerische und kulturelle Fachkräfte (NOGA 90)
    "3432": "Dienstleistungen", # Raumgestalter, Dekorateure (Design, NOGA 74)
    "3434": "Gastgewerbe",      # Küchenchefs

    # --- 4: Bürokräfte ---
    "4211": "Finanzen",         # Bankschalter, Finanzdienstleistungen (NOGA 64)
    "4412": "Transport",        # Postverteiler und -sortierer (NOGA 53, wie Posthalter/in)

    # --- 5: Dienstleistungs- und Verkaufsberufe ---
    "511": "Transport",         # Flugbegleiter, Zugbegleiter, Schaffner
    "5113": "Gastgewerbe",      # Reiseleiter (Tourismus, NOGA 79)
    "514": "Dienstleistungen",  # Coiffeure, Kosmetiker (NOGA 96)
    "515": "Dienstleistungen",  # Hauswarte, Reinigungs-/Hauswirtschaftsleitung (NOGA 81)
    "516": "Dienstleistungen",  # sonstige personenbezogene Dienstleistungen
    "532": "Gesundheit",        # Betreuungsberufe im Gesundheitswesen (Pflegehilfe, Spitex)
    "5414": "Sicherheit",       # Wachpersonal (NOGA 80)

    # --- 7/8: Handwerk, Anlagen- und Maschinenbedienung ---
    "7411": "Bau",              # Elektroinstallateure (Gebäude)
    "8341": "Landwirtschaft",   # Führer land- und forstwirtschaftlicher Maschinen
    "8342": "Bau",              # Erdbewegungs- und Strassenbaumaschinen

    # --- 9: Hilfsarbeitskräfte ---
    "931": "Bau",               # Hilfsarbeiter im Hoch- und Tiefbau
    "9311": "Industrie",        # Hilfsarbeiter im Bergbau
    "933": "Transport",         # Hilfsarbeiter in Transport und Lagerei
    "961": "Umwelt",            # Abfallentsorgung (NOGA 38)
}
BRANCHE_DEFAULT = "Dienstleistungen"

# --neue-berufe: SE-Berufsgattungen ab dieser Grösse (Tsd., Jahresblatt) aufnehmen
NEUE_BERUFE_SCHWELLE = 5.0
# Restgruppen (Bezeichnung enthält einen dieser Begriffe) werden nicht aufgenommen …
RESTGRUPPEN_BEGRIFFE = ("onA", "anderweitig nicht genannt", "ohne nähere Angabe")
# … ausser sie sind gross und inhaltlich klar (Begründung → Mapping, docs/audit_isco_codes.md)
RESTGRUPPEN_AUSNAHMEN: dict[str, str] = {
    "4419": ("SE-Berufsgattung (automatisch ergänzt) → voller SE-Wert; Restgruppe «a.n.g.», "
             "aber inhaltlich klar: 84 % Berufsart 44192 Bürokräfte Verkauf "
             "(Verkaufsinnendienst), dazu 44191 Marketing und Werbung"),
    "9329": ("SE-Berufsgattung (automatisch ergänzt) → voller SE-Wert; Restgruppe «a.n.g.», "
             "aber inhaltlich klar: einzige Berufsart 93290, Hilfsarbeiter in der Produktion "
             "(ISCO-Untergruppe 932 hat sonst nur 9321 Verpackung)"),
}
NEUE_BERUFE_BEGRUENDUNG = "SE-Berufsgattung (automatisch ergänzt) → voller SE-Wert"

# Löhne: BFS LSE 2024 (2-stellige Gruppe × 12, Fallback 1-stellig/Total) aus
# update_loehne.py. Die frühere, geschätzte LOHN_MAP («LSE 2022, geschätzt») ist entfernt.
# Salarium-Profile für heterogene Gruppen setzt erst update_loehne.py.


def _zahl(wert) -> float:
    """SE-Zelle → float; «X» (nicht publiziert), leer → NaN."""
    if wert is None:
        return np.nan
    if isinstance(wert, str):
        wert = wert.strip()
        if wert in ("", "X"):
            return np.nan
    try:
        return float(wert)
    except (TypeError, ValueError):
        return np.nan


def _code(wert) -> str:
    return "" if wert is None else str(wert).strip()


def parse_se_excel(filepath: Path, blatt: str = DEFAULT_BLATT) -> pd.DataFrame:
    """SE-Excel lesen: 4-stellige Berufsgattungen und 5-stellige Berufsarten.

    Returns:
        DataFrame mit ebene (4 oder 5), code, bezeichnung, total, maenner, frauen
        (in 1000, «X» → NaN) und total_lt50 (Zahlenformat in Klammern = < 50 Beobachtungen).
    """
    import openpyxl

    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    try:
        if str(blatt) not in wb.sheetnames:
            raise ValueError(f"Blatt «{blatt}» nicht in {Path(filepath).name} "
                             f"(vorhanden: {', '.join(wb.sheetnames)})")
        rows = []
        for zeile in wb[str(blatt)].iter_rows():
            zellen = list(zeile) + [None] * (9 - len(zeile))
            werte = [getattr(z, "value", None) for z in zellen[:9]]
            gattung, art = _code(werte[3]), _code(werte[4])
            if gattung and not art and gattung != "X":
                ebene, code = 4, gattung
            elif art and not gattung and art != "X":
                ebene, code = 5, art
            else:
                continue
            fmt = str(getattr(zellen[6], "number_format", "") or "")
            rows.append({
                "ebene": ebene, "code": code, "bezeichnung": _code(werte[5]),
                "total": _zahl(werte[6]), "maenner": _zahl(werte[7]), "frauen": _zahl(werte[8]),
                "total_lt50": "(" in fmt,
            })
    finally:
        wb.close()
    return pd.DataFrame(rows, columns=["ebene", "code", "bezeichnung", "total", "maenner",
                                       "frauen", "total_lt50"])


def parse_bfs_excel(filepath: Path, blatt: str = DEFAULT_BLATT) -> pd.DataFrame:
    """BFS-SE-Excel einlesen, nur 4-stellige Berufsgattungen mit publiziertem Total.

    Args:
        filepath: Pfad zur BFS-Excel-Datei (su-d-40.02.03.02.01.03.10.xlsx).
        blatt: Name des Tabellenblatts, z. B. "2024" (Einzeljahr) oder
               "2022-2024" (gepoolte Mehrjahresauswertung).
    """
    se = parse_se_excel(filepath, blatt)
    bfs = se[se["ebene"] == 4].rename(columns={"code": "isco_code", "bezeichnung": "beruf_bfs",
                                               "total": "beschaeftigte_total"})
    bfs = bfs[["isco_code", "beruf_bfs", "beschaeftigte_total", "maenner", "frauen"]].copy()
    bfs["frauen_pct"] = (bfs["frauen"] / bfs["beschaeftigte_total"] * 100).round(1)
    return bfs.dropna(subset=["beschaeftigte_total"]).reset_index(drop=True)


def lade_se(blaetter: tuple[str, ...] = SE_CSV_BLAETTER, raw: Path = BFS_FILE,
            csv: Path = SE_CSV, schreiben: bool = True) -> pd.DataFrame:
    """SE-Werte (Spalte blatt) — Rohdatei bevorzugt, sonst versionierte CSV.

    Mit Rohdatei wird die CSV (Blätter SE_CSV_BLAETTER) neu geschrieben.
    """
    if raw.exists():
        lesen = list(dict.fromkeys(list(blaetter) + (list(SE_CSV_BLAETTER) if schreiben else [])))
        tab = pd.concat([parse_se_excel(raw, b).assign(blatt=b) for b in lesen], ignore_index=True)
        tab = tab[["blatt"] + [c for c in tab.columns if c != "blatt"]]
        # 6 Nachkommastellen (= 1 Person) — gleiche Werte mit und ohne Rohdatei
        tab[["total", "maenner", "frauen"]] = tab[["total", "maenner", "frauen"]].round(6)
        if schreiben:
            tab[tab["blatt"].isin(SE_CSV_BLAETTER)].to_csv(csv, index=False)
        return tab[tab["blatt"].isin(blaetter)].reset_index(drop=True)
    tab = pd.read_csv(csv, dtype={"blatt": str, "code": str})
    fehlt = set(blaetter) - set(tab["blatt"])
    if fehlt:
        raise SystemExit(f"Blatt {sorted(fehlt)} nicht in {csv.name} — Rohdatei {raw.name} "
                         f"nach {raw.parent} herunterladen")
    tab["total_lt50"] = tab["total_lt50"].astype(bool)
    return tab[tab["blatt"].isin(blaetter)].reset_index(drop=True)


def _liste(text) -> list[str]:
    if text is None or (isinstance(text, float) and np.isnan(text)):
        return []
    return [t.strip() for t in str(text).split(TRENNER.strip()) if t.strip()]


def lade_mapping(path: Path = MAPPING_CSV) -> pd.DataFrame:
    """Mapping beruf → Berufsgattung/Berufsart(en) (Spalten siehe Moduldoku)."""
    m = pd.read_csv(path, dtype=str, keep_default_na=False)
    doppelt = m[m["beruf"].duplicated(keep=False)]
    if not doppelt.empty:
        raise ValueError(f"Mapping: Beruf mehrfach: {sorted(set(doppelt['beruf']))}")
    falsch = set(m["ebene"]) - {EBENE_GATTUNG, EBENE_BERUFSART}
    if falsch:
        raise ValueError(f"Mapping: unbekannte ebene {sorted(falsch)}")
    return m


def _se_index(se: pd.DataFrame, blatt: str, ebene: int) -> pd.DataFrame:
    sel = se[(se["blatt"] == blatt) & (se["ebene"].astype(int) == ebene)]
    return sel.drop_duplicates("code").set_index("code")


def _ist_ona(bezeichnung: str) -> bool:
    return "onA" in str(bezeichnung)


def _frauen_anteil(codes: list[str], idx: pd.DataFrame) -> float:
    """100 × Σ Frauen / Σ Total über die Codes; NaN, wenn eine Frauenzahl fehlt."""
    sel = idx.reindex(codes)
    sel = sel[sel["total"].notna()]
    if sel.empty or sel["frauen"].isna().any() or sel["total"].sum() <= 0:
        return np.nan
    return float(sel["frauen"].sum() / sel["total"].sum() * 100)


def runde_mit_summe(werte: list[float], summe: float, stellen: int = 1) -> list[float]:
    """Auf `stellen` runden, sodass die Summe exakt round(summe, stellen) ist (grösster Rest)."""
    faktor = 10 ** stellen
    ziel = int(round(summe * faktor))
    roh = [w * faktor for w in werte]
    basis = [int(np.floor(r)) for r in roh]
    rest = ziel - sum(basis)
    reihenfolge = sorted(range(len(roh)), key=lambda i: (-(roh[i] - basis[i]), i))
    for i in reihenfolge[:max(rest, 0)]:
        basis[i] += 1
    return [b / faktor for b in basis]


def beschaeftigte_berechnen(mapping: pd.DataFrame, se: pd.DataFrame,
                            blatt: str = DEFAULT_BLATT, pool_blatt: str = POOL_BLATT) -> pd.DataFrame:
    """Beschäftigte (1000) und Frauenanteil (%) je Beruf aus SE und Mapping.

    Returns: DataFrame mit beruf, isco_code, beschaeftigte_1000, frauen_pct, se_blatt.
    """
    g_haupt, a_haupt = _se_index(se, blatt, 4), _se_index(se, blatt, 5)
    g_pool, a_pool = _se_index(se, pool_blatt, 4), _se_index(se, pool_blatt, 5)
    out = []
    for code, grp in mapping.groupby("isco_code", sort=True):
        if code not in g_haupt.index:
            raise ValueError(f"Berufsgattung {code} nicht in der SE ({grp['beruf'].tolist()})")
        total, quelle, arten_idx = g_haupt.at[code, "total"], blatt, a_haupt
        if pd.isna(total) and code in g_pool.index and pd.notna(g_pool.at[code, "total"]):
            total, quelle, arten_idx = g_pool.at[code, "total"], pool_blatt, a_pool
        if pd.isna(total):
            raise ValueError(f"Berufsgattung {code}: kein publizierter SE-Wert")
        ebenen = set(grp["ebene"])
        if len(grp) == 1 and ebenen == {EBENE_GATTUNG}:
            beruf = grp["beruf"].iloc[0]
            frauen = _frauen_anteil([code], g_haupt)
            if pd.isna(frauen):
                frauen = _frauen_anteil([code], g_pool)
            out.append({"beruf": beruf, "isco_code": code, "roh": float(total),
                        "frauen_pct": frauen, "se_blatt": quelle})
            continue
        if ebenen != {EBENE_BERUFSART}:
            raise ValueError(f"Berufsgattung {code} hat {len(grp)} Berufe — alle brauchen "
                             f"ebene={EBENE_BERUFSART}: {grp['beruf'].tolist()}")
        arten = arten_idx[arten_idx.index.str.startswith(code) & (arten_idx.index.str.len() == 5)]
        zugeordnet: dict[str, str] = {}
        for beruf, liste in zip(grp["beruf"], grp["berufsarten"].map(_liste)):
            if not liste:
                raise ValueError(f"{beruf}: ebene={EBENE_BERUFSART} ohne berufsarten")
            for art in liste:
                if art not in arten.index:
                    raise ValueError(f"{beruf}: Berufsart {art} gehört nicht zu {code}")
                if art in zugeordnet:
                    raise ValueError(f"Berufsart {art} doppelt: {zugeordnet[art]} / {beruf}")
                zugeordnet[art] = beruf
        offen = [a for a in arten.index if a not in zugeordnet and pd.notna(arten.at[a, "total"])
                 and not _ist_ona(arten.at[a, "bezeichnung"])]
        if offen:
            raise ValueError(f"Berufsgattung {code}: Berufsarten ohne Beruf: {offen}")
        eigen = {beruf: float(arten.reindex(_liste(text))["total"].fillna(0.0).sum())
                 for beruf, text in zip(grp["beruf"], grp["berufsarten"])}
        summe = sum(eigen.values())
        for beruf, liste in zip(grp["beruf"], grp["berufsarten"].map(_liste)):
            frauen = _frauen_anteil(liste, a_haupt)
            if pd.isna(frauen):
                frauen = _frauen_anteil(liste, a_pool)
            # eigener Anteil + Rest der Gattung (onA, nicht publiziert) proportional
            out.append({"beruf": beruf, "isco_code": code, "roh": float(total) * eigen[beruf] / summe,
                        "frauen_pct": frauen, "se_blatt": quelle})
    res = pd.DataFrame(out)
    res["beschaeftigte_1000"] = np.nan
    for code, idx in res.groupby("isco_code").groups.items():
        werte = res.loc[idx, "roh"].tolist()
        res.loc[idx, "beschaeftigte_1000"] = runde_mit_summe(werte, sum(werte))
    res["frauen_pct"] = res["frauen_pct"].round(1)
    return res[["beruf", "isco_code", "beschaeftigte_1000", "frauen_pct", "se_blatt"]]


def se_gattungswert(se: pd.DataFrame, code: str, blatt: str = DEFAULT_BLATT,
                    pool_blatt: str = POOL_BLATT) -> float:
    """SE-Wert einer Berufsgattung (Jahresblatt, Fallback gepoolt), auf 0.1 gerundet."""
    for b in (blatt, pool_blatt):
        g = _se_index(se, b, 4)
        if code in g.index and pd.notna(g.at[code, "total"]):
            return round(float(g.at[code, "total"]), 1)
    return np.nan


def branche_fuer_isco(isco_code: str) -> str:
    """Branche über den längsten passenden ISCO-Präfix (4 → 3 → 2 Stellen) bestimmen."""
    code = str(isco_code).strip()
    for laenge in (4, 3, 2):
        if len(code) >= laenge and code[:laenge] in BRANCHE_MAP:
            return BRANCHE_MAP[code[:laenge]]
    return BRANCHE_DEFAULT


def assign_metadata(isco_code: str) -> tuple[str, str, int]:
    """Branche, Qualifikation, Lohn (LSE 2024, siehe update_loehne.py) aus ISCO-Code ableiten."""
    major = isco_code[0] if isco_code else "9"
    branche = branche_fuer_isco(isco_code)
    qualifikation = QUALIFIKATION_MAP.get(major, "Sekundär II")
    lohn, _ = lse_basislohn(isco_code, _lse())
    return branche, qualifikation, lohn


@lru_cache(maxsize=1)
def _lse() -> dict[str, int]:
    return lade_lse(schreiben=False)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="BFS Strukturerhebung (SE) einlesen und Beschäftigte aller Berufe setzen."
    )
    parser.add_argument(
        "--blatt",
        default=DEFAULT_BLATT,
        help=f'Tabellenblatt der BFS-Datei, z. B. "2024" oder "2022-2024" (Default: "{DEFAULT_BLATT}")',
    )
    parser.add_argument("--neue-berufe", action="store_true",
                        help="neue SE-Berufsgattungen (>= 5000) in berufe_ch.csv aufnehmen")
    parser.add_argument("--dry-run", action="store_true", help="Änderungen nur anzeigen")
    parser.add_argument("--pfad", type=Path, default=PROCESSED_PATH, help="Verzeichnis der CSVs")
    return parser.parse_args(argv)


def _lesen(path: Path) -> pd.DataFrame:
    """CSV als Text lesen, damit unveränderte Zellen exakt erhalten bleiben."""
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _fmt1(wert: float) -> str:
    return "" if pd.isna(wert) else f"{float(wert):.1f}"


def _spalte_setzen(df: pd.DataFrame, spalte: str, neu: pd.Series, numerisch: bool) -> int:
    """Spalte setzen; numerisch gleiche Zellen behalten ihren Text. Gibt Anzahl Änderungen zurück."""
    if spalte not in df.columns:
        df.insert(df.columns.get_loc("beruf") + 1, spalte, "")
    alt = df[spalte]
    if numerisch:
        alt_num = pd.to_numeric(alt, errors="coerce")
        neu_num = pd.to_numeric(neu, errors="coerce")
        gleich = (alt_num.round(6) == neu_num.round(6)) | (alt_num.isna() & neu_num.isna())
    else:
        gleich = alt == neu
    df[spalte] = alt.where(gleich, neu)
    return int((~gleich).sum())


def beschaeftigte_setzen(pfad: Path, werte: pd.DataFrame, mapping: pd.DataFrame,
                         dry_run: bool = False) -> None:
    """beschaeftigte_1000, frauen_pct und synonyme in allen CSVs setzen."""
    w = werte.set_index("beruf")
    syn = mapping.set_index("beruf")["synonyme"]
    codes = mapping.set_index("beruf")["isco_code"]
    for name in CSV_DATEIEN:
        path = pfad / name
        if not path.exists():
            print(f"– {name}: nicht vorhanden, übersprungen")
            continue
        df = _lesen(path)
        fehlt = sorted(set(df["beruf"]) - set(w.index))
        if fehlt:
            raise SystemExit(f"{name}: Berufe ohne Eintrag in {MAPPING_CSV.name}: {fehlt}")
        falsch = df[df["isco_code"].str.strip() != df["beruf"].map(codes)]
        if not falsch.empty:
            raise SystemExit(f"{name}: isco_code weicht vom Mapping ab: {falsch['beruf'].tolist()}")
        vorher = pd.to_numeric(df["beschaeftigte_1000"], errors="coerce").sum()
        n_b = _spalte_setzen(df, "beschaeftigte_1000", df["beruf"].map(w["beschaeftigte_1000"]).map(_fmt1), True)
        n_f = _spalte_setzen(df, "frauen_pct", df["beruf"].map(w["frauen_pct"]).map(_fmt1), True)
        n_s = _spalte_setzen(df, "synonyme", df["beruf"].map(syn).fillna(""), False)
        nachher = pd.to_numeric(df["beschaeftigte_1000"], errors="coerce").sum()
        print(f"✓ {name}: {len(df)} Berufe; geändert: {n_b} Beschäftigte, {n_f} Frauenanteil, "
              f"{n_s} Synonyme; Σ Beschäftigte {vorher:,.1f} → {nachher:,.1f} Tsd.")
        if not dry_run:
            df.to_csv(path, index=False)


def ist_restgruppe(bezeichnung: str) -> bool:
    """Restgruppe der SE («onA», «anderweitig nicht genannt», «ohne nähere Angabe»)?"""
    return any(b in str(bezeichnung) for b in RESTGRUPPEN_BEGRIFFE)


def neue_kandidaten(se: pd.DataFrame, mapping: pd.DataFrame, blatt: str = DEFAULT_BLATT,
                    schwelle: float = NEUE_BERUFE_SCHWELLE) -> pd.DataFrame:
    """SE-Berufsgattungen >= schwelle (Tsd., Jahresblatt), die noch keinen Beruf haben.

    Restgruppen sind ausgeschlossen, ausser sie stehen in RESTGRUPPEN_AUSNAHMEN.
    Returns: DataFrame mit code, bezeichnung, total (nach Code sortiert).
    """
    g = _se_index(se, blatt, 4).reset_index()
    neu = g[(g["total"] >= schwelle) & ~g["code"].isin(set(mapping["isco_code"]))]
    rest = neu["bezeichnung"].map(ist_restgruppe) & ~neu["code"].isin(set(RESTGRUPPEN_AUSNAHMEN))
    return neu.loc[~rest, ["code", "bezeichnung", "total"]].sort_values("code").reset_index(drop=True)


def neue_berufe_aufnehmen(pfad: Path, se: pd.DataFrame, mapping: pd.DataFrame, blatt: str,
                          mapping_path: Path, dry_run: bool = False) -> pd.DataFrame:
    """Neue Berufsgattungen (neue_kandidaten) in das Mapping und alle CSVs aufnehmen.

    Beruf = SE-Bezeichnung, ebene «gattung». Branche, Qualifikation und LSE-Basislohn folgen
    aus dem ISCO-Code; Beschäftigte/Frauenanteil setzt danach beschaeftigte_setzen(). ESCO-Felder
    und Scores bleiben leer (beschreibung_hash leer) — die App zeigt solche Einträge als
    «noch nicht bewertet». Danach: ESCO-Zuordnung, update_loehne.py --offline, Scoring.
    """
    kandidaten = neue_kandidaten(se, mapping, blatt)
    if kandidaten.empty:
        print("✓ keine neuen Berufsgattungen")
        return mapping
    doppelt = set(kandidaten["bezeichnung"]) & set(mapping["beruf"])
    if doppelt:
        raise SystemExit(f"Neue Berufsgattung mit bestehendem Berufstitel: {sorted(doppelt)}")
    zeilen, neue_map = [], []
    for _, row in kandidaten.iterrows():
        code, beruf = str(row["code"]), row["bezeichnung"]
        branche, qualifikation, lohn = assign_metadata(code)
        zeilen.append({"beruf": beruf, "isco_code": code, "branche": branche,
                       "lohn_median_chf": str(lohn), "lohn_quelle": lse_basislohn(code, _lse())[1],
                       "lohn_unsicher": "False", "qualifikation": qualifikation,
                       "scores_gemittelt": "False"})
        neue_map.append({"beruf": beruf, "isco_code": code, "ebene": EBENE_GATTUNG,
                         "begruendung": RESTGRUPPEN_AUSNAHMEN.get(code, NEUE_BERUFE_BEGRUENDUNG)})
        print(f"  + {code} {beruf} ({row['total']:.1f} Tsd., {branche})")
    mapping = pd.concat([mapping, pd.DataFrame(neue_map)], ignore_index=True).fillna("")
    for name in CSV_DATEIEN:
        path = pfad / name
        if not path.exists():
            continue
        df = _lesen(path)
        neu = pd.DataFrame(zeilen).reindex(columns=df.columns).fillna("")
        df = pd.concat([df, neu], ignore_index=True)
        if not dry_run:
            df.to_csv(path, index=False)
    print(f"✓ {len(zeilen)} neue Berufe — danach ESCO-Zuordnung, update_loehne.py --offline "
          "und Scoring ausführen")
    if not dry_run:
        mapping.to_csv(mapping_path, index=False)
    return mapping


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    blaetter = tuple(dict.fromkeys([args.blatt, POOL_BLATT]))
    se = lade_se(blaetter, raw=BFS_FILE, csv=args.pfad / SE_CSV.name, schreiben=not args.dry_run)
    n_gattungen = int(((se["blatt"] == args.blatt) & (se["ebene"].astype(int) == 4)).sum())
    print(f"✓ BFS Strukturerhebung (SE), Blatt «{args.blatt}»: {n_gattungen} Berufsgattungen gelesen")
    mapping_path = args.pfad / MAPPING_CSV.name
    mapping = lade_mapping(mapping_path)
    if args.neue_berufe:
        mapping = neue_berufe_aufnehmen(args.pfad, se, mapping, args.blatt, mapping_path, args.dry_run)
    werte = beschaeftigte_berechnen(mapping, se, blatt=args.blatt)
    print(f"✓ {len(werte)} Berufe, {werte['isco_code'].nunique()} Berufsgattungen, "
          f"Σ {werte['beschaeftigte_1000'].sum():,.1f} Tsd. Erwerbstätige")
    beschaeftigte_setzen(args.pfad, werte, mapping, dry_run=args.dry_run)
    print("→ Löhne (Gewichte = Beschäftigte): python src/data/update_loehne.py --offline")


if __name__ == "__main__":
    main()
