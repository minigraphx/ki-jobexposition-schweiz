"""
KI-Expositions-Scoring via Claude Batch API (Karpathy-Methode, adaptiert für CH).

Verwendet die Message Batches API für asynchrone Verarbeitung aller Berufe in einem Aufruf.
Günstiger als synchrone Calls und umgeht Mindestguthaben-Beschränkungen.

Für jeden Beruf wird ein Score 0–10 generiert basierend auf:
- Digitaler Output (25%)
- Wiederholbarkeit (25%)
- Physische Präsenz (20%, negativ)
- Kreativität (15%, negativ)
- Soziale Interaktion (15%, negativ)
"""

import json
import logging
import os
import time
from pathlib import Path

import anthropic
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROCESSED_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "processed"
BATCH_ID_FILE = PROCESSED_DATA_PATH / ".batch_id"

MODEL = "claude-sonnet-4-6"
POLL_INTERVAL_SECONDS = 30

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


def build_batch_requests(jobs_df: pd.DataFrame) -> list[dict]:
    """Batch-Requests für alle Berufe erstellen."""
    requests = []
    for idx, row in jobs_df.iterrows():
        prompt = SCORING_PROMPT.format(
            beruf=row["beruf"],
            beschreibung=row.get("esco_beschreibung", "") or "Keine Beschreibung verfügbar.",
        )
        requests.append({
            "custom_id": str(idx),
            "params": {
                "model": MODEL,
                "max_tokens": 512,
                "messages": [{"role": "user", "content": prompt}],
            },
        })
    return requests


def submit_batch(client: anthropic.Anthropic, jobs_df: pd.DataFrame) -> str:
    """Batch einreichen und Batch-ID zurückgeben."""
    requests = build_batch_requests(jobs_df)
    logger.info(f"Sende Batch mit {len(requests)} Requests...")
    batch = client.beta.messages.batches.create(requests=requests)
    batch_id = batch.id
    BATCH_ID_FILE.write_text(batch_id)
    logger.info(f"Batch eingereicht: {batch_id}")
    logger.info(f"Batch-ID gespeichert in {BATCH_ID_FILE} (für Resume bei Absturz)")
    return batch_id


def wait_for_batch(client: anthropic.Anthropic, batch_id: str) -> None:
    """Warten bis Batch abgeschlossen ist."""
    logger.info(f"Warte auf Batch {batch_id} (polling alle {POLL_INTERVAL_SECONDS}s)...")
    while True:
        batch = client.beta.messages.batches.retrieve(batch_id)
        counts = batch.request_counts
        logger.info(
            f"Status: {batch.processing_status} | "
            f"Fertig: {counts.succeeded} | "
            f"Fehler: {counts.errored} | "
            f"Ausstehend: {counts.processing}"
        )
        if batch.processing_status == "ended":
            break
        time.sleep(POLL_INTERVAL_SECONDS)


def parse_result(raw: str) -> dict:
    """JSON aus API-Antwort extrahieren."""
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()
    return json.loads(raw)


def collect_results(client: anthropic.Anthropic, batch_id: str, jobs_df: pd.DataFrame) -> pd.DataFrame:
    """Batch-Ergebnisse abrufen und mit jobs_df zusammenführen."""
    scores = {}
    failed = []

    for result in client.beta.messages.batches.results(batch_id):
        idx = int(result.custom_id)
        beruf = jobs_df.loc[idx, "beruf"]

        if result.result.type == "succeeded":
            try:
                data = parse_result(result.result.message.content[0].text)
                data["beruf"] = beruf
                scores[idx] = data
            except json.JSONDecodeError as e:
                logger.warning(f"Ungültiges JSON für '{beruf}': {e}")
                failed.append(beruf)
        else:
            logger.warning(f"Fehler für '{beruf}': {result.result.type}")
            failed.append(beruf)

    if failed:
        logger.warning(f"{len(failed)} Berufe fehlgeschlagen: {', '.join(failed)}")

    scores_df = pd.DataFrame(list(scores.values()))
    merged = jobs_df.merge(scores_df, on="beruf", how="left")
    logger.info(f"{len(scores)} von {len(jobs_df)} Berufen erfolgreich gescort.")
    return merged


def score_all_jobs(jobs_df: pd.DataFrame, batch_id: str | None = None) -> pd.DataFrame:
    """
    Alle Berufe via Batch API scoren.

    Wenn batch_id angegeben, wird ein laufender Batch weiterverfolgt (Resume).
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    if batch_id is None:
        # Prüfen ob noch eine offene Batch-ID existiert
        if BATCH_ID_FILE.exists():
            saved_id = BATCH_ID_FILE.read_text().strip()
            logger.info(f"Gefundene gespeicherte Batch-ID: {saved_id}")
            logger.info("Verwende bestehenden Batch. Zum Neustart: .batch_id Datei löschen.")
            batch_id = saved_id
        else:
            batch_id = submit_batch(client, jobs_df)

    wait_for_batch(client, batch_id)
    merged = collect_results(client, batch_id, jobs_df)

    # Batch-ID löschen nach erfolgreichem Abschluss
    if BATCH_ID_FILE.exists():
        BATCH_ID_FILE.unlink()

    return merged


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from ch_adjustments import apply_ch_adjustments

    jobs_df = pd.read_csv(PROCESSED_DATA_PATH / "berufe_ch_esco.csv")
    logger.info(f"Starte Batch-Scoring für {len(jobs_df)} Berufe...")

    merged = score_all_jobs(jobs_df)

    if "score_gesamt" not in merged.columns:
        logger.error("Scoring fehlgeschlagen — scores.csv nicht aktualisiert.")
        raise SystemExit(1)

    merged = apply_ch_adjustments(merged)
    merged.to_csv(PROCESSED_DATA_PATH / "scores.csv", index=False)
    logger.info(f"scores.csv gespeichert.")

    print(f"\nTop 10 exponierte Berufe:")
    print(merged.nlargest(10, "score_ch")[["beruf", "score_ch", "zeitrahmen"]].to_string())
    print(f"\nTop 10 sicherste Berufe:")
    print(merged.nsmallest(10, "score_ch")[["beruf", "score_ch", "zeitrahmen"]].to_string())
