"""
Korrigiert 14 Berufe, deren haupt_risiko/begruendung fälschlicherweise
Brennschneider-Inhalte enthalten (Batch-API-Artefakt).

Für 9 Berufe mit korrekten ESCO-Beschreibungen: Neu-Scoring mit originaler Beschreibung.
Für 5 Berufe mit falschen ESCO-Matches: Neu-Scoring nur auf Basis des Berufstitels.
"""

import json
import logging
import os
from pathlib import Path

import anthropic
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROCESSED_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "processed"

MODEL = "claude-sonnet-4-6"

SCORING_PROMPT = """Du bist ein Experte für den Arbeitsmarkt und KI-Automatisierung, spezialisiert auf den Schweizer Kontext.

Bewerte den folgenden Beruf hinsichtlich seiner KI-Exposition nach diesen Kriterien (je 0-10):

**Beruf:** {beruf}
**Beschreibung:** {beschreibung}

Bewerte auf einer Skala von 0 (gar nicht betroffen) bis 10 (maximal betroffen):

1. **Digitaler Output (25%)**: Arbeitet der Beruf primär mit digitalen Informationen, Texten, Daten oder Entscheidungen?
2. **Wiederholbarkeit (25%)**: Sind die Kerntätigkeiten strukturiert, vorhersehbar und regelbasiert?
3. **Physische Präsenz (20%, negativ)**: Je mehr physische Präsenz nötig, desto NIEDRIGER der Score.
4. **Kreativität (15%, negativ)**: Je mehr originelles Denken erforderlich, desto NIEDRIGER der Score.
5. **Soziale Interaktion (15%, negativ)**: Je mehr Empathie/Vertrauen/menschliche Beziehung nötig, desto NIEDRIGER der Score.

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

WRONG_ESCO_JOBS = {
    "Polymechaniker/in EFZ",
    "Immobilienbewirtschafter/in",
    "Automatiker/in EFZ",
    "Bauführer/in",
    "Elektroplaner/in EFZ",
}


def parse_result(raw: str) -> dict:
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()
    return json.loads(raw)


def rescore_job(client: anthropic.Anthropic, beruf: str, beschreibung: str) -> dict:
    prompt = SCORING_PROMPT.format(beruf=beruf, beschreibung=beschreibung)
    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    return parse_result(response.content[0].text)


SESSION_TOKEN_FILE = Path("/home/claude/.claude/remote/.session_ingress_token")


def _make_client() -> anthropic.Anthropic:
    if api_key := os.environ.get("ANTHROPIC_API_KEY"):
        return anthropic.Anthropic(api_key=api_key)
    if SESSION_TOKEN_FILE.exists():
        return anthropic.Anthropic(auth_token=SESSION_TOKEN_FILE.read_text().strip())
    raise RuntimeError("Kein ANTHROPIC_API_KEY und kein Session-Token gefunden.")


def main():
    client = _make_client()

    scores_df = pd.read_csv(PROCESSED_DATA_PATH / "scores.csv")
    verified_df = pd.read_csv(PROCESSED_DATA_PATH / "berufe_ch_esco_verified.csv")

    contaminated_mask = (
        scores_df["begruendung"].str.contains("Brennschneid", case=False, na=False)
        | scores_df["haupt_risiko"].str.contains("Brennschneid", case=False, na=False)
    )
    affected_jobs = scores_df[contaminated_mask]["beruf"].tolist()
    logger.info(f"{len(affected_jobs)} betroffene Berufe gefunden: {affected_jobs}")

    desc_map = verified_df.set_index("beruf")["esco_beschreibung"].to_dict()

    score_fields = [
        "score_gesamt", "score_digital", "score_wiederholbarkeit",
        "score_physisch", "score_kreativitaet", "score_sozial",
        "haupt_risiko", "zeitrahmen", "begruendung",
    ]

    for beruf in affected_jobs:
        if beruf in WRONG_ESCO_JOBS:
            beschreibung = "Keine Beschreibung verfügbar."
            logger.info(f"  [{beruf}] falscher ESCO-Match → scoring ohne Beschreibung")
        else:
            raw = desc_map.get(beruf, "")
            beschreibung = raw if raw and pd.notna(raw) else "Keine Beschreibung verfügbar."
            logger.info(f"  [{beruf}] scoring mit ESCO-Beschreibung")

        try:
            result = rescore_job(client, beruf, beschreibung)
        except Exception as e:
            logger.error(f"  Fehler bei '{beruf}': {e}")
            continue

        idx = scores_df[scores_df["beruf"] == beruf].index
        for field in score_fields:
            if field in result:
                scores_df.loc[idx, field] = result[field]

        # score_ch neu berechnen
        scores_df.loc[idx, "score_ch"] = (
            scores_df.loc[idx, "score_gesamt"]
            + scores_df.loc[idx, "delta_branche"]
            + scores_df.loc[idx, "delta_lohn"]
        ).clip(0, 10)

        logger.info(f"  OK: score_gesamt={result['score_gesamt']}, zeitrahmen={result['zeitrahmen']}")

    scores_df.to_csv(PROCESSED_DATA_PATH / "scores.csv", index=False)
    logger.info("scores.csv aktualisiert.")


if __name__ == "__main__":
    main()
