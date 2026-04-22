"""
KI-Expositions-Scoring via Claude API (Karpathy-Methode, adaptiert für CH).

Synchrone Verarbeitung mit Hash-basiertem Delta:
  - Nur Berufe mit geänderter ESCO-Beschreibung werden neu gescort
  - --force ohne Argument: alle Berufe neu scoren
  - --force "Buchhalter/in": Beruf nach Name selektiv neu scoren
  - --force 2411: alle Berufe mit diesem ISCO-Code-Präfix neu scoren
  - Mehrere Argumente kombinierbar: --force "Arzt/Ärztin" 2411

Scoring-Kriterien je 0–10:
  - Digitaler Output (25%)
  - Wiederholbarkeit (25%)
  - Physische Präsenz (20%, negativ)
  - Kreativität (15%, negativ)
  - Soziale Interaktion (15%, negativ)
"""

import argparse
import hashlib
import json
import logging
import os
from pathlib import Path

import anthropic
import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROCESSED_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "processed"
SCORES_PATH = PROCESSED_DATA_PATH / "scores.csv"

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


def compute_hash(beruf: str, beschreibung: str) -> str:
    """SHA-256-Hash von Beruf + Beschreibung (erste 12 Zeichen)."""
    return hashlib.sha256(f"{beruf}||{beschreibung}".encode()).hexdigest()[:12]


def get_beschreibung(row: pd.Series) -> str:
    """ESCO-Beschreibung aus Row lesen, mit Fallback bei fehlendem Wert."""
    raw = row.get("esco_beschreibung", "")
    return raw if (raw and pd.notna(raw)) else "Keine Beschreibung verfügbar."


def parse_result(raw: str) -> dict:
    """JSON aus API-Antwort extrahieren (mit Markdown-Code-Block-Fallback)."""
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()
    return json.loads(raw)


def find_jobs_to_score(
    jobs_df: pd.DataFrame,
    scores_path: Path,
    force: list[str] | None = None,
) -> pd.DataFrame:
    """
    Jobs ermitteln die neu gescort werden müssen.

    Args:
        jobs_df:     Alle verfügbaren Berufe (mit esco_beschreibung).
        scores_path: Pfad zur bestehenden scores.csv.
        force:       None  → nur neue/geänderte Berufe (Hash-Delta)
                     []    → alle Berufe
                     [...] → Berufe nach Name (exact, case-insensitive) oder ISCO-Präfix
    """
    jobs_df = jobs_df.copy()
    jobs_df["_hash"] = jobs_df.apply(
        lambda r: compute_hash(r["beruf"], get_beschreibung(r)), axis=1
    )

    # force=[] → alle neu scoren
    if force is not None and len(force) == 0:
        logger.info(f"--force: alle {len(jobs_df)} Berufe werden neu gescort.")
        return jobs_df

    # force=[term, ...] → selektiv nach Name oder ISCO-Präfix
    if force:
        mask = pd.Series(False, index=jobs_df.index)
        for term in force:
            if term.isdigit():
                mask |= jobs_df["isco_code"].astype(str).str.startswith(term)
            else:
                mask |= jobs_df["beruf"].str.lower() == term.lower()
        selected = jobs_df[mask]
        if selected.empty:
            logger.warning(f"--force: keine Übereinstimmung für {force}.")
        else:
            logger.info(
                f"--force: {len(selected)} Beruf(e) selektiv neu gescort: "
                f"{selected['beruf'].tolist()}"
            )
        return selected

    # Kein force → Hash-Delta
    if not scores_path.exists():
        logger.info("Keine scores.csv gefunden — alle Berufe werden gescort.")
        return jobs_df

    existing = pd.read_csv(scores_path)
    if "beschreibung_hash" not in existing.columns:
        logger.info("Kein Hash in scores.csv vorhanden — alle Berufe werden gescort.")
        return jobs_df

    existing_hashes = dict(zip(existing["beruf"], existing["beschreibung_hash"]))
    changed = jobs_df[
        jobs_df.apply(
            lambda r: existing_hashes.get(r["beruf"]) != r["_hash"], axis=1
        )
    ]

    known = set(existing["beruf"])
    n_new = (~changed["beruf"].isin(known)).sum()
    n_changed = len(changed) - n_new
    logger.info(
        f"Delta: {n_new} neue, {n_changed} geänderte Berufe → {len(changed)} total."
    )
    return changed


def score_single_job(client: anthropic.Anthropic, row: pd.Series) -> dict:
    """Einen Beruf synchron via Claude API scoren."""
    prompt = SCORING_PROMPT.format(
        beruf=row["beruf"],
        beschreibung=get_beschreibung(row),
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    return parse_result(response.content[0].text)


def score_changed_jobs(
    jobs_df: pd.DataFrame,
    scores_path: Path = SCORES_PATH,
    force: list[str] | None = None,
) -> pd.DataFrame:
    """
    Nur geänderte/neue Berufe scoren und Ergebnis mit bestehender scores.csv zusammenführen.

    Returns:
        Vollständiger DataFrame mit allen Berufen und aktualisierten Scores.
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    to_score = find_jobs_to_score(jobs_df, scores_path, force)

    if to_score.empty:
        logger.info("Keine Änderungen erkannt — scores.csv bleibt unverändert.")
        return pd.read_csv(scores_path) if scores_path.exists() else jobs_df.copy()

    new_scores: list[dict] = []
    failed: list[str] = []

    for _, row in tqdm(to_score.iterrows(), total=len(to_score), desc="Scoring"):
        try:
            data = score_single_job(client, row)
            data["beruf"] = row["beruf"]
            data["beschreibung_hash"] = row["_hash"]
            new_scores.append(data)
        except Exception as e:
            logger.warning(f"Fehler bei '{row['beruf']}': {e}")
            failed.append(row["beruf"])

    if failed:
        logger.warning(f"{len(failed)} Berufe fehlgeschlagen: {', '.join(failed)}")

    if not new_scores:
        logger.error("Kein einziger Beruf erfolgreich gescort.")
        return pd.read_csv(scores_path) if scores_path.exists() else jobs_df.copy()

    scores_df = pd.DataFrame(new_scores)

    # Basis-Spalten der neu gescorten Berufe mit den neuen Scores verbinden
    scored_rows = (
        to_score[to_score["beruf"].isin(scores_df["beruf"])]
        .merge(scores_df, on="beruf")
        .drop(columns=["_hash"], errors="ignore")
    )

    if scores_path.exists():
        existing = pd.read_csv(scores_path)
        # Alte Zeilen der neu gescorten Berufe ersetzen
        kept = existing[~existing["beruf"].isin(scored_rows["beruf"])]
        result = pd.concat([kept, scored_rows], ignore_index=True)
    else:
        result = scored_rows

    logger.info(f"✓ {len(new_scores)} Berufe erfolgreich gescort.")
    return result


if __name__ == "__main__":  # pragma: no cover
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from ch_adjustments import apply_ch_adjustments

    parser = argparse.ArgumentParser(
        description="KI-Expositions-Scoring für Schweizer Berufe (nur Delta)."
    )
    parser.add_argument(
        "--force",
        nargs="*",
        metavar="BERUF_ODER_ISCO",
        help=(
            "Ohne Argumente: alle Berufe neu scoren. "
            "Mit Name(n) oder ISCO-Code(s): nur diese Berufe."
        ),
    )
    args = parser.parse_args()

    jobs_df = pd.read_csv(PROCESSED_DATA_PATH / "berufe_ch_esco_verified.csv")
    logger.info(f"{len(jobs_df)} Berufe geladen.")

    result = score_changed_jobs(jobs_df, scores_path=SCORES_PATH, force=args.force)

    if "score_gesamt" not in result.columns:
        logger.error("Scoring fehlgeschlagen — scores.csv nicht aktualisiert.")
        raise SystemExit(1)

    result = apply_ch_adjustments(result)
    result.to_csv(SCORES_PATH, index=False)
    logger.info(f"scores.csv gespeichert ({len(result)} Berufe).")

    print("\nTop 10 exponierte Berufe:")
    print(result.nlargest(10, "score_ch")[["beruf", "score_ch", "zeitrahmen"]].to_string())
    print("\nTop 10 sicherste Berufe:")
    print(result.nsmallest(10, "score_ch")[["beruf", "score_ch", "zeitrahmen"]].to_string())
