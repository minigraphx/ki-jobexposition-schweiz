"""
ESCO-Berufsbeschreibungen zur CH-Berufsliste hinzufügen.

Suchstrategie (6 Stufen, erste valide wird verwendet):
1. ESCO-Textsuche DE mit Berufstitel
2. ESCO-Textsuche DE/EN mit KI-generierten Alternativen (Synonyme, Oberbegriffe)
3. ESCO-Berufe der ISCO-Gruppe (ISCO-Concept-Endpunkt → narrowerOccupation)
4. berufsberatung.ch Suche (offizielle CH-Berufsberatung)
5. Wikipedia DE Extrakt
6. KI-generierte Beschreibung (mit ISCO-Kontext, Schweiz-spezifisch)

Jeder ESCO-Kandidat (Stufen 1–3) muss zwei Prüfungen bestehen:
- **ISCO-Konsistenz (hart):** ESCO-ISCO-4-Steller == unser isco_code → «korrekt»;
  gleiche 3-stellige Gruppe oder dokumentierte Ausnahme (`ISCO_AUSNAHMEN`) → «plausibel»;
  sonst verworfen (ohne Sprachmodell-Aufruf).
- **Inhaltliche Prüfung:** ein Sprachmodell bestätigt, dass die ESCO-Beschreibung zum Beruf passt.

Alle ESCO-Abfragen laufen mit `selectedVersion=v1.2.1` (ohne Versionsangabe liefern einzelne
URIs HTTP 500). Ergebnis je Beruf: esco_uri, esco_titel, esco_beschreibung, beschreibung_quelle,
esco_isco_code, esco_match_qualitaet (korrekt / plausibel / fallback).

Verwendung:
  python enrich_with_esco.py                  # nur Berufe ohne Zuordnung (neue Einträge)
  python enrich_with_esco.py --alle           # alle Berufe neu (überschreibt kuratierte Zuordnungen!)
  python enrich_with_esco.py --fix-wrong      # Einträge aus KNOWN_WRONG_MATCHES
  python enrich_with_esco.py --job "Grafik- und Multimediadesigner"

Benötigt: ANTHROPIC_API_KEY in .env (Validierung, Stufen 2 und 6).
Die ESCO-API ist aus der Cloud erreichbar (Stand Okt. 2026); sequentiell mit Pausen abfragen.
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
ESCO_VERSION = "v1.2.1"
ESCO_ISCO_URI = "http://data.europa.eu/esco/isco/C{code}"
HEADERS = {"Accept": "application/json", "User-Agent": "ki-jobexposition-ch/2.0"}
PAUSE = 0.5  # Sekunden zwischen ESCO-Abfragen
MODELL = "claude-haiku-4-5-20251001"  # Validierung, Suchbegriffe, Fallback-Beschreibung

QUELLE_ESCO = "ESCO"
QUELLE_KI = "KI-generiert"
QUALITAETEN = ("korrekt", "plausibel", "fallback")

# Bekannte falsche ESCO-Matches – werden bei --fix-wrong neu gesucht.
# Stand ESCO-Audit #52 (Okt. 2026): alle bekannten Fehlzuordnungen sind manuell korrigiert
# (docs/audit_esco_zuordnungen.md). Die früheren 25 Einträge (Abfallmakler-, Brennschneider-,
# 3D-Druck-Kontamination) bezogen sich teils auf Titel, die seit #51 zusammengelegt sind.
# Neue Fehlzuordnungen hier mit aktuellem `beruf`-Titel eintragen.
KNOWN_WRONG_MATCHES: list[str] = []

# Ausnahmen der ISCO-Konsistenzprüfung: unser isco_code → (zulässige ESCO-ISCO-Präfixe, Grund).
# Ein Kandidat aus einer dieser Gruppen gilt als «plausibel».
ISCO_AUSNAHMEN: dict[str, tuple[tuple[str, ...], str]] = {
    # ESCO-Konventionen / CH-ISCO-19-Besonderheiten
    "3221": (("5321",), "ESCO v1.2.1 hat keinen Beruf in ISCO 3221; Pflege auf mittlerer Stufe "
                        "(FaGe) steht als «nurse assistant» unter 5321"),
    "3211": (("2269",), "ESCO führt Radiologiefachpersonal (radiographer) unter 2269"),
    "3112": (("3123",), "CH-ISCO-19 führt Bauführer in 3112, ESCO die Bauleitung "
                        "(construction general supervisor) in 3123"),
    "7200": (("72",), "CH-ISCO-19-Sammelcode (Polymechaniker) ohne ISCO-08-Gruppe → "
                      "ESCO-Berufe der Untergruppe 72"),
    "2149": (("1219",), "ESCO führt Projektmanager als Führungskräfte (1219)"),
    "2511": (("1330",), "ESCO führt IT-Projektmanager als Führungskräfte (1330)"),
    "4419": (("4311",), "CH-ISCO-19 führt Bürokräfte Verkauf (Verkaufsinnendienst) als Berufsart "
                        "44192, ESCO den Verkaufssachbearbeiter (sales support assistant) unter 4311"),
    # Offene ISCO-Codes aus #51 (docs/audit_isco_codes.md): Code vermutlich falsch,
    # der ESCO-Beruf passt zum Berufstitel. Nach Klärung des Codes entfernen.
    "3312": (("4312",), "Versicherungskaufmann/-frau: Code 3312 offen (#51), ESCO insurance clerk 4312"),
    "2422": (("3321",), "Versicherungsexperte/-expertin: Code 2422 offen (#51), ESCO Underwriter 3321"),
    "4415": (("4211",), "Posthalter/in: Code 4415 offen (#51), ESCO Postschalter 4211"),
    "7421": (("3113",), "Mechatroniker/in EFZ: Code 7421 offen (#51), ESCO führt «Mechatroniker» "
                        "als Bezeichnung von Elektronikmechaniker (3113)"),
}

# ISCO Hauptgruppen für Kontext in Prompts
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
# ISCO-Konsistenz
# ---------------------------------------------------------------------------

def normalize_isco(value) -> str:
    """ISCO-Code als 4-stelligen String (z. B. 2221.0 → "2221"); leer bei ungültigem Wert."""
    try:
        return str(int(float(value))).zfill(4)
    except (ValueError, TypeError):
        return ""


def isco_konsistenz(isco_code, esco_isco) -> str | None:
    """
    Harte Validierung eines ESCO-Kandidaten gegen unseren isco_code.

    Returns:
        "korrekt"   — ESCO-ISCO-4-Steller == isco_code
        "plausibel" — gleiche 3-stellige Gruppe oder Ausnahme aus ISCO_AUSNAHMEN
        None        — inkonsistent, Kandidat verwerfen
    """
    ours = normalize_isco(isco_code)
    theirs = re.sub(r"\D", "", str(esco_isco or ""))[:4]
    if not ours or len(theirs) < 4:
        return None
    if theirs == ours:
        return "korrekt"
    if theirs[:3] == ours[:3]:
        return "plausibel"
    erlaubt = ISCO_AUSNAHMEN.get(ours)
    if erlaubt and any(theirs.startswith(p) for p in erlaubt[0]):
        return "plausibel"
    return None


# ---------------------------------------------------------------------------
# ESCO API
# ---------------------------------------------------------------------------

def _esco_get(path: str, params: dict) -> dict | None:
    """GET auf die ESCO-API mit fester Version; None bei Fehler oder HTTP ≠ 200."""
    try:
        resp = requests.get(f"{ESCO_API}/{path}",
                            params={**params, "selectedVersion": ESCO_VERSION},
                            headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        logger.debug(f"ESCO {path} HTTP {resp.status_code}: {params}")
    except Exception as e:
        logger.debug(f"ESCO {path} fehlgeschlagen: {e}")
    return None


def esco_search_text(query: str, language: str = "de", limit: int = 5) -> list[dict]:
    data = _esco_get("search", {"text": query, "language": language,
                                "type": "occupation", "limit": limit})
    return (data or {}).get("_embedded", {}).get("results", [])


def esco_get_occupation(uri: str, language: str = "de") -> dict:
    """Rohe ESCO-Occupation-Ressource (leeres dict bei Fehler)."""
    return _esco_get("resource/occupation", {"uri": uri, "language": language}) or {}


def occupation_isco_code(detail: dict) -> str:
    """ISCO-4-Steller einer ESCO-Occupation: broaderIscoGroup, sonst Präfix des ESCO-Codes
    (Unterberufe wie 2330.1.4 haben nur broaderOccupation)."""
    for g in detail.get("_links", {}).get("broaderIscoGroup", []):
        code = re.sub(r"\D", "", str(g.get("code", "")))
        if len(code) == 4:
            return code
    code = str(detail.get("code", "") or "").split(".")[0]
    return code if re.fullmatch(r"\d{4}", code) else ""


def get_description(detail: dict, lang: str = "de") -> str:
    """Beschreibung einer Occupation-Ressource (Fallback Englisch)."""
    desc = detail.get("description", {}) or {}
    for code in [lang, "en"]:
        if code in desc and desc[code].get("literal"):
            return desc[code]["literal"].strip()
    return ""


def occupation_info(detail: dict) -> dict:
    """Die für die Berufsliste relevanten Felder einer Occupation-Ressource."""
    return {
        "esco_uri": detail.get("uri", ""),
        "esco_titel": detail.get("title", "") or "",
        "esco_beschreibung": get_description(detail, "de"),
        "esco_isco_code": occupation_isco_code(detail),
    }


def esco_get_description(uri: str) -> str:
    return get_description(esco_get_occupation(uri, "de"), "de")


def _isco_concept_codes(isco_code: str) -> list[str]:
    """ISCO-Concept-Codes zum Abfragen: 4-Steller, bei CH-Sammelcodes (z. B. 7200) die
    Obergruppe ohne Nullen (72)."""
    code = normalize_isco(isco_code)
    if not code:
        return []
    codes = [code]
    gekuerzt = code.rstrip("0")
    if gekuerzt and gekuerzt != code:
        codes.append(gekuerzt)
    return codes


def esco_search_isco(isco_code: str, language: str = "de", limit: int = 10,
                     max_tiefe: int = 3) -> list[dict]:
    """
    Alle ESCO-Berufe einer ISCO-Gruppe über den Concept-Endpunkt
    (/resource/concept?uri=http://data.europa.eu/esco/isco/C{code} → _links.narrowerOccupation).

    Hat die Gruppe keine direkten Berufe (2-/3-stellige Ebene), wird rekursiv über
    narrowerConcept bis zu den 4-stelligen Gruppen abgestiegen. Der frühere Parameter
    `iscoGroup` der Suche wird von der API ignoriert (lieferte alphabetische Fehltreffer).

    Returns:
        Liste von {"uri", "title", "isco_code"} (höchstens `limit`).
    """
    ergebnis: list[dict] = []
    gesehen: set[str] = set()

    def besuchen(code: str, tiefe: int) -> None:
        if len(ergebnis) >= limit or tiefe > max_tiefe:
            return
        data = _esco_get("resource/concept",
                         {"uri": ESCO_ISCO_URI.format(code=code), "language": language})
        time.sleep(PAUSE)
        if not data:
            return
        links = data.get("_links", {})
        for occ in links.get("narrowerOccupation", []):
            uri = occ.get("uri", "")
            if uri and uri not in gesehen:
                gesehen.add(uri)
                ergebnis.append({"uri": uri, "title": occ.get("title", ""),
                                 "isco_code": str(data.get("code", code))})
                if len(ergebnis) >= limit:
                    return
        if not links.get("narrowerOccupation"):
            for sub in links.get("narrowerConcept", []):
                sub_code = str(sub.get("code") or sub.get("uri", "").rsplit("/C", 1)[-1])
                if sub_code:
                    besuchen(sub_code, tiefe + 1)

    for code in _isco_concept_codes(isco_code):
        besuchen(code, 0)
        if ergebnis:
            break
    return ergebnis[:limit]


# ---------------------------------------------------------------------------
# berufsberatung.ch (offizielle CH-Berufsberatung)
# ---------------------------------------------------------------------------

def berufsberatung_search(beruf: str) -> str:
    """
    Sucht auf berufsberatung.ch nach dem Beruf und extrahiert die Beschreibung.
    Gibt Beschreibungstext zurück oder leeren String.

    Hinweis (Okt. 2026): Die Website wurde neu aufgebaut; die alte Suche liefert keine
    Treffer mehr (Suchergebnisse werden clientseitig geladen).
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
# Sprachmodell-Hilfsfunktionen
# ---------------------------------------------------------------------------

def _parse_json(text: str) -> dict:
    """JSON aus API-Antwort extrahieren – toleriert Markdown-Code-Blöcke."""
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    return json.loads(text)


def ki_validate(client: anthropic.Anthropic, beruf: str,
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
            model=MODELL, max_tokens=64,
            messages=[{"role": "user", "content": prompt}])
        return _parse_json(resp.content[0].text).get("valid", False)
    except Exception:
        return False


def ki_alt_terms(client: anthropic.Anthropic, beruf: str,
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
            model=MODELL, max_tokens=120,
            messages=[{"role": "user", "content": prompt}])
        return _parse_json(resp.content[0].text).get("terms", [])
    except Exception:
        return []


def ki_generate_description(client: anthropic.Anthropic, beruf: str,
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
            model=MODELL, max_tokens=300,
            messages=[{"role": "user", "content": prompt}])
        text = resp.content[0].text.strip()
        # Markdown-Überschriften entfernen, die das Modell manchmal hinzufügt
        text = re.sub(r"^#+\s+.+\n+", "", text).strip()
        return text
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Hauptlogik: find_best_match mit 6 Stufen
# ---------------------------------------------------------------------------

def _fallback(beruf: str, beschreibung: str, quelle: str) -> dict:
    return {"esco_uri": "", "esco_titel": beruf, "esco_beschreibung": beschreibung,
            "beschreibung_quelle": quelle, "esco_isco_code": "",
            "esco_match_qualitaet": "fallback"}


def _try_esco_candidates(client: anthropic.Anthropic, beruf: str, isco_code: str,
                         candidates: list[dict],
                         blocked_uris: set[str] | None = None) -> dict | None:
    """Prüft Kandidaten (ISCO-Konsistenz, dann inhaltlich) und gibt den ersten gültigen zurück.

    blocked_uris: URIs, die bereits einem anderen Beruf gehören — werden übersprungen,
    um Kreuz-Kontamination (eine URI für mehrere Berufe) zu verhindern.
    """
    for c in candidates:
        uri = c.get("uri", "")
        if not uri:
            continue
        if blocked_uris and uri in blocked_uris:
            logger.debug(f"    URI geblockt (bereits vergeben): {c.get('title', '')}")
            continue
        detail = esco_get_occupation(uri, "de")
        time.sleep(PAUSE)
        if not detail:
            continue
        info = occupation_info(detail)
        qualitaet = isco_konsistenz(isco_code, info["esco_isco_code"])
        if qualitaet is None:
            logger.debug(f"    ISCO inkonsistent ({info['esco_isco_code']} ≠ {isco_code}): "
                         f"{info['esco_titel']}")
            continue
        if ki_validate(client, beruf, info["esco_titel"], info["esco_beschreibung"]):
            return {**info, "beschreibung_quelle": QUELLE_ESCO,
                    "esco_match_qualitaet": qualitaet}
        time.sleep(0.1)
    return None


def find_best_match(client: anthropic.Anthropic, beruf: str,
                    isco_code: str,
                    blocked_uris: set[str] | None = None) -> dict:
    """
    Durchläuft 6 Suchstufen und gibt ein dict mit esco_uri, esco_titel, esco_beschreibung,
    beschreibung_quelle, esco_isco_code, esco_match_qualitaet zurück.

    beschreibung_quelle-Werte:
        "ESCO"              — offizielle EU-Klassifikation (Stufen 1–3)
        "berufsberatung.ch" — offizielle CH-Berufsberatung (Stufe 4)
        "Wikipedia"         — Wikipedia DE (Stufe 5)
        "KI-generiert"      — generierte Beschreibung, kein externer Match (Stufe 6)
    """
    isco_code = normalize_isco(isco_code) or str(isco_code)
    beruf_clean = beruf.replace("/-", " ").replace("/", " ").replace("EFZ", "").strip()

    # Stufe 1: ESCO DE direkt
    logger.debug(f"  Stufe 1: ESCO DE '{beruf_clean}'")
    result = _try_esco_candidates(client, beruf, isco_code,
                                  esco_search_text(beruf_clean, "de", 5), blocked_uris)
    if result:
        logger.info(f"    ✓ Stufe 1 (ESCO DE): {result['esco_titel']}")
        return result

    # Stufe 2: ESCO mit KI-generierten Alternativen
    logger.debug("  Stufe 2: alternative Suchbegriffe")
    for term in ki_alt_terms(client, beruf, isco_code):
        for lang in ["de", "en"]:
            candidates = esco_search_text(term, lang, 5)
            time.sleep(PAUSE)
            result = _try_esco_candidates(client, beruf, isco_code, candidates, blocked_uris)
            if result:
                logger.info(f"    ✓ Stufe 2 (ESCO '{term}' {lang.upper()}): {result['esco_titel']}")
                return result

    # Stufe 3: ESCO-Berufe der ISCO-Gruppe
    logger.debug(f"  Stufe 3: ESCO ISCO-Gruppe {isco_code}")
    result = _try_esco_candidates(client, beruf, isco_code,
                                  esco_search_isco(isco_code, "de", 10), blocked_uris)
    if result:
        logger.info(f"    ✓ Stufe 3 (ESCO ISCO-{isco_code}): {result['esco_titel']}")
        return result

    # Stufe 4: berufsberatung.ch
    logger.debug("  Stufe 4: berufsberatung.ch")
    bb_desc = berufsberatung_search(beruf)
    if len(bb_desc) > 80:
        logger.info(f"    ✓ Stufe 4 (berufsberatung.ch): {len(bb_desc)} Zeichen")
        return _fallback(beruf, bb_desc, "berufsberatung.ch")
    time.sleep(0.2)

    # Stufe 5: Wikipedia DE
    logger.debug("  Stufe 5: Wikipedia DE")
    wiki_desc = wikipedia_description(beruf)
    if len(wiki_desc) > 80:
        logger.info(f"    ✓ Stufe 5 (Wikipedia DE): {len(wiki_desc)} Zeichen")
        return _fallback(beruf, wiki_desc, "Wikipedia")
    time.sleep(0.2)

    # Stufe 6: generierte Beschreibung
    logger.info("    → Stufe 6: generierte Beschreibung (kein externer Match)")
    return _fallback(beruf, ki_generate_description(client, beruf, isco_code), QUELLE_KI)


# ---------------------------------------------------------------------------
# Batch-Verarbeitung
# ---------------------------------------------------------------------------

ESCO_SPALTEN = ["esco_uri", "esco_titel", "esco_beschreibung", "beschreibung_quelle",
                "esco_isco_code", "esco_match_qualitaet"]


def enrich_jobs(jobs_df: pd.DataFrame, client: anthropic.Anthropic,
                df_existing: pd.DataFrame | None = None) -> pd.DataFrame:
    total = len(jobs_df)
    ergebnisse: list[dict] = []

    # URIs der nicht neu zu verarbeitenden Berufe sperren
    # (verhindert Kreuz-Kontamination: keine URI wird zwei Berufen zugewiesen)
    used_uris: set[str] = set()
    if df_existing is not None:
        jobs_being_updated = set(jobs_df["beruf"])
        for _, r in df_existing.iterrows():
            if r["beruf"] not in jobs_being_updated:
                uri = r.get("esco_uri", "")
                if isinstance(uri, str) and uri.strip():
                    used_uris.add(uri.strip())

    for i, (_, row) in enumerate(jobs_df.iterrows(), 1):
        beruf = row["beruf"]
        isco = normalize_isco(row["isco_code"]) or str(row["isco_code"])
        logger.info(f"[{i:3d}/{total}] {beruf}")

        if df_existing is not None:
            prev = df_existing[df_existing["beruf"] == beruf]
            if not prev.empty:
                p = prev.iloc[0]
                logger.info(f"    VORHER  titel: {p.get('esco_titel', '') or '–'}")
                logger.info(f"    VORHER  desc:  {str(p.get('esco_beschreibung', '') or '–')[:120]}")

        match = find_best_match(client, beruf, isco, blocked_uris=used_uris)
        if match["esco_uri"]:
            used_uris.add(match["esco_uri"])  # neu vergebene URI für folgende Berufe sperren
        ergebnisse.append(match)

        logger.info(f"    NACHHER quelle: {match['beschreibung_quelle']} "
                    f"({match['esco_match_qualitaet']})")
        logger.info(f"    NACHHER titel:  {match['esco_titel']}")
        logger.info(f"    NACHHER desc:   {match['esco_beschreibung'][:120]}")
        time.sleep(PAUSE)

    result = jobs_df.copy().reset_index(drop=True)
    for col in ESCO_SPALTEN:
        result[col] = [m[col] for m in ergebnisse]
    return result


def merge_into(df_existing: pd.DataFrame, enriched: pd.DataFrame) -> pd.DataFrame:
    """Neue Zuordnungen in die bestehende Tabelle übernehmen; neue Berufe anhängen."""
    df_out = df_existing.copy()
    for col in ESCO_SPALTEN:
        if col not in df_out.columns:
            df_out[col] = ""
        df_out[col] = df_out[col].astype(object)
    neu = []
    for _, row in enriched.iterrows():
        mask = df_out["beruf"] == row["beruf"]
        if mask.any():
            for col in ESCO_SPALTEN:
                df_out.loc[mask, col] = row[col]
        else:
            neu.append(row)
    if neu:
        df_out = pd.concat([df_out, pd.DataFrame(neu)], ignore_index=True)
    return df_out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="ESCO-Enrichment mit ISCO-Konsistenzprüfung")
    parser.add_argument("--fix-wrong", action="store_true",
                        help="Nur die Einträge aus KNOWN_WRONG_MATCHES neu suchen")
    parser.add_argument("--job", type=str, default=None,
                        help="Einzelnen Beruf verarbeiten")
    parser.add_argument("--alle", action="store_true",
                        help="Alle Berufe neu (überschreibt kuratierte Zuordnungen)")
    args = parser.parse_args()

    df_base = pd.read_csv(PROCESSED_PATH / "berufe_ch.csv")
    df_existing = pd.read_csv(PROCESSED_PATH / "berufe_ch_esco.csv")

    if args.job:
        target_jobs = [args.job]
    elif args.fix_wrong:
        target_jobs = KNOWN_WRONG_MATCHES
        if not target_jobs:
            logger.info("KNOWN_WRONG_MATCHES ist leer — nichts zu tun.")
            return
    elif args.alle:
        target_jobs = df_base["beruf"].tolist()
    else:
        zugeordnet = set()
        if "esco_match_qualitaet" in df_existing.columns:
            zugeordnet = set(df_existing.loc[
                df_existing["esco_match_qualitaet"].isin(QUALITAETEN), "beruf"])
        target_jobs = [b for b in df_base["beruf"] if b not in zugeordnet]
        if not target_jobs:
            logger.info("Alle Berufe haben eine Zuordnung — nichts zu tun "
                        "(--job, --fix-wrong oder --alle).")
            return

    target_df = df_base[df_base["beruf"].isin(target_jobs)].reset_index(drop=True)
    not_found = [j for j in target_jobs if j not in df_base["beruf"].values]
    if not_found:
        logger.warning(f"Nicht in berufe_ch.csv gefunden: {not_found}")

    client = make_client()
    logger.info(f"Verarbeite {len(target_df)} Berufe mit 6-stufiger Suchstrategie...")
    enriched = enrich_jobs(target_df, client, df_existing)
    df_out = merge_into(df_existing, enriched)

    output_esco = PROCESSED_PATH / "berufe_ch_esco.csv"
    output_verified = PROCESSED_PATH / "berufe_ch_esco_verified.csv"
    df_out.to_csv(output_esco, index=False)
    df_out.to_csv(output_verified, index=False)

    with_uri = (df_out["esco_uri"].fillna("").astype(str).str.strip() != "").sum()
    logger.info(f"Gespeichert: {output_esco}")
    logger.info(f"Mit ESCO-URI: {with_uri}/{len(df_out)}")
    logger.info(f"Mit Fallback-Beschreibung: {len(df_out) - with_uri}/{len(df_out)}")


if __name__ == "__main__":
    main()
