"""Aufgabenbasierte KI-Expositionsbewertung über die API (Rubrik v2.2) — lokal mit eigenen Keys.

Je Eintrag in scores.csv wird der Input gebaut (task_inputs.py) und von einem Sprachmodell nach
der Rubrik bewertet. Die rohe Bewertung landet mit Metadaten unter
``data/processed/bewertungen/<provider>/run<N>/<isco>_<slug>.json``.

Provider
    claude   Anthropic Python SDK, Messages API (beta-Namespace wegen Refusal-Fallback),
             adaptive thinking, output_config.effort (Standard "high"), Structured Outputs
             (output_config.format, json_schema), Streaming + get_final_message, Prompt-Caching
             des System-Prompts, server-seitiger Refusal-Fallback (fallbacks="default").
    gemini   Google Gen AI SDK (google-genai), models.generate_content mit
             response_mime_type="application/json" + response_json_schema, thinking_level
             (Standard "high"), keine Sampling-Parameter (werden vom Modell ignoriert),
             automatic function calling aus (keine Tools).
    claude-cli  Claude Code im Print-Modus (``claude -p``) mit dem eigenen Claude-Abo statt API-Key:
             gleicher System-Prompt (--system-prompt-file), gleiches Schema (--json-schema),
             --effort, keine Tools, kein CLAUDE.md/Auto-Memory, leeres Arbeitsverzeichnis;
             API-Keys werden aus der Umgebung des Unterprozesses entfernt (sonst rechnet Claude Code
             über die API ab). Kein server-seitiger Fallback, kein Batch, kein --count-tokens;
             der Korrekturversuch wird als ein Prompt mit vorheriger Antwort gestellt.
             Ergebnisse unter bewertungen/claude-cli/ (getrennt von den API-Läufen).

Ablauf je Lauf: Reihenfolge mit festem Seed gemischt, nur fehlende/veraltete Bewertungen
(Input-Hash, Modell) werden angefragt (``--force`` = alle). Jede Antwort wird gegen das Schema
und die Plausibilitätsregeln validiert; bei Fehler ein Korrekturversuch mit Fehlermeldung,
sonst wird sie als fehlgeschlagen protokolliert. Nach Lauf 1 und 2 folgt automatisch Lauf 3
für Einträge mit |Δ ζ-Score| > DRITTER_LAUF_SCHWELLE.

Batch-Modus (beide Provider, 50 % günstiger, Ergebnis bis 24 h; Logik in task_batch.py)
    --batch submit    Anfragen einreichen (Delta wie synchron), Zustand unter <provider>/batches/
    --batch status    offene Batches mit Status/Zählern
    --batch collect   fertige Ergebnisse holen, validieren und wie synchron speichern (idempotent)
    --batch followup  Wiederholungen/Korrekturen + dritte Läufe (|Δζ| > Schwelle) als neuen Batch;
                      Refusals mit --refusal-sync synchron (claude: mit Fallback)

Beispiele
    python src/scoring/task_scorer.py --provider claude --only 2512 --runs 1       # synchrone Probe
    python src/scoring/task_scorer.py --provider claude --pilot --runs 2 --dry-run
    python src/scoring/task_scorer.py --provider claude --pilot --runs 2
    python src/scoring/task_scorer.py --provider claude --runs 2 --batch submit --dry-run
    python src/scoring/task_scorer.py --provider claude --runs 2 --batch submit   # alle Einträge
    python src/scoring/task_scorer.py --provider claude --batch status
    python src/scoring/task_scorer.py --provider claude --batch collect
    python src/scoring/task_scorer.py --provider claude --batch followup --refusal-sync
    python src/scoring/task_scorer.py --provider claude --only 2411 2512 --force
    python src/scoring/task_scorer.py --provider claude-cli --pilot --runs 2       # über das Abo

Keys aus .env: ANTHROPIC_API_KEY (claude); GEMINI_API_KEY oder GOOGLE_API_KEY (gemini;
GOOGLE_API_KEY hat Vorrang, wenn beide gesetzt sind). claude-cli braucht keinen Key, sondern ein
in Claude Code angemeldetes Abo (``claude`` starten, /login).
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib
import json
import logging
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import task_inputs as ti  # noqa: E402
import task_rubrik as tr  # noqa: E402

log = logging.getLogger("task_scorer")

# --------------------------------------------------------------------------- Konfiguration

PROVIDER = ("claude", "claude-cli", "gemini")
MODELL = {"claude": "claude-opus-5-5", "claude-cli": "claude-opus-5-5", "gemini": "gemini-4-argon"}

CLAUDE_EFFORT = "high"                      # output_config.effort; Modell-Default wäre "medium"
CLAUDE_EFFORTS = ("low", "medium", "high", "xhigh", "max")
CLAUDE_MAX_TOKENS = 64000                   # Thinking + Antwort; Streaming nötig
CLAUDE_FALLBACK_BETA = "server-side-fallback-2026-07-01"   # gehört zu fallbacks="default"
CLAUDE_TIMEOUT_S = 900.0

CLAUDE_CLI = "claude"                       # Claude Code (muss im PATH liegen)
CLAUDE_CLI_TIMEOUT_S = 1800.0
# aus der Umgebung von `claude -p` entfernt: mit API-Key/-Token oder Cloud-Provider rechnet Claude Code
# nicht über das Abo ab (ANTHROPIC_API_KEY kommt sonst aus .env)
CLAUDE_CLI_ENV_ENTFERNEN = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN",
                            "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY")
# nur Rubrik + Input im Kontext: kein CLAUDE.md, keine Auto-Memory
CLAUDE_CLI_ENV_SETZEN = {"CLAUDE_CODE_DISABLE_CLAUDE_MDS": "1", "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"}

GEMINI_THINKING = "high"                    # thinking_level; Modell-Default wäre "medium"
GEMINI_THINKING_LEVELS = ("low", "medium", "high")
GEMINI_MAX_OUTPUT_TOKENS = 65536            # Standard-Obergrenze synchron (Thinking + Antwort)
GEMINI_BATCH_MAX_OUTPUT_TOKENS = 32768      # Batch-API: «Decoding continuation is not supported for batch
                                            # requests, so max_output_tokens cannot exceed 32768» (HTTP 400)
GEMINI_TIMEOUT_MS = 15 * 60 * 1000          # Doku: Client-Timeout mindestens 15 Minuten

DRITTER_LAUF_SCHWELLE = 1.0     # |Δ ζ-Score| (0–10) zwischen Lauf 1 und 2, ab dem Lauf 3 folgt
SEED = 20261013                 # Reihenfolge je Lauf: random.Random(SEED + lauf)
MAX_PARALLEL = 2
VALIDIERUNGS_KORREKTUREN = 1    # Korrekturversuche nach ungültiger Antwort
API_VERSUCHE = 6                # eigene Wiederholungen bei 429/5xx/Netz (zusätzlich zu SDK-Retries)
BACKOFF_START_S = 5.0
BACKOFF_MAX_S = 120.0

# Preise USD je 1 Mio. Tokens (Stand 13.10.2026; Quellen siehe docs/neubewertung_lokal.md)
PREISE = {
    "claude": {"input": 4.00, "output": 20.00, "cache_write": 5.00, "cache_write_1h": 8.00, "cache_read": 0.20},
    "gemini": {"input": 2.00, "output": 10.00, "cache_read": 0.10},          # Einführungspreis bis 30.11.2026
    "gemini_ab_2026_12": {"input": 4.00, "output": 20.00, "cache_read": 0.20},
}
BATCH_RABATT = 0.5              # beide Batch-APIs: 50 % auf alle Tokens (Claude: auch Cache-Lesen/-Schreiben)
BATCH_CACHE_TREFFER = (0.98, 0.30)   # Claude-Doku: Cache-Treffer im Batch «best effort», typisch 30–98 %
# Schätzung für den Dry-Run ohne Messwerte. Kalibriert an der ersten Claude-Probe (2512, effort high,
# 13.10.2026): System-Prompt 67 034 Zeichen → 36 937 Tokens (1.8 Zeichen/Token), Ausgabe 4 847 Tokens
# inkl. Thinking. Liegen gültige Ergebnisdateien vor, nimmt der Dry-Run deren Mittelwerte.
ZEICHEN_JE_TOKEN = 1.8
AUSGABE_TOKENS = {"low": 3500, "medium": 4500, "high": 5500, "xhigh": 7500, "max": 10000}


class FatalerFehler(RuntimeError):
    """Abbruch des ganzen Laufs (fehlender/ungültiger Key, unbekanntes Modell)."""


class AnfrageFehler(RuntimeError):
    """Diese Anfrage ist gescheitert (kein Wiederholen sinnvoll)."""


class AntwortFehler(RuntimeError):
    """Antwort unbrauchbar (Refusal, abgeschnitten, blockiert, kein JSON)."""

    def __init__(self, msg: str, roh: dict | None = None):
        super().__init__(msg)
        self.roh = roh or {}


# --------------------------------------------------------------------------- Hilfen

def _jetzt() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _als_dict(obj: Any) -> Any:
    """SDK-Objekte (pydantic) → dict, rekursiv tolerant."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {k: _als_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_als_dict(v) for v in obj]
    for meth in ("model_dump", "to_dict"):
        f = getattr(obj, meth, None)
        if callable(f):
            try:
                return _als_dict(f(exclude_none=True, mode="json") if meth == "model_dump" else f())
            except TypeError:
                return _als_dict(f())
    if hasattr(obj, "__dict__"):
        return {k: _als_dict(v) for k, v in vars(obj).items() if not k.startswith("_")}
    return str(obj)


def _schreibe_json(pfad: Path, daten: dict) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    tmp = pfad.with_suffix(pfad.suffix + ".tmp")
    tmp.write_text(json.dumps(daten, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, pfad)


def parse_json_text(text: str) -> Any:
    """JSON aus der Antwort; toleriert Code-Fences (sollten mit Structured Outputs nicht vorkommen)."""
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else ""
        t = t.rsplit("```", 1)[0]
    return json.loads(t)


class Drossel:
    """Gemeinsame Pause für alle Worker nach einem Rate-Limit (429)."""

    def __init__(self, schlafen: Callable[[float], None] = time.sleep):
        self._bis = 0.0
        self._lock = threading.Lock()
        self._schlafen = schlafen

    def pausiere(self, sekunden: float) -> None:
        with self._lock:
            self._bis = max(self._bis, time.monotonic() + sekunden)

    def warte(self) -> None:
        rest = self._bis - time.monotonic()
        if rest > 0:
            self._schlafen(rest)


@dataclass
class Antwort:
    """Normalisierte Modellantwort (provider-unabhängig)."""
    text: str
    model_served: str | None
    stop_reason: str | None
    usage: dict
    request_id: str | None = None
    fallback: dict | None = None
    fortsetzung: Any = None        # provider-spezifisch: Assistant-Turn für den Korrekturversuch


@dataclass
class Ergebnis:
    status: str                     # "ok" | "fehlgeschlagen"
    bewertung: dict | None
    meta: dict
    rohantwort: str | None = None


# --------------------------------------------------------------------------- Provider: Claude

class ClaudeBewerter:
    provider = "claude"

    def __init__(self, model: str = MODELL["claude"], effort: str = CLAUDE_EFFORT,
                 max_tokens: int = CLAUDE_MAX_TOKENS, client: Any = None, fallback: bool = True):
        if effort not in CLAUDE_EFFORTS:
            raise ValueError(f"effort muss einer von {CLAUDE_EFFORTS} sein")
        self.model, self.effort, self.max_tokens, self.fallback = model, effort, max_tokens, fallback
        self._client = client
        self._client_lock = threading.Lock()
        self.schema = tr.schema_fuer_claude()

    @property
    def client(self):
        # Lock: bei --max-parallel > 1 dürfen nicht zwei Threads je einen Client anlegen (der
        # überschriebene würde vom GC geschlossen, während er noch eine Anfrage sendet)
        with self._client_lock:
            if self._client is None:
                import anthropic
                self._client = anthropic.Anthropic(timeout=CLAUDE_TIMEOUT_S, max_retries=2)
            return self._client

    def einstellungen(self) -> dict:
        return {"effort": self.effort, "thinking": "adaptive", "max_tokens": self.max_tokens,
                "fallbacks": "default" if self.fallback else None, "structured_output": "output_config.format"}

    def _system(self) -> list[dict]:
        return [{"type": "text", "text": tr.system_prompt(), "cache_control": {"type": "ephemeral"}}]

    def _anfrage(self, messages: list[dict]) -> dict:
        kw: dict = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": self._system(),
            "messages": messages,
            "thinking": {"type": "adaptive"},
            "output_config": {"effort": self.effort,
                              "format": {"type": "json_schema", "schema": self.schema}},
        }
        if self.fallback:
            kw["betas"] = [CLAUDE_FALLBACK_BETA]
            kw["fallbacks"] = "default"
        return kw

    def start(self, input_rec: dict) -> list[dict]:
        return [{"role": "user", "content": tr.user_prompt(input_rec)}]

    def weiter(self, verlauf: list[dict], antwort: Antwort, fehler: list[str]) -> list[dict]:
        # nur den Text des Assistant-Turns zurückgeben (append-only, keine Thinking-Blöcke editiert)
        return verlauf + [{"role": "assistant", "content": [{"type": "text", "text": antwort.text}]},
                          {"role": "user", "content": tr.korrektur_prompt(fehler)}]

    def frage(self, verlauf: list[dict]) -> Antwort:
        import anthropic
        try:
            with self.client.beta.messages.stream(**self._anfrage(verlauf)) as stream:
                msg = stream.get_final_message()
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as e:
            raise FatalerFehler(f"Anthropic: Zugriff verweigert ({e.status_code}) — ANTHROPIC_API_KEY prüfen") from e
        except anthropic.NotFoundError as e:
            raise FatalerFehler(f"Anthropic: Modell/Endpunkt nicht gefunden ({self.model})") from e
        except anthropic.BadRequestError as e:
            raise AnfrageFehler(f"Anthropic: ungültige Anfrage (400): {e.message}") from e
        except anthropic.RateLimitError as e:
            raise _Wiederholbar(_retry_after(e), f"Rate-Limit (429): {e.message}", rate_limit=True) from e
        except anthropic.APIStatusError as e:
            if e.status_code >= 500:
                raise _Wiederholbar(None, f"Serverfehler ({e.status_code}): {e.message}") from e
            raise AnfrageFehler(f"Anthropic: Fehler {e.status_code}: {e.message}") from e
        except anthropic.APIConnectionError as e:     # inkl. APITimeoutError
            raise _Wiederholbar(None, f"Verbindungsfehler: {e}") from e
        return self._auswerten(msg)

    def _auswerten(self, msg: Any) -> Antwort:
        usage = _als_dict(getattr(msg, "usage", None)) or {}
        inhalt = list(getattr(msg, "content", None) or [])
        wechsel = [i for i, b in enumerate(inhalt) if getattr(b, "type", None) == "fallback"]
        fallback = None
        if wechsel or any((it or {}).get("type") == "fallback_message" for it in usage.get("iterations") or []):
            fallback = {"wechsel": [{"von": getattr(getattr(inhalt[i], "from_", None), "model", None),
                                     "zu": getattr(getattr(inhalt[i], "to", None), "model", None)} for i in wechsel],
                        "bedient_von": getattr(msg, "model", None)}
        nach = inhalt[wechsel[-1] + 1:] if wechsel else inhalt
        text = "".join(getattr(b, "text", "") for b in nach if getattr(b, "type", None) == "text")
        stop = getattr(msg, "stop_reason", None)
        roh = {"model_served": getattr(msg, "model", None), "stop_reason": stop, "usage": usage, "fallback": fallback}
        if stop == "refusal":
            det = _als_dict(getattr(msg, "stop_details", None)) or {}
            raise AntwortFehler(f"Refusal (Kategorie {det.get('category')}): {det.get('explanation') or ''}".strip(),
                                {**roh, "stop_details": det})
        if stop == "max_tokens":
            raise AntwortFehler(f"Antwort abgeschnitten (max_tokens = {self.max_tokens})", roh)
        if stop not in ("end_turn", "stop_sequence"):
            raise AntwortFehler(f"unerwarteter stop_reason: {stop}", roh)
        return Antwort(text=text, model_served=getattr(msg, "model", None), stop_reason=stop, usage=usage,
                       request_id=getattr(msg, "_request_id", None), fallback=fallback)

    def zaehle_tokens(self, input_rec: dict) -> int:
        """Exakte Input-Tokens via count_tokens (kostenlos, braucht Key + Netz)."""
        kw = self._anfrage(self.start(input_rec))
        for k in ("max_tokens", "fallbacks"):
            kw.pop(k, None)
        kw.pop("betas", None)
        return self.client.beta.messages.count_tokens(**kw).input_tokens


class _Wiederholbar(RuntimeError):
    """Vorübergehender Fehler (429, 5xx, Netz): nach Pause wiederholen."""

    def __init__(self, warte_s: float | None, msg: str, rate_limit: bool = False):
        super().__init__(msg)
        self.warte_s = warte_s
        self.rate_limit = rate_limit


def _retry_after(e: Any) -> float | None:
    try:
        return float(e.response.headers.get("retry-after"))
    except (AttributeError, TypeError, ValueError):
        return None


# --------------------------------------------------------------------------- Provider: Claude über das Abo (CLI)

_ABO_LIMIT = re.compile(r"usage limit|limit reached|hit your limit|session limit|weekly limit|out of extra usage",
                        re.IGNORECASE)
_NICHT_ANGEMELDET = re.compile(r"not logged in|please run /login|/login|invalid api key|authentication|oauth",
                               re.IGNORECASE)
_UEBERLASTET = re.compile(r"overloaded|529|internal server error|api error: 5\d\d|timed? ?out|connection",
                          re.IGNORECASE)


class ClaudeCliBewerter:
    """Claude über ``claude -p`` (Claude Code, eigenes Abo); Prompts, Schema und Validierung wie ClaudeBewerter."""
    provider = "claude-cli"

    def __init__(self, model: str = MODELL["claude-cli"], effort: str = CLAUDE_EFFORT, programm: str = CLAUDE_CLI,
                 ausfuehren: Callable[..., Any] = subprocess.run, timeout_s: float = CLAUDE_CLI_TIMEOUT_S):
        if effort not in CLAUDE_EFFORTS:
            raise ValueError(f"effort muss einer von {CLAUDE_EFFORTS} sein")
        self.model, self.effort, self.programm, self.timeout_s = model, effort, programm, timeout_s
        self._ausfuehren = ausfuehren
        self._lock = threading.Lock()
        self._tmp: tempfile.TemporaryDirectory | None = None
        self._version: str | None = None
        self.schema_text = json.dumps(tr.schema_fuer_claude(), ensure_ascii=False)

    def _verzeichnisse(self) -> tuple[Path, Path]:
        """(System-Prompt-Datei, leeres Arbeitsverzeichnis) — einmal je Bewerter angelegt."""
        with self._lock:
            if self._tmp is None:
                self._tmp = tempfile.TemporaryDirectory(prefix="task_scorer_cli_")
                basis = Path(self._tmp.name)
                (basis / "leer").mkdir()
                (basis / "system.md").write_text(tr.system_prompt(), encoding="utf-8")
            basis = Path(self._tmp.name)
            return basis / "system.md", basis / "leer"

    def umgebung(self) -> dict[str, str]:
        env = {k: v for k, v in os.environ.items() if k not in CLAUDE_CLI_ENV_ENTFERNEN}
        env.update(CLAUDE_CLI_ENV_SETZEN)
        return env

    def version(self) -> str | None:
        if self._version is None:
            try:
                r = self._ausfuehren([self.programm, "--version"], capture_output=True, text=True,
                                     encoding="utf-8", timeout=60, env=self.umgebung())
                self._version = (r.stdout or "").strip() or None
            except (OSError, subprocess.SubprocessError):
                self._version = None
        return self._version

    def einstellungen(self) -> dict:
        return {"effort": self.effort, "thinking": "adaptive (Claude Code)", "structured_output": "--json-schema",
                "zugang": "claude -p (Abo)", "cli_version": self.version(), "tools": "keine", "fallbacks": None}

    def befehl(self, system_datei: Path) -> list[str]:
        return [self.programm, "-p", "--model", self.model, "--effort", self.effort, "--output-format", "json",
                "--tools", "", "--strict-mcp-config", "--no-session-persistence", "--disable-slash-commands",
                "--setting-sources", "", "--exclude-dynamic-system-prompt-sections",
                "--system-prompt-file", str(system_datei), "--json-schema", self.schema_text]

    def start(self, input_rec: dict) -> list[dict]:
        return [{"role": "user", "text": tr.user_prompt(input_rec)}]

    def weiter(self, verlauf: list[dict], antwort: Antwort, fehler: list[str]) -> list[dict]:
        return verlauf + [{"role": "assistant", "text": antwort.text},
                          {"role": "user", "text": tr.korrektur_prompt(fehler)}]

    @staticmethod
    def prompt(verlauf: list[dict]) -> str:
        """Ein Prompt je Aufruf: ``claude -p`` ist einstufig; der Korrekturversuch enthält die vorherige Antwort."""
        if len(verlauf) == 1:
            return verlauf[0]["text"]
        teile = [verlauf[0]["text"]]
        for t in verlauf[1:]:
            kopf = "Deine bisherige Antwort (JSON):" if t["role"] == "assistant" else "Rückmeldung zur Antwort:"
            teile.append(f"---\n{kopf}\n{t['text']}")
        return "\n\n".join(teile)

    def frage(self, verlauf: list[dict]) -> Antwort:
        system_datei, arbeitsdir = self._verzeichnisse()
        try:
            r = self._ausfuehren(self.befehl(system_datei), input=self.prompt(verlauf), capture_output=True,
                                 text=True, encoding="utf-8", cwd=str(arbeitsdir), env=self.umgebung(),
                                 timeout=self.timeout_s)
        except FileNotFoundError as e:
            raise FatalerFehler(f"Claude Code nicht gefunden («{self.programm}») — installieren und anmelden") from e
        except subprocess.TimeoutExpired as e:
            raise _Wiederholbar(None, f"claude -p: Zeitüberschreitung nach {self.timeout_s:.0f} s") from e
        try:
            d = json.loads(r.stdout or "")
        except json.JSONDecodeError:
            d = None
        if not isinstance(d, dict):
            text = ((r.stderr or "") + " " + (r.stdout or "")).strip()[:500]
            self._fehler(text, None)
            raise AnfrageFehler(f"claude -p: keine JSON-Ausgabe (Exit-Code {r.returncode}): {text}")
        if d.get("is_error") or d.get("subtype") != "success":
            text = str(d.get("result") or d.get("subtype") or "")[:500]
            self._fehler(text, d.get("api_error_status"))
            raise AntwortFehler(f"claude -p: {d.get('subtype')}: {text}", self._roh(d))
        return self._auswerten(d)

    def _fehler(self, text: str, status: Any) -> None:
        """Abbruch- und Wiederholungsfälle; kehrt zurück, wenn der Fehler nur diesen Eintrag betrifft."""
        if _ABO_LIMIT.search(text):
            raise FatalerFehler(f"Abo-Nutzungslimit erreicht ({text}) — später erneut starten; "
                                "fertige Einträge werden übersprungen")
        if status in (401, 403) or _NICHT_ANGEMELDET.search(text):
            raise FatalerFehler(f"Claude Code nicht angemeldet ({text}) — `claude` starten und /login "
                                "mit dem Abo-Konto ausführen")
        if status == 429 or (isinstance(status, int) and status >= 500) or _UEBERLASTET.search(text):
            raise _Wiederholbar(None, f"claude -p: vorübergehender Fehler ({status}): {text}")

    @staticmethod
    def _modell(d: dict) -> str | None:
        mu = d.get("modelUsage") or {}
        if not mu:
            return None
        return max(mu, key=lambda k: (mu[k] or {}).get("outputTokens", 0))

    def _roh(self, d: dict) -> dict:
        usage = {k: v for k, v in (d.get("usage") or {}).items() if k != "iterations"}
        if isinstance(d.get("total_cost_usd"), (int, float)):
            usage["api_aequivalent_usd"] = d["total_cost_usd"]     # Listenpreis-Äquivalent, nicht abgerechnet
        return {"model_served": self._modell(d), "stop_reason": d.get("stop_reason"), "usage": usage,
                "fallback": None}

    def _auswerten(self, d: dict) -> Antwort:
        roh = self._roh(d)
        if roh["stop_reason"] == "refusal":
            raise AntwortFehler("Refusal (claude -p)", roh)
        if roh["stop_reason"] == "max_tokens":
            raise AntwortFehler("Antwort abgeschnitten (max_tokens)", roh)
        so = d.get("structured_output")
        text = json.dumps(so, ensure_ascii=False) if so is not None else str(d.get("result") or "")
        return Antwort(text=text, model_served=roh["model_served"], stop_reason=roh["stop_reason"],
                       usage=roh["usage"], request_id=d.get("uuid"))

    def zaehle_tokens(self, input_rec: dict) -> int:
        raise FatalerFehler("--count-tokens gibt es nur mit --provider claude (API); claude-cli schätzt aus "
                            "gemessenen Läufen")


# --------------------------------------------------------------------------- Provider: Gemini

class GeminiBewerter:
    provider = "gemini"

    def __init__(self, model: str = MODELL["gemini"], thinking_level: str = GEMINI_THINKING,
                 max_output_tokens: int = GEMINI_MAX_OUTPUT_TOKENS, client: Any = None):
        if thinking_level not in GEMINI_THINKING_LEVELS:
            raise ValueError(f"thinking_level muss einer von {GEMINI_THINKING_LEVELS} sein")
        self.model, self.thinking_level, self.max_output_tokens = model, thinking_level, max_output_tokens
        self._client = client
        self._client_lock = threading.Lock()
        self.schema = tr.schema_fuer_gemini()

    @property
    def client(self):
        # Lock: genai.Client schliesst seinen HTTP-Client in __del__; legen zwei Threads gleichzeitig
        # einen Client an, wird der überschriebene geschlossen, während client.models ihn noch nutzt
        # («Cannot send a request, as the client has been closed»)
        with self._client_lock:
            if self._client is None:
                from google import genai
                from google.genai import types
                self._client = genai.Client(http_options=types.HttpOptions(
                    timeout=GEMINI_TIMEOUT_MS, retry_options=types.HttpRetryOptions(attempts=3)))
            return self._client

    def _verwerfe_client(self, alt: Any) -> None:
        """Geschlossenen Client verwerfen; der nächste Zugriff legt einen neuen an."""
        with self._client_lock:
            if self._client is alt:
                self._client = None

    def einstellungen(self) -> dict:
        return {"thinking_level": self.thinking_level, "max_output_tokens": self.max_output_tokens,
                "temperature": None, "structured_output": "response_mime_type + response_json_schema"}

    def _config(self, max_output_tokens: int | None = None):
        from google.genai import types
        return types.GenerateContentConfig(
            system_instruction=tr.system_prompt(),
            response_mime_type="application/json",
            response_json_schema=self.schema,
            thinking_config=types.ThinkingConfig(thinking_level=self.thinking_level),
            max_output_tokens=max_output_tokens or self.max_output_tokens,
            # keine Tools → automatic function calling (clientseitig im SDK) explizit aus
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

    def start(self, input_rec: dict) -> list:
        from google.genai import types
        return [types.Content(role="user", parts=[types.Part(text=tr.user_prompt(input_rec))])]

    def weiter(self, verlauf: list, antwort: Antwort, fehler: list[str]) -> list:
        from google.genai import types
        modell_turn = antwort.fortsetzung or types.Content(role="model", parts=[types.Part(text=antwort.text)])
        return verlauf + [modell_turn,
                          types.Content(role="user", parts=[types.Part(text=tr.korrektur_prompt(fehler))])]

    def frage(self, verlauf: list) -> Antwort:
        from google.genai import errors
        client = self.client              # lokale Referenz hält den Client während der Anfrage am Leben
        try:
            resp = client.models.generate_content(model=self.model, contents=verlauf, config=self._config())
        except errors.ClientError as e:
            if e.code in (401, 403):
                raise FatalerFehler(f"Gemini: Zugriff verweigert ({e.code}) — GEMINI_API_KEY/GOOGLE_API_KEY "
                                    "und Paid-Tier prüfen") from e
            if e.code == 404:
                raise FatalerFehler(f"Gemini: Modell nicht gefunden ({self.model})") from e
            if e.code == 429:
                raise _Wiederholbar(None, f"Rate-Limit (429): {e.message}", rate_limit=True) from e
            raise AnfrageFehler(f"Gemini: Fehler {e.code}: {e.message}") from e
        except errors.ServerError as e:
            raise _Wiederholbar(None, f"Serverfehler ({e.code}): {e.message}") from e
        except errors.APIError as e:
            raise _Wiederholbar(None, f"API-Fehler ({e.code}): {e.message}") from e
        except _netzfehler() as e:
            raise _Wiederholbar(None, f"Verbindungsfehler: {e}") from e
        except RuntimeError as e:
            if "client has been closed" not in str(e):
                raise
            self._verwerfe_client(client)
            raise _Wiederholbar(None, f"HTTP-Client geschlossen, neuer Client: {e}") from e
        return self._auswerten(resp)

    def _auswerten(self, resp: Any, max_output_tokens: int | None = None) -> Antwort:
        usage = _als_dict(getattr(resp, "usage_metadata", None)) or {}
        served = getattr(resp, "model_version", None)
        pf = getattr(resp, "prompt_feedback", None)
        block = getattr(pf, "block_reason", None) if pf is not None else None
        roh = {"model_served": served, "usage": usage}
        if block:
            raise AntwortFehler(f"Prompt blockiert: {getattr(block, 'name', block)}", roh)
        kand = list(getattr(resp, "candidates", None) or [])
        if not kand:
            raise AntwortFehler("keine Antwort-Kandidaten", roh)
        fr = getattr(kand[0], "finish_reason", None)
        stop = getattr(fr, "name", None) or (str(fr) if fr is not None else None)
        roh["stop_reason"] = stop
        if stop == "MAX_TOKENS":
            grenze = max_output_tokens or self.max_output_tokens
            raise AntwortFehler(f"Antwort abgeschnitten (max_output_tokens = {grenze})", roh)
        if stop not in ("STOP", None):
            raise AntwortFehler(f"Antwort beendet mit finish_reason {stop}", roh)
        text = getattr(resp, "text", None) or ""
        return Antwort(text=text, model_served=served, stop_reason=stop, usage=usage,
                       request_id=getattr(resp, "response_id", None), fortsetzung=getattr(kand[0], "content", None))

    def zaehle_tokens(self, input_rec: dict) -> int:
        # Systemtext + Nachricht als ein Inhalt zählen (count_tokens zählt nur contents verlässlich)
        r = self.client.models.count_tokens(model=self.model,
                                            contents=tr.system_prompt() + "\n\n" + tr.user_prompt(input_rec))
        return r.total_tokens


def _netzfehler() -> tuple:
    """Transportfehler (Timeout, Verbindungsabbruch, Protokollfehler) des Gemini-SDK.

    google-genai sendet synchron über httpx; httpx2 nur, falls installiert und konfiguriert.
    """
    fehler: tuple = (ConnectionError,)
    for modul in ("httpx", "httpx2"):
        try:
            fehler += (importlib.import_module(modul).TransportError,)
        except (ImportError, AttributeError):
            pass
    return fehler


# --------------------------------------------------------------------------- Bewertung eines Eintrags

def _summe_usage(liste: list[dict]) -> dict:
    s: dict = {}
    for u in liste:
        for k, v in (u or {}).items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                s[k] = s.get(k, 0) + v
    return s


def token_zeile(provider: str, usages: list[dict]) -> str:
    """Summenzeile: Input (davon Cache), Output inkl. Thinking und die rohen Zähler des Providers."""
    s = _summe_usage(usages)
    ein = sys_ = aus = 0.0
    for u in usages:
        i, c, o = _usage_kennzahlen(provider, u or {})
        ein, sys_, aus = ein + i, sys_ + c, aus + o
    return (f"Tokens: Input {ein:,.0f} (davon Cache {sys_:,.0f}) · Output {aus:,.0f} (inkl. Thinking) · "
            f"roh {json.dumps(s, ensure_ascii=False)}")


def mit_wiederholung(fn: Callable[[], Antwort], drossel: Drossel, versuche: int = API_VERSUCHE,
                     schlafen: Callable[[float], None] = time.sleep) -> Antwort:
    warte = BACKOFF_START_S
    for n in range(1, versuche + 1):
        drossel.warte()
        try:
            return fn()
        except _Wiederholbar as e:
            if n == versuche:
                raise AnfrageFehler(f"aufgegeben nach {versuche} Versuchen: {e}") from e
            pause = e.warte_s if e.warte_s else min(warte, BACKOFF_MAX_S) * (1 + random.random() * 0.25)
            if e.rate_limit:
                drossel.pausiere(pause)
            log.warning("%s — neuer Versuch in %.0f s (%d/%d)", e, pause, n, versuche)
            schlafen(pause)
            warte *= 2
    raise AssertionError("unerreichbar")  # pragma: no cover


def bewerte(bewerter: Any, eintrag: ti.Eintrag, lauf: int, drossel: Drossel,
            schlafen: Callable[[float], None] = time.sleep) -> Ergebnis:
    """Ein Eintrag, ein Lauf: Anfrage → Validierung → ggf. ein Korrekturversuch."""
    verlauf = bewerter.start(eintrag.input)
    usages, fehler_liste, hinweise, request_ids = [], [], [], []
    antwort: Antwort | None = None
    letzte_roh: str | None = None
    meta_roh: dict = {}
    bewertung = None
    for versuch in range(1 + VALIDIERUNGS_KORREKTUREN):
        try:
            antwort = mit_wiederholung(lambda: bewerter.frage(verlauf), drossel, schlafen=schlafen)
        except AntwortFehler as e:
            fehler_liste.append(str(e))
            meta_roh = e.roh
            usages.append(e.roh.get("usage") or {})
            break
        except AnfrageFehler as e:
            fehler_liste.append(str(e))
            break
        usages.append(antwort.usage)
        request_ids.append(antwort.request_id)
        letzte_roh = antwort.text
        try:
            kandidat = parse_json_text(antwort.text)
            probleme = tr.pruefe_bewertung(kandidat, eintrag.input)
        except json.JSONDecodeError as e:
            kandidat, probleme = None, [f"kein gültiges JSON: {e}"]
        if not probleme:
            bewertung = kandidat
            hinweise = tr.hinweise(kandidat)
            break
        fehler_liste.append(f"Versuch {versuch + 1}: " + "; ".join(probleme[:10]))
        if versuch < VALIDIERUNGS_KORREKTUREN:
            verlauf = bewerter.weiter(verlauf, antwort, probleme)
    ok = bewertung is not None
    meta = {
        "provider": bewerter.provider,
        "model_requested": bewerter.model,
        "model_served": antwort.model_served if antwort else meta_roh.get("model_served"),
        "fallback": antwort.fallback if antwort else meta_roh.get("fallback"),
        "rubrik_version": tr.RUBRIK_VERSION,
        "input_hash": eintrag.input_hash,
        "isco_code": eintrag.isco_code,
        "beruf": eintrag.beruf,
        "lauf": lauf,
        "reihenfolge_seed": SEED + lauf,
        "timestamp": _jetzt(),
        "einstellungen": bewerter.einstellungen(),
        "stop_reason": antwort.stop_reason if antwort else meta_roh.get("stop_reason"),
        "stop_details": meta_roh.get("stop_details"),
        "usage": _summe_usage(usages),
        "usage_je_versuch": usages,
        "request_ids": [r for r in request_ids if r],
        "versuche": len(usages),
        "status": "ok" if ok else "fehlgeschlagen",
        "fehler": fehler_liste,
        "hinweise": hinweise,
    }
    return Ergebnis("ok" if ok else "fehlgeschlagen", bewertung, meta, None if ok else letzte_roh)


# --------------------------------------------------------------------------- Dateien & Delta

def ziel_pfad(basis: Path, provider: str, lauf: int, eintrag: ti.Eintrag) -> Path:
    return basis / provider / f"run{lauf}" / eintrag.datei


def lade_ergebnis(pfad: Path) -> dict | None:
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def ist_aktuell(daten: dict | None, eintrag: ti.Eintrag, model: str) -> bool:
    """Gültige Bewertung mit gleichem Input-Hash, gleicher Rubrik-Version und gleichem Modell."""
    if not daten:
        return False
    m = daten.get("meta") or {}
    return (m.get("status") == "ok" and m.get("input_hash") == eintrag.input_hash
            and m.get("rubrik_version") == tr.RUBRIK_VERSION and m.get("model_requested") == model
            and not tr.pruefe_bewertung(daten.get("bewertung"), eintrag.input))


def speichere(pfad: Path, erg: Ergebnis) -> None:
    daten = {"meta": erg.meta, "bewertung": erg.bewertung}
    if erg.rohantwort is not None:
        daten["rohantwort"] = erg.rohantwort
    _schreibe_json(pfad, daten)


def reihenfolge(eintraege: list[ti.Eintrag], lauf: int) -> list[ti.Eintrag]:
    r = list(eintraege)
    random.Random(SEED + lauf).shuffle(r)
    return r


def zeta_aus_datei(daten: dict | None) -> float | None:
    if not daten or (daten.get("meta") or {}).get("status") != "ok" or not daten.get("bewertung"):
        return None
    return tr.zeta_score(daten["bewertung"])


def braucht_dritten_lauf(d1: dict | None, d2: dict | None, schwelle: float = DRITTER_LAUF_SCHWELLE) -> bool:
    z1, z2 = zeta_aus_datei(d1), zeta_aus_datei(d2)
    return z1 is not None and z2 is not None and abs(z1 - z2) > schwelle


# --------------------------------------------------------------------------- Dry-Run / Kosten

def kosten_usd(provider: str, input_tokens: float, output_tokens: float, cache_write: float = 0.0,
               cache_read: float = 0.0, preisliste: str | None = None) -> float:
    p = PREISE[preisliste or ("claude" if provider == "claude-cli" else provider)]
    return (input_tokens * p["input"] + output_tokens * p["output"]
            + cache_write * p.get("cache_write", p["input"]) + cache_read * p.get("cache_read", p["input"])) / 1e6


def stufe_von(bewerter: Any) -> str:
    return getattr(bewerter, "effort", None) or getattr(bewerter, "thinking_level", None) or "high"


def _usage_kennzahlen(provider: str, u: dict) -> tuple[float, float, float]:
    """(Input gesamt, davon gecachter/zu cachender System-Teil, Output inkl. Thinking) eines Aufrufs."""
    def g(k: str) -> float:
        v = u.get(k)
        return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else 0.0
    if provider in ("claude", "claude-cli"):
        system = g("cache_creation_input_tokens") + g("cache_read_input_tokens")
        return g("input_tokens") + system, system, g("output_tokens")
    return g("prompt_token_count"), g("cached_content_token_count"), g("candidates_token_count") + g("thoughts_token_count")


def gemessene_usage(basis: Path | None, provider: str, stufe: str | None = None) -> dict | None:
    """Mittelwerte aus vorhandenen Ergebnisdateien (je Datei der erste Aufruf; nur gleiche Stufe).

    Grundlage des Dry-Runs, sobald echte Läufe vorliegen; None, wenn nichts Brauchbares da ist.
    """
    if basis is None or not (basis / provider).is_dir():
        return None
    ein, sys_, aus = [], [], []
    for p in sorted((basis / provider).glob("run*/*.json")):
        m = (lade_ergebnis(p) or {}).get("meta") or {}
        st = (m.get("einstellungen") or {})
        if stufe and (st.get("effort") or st.get("thinking_level")) != stufe:
            continue
        liste = m.get("usage_je_versuch") or ([m["usage"]] if m.get("usage") else [])
        if not liste or not isinstance(liste[0], dict):
            continue
        i, s, o = _usage_kennzahlen(provider, liste[0])
        if o <= 0:
            continue
        aus.append(o)
        if i > 0:
            ein.append(i)
        if s > 0:
            sys_.append(s)
    if not aus:
        return None
    return {"n": len(aus), "output": sum(aus) / len(aus), "input": sum(ein) / len(ein) if ein else None,
            "system": max(sys_) if sys_ else None}


def _kosten_claude_batch(tin: float, tout: float, sys_gesamt: float, treffer: float, ttl: str) -> float:
    """Claude-Batch: 50 % auf alles; System-Prompt je Anfrage entweder Cache-Lesen oder Cache-Schreiben."""
    p = PREISE["claude"]
    schreib_preis = p["cache_write_1h"] if ttl == "1h" else p["cache_write"]
    usd = ((tin - sys_gesamt) * p["input"] + tout * p["output"]
           + sys_gesamt * (1 - treffer) * schreib_preis + sys_gesamt * treffer * p["cache_read"]) / 1e6
    return usd * BATCH_RABATT


def schaetze(bewerter: Any, eintraege: list[ti.Eintrag], n_aufrufe: int, n_dritter_max: int,
             zaehlen: bool = False, basis: Path | None = None, cache_ttl: str = "5m") -> dict:
    """Token- und Kostenschätzung ohne Bewertungsaufruf (count_tokens nur mit ``zaehlen``).

    Input: count_tokens (``zaehlen``) > Mittelwert gemessener Aufrufe (``basis``) > grob über Zeichen.
    Output: Mittelwert gemessener Aufrufe > AUSGABE_TOKENS[stufe].
    """
    stufe = stufe_von(bewerter)
    gem = gemessene_usage(basis, bewerter.provider, stufe)
    if gem is None and bewerter.provider == "claude-cli":       # gleiche Prompts → API-Messwerte übertragbar
        gem = gemessene_usage(basis, "claude", stufe)
    sys_tok = (gem or {}).get("system") or len(tr.system_prompt()) / ZEICHEN_JE_TOKEN
    if zaehlen and eintraege:
        tok = [bewerter.zaehle_tokens(e.input) for e in eintraege]
        mittel_in, methode = sum(tok) / len(tok), "count_tokens"
    elif gem and gem.get("input"):
        mittel_in, methode = gem["input"], f"gemessen aus {gem['n']} Aufrufen"
    else:
        tok = [sys_tok + len(tr.user_prompt(e.input)) / ZEICHEN_JE_TOKEN for e in eintraege]
        mittel_in = sum(tok) / len(tok) if tok else 0.0
        methode = f"grob (Zeichen/{ZEICHEN_JE_TOKEN:g})"
    if gem:
        aus, aus_methode = gem["output"], f"gemessen aus {gem['n']} Aufrufen"
    else:
        aus, aus_methode = AUSGABE_TOKENS.get(stufe, AUSGABE_TOKENS["high"]), "Schätzung"
    sys_tok = min(sys_tok, mittel_in)
    res = {"methode": methode, "output_methode": aus_methode, "aufrufe": n_aufrufe,
           "dritter_lauf_max": n_dritter_max, "input_tokens_je_aufruf": round(mittel_in),
           "system_tokens_geschaetzt": round(sys_tok), "output_tokens_je_aufruf": round(aus), "stufe": stufe,
           "cache_ttl_batch": cache_ttl}
    for name, n in (("", n_aufrufe), ("_mit_dritter_max", n_aufrufe + n_dritter_max)):
        tin, tout = mittel_in * n, aus * n
        if bewerter.provider in ("claude", "claude-cli"):
            # System-Prompt gecacht: je Aufruf Cache-Lesen, einmal je parallelem Worker Schreiben
            schreib = min(n, MAX_PARALLEL) * sys_tok
            lesen = max(n - MAX_PARALLEL, 0) * sys_tok
            ungecacht = tin - schreib - lesen
            res[f"usd_ohne_cache{name}"] = kosten_usd("claude", tin, tout)
            res[f"usd_mit_cache{name}"] = kosten_usd("claude", ungecacht, tout, schreib, lesen)
            res[f"usd_batch_ohne_cache{name}"] = kosten_usd("claude", tin, tout) * BATCH_RABATT
            hoch, tief = BATCH_CACHE_TREFFER
            res[f"usd_batch_cache_hoch{name}"] = _kosten_claude_batch(tin, tout, n * sys_tok, hoch, cache_ttl)
            res[f"usd_batch_cache_tief{name}"] = _kosten_claude_batch(tin, tout, n * sys_tok, tief, cache_ttl)
        else:
            lesen = max(n - 1, 0) * sys_tok
            res[f"usd_ohne_cache{name}"] = kosten_usd("gemini", tin, tout)
            res[f"usd_mit_cache{name}"] = kosten_usd("gemini", tin - lesen, tout, 0, lesen)
            res[f"usd_ab_2026_12{name}"] = kosten_usd("gemini", tin, tout, preisliste="gemini_ab_2026_12")
            res[f"usd_batch{name}"] = kosten_usd("gemini", tin, tout) * BATCH_RABATT
            res[f"usd_batch_ab_2026_12{name}"] = res[f"usd_ab_2026_12{name}"] * BATCH_RABATT
        res[f"input_tokens{name}"] = round(tin)
        res[f"output_tokens{name}"] = round(tout)
    return res


def _batch_zeile(provider: str, s: dict, name: str = "") -> str:
    if provider == "claude":
        hoch, tief = BATCH_CACHE_TREFFER
        return (f"~${s['usd_batch_cache_hoch' + name]:.2f} (Cache-Treffer {hoch:.0%}) bis "
                f"~${s['usd_batch_cache_tief' + name]:.2f} (Treffer {tief:.0%}; Cache-TTL {s['cache_ttl_batch']})"
                f" · ~${s['usd_batch_ohne_cache' + name]:.2f} ohne Cache")
    return (f"~${s['usd_batch' + name]:.2f} ohne Cache (Einführungspreis; ab 1.12.2026 "
            f"~${s['usd_batch_ab_2026_12' + name]:.2f})")


def formatiere_schaetzung(provider: str, model: str, s: dict, batch: bool = False) -> str:
    kopf = "Dry-Run Batch" if batch else "Dry-Run"
    z = [f"{kopf} {provider} ({model}, Stufe {s['stufe']}) — keine Bewertungsaufrufe",
         f"  Aufrufe (Lauf 1..N, ohne dritten Lauf): {s['aufrufe']}"
         f"  · dritter Lauf: bis zu {s['dritter_lauf_max']} weitere (nur bei |Δζ| > {DRITTER_LAUF_SCHWELLE:g})",
         f"  Input-Tokens je Aufruf: ~{s['input_tokens_je_aufruf']:,} (davon System/Rubrik ~{s['system_tokens_geschaetzt']:,};"
         f" Methode: {s['methode']})",
         f"  Output-Tokens je Aufruf (inkl. Thinking; {s['output_methode']}): ~{s['output_tokens_je_aufruf']:,}",
         f"  Summe: ~{s['input_tokens']:,} Input- und ~{s['output_tokens']:,} Output-Tokens"]
    synchron = f"~${s['usd_mit_cache']:.2f} mit Cache · ~${s['usd_ohne_cache']:.2f} ohne Cache"
    if provider == "claude-cli":
        z.append("  Kosten: keine API-Kosten — läuft über das Claude-Abo und zählt gegen dessen 5-h- und Wochenlimits")
        z.append(f"  zum Vergleich API-Listenpreis synchron: {synchron}")
        return "\n".join(z)
    if batch:
        z.append(f"  Kosten Batch (−{BATCH_RABATT:.0%}): {_batch_zeile(provider, s)}")
        z.append(f"  zum Vergleich synchron: {synchron}")
    else:
        z.append(f"  Kosten: {synchron}")
        if provider == "gemini":
            z.append(f"          (Einführungspreis bis 30.11.2026; ab 1.12.2026 ohne Cache ~${s['usd_ab_2026_12']:.2f})")
        z.append(f"  im Batch-Modus (−{BATCH_RABATT:.0%}): {_batch_zeile(provider, s)}")
    z.append(f"  inkl. maximalem drittem Lauf: ~${s['usd_mit_cache_mit_dritter_max']:.2f} mit Cache · "
             f"~${s['usd_ohne_cache_mit_dritter_max']:.2f} ohne Cache"
             + (f" · Batch {_batch_zeile(provider, s, '_mit_dritter_max')}" if batch else ""))
    z.append("  Wiederholungen bei ungültigen Antworten sind nicht eingerechnet (Erfahrung: wenige Prozent).")
    return "\n".join(z)


# --------------------------------------------------------------------------- Lauf-Steuerung

@dataclass
class Bilanz:
    ok: int = 0
    fehlgeschlagen: int = 0
    uebersprungen: int = 0
    usage: list[dict] = field(default_factory=list)
    fehler: list[str] = field(default_factory=list)


class Protokoll:
    def __init__(self, pfad: Path):
        self.pfad = pfad
        self._lock = threading.Lock()

    def schreibe(self, eintrag: dict) -> None:
        with self._lock:
            self.pfad.parent.mkdir(parents=True, exist_ok=True)
            with self.pfad.open("a", encoding="utf-8") as f:
                f.write(json.dumps(eintrag, ensure_ascii=False) + "\n")


def fuehre_lauf_aus(bewerter: Any, eintraege: list[ti.Eintrag], lauf: int, basis: Path, force: bool,
                    max_parallel: int, drossel: Drossel, protokoll: Protokoll, bilanz: Bilanz,
                    schlafen: Callable[[float], None] = time.sleep) -> None:
    offen = []
    for e in reihenfolge(eintraege, lauf):
        pfad = ziel_pfad(basis, bewerter.provider, lauf, e)
        if not force and ist_aktuell(lade_ergebnis(pfad), e, bewerter.model):
            bilanz.uebersprungen += 1
            continue
        offen.append((e, pfad))
    log.info("Lauf %d: %d Anfragen, %d aktuell (übersprungen)", lauf, len(offen), len(eintraege) - len(offen))

    def eins(e: ti.Eintrag, pfad: Path) -> Ergebnis:
        erg = bewerte(bewerter, e, lauf, drossel, schlafen=schlafen)
        speichere(pfad, erg)
        protokoll.schreibe({"timestamp": erg.meta["timestamp"], "lauf": lauf, "datei": e.datei,
                            "status": erg.status, "model_served": erg.meta["model_served"],
                            "fallback": bool(erg.meta["fallback"]), "usage": erg.meta["usage"],
                            "fehler": erg.meta["fehler"]})
        return erg

    with ThreadPoolExecutor(max_workers=max(1, max_parallel)) as pool:
        futures = {pool.submit(eins, e, p): e for e, p in offen}
        for fut in as_completed(futures):
            e = futures[fut]
            try:
                erg = fut.result()
            except FatalerFehler:
                for f in futures:
                    f.cancel()
                raise
            except Exception as exc:     # unerwarteter Fehler: nur dieser Eintrag scheitert, der Lauf geht weiter
                text = f"unerwarteter Fehler: {type(exc).__name__}: {exc}"
                protokoll.schreibe({"timestamp": _jetzt(), "lauf": lauf, "datei": e.datei, "status": "fehlgeschlagen",
                                    "model_served": None, "fallback": False, "usage": {}, "fehler": [text]})
                bilanz.fehlgeschlagen += 1
                bilanz.fehler.append(f"run{lauf}/{e.datei}: {text}")
                log.exception("✗ run%d %s: %s", lauf, e.datei, text)
                continue
            bilanz.usage.append(erg.meta["usage"])
            if erg.status == "ok":
                bilanz.ok += 1
                served = erg.meta["model_served"]
                extra = f" (bedient von {served})" if served and served != bewerter.model else ""
                log.info("✓ run%d %s%s", lauf, e.datei, extra)
            else:
                bilanz.fehlgeschlagen += 1
                bilanz.fehler.append(f"run{lauf}/{e.datei}: {'; '.join(erg.meta['fehler'])}")
                log.error("✗ run%d %s: %s", lauf, e.datei, "; ".join(erg.meta["fehler"]))


def kandidaten_dritter_lauf(provider: str, eintraege: list[ti.Eintrag], basis: Path,
                            schwelle: float = DRITTER_LAUF_SCHWELLE) -> list[ti.Eintrag]:
    res = []
    for e in eintraege:
        d1 = lade_ergebnis(ziel_pfad(basis, provider, 1, e))
        d2 = lade_ergebnis(ziel_pfad(basis, provider, 2, e))
        if braucht_dritten_lauf(d1, d2, schwelle):
            res.append(e)
    return res


def erstelle_bewerter(a: argparse.Namespace) -> Any:
    if a.provider == "claude-cli":
        return ClaudeCliBewerter(model=a.model or MODELL["claude-cli"], effort=a.effort)
    if a.provider == "claude":
        return ClaudeBewerter(model=a.model or MODELL["claude"], effort=a.effort,
                              max_tokens=a.max_tokens or CLAUDE_MAX_TOKENS, fallback=not a.no_fallback)
    return GeminiBewerter(model=a.model or MODELL["gemini"], thinking_level=a.thinking_level,
                          max_output_tokens=a.max_tokens or GEMINI_MAX_OUTPUT_TOKENS)


PAKETE = {"claude": ("anthropic", "anthropic"), "claude-cli": ("anthropic", "anthropic"),   # cli: transform_schema
          "gemini": ("google.genai", "google-genai")}


def pruefe_pakete(provider: str, importieren: Callable[[str], Any] = importlib.import_module) -> None:
    """SDK des Providers früh importieren — fehlt es, mit klarer Anleitung abbrechen (vor dem ersten Lauf)."""
    modul, paket = PAKETE[provider]
    try:
        importieren(modul)
    except ImportError as e:
        msg = (f"Python-Paket «{paket}» fehlt oder ist nicht importierbar ({e.__class__.__name__}: {e}). "
               f"Installieren im aktiven venv ({sys.executable}): "
               "`python -m pip install -r requirements-scoring.txt`")
        if provider == "gemini":
            msg += (" — Hinweis: Ein fremdes Paket namens «google» kann den Namespace «google.*» überdecken; "
                    "prüfen mit `python -m pip show google` (falls installiert und nicht benötigt: "
                    "`python -m pip uninstall google`, danach google-genai neu installieren).")
        raise FatalerFehler(msg) from e


def pruefe_keys(provider: str) -> None:
    if provider == "gemini" and not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        raise FatalerFehler("GEMINI_API_KEY (oder GOOGLE_API_KEY) fehlt — in .env eintragen")
    if provider == "claude-cli":
        if shutil.which(CLAUDE_CLI) is None:
            raise FatalerFehler(f"Claude Code («{CLAUDE_CLI}») nicht im PATH — installieren, `claude` starten "
                                "und /login mit dem Abo-Konto ausführen")
        if any(os.environ.get(k) for k in CLAUDE_CLI_ENV_ENTFERNEN):
            log.info("API-Zugangsdaten aus der Umgebung werden für claude -p entfernt (Abrechnung über das Abo)")
        return
    if provider == "claude" and not os.environ.get("ANTHROPIC_API_KEY"):
        log.warning("ANTHROPIC_API_KEY nicht gesetzt — das SDK versucht andere Anmeldedaten "
                    "(ANTHROPIC_AUTH_TOKEN bzw. `ant auth login`-Profil)")


BATCH_AKTIONEN = ("submit", "status", "collect", "followup")


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--provider", choices=PROVIDER, required=True)
    ap.add_argument("--runs", type=int, default=2, choices=(1, 2, 3),
                    help="unabhängige Läufe (Standard 2; bei 2 folgt Lauf 3 automatisch, wenn |Δζ| > Schwelle; "
                         "im Batch-Modus über --batch followup)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--only", nargs="+", metavar="ISCO", help="nur diese ISCO-Codes oder -Präfixe")
    g.add_argument("--pilot", action="store_true", help="nur die 15 Pilotberufe")
    ap.add_argument("--force", action="store_true", help="auch aktuelle (bzw. in offenen Batches enthaltene) "
                                                         "Bewertungen neu anfragen")
    ap.add_argument("--dry-run", action="store_true", help="nur Aufrufe und Token-/Kostenschätzung zeigen")
    ap.add_argument("--count-tokens", action="store_true",
                    help="mit --dry-run: exakte Input-Tokens über count_tokens (braucht Key, kostenlos)")
    ap.add_argument("--max-parallel", type=int, default=MAX_PARALLEL)
    ap.add_argument("--model", default=None, help="Modell-ID überschreiben")
    ap.add_argument("--effort", default=CLAUDE_EFFORT, choices=CLAUDE_EFFORTS, help="nur claude / claude-cli")
    ap.add_argument("--thinking-level", default=GEMINI_THINKING, choices=GEMINI_THINKING_LEVELS, help="nur gemini")
    ap.add_argument("--max-tokens", type=int, default=None, help="Obergrenze Thinking + Antwort")
    ap.add_argument("--no-fallback", action="store_true", help="nur claude: kein Refusal-Fallback (synchron)")
    ap.add_argument("--no-third-run", action="store_true", help="keinen dritten Lauf bei |Δζ| > Schwelle")
    ap.add_argument("--threshold", type=float, default=DRITTER_LAUF_SCHWELLE, help="Schwelle |Δζ| für Lauf 3")
    ap.add_argument("--out", default=str(tr.BEWERTUNGEN_DIR), help="Basisverzeichnis der Bewertungen")
    b = ap.add_argument_group("Batch-Modus (50 %% günstiger, Ergebnis bis 24 h; siehe docs/neubewertung_lokal.md)")
    b.add_argument("--batch", choices=BATCH_AKTIONEN, default=None,
                   help="submit: einreichen · status: offene Batches anzeigen · collect: fertige Ergebnisse holen "
                        "· followup: Wiederholungen + dritte Läufe als neuen Batch einreichen")
    b.add_argument("--batch-id", default=None, help="status/collect nur für diesen Batch")
    b.add_argument("--refusal-sync", action="store_true",
                   help="followup: Refusals synchron (claude: mit server-seitigem Fallback) nachholen")
    b.add_argument("--cache-ttl", choices=("5m", "1h"), default="5m",
                   help="nur claude im Batch: TTL des System-Prompt-Caches (Standard 5m: Fehltreffer kosten "
                        "1.25× statt 2×; 1h lohnt nur bei deutlich höherer Trefferquote, siehe Dry-Run)")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None, bewerter: Any = None,
         schlafen: Callable[[float], None] = time.sleep) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    a = parse_args(argv)
    try:
        from dotenv import load_dotenv
        load_dotenv(tr.REPO_DIR / ".env")
    except ImportError:          # pragma: no cover
        pass
    eintraege = ti.baue_eintraege(a.only, a.pilot)
    if not eintraege:
        log.error("keine Einträge ausgewählt")
        return 2
    bewerter = bewerter or erstelle_bewerter(a)
    basis = Path(a.out)
    laeufe = list(range(1, a.runs + 1))

    if a.batch:
        if bewerter.provider == "claude-cli":
            log.error("--batch gibt es nur für die APIs (claude, gemini), nicht für claude-cli")
            return 2
        import task_batch as tb
        return tb.ausfuehren(a, bewerter, eintraege, basis, schlafen=schlafen)

    if a.dry_run:
        n = 0
        for lauf in laeufe:
            for e in eintraege:
                if a.force or not ist_aktuell(lade_ergebnis(ziel_pfad(basis, bewerter.provider, lauf, e)),
                                              e, bewerter.model):
                    n += 1
        n3 = len(eintraege) if (a.runs == 2 and not a.no_third_run) else 0
        print(f"{len(eintraege)} Einträge × {a.runs} Läufe")
        try:
            if a.count_tokens:
                pruefe_pakete(bewerter.provider)
            s = schaetze(bewerter, eintraege, n, n3, zaehlen=a.count_tokens, basis=basis, cache_ttl=a.cache_ttl)
        except FatalerFehler as e:
            log.error("Abbruch: %s", e)
            return 3
        print(formatiere_schaetzung(bewerter.provider, bewerter.model, s))
        return 0

    try:
        pruefe_pakete(bewerter.provider)
        pruefe_keys(bewerter.provider)
        drossel = Drossel(schlafen)
        protokoll = Protokoll(basis / bewerter.provider / "protokoll.jsonl")
        bilanz = Bilanz()
        for lauf in laeufe:
            fuehre_lauf_aus(bewerter, eintraege, lauf, basis, a.force, a.max_parallel, drossel, protokoll,
                            bilanz, schlafen)
        if a.runs == 2 and not a.no_third_run:
            dritte = kandidaten_dritter_lauf(bewerter.provider, eintraege, basis, a.threshold)
            log.info("Dritter Lauf für %d Einträge (|Δζ| > %g)", len(dritte), a.threshold)
            if dritte:
                fuehre_lauf_aus(bewerter, dritte, 3, basis, a.force, a.max_parallel, drossel, protokoll,
                                bilanz, schlafen)
    except FatalerFehler as e:
        log.error("Abbruch: %s", e)
        return 3
    print(f"Fertig: {bilanz.ok} ok, {bilanz.fehlgeschlagen} fehlgeschlagen, {bilanz.uebersprungen} übersprungen")
    print(token_zeile(bewerter.provider, bilanz.usage))
    for f in bilanz.fehler:
        print(f"  FEHLGESCHLAGEN {f}")
    return 1 if bilanz.fehlgeschlagen else 0


if __name__ == "__main__":
    # Über den Modulnamen ausführen: task_batch importiert «task_scorer»; liefe main() hier in __main__,
    # gäbe es zwei Kopien der Klassen (__main__.AntwortFehler ≠ task_scorer.AntwortFehler) und
    # «except ts.AntwortFehler» in task_batch griffe bei Fehlern des Bewerters nicht.
    import task_scorer
    sys.exit(task_scorer.main())
