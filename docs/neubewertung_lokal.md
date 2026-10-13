# Aufgabenbasierte Neubewertung lokal ausführen (Rubrik v2.2)

Diese Anleitung beschreibt, wie du die neue aufgabenbasierte KI-Expositionsbewertung **auf deinem
Rechner mit eigenen API-Keys** laufen lässt: zuerst eine kurze synchrone Probe je Provider, danach
der volle Lauf für alle Einträge (derzeit 187) — empfohlen im **Batch-Modus** (50 % günstiger).
Die App und `scores.csv` bleiben unverändert; die Ergebnisse landen in
`data/processed/bewertungen/` und `data/processed/scores_aufgaben.csv`.

Rubrik v2.2 = Pilot-Rubrik v2.1 **plus** ein Block `zusammenfassung` je Beruf (`haupt_risiko`,
`begruendung`, `zeitrahmen`). Der Block fliesst nicht in ζ, β oder die Zeitersparnis ein.

## 1. Einrichten (einmalig)

Voraussetzung: Python ≥ 3.10.

```bash
cd ki-jobexposition-schweiz
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
python -m pip install -r requirements-dev.txt  # enthält requirements-scoring.txt (anthropic, google-genai, jsonschema)
pytest tests/ -q                     # alles grün? (ohne Netz, ohne Keys)
```

`.env` im Repo-Wurzelverzeichnis anlegen bzw. ergänzen (wird nie committet):

```bash
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...        # alternativ GOOGLE_API_KEY (hat Vorrang, wenn beide gesetzt sind)
```

Das Gemini-Modell ist nur im **Paid Tier** der Gemini API verfügbar (nicht im Free Tier und nicht
im Google-AI-Pro-Abo).

`task_scorer.py` prüft vor dem ersten Aufruf, ob das SDK des Providers importierbar ist, und bricht
sonst mit einer klaren Meldung ab (`Python-Paket «google-genai» fehlt …`). Abhilfe:
`python -m pip install -r requirements-scoring.txt` im aktiven venv. Bleibt der Fehler bei Gemini,
überdeckt oft ein fremdes Paket namens `google` den Namespace: `python -m pip show google` — falls
installiert und nicht benötigt, `python -m pip uninstall google` und google-genai neu installieren.

## 2. Dry-Run: Aufrufe und Kosten prüfen (ohne Bewertungsaufruf)

```bash
python src/scoring/task_scorer.py --provider claude --runs 2 --batch submit --dry-run   # alle, Batch
python src/scoring/task_scorer.py --provider gemini --runs 2 --batch submit --dry-run
python src/scoring/task_scorer.py --provider claude --pilot --runs 2 --dry-run          # Pilot, synchron
# genauer (exakte Input-Tokens über count_tokens; kostenlos, braucht Key + Netz):
python src/scoring/task_scorer.py --provider claude --pilot --runs 2 --dry-run --count-tokens
```

Liegen bereits Ergebnisdateien vor (z. B. nach der Probe in Abschnitt 3), rechnet der Dry-Run mit
deren **gemessenen** Mittelwerten (Ausgabe «gemessen aus N Aufrufen»), sonst mit der Schätzung.
Die Schätzung ist an der ersten Claude-Probe (2512, effort high, 13.10.2026) kalibriert:
System-Prompt (Auftrag + Rubrik + Schema) 36 937 Tokens, Berufs-Input ~3 000 Tokens, Ausgabe 4 847
Tokens inkl. Thinking → Schätzwerte ~40 700 Input-Tokens je Aufruf (davon ~37 200 cachebar) und
~5 500 Output-Tokens (Stufe «high»).

Schätzung vom 13.10.2026 (Dry-Run, ohne Messwerte; Preise je Mio. Tokens: Claude $4 / $20,
Cache-Lesen $0.20, Cache-Schreiben $5 (5 min) bzw. $8 (1 h); Gemini $2 / $10 Einführungspreis):

| Umfang | Aufrufe | Claude synchron | Claude **Batch** | Gemini synchron | Gemini **Batch** |
|---|---|---|---|---|---|
| Pilot, 2 Läufe | 30 (+ bis 15 für Lauf 3) | ~$4.30 mit Cache / ~$8.20 ohne | ~$2.05–3.90 (Cache-Treffer 98–30 %) / ~$4.10 ohne Cache | ~$2.05 mit Cache / ~$4.10 ohne | ~$2.05 |
| alle 187, 2 Läufe | 374 (+ bis 187) | ~$49 mit Cache / ~$102 ohne | **~$25–48** / ~$51 ohne Cache | ~$25 mit Cache / ~$51 ohne | **~$26** |
| alle 187 inkl. maximalem Lauf 3 | bis 561 | ~$74 / ~$153 | ~$38–72 / ~$77 | ~$37 / ~$77 | ~$38 |

- **Batch-Rabatt:** beide APIs 50 % auf alle Tokens; bei Claude stapeln sich Batch- und
  Cache-Rabatt. Cache-Treffer sind im Batch nur «best effort» (Claude-Doku: typisch 30–98 %),
  deshalb die Spanne. Standard-TTL im Batch ist 5 min (`--cache-ttl 5m`): ein Fehltreffer kostet
  1.25× statt 2× (1 h) des Input-Preises; mit `--cache-ttl 1h` wäre der Fall «30 % Treffer» teurer
  (~$63) als ganz ohne Cache. Die tatsächlichen Cache-Zahlen stehen nach `collect` in `meta.usage`
  (`cache_read_input_tokens` vs. `cache_creation_input_tokens`).
- **Gemini:** «mit Cache» (synchron) setzt implizites Caching ab 4096 Tokens voraus — nicht
  garantiert. Im Batch wird kein Cache genutzt (die Batch-Doku nennt nur explizites Context
  Caching über `cached_content`); der Batch ist damit nur dann klar günstiger, wenn das implizite
  Caching synchron nicht greift. Ab 1.12.2026 verdoppeln sich die Gemini-Preise ($4 / $20).
- Wiederholungen bei ungültigen Antworten sind nicht eingerechnet (Erfahrung: wenige Prozent).

## 3. Synchrone Probe (Schema-Prüfung, je Provider ein Aufruf)

Vor dem vollen Lauf je Provider **einen** Beruf synchron bewerten — so siehst du sofort, ob Key,
Modell, Structured Output und Validierung funktionieren:

```bash
python src/scoring/task_scorer.py --provider claude --only 2512 --runs 1
python src/scoring/task_scorer.py --provider gemini --only 2512 --runs 1
```

Erwartet: `Fertig: 1 ok, 0 fehlgeschlagen, …` und eine `Tokens: …`-Zeile; die Datei
`data/processed/bewertungen/<provider>/run1/2512_softwareentwickler.json` hat `meta.status = "ok"`.

## 4. Voller Lauf im Batch-Modus (empfohlen)

Der Batch-Modus ist **zustandsbehaftet**: Jeder Schritt ist ein eigener Befehl, das Terminal darf
zwischendurch geschlossen werden. Ein Batch braucht meist unter einer Stunde, höchstens **24 h**
(Claude: danach verfallen offene Anfragen; Gemini: Ziel 24 h, Ablauf nach 48 h).

```bash
# 1. Einreichen (je Provider; nur fehlende/veraltete Einträge, Läufe 1 und 2)
python src/scoring/task_scorer.py --provider claude --runs 2 --batch submit
python src/scoring/task_scorer.py --provider gemini --runs 2 --batch submit

# 2. Status ansehen (beliebig oft)
python src/scoring/task_scorer.py --provider claude --batch status

# 3. Fertige Ergebnisse einsammeln (validiert, gleiches Format wie synchron)
python src/scoring/task_scorer.py --provider claude --batch collect

# 4. Nachlauf: Wiederholungen + dritte Läufe (|Δζ| > 1.0) als neuen Batch; Refusals synchron
python src/scoring/task_scorer.py --provider claude --runs 2 --batch followup --refusal-sync
python src/scoring/task_scorer.py --provider claude --batch collect      # nach Abschluss

# 5. Auswerten
python src/scoring/task_aggregate.py      # → data/processed/scores_aufgaben.csv
python src/scoring/task_vergleich.py      # → data/processed/bewertungen/vergleich.md
```

Für Gemini dieselben Befehle mit `--provider gemini`. `--pilot` bzw. `--only …` schränken
`submit`/`followup` wie im synchronen Modus ein; `--dry-run` zeigt bei `submit` und `followup` die
Anzahl Anfragen und die Kosten mit Batch-Rabatt, ohne etwas einzureichen.

Was die Schritte tun:

- **`submit`** baut dieselben Anfragen wie synchron (System-Prompt, Berufs-Input, Schema, Thinking-
  Stufe) und reicht sie ein. Übersprungen werden Einträge mit gültigem, aktuellem Ergebnis (gleicher
  Input-Hash, Rubrik-Version, Modell) und solche, die schon in einem offenen Batch stecken
  (`--force` reicht trotzdem ein). Je Batch entsteht eine Zustandsdatei
  `data/processed/bewertungen/<provider>/batches/<batch_id>.json` (custom_id → Eintrag, Lauf,
  Input-Hash; Modell, Rubrik-Version, Einstellungen, Zeitpunkt — keine Keys). Gemini-Batches mit
  Inline-Anfragen müssen unter 20 MB bleiben; grössere Läufe werden automatisch auf mehrere Batches
  verteilt (je Anfrage ~95 KB; der volle Lauf mit 374 Anfragen ≈ 3 Batches).
- **`status`** fragt alle noch nicht eingesammelten Batches ab (Status, Zähler).
- **`collect`** holt nur **fertige** Batches, ordnet jedes Ergebnis über seine `custom_id` zu
  (Ergebnisse kommen in beliebiger Reihenfolge), prüft es wie synchron (Schema + Summe = 100 +
  isco_code/beruf) und schreibt es nach `run<N>/` mit `meta.modus = "batch"`, `batch_id`,
  `custom_id`, `model_served`, `usage`, `stop_reason`. Fehlgeschlagene Anfragen (ungültig, Refusal,
  Fehler, abgelaufen, fehlend) werden als `status = "fehlgeschlagen"` mit `meta.fehler_art`
  gespeichert und in `protokoll.jsonl` vermerkt. Eingesammelte Batches werden markiert — ein
  zweites `collect` ändert nichts. Eine vorhandene gültige Bewertung wird nie durch ein
  fehlgeschlagenes Batch-Ergebnis überschrieben.
- **`followup`** reicht als neuen Batch ein: (a) **Korrekturen** für ungültige Antworten (wie
  synchron: Antwort + Fehlerliste als Folgeturn, ein Korrekturversuch), (b) **Wiederholungen** für
  Fehler/abgelaufene/fehlende Ergebnisse, (c) **Lauf 3** für Einträge mit |Δζ| zwischen Lauf 1 und 2
  > 1.0 (`--threshold`, `--no-third-run`). **Refusals** werden nicht erneut in den Batch gegeben:
  Der server-seitige Refusal-Fallback von Claude ist in der Batches-API nicht verfügbar. Mit
  `--refusal-sync` werden sie synchron nachgeholt (Claude mit Fallback — `meta.model_served` zeigt
  das bedienende Modell), sonst nur aufgelistet.

## 5. Alternativ: synchron (Pilot)

```bash
python src/scoring/task_scorer.py --provider claude --pilot --runs 2
python src/scoring/task_scorer.py --provider gemini --pilot --runs 2
python src/scoring/task_vergleich.py
```

- Je Provider zwei unabhängige Läufe (Reihenfolge je Lauf mit festem Seed gemischt). Weicht der
  ζ-Score eines Berufs zwischen Lauf 1 und 2 um mehr als 1.0 ab, folgt automatisch Lauf 3.
- Parallelität: Standard 2 gleichzeitige Anfragen (`--max-parallel`). Bei Stufe «high» kann ein
  einzelner Aufruf mehrere Minuten dauern; für den Pilot (30–45 Aufrufe) grob 30–90 Minuten je
  Provider einplanen (nicht gemessen). Das Terminal muss offen bleiben.
- Ergebnisse: `data/processed/bewertungen/<provider>/run<N>/<isco>_<slug>.json` mit `meta`
  (Provider, angefragtes und tatsächlich bedienendes Modell, Rubrik-Version, Input-Hash, Zeit,
  Tokens, stop_reason, Fehler, Hinweise) und `bewertung`.
- `task_vergleich.py` schreibt `data/processed/bewertungen/vergleich.md`: Pilot (Abo-Läufe,
  `data/processed/bewertungen/pilot_abo/`) vs. API-Claude vs. API-Gemini für die 15 Pilotberufe
  und die Spearman-Korrelation gegen ILO 2025, Eloundou et al. und den Anthropic Economic Index.

Synchron und Batch lassen sich mischen: Beide schreiben dasselbe Format, die Delta-Logik sieht
gültige Ergebnisse beider Wege.

## 6. Ergebnisse committen und pushen

```bash
python src/scoring/task_aggregate.py
git add data/processed/bewertungen/ data/processed/scores_aufgaben.csv
git commit -m "data: aufgabenbasierte Bewertung (Rubrik v2.2)"
git push origin <branch>
```

Die Zustandsdateien unter `bewertungen/<provider>/batches/` dürfen mit committet werden (keine
Keys). Ein Push auf HuggingFace (`git push hf main`) ist nicht nötig — die App nutzt die neuen
Werte erst nach dem separaten App-Umbau.

## 7. Wenn etwas schiefgeht

Alles ist **jederzeit wiederholbar**: Derselbe Befehl fragt nur Einträge an, für die noch keine
gültige, aktuelle Bewertung existiert (gleicher Input-Hash, gleiche Rubrik-Version, gleiches
Modell) bzw. die nicht schon in einem offenen Batch stecken. Abbrechen mit Ctrl-C ist unkritisch
(Dateien werden atomar geschrieben; ein eingereichter Batch läuft serverseitig weiter).

| Meldung | Bedeutung / Abhilfe |
|---|---|
| `Abbruch: Python-Paket «…» fehlt …` | SDK nicht installiert → `python -m pip install -r requirements-scoring.txt`; bei Gemini `pip show google` prüfen (siehe Abschnitt 1) |
| `Abbruch: … Zugriff verweigert (401/403)` | Key fehlt/falsch, bei Gemini evtl. kein Paid Tier → `.env` prüfen |
| `Abbruch: … Modell nicht gefunden` | Modell-ID ungültig oder nicht freigeschaltet → `--model <id>` |
| `Rate-Limit (429) — neuer Versuch in … s` | synchron: wird automatisch mit Pause wiederholt; bei Häufung `--max-parallel 1` |
| `✗ run1 …: Versuch 1: …; Versuch 2: …` | synchron zweimal ungültig (Schema/Summe ≠ 100) → als fehlgeschlagen gespeichert (`rohantwort`); Befehl erneut ausführen |
| `Refusal (Kategorie …)` | Modell hat abgelehnt. Synchron greift bei Claude vorher der server-seitige Fallback; im Batch nicht → `--batch followup --refusal-sync` |
| `Antwort abgeschnitten (max_tokens …)` | Thinking + Antwort zu lang → `--max-tokens` erhöhen oder `--effort medium` / `--thinking-level medium` |
| `Verbindungsfehler` / `Serverfehler (5xx)` | synchron automatische Wiederholung; im Batch-Modus Befehl später wiederholen (Zustand bleibt) |
| `noch nicht fertig: <batch_id> (in_progress)` | Batch läuft noch → später `--batch collect` |
| `[expired]` / `[fehlt]` nach `collect` | Anfrage nicht innerhalb der Frist bearbeitet → `--batch followup` |
| `[validierung]` nach `collect` | Antwort ungültig → `--batch followup` reicht einen Korrekturversuch ein |

`--force` fragt auch aktuelle Bewertungen neu an (z. B. `--only 2411 --force`). Alle Aufrufe stehen
in `data/processed/bewertungen/<provider>/protokoll.jsonl`.

## 8. Verwendete Modelle und Parameter (geprüft am 13.10.2026)

| Provider | Modell-ID | Einstellungen | Quelle |
|---|---|---|---|
| Anthropic | `claude-opus-5-5` | Messages API über `client.beta.messages.stream(...)` + `get_final_message()`; `thinking={"type": "adaptive"}` (Thinking ist bei diesem Modell immer an; `disabled`/`budget_tokens` → 400); `output_config={"effort": "high", "format": {"type": "json_schema", "schema": …}}` (Modell-Default wäre `medium`); `max_tokens=64000`; System-Prompt mit `cache_control`; `fallbacks="default"` mit Beta-Header `server-side-fallback-2026-07-01`; keine Sampling-Parameter | Anthropic-SDK-Dokumentation (claude-api-Referenz: Python README, Structured Outputs, Opus-5.5-Migration, Refusal-Fallbacks); `anthropic` 1.13.0 |
| Anthropic, Batch | `claude-opus-5-5` | `client.messages.batches.create(requests=[{"custom_id", "params"}])` mit denselben Parametern **ohne** `fallbacks`/Beta-Header (von der Batches-API abgelehnt) und ohne Streaming; `retrieve(id).processing_status == "ended"`, dann `results(id)` (Typen `succeeded`/`errored`/`canceled`/`expired`); custom_id `^[a-zA-Z0-9_-]{1,64}$`; Ergebnisse in beliebiger Reihenfolge; ≤ 100 000 Anfragen bzw. 256 MB je Batch; Ablauf nach 24 h, Ergebnisse 29 Tage abrufbar; Batch-Preis Opus 5.5 $2 / $10, Rabatt stapelt sich mit Prompt-Caching; Cache-Treffer «best effort» (30–98 %), Doku regt 1-h-TTL an | platform.claude.com/docs/en/build-with-claude/batch-processing; claude-api-Referenz (python/claude-api/batches.md, Refusal-Fallbacks: «rejected on the Batches API», cost-optimization 2.5) |
| Google | `gemini-4-argon` (Stable) | `client.models.generate_content(...)` mit `GenerateContentConfig(system_instruction=…, response_mime_type="application/json", response_json_schema=…, thinking_config=ThinkingConfig(thinking_level="high"), max_output_tokens=65536, automatic_function_calling=AutomaticFunctionCallingConfig(disable=True))`; keine `temperature`/`top_p`/`top_k` (laut Migrationshinweis ignoriert); Client-Timeout 15 min | ai.google.dev/gemini-api/docs/models/gemini-4-argon, …/docs/latest-model, …/docs/generate-content/structured-output, …/docs/generate-content/thinking; Blog «Gemini 4 Argon is now available for developers» (13.10.2026); `google-genai` 2.30.1 |
| Google, Batch | `gemini-4-argon` | `client.batches.create(model=…, src=[InlinedRequest(contents=…, config=<gleiche GenerateContentConfig>, metadata={"custom_id": …})], config={"display_name": …})`; `client.batches.get(name=…)` bis `JOB_STATE_SUCCEEDED`/`PARTIALLY_SUCCEEDED`/`FAILED`/`CANCELLED`/`EXPIRED`; Ergebnisse in `dest.inlined_responses` (je `response` oder `error`, `metadata` zurück); Inline < 20 MB je Batch (JSONL-Datei bis 2 GB wäre die Alternative); 50 % des Standardpreises; Ziel 24 h, Ablauf nach 48 h; Einreichen ist nicht idempotent | ai.google.dev/gemini-api/docs/batch-mode; SDK-Quelltext `google-genai` 2.30.1 (`types.InlinedRequest`/`InlinedResponse`, `batches.create`, `_InlinedRequest_to_mldev`) |

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
- Gemini-Batch: Die Doku sagt nicht ausdrücklich, dass Inline-Antworten `metadata` zurückgeben oder
  die Reihenfolge erhalten; das SDK liest `metadata` aus der Antwort. Fehlt sie bei allen Antworten
  und stimmt die Anzahl, wird über die Position zugeordnet (`meta.zuordnung = "position"`) — die
  Prüfung isco_code/beruf = Input fängt Verwechslungen ab.
