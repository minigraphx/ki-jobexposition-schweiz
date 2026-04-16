"""
ESCO API: Berufsbeschreibungen für Schweizer Berufe holen.
ESCO v1.2 – https://esco.ec.europa.eu/en/use-esco/esco-api
"""

import requests
import pandas as pd
import time

ESCO_BASE_URL = "https://ec.europa.eu/esco/api"


def search_occupation(title: str, language: str = "de") -> list[dict]:
    """Beruf nach Titel suchen, gibt Liste von Treffern zurück."""
    url = f"{ESCO_BASE_URL}/search"
    params = {
        "text": title,
        "language": language,
        "type": "occupation",
        "limit": 5,
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    results = resp.json().get("_embedded", {}).get("results", [])
    return results


def get_occupation_detail(uri: str, language: str = "de") -> dict:
    """Detailinformationen zu einem Beruf anhand seiner ESCO-URI holen."""
    params = {"uri": uri, "language": language}
    resp = requests.get(f"{ESCO_BASE_URL}/resource/occupation", params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def fetch_descriptions_for_jobs(jobs_df: pd.DataFrame, language: str = "de") -> pd.DataFrame:
    """
    Für eine Liste von Berufen (DataFrame mit Spalte 'beruf') die ESCO-Beschreibung holen.
    Gibt erweitertes DataFrame zurück.
    """
    descriptions = []
    for _, row in jobs_df.iterrows():
        beruf = row["beruf"]
        try:
            results = search_occupation(beruf, language)
            if results:
                uri = results[0]["uri"]
                detail = get_occupation_detail(uri, language)
                desc = detail.get("description", {}).get("en", {}).get("literal", "")
                descriptions.append({"beruf": beruf, "esco_uri": uri, "esco_beschreibung": desc})
            else:
                descriptions.append({"beruf": beruf, "esco_uri": None, "esco_beschreibung": None})
        except Exception as e:
            print(f"Fehler bei '{beruf}': {e}")
            descriptions.append({"beruf": beruf, "esco_uri": None, "esco_beschreibung": None})
        time.sleep(0.3)  # Rate limiting

    return jobs_df.merge(pd.DataFrame(descriptions), on="beruf", how="left")


if __name__ == "__main__":
    # Test mit 3 Berufen
    test = pd.DataFrame({"beruf": ["Buchhalter", "Krankenpfleger", "Softwareentwickler"]})
    result = fetch_descriptions_for_jobs(test)
    print(result[["beruf", "esco_beschreibung"]].to_string())
