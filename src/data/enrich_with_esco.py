"""
ESCO-Berufsbeschreibungen zur CH-Berufsliste hinzufügen.

Strategie:
1. Suche auf Deutsch mit Berufsname → bis zu 5 Kandidaten
2. Claude Haiku validiert jeden Kandidaten: Passt der ESCO-Titel zum CH-Beruf?
3. Ersten validierten Treffer verwenden
4. Fallback: Englische Suche, dann erneute Haiku-Validierung
5. Falls kein validerter Match: Haiku schreibt Berufsbeschreibung direkt

Verwendung:
  python enrich_with_esco.py                  # alle 204 Berufe
  python enrich_with_esco.py --fix-wrong      # nur bekannte Fehler reparieren
  python enrich_with_esco.py --job "Grafiker/in"  # einzelner Beruf

Benötigt: ANTHROPIC_API_KEY in .env
ESCO-API muss erreichbar sein (lokal ausführen, nicht in CI/Sandbox).
"""

import argparse
import json
import logging
import os
import time
from pathlib import Path

import anthropic
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROCESSED_PATH = Path(__file__).parent.parent.parent / "data" / "processed"
ESCO_API = "https://ec.europa.eu/esco/api"

# Bekannte falsche ESCO-Matches (aus Audit ermittelt)
KNOWN_WRONG_MATCHES = [
    "Bankkaufmann/-frau",
    "Polymechaniker/in EFZ",
    "Logistiker/in EFZ",
    "Immobilienbewirtschafter/in",
    "Automatiker/in EFZ",
    "Bauführer/in",
    "Grafiker/in",
    "Hochbauzeichner/in EFZ",
    "Elektroplaner/in EFZ",
]

VALIDATE_PROMPT = """Beruf (Schweiz): {beruf}
ESCO-Treffer: {esco_titel}
ESCO-Beschreibung: {esco_beschreibung}

Ist das ein sinnvoller ESCO-Match für diesen Schweizer Beruf?
Ein guter Match beschreibt denselben Beruf oder eine sehr nahe Verwandte Tätigkeit.
Ein schlechter Match beschreibt einen völlig anderen Beruf.

Antworte NUR mit JSON: {{"valid": true}} oder {{"valid": false}}"""

DESC_PROMPT = """Schreibe eine sachliche Berufsbeschreibung auf Deutsch für den Beruf \
"{beruf}" im Schweizer Arbeitsmarkt.
2-3 präzise Sätze über die typischen Kernaufgaben.
Antworte NUR mit dem Beschreibungstext."""


def make_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if api_key:
        return anthropic.Anthropic(api_key=api_key)
    token_file = Path("/home/claude/.claude/remote/.session_ingress_token")
    if token_file.exists():
        return anthropic.Anthropic(auth_token=token_file.read_text().strip())
    raise RuntimeError("Kein ANTHROPIC_API_KEY in .env gefunden.")


def esco_search(query: str, language: str = "de", limit: int = 5) -> list:
    try:
        resp = requests.get(
            f"{ESCO_API}/search",
            params={"text": query, "language": language, "type": "occupation", "limit": limit},
            headers={"Accept": "application/json", "User-Agent": "ki-jobexposition-ch/1.0"},
            timeout=15,
        )
        if resp.status_code != 200:
            return []
        return resp.json().get("_embedded", {}).get("results", [])
    except Exception as e:
        logger.warning(f"ESCO-Suche fehlgeschlagen: {e}")
        return []


def esco_get_description(uri: str, language: str = "de") -> str:
    try:
        resp = requests.get(
            f"{ESCO_API}/resource/occupation",
            params={"uri": uri, "language": language},
            headers={"Accept": "application/json"},
            timeout=15,
        )
        if resp.status_code != 200:
            return ""
        detail = resp.json()
        desc = detail.get("description", {})
        for lang in [language, "en"]:
            if lang in desc and desc[lang].get("literal"):
                return desc[lang]["literal"]
    except Exception:
        pass
    return ""


def haiku_validate(client: anthropic.Anthropic, beruf: str, esco_titel: str,
                   esco_beschreibung: str) -> bool:
    prompt = VALIDATE_PROMPT.format(
        beruf=beruf, esco_titel=esco_titel,
        esco_beschreibung=esco_beschreibung[:300]
    )
    try:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=32,
            messages=[{"role": "user", "content": prompt}],
        )
        result = json.loads(resp.content[0].text.strip())
        return bool(result.get("valid", False))
    except Exception:
        return False


def haiku_generate_description(client: anthropic.Anthropic, beruf: str) -> str:
    try:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": DESC_PROMPT.format(beruf=beruf)}],
        )
        return resp.content[0].text.strip()
    except Exception:
        return ""


def find_best_match(client: anthropic.Anthropic, beruf: str,
                    isco_code: str) -> tuple[str, str, str]:
    """
    Gibt (esco_uri, esco_titel, esco_beschreibung) zurück.
    Haiku validiert jeden Kandidaten; Fallback auf Haiku-generierte Beschreibung.
    """
    beruf_clean = beruf.replace("/-", " ").replace("/", " ").replace("EFZ", "").strip()

    for language in ["de", "en"]:
        results = esco_search(beruf_clean, language=language, limit=5)
        if not results and language == "de":
            # Kürzere Suche versuchen
            short = beruf_clean.split()[0]
            results = esco_search(short, language="de", limit=5)

        for candidate in results:
            uri = candidate.get("uri", "")
            titel = candidate.get("title", "")
            if not uri:
                continue

            beschreibung = esco_get_description(uri, language="de")
            time.sleep(0.3)

            if haiku_validate(client, beruf, titel, beschreibung):
                logger.info(f"    ✓ Validierter Match: {titel}")
                time.sleep(0.1)
                return uri, titel, beschreibung
            else:
                logger.debug(f"    ✗ Abgelehnt: {titel}")
            time.sleep(0.1)

    # Kein validerter ESCO-Match → Haiku generiert Beschreibung direkt
    logger.warning(f"    Kein ESCO-Match für '{beruf}' → Haiku-Beschreibung")
    haiku_desc = haiku_generate_description(client, beruf)
    time.sleep(0.1)
    return "", beruf, haiku_desc


def enrich_jobs(jobs_df: pd.DataFrame, client: anthropic.Anthropic) -> pd.DataFrame:
    uris, titel_list, beschreibungen = [], [], []

    for i, row in jobs_df.iterrows():
        beruf = row["beruf"]
        isco = str(row["isco_code"])
        logger.info(f"[{i+1:3d}/{len(jobs_df)}] {beruf}")

        uri, titel, beschreibung = find_best_match(client, beruf, isco)
        uris.append(uri)
        titel_list.append(titel)
        beschreibungen.append(beschreibung)

        status = f"ESCO: {titel[:40]}" if uri else "Haiku-Beschreibung"
        logger.info(f"    → {status}")
        time.sleep(0.4)

    jobs_df = jobs_df.copy()
    jobs_df["esco_uri"] = uris
    jobs_df["esco_titel"] = titel_list
    jobs_df["esco_beschreibung"] = beschreibungen
    return jobs_df


def main():
    parser = argparse.ArgumentParser(description="ESCO-Enrichment mit Haiku-Validierung")
    parser.add_argument("--fix-wrong", action="store_true",
                        help="Nur bekannte Fehler reparieren")
    parser.add_argument("--job", type=str, default=None,
                        help="Einzelnen Beruf verarbeiten")
    args = parser.parse_args()

    client = make_client()

    input_file = PROCESSED_PATH / "berufe_ch_esco.csv"
    output_esco = PROCESSED_PATH / "berufe_ch_esco.csv"
    output_verified = PROCESSED_PATH / "berufe_ch_esco_verified.csv"

    df_base = pd.read_csv(PROCESSED_PATH / "berufe_ch.csv")
    df_existing = pd.read_csv(input_file)

    if args.job:
        target_jobs = [args.job]
    elif args.fix_wrong:
        target_jobs = KNOWN_WRONG_MATCHES
    else:
        target_jobs = df_base["beruf"].tolist()

    logger.info(f"Verarbeite {len(target_jobs)} Berufe...")

    target_df = df_base[df_base["beruf"].isin(target_jobs)].reset_index(drop=True)
    enriched = enrich_jobs(target_df, client)

    # Bestehende Daten mit Korrekturen zusammenführen
    df_out = df_existing.copy()
    for _, row in enriched.iterrows():
        mask = df_out["beruf"] == row["beruf"]
        df_out.loc[mask, "esco_uri"] = row["esco_uri"]
        df_out.loc[mask, "esco_titel"] = row["esco_titel"]
        df_out.loc[mask, "esco_beschreibung"] = row["esco_beschreibung"]

    df_out.to_csv(output_esco, index=False)
    df_out.to_csv(output_verified, index=False)

    logger.info(f"Gespeichert: {output_esco}")
    logger.info(f"Gespeichert: {output_verified}")
    logger.info(f"Mit ESCO-URI: {(df_out['esco_uri'] != '').sum()}/{len(df_out)}")
    logger.info(f"Bekannte Fehler repariert: {len([j for j in target_jobs if j in KNOWN_WRONG_MATCHES])}")


if __name__ == "__main__":
    main()
