"""
ESCO-Berufsbeschreibungen zur CH-Berufsliste hinzufügen.

Strategie:
1. Primär: ISCO-Code → ESCO Suche nach ISCO-Gruppe → Erste passende Occupation
2. Fallback: Textsuche mit Berufsname auf Deutsch
3. Fallback 2: Englische Suche

Alle Beschreibungen auf Deutsch holen (language=de).
Falls keine DE-Beschreibung: EN nehmen.
"""

import json
import time
import pandas as pd
import requests
from pathlib import Path

PROCESSED_PATH = Path(__file__).parent.parent.parent / "data" / "processed"
ESCO_API = "https://ec.europa.eu/esco/api"


def esco_search(query: str, language: str = "de", limit: int = 3) -> list:
    resp = requests.get(
        f"{ESCO_API}/search",
        params={"text": query, "language": language, "type": "occupation", "limit": limit},
        headers={"Accept": "application/json"},
        timeout=15,
    )
    if resp.status_code != 200:
        return []
    return resp.json().get("_embedded", {}).get("results", [])


def esco_get_occupation(uri: str, language: str = "de") -> dict:
    resp = requests.get(
        f"{ESCO_API}/resource/occupation",
        params={"uri": uri, "language": language},
        headers={"Accept": "application/json"},
        timeout=15,
    )
    if resp.status_code != 200:
        return {}
    return resp.json()


def get_description(detail: dict, lang: str = "de") -> str:
    desc = detail.get("description", {})
    # Versuche DE, dann EN
    for l in [lang, "en"]:
        if l in desc and desc[l].get("literal"):
            return desc[l]["literal"]
    return ""


def find_best_match(beruf: str, isco_code: str) -> tuple[str, str, str]:
    """
    Gibt (esco_uri, esco_titel, beschreibung) zurück.
    """
    # 1. Suche auf Deutsch mit Berufsname
    beruf_clean = beruf.replace("/-", " ").replace("/", " ").replace("EFZ", "").strip()
    results = esco_search(beruf_clean, language="de", limit=5)

    if not results:
        # Fallback: Englisch
        results = esco_search(beruf_clean, language="en", limit=5)

    if not results:
        return ("", beruf, "")

    # Besten Treffer nehmen (ISCO-Code-Übereinstimmung priorisieren)
    best = None
    for r in results:
        code = r.get("code", "")
        # ISCO-Code-Präfix prüfen (erste 4 Stellen)
        if code and isco_code and code.startswith(isco_code[:4]):
            best = r
            break
    if not best:
        best = results[0]

    uri = best.get("uri", "")
    titel = best.get("title", beruf)

    # Detail-Beschreibung holen
    detail = esco_get_occupation(uri, language="de")
    beschreibung = get_description(detail, lang="de")

    return (uri, titel, beschreibung)


def enrich_berufeliste(input_file: str = "berufe_ch.csv",
                       output_file: str = "berufe_ch_esco.csv") -> pd.DataFrame:
    df = pd.read_csv(PROCESSED_PATH / input_file)

    uris, titel_esco, beschreibungen = [], [], []

    for i, row in df.iterrows():
        beruf = row["beruf"]
        isco = str(row["isco_code"])
        print(f"[{i+1:3d}/{len(df)}] {beruf}...", end=" ", flush=True)

        uri, titel, beschreibung = find_best_match(beruf, isco)
        uris.append(uri)
        titel_esco.append(titel)
        beschreibungen.append(beschreibung)

        status = "OK" if beschreibung else "KEIN TEXT"
        print(status)
        time.sleep(0.4)  # Rate limiting

    df["esco_uri"] = uris
    df["esco_titel"] = titel_esco
    df["esco_beschreibung"] = beschreibungen

    out = PROCESSED_PATH / output_file
    df.to_csv(out, index=False)
    print(f"\nGespeichert: {out}")
    print(f"Mit Beschreibung: {(df['esco_beschreibung'] != '').sum()}/{len(df)}")
    return df


if __name__ == "__main__":
    enrich_berufeliste()
