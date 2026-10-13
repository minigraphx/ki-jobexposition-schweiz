"""
fetch_bgs.py — Grenzgänger-Anteil pro Branche aus der BFS-Grenzgängerstatistik (GGS)

Zähler — BFS Grenzgängerstatistik (GGS; im Repo historisch «BGS»), stats.swiss-Dataflow
    CH1.GGS,DF_GGS_4,1.0.0 «Ausländische Grenzgänger/-innen nach Wirtschaftszweig und
    Erwerbsstatus», Quartalswerte seit 2002, Datenquelle ZEMIS / AHV.
    SDMX-REST (öffentlich, ohne Schlüssel):
        https://disseminate.stats.swiss/rest/data/CH1.GGS,DF_GGS_4,1.0.0/._T.Q?startPeriod=2022-Q1
        Accept: application/vnd.sdmx.data+csv;version=1.0.0
    Dimensionen: NOGA (CL_NOGA_DIVISION: Abteilungen 01–99, Abschnitte A–U, Sektoren 1–3,
    _T), AUFZW (Erwerbsstatus: _T Total, 1 unselbständig, 50 selbständig, -9 unbekannt),
    FREQ (Q). Verwendet: AUFZW=_T, die 2-stelligen NOGA-Abteilungen. Die Werte sind
    Personen (auf Basis ZEMIS/AHV hochgerechnet, daher Dezimalstellen), keine VZÄ.

Nenner — BFS STATENT, PX-Tabelle px-x-0602010000_101 «Arbeitsstätten und Beschäftigte nach
    Jahr, Kanton, Wirtschaftsabteilung und Beobachtungseinheit», Schweiz total,
    Beobachtungseinheit «Beschäftigte» (neuestes Jahr, Referenzmonat Dezember).
    STATENT ist arbeitsortbasiert und erfasst Beschäftigte über den AHV-pflichtigen Lohn
    (≥ 2'300 CHF/Jahr) — Grenzgänger/-innen sind darin enthalten. Personen mit Verträgen
    bei mehreren Unternehmen werden mehrfach gezählt.

Definition:
    grenzgaenger_anteil[branche] = Σ GGS-Grenzgänger (NOGA-Abteilungen der Branche)
                                   / Σ STATENT-Beschäftigte (gleiche NOGA-Abteilungen)
    Bezugsperiode Zähler: Jahresmittel des neuesten vollständigen Kalenderjahres
    (Mittel der vier Quartale), zusätzlich das neueste Quartal als eigene Spalte.
    NOGA 97/98 (private Haushalte) und 99 (exterritoriale Organisationen) fehlen in
    STATENT und werden daher auch im Zähler nicht berücksichtigt.

Dateien:
    data/raw/bgs_df_ggs_4.csv                 SDMX-CSV-Rohdownload (gitignored)
    data/processed/bgs_grenzgaenger_noga.csv  aufbereitet: noga, periode, grenzgaenger, obs_status
    data/processed/statent_beschaeftigte_noga.csv  jahr, noga, beschaeftigte, vzae
    data/processed/grenzgaenger_anteil_branche.csv Ergebnis je interner Branche

Aufruf:
    python src/data/fetch_bgs.py              # GGS + STATENT online laden, alles neu schreiben
    python src/data/fetch_bgs.py --offline    # nur die versionierten CSVs verwenden
    python src/data/fetch_bgs.py --periode 2026-Q2   # einzelnes Quartal statt Jahresmittel
    python src/data/fetch_bgs.py --dry-run    # nichts schreiben, nur Vergleich ausgeben

Historie: Bis Oktober 2026 enthielt dieses Skript hart kodierte Schätzanteile
(BRANCHE_FALLBACK_ANTEIL) und rechnete mit dem BZ-2008-Nenner aus kmu_anteil_branche.csv.
Beides ist entfernt; die alten Werte sind nur noch in der Git-Historie.
"""

from __future__ import annotations

import argparse
import io
import logging
import re
from pathlib import Path

import pandas as pd

from fetch_statent import NOGA_ZU_BRANCHE  # gemeinsames NOGA-Abteilung → Branche-Mapping

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent.parent
PROCESSED_DATA_PATH = ROOT / "data" / "processed"
RAW_DATA_PATH = ROOT / "data" / "raw"

BGS_RAW_PATH = RAW_DATA_PATH / "bgs_df_ggs_4.csv"
BGS_CSV = PROCESSED_DATA_PATH / "bgs_grenzgaenger_noga.csv"
STATENT_CSV = PROCESSED_DATA_PATH / "statent_beschaeftigte_noga.csv"
OUTPUT_CSV = PROCESSED_DATA_PATH / "grenzgaenger_anteil_branche.csv"

SDMX_DATA_URL = "https://disseminate.stats.swiss/rest/data/CH1.GGS,DF_GGS_4,1.0.0/._T.Q"
SDMX_CSV_ACCEPT = "application/vnd.sdmx.data+csv;version=1.0.0"
BGS_START = "2022-Q1"
STATENT_URL = (
    "https://www.pxweb.bfs.admin.ch/api/v1/de/"
    "px-x-0602010000_101/px-x-0602010000_101.px"
)
STATENT_SCHWEIZ = "999"
STATENT_EINHEIT_BESCHAEFTIGTE = "2"
STATENT_EINHEIT_VZAE = "5"
HTTP_HEADERS = {"User-Agent": "ki-jobexposition-schweiz (Forschung, sequenziell, geringe Last)"}

# NOGA-Abteilungen, die STATENT nicht abdeckt → bewusst ohne Branche (Zähler und Nenner)
NOGA_OHNE_BRANCHE: dict[str, str] = {
    "97": "Private Haushalte mit Hauspersonal",
    "98": "Private Haushalte, Eigenbedarf",
    "99": "Exterritoriale Organisationen",
}

_QUARTAL_RE = re.compile(r"^(\d{4})-Q([1-4])$")


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _code(wert: str) -> str:
    """SDMX-CSV mit labels=both liefert «01: Landwirtschaft …» → nur den Code behalten."""
    return str(wert).split(":", 1)[0].strip()


def parse_bgs_sdmx_csv(source) -> pd.DataFrame:
    """
    Liest den SDMX-CSV-Export von DF_GGS_4 (Pfad, Datei-Objekt oder Text-Buffer).

    Behält Erwerbsstatus Total (AUFZW=_T), Quartalswerte und die 2-stelligen
    NOGA-Abteilungen; Abschnitte (A–U), Sektoren (1–3), _T und -9 entfallen.

    Returns:
        DataFrame [noga, periode, grenzgaenger, obs_status], sortiert.

    Raises:
        ValueError: bei fehlenden Pflichtspalten oder ohne verwertbare Zeilen.
    """
    df = pd.read_csv(source, dtype=str, keep_default_na=False)
    pflicht = {"NOGA", "AUFZW", "TIME_PERIOD", "OBS_VALUE"}
    if fehlend := pflicht - set(df.columns):
        raise ValueError(f"GGS-CSV unvollständig — fehlende Spalten: {sorted(fehlend)}")

    for spalte in ("NOGA", "AUFZW", "FREQ"):
        if spalte in df.columns:
            df[spalte] = df[spalte].map(_code)
    maske = (df["AUFZW"] == "_T") & df["NOGA"].str.fullmatch(r"\d{2}")
    if "FREQ" in df.columns:
        maske &= df["FREQ"] == "Q"
    df = df[maske]
    if df.empty:
        raise ValueError("GGS-CSV enthält keine Quartalszeilen mit AUFZW=_T und NOGA-Abteilung.")

    out = pd.DataFrame({
        "noga": df["NOGA"],
        "periode": df["TIME_PERIOD"].str.strip(),
        "grenzgaenger": pd.to_numeric(df["OBS_VALUE"], errors="coerce"),
        "obs_status": df["OBS_STATUS"] if "OBS_STATUS" in df.columns else "",
    })
    if out["grenzgaenger"].isna().any():
        n = int(out["grenzgaenger"].isna().sum())
        logger.warning(f"GGS: {n} Werte nicht numerisch → 0 gesetzt.")
        out["grenzgaenger"] = out["grenzgaenger"].fillna(0.0)
    if not out["periode"].str.fullmatch(_QUARTAL_RE.pattern).all():
        raise ValueError("GGS-CSV: TIME_PERIOD nicht im Format JJJJ-Qn.")
    return out.sort_values(["periode", "noga"]).reset_index(drop=True)


def parse_statent_pxweb(antwort: dict) -> pd.DataFrame:
    """
    Wandelt die PxWeb-JSON-Antwort (Schweiz total, alle Wirtschaftsabteilungen,
    Beobachtungseinheiten Beschäftigte und VZÄ) in [jahr, noga, beschaeftigte, vzae].
    «X» (Datenschutz) und «...» werden zu 0.
    """
    zeilen = []
    for d in antwort["data"]:
        jahr, _kanton, noga, einheit = d["key"]
        if noga == "999":
            continue
        wert = pd.to_numeric(d["values"][0], errors="coerce")
        zeilen.append({
            "jahr": int(jahr),
            "noga": str(noga).zfill(2),
            "einheit": einheit,
            "wert": 0.0 if pd.isna(wert) else float(wert),
        })
    if not zeilen:
        raise ValueError("STATENT-Antwort ohne Daten.")
    df = pd.DataFrame(zeilen).pivot_table(
        index=["jahr", "noga"], columns="einheit", values="wert", aggfunc="sum"
    )
    df = df.rename(columns={STATENT_EINHEIT_BESCHAEFTIGTE: "beschaeftigte",
                            STATENT_EINHEIT_VZAE: "vzae"})
    for spalte in ("beschaeftigte", "vzae"):
        if spalte not in df.columns:
            df[spalte] = 0.0
    df = df[["beschaeftigte", "vzae"]].round(0).astype(int).reset_index()
    df.columns.name = None
    return df.sort_values(["jahr", "noga"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Online-Abruf
# ---------------------------------------------------------------------------

def fetch_bgs_online(start: str = BGS_START, raw_path: Path = BGS_RAW_PATH) -> pd.DataFrame:
    """Lädt DF_GGS_4 (AUFZW=_T, Quartale ab `start`) als SDMX-CSV; Rohdatei → data/raw/."""
    import requests

    resp = requests.get(
        SDMX_DATA_URL,
        params={"startPeriod": start},
        headers={**HTTP_HEADERS, "Accept": SDMX_CSV_ACCEPT},
        timeout=120,
    )
    resp.raise_for_status()
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(resp.text, encoding="utf-8")
    logger.info(f"GGS-Rohdaten gespeichert: {raw_path} ({len(resp.text):,} Zeichen)")
    return parse_bgs_sdmx_csv(io.StringIO(resp.text))


def fetch_statent_online() -> pd.DataFrame:
    """Lädt STATENT-Beschäftigte und -VZÄ je Wirtschaftsabteilung (Schweiz, neuestes Jahr)."""
    import requests

    meta = requests.get(STATENT_URL, headers=HTTP_HEADERS, timeout=60)
    meta.raise_for_status()
    jahr = max(meta.json()["variables"][0]["values"])
    query = {
        "query": [
            {"code": "Jahr", "selection": {"filter": "item", "values": [jahr]}},
            {"code": "Kanton", "selection": {"filter": "item", "values": [STATENT_SCHWEIZ]}},
            {"code": "Wirtschaftsabteilung", "selection": {"filter": "all", "values": ["*"]}},
            {"code": "Beobachtungseinheit", "selection": {
                "filter": "item",
                "values": [STATENT_EINHEIT_BESCHAEFTIGTE, STATENT_EINHEIT_VZAE]}},
        ],
        "response": {"format": "json"},
    }
    resp = requests.post(STATENT_URL, json=query, headers=HTTP_HEADERS, timeout=120)
    resp.raise_for_status()
    return parse_statent_pxweb(resp.json())


# ---------------------------------------------------------------------------
# Berechnung
# ---------------------------------------------------------------------------

def waehle_periode(bgs: pd.DataFrame, periode: str | None = None) -> tuple[pd.Series, str]:
    """
    Wählt die Bezugsperiode des Zählers.

    Args:
        bgs: Ausgabe von parse_bgs_sdmx_csv.
        periode: None → Jahresmittel des neuesten vollständigen Jahres (4 Quartale);
                 «JJJJ» → Jahresmittel dieses Jahres; «JJJJ-Qn» → dieses Quartal.

    Returns:
        (Grenzgänger je NOGA-Abteilung, Periodenbezeichnung)
    """
    quartale = bgs["periode"].drop_duplicates()
    jahre = quartale.str[:4].value_counts()
    vollstaendig = sorted(jahre[jahre == 4].index)

    if periode is None:
        if not vollstaendig:
            raise ValueError("Kein Kalenderjahr mit vier GGS-Quartalen vorhanden.")
        periode = vollstaendig[-1]

    if _QUARTAL_RE.match(periode):
        sel = bgs[bgs["periode"] == periode]
        if sel.empty:
            raise ValueError(f"Quartal {periode} nicht in den GGS-Daten.")
        return sel.set_index("noga")["grenzgaenger"], periode

    if re.fullmatch(r"\d{4}", periode):
        if periode not in vollstaendig:
            raise ValueError(f"Jahr {periode} hat nicht vier GGS-Quartale.")
        sel = bgs[bgs["periode"].str.startswith(periode)]
        return sel.groupby("noga")["grenzgaenger"].mean(), periode

    raise ValueError(f"Ungültige Periode {periode!r} (erwartet JJJJ oder JJJJ-Qn).")


def aggregiere_nach_branche(werte: pd.Series) -> tuple[pd.Series, float]:
    """
    Summiert Werte je NOGA-Abteilung auf die internen Branchen.

    Returns:
        (Summe je Branche über alle 21 Branchen, Summe der bewusst ausgeschlossenen
        NOGA 97–99)

    Raises:
        ValueError: wenn eine NOGA-Abteilung weder gemappt noch ausgeschlossen ist.
    """
    noga = werte.index.astype(str).str.zfill(2)
    werte = pd.Series(werte.to_numpy(dtype=float), index=noga)
    unbekannt = sorted(set(noga) - set(NOGA_ZU_BRANCHE) - set(NOGA_OHNE_BRANCHE))
    if unbekannt:
        raise ValueError(f"NOGA-Abteilungen ohne Branchen-Zuordnung: {unbekannt}")
    ausgeschlossen = float(werte[werte.index.isin(list(NOGA_OHNE_BRANCHE))].sum())
    gemappt = werte[werte.index.isin(list(NOGA_ZU_BRANCHE))]
    summe = gemappt.groupby(gemappt.index.map(NOGA_ZU_BRANCHE)).sum()
    alle = sorted(set(NOGA_ZU_BRANCHE.values()))
    return summe.reindex(alle, fill_value=0.0), ausgeschlossen


def compute_grenzgaenger_anteil(
    bgs: pd.DataFrame,
    statent: pd.DataFrame,
    periode: str | None = None,
) -> pd.DataFrame:
    """
    Grenzgänger-Anteil je interner Branche.

    Returns:
        DataFrame [branche, grenzgaenger, beschaeftigte_total, grenzgaenger_anteil,
                   grenzgaenger_quartal, grenzgaenger_anteil_quartal,
                   bgs_periode, bgs_quartal, statent_jahr], absteigend nach Anteil.
    """
    zaehler, label = waehle_periode(bgs, periode)
    letztes_quartal = bgs["periode"].max()
    zaehler_q, _ = waehle_periode(bgs, letztes_quartal)

    statent_jahr = int(statent["jahr"].max())
    nenner_noga = statent[statent["jahr"] == statent_jahr].set_index("noga")["beschaeftigte"]

    gg, _ = aggregiere_nach_branche(zaehler)
    gg_q, _ = aggregiere_nach_branche(zaehler_q)
    nenner, _ = aggregiere_nach_branche(nenner_noga)
    if (nenner <= 0).any():
        raise ValueError(f"STATENT-Nenner fehlt für: {list(nenner[nenner <= 0].index)}")

    df = pd.DataFrame({
        "branche": gg.index,
        "grenzgaenger": gg.round(0).astype(int).to_numpy(),
        "beschaeftigte_total": nenner.round(0).astype(int).to_numpy(),
        "grenzgaenger_anteil": (gg / nenner).round(4).to_numpy(),
        "grenzgaenger_quartal": gg_q.round(0).astype(int).to_numpy(),
        "grenzgaenger_anteil_quartal": (gg_q / nenner).round(4).to_numpy(),
        "bgs_periode": label,
        "bgs_quartal": letztes_quartal,
        "statent_jahr": statent_jahr,
    })
    if not df["grenzgaenger_anteil"].between(0, 1).all():
        raise ValueError("Grenzgänger-Anteil ausserhalb 0–1 — Zähler/Nenner prüfen.")
    return df.sort_values("grenzgaenger_anteil", ascending=False).reset_index(drop=True)


def vergleich_mit_bisher(neu: pd.DataFrame, alt_path: Path = OUTPUT_CSV) -> pd.DataFrame | None:
    """Vergleicht den Anteil je Branche mit der bisher gespeicherten Ergebnisdatei."""
    if not alt_path.exists():
        return None
    alt = pd.read_csv(alt_path)[["branche", "grenzgaenger", "grenzgaenger_anteil"]]
    v = alt.merge(neu[["branche", "grenzgaenger", "grenzgaenger_anteil"]],
                  on="branche", how="outer", suffixes=("_alt", "_neu"))
    v["diff_pp"] = ((v["grenzgaenger_anteil_neu"] - v["grenzgaenger_anteil_alt"]) * 100).round(1)
    return v.sort_values("grenzgaenger_anteil_neu", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--offline", action="store_true",
                        help="versionierte CSVs in data/processed/ verwenden (kein Netz)")
    parser.add_argument("--periode", default=None,
                        help="JJJJ (Jahresmittel) oder JJJJ-Qn; Standard: neuestes volles Jahr")
    parser.add_argument("--start", default=BGS_START, help="erstes GGS-Quartal beim Abruf")
    parser.add_argument("--dry-run", action="store_true", help="nichts schreiben")
    args = parser.parse_args(argv)

    if args.offline:
        bgs = pd.read_csv(BGS_CSV, dtype={"noga": str, "periode": str, "obs_status": str},
                          keep_default_na=False)
        statent = pd.read_csv(STATENT_CSV, dtype={"noga": str})
        logger.info(f"Offline: {BGS_CSV.name} ({len(bgs)} Zeilen), {STATENT_CSV.name}")
    else:
        bgs = fetch_bgs_online(args.start)
        statent = fetch_statent_online()
        logger.info(f"GGS: {bgs['periode'].min()} … {bgs['periode'].max()}, "
                    f"{bgs['noga'].nunique()} NOGA-Abteilungen")
        logger.info(f"STATENT {statent['jahr'].max()}: "
                    f"{int(statent['beschaeftigte'].sum()):,} Beschäftigte")
        if not args.dry_run:
            bgs.to_csv(BGS_CSV, index=False)
            statent.to_csv(STATENT_CSV, index=False)

    df = compute_grenzgaenger_anteil(bgs, statent, args.periode)

    zaehler, label = waehle_periode(bgs, args.periode)
    _, ausgeschlossen = aggregiere_nach_branche(zaehler)
    logger.info(
        f"Zähler GGS {label}: {df['grenzgaenger'].sum():,} Grenzgänger/-innen in 21 Branchen "
        f"(+{ausgeschlossen:,.0f} in NOGA 97–99, nicht zugeordnet); "
        f"Nenner STATENT {df['statent_jahr'].iloc[0]}: {df['beschaeftigte_total'].sum():,}"
    )

    vergleich = vergleich_mit_bisher(df)
    if vergleich is not None:
        logger.info("\nVergleich mit bisheriger Datei (Anteil alt → neu, Δ in %-Punkten):")
        for _, r in vergleich.iterrows():
            logger.info(f"  {r['branche']:18s} {r['grenzgaenger_anteil_alt']:6.1%} → "
                        f"{r['grenzgaenger_anteil_neu']:6.1%}  ({r['diff_pp']:+.1f})")

    if args.dry_run:
        logger.info("--dry-run: nichts geschrieben.")
        return
    df.to_csv(OUTPUT_CSV, index=False)
    logger.info(f"Gespeichert: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
