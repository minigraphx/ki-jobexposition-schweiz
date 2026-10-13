"""
fetch_statent.py — Grossfirmen-Anteil pro Branche aus BFS STATENT (KMU-Adoptions-Faktor)

Quelle — BFS Statistik der Unternehmensstruktur (STATENT), Tabelle ts-x-06.02.01.01
    «Marktwirtschaftliche Unternehmen nach Wirtschaftsabteilungen und Grössenklasse»
    (CSV, OGD, jährlich seit 2011; Stand der Ausgabe 2011–2024: 20.08.2026).
    Metadaten/Download über die DAM-API des BFS (öffentlich, ohne Schlüssel):
        https://dam-api.bfs.admin.ch/hub/api/dam/assets?orderNr=ts-x-06.02.01.01
        → Asset mit lifecycle CURRENT → Link rel=master (CSV)
    Spalten: PERIOD, NOGA (Abteilung 01–96, 999 = Total), SIZE (1: 1–9, 2: 10–49,
    3: 50–249, 4: ≥250 Beschäftigte, 999 = Total), INDICATOR (1 = Unternehmen,
    2 = Beschäftigte), VALUE, STATUS (A = normal, Q = aus Datenschutzgründen gesperrt).

Begriffe:
    - Einheit: **Unternehmen** (rechtliche Einheit inkl. aller Arbeitsstätten), nicht
      Arbeitsstätte. Alle Beschäftigten eines Unternehmens zählen zu dessen Haupttätigkeit
      (NOGA) und Grössenklasse. Für «KI-Adoption in Grossfirmen» ist das der fachlich
      richtige Begriff: Investitions- und IT-Entscheide fallen auf Unternehmensebene
      (eine Coop-Filiale ist keine KMU).
    - Grössenklasse nach **Beschäftigten** (Köpfe inkl. Teilzeit), nicht nach VZÄ;
      gezählt werden ebenfalls Beschäftigte. Eine VZÄ-Variante je Abteilung × Grössenklasse
      publiziert das BFS nicht.
    - Nur **marktwirtschaftliche** Unternehmen: nicht-marktwirtschaftliche institutionelle
      Einheiten (öffentliche Verwaltung, öffentliche Schulen, Teile des Sozialwesens) fehlen.
      NOGA 84 ist daher leer → «Öff. Verwaltung» erhält keinen Anteil (Verschiebung 0).
      Die Spalte `abdeckung` zeigt je Branche den Anteil der STATENT-Beschäftigten
      (alle Arbeitsstätten, statent_beschaeftigte_noga.csv), den die Tabelle abdeckt.

Gesperrte Werte (STATUS Q):
    Je NOGA-Abteilung wird die Differenz «Total − bekannte Grössenklassen» zu gleichen
    Teilen auf die gesperrten Klassen verteilt. Ist auch das Total gesperrt, werden die
    gesperrten Klassen 0 gesetzt (betrifft 2024 nur NOGA 06/09 mit < 100 Beschäftigten).
    Die Spannweite des Branchenanteils (Rest ganz/gar nicht in ≥250) wird geloggt.

Definition:
    grossfirmen_anteil[branche] = Σ Beschäftigte in Unternehmen ≥250 Beschäftigte
                                  / Σ Beschäftigte (alle Grössenklassen)
    über alle NOGA-Abteilungen der Branche (Mapping NOGA_ZU_BRANCHE).

Dateien:
    data/raw/statent_ts-x-06.02.01.01.csv             Rohdownload (gitignored)
    data/processed/statent_groessenklassen_noga.csv  aufbereitet, alle Jahre:
        jahr, noga, groessenklasse, unternehmen, unternehmen_status,
        beschaeftigte, beschaeftigte_status
    data/processed/kmu_anteil_branche.csv            Ergebnis je interner Branche:
        branche, beschaeftigte_total, beschaeftigte_gross, grossfirmen_anteil,
        quelle, jahr, einheit, abdeckung

Aufruf:
    python src/data/fetch_statent.py                  # online laden, beide CSVs schreiben
    python src/data/fetch_statent.py --offline        # versionierte Tabelle verwenden
    python src/data/fetch_statent.py --year 2023      # anderes STATENT-Jahr
    python src/data/fetch_statent.py --offline --apply-scores --dry-run
        # zeigt, wie sich grossfirmen_anteil / zeitrahmen_kmu_delta / zeitrahmen in
        # scores.csv ändern würden, ohne etwas zu schreiben
    python src/data/fetch_statent.py --offline --apply-scores
        # kmu_anteil_branche.csv schreiben und die drei KMU-Spalten in scores.csv neu
        # berechnen (ausgehend von zeitrahmen_roh; alle anderen Zellen bleiben byte-gleich)

Historie: Bis Oktober 2026 stammte der Anteil aus der Betriebszählung 2008
(px-x-0602050000_102, Arbeitsstätten ≥250 VZÄ). Die Werte sind in der Git-Historie;
der Vergleich alt/neu steht in der Methodik-Seite.
"""

from __future__ import annotations

import argparse
import io
import logging
import sys
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent.parent
PROCESSED_DATA_PATH = ROOT / "data" / "processed"
RAW_DATA_PATH = ROOT / "data" / "raw"

STATENT_GK_BESTELLNR = "ts-x-06.02.01.01"
DAM_ASSETS_URL = "https://dam-api.bfs.admin.ch/hub/api/dam/assets"
HTTP_HEADERS = {"User-Agent": "ki-jobexposition-schweiz (Forschung, sequenziell, geringe Last)"}

RAW_CSV = RAW_DATA_PATH / f"statent_{STATENT_GK_BESTELLNR}.csv"
GROESSENKLASSEN_CSV = PROCESSED_DATA_PATH / "statent_groessenklassen_noga.csv"
STATENT_NOGA_CSV = PROCESSED_DATA_PATH / "statent_beschaeftigte_noga.csv"
KMU_CSV = PROCESSED_DATA_PATH / "kmu_anteil_branche.csv"
SCORES_CSV = PROCESSED_DATA_PATH / "scores.csv"

# SIZE-Codes der BFS-Tabelle → lesbare Grössenklasse
GROESSENKLASSEN: dict[str, str] = {
    "1": "1-9",
    "2": "10-49",
    "3": "50-249",
    "4": "250+",
    "999": "total",
}
KLASSEN_DETAIL = ["1-9", "10-49", "50-249", "250+"]
GROSSFIRMEN_KLASSE = "250+"
INDIKATOREN = {"1": "unternehmen", "2": "beschaeftigte"}

QUELLE = f"BFS STATENT {STATENT_GK_BESTELLNR} (marktwirtschaftliche Unternehmen)"
EINHEIT = "Beschäftigte in Unternehmen mit ≥250 Beschäftigten"

# NOGA-Abteilung (2-stellig) → interne Branche
# Alle 85 NOGA-Abteilungen 01–96 der STATENT-Tabellen sind gemappt (97–99 fehlen in STATENT).
# Abteilungen die mehreren internen Branchen zuzuordnen wären, erhalten
# die dominante Branche nach Beschäftigtenzahl.
NOGA_ZU_BRANCHE: dict[str, str] = {
    # Landwirtschaft / Forstwirtschaft / Fischerei
    "01": "Landwirtschaft",
    "02": "Landwirtschaft",
    "03": "Landwirtschaft",
    # Bergbau → Industrie (klein, aber Rohstoffgewinnung)
    "05": "Industrie",
    "06": "Industrie",
    "07": "Industrie",
    "08": "Umwelt",
    "09": "Industrie",
    # Verarbeitendes Gewerbe (MEM, Pharma, Chemie, Nahrungsmittel …)
    "10": "Industrie",
    "11": "Industrie",
    "12": "Industrie",
    "13": "Industrie",
    "14": "Industrie",
    "15": "Industrie",
    "16": "Industrie",
    "17": "Industrie",
    "18": "Medien",       # Druck / Vervielfältigung → Medien
    "19": "Industrie",
    "20": "Industrie",
    "21": "Industrie",    # Pharma → Industrie (Roche, Novartis)
    "22": "Industrie",
    "23": "Industrie",
    "24": "Industrie",
    "25": "Industrie",
    "26": "ICT",          # Elektronik/Optik → ICT-nah
    "27": "Industrie",
    "28": "Industrie",
    "29": "Industrie",
    "30": "Industrie",
    "31": "Industrie",
    "32": "Industrie",
    "33": "Industrie",
    # Energie / Wasser / Abfall
    "35": "Umwelt",
    "36": "Umwelt",
    "37": "Umwelt",
    "38": "Umwelt",
    "39": "Umwelt",
    # Bau
    "41": "Bau",
    "42": "Bau",
    "43": "Bau",
    # Handel
    "45": "Detailhandel",  # Autohandel
    "46": "Dienstleistungen",  # Grosshandel → Dienstleistungen
    "47": "Detailhandel",
    # Transport / Logistik
    "49": "Transport",
    "50": "Transport",
    "51": "Transport",
    "52": "Transport",
    "53": "Transport",
    # Gastgewerbe
    "55": "Gastgewerbe",
    "56": "Gastgewerbe",
    # Medien / ICT
    "58": "Medien",
    "59": "Medien",
    "60": "Medien",
    "61": "ICT",
    "62": "ICT",
    "63": "ICT",
    # Finanz- und Versicherungsdienstleistungen
    "64": "Finanzen",
    "65": "Versicherungen",
    "66": "Finanzen",
    # Immobilien
    "68": "Immobilien",
    # Freiberufliche / wissenschaftliche / technische Tätigkeiten
    "69": "Recht",
    "70": "Beratung",
    "71": "Beratung",
    "72": "Dienstleistungen",  # Forschung & Entwicklung
    "73": "Medien",            # Werbung
    "74": "Dienstleistungen",
    "75": "Gesundheit",        # Veterinärwesen
    # Sonstige wirtschaftliche Dienstleistungen
    "77": "Dienstleistungen",
    "78": "Dienstleistungen",
    "79": "Gastgewerbe",       # Reisebüros → Gastgewerbe-nah
    "80": "Sicherheit",
    "81": "Dienstleistungen",
    "82": "Dienstleistungen",
    # Öffentliche Verwaltung
    "84": "Öff. Verwaltung",
    # Bildung
    "85": "Bildung",
    # Gesundheit / Soziales
    "86": "Gesundheit",
    "87": "Soziales",
    "88": "Soziales",
    # Kultur / Sport / Unterhaltung
    "90": "Medien",
    "91": "Bildung",
    "92": "Dienstleistungen",
    "93": "Dienstleistungen",
    # Interessenvertretungen / persönliche Dienstleistungen
    "94": "Verwaltung",
    "95": "Dienstleistungen",
    "96": "Dienstleistungen",
}


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_statent_groessenklassen_csv(source) -> pd.DataFrame:
    """
    Liest den OGD-CSV-Export ts-x-06.02.01.01 (Pfad, Datei-Objekt oder Text-Buffer).

    Returns:
        DataFrame [jahr, noga, groessenklasse, unternehmen, unternehmen_status,
                   beschaeftigte, beschaeftigte_status] — eine Zeile je Jahr × NOGA ×
        Grössenklasse; noga «999» und groessenklasse «total» sind die Totale.
        Gesperrte Werte (STATUS Q) sind leer (NaN).

    Raises:
        ValueError: bei fehlenden Spalten, unbekannten Codes oder ohne Daten.
    """
    df = pd.read_csv(source, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    pflicht = {"PERIOD", "NOGA", "SIZE", "INDICATOR", "VALUE", "STATUS"}
    if fehlend := pflicht - set(df.columns):
        raise ValueError(f"STATENT-CSV unvollständig — fehlende Spalten: {sorted(fehlend)}")
    if df.empty:
        raise ValueError("STATENT-CSV ohne Daten.")
    for spalte in pflicht:
        df[spalte] = df[spalte].str.strip()
    if unbekannt := set(df["SIZE"]) - set(GROESSENKLASSEN):
        raise ValueError(f"Unbekannte Grössenklassen-Codes: {sorted(unbekannt)}")
    df = df[df["INDICATOR"].isin(INDIKATOREN)]

    werte = pd.to_numeric(df["VALUE"], errors="coerce")
    werte[df["STATUS"] == "Q"] = float("nan")
    lang = pd.DataFrame({
        "jahr": df["PERIOD"].astype(int),
        "noga": df["NOGA"].str.zfill(2),
        "groessenklasse": df["SIZE"].map(GROESSENKLASSEN),
        "indikator": df["INDICATOR"].map(INDIKATOREN),
        "wert": werte,
        "status": df["STATUS"],
    })
    breit = lang.pivot_table(index=["jahr", "noga", "groessenklasse"], columns="indikator",
                             values=["wert", "status"], aggfunc="first", dropna=False)
    out = pd.DataFrame(index=breit.index)
    for ind in INDIKATOREN.values():
        out[ind] = breit[("wert", ind)] if ("wert", ind) in breit.columns else float("nan")
        out[f"{ind}_status"] = (breit[("status", ind)] if ("status", ind) in breit.columns
                                else "")
    out = out.reset_index()
    for ind in INDIKATOREN.values():
        out[ind] = out[ind].astype("Int64")
    reihenfolge = {k: i for i, k in enumerate(GROESSENKLASSEN.values())}
    out = out.sort_values(["jahr", "noga", "groessenklasse"],
                          key=lambda s: s.map(reihenfolge) if s.name == "groessenklasse" else s)
    return out[["jahr", "noga", "groessenklasse", "unternehmen", "unternehmen_status",
                "beschaeftigte", "beschaeftigte_status"]].reset_index(drop=True)


def lese_groessenklassen(path: Path = GROESSENKLASSEN_CSV) -> pd.DataFrame:
    """Versionierte Tabelle lesen (gleiche Typen wie parse_statent_groessenklassen_csv)."""
    df = pd.read_csv(path, dtype={"noga": str, "groessenklasse": str,
                                  "unternehmen_status": str, "beschaeftigte_status": str},
                     keep_default_na=False, na_values={"unternehmen": [""], "beschaeftigte": [""]})
    for ind in INDIKATOREN.values():
        df[ind] = pd.to_numeric(df[ind], errors="coerce").astype("Int64")
    return df


# ---------------------------------------------------------------------------
# Online-Abruf
# ---------------------------------------------------------------------------

def finde_aktuelles_asset(bestellnr: str = STATENT_GK_BESTELLNR) -> dict:
    """Sucht in der BFS-DAM-API das aktuelle Asset zur BFS-Nummer und liefert Metadaten."""
    import requests

    resp = requests.get(DAM_ASSETS_URL, params={"orderNr": bestellnr, "language": "de"},
                        headers=HTTP_HEADERS, timeout=60)
    resp.raise_for_status()
    kandidaten = [a for a in resp.json().get("data", [])
                  if a.get("shop", {}).get("orderNr") == bestellnr
                  and a.get("bfs", {}).get("lifecycleGroup") == "CURRENT"]
    if not kandidaten:
        raise ValueError(f"Kein aktuelles BFS-Asset für {bestellnr} gefunden.")
    asset = kandidaten[0]
    master = next((link["href"] for link in asset.get("links", [])
                   if link.get("rel") == "master"), None)
    if master is None:
        raise ValueError(f"Asset {asset['ids']['damId']} ohne Download-Link.")
    return {
        "dam_id": asset["ids"]["damId"],
        "titel": asset["description"]["titles"]["main"],
        "periode": asset["description"].get("bibliography", {}).get("period", ""),
        "stand": asset.get("bfs", {}).get("embargo", "")[:10],
        "url": master,
    }


def fetch_statent_groessenklassen_online(raw_path: Path = RAW_CSV) -> pd.DataFrame:
    """Lädt ts-x-06.02.01.01 (aktuelle Ausgabe), speichert die Rohdatei in data/raw/."""
    import requests

    meta = finde_aktuelles_asset()
    logger.info(f"BFS-Asset {meta['dam_id']}: «{meta['titel']}», {meta['periode']}, "
                f"Stand {meta['stand']}")
    resp = requests.get(meta["url"], headers=HTTP_HEADERS, timeout=120)
    resp.raise_for_status()
    text = resp.content.decode("utf-8-sig")
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(text, encoding="utf-8")
    logger.info(f"Rohdaten gespeichert: {raw_path} ({len(text):,} Zeichen)")
    return parse_statent_groessenklassen_csv(io.StringIO(text))


# ---------------------------------------------------------------------------
# Berechnung
# ---------------------------------------------------------------------------

def schaetze_gesperrte_werte(gk: pd.DataFrame, jahr: int) -> pd.DataFrame:
    """
    Beschäftigte je NOGA-Abteilung × Grössenklasse für ein Jahr, gesperrte Zellen geschätzt.

    Returns:
        DataFrame (Index noga) mit Spalten der vier Klassen, «rest_gesperrt» (auf gesperrte
        Klassen verteilte Beschäftigte) und «gross_gesperrt» (True, wenn die Klasse ≥250
        gesperrt war).
    """
    sel = gk[(gk["jahr"] == jahr) & (gk["noga"] != "999")]
    if sel.empty:
        raise ValueError(f"Keine STATENT-Grössenklassen für {jahr}.")
    breit = sel.pivot(index="noga", columns="groessenklasse", values="beschaeftigte")
    breit = breit.reindex(columns=KLASSEN_DETAIL + ["total"]).astype("Float64")

    zeilen = {}
    for noga, r in breit.iterrows():
        werte = {k: r[k] for k in KLASSEN_DETAIL}
        gesperrt = [k for k, v in werte.items() if pd.isna(v)]
        bekannt = float(sum(v for v in werte.values() if pd.notna(v)))
        rest = 0.0
        if gesperrt:
            if pd.notna(r["total"]):
                rest = max(float(r["total"]) - bekannt, 0.0)
                for k in gesperrt:
                    werte[k] = rest / len(gesperrt)
            else:
                for k in gesperrt:
                    werte[k] = 0.0
        zeile = {k: float(v) for k, v in werte.items()}
        zeile["rest_gesperrt"] = rest
        zeile["gross_gesperrt"] = GROSSFIRMEN_KLASSE in gesperrt
        zeilen[noga] = zeile
    return pd.DataFrame.from_dict(zeilen, orient="index").rename_axis("noga")


def _summe_je_branche(werte: pd.Series) -> pd.Series:
    """Summiert eine Serie (Index NOGA) auf die internen Branchen; prüft das Mapping."""
    noga = werte.index.astype(str).str.zfill(2)
    if unbekannt := sorted(set(noga) - set(NOGA_ZU_BRANCHE)):
        raise ValueError(f"NOGA-Abteilungen ohne Branchen-Zuordnung: {unbekannt}")
    s = pd.Series(werte.to_numpy(dtype=float), index=noga)
    return s.groupby(s.index.map(NOGA_ZU_BRANCHE)).sum()


def compute_kmu_anteil(
    gk: pd.DataFrame,
    jahr: int | None = None,
    statent_noga: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Grossfirmen-Anteil (Beschäftigte in Unternehmen ≥250 Beschäftigte) je interner Branche.

    Args:
        gk: Ausgabe von parse_statent_groessenklassen_csv / lese_groessenklassen.
        jahr: STATENT-Jahr; None → neuestes Jahr in gk.
        statent_noga: optional statent_beschaeftigte_noga.csv (alle Arbeitsstätten) für die
            Spalte `abdeckung`; fehlt sie, bleibt `abdeckung` leer.

    Returns:
        DataFrame [branche, beschaeftigte_total, beschaeftigte_gross, grossfirmen_anteil,
                   quelle, jahr, einheit, abdeckung], alle 21 Branchen, alphabetisch.
        Branchen ohne marktwirtschaftliche Unternehmen (Öff. Verwaltung) erhalten
        grossfirmen_anteil = NaN.
    """
    jahr = int(gk["jahr"].max()) if jahr is None else int(jahr)
    w = schaetze_gesperrte_werte(gk, jahr)
    w["total"] = w[KLASSEN_DETAIL].sum(axis=1)
    alle = sorted(set(NOGA_ZU_BRANCHE.values()))

    total = _summe_je_branche(w["total"]).reindex(alle, fill_value=0.0)
    gross = _summe_je_branche(w[GROSSFIRMEN_KLASSE]).reindex(alle, fill_value=0.0)
    anteil = (gross / total.where(total > 0)).round(4)

    abdeckung = pd.Series(float("nan"), index=alle)
    if statent_noga is not None and not statent_noga.empty:
        sj = statent_noga[statent_noga["jahr"] == jahr]
        if not sj.empty:
            nenner = _summe_je_branche(sj.set_index("noga")["beschaeftigte"]).reindex(alle)
            abdeckung = (total / nenner.where(nenner > 0)).round(3)

    df = pd.DataFrame({
        "branche": alle,
        "beschaeftigte_total": total.round(0).astype(int).to_numpy(),
        "beschaeftigte_gross": gross.round(0).astype(int).to_numpy(),
        "grossfirmen_anteil": anteil.to_numpy(),
        "quelle": QUELLE,
        "jahr": jahr,
        "einheit": EINHEIT,
        "abdeckung": abdeckung.reindex(alle).to_numpy(),
    })
    gueltig = df["grossfirmen_anteil"].dropna()
    if not gueltig.between(0, 1).all():
        raise ValueError("Grossfirmen-Anteil ausserhalb 0–1 — Daten prüfen.")
    return df


def spannweite_gesperrt(gk: pd.DataFrame, jahr: int) -> pd.DataFrame:
    """
    Spannweite des Branchenanteils bei gesperrter Klasse ≥250: Rest ganz in ≥250 (max)
    bzw. gar nicht (min). Nur Branchen mit mindestens einer betroffenen Abteilung.
    """
    w = schaetze_gesperrte_werte(gk, jahr)
    w["total"] = w[KLASSEN_DETAIL].sum(axis=1)
    betroffen = w[w["gross_gesperrt"]]
    if betroffen.empty:
        return pd.DataFrame(columns=["branche", "anteil_min", "anteil_max"])
    total = _summe_je_branche(w["total"])
    gross = _summe_je_branche(w[GROSSFIRMEN_KLASSE])
    anteil_gesperrt = betroffen[GROSSFIRMEN_KLASSE]
    rest = betroffen["rest_gesperrt"]
    minus = _summe_je_branche(anteil_gesperrt)
    plus = _summe_je_branche(rest - anteil_gesperrt)
    branchen = minus.index
    return pd.DataFrame({
        "branche": branchen,
        "anteil_min": ((gross[branchen] - minus) / total[branchen]).round(4).to_numpy(),
        "anteil_max": ((gross[branchen] + plus) / total[branchen]).round(4).to_numpy(),
    })


def vergleich_mit_bisher(neu: pd.DataFrame, alt: pd.DataFrame | None) -> pd.DataFrame | None:
    """Anteil je Branche: bisherige Datei vs. neu berechnet (Δ in Prozentpunkten)."""
    if alt is None or alt.empty:
        return None
    v = alt[["branche", "grossfirmen_anteil"]].merge(
        neu[["branche", "grossfirmen_anteil"]], on="branche", how="outer",
        suffixes=("_alt", "_neu"))
    v["diff_pp"] = ((v["grossfirmen_anteil_neu"] - v["grossfirmen_anteil_alt"]) * 100).round(1)
    return v.sort_values("grossfirmen_anteil_neu", ascending=False,
                         na_position="last").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Anwenden auf scores.csv (grossfirmen_anteil, zeitrahmen_kmu_delta, zeitrahmen)
# ---------------------------------------------------------------------------

def _fmt_anteil(v) -> str:
    return "" if v is None or pd.isna(v) else repr(float(v))


def zeitrahmen_in_scores_neu(
    scores_text: pd.DataFrame,
    kmu_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Berechnet die KMU-Spalten von scores.csv mit einer neuen kmu_anteil_branche-Tabelle.

    Ausgangspunkt ist `zeitrahmen_roh` (Rohwert des Scorings); fehlt er, gilt `zeitrahmen`
    als Rohwert und wird als `zeitrahmen_roh` gespeichert. Geschrieben werden nur
    grossfirmen_anteil, zeitrahmen_kmu_delta, zeitrahmen (und ggf. zeitrahmen_roh).

    Args:
        scores_text: scores.csv als Text (dtype=str, keep_default_na=False).
        kmu_df: Tabelle mit Spalten branche, grossfirmen_anteil.

    Returns:
        (neue scores-Tabelle als Text, Änderungsübersicht je Zeile mit Änderung)
    """
    sys.path.insert(0, str(ROOT / "src" / "scoring"))
    from ch_adjustments import adjust_zeitrahmen_fuer_kmu

    num = scores_text[["beruf", "branche", "zeitrahmen"]].copy()
    if "zeitrahmen_roh" in scores_text.columns:
        num["zeitrahmen_roh"] = scores_text["zeitrahmen_roh"].replace("", pd.NA)
    res = adjust_zeitrahmen_fuer_kmu(num, kmu_df=kmu_df)

    out = scores_text.copy()
    neu_anteil = res["grossfirmen_anteil"].map(_fmt_anteil)
    neu_delta = res["zeitrahmen_kmu_delta"].astype(int).astype(str)
    alt = {s: (out[s] if s in out.columns else pd.Series("", index=out.index))
           for s in ("grossfirmen_anteil", "zeitrahmen_kmu_delta", "zeitrahmen")}

    out["zeitrahmen_roh"] = res["zeitrahmen_roh"]
    out["grossfirmen_anteil"] = neu_anteil
    out["zeitrahmen_kmu_delta"] = neu_delta
    out["zeitrahmen"] = res["zeitrahmen"]

    alt_anteil = pd.to_numeric(alt["grossfirmen_anteil"], errors="coerce")
    neu_anteil_num = pd.to_numeric(neu_anteil, errors="coerce")
    anteil_geaendert = ~((alt_anteil - neu_anteil_num).abs().lt(1e-9)
                         | (alt_anteil.isna() & neu_anteil_num.isna()))
    geaendert = (anteil_geaendert | (alt["zeitrahmen_kmu_delta"] != neu_delta)
                 | (alt["zeitrahmen"] != out["zeitrahmen"]))
    diff = pd.DataFrame({
        "beruf": out["beruf"],
        "branche": out["branche"],
        "zeitrahmen_roh": out["zeitrahmen_roh"],
        "delta_alt": alt["zeitrahmen_kmu_delta"],
        "delta_neu": neu_delta,
        "zeitrahmen_alt": alt["zeitrahmen"],
        "zeitrahmen_neu": out["zeitrahmen"],
    })[geaendert]
    return out, diff


def apply_scores(kmu_df: pd.DataFrame, scores_path: Path = SCORES_CSV,
                 dry_run: bool = False) -> pd.DataFrame:
    """Wendet die neue KMU-Tabelle auf scores.csv an (oder zeigt nur die Änderungen)."""
    text = pd.read_csv(scores_path, dtype=str, keep_default_na=False)
    out, diff = zeitrahmen_in_scores_neu(text, kmu_df)

    z = diff[diff["zeitrahmen_alt"] != diff["zeitrahmen_neu"]]
    d = diff[diff["delta_alt"] != diff["delta_neu"]]
    logger.info(f"\nscores.csv ({len(text)} Berufe): {len(diff)} Zeilen mit geänderten "
                f"KMU-Spalten, {len(d)} mit neuer Verschiebung, {len(z)} mit neuem zeitrahmen.")
    if not d.empty:
        uebersicht = (d.groupby(["branche", "delta_alt", "delta_neu"]).size()
                      .rename("berufe").reset_index())
        for _, r in uebersicht.iterrows():
            logger.info(f"  {r['branche']:18s} Verschiebung {r['delta_alt']:>2s} → "
                        f"{r['delta_neu']:>2s}  ({r['berufe']} Berufe)")
    for _, r in z.head(15).iterrows():
        logger.info(f"    {r['beruf'][:45]:45s} {r['zeitrahmen_roh']:>10s}: "
                    f"{r['zeitrahmen_alt']} → {r['zeitrahmen_neu']}")
    if len(z) > 15:
        logger.info(f"    … und {len(z) - 15} weitere")
    if "zeitrahmen" in text.columns:
        vorher = text["zeitrahmen"].value_counts()
        nachher = out["zeitrahmen"].value_counts()
        stufen = [s for s in ("1-2 Jahre", "3-5 Jahre", "5-10 Jahre", ">10 Jahre")
                  if s in vorher.index or s in nachher.index]
        logger.info("  Verteilung zeitrahmen alt → neu: " + ", ".join(
            f"{s} {int(vorher.get(s, 0))} → {int(nachher.get(s, 0))}" for s in stufen))

    if dry_run:
        logger.info("--dry-run: scores.csv nicht geschrieben.")
    else:
        spalten = list(text.columns) + [c for c in out.columns if c not in text.columns]
        out[spalten].to_csv(scores_path, index=False)
        logger.info(f"Gespeichert: {scores_path}")
    return diff


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--offline", action="store_true",
                        help="versionierte statent_groessenklassen_noga.csv verwenden (kein Netz)")
    parser.add_argument("--year", dest="jahr", metavar="YEAR", type=int, default=None,
                        help="STATENT-Jahr (Standard: neuestes verfügbares)")
    parser.add_argument("--apply-scores", action="store_true",
                        help="grossfirmen_anteil, zeitrahmen_kmu_delta, zeitrahmen in "
                             "scores.csv neu berechnen")
    parser.add_argument("--scores", type=Path, default=SCORES_CSV, help="Pfad zu scores.csv")
    parser.add_argument("--dry-run", action="store_true", help="nichts schreiben")
    args = parser.parse_args(argv)

    if args.offline:
        gk = lese_groessenklassen()
        logger.info(f"Offline: {GROESSENKLASSEN_CSV.name} ({len(gk)} Zeilen, "
                    f"{gk['jahr'].min()}–{gk['jahr'].max()})")
    else:
        gk = fetch_statent_groessenklassen_online()
        if not args.dry_run:
            gk.to_csv(GROESSENKLASSEN_CSV, index=False)
            logger.info(f"Gespeichert: {GROESSENKLASSEN_CSV}")

    statent_noga = (pd.read_csv(STATENT_NOGA_CSV, dtype={"noga": str})
                    if STATENT_NOGA_CSV.exists() else None)
    kmu = compute_kmu_anteil(gk, args.jahr, statent_noga)
    jahr = int(kmu["jahr"].iloc[0])

    gesamt = gk[(gk["jahr"] == jahr) & (gk["noga"] == "999")].set_index("groessenklasse")
    if {"250+", "total"} <= set(gesamt.index):
        logger.info(f"STATENT {jahr}, marktwirtschaftliche Unternehmen: "
                    f"{int(gesamt.at['total', 'beschaeftigte']):,} Beschäftigte, davon "
                    f"{gesamt.at['250+', 'beschaeftigte'] / gesamt.at['total', 'beschaeftigte']:.1%}"
                    f" in Unternehmen ≥250 Beschäftigte")
    for _, r in spannweite_gesperrt(gk, jahr).iterrows():
        logger.info(f"  gesperrte Werte {r['branche']}: Anteil {r['anteil_min']:.1%} … "
                    f"{r['anteil_max']:.1%}")

    alt = pd.read_csv(KMU_CSV) if KMU_CSV.exists() else None
    vergleich = vergleich_mit_bisher(kmu, alt)
    if vergleich is not None:
        logger.info("\nGrossfirmen-Anteil je Branche, bisherige Datei → neu (Δ in %-Punkten):")
        for _, r in vergleich.iterrows():
            neu_txt = ("   –  " if pd.isna(r["grossfirmen_anteil_neu"])
                       else f"{r['grossfirmen_anteil_neu']:6.1%}")
            logger.info(f"  {r['branche']:18s} {r['grossfirmen_anteil_alt']:6.1%} → {neu_txt}"
                        + ("" if pd.isna(r["diff_pp"]) else f"  ({r['diff_pp']:+.1f})"))

    if not args.dry_run:
        kmu.to_csv(KMU_CSV, index=False)
        logger.info(f"Gespeichert: {KMU_CSV}")

    if args.apply_scores:
        apply_scores(kmu, args.scores, dry_run=args.dry_run)
    elif args.dry_run:
        logger.info("--dry-run: nichts geschrieben.")


if __name__ == "__main__":  # pragma: no cover
    main()
