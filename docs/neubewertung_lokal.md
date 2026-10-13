# Aufgabenbasierte Neubewertung lokal ausführen (Rubrik v2.2)

Diese Anleitung beschreibt, wie du die neue aufgabenbasierte KI-Expositionsbewertung **auf deinem
Rechner mit eigenen API-Keys** laufen lässt — zuerst für die 15 Pilotberufe mit beiden Providern,
danach optional für alle 179 Einträge. Die App und `scores.csv` bleiben unverändert; die
Ergebnisse landen in `data/processed/bewertungen/` und `data/processed/scores_aufgaben.csv`.

Rubrik v2.2 = Pilot-Rubrik v2.1 **plus** ein Block `zusammenfassung` je Beruf (`haupt_risiko`,
`begruendung`, `zeitrahmen`). Der Block fliesst nicht in ζ, β oder die Zeitersparnis ein.

## 1. Einrichten (einmalig)

Voraussetzung: Python ≥ 3.10.

```bash
cd ki-jobexposition-schweiz
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt  # enthält requirements-scoring.txt (anthropic, google-genai, jsonschema)
pytest tests/ -q                     # alles grün? (ohne Netz, ohne Keys)
```

`.env` im Repo-Wurzelverzeichnis anlegen bzw. ergänzen (wird nie committet):

```bash
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...        # alternativ GOOGLE_API_KEY (hat Vorrang, wenn beide gesetzt sind)
```

Das Gemini-Modell ist nur im **Paid Tier** der Gemini API verfügbar (nicht im Free Tier und nicht
im Google-AI-Pro-Abo).

## 2. Dry-Run: Aufrufe und Kosten prüfen (ohne Bewertungsaufruf)

```bash
python src/scoring/task_scorer.py --provider claude --pilot --runs 2 --dry-run
python src/scoring/task_scorer.py --provider gemini --pilot --runs 2 --dry-run
# genauer (exakte Input-Tokens über count_tokens; kostenlos, braucht Key + Netz):
python src/scoring/task_scorer.py --provider claude --pilot --runs 2 --dry-run --count-tokens
```

Schätzung vom 13.10.2026 (grob: Zeichen/3; ~24 500 Input-Tokens je Aufruf, davon ~22 300 für
Rubrik + Schema + Auftrag, die gecacht werden; ~13 000 Output-Tokens inkl. Thinking bei Stufe
«high» — der Output ist die grösste Unsicherheit):

| Umfang | Aufrufe | Claude (`claude-opus-5-5`, effort high) | Gemini (`gemini-4-argon`, thinking high) |
|---|---|---|---|
| Pilot, 2 Läufe | 30 (+ bis 15 für Lauf 3) | ~$8 mit Cache / ~$11 ohne (max. ~$16 inkl. Lauf 3) | ~$4 mit Cache / ~$5 ohne (max. ~$8) |
| alle 179, 2 Läufe | 358 (+ bis 179) | ~$98 mit Cache / ~$128 ohne (max. ~$192) | ~$49 mit Cache / ~$64 ohne (max. ~$96) |

Gemini-Preise sind Einführungspreise bis 30.11.2026 ($2 / $10 je Mio. Input-/Output-Tokens); ab
1.12.2026 verdoppeln sie sich ($4 / $20). Claude: $4 / $20, Cache-Lesen $0.20, Cache-Schreiben
$5 je Mio. Tokens. «Mit Cache» setzt voraus, dass der identische System-Prompt aus dem Cache
gelesen wird (Claude: explizites Prompt-Caching; Gemini: implizites Caching ab 4096 Tokens, nicht
garantiert). Die tatsächlichen Tokens stehen nach dem Lauf in jeder Ergebnisdatei (`meta.usage`)
und in `protokoll.jsonl`.

## 3. Pilot mit beiden Providern

```bash
python src/scoring/task_scorer.py --provider claude --pilot --runs 2
python src/scoring/task_scorer.py --provider gemini --pilot --runs 2
python src/scoring/task_vergleich.py
```

- Je Provider zwei unabhängige Läufe (Reihenfolge je Lauf mit festem Seed gemischt). Weicht der
  ζ-Score eines Berufs zwischen Lauf 1 und 2 um mehr als 1.0 ab, folgt automatisch Lauf 3 für
  diesen Beruf.
- Parallelität: Standard 2 gleichzeitige Anfragen (`--max-parallel`). Bei Stufe «high» kann ein
  einzelner Aufruf mehrere Minuten dauern; für den Pilot (30–45 Aufrufe) grob 30–90 Minuten je
  Provider einplanen (nicht gemessen).
- Ergebnisse: `data/processed/bewertungen/<provider>/run<N>/<isco>_<slug>.json` mit `meta`
  (Provider, angefragtes und tatsächlich bedienendes Modell, Rubrik-Version, Input-Hash, Zeit,
  Tokens, stop_reason, Fehler, Hinweise) und `bewertung`.
- `task_vergleich.py` schreibt `data/processed/bewertungen/vergleich.md`: Pilot (Abo-Läufe,
  `data/processed/bewertungen/pilot_abo/`) vs. API-Claude vs. API-Gemini für die 15 Pilotberufe
  und die Spearman-Korrelation gegen ILO 2025, Eloundou et al. und den Anthropic Economic Index.

Optional danach alle 179 Einträge (nur fehlende/geänderte werden angefragt):

```bash
python src/scoring/task_scorer.py --provider claude --runs 2
python src/scoring/task_scorer.py --provider gemini --runs 2
python src/scoring/task_aggregate.py      # → data/processed/scores_aufgaben.csv
python src/scoring/task_vergleich.py
```

## 4. Ergebnisse committen und pushen

```bash
python src/scoring/task_aggregate.py
git add data/processed/bewertungen/ data/processed/scores_aufgaben.csv
git commit -m "data: aufgabenbasierte Bewertung Pilot (Rubrik v2.2)"
git push origin <branch>
```

Ein Push auf HuggingFace (`git push hf main`) ist nicht nötig — die App nutzt die neuen Werte
erst nach dem separaten App-Umbau.

## 5. Wenn etwas schiefgeht

Der Lauf ist **jederzeit wiederholbar**: Derselbe Befehl fragt nur Einträge an, für die noch keine
gültige, aktuelle Bewertung existiert (gleicher Input-Hash, gleiche Rubrik-Version, gleiches
Modell). Abbrechen mit Ctrl-C ist unkritisch (Dateien werden atomar geschrieben).

| Meldung | Bedeutung / Abhilfe |
|---|---|
| `Abbruch: … Zugriff verweigert (401/403)` | Key fehlt/falsch, bei Gemini evtl. kein Paid Tier → `.env` prüfen |
| `Abbruch: … Modell nicht gefunden` | Modell-ID ungültig oder nicht freigeschaltet → `--model <id>` |
| `Rate-Limit (429) — neuer Versuch in … s` | wird automatisch mit Pause wiederholt; bei Häufung `--max-parallel 1` |
| `✗ run1 …: Versuch 1: …; Versuch 2: …` | Antwort zweimal ungültig (Schema/Summe ≠ 100) → als fehlgeschlagen gespeichert (`rohantwort` in der Datei); Befehl einfach erneut ausführen |
| `Refusal (Kategorie …)` | Modell hat abgelehnt; bei Claude greift vorher der server-seitige Fallback — `meta.model_served` / `meta.fallback` zeigen, welches Modell bedient hat |
| `Antwort abgeschnitten (max_tokens …)` | Thinking + Antwort zu lang → `--max-tokens` erhöhen oder `--effort medium` / `--thinking-level medium` |
| `Verbindungsfehler` / `Serverfehler (5xx)` | automatische Wiederholung mit Backoff; sonst später erneut starten |

`--force` fragt auch aktuelle Bewertungen neu an (z. B. `--nur 2411 --force`). Alle Aufrufe stehen
in `data/processed/bewertungen/<provider>/protokoll.jsonl`.

## 6. Verwendete Modelle und Parameter (geprüft am 13.10.2026)

| Provider | Modell-ID | Einstellungen | Quelle |
|---|---|---|---|
| Anthropic | `claude-opus-5-5` | Messages API über `client.beta.messages.stream(...)` + `get_final_message()`; `thinking={"type": "adaptive"}` (Thinking ist bei diesem Modell immer an; `disabled`/`budget_tokens` → 400); `output_config={"effort": "high", "format": {"type": "json_schema", "schema": …}}` (Modell-Default wäre `medium`); `max_tokens=64000`; System-Prompt mit `cache_control`; `fallbacks="default"` mit Beta-Header `server-side-fallback-2026-07-01`; keine Sampling-Parameter | Anthropic-SDK-Dokumentation (claude-api-Referenz: Python README, Structured Outputs, Opus-5.5-Migration, Refusal-Fallbacks); `anthropic` 1.13.0 |
| Google | `gemini-4-argon` (Stable) | `client.models.generate_content(...)` mit `GenerateContentConfig(system_instruction=…, response_mime_type="application/json", response_json_schema=…, thinking_config=ThinkingConfig(thinking_level="high"), max_output_tokens=65536)`; keine `temperature`/`top_p`/`top_k` (laut Migrationshinweis ignoriert); Client-Timeout 15 min | ai.google.dev/gemini-api/docs/models/gemini-4-argon, …/docs/latest-model, …/docs/generate-content/structured-output, …/docs/generate-content/thinking; Blog «Gemini 4 Argon is now available for developers» (13.10.2026); `google-genai` 2.30.1 |

Hinweise:
- Die Gemini-Doku zeigt für Python inzwischen `config={"response_format": {"text": {...}}}`; das
  aktuelle SDK `google-genai` 2.30.1 lehnt dieses Feld in `GenerateContentConfig` ab (*extra inputs
  are not permitted*). Verwendet wird daher das im SDK dokumentierte Paar `response_mime_type` +
  `response_json_schema` (in der REST-Referenz als Vorgänger von `responseFormat` geführt).
- Gemini empfiehlt für neue Projekte die Interactions API (Beta); `generateContent` bleibt laut
  Doku der stabile Weg und speichert keine Interaktionen serverseitig.
- Structured Outputs unterstützen nicht alle JSON-Schema-Features (z. B. if/then, minLength).
  Gesendet wird ein daraus abgeleitetes, kompatibles Schema; geprüft wird jede Antwort lokal gegen
  das vollständige Schema `src/scoring/rubrik/schema_v2_2.json`.
