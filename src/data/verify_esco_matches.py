"""
ESCO-Matchqualität prüfen und schlechte Matches verbessern.

Phase 1: Bestehende Matches in berufe_ch_esco.csv bewerten (Score 0/1/2).
Phase 2: Score-0-Einträge mit verbesserten Suchstrategien neu matchen.
Phase 3: berufe_ch_esco_verified.csv + Bericht ausgeben.
"""

import re
import sys
import time
from pathlib import Path

import pandas as pd

# Pfad für Imports relativ zu diesem File setzen
sys.path.insert(0, str(Path(__file__).parent))
from enrich_with_esco import esco_get_occupation, esco_search, get_description

PROCESSED_PATH = Path(__file__).parent.parent.parent / "data" / "processed"
RATE_LIMIT = 0.4


# ---------------------------------------------------------------------------
# Phase 1: Scoring
# ---------------------------------------------------------------------------

def fetch_esco_isco(uri: str, cache: dict[str, str]) -> str:
    """ISCO-Code der ESCO-Occupation für eine URI holen (gecacht)."""
    if uri in cache:
        return cache[uri]
    if not uri:
        cache[uri] = ""
        return ""
    detail = esco_get_occupation(uri, language="de")
    time.sleep(RATE_LIMIT)
    groups = detail.get("hasISCOGroup", [])
    code = groups[0].get("code", "") if groups else ""
    # Nur die ersten 4 Ziffern behalten (ISCO-Code kann als "2221.1" kommen)
    code = re.sub(r"\D.*", "", code)
    cache[uri] = code
    return code


def normalize_isco(value) -> str:
    """Sicherstellen dass ISCO-Code ein 4-stelliger String ist."""
    try:
        return str(int(float(value))).zfill(4)
    except (ValueError, TypeError):
        return ""


def compute_score(beruf_isco: str, esco_isco: str) -> int:
    """
    0 = kein Overlap
    1 = erste 2 Stellen stimmen überein (ISCO Major Group)
    2 = erste 4 Stellen stimmen überein (ISCO Unit Group)
    """
    if not beruf_isco or not esco_isco:
        return 0
    if esco_isco[:4] == beruf_isco[:4]:
        return 2
    if esco_isco[:2] == beruf_isco[:2]:
        return 1
    return 0


# ---------------------------------------------------------------------------
# Phase 2: Re-Enrichment
# ---------------------------------------------------------------------------

def search_variants(beruf: str) -> list[str]:
    """Gibt bereinigte Suchbegriffe in absteigender Priorität zurück."""
    variants = []

    # 1. "Dipl." Präfix entfernen
    no_dipl = re.sub(r"^[Dd]ipl\.\s*", "", beruf).strip()
    if no_dipl != beruf:
        variants.append(no_dipl)

    # 2. Klammerzusätze entfernen: "(allg. Richtung)", "(FaGe)", etc.
    no_paren = re.sub(r"\(.*?\)", "", beruf).strip()
    if no_paren != beruf and no_paren not in variants:
        variants.append(no_paren)

    # 3. Geschlechts-Suffix entfernen: "/-frau", "/-mann", "/in", "/-in", "/-er"
    no_gender = re.sub(r"\s*/[-]?(frau|mann|in|er)\b", "", beruf, flags=re.IGNORECASE).strip()
    # Auch "EFZ" und "EBA" entfernen
    no_gender = re.sub(r"\b(EFZ|EBA)\b", "", no_gender).strip()
    if no_gender and no_gender not in variants:
        variants.append(no_gender)

    # 4. Nur den ersten Teil vor "/" nehmen
    if "/" in beruf:
        first_part = beruf.split("/")[0].strip()
        first_part = re.sub(r"\b(EFZ|EBA)\b", "", first_part).strip()
        if first_part and first_part not in variants:
            variants.append(first_part)

    # 5. Basisvariante (Standard-Bereinigung wie in enrich_with_esco.py)
    base = beruf.replace("/-", " ").replace("/", " ")
    base = re.sub(r"\b(EFZ|EBA)\b", "", base).strip()
    if base and base not in variants:
        variants.append(base)

    return variants


def esco_search_by_group(isco_prefix: str, language: str = "de", limit: int = 5) -> list[dict]:
    """Direkte ISCO-Gruppen-Suche via iscoGroup= Parameter."""
    import requests
    try:
        resp = requests.get(
            "https://ec.europa.eu/esco/api/search",
            params={"iscoGroup": isco_prefix, "language": language, "type": "occupation", "limit": limit},
            headers={"Accept": "application/json"},
            timeout=15,
        )
        if resp.status_code != 200:
            return []
        return resp.json().get("_embedded", {}).get("results", [])
    except Exception:
        return []


def try_rematch(
    beruf: str,
    isco_code: str,
    group_cache: dict[str, list],
) -> tuple[str, str, str, int] | None:
    """
    Versucht einen besseren ESCO-Match zu finden.
    Gibt (uri, titel, beschreibung, score) zurück oder None.
    """
    # Textsuch-Varianten
    for query in search_variants(beruf):
        for lang in ("de", "en"):
            results = esco_search(query, language=lang, limit=5)
            time.sleep(RATE_LIMIT)
            for r in results:
                candidate_isco = re.sub(r"\D.*", "", r.get("code", ""))
                score = compute_score(isco_code, candidate_isco)
                if score >= 1:
                    uri = r.get("uri", "")
                    titel = r.get("title", beruf)
                    detail = esco_get_occupation(uri, language="de")
                    time.sleep(RATE_LIMIT)
                    beschreibung = get_description(detail, lang="de")
                    return (uri, titel, beschreibung, score)
            if results:
                break  # Deutsch hat Ergebnisse → kein Englisch-Fallback nötig

    # ISCO-Gruppen-Suche als letzter Ausweg
    if isco_code not in group_cache:
        group_cache[isco_code] = esco_search_by_group(isco_code[:4])
        time.sleep(RATE_LIMIT)

    for r in group_cache[isco_code]:
        candidate_isco = re.sub(r"\D.*", "", r.get("code", ""))
        score = compute_score(isco_code, candidate_isco)
        if score >= 1:
            uri = r.get("uri", "")
            titel = r.get("title", beruf)
            detail = esco_get_occupation(uri, language="de")
            time.sleep(RATE_LIMIT)
            beschreibung = get_description(detail, lang="de")
            return (uri, titel, beschreibung, score)

    return None


# ---------------------------------------------------------------------------
# Hauptfunktion
# ---------------------------------------------------------------------------

def verify_and_fix(
    input_file: str = "berufe_ch_esco.csv",
    output_file: str = "berufe_ch_esco_verified.csv",
) -> pd.DataFrame:
    df = pd.read_csv(PROCESSED_PATH / input_file)

    # --- Phase 1: Scores berechnen ---
    print("Phase 1: Bestehende Matches bewerten...")
    isco_cache: dict[str, str] = {}
    scores = []

    unique_uris = df["esco_uri"].dropna().unique()
    print(f"  {len(unique_uris)} eindeutige URIs werden geprüft...")

    for i, row in df.iterrows():
        beruf_isco = normalize_isco(row["isco_code"])
        uri = row.get("esco_uri", "")
        esco_isco = fetch_esco_isco(str(uri) if uri == uri else "", isco_cache)
        score = compute_score(beruf_isco, esco_isco)
        scores.append(score)
        print(f"  [{i+1:3d}/{len(df)}] {row['beruf'][:35]:<35} isco={beruf_isco} esco={esco_isco or '????'} → {score}")

    df["match_score"] = scores

    before_counts = df["match_score"].value_counts().to_dict()

    # --- Phase 2: Score-0 neu matchen ---
    bad_mask = df["match_score"] == 0
    bad_count = bad_mask.sum()
    print(f"\nPhase 2: {bad_count} schlechte Matches werden neu gesucht...")

    group_cache: dict[str, list] = {}

    for i, row in df[bad_mask].iterrows():
        beruf = row["beruf"]
        isco_code = normalize_isco(row["isco_code"])
        print(f"  Suche: {beruf} [isco: {isco_code}]...", end=" ", flush=True)

        result = try_rematch(beruf, isco_code, group_cache)
        if result:
            uri, titel, beschreibung, new_score = result
            df.at[i, "esco_uri"] = uri
            df.at[i, "esco_titel"] = titel
            df.at[i, "esco_beschreibung"] = beschreibung
            df.at[i, "match_score"] = new_score
            print(f"OK (score={new_score}, {titel[:40]})")
        else:
            print("kein Treffer")

    # --- Phase 3: Speichern + Bericht ---
    out_path = PROCESSED_PATH / output_file
    df.to_csv(out_path, index=False)

    after_counts = df["match_score"].value_counts().to_dict()
    still_bad = df[df["match_score"] == 0][["beruf", "isco_code"]]

    print(f"\n=== ESCO Match Quality ===")
    print(f"BEFORE:  score=2: {before_counts.get(2, 0):3d}  score=1: {before_counts.get(1, 0):3d}  score=0: {before_counts.get(0, 0):3d}")
    print(f"AFTER:   score=2: {after_counts.get(2, 0):3d}  score=1: {after_counts.get(1, 0):3d}  score=0: {after_counts.get(0, 0):3d}")
    if not still_bad.empty:
        print(f"\nVerbleibend ohne Match (score=0):")
        for _, r in still_bad.iterrows():
            print(f"  - {r['beruf']} [isco: {normalize_isco(r['isco_code'])}]")
    print(f"\nGespeichert: {out_path}")

    return df


if __name__ == "__main__":
    verify_and_fix()
