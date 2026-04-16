"""
Manuelle Korrekturen für die 22 ungematchten Berufe in berufe_ch_esco_verified.csv.
Verwendet gezielt gewählte Suchbegriffe + ISCO-Gruppen-Suche.
"""

import re
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from enrich_with_esco import esco_get_occupation, esco_search, get_description

PROCESSED_PATH = Path(__file__).parent.parent.parent / "data" / "processed"
RATE_LIMIT = 0.5

# Gezielte Suchbegriffe pro Beruf (mehrere Varianten, beste zuerst)
MANUAL_QUERIES: dict[str, list[str]] = {
    "Dipl. Pflegefachperson":               ["Pflegefachmann", "Krankenpfleger", "registered nurse"],
    "Kaufmann/-frau EFZ (allg. Richtung)":  ["Bürokaufmann", "Büroangestellter", "office clerk"],
    "Detailhandelsfachmann/-frau EFZ":       ["Einzelhandelskaufmann", "Verkäufer Einzelhandel", "shop sales assistant"],
    "Primarlehrer/in":                       ["Grundschullehrer", "Primarschullehrer", "primary school teacher"],
    "Sekundarlehrer/in":                     ["Sekundarschullehrer", "secondary education teacher"],
    "Lastwagenfahrer/in":                    ["LKW-Fahrer", "Kraftfahrer Güterverkehr", "heavy truck driver"],
    "Pflegeassistent/in":                    ["Pflegehelfer", "Pflegehilfskraft", "healthcare assistant"],
    "Spitex-Mitarbeiter/in":                 ["Hauspflegekraft", "ambulante Pflege", "home care worker"],
    "Projektleiter/in (allg.)":              ["Projektmanager", "project manager"],
    "Arztpraxisassistent/in":                ["Medizinische Fachangestellte", "Arzthelfer", "medical assistant"],
    "Restaurantfachmann/-frau EFZ":          ["Kellner", "Servicemitarbeiter Restaurant", "waiter"],
    "Lieferwagenfahrer/in":                  ["Auslieferungsfahrer", "Lieferkraftfahrer", "delivery driver"],
    "Produktionsmitarbeiter/in (Pharma)":    ["Pharmamitarbeiter Produktion", "Maschinenführer Produktion", "pharmaceutical production"],
    "Filialleiter/in (Detailhandel)":        ["Filialleiter Einzelhandel", "Einzelhandelsleiter", "retail manager"],
    "ICT-Supporter/in":                      ["IT-Helpdesk", "ICT-Benutzerbetreuung", "ICT user support"],
    "Maschinenführer/in":                    ["Maschinenführer Fertigung", "Anlagenführer", "machine operator"],
    "Hotelfachmann/-frau EFZ":               ["Hotelrezeptionist", "Hotelmitarbeiter", "hotel receptionist"],
    "Hauswirtschaftler/in EFZ":              ["Hauswirtschafterin", "Hauswirtschaft", "housekeeper"],
    "Mechatroniker/in EFZ":                  ["Mechatroniker", "mechatronics technician"],
    "Telematiker/in EFZ":                    ["Telekommunikationstechniker", "Netzwerktechniker", "telecommunications technician"],
    "Compliance Officer":                    ["Compliance-Beauftragter", "compliance officer"],
    "Drogist/in":                            ["Drogist", "Pharmazeutisch-technischer Assistent", "pharmacy technician"],
}


def normalize_isco(value) -> str:
    try:
        return str(int(float(value))).zfill(4)
    except (ValueError, TypeError):
        return ""


def compute_score(beruf_isco: str, esco_isco: str) -> int:
    if not beruf_isco or not esco_isco:
        return 0
    clean = re.sub(r"\D.*", "", esco_isco)
    if clean[:4] == beruf_isco[:4]:
        return 2
    if clean[:2] == beruf_isco[:2]:
        return 1
    return 0


def find_match(beruf: str, isco_code: str) -> tuple[str, str, str, int] | None:
    queries = MANUAL_QUERIES.get(beruf, [])
    for query in queries:
        for lang in ("de", "en"):
            results = esco_search(query, language=lang, limit=5)
            time.sleep(RATE_LIMIT)
            # Erst score=2, dann score=1 akzeptieren
            for min_score in (2, 1):
                for r in results:
                    s = compute_score(isco_code, re.sub(r"\D.*", "", r.get("code", "")))
                    if s >= min_score:
                        uri = r.get("uri", "")
                        titel = r.get("title", beruf)
                        detail = esco_get_occupation(uri, language="de")
                        time.sleep(RATE_LIMIT)
                        beschreibung = get_description(detail, lang="de")
                        return (uri, titel, beschreibung, s)
    return None


def patch() -> None:
    input_file = "berufe_ch_esco_verified.csv"
    df = pd.read_csv(PROCESSED_PATH / input_file)

    unmatched = df[df["match_score"] == 0]["beruf"].tolist()
    print(f"{len(unmatched)} Berufe werden gepatcht...\n")

    fixed = 0
    for beruf in unmatched:
        idx = df[df["beruf"] == beruf].index[0]
        isco_code = normalize_isco(df.at[idx, "isco_code"])
        print(f"  {beruf} [isco: {isco_code}]... ", end="", flush=True)

        result = find_match(beruf, isco_code)
        if result:
            uri, titel, beschreibung, score = result
            df.at[idx, "esco_uri"] = uri
            df.at[idx, "esco_titel"] = titel
            df.at[idx, "esco_beschreibung"] = beschreibung
            df.at[idx, "match_score"] = score
            fixed += 1
            print(f"OK (score={score}, {titel[:45]})")
        else:
            print("kein Treffer")

    df.to_csv(PROCESSED_PATH / input_file, index=False)

    counts = df["match_score"].value_counts().to_dict()
    print(f"\n=== Ergebnis ===")
    print(f"score=2: {counts.get(2,0)}  score=1: {counts.get(1,0)}  score=0: {counts.get(0,0)}")
    print(f"Gepatcht: {fixed}/{len(unmatched)}")

    still_bad = df[df["match_score"] == 0]["beruf"].tolist()
    if still_bad:
        print(f"\nNoch ohne Match:")
        for b in still_bad:
            print(f"  - {b}")
    print(f"\nGespeichert: {PROCESSED_PATH / input_file}")


if __name__ == "__main__":
    patch()
