"""
Löhne auf BFS LSE 2024 umstellen (ersetzt die geschätzte LOHN_MAP).

Quelle Basis: BFS Lohnstrukturerhebung (LSE) 2024, Tabelle T17 «Monatlicher Bruttolohn
(Zentralwert) nach Berufsgruppen, Lebensalter und Geschlecht — Privater und öffentlicher
Sektor zusammen», Asset 36355224, Datei je-d-03.04.01.02.47.xlsx (Blatt «2024»):
https://www.bfs.admin.ch/bfs/de/home/statistiken/kataloge-datenbanken.assetdetail.36355224.html
Die LSE publiziert Berufe nur 2-stellig (CH-ISCO-19-Untergruppen). Der Wert ist der
standardisierte Monatslohn (Vollzeit, inkl. 1/12 des 13. Monatslohns und 1/12 der
Sonderzahlungen) → Jahreslohn = Monatslohn × 12.

Methode
1. Basis (alle Berufe): lohn_median_chf = LSE-2024-Median der 2-stelligen Gruppe × 12,
   lohn_quelle = "LSE2024_2d". Gruppen ohne LSE-Wert (01–03 Armee, 63, 95) fallen auf die
   1-stellige Hauptgruppe ("LSE2024_1d") bzw. den Gesamtmedian ("LSE2024_total") zurück.
2. Heterogene Gruppen (11–14, 22, 24, 26): Profilmethode mit BFS Salarium (Lohnrechner auf
   Basis LSE 2024, nur Privatsektor). Jeder Beruf hat ein festes Profil in
   data/processed/lohn_profile_salarium.csv (Salarium-Berufsgruppe, NOGA-Abteilung der
   Hauptbranche, formale Pflichtausbildung). Alle übrigen Merkmale sind für alle Berufe
   gleich (NORMPROFIL). Kalibrierung auf die LSE je 2-stelliger LSE-Gruppe g:

       lohn_j = LSE_g × 12 × S_j / S̄_g,   S̄_g = Σ_k∈g w_k·S_k / Σ_k∈g w_k

   S_j = Salarium-Median des Profils von Beruf j, als Mittel über die 7 Grossregionen
   gewichtet mit den Vollzeitäquivalenten der jeweiligen NOGA-Abteilung (BFS STATENT).
   w_k = beschaeftigte_1000 (aus berufe_ch.csv, BFS SE). Damit ist das
   beschäftigungsgewichtete Mittel der kalibrierten Löhne der Gruppe gleich dem
   LSE-Gruppenmedian × 12: Salarium verteilt nur um (Branche, Ausbildung), das Niveau
   stammt aus der LSE. Berufe der Gruppe ohne Salarium-Wert (z. B. 1112, NOGA 84 nicht
   im Salarium-Modell) erhalten S = S̄_g, also LSE_g × 12, und zählen nicht in S̄_g.
   lohn_quelle = "LSE2024_2d+Salarium". Für die Führungskräfte (Salarium-Gruppe 10 =
   ISCO 11–14) wird je LSE-Gruppe 11, 12, 13, 14 separat normiert.
3. scores.csv: regelbasierte Folgespalten neu berechnen — lohnklasse, delta_lohn,
   delta_branche, score_ch (ch_adjustments.apply_ch_adjustments) und adaptabilitaet
   (adaptability_scorer.berechne_adaptabilitaet). LLM-Scores und Texte bleiben unverändert.

Dateien (data/processed/, versioniert, damit die Pipeline ohne Rohdaten läuft):
    lse2024_monatslohn_isco.csv   LSE-2024-Mediane (Total, 1- und 2-stellig) aus T17
    lohn_profile_salarium.csv     Salarium-Profil je Beruf (manuell gepflegt)
    lohn_salarium_abfragen.csv    Salarium-Antworten je Profil und Grossregion
    statent_vzae_grossregion.csv  STATENT-VZÄ je NOGA-Abteilung und Grossregion (Gewichte)

Aufruf:
    python src/data/update_loehne.py --offline            # gespeicherte Salarium-Werte
    python src/data/update_loehne.py                      # Salarium neu abfragen
    python src/data/update_loehne.py --offline --dry-run  # nur anzeigen
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "scoring"))

from adaptability_scorer import berechne_adaptabilitaet  # noqa: E402
from ch_adjustments import apply_ch_adjustments  # noqa: E402

ROOT = Path(__file__).parent.parent.parent
RAW_PATH = ROOT / "data" / "raw"
PROCESSED_PATH = ROOT / "data" / "processed"

LSE_RAW = RAW_PATH / "je-d-03.04.01.02.47.xlsx"
LSE_BLATT = "2024"
LSE_CSV = PROCESSED_PATH / "lse2024_monatslohn_isco.csv"
PROFILE_CSV = PROCESSED_PATH / "lohn_profile_salarium.csv"
SALARIUM_CSV = PROCESSED_PATH / "lohn_salarium_abfragen.csv"
STATENT_CSV = PROCESSED_PATH / "statent_vzae_grossregion.csv"

BASIS_DATEIEN = ["berufe_ch.csv", "berufe_ch_esco.csv", "berufe_ch_esco_verified.csv"]
SCORES_DATEI = "scores.csv"
BESCHAEFTIGTE_DATEI = "berufe_ch.csv"  # Quelle der Gewichte w_k (beschaeftigte_1000)

MONATE = 12  # LSE-Monatslohn enthält 13. Monatslohn und Sonderzahlungen bereits anteilig

QUELLE_2D = "LSE2024_2d"
QUELLE_1D = "LSE2024_1d"
QUELLE_TOTAL = "LSE2024_total"
QUELLE_SALARIUM = "LSE2024_2d+Salarium"

# 2-stellige Gruppen, in denen die Salarium-Profilmethode angewendet wird
HETEROGENE_GRUPPEN: frozenset[str] = frozenset({"11", "12", "13", "14", "22", "24", "26"})

# Salarium-Ausbildungscodes (GET /api/Data/code/education-levels)
AUSBILDUNG_CODES: dict[str, int] = {
    "UNI": 1,   # Universitäre Hochschule (UNI, ETH)
    "FH": 2,    # Fachhochschule (FH), Pädagogische Hochschule (PH)
    "HBB": 3,   # Höhere Berufsbildung, Höhere Fachschule (HF)
    "LS": 4,    # Lehrerseminar
    "MAT": 5,   # Matura
    "EFZ": 6,   # Abgeschlossene Berufsausbildung (EFZ)
    "INT": 7,   # Unternehmensinterne Berufsausbildung
    "OHNE": 8,  # Ohne abgeschlossene Berufsausbildung
}
STANDARD = "STANDARD"  # Salarium-Default der Kombination NOGA × Grossregion × Gruppe

# Für alle Profile identische Merkmale. Alter/Dienstjahre/Arbeitszeit gemäss Issue #45;
# keine Kader- und keine Sonderzahlungsannahme. Nur das Verhältnis S_j / S̄_g geht in
# den Lohn ein — das Niveau kommt aus der LSE.
NORMPROFIL: dict[str, int] = {
    "ageCode": 42,
    "workYearCode": 8,
    "workHourValue": 40,
    "managementLevelCode": 3,     # ohne Kaderfunktion
    "genderCode": 0,
    "permitCode": 1,              # Schweizer/innen
    "companySizeCode": 3,         # 50 und mehr Beschäftigte
    "hasBonusCode": 0,
    "hasThirteenSalaryCode": 1,
    "hasHourContractCode": 0,     # Monatslohn
}

# Salarium-Grossregionen (GET /api/Data/code/regions) und zugehörige Kantone (BFS-Nr.)
GROSSREGIONEN: dict[int, tuple[str, tuple[int, ...]]] = {
    1: ("Genferseeregion", (22, 23, 25)),
    2: ("Espace Mittelland", (2, 10, 11, 24, 26)),
    3: ("Nordwestschweiz", (12, 13, 19)),
    4: ("Zürich", (1,)),
    5: ("Ostschweiz", (8, 14, 15, 16, 17, 18, 20)),
    6: ("Zentralschweiz", (3, 4, 5, 6, 7, 9)),
    7: ("Tessin", (21,)),
}

SALARIUM_BASE = "https://www.salarium.bfs.admin.ch"
SALARIUM_PAUSE_S = 1.2
STATENT_URL = (
    "https://www.pxweb.bfs.admin.ch/api/v1/de/"
    "px-x-0602010000_101/px-x-0602010000_101.px"
)
HTTP_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "ki-jobexposition-schweiz (Forschung, sequenziell, geringe Last)",
}


# ---------------------------------------------------------------------------
# LSE 2024
# ---------------------------------------------------------------------------

def parse_lse_excel(path: Path, blatt: str = LSE_BLATT) -> pd.DataFrame:
    """T17-Excel lesen → isco_prefix ("" = Total, 1- oder 2-stellig), ebene, bezeichnung, median_monat."""
    df = pd.read_excel(path, sheet_name=blatt, header=None)
    rows = []
    for _, r in df.iterrows():
        code = "" if pd.isna(r[0]) else str(r[0]).strip()
        label = "" if pd.isna(r[1]) else str(r[1]).strip()
        if code == "" and label.upper() == "TOTAL":
            ebene = 0
        elif re.fullmatch(r"\d{1,2}", code):
            ebene = len(code)
        else:
            continue
        wert = r[3]
        if isinstance(wert, str):
            m = re.search(r"\d+", wert.replace("'", ""))
            wert = float(m.group(0)) if m else None
        rows.append({"isco_prefix": code, "ebene": ebene, "bezeichnung": label,
                     "median_monat": None if pd.isna(wert) else int(wert)})
    return pd.DataFrame(rows)


def lade_lse(raw: Path = LSE_RAW, csv: Path = LSE_CSV, schreiben: bool = True) -> dict[str, int]:
    """LSE-Mediane als {präfix: Monatslohn}; Rohdatei bevorzugt, sonst versionierte CSV."""
    if raw.exists():
        tab = parse_lse_excel(raw)
        if schreiben:
            tab.to_csv(csv, index=False)
    else:
        tab = pd.read_csv(csv, dtype={"isco_prefix": str}, keep_default_na=False)
    tab = tab[tab["median_monat"].astype(str) != ""]
    return {str(p): int(float(v)) for p, v in zip(tab["isco_prefix"], tab["median_monat"])}


def lse_basislohn(isco_code: str, lse: dict[str, int]) -> tuple[int, str]:
    """Jahreslohn und Quelle aus der LSE: 2-stellig → 1-stellig → Total."""
    code = str(isco_code).strip()
    if code[:2] in lse:
        return lse[code[:2]] * MONATE, QUELLE_2D
    if code[:1] in lse:
        return lse[code[:1]] * MONATE, QUELLE_1D
    return lse[""] * MONATE, QUELLE_TOTAL


# ---------------------------------------------------------------------------
# Salarium-Profile
# ---------------------------------------------------------------------------

def salarium_gruppe(isco_code: str) -> int:
    """Salarium-Berufsgruppe: 2-stellig, Führungskräfte 11–14 zusammengefasst (10)."""
    zwei = int(str(isco_code)[:2])
    return 10 if 11 <= zwei <= 14 else zwei


def lade_profile(path: Path = PROFILE_CSV) -> pd.DataFrame:
    prof = pd.read_csv(path, dtype={"isco_code": str})
    unbekannt = set(prof["ausbildung"]) - set(AUSBILDUNG_CODES) - {STANDARD}
    if unbekannt:
        raise ValueError(f"Unbekannte Ausbildung in {path.name}: {sorted(unbekannt)}")
    falsch = prof[prof["isco_code"].map(salarium_gruppe) != prof["salarium_gruppe"]]
    if not falsch.empty:
        raise ValueError(f"salarium_gruppe passt nicht zum ISCO-Code: {falsch['beruf'].tolist()}")
    return prof


def benoetigte_abfragen(profile: pd.DataFrame) -> list[tuple[int, int, str]]:
    """Alle (salarium_gruppe, noga, ausbildung) der Profile, sortiert und eindeutig."""
    return sorted({(int(r.salarium_gruppe), int(r.noga), str(r.ausbildung)) for r in profile.itertuples()})


class SalariumClient:
    """Minimaler, zurückhaltender Client (sequenziell, Pause vor jedem Request)."""

    def __init__(self, pause: float = SALARIUM_PAUSE_S):
        import requests

        self.pause = pause
        self.session = requests.Session()
        self.session.headers.update(HTTP_HEADERS)

    def _get(self, pfad: str):
        time.sleep(self.pause)
        r = self.session.get(SALARIUM_BASE + pfad, timeout=30)
        r.raise_for_status()
        return r

    def konsistent(self, noga: int, region: int, gruppe: int) -> bool:
        return self._get(f"/api/Calculation/consistent/{noga}/{region}/{gruppe}").text.strip() == "true"

    def standard(self, noga: int, region: int, gruppe: int) -> dict:
        return self._get(f"/api/Calculation/default/{noga}/{region}/{gruppe}").json()

    def median(self, body: dict) -> tuple[int | None, int | None]:
        time.sleep(self.pause)
        r = self.session.post(SALARIUM_BASE + "/api/Calculation/calculate-salary", json=body, timeout=30)
        r.raise_for_status()
        js = r.json()
        werte = {x["code"]: x["value"] for x in js.get("statisticalResults") or []}
        return werte.get(50), js.get("quality")


def abfragen_salarium(specs: list[tuple[int, int, str]], client: SalariumClient) -> pd.DataFrame:
    """Salarium-Median je Spezifikation und Grossregion abfragen."""
    heute = date.today().isoformat()
    rows, konsistenz, defaults = [], {}, {}
    for gruppe, noga, ausbildung in specs:
        for region in GROSSREGIONEN:
            key = (noga, region, gruppe)
            if key not in konsistenz:
                konsistenz[key] = client.konsistent(*key)
            row = {"salarium_gruppe": gruppe, "noga": noga, "ausbildung": ausbildung,
                   "region": region, "konsistent": konsistenz[key], "ausbildung_code": None,
                   "median_monat": None, "qualitaet": None, "abfrage_datum": heute}
            if konsistenz[key]:
                if ausbildung == STANDARD:
                    if key not in defaults:
                        defaults[key] = client.standard(*key)
                    code = int(defaults[key]["educationLevelCode"])
                else:
                    code = AUSBILDUNG_CODES[ausbildung]
                body = dict(NORMPROFIL, nogaId=noga, regionCode=region,
                            occupationalGroupCode=gruppe, educationLevelCode=code)
                med, qual = client.median(body)
                row.update(ausbildung_code=code, median_monat=med, qualitaet=qual)
            rows.append(row)
            print(f"  Salarium {gruppe}/{noga}/{ausbildung}/R{region}: "
                  f"{row['median_monat'] if row['konsistent'] else 'nicht konsistent'}", flush=True)
    df = pd.DataFrame(rows)
    for spalte in ["ausbildung_code", "median_monat", "qualitaet"]:
        df[spalte] = df[spalte].astype("Int64")
    df["normprofil_id"] = normprofil_id()
    return df


def normprofil_id(profil: dict[str, int] | None = None) -> str:
    """Kurze Kennung des Normprofils (erkennt veraltete gespeicherte Abfragen)."""
    text = json.dumps(profil or NORMPROFIL, sort_keys=True)
    return hashlib.sha256(text.encode()).hexdigest()[:10]


# ---------------------------------------------------------------------------
# STATENT-Gewichte
# ---------------------------------------------------------------------------

def abfragen_statent() -> pd.DataFrame:
    """VZÄ je Kanton × NOGA-Abteilung (neuestes STATENT-Jahr) → je Grossregion summiert."""
    import requests

    meta = requests.get(STATENT_URL, headers=HTTP_HEADERS, timeout=60).json()
    jahr = max(meta["variables"][0]["values"])
    kantone = [str(k) for _, (_, ks) in GROSSREGIONEN.items() for k in ks]
    query = {
        "query": [
            {"code": "Jahr", "selection": {"filter": "item", "values": [jahr]}},
            {"code": "Kanton", "selection": {"filter": "item", "values": kantone}},
            {"code": "Wirtschaftsabteilung", "selection": {"filter": "all", "values": ["*"]}},
            {"code": "Beobachtungseinheit", "selection": {"filter": "item", "values": ["5"]}},
        ],
        "response": {"format": "json"},
    }
    data = requests.post(STATENT_URL, json=query, headers=HTTP_HEADERS, timeout=120).json()["data"]
    kanton_region = {k: r for r, (_, ks) in GROSSREGIONEN.items() for k in ks}
    rows = []
    for d in data:
        _, kanton, noga, _ = d["key"]
        if noga == "999":
            continue
        # «X» (Datenschutz), «...» u. ä. → 0
        vzae = pd.to_numeric(d["values"][0], errors="coerce")
        rows.append({"noga": int(noga), "region": kanton_region[int(kanton)],
                     "vzae": 0.0 if pd.isna(vzae) else float(vzae)})
    out = pd.DataFrame(rows).groupby(["noga", "region"], as_index=False)["vzae"].sum()
    out["vzae"] = out["vzae"].round(0).astype(int)
    out.insert(0, "jahr", int(jahr))
    return out


def gewichteter_salarium_wert(abfragen: pd.DataFrame, gewichte: pd.DataFrame,
                              gruppe: int, noga: int, ausbildung: str) -> float | None:
    """VZÄ-gewichtetes Mittel der Salarium-Mediane über die konsistenten Grossregionen."""
    sel = abfragen[(abfragen["salarium_gruppe"] == gruppe) & (abfragen["noga"] == noga)
                   & (abfragen["ausbildung"] == ausbildung) & abfragen["median_monat"].notna()]
    if sel.empty:
        return None
    w = gewichte[gewichte["noga"] == noga].set_index("region")["vzae"]
    gew = sel["region"].map(w).fillna(0.0).astype(float)
    if gew.sum() <= 0:  # keine Gewichte → ungewichtetes Mittel
        return float(sel["median_monat"].astype(float).mean())
    return float((sel["median_monat"].astype(float) * gew).sum() / gew.sum())


def gruppen_mittel(s_werte: list[float], gewichte_w: list[float]) -> float:
    """S̄_g = Σ w_k·S_k / Σ w_k (beschäftigungsgewichtetes Mittel der Salarium-Werte)."""
    summe_w = float(sum(gewichte_w))
    if summe_w <= 0:  # keine Beschäftigtenzahlen → ungewichtet
        return float(sum(s_werte)) / len(s_werte)
    return float(sum(s * w for s, w in zip(s_werte, gewichte_w))) / summe_w


def kalibrierter_lohn(lse_monat: float, s_beruf: float, s_mittel: float) -> int:
    """lohn_j = LSE_g × 12 × S_j / S̄_g, auf 100 CHF gerundet."""
    return int(round(lse_monat * MONATE * s_beruf / s_mittel / 100.0) * 100)


# ---------------------------------------------------------------------------
# Lohn je Beruf
# ---------------------------------------------------------------------------

def berechne_loehne(df: pd.DataFrame, lse: dict[str, int], profile: pd.DataFrame,
                    abfragen: pd.DataFrame | None, gewichte: pd.DataFrame | None,
                    beschaeftigte: dict[tuple[str, str], float] | None = None) -> pd.DataFrame:
    """Je Zeile (beruf, isco_code) → lohn_median_chf, lohn_quelle.

    beschaeftigte: Gewichte w_k je (isco_code, beruf); Default = Spalte beschaeftigte_1000 von df.
    """
    codes = df["isco_code"].astype(str).str.strip().tolist()
    berufe = df["beruf"].tolist()
    if beschaeftigte is None:
        w_spalte = pd.to_numeric(df.get("beschaeftigte_1000", pd.Series(0.0, index=df.index)),
                                 errors="coerce").fillna(0.0)
        beschaeftigte = dict(zip(zip(codes, berufe), w_spalte))
    prof = {(str(r.isco_code), r.beruf): r for r in profile.itertuples()}

    # 1) Basis LSE und Salarium-Wert S_j je Zeile
    basis, s_j = [], []
    for code, beruf in zip(codes, berufe):
        lohn, quelle = lse_basislohn(code, lse)
        basis.append((lohn, quelle))
        p = prof.get((code, beruf))
        s = None
        if p is not None and quelle == QUELLE_2D and abfragen is not None and gewichte is not None:
            s = gewichteter_salarium_wert(abfragen, gewichte, int(p.salarium_gruppe),
                                          int(p.noga), str(p.ausbildung))
            if not s:
                print(f"  ! Kein Salarium-Wert für {code} {beruf} (Kombination in Salarium "
                      f"nicht konsistent) → {QUELLE_2D}")
        elif p is None and code[:2] in HETEROGENE_GRUPPEN:
            print(f"  ! Kein Salarium-Profil für {code} {beruf} → {QUELLE_2D}")
        s_j.append(s or None)

    # 2) S̄_g je 2-stelliger LSE-Gruppe (nur Berufe mit Salarium-Wert)
    gruppen: dict[str, tuple[list[float], list[float]]] = {}
    for code, beruf, s in zip(codes, berufe, s_j):
        if s:
            werte, w = gruppen.setdefault(code[:2], ([], []))
            werte.append(s)
            w.append(float(beschaeftigte.get((code, beruf), 0.0) or 0.0))
    mittel = {g: gruppen_mittel(werte, w) for g, (werte, w) in gruppen.items()}

    # 3) lohn_j = LSE_g × 12 × S_j / S̄_g; ohne S_j bleibt LSE_g × 12
    out = []
    for code, (lohn, quelle), s in zip(codes, basis, s_j):
        if s:
            lohn, quelle = kalibrierter_lohn(lse[code[:2]], s, mittel[code[:2]]), QUELLE_SALARIUM
        out.append({"lohn_median_chf": lohn, "lohn_quelle": quelle})
    return pd.DataFrame(out, index=df.index)


def _lesen(path: Path) -> pd.DataFrame:
    """CSV als Text lesen, damit unveränderte Zellen exakt erhalten bleiben."""
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _lohn_spalten_setzen(text_df: pd.DataFrame, loehne: pd.DataFrame) -> pd.DataFrame:
    out = text_df.copy()
    out["lohn_median_chf"] = loehne["lohn_median_chf"].astype(int).astype(str)
    if "lohn_quelle" not in out.columns:
        pos = out.columns.get_loc("lohn_median_chf") + 1
        out.insert(pos, "lohn_quelle", "")
    out["lohn_quelle"] = loehne["lohn_quelle"]
    return out


def _fmt(v: float) -> str:
    return "" if pd.isna(v) else repr(round(float(v), 4))


def scores_folgespalten(text_df: pd.DataFrame) -> pd.DataFrame:
    """Lohnabhängige, regelbasierte Spalten in scores.csv für alle Zeilen neu berechnen."""
    num = text_df.copy()
    for spalte in ["lohn_median_chf", "score_gesamt", "score_digital"]:
        num[spalte] = pd.to_numeric(num[spalte])
    num["branche"] = num["branche"].replace("", pd.NA)
    res = apply_ch_adjustments(num)
    res["adaptabilitaet"] = berechne_adaptabilitaet(res)

    out = text_df.copy()
    out["lohnklasse"] = res["lohnklasse"]
    for spalte in ["delta_branche", "delta_lohn", "score_ch", "adaptabilitaet"]:
        neu = res[spalte].map(_fmt)
        # Zellen mit numerisch gleichem Wert unverändert lassen (Formatierung erhalten)
        alt = pd.to_numeric(out[spalte], errors="coerce") if spalte in out.columns else None
        if alt is not None:
            gleich = (alt.round(6) == res[spalte].astype(float).round(6))
            neu = neu.where(~gleich, out[spalte])
        out[spalte] = neu
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--offline", action="store_true",
                        help="gespeicherte Salarium- und STATENT-Werte verwenden (kein Netz)")
    parser.add_argument("--dry-run", action="store_true", help="Änderungen nur anzeigen")
    parser.add_argument("--pfad", type=Path, default=PROCESSED_PATH, help="Verzeichnis der CSVs")
    args = parser.parse_args(argv)

    lse = lade_lse(raw=LSE_RAW, csv=args.pfad / LSE_CSV.name, schreiben=not args.dry_run)
    print(f"✓ LSE 2024: {len(lse)} Mediane (Total, 1- und 2-stellig)")
    profile = lade_profile(args.pfad / PROFILE_CSV.name)

    statent_path = args.pfad / STATENT_CSV.name
    salarium_path = args.pfad / SALARIUM_CSV.name
    if args.offline:
        gewichte = pd.read_csv(statent_path)
        abfragen = pd.read_csv(salarium_path)
        if "normprofil_id" in abfragen and set(abfragen["normprofil_id"]) != {normprofil_id()}:
            raise SystemExit(f"{salarium_path.name} passt nicht zum NORMPROFIL — ohne --offline neu abfragen")
    else:
        gewichte = abfragen_statent()
        print(f"✓ STATENT {gewichte['jahr'].iloc[0]}: {len(gewichte)} NOGA × Grossregion")
        abfragen = abfragen_salarium(benoetigte_abfragen(profile), SalariumClient())
        if not args.dry_run:
            gewichte.to_csv(statent_path, index=False)
            abfragen.to_csv(salarium_path, index=False)
    print(f"✓ Salarium: {len(abfragen)} Abfragen ({int(abfragen['median_monat'].notna().sum())} mit Wert)")

    # Gewichte w_k für S̄_g einheitlich aus berufe_ch.csv (BFS SE), damit alle CSVs
    # dieselben Löhne erhalten; fehlt die Datei, nutzt jede CSV ihre eigene Spalte.
    beschaeftigte = None
    basis_path = args.pfad / BESCHAEFTIGTE_DATEI
    b = pd.read_csv(basis_path, dtype={"isco_code": str}) if basis_path.exists() else None
    if b is not None and "beschaeftigte_1000" in b.columns:
        beschaeftigte = dict(zip(zip(b["isco_code"].str.strip(), b["beruf"]),
                                 pd.to_numeric(b["beschaeftigte_1000"], errors="coerce").fillna(0.0)))

    for name in BASIS_DATEIEN + [SCORES_DATEI]:
        path = args.pfad / name
        if not path.exists():
            print(f"– {name}: nicht vorhanden, übersprungen")
            continue
        df = _lesen(path)
        loehne = berechne_loehne(df, lse, profile, abfragen, gewichte, beschaeftigte)
        alt = pd.to_numeric(df["lohn_median_chf"], errors="coerce")
        geaendert = alt != loehne["lohn_median_chf"]
        print(f"✓ {name}: {int(geaendert.sum())} Zeilen mit neuem Lohn")
        out = _lohn_spalten_setzen(df, loehne)
        if name == SCORES_DATEI:
            out = scores_folgespalten(out)
        if not args.dry_run:
            out.to_csv(path, index=False)


if __name__ == "__main__":  # pragma: no cover
    main()
