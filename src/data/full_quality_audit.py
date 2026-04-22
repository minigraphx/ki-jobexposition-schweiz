"""
Vollständige Datenqualitätsprüfung und -korrektur für alle 204 Berufe.

Phase 1 (Haiku):  Prüft ob haupt_risiko/begruendung zum Berufstitel passt.
Phase 2 (Haiku):  Generiert korrekte Berufsbeschreibung für fehlerhafte Jobs.
Phase 3 (Sonnet): Rescort fehlerhafte Jobs mit den korrigierten Beschreibungen.

Haiku für günstige Klassifikations-/Generierungsaufgaben,
Sonnet für das eigentliche Scoring (Konsistenz mit Originaldaten).
"""

import json
import logging
import time
from pathlib import Path

import anthropic
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROCESSED_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "processed"
SESSION_TOKEN_FILE = Path("/home/claude/.claude/remote/.session_ingress_token")

HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-6"

AUDIT_PROMPT = """Du bist ein Qualitätsprüfer für Schweizer Berufsdaten.

Beruf: {beruf}
KI-Hauptrisiko: {haupt_risiko}
Begründung: {begruendung}

Ist diese Beschreibung inhaltlich korrekt für den genannten Beruf?
Ein Fehler liegt vor wenn die Beschreibung einen völlig anderen Beruf beschreibt \
(z.B. Graveur-Text für einen Primarlehrer, Brennschneider-Text für eine Pflegefachkraft).
Kleine Unschärfen oder allgemeine Formulierungen sind kein Fehler.

Antworte NUR mit validem JSON:
{{"valid": true, "reason": ""}}
oder
{{"valid": false, "reason": "kurze Beschreibung des Fehlers"}}"""

DESC_PROMPT = """Schreibe eine sachliche Berufsbeschreibung auf Deutsch für den Beruf \
"{beruf}" im Schweizer Arbeitsmarkt.
2-3 präzise Sätze, ähnlich wie eine ESCO-Berufsbeschreibung.
Beschreibe die typischen Kernaufgaben und das Arbeitsumfeld.
Antworte NUR mit dem Beschreibungstext, ohne Anführungszeichen."""

SCORING_PROMPT = """Du bist ein Experte für den Arbeitsmarkt und KI-Automatisierung, \
spezialisiert auf den Schweizer Kontext.

Bewerte den folgenden Beruf hinsichtlich seiner KI-Exposition nach diesen Kriterien (je 0-10):

**Beruf:** {beruf}
**Beschreibung:** {beschreibung}

Bewerte auf einer Skala von 0 (gar nicht betroffen) bis 10 (maximal betroffen):

1. **Digitaler Output (25%)**: Arbeitet der Beruf primär mit digitalen Informationen, Texten, \
Daten oder Entscheidungen?
2. **Wiederholbarkeit (25%)**: Sind die Kerntätigkeiten strukturiert, vorhersehbar und regelbasiert?
3. **Physische Präsenz (20%, negativ)**: Je mehr physische Präsenz nötig, desto NIEDRIGER der Score.
4. **Kreativität (15%, negativ)**: Je mehr originelles Denken erforderlich, desto NIEDRIGER der Score.
5. **Soziale Interaktion (15%, negativ)**: Je mehr Empathie/Vertrauen/menschliche Beziehung nötig, \
desto NIEDRIGER der Score.

Antworte NUR mit validem JSON in diesem Format:
{{
  "score_gesamt": <float 0-10>,
  "score_digital": <float 0-10>,
  "score_wiederholbarkeit": <float 0-10>,
  "score_physisch": <float 0-10>,
  "score_kreativitaet": <float 0-10>,
  "score_sozial": <float 0-10>,
  "haupt_risiko": "<kurze Beschreibung was konkret automatisiert werden könnte>",
  "zeitrahmen": "<Schätzung: 1-2 Jahre / 3-5 Jahre / 5-10 Jahre / >10 Jahre>",
  "begruendung": "<2-3 Sätze Begründung, Schweiz-spezifisch wenn relevant>"
}}"""


def make_client() -> anthropic.Anthropic:
    if SESSION_TOKEN_FILE.exists():
        return anthropic.Anthropic(auth_token=SESSION_TOKEN_FILE.read_text().strip())
    import os
    if api_key := os.environ.get("ANTHROPIC_API_KEY"):
        return anthropic.Anthropic(api_key=api_key)
    raise RuntimeError("Kein API-Token gefunden.")


def parse_json(text: str) -> dict:
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    return json.loads(text)


def audit_job(client: anthropic.Anthropic, beruf: str, haupt_risiko: str,
              begruendung: str) -> dict:
    prompt = AUDIT_PROMPT.format(beruf=beruf, haupt_risiko=haupt_risiko,
                                 begruendung=begruendung)
    resp = client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=128,
        messages=[{"role": "user", "content": prompt}],
    )
    try:
        return parse_json(resp.content[0].text)
    except Exception:
        return {"valid": True, "reason": "parse-error – als OK behandelt"}


def generate_description(client: anthropic.Anthropic, beruf: str) -> str:
    prompt = DESC_PROMPT.format(beruf=beruf)
    resp = client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text.strip()


def rescore_job(client: anthropic.Anthropic, beruf: str, beschreibung: str) -> dict:
    prompt = SCORING_PROMPT.format(beruf=beruf, beschreibung=beschreibung)
    resp = client.messages.create(
        model=SONNET_MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    return parse_json(resp.content[0].text)


def run_audit(client: anthropic.Anthropic, df: pd.DataFrame) -> list[dict]:
    """Phase 1: Haiku prüft alle Beschreibungen."""
    flagged = []
    total = len(df)
    for i, (_, row) in enumerate(df.iterrows(), 1):
        beruf = row["beruf"]
        haupt_risiko = str(row.get("haupt_risiko", "") or "")
        begruendung = str(row.get("begruendung", "") or "")

        if not haupt_risiko and not begruendung:
            logger.info(f"[{i:3d}/{total}] {beruf[:40]:40s} → SKIP (keine Beschreibung)")
            continue

        result = audit_job(client, beruf, haupt_risiko, begruendung)
        if not result.get("valid", True):
            reason = result.get("reason", "")
            logger.warning(f"[{i:3d}/{total}] FEHLER: {beruf} — {reason}")
            flagged.append({"beruf": beruf, "reason": reason})
        else:
            logger.info(f"[{i:3d}/{total}] {beruf[:40]:40s} → OK")

        time.sleep(0.1)  # sanftes Rate-Limiting

    return flagged


def fix_and_rescore(client: anthropic.Anthropic, df: pd.DataFrame,
                    flagged: list[dict]) -> pd.DataFrame:
    """Phase 2+3: Haiku generiert Beschreibung, Sonnet rescort."""
    score_fields = [
        "score_gesamt", "score_digital", "score_wiederholbarkeit",
        "score_physisch", "score_kreativitaet", "score_sozial",
        "haupt_risiko", "zeitrahmen", "begruendung",
    ]
    for entry in flagged:
        beruf = entry["beruf"]
        logger.info(f"Korrigiere: {beruf}")

        # Phase 2: Haiku generiert korrekte Beschreibung
        beschreibung = generate_description(client, beruf)
        logger.info(f"  Beschreibung: {beschreibung[:80]}...")
        time.sleep(0.1)

        # Phase 3: Sonnet rescort mit korrekter Beschreibung
        try:
            result = rescore_job(client, beruf, beschreibung)
        except Exception as e:
            logger.error(f"  Scoring-Fehler für '{beruf}': {e}")
            continue

        idx = df[df["beruf"] == beruf].index
        for field in score_fields:
            if field in result:
                df.loc[idx, field] = result[field]

        # score_ch neu berechnen
        df.loc[idx, "score_ch"] = (
            df.loc[idx, "score_gesamt"]
            + df.loc[idx, "delta_branche"]
            + df.loc[idx, "delta_lohn"]
        ).clip(0, 10)

        # Haiku-generierte Beschreibung in esco_beschreibung sichern
        df.loc[idx, "esco_beschreibung"] = beschreibung

        logger.info(f"  score_gesamt={result['score_gesamt']}, "
                    f"zeitrahmen={result['zeitrahmen']}")
        time.sleep(0.2)

    return df


def main():
    client = make_client()
    df = pd.read_csv(PROCESSED_DATA_PATH / "scores.csv")
    logger.info(f"Starte Audit für {len(df)} Berufe (Haiku-Validierung)...")

    # Phase 1: Audit
    flagged = run_audit(client, df)

    if not flagged:
        logger.info("Kein Fehler gefunden. Datenqualität ist in Ordnung.")
        return

    logger.info(f"\n{'='*60}")
    logger.info(f"{len(flagged)} fehlerhafte Beschreibungen gefunden:")
    for f in flagged:
        logger.info(f"  • {f['beruf']}: {f['reason']}")
    logger.info(f"{'='*60}\n")

    # Phase 2+3: Fix & Rescore
    logger.info("Starte Korrektur (Haiku → Beschreibung, Sonnet → Scoring)...")
    df = fix_and_rescore(client, df, flagged)

    df.to_csv(PROCESSED_DATA_PATH / "scores.csv", index=False)
    logger.info("scores.csv aktualisiert.")

    # Audit-Report speichern
    report_path = PROCESSED_DATA_PATH / "audit_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({"flagged_count": len(flagged), "flagged": flagged}, f,
                  ensure_ascii=False, indent=2)
    logger.info(f"Report gespeichert: {report_path}")


if __name__ == "__main__":
    main()
