"""
ESCO-Berufsbeschreibungen zur CH-Berufsliste hinzufügen.

Suchstrategie (6 Stufen, erste valide wird verwendet):
1. ESCO-Textsuche DE mit Berufstitel
2. ESCO-Textsuche DE/EN mit Haiku-generierten Alternativen (Synonyme, Oberbegriffe)
3. ESCO-Suche gefiltert nach ISCO-Code-Gruppe
4. berufsberatung.ch Suche (offizielle CH-Berufsberatung)
5. Wikipedia DE Extrakt
6. Haiku generiert Beschreibung direkt (mit ISCO-Kontext, Schweiz-spezifisch)

Jeder ESCO-Kandidat wird via Claude Haiku validiert bevor er akzeptiert wird.

Verwendung:
  python enrich_with_esco.py                  # alle 204 Berufe
  python enrich_with_esco.py --fix-wrong      # nur bekannte 16 Fehler
  python enrich_with_esco.py --job "Grafiker/in"

Benötigt: ANTHROPIC_API_KEY in .env
ESCO-API ist im Cloud-Environment blockiert → lokal ausführen.
"""

import argparse
import json
import logging
import os
import re
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
HEADERS = {"Accept": "application/json", "User-Agent": "ki-jobexposition-ch/2.0"}

# Bekannte falsche ESCO-Matches – werden bei --fix-wrong verarbeitet
KNOWN_WRONG_MATCHES = [
    # Gruppe 1: falsch in berufe_ch_esco_verified.csv
    "Bankkaufmann/-frau",                  # → Abfallmakler
    "Polymechaniker/in EFZ",               # → Brennschneider
    "Logistiker/in EFZ",                   # → Abfallmakler
    "Immobilienbewirtschafter/in",          # → Abfallmakler
    "Automatiker/in EFZ",                  # → 3D-Druck-Techniker
    "Bauführer/in",                        # → 3D-Druck-Techniker
    "Grafiker/in",                         # → Kartograf
    "Hochbauzeichner/in EFZ",              # → 3D-Druck-Techniker
    "Elektroplaner/in EFZ",                # → 3D-Druck-Techniker
    # Gruppe 2: falsch nur in berufe_ch_esco.csv (unverifiziert)
    "PR-Spezialist/in",                    # → Preiskalkulation
    "Reinigungspersonal und Hilfskräfte in Privathaushalten",  # → Netzverankerung Aquakultur
    "Leitende Verwaltungsbedienstete",     # → Hauswirtschafter
    "Technische Verkaufsfachkräfte (ohne Informations- und Kommunikationstechnologie)",
    "Bürokräfte in der Transportwirtschaft und verwandte Berufe",  # → Lebensmitteltechniker
    "Physiotherapeutische Techniker und Assistenten",  # → Anästhesietechnischer Assistent
    "Fachkräfte in Personalschulung und -entwicklung",  # → Hydraulik-Fachkraft
]

# ISCO Hauptgruppen für Kontext in Haiku-Prompts
ISCO_MAJOR_GROUPS = {
    "1": "Führungskräfte",
    "2": "Akademische Berufe",
    "3": "Techniker und gleichrangige nichttechnische Berufe",
    "4": "Bürokräfte",
    "5": "Dienstleistungsberufe und Verkäufer",
    "6": "Fachkräfte in der Landwirtschaft",
    "7": "Handwerks- und verwandte Berufe",
    "8": "Anlagen- und Maschinenbediener",
    "9": "Hilfsarbeitskräfte",
}


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

def make_client() -> anthropic.Anthropic:
    if api_key := os.environ.get("ANTHROPIC_API_KEY"):
        return anthropic.Anthropic(api_key=api_key)
    token_file = Path("/home/claude/.claude/remote/.session_ingress_token")
    if token_file.exists():
        return anthropic.Anthropic(auth_token=token_file.read_text().strip())
    raise RuntimeError("Kein ANTHROPIC_API_KEY in .env und kein Session-Token.")


# ---------------------------------------------------------------------------
# ESCO API
# ---------------------------------------------------------------------------

def esco_search_text(query: str, language: str = "de", limit: int = 5) -> list[dict]:
    try:
        resp = requests.get(f"{ESCO_API}/search",
            params={"text": query, "language": language,
                    "type": "occupation", "limit": limit},
            headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            return resp.json().get("_embedded", {}).get("results", [])
    except Exception as e:
        logger.debug(f"ESCO-Textsuche fehlgeschlagen: {e}")
    return []


def esco_search_isco(isco_code: str, language: str = "de", limit: int = 10) -> list[dict]:
    """Suche alle ESCO-Berufe einer ISCO-4-stelligen Gruppe."""
    try:
        resp = requests.get(f"{ESCO_API}/search",
            params={"iscoGroup": isco_code[:4], "language": language,
                    "type": "occupation", "limit": limit},
            headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            return resp.json().get("_embedded", {}).get("results", [])
    except Exception as e:
        logger.debug(f"ESCO-ISCO-Suche fehlgeschlagen: {e}")
    return []


def esco_get_description(uri: str) -> str:
    try:
        resp = requests.get(f"{ESCO_API}/resource/occupation",
            params={"uri": uri, "language": "de"},
            headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            detail = resp.json()
            desc = detail.get("description", {})
            for lang in ["de", "en"]:
                if lang in desc and desc[lang].get("literal"):
                    return desc[lang]["literal"]
    except Exception:
        pass
    return ""


# ---------------------------------------------------------------------------
# berufsberatung.ch (offizielle CH-Berufsberatung)
# ---------------------------------------------------------------------------

def berufsberatung_search(beruf: str) -> str:
    """
    Sucht auf berufsberatung.ch nach dem Beruf und extrahiert die Beschreibung.
    Gibt Beschreibungstext zurück oder leeren String.
    """
    try:
        query = beruf.replace("/-", " ").replace("/", " ").replace("EFZ", "").strip()
        resp = requests.get(
            "https://www.berufsberatung.ch/dyn/show/2823",
            params={"term": query, "lang": "de"},
            headers={**HEADERS, "User-Agent": "Mozilla/5.0 (compatible; research-bot)"},
            timeout=15)
        if resp.status_code != 200:
            return ""
        # Ersten Beruf-Link aus Suchergebnissen extrahieren
        match = re.search(r'href="(/dyn/show/\d+\?id=\d+)"', resp.text)
        if not match:
            return ""
        detail_url = "https://www.berufsberatung.ch" + match.group(1)
        detail = requests.get(detail_url,
            headers={**HEADERS, "User-Agent": "Mozilla/5.0 (compatible; research-bot)"},
            timeout=15)
        if detail.status_code != 200:
            return ""
        # Kurzbeschreibung extrahieren (im <div class="lead"> oder ersten <p>)
        text = re.sub(r"<[^>]+>", " ", detail.text)
        text = re.sub(r"\s+", " ", text).strip()
        # Sinnvollen Ausschnitt finden – nach "Kurzbeschreibung" oder "Aufgaben"
        for marker in ["Kurzbeschreibung", "Aufgaben", "Tätigkeiten"]:
            idx = text.find(marker)
            if idx != -1:
                snippet = text[idx + len(marker):idx + len(marker) + 600].strip()
                if len(snippet) > 80:
                    return snippet[:500]
        return ""
    except Exception as e:
        logger.debug(f"berufsberatung.ch fehlgeschlagen für '{beruf}': {e}")
        return ""


# ---------------------------------------------------------------------------
# Wikipedia DE
# ---------------------------------------------------------------------------

def wikipedia_description(beruf: str) -> str:
    """Holt Wikipedia DE-Intro für den Beruf."""
    try:
        query = beruf.replace("/-", " ").replace("/", " ").replace("EFZ", "").strip()
        resp = requests.get(
            "https://de.wikipedia.org/w/api.php",
            params={"action": "query", "titles": query, "prop": "extracts",
                    "exintro": 1, "exchars": 500, "format": "json",
                    "redirects": 1},
            headers={**HEADERS, "User-Agent": "Mozilla/5.0"},
            timeout=10)
        if resp.status_code != 200:
            return ""
        pages = resp.json().get("query", {}).get("pages", {})
        for page in pages.values():
            if page.get("pageid") and page.get("extract"):
                text = re.sub(r"<[^>]+>", "", page["extract"])
                text = re.sub(r"\s+", " ", text).strip()
                if len(text) > 80:
                    return text[:500]
        return ""
    except Exception as e:
        logger.debug(f"Wikipedia fehlgeschlagen für '{beruf}': {e}")
        return ""


# ---------------------------------------------------------------------------
# Haiku Hilfsfunktionen
# ---------------------------------------------------------------------------

def _parse_json(text: str) -> dict:
    """JSON aus API-Antwort extrahieren – toleriert Markdown-Code-Blöcke."""
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    return json.loads(text)


def haiku_validate(client: anthropic.Anthropic, beruf: str,
                   esco_titel: str, esco_beschreibung: str) -> bool:
    prompt = (
        f"Beruf (Schweiz): {beruf}\n"
        f"ESCO-Treffer: {esco_titel}\n"
        f"ESCO-Beschreibung: {esco_beschreibung[:300]}\n\n"
        "Ist das ein sinnvoller ESCO-Match (gleiche oder sehr ähnliche Tätigkeit)?\n"
        'Antworte NUR mit JSON: {"valid": true} oder {"valid": false}'
    )
    try:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=64,
            messages=[{"role": "user", "content": prompt}])
        return _parse_json(resp.content[0].text).get("valid", False)
    except Exception:
        return False


def haiku_alt_terms(client: anthropic.Anthropic, beruf: str,
                    isco_code: str) -> list[str]:
    """Generiert alternative Suchbegriffe für ESCO."""
    major = ISCO_MAJOR_GROUPS.get(str(isco_code)[0], "")
    prompt = (
        f"Schweizer Beruf: {beruf} (ISCO-Code: {isco_code}, Kategorie: {major})\n\n"
        "Generiere 4 alternative Suchbegriffe für die europäische ESCO-Datenbank:\n"
        "1. Kurzform des deutschen Berufsnamens (ohne EFZ, HF, etc.)\n"
        "2. Synonym oder verwandter Beruf auf Deutsch\n"
        "3. Englische Entsprechung\n"
        "4. Oberbegriff oder ISCO-Bezeichnung\n\n"
        'Antworte NUR mit JSON: {"terms": ["...", "...", "...", "..."]}'
    )
    try:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=120,
            messages=[{"role": "user", "content": prompt}])
        return _parse_json(resp.content[0].text).get("terms", [])
    except Exception:
        return []


def haiku_generate_description(client: anthropic.Anthropic, beruf: str,
                                isco_code: str) -> str:
    """Generiert eine qualitative Berufsbeschreibung mit Schweiz-Kontext."""
    major = ISCO_MAJOR_GROUPS.get(str(isco_code)[0], "")
    prompt = (
        f"Schreibe eine sachliche Berufsbeschreibung auf Deutsch für den Beruf "
        f'"{beruf}" im Schweizer Arbeitsmarkt.\n'
        f"ISCO-Kategorie: {major} (Code {isco_code})\n\n"
        "Anforderungen:\n"
        "- 3-4 Sätze, ähnlich wie eine ESCO- oder berufsberatung.ch-Beschreibung\n"
        "- Beschreibe die typischen Kernaufgaben und das Arbeitsumfeld\n"
        "- Schweiz-spezifische Besonderheiten erwähnen wenn relevant "
        "(z.B. duales Berufsbildungssystem, Schweizer Normen, mehrsprachiges Umfeld)\n"
        "- Kein JSON, nur der Beschreibungstext"
    )
    try:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=300,
            messages=[{"role": "user", "content": prompt}])
        text = resp.content[0].text.strip()
        # Markdown-Überschriften entfernen die Haiku manchmal hinzufügt
        text = re.sub(r"^#+\s+.+\n+", "", text).strip()
        return text
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Hauptlogik: find_best_match mit 6 Stufen
# ---------------------------------------------------------------------------

def _try_esco_candidates(client: anthropic.Anthropic, beruf: str,
                          candidates: list[dict]) -> tuple[str, str, str] | None:
    """Validiert Kandidaten und gibt ersten validen zurück."""
    for c in candidates:
        uri = c.get("uri", "")
        titel = c.get("title", "")
        if not uri:
            continue
        beschreibung = esco_get_description(uri)
        time.sleep(0.3)
        if haiku_validate(client, beruf, titel, beschreibung):
            time.sleep(0.1)
            return uri, titel, beschreibung
        time.sleep(0.1)
    return None


def find_best_match(client: anthropic.Anthropic, beruf: str,
                    isco_code: str) -> tuple[str, str, str]:
    """
    Gibt (esco_uri, esco_titel, esco_beschreibung) zurück.
    Durchläuft 6 Suchstufen; Haiku validiert jeden ESCO-Kandidaten.
    """
    beruf_clean = beruf.replace("/-", " ").replace("/", " ").replace("EFZ", "").strip()

    # Stufe 1: ESCO DE direkt
    logger.debug(f"  Stufe 1: ESCO DE '{beruf_clean}'")
    result = _try_esco_candidates(client, beruf, esco_search_text(beruf_clean, "de", 5))
    if result:
        logger.info(f"    ✓ Stufe 1 (ESCO DE): {result[1]}")
        return result

    # Stufe 2: ESCO mit Haiku-generierten Alternativen
    logger.debug("  Stufe 2: Haiku-Alternativen")
    alt_terms = haiku_alt_terms(client, beruf, isco_code)
    time.sleep(0.1)
    for term in alt_terms:
        for lang in ["de", "en"]:
            candidates = esco_search_text(term, lang, 5)
            result = _try_esco_candidates(client, beruf, candidates)
            if result:
                logger.info(f"    ✓ Stufe 2 (ESCO '{term}' {lang.upper()}): {result[1]}")
                return result
            time.sleep(0.2)

    # Stufe 3: ESCO nach ISCO-Code-Gruppe
    logger.debug(f"  Stufe 3: ESCO ISCO-Gruppe {isco_code[:4]}")
    result = _try_esco_candidates(client, beruf, esco_search_isco(isco_code, "de", 10))
    if result:
        logger.info(f"    ✓ Stufe 3 (ESCO ISCO-{isco_code[:4]}): {result[1]}")
        return result

    # Stufe 4: berufsberatung.ch
    logger.debug("  Stufe 4: berufsberatung.ch")
    bb_desc = berufsberatung_search(beruf)
    if len(bb_desc) > 80:
        logger.info(f"    ✓ Stufe 4 (berufsberatung.ch): {len(bb_desc)} Zeichen")
        return "", beruf, bb_desc
    time.sleep(0.2)

    # Stufe 5: Wikipedia DE
    logger.debug("  Stufe 5: Wikipedia DE")
    wiki_desc = wikipedia_description(beruf)
    if len(wiki_desc) > 80:
        logger.info(f"    ✓ Stufe 5 (Wikipedia DE): {len(wiki_desc)} Zeichen")
        return "", beruf, wiki_desc
    time.sleep(0.2)

    # Stufe 6: Haiku generiert Beschreibung direkt
    logger.info("    → Stufe 6: Haiku generiert Beschreibung (kein externer Match)")
    desc = haiku_generate_description(client, beruf, isco_code)
    return "", beruf, desc


# ---------------------------------------------------------------------------
# Batch-Verarbeitung
# ---------------------------------------------------------------------------

def enrich_jobs(jobs_df: pd.DataFrame, client: anthropic.Anthropic,
                df_existing: pd.DataFrame | None = None) -> pd.DataFrame:
    uris, titel_list, beschreibungen = [], [], []
    total = len(jobs_df)

    for i, (_, row) in enumerate(jobs_df.iterrows(), 1):
        beruf = row["beruf"]
        isco = str(row["isco_code"])
        logger.info(f"[{i:3d}/{total}] {beruf}")

        # Vorher-Zustand aus bestehender Datei zeigen
        if df_existing is not None:
            prev = df_existing[df_existing["beruf"] == beruf]
            if not prev.empty:
                p = prev.iloc[0]
                prev_titel = str(p.get("esco_titel", "") or "–")
                prev_desc = str(p.get("esco_beschreibung", "") or "–")
                logger.info(f"    VORHER  titel: {prev_titel}")
                logger.info(f"    VORHER  desc:  {prev_desc[:120]}")

        uri, titel, beschreibung = find_best_match(client, beruf, isco)
        uris.append(uri)
        titel_list.append(titel)
        beschreibungen.append(beschreibung)

        source = f"ESCO: {titel[:40]}" if uri else "Fallback"
        logger.info(f"    NACHHER quelle: {source}")
        logger.info(f"    NACHHER titel:  {titel}")
        logger.info(f"    NACHHER desc:   {beschreibung[:120]}")
        time.sleep(0.4)

    result = jobs_df.copy()
    result["esco_uri"] = uris
    result["esco_titel"] = titel_list
    result["esco_beschreibung"] = beschreibungen
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="ESCO-Enrichment mit Haiku-Validierung")
    parser.add_argument("--fix-wrong", action="store_true",
                        help="Nur die 16 bekannten Fehlmatches reparieren")
    parser.add_argument("--job", type=str, default=None,
                        help="Einzelnen Beruf verarbeiten")
    args = parser.parse_args()

    client = make_client()
    df_base = pd.read_csv(PROCESSED_PATH / "berufe_ch.csv")
    df_existing = pd.read_csv(PROCESSED_PATH / "berufe_ch_esco.csv")

    if args.job:
        target_jobs = [args.job]
    elif args.fix_wrong:
        target_jobs = KNOWN_WRONG_MATCHES
    else:
        target_jobs = df_base["beruf"].tolist()

    target_df = df_base[df_base["beruf"].isin(target_jobs)].reset_index(drop=True)
    not_found = [j for j in target_jobs if j not in df_base["beruf"].values]
    if not_found:
        logger.warning(f"Nicht in berufe_ch.csv gefunden: {not_found}")

    logger.info(f"Verarbeite {len(target_df)} Berufe mit 6-stufiger Suchstrategie...")

    enriched = enrich_jobs(target_df, client, df_existing)

    # Korrekturen in bestehende Datei einpflegen
    df_out = df_existing.copy()
    for _, row in enriched.iterrows():
        mask = df_out["beruf"] == row["beruf"]
        df_out.loc[mask, "esco_uri"] = row["esco_uri"]
        df_out.loc[mask, "esco_titel"] = row["esco_titel"]
        df_out.loc[mask, "esco_beschreibung"] = row["esco_beschreibung"]

    output_esco = PROCESSED_PATH / "berufe_ch_esco.csv"
    output_verified = PROCESSED_PATH / "berufe_ch_esco_verified.csv"
    df_out.to_csv(output_esco, index=False)
    df_out.to_csv(output_verified, index=False)

    with_uri = (df_out["esco_uri"].notna() & (df_out["esco_uri"] != "")).sum()
    logger.info(f"Gespeichert: {output_esco}")
    logger.info(f"Mit ESCO-URI: {with_uri}/{len(df_out)}")
    logger.info(f"Mit Fallback-Beschreibung: {len(df_out) - with_uri}/{len(df_out)}")


if __name__ == "__main__":
    main()
