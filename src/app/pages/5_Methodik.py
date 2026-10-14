"""
Seite 5: Methodik & Quellen
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import gemeinsam as g  # noqa: E402

st.title("Methodik & Quellen")

DATA_PATH = g.SCORES_PATH
df = g.lade_scores()
n_berufe = len(df) if df is not None else 0
if df is not None:
    quellen = df["description_source"].fillna("").value_counts()
    n_esco = int(quellen.get("ESCO", 0))
    n_bb = int(quellen.get("berufsberatung.ch", 0))
    n_wiki = int(quellen.get("Wikipedia", 0))
    n_fallback = n_berufe - n_esco - n_bb - n_wiki
    qual = df["esco_match_quality"].fillna("").value_counts()
    n_korrekt, n_plausibel = int(qual.get("korrekt", 0)), int(qual.get("plausibel", 0))
    syn = df["synonyms"].fillna("").astype(str).str.strip()
    n_zusammen = int((syn != "").sum())
    n_titel = int(syn[syn != ""].str.split(";").str.len().sum())
else:
    n_esco = n_bb = n_wiki = n_fallback = n_korrekt = n_plausibel = n_zusammen = n_titel = 0


def _tsd(wert: float) -> str:
    return g.tsd(wert)


summe_tsd = float(df["employed_k"].sum()) if df is not None else 0.0
summe_text = _tsd(summe_tsd)
# SE 2024, Blatt «2024», Zeile Total (alle Erwerbstätigen, inkl. Beruf unbekannt)
SE_TOTAL_TSD = 4583.7
abdeckung_text = f"{summe_tsd / SE_TOTAL_TSD * 100:.1f} %".replace(".", ",")


def _f(wert: float, stellen: int = 1) -> str:
    return "–" if wert is None or pd.isna(wert) else f"{wert:.{stellen}f}"


# ─── Kennzahlen der aufgabenbasierten Bewertung (zur Laufzeit) ────────────────
if df is not None:
    n_unsicher = int(df["uncertain"].sum())
    n_provider = int(df["uncertain_reason"].fillna("").str.contains("Provider").sum())
    n_laeufe = int(df["uncertain_reason"].fillna("").str.contains("Läufe").sum())
    n_dritter = int(((df["n_runs_claude"] >= 3) | (df["n_runs_gemini"] >= 3)).sum())
    n_aufrufe = int((df["n_runs_claude"] + df["n_runs_gemini"]).sum())
    expo_w = g.gewichtet(df, "exposure")
    beispiel = df.loc[df["physical_automation"].idxmax()]
else:
    n_unsicher = n_provider = n_laeufe = n_dritter = n_aufrufe = 0
    expo_w = float("nan")
    beispiel = None

st.markdown("""
Diese Seite erklärt, wie die KI-Expositions-Scores entstehen, wie gut sie mit internationalen
Messungen übereinstimmen und woher die Daten stammen.
""")

# ─── KI-Exposition ────────────────────────────────────────────────────────────
st.header("KI-Expositions-Score (0–10)")
st.markdown(f"""
Der Score misst, welcher Teil der Arbeitszeit eines Berufs auf Tätigkeiten entfällt, die
**generative KI** (Sprachmodelle und darauf aufbauende Software) technisch stark beschleunigen kann.
Die Methode folgt der aufgabenbasierten Rubrik von **Eloundou et al. (*GPTs are GPTs*, Science 2024)**
und dem Index der **ILO (Gmyrek et al. 2025)**: Bewertet wird nicht der Beruf als Ganzes, sondern
jede seiner Tätigkeiten.

**Ablauf je Beruf** (Rubrik v2.2, `src/scoring/rubrik/`):

1. **Tätigkeiten ableiten:** 8–12 konkrete, beobachtbare Kerntätigkeiten mit ihrem Anteil an der
   Arbeitszeit (Summe 100 %) — aus der ESCO-Beschreibung, den wesentlichen ESCO-Kompetenzen und dem
   Schweizer Berufskontext (Bezugsperson: typische, voll ausgebildete Erwerbsperson in einem
   typischen Schweizer Betrieb, 2026).
2. **Stufe je Tätigkeit:** Reduziert die Technik die Zeit für die Tätigkeit um **mindestens 50 %
   bei gleicher Qualität** — Prüf- und Korrekturaufwand eingerechnet?

| Stufe | Bedeutung |
|---|---|
| **E0** | nicht exponiert: Schwelle nicht erreicht (z. B. körperliche Arbeit, Präsenz, Ermessen vor Ort) |
| **E1** | direkt exponiert: ein Chat-Sprachmodell mit Text-Kontext reicht |
| **E2** | exponiert mit Zusatzsoftware: erst mit Werkzeugen, Integration oder Multimodalität (z. B. KI in der Fachsoftware) |

3. **Modus und Restzeit** (nur E1/E2): **ersetzend** (KI führt aus, der Mensch gibt höchstens frei),
   **delegierend** (KI erstellt das Ergebnis, der Mensch prüft jede Ausgabe fachlich) oder
   **unterstützend** (der Mensch arbeitet selbst, KI liefert Teilergebnisse); dazu die verbleibende
   menschliche Zeit (< 10 %, 10–30 % oder 30–50 % der heutigen Zeit).
4. **Automatisierung ohne generative KI (P-Feld):** P1, wenn heute in der Schweiz kommerziell
   verfügbare nicht-generative Technik die Tätigkeit zu mindestens 50 % übernehmen kann —
   **physisch** (Robotik, Automaten, Selbstbedienung, autonome Technik) oder **Software**
   (klassische Regel-Software); sonst P0.
5. **Sicherheit** je Tätigkeit (hoch / mittel / tief) und eine **Zusammenfassung** (Hauptrisiko,
   Begründung, Zeitrahmen der Adoption).

Die Modelle berechnen keinen Gesamtscore; die Kennzahlen bildet der Code aus den Tätigkeiten
(w = Zeitanteil, Σ w = 1):

| Kennzahl | Formel | In der App |
|---|---|---|
| **ζ (Hauptmass)** | Σ w · 1[E1 oder E2] | **KI-Exposition** = 10 · ζ |
| β (vorsichtige Variante) | Σ w · (1[E1] + 0.5 · 1[E2]) | nur in den Daten (`exposure_beta`) |
| Zeitersparnis | Σ w · 1[E1/E2] · (1 − Restzeit) mit Bandmitten 0.05 / 0.20 / 0.40 | **Zeitersparnis** = 10 · Wert |
| Modus-Anteile | Anteil der exponierten Zeit je Modus | Berufssuche (ersetzend / delegierend / unterstützend) |
| Ersetzbare Zeit | Σ w · 1[ersetzend] · (1 − Restzeit) | Berufssuche, Branchen-Heatmap |
| P physisch / Software | 10 · Σ w · 1[P1, Art physisch bzw. Software] | **Physische** bzw. **Software-Automatisierung** |

**Zwei Modelle, mehrere Läufe:** Jeder Beruf wird unabhängig von **Claude Opus 5.5** (Anthropic,
über das eigene Abo) und **Gemini 4 Argon** (Google) bewertet, je in **zwei unabhängigen Läufen**
(jeder Beruf ein eigener Aufruf, gleiche Rubrik, gleiches Schema, gleiche Validierung; die Berufe
je Lauf in neu gemischter Reihenfolge). Weichen die zwei Läufe eines Modells um mehr als 1 Punkt ab, folgt automatisch ein
**dritter Lauf** (bei {n_dritter} Berufen). Jede Antwort wird gegen das JSON-Schema der Rubrik
geprüft (Zeitanteile = 100, Pflichtfelder, Regeln); ungültige Antworten werden einmal zur Korrektur
zurückgegeben und sonst verworfen. Insgesamt fliessen {n_aufrufe} gültige Bewertungen ein. Der
Score ist das **Mittel über alle gültigen Läufe beider Modelle**.

**Unsicherheits-Markierung:** Ein Beruf gilt als **unsicher**, wenn die Modelle um mehr als
1,0 Punkt voneinander abweichen, die Läufe eines Modells um mehr als 1,0 Punkt streuen oder
weniger als zwei gültige Läufe vorliegen. Das trifft auf **{n_unsicher} von {n_berufe} Berufen** zu
({n_provider}× Modell-Abweichung, {n_laeufe}× Streuung der Läufe; Mehrfachnennung möglich). Die Matrix
zeigt sie als Raute, die Berufssuche nennt beide Modellwerte und den Grund.

**Physische Automatisierung separat:** Der Hauptscore misst nur generative KI. Klassische Technik —
Selbstbedienungskassen, Sortieranlagen, Roboter, Regel-Software — zählt bewusst nicht dazu, damit
der Score eine klar umrissene Grösse bleibt. Sie steht als eigene Kennzahl daneben (Treemap, Matrix,
Branchen, Berufssuche).""" + (f""" Beispiel: **{beispiel['occupation']}** haben eine KI-Exposition von nur
**{_f(beispiel['exposure'])}**, aber eine physische Automatisierung von **{_f(beispiel['physical_automation'])}**"""
    + (" — wegen Selbstbedienungskassen und automatischer Zahlung." if beispiel["isco_code"] == "5230" else ".")
    if beispiel is not None else "") + f"""

Beschäftigungsgewichtet liegt die KI-Exposition aller erfassten Erwerbstätigen bei
**{_f(expo_w)} von 10**.

**Kein Lohn- und Branchenzuschlag mehr:** Die frühere Methode verschob den Score je nach Branche
(−0,3 bis +0,4) und Lohnklasse (−0,2 bis +0,4). Beides ist entfallen: Die Tätigkeitsbewertung erfasst
die Unterschiede direkt, und die Branche wirkt nur noch über den Zeitrahmen der Einführung
(KMU-Faktor, unten). Die Expositionswerte sind damit reine Tätigkeitsmasse ohne Zuschläge.
""")

# ─── KMU-Adoptions-Faktor: STATENT-Anteile, Vergleich mit Betriebszählung 2008 ──
# Schwellen wie in src/scoring/kmu_faktor.py (GROSSFIRMEN_SCHWELLE_HOCH / _TIEF)
KMU_SCHWELLE_HOCH, KMU_SCHWELLE_TIEF = 0.50, 0.15
# Bis Oktober 2026 verwendet: BZ 2008, Arbeitsstätten ≥250 VZÄ, Schwellen 0.40 / 0.10
BZ2008_ANTEIL = {
    "Bau": 0.0391, "Beratung": 0.139, "Bildung": 0.119, "Detailhandel": 0.0228,
    "Dienstleistungen": 0.0943, "Finanzen": 0.2799, "Gastgewerbe": 0.0238,
    "Gesundheit": 0.4893, "ICT": 0.3063, "Immobilien": 0.0395, "Industrie": 0.3138,
    "Landwirtschaft": 0.0, "Medien": 0.1702, "Recht": 0.0696, "Sicherheit": 0.3297,
    "Soziales": 0.045, "Transport": 0.2537, "Umwelt": 0.1583, "Versicherungen": 0.4653,
    "Verwaltung": 0.0481, "Öff. Verwaltung": 0.1507,
}


def _verschiebung(anteil: float, hoch: float, tief: float) -> str:
    if pd.isna(anteil):
        return "0"
    if anteil >= hoch:
        return "−1"
    return "+1" if anteil < tief else "0"


def _prozent(wert: float) -> str:
    return "–" if pd.isna(wert) else f"{wert * 100:.1f} %".replace(".", ",")


kmu_df = g.lade_csv(str(g.KMU_PATH))
KMU_JAHR = int(kmu_df["year"].iloc[0]) if kmu_df is not None else "2024"
KMU_MITTEL = (kmu_df["employed_large"].sum() / kmu_df["employed_total"].sum()
              if kmu_df is not None else float("nan"))
KMU_MITTEL_TEXT = "–" if pd.isna(KMU_MITTEL) else f"{KMU_MITTEL * 100:.0f} %"
kmu_vergleich = None
if kmu_df is not None:
    zeilen = [
        f"| Branche | STATENT {KMU_JAHR} (Unternehmen) | Verschiebung | BZ 2008 (Arbeitsstätten) "
        "| Verschiebung bisher | Abdeckung |",
        "|---|---:|:---:|---:|:---:|---:|",
    ]
    for _, r in kmu_df.sort_values("large_firm_share", ascending=False, na_position="last").iterrows():
        alt = BZ2008_ANTEIL.get(r["sector"], float("nan"))
        abdeckung = r.get("coverage", float("nan"))
        zeilen.append(
            f"| {r['sector']} | {_prozent(r['large_firm_share'])} "
            f"| {_verschiebung(r['large_firm_share'], KMU_SCHWELLE_HOCH, KMU_SCHWELLE_TIEF)} "
            f"| {_prozent(alt)} | {_verschiebung(alt, 0.40, 0.10)} "
            f"| {'–' if pd.isna(abdeckung) else f'{abdeckung * 100:.0f} %'} |"
        )
    kmu_vergleich = "\n".join(zeilen)

zeit_vert = ""
if df is not None:
    stufen = ["1-2 Jahre", "3-5 Jahre", "5-10 Jahre", ">10 Jahre"]
    roh, neu = df["timeframe_raw"].value_counts(), df["timeframe"].value_counts()
    zeit_vert = ", ".join(f"{s}: {int(roh.get(s, 0))} → {int(neu.get(s, 0))}" for s in stufen)
    n_verschoben = int((df["timeframe_sme_shift"] != 0).sum())

st.subheader("Zeitrahmen und KMU-Adoptions-Faktor")
st.markdown(f"""
Jede Bewertung schätzt zusätzlich einen **Zeitrahmen**: bis wann die exponierten Tätigkeiten in
mindestens rund einem Drittel der Schweizer Betriebe tatsächlich mit KI erledigt werden
(1–2 / 3–5 / 5–10 / > 10 Jahre). In `timeframe_raw` steht der Median über alle Läufe beider Modelle
(bei Gleichstand der spätere Wert).

Grossunternehmen führen KI in der Regel schneller ein als KMU. Der **KMU-Adoptions-Faktor** verschiebt
den Zeitrahmen deshalb je Branche um eine Stufe — er wirkt auf das **Wann**, nicht auf die Höhe der
Exposition. Das Ergebnis steht in `timeframe`, die Verschiebung in `timeframe_sme_shift`
({n_verschoben if df is not None else 0} Berufe verschoben; Verteilung vorher → nachher: {zeit_vert}).

- **Quelle:** BFS Statistik der Unternehmensstruktur (STATENT) **{KMU_JAHR}**, Tabelle
  [ts-x-06.02.01.01](https://www.bfs.admin.ch/bfs/de/home/statistiken/kataloge-datenbanken.assetdetail.36734598.html) «Marktwirtschaftliche Unternehmen
  nach Wirtschaftsabteilungen und Grössenklasse» (Stand 20.08.2026), automatisch geladen über die
  BFS-DAM-Schnittstelle (`src/data/fetch_statent.py`).
- **Einheit Unternehmen, nicht Arbeitsstätte:** Alle Beschäftigten eines Unternehmens zählen zu
  dessen Haupttätigkeit (NOGA-Abteilung) und Grössenklasse. Das ist der fachlich passende Begriff,
  weil Investitions- und IT-Entscheide auf Unternehmensebene fallen — eine Filiale einer
  Detailhandelskette ist kein KMU.
- **Grösse und Zählgrösse:** Beschäftigte (Personen inkl. Teilzeit). Eine Auswertung nach
  Vollzeitäquivalenten je Wirtschaftsabteilung × Grössenklasse publiziert das BFS nicht.
- **Definition:** Grossfirmen-Anteil = Beschäftigte in Unternehmen mit **≥ 250 Beschäftigten** /
  alle Beschäftigten der NOGA-Abteilungen einer Branche (gleiches NOGA-Mapping wie der
  Grenzgänger-Anteil). Schweizweit (alle marktwirtschaftlichen Unternehmen) {KMU_MITTEL_TEXT}.
- **Schwellen:** ≥ 50 % → **−1 Stufe** (früher) · 15–50 % → neutral · < 15 % → **+1 Stufe** (später).
  Das obere Segment umfasst Branchen, in denen die **Mehrheit** der Beschäftigten in Grossunternehmen
  arbeitet; das untere Segment Branchen mit mindestens **85 % KMU-Beschäftigten** (weniger als rund
  die Hälfte des Landesmittels). Die Grenzen entsprechen etwa dem oberen und unteren Quartil der
  Branchenverteilung (47 % bzw. 15 %) und dem ursprünglichen Entwurf in Issue #33.
  Das obere Ergebnis ist robust (identisch für Schwellen von 45 bis 53 %); knapp über der unteren
  Schwelle liegen Verwaltung/Verbände (15,3 %) und Gastgewerbe (15,5 %), die deshalb neutral bleiben.
- **Grenzen:** Nur **marktwirtschaftliche** Unternehmen. Die öffentliche Verwaltung (NOGA 84) fehlt
  vollständig → kein Anteil, keine Verschiebung. Bei Bildung, Soziales und Verwaltung/Verbänden deckt
  die Tabelle nur einen Teil der Beschäftigten ab (Spalte «Abdeckung»; öffentliche Schulen und
  Sozialdienste fehlen). Nicht-marktwirtschaftliche Einheiten sind schweizweit zu rund 69 % gross
  (≥ 250 Beschäftigte, STATENT {KMU_JAHR}); die Grösse wirkt dort aber nicht über Wettbewerb und
  Investitionsentscheide und wird bewusst nicht verrechnet. Abdeckung über 100 % (z. B.
  Versicherungen) entsteht, weil die Tabelle ganze Unternehmen ihrer Hauptbranche zuordnet,
  STATENT-Arbeitsstätten dagegen nach ihrer eigenen Tätigkeit. Aus Datenschutzgründen gesperrte
  Zellen werden aus der Differenz zum Total geschätzt (Einfluss < 1 Prozentpunkt). Nur 2-stellige
  NOGA; ein Beruf gehört genau einer Branche.
- **Frühere Werte:** Bis Oktober 2026 stammte der Anteil aus der **Betriebszählung 2008**
  (Arbeitsstätten ≥ 250 Vollzeitäquivalente) mit Schwellen 40 % / 10 %. Weil dort jede Filiale
  einzeln zählte, galten Detailhandel (2 %), Gastgewerbe (2 %) oder Soziales (5 %) als fast reine
  KMU-Branchen; der Unternehmensbegriff liefert durchwegs höhere Anteile (Landesmittel 17 % → {KMU_MITTEL_TEXT}),
  daher die neuen Schwellen.
""")
if kmu_vergleich is not None:
    st.markdown(kmu_vergleich)

st.divider()

# ─── Validierung ──────────────────────────────────────────────────────────────
st.header("Validierung: Vergleich mit internationalen Messungen")

BENCH = {
    "ilo25_mean": ("ILO 2025 (Gmyrek et al.)", "Hauptvalidierung: unabhängiger, aufgabenbasierter Index "
                   "der ILO mit eigener Tätigkeitsliste und Bewertung, nativ für die ISCO-08-Berufsgattungen "
                   "(mittlerer Task-Score)."),
    "eloundou_gpt4_beta": ("Eloundou et al. 2024 (β, GPT-4)", "Gleiche Rubrik-Familie (E0/E1/E2) — daher **keine "
                           "unabhängige Prüfung**; die Bewertungen stammen von 2023 (GPT-4, US-Tätigkeiten aus O*NET)."),
    "aei_observed_exposure": ("Anthropic Economic Index, März 2026 (beobachtete Exposition)",
                              "Misst die **tatsächliche Nutzung** von Claude je Tätigkeit, nicht die technische "
                              "Machbarkeit — eine tiefere Übereinstimmung ist zu erwarten."),
}
bench = g.lade_csv(str(g.BENCHMARK_PATH))
if df is not None and bench is not None:
    # je ISCO-4-Code ein Wert (mehrere Einträge eines Codes beschäftigungsgewichtet gemittelt)
    je_code = pd.DataFrame([
        {"isco_code": code, "exposure": g.gewichtet(d, "exposure")} for code, d in df.groupby("isco_code")])
    vergleich = je_code.merge(bench, on="isco_code", how="left")
    zeilen = ["| Benchmark | Spearman ρ | ISCO-Codes | Einordnung |", "|---|:---:|:---:|---|"]
    for spalte, (name, einordnung) in BENCH.items():
        rho, n = g.spearman(vergleich["exposure"], vergleich[spalte])
        zeilen.append(f"| {name} | **{_f(rho, 2)}** | {n} | {einordnung} |")
    st.markdown("\n".join(zeilen))
    st.markdown(f"""
Spearman ρ ist die Rangkorrelation: 1 = gleiche Reihenfolge der Berufe, 0 = kein Zusammenhang.
Grundlage sind die {len(je_code)} ISCO-4-Codes der App (Einträge mit gleichem Code beschäftigungsgewichtet
gemittelt), soweit der Benchmark einen Wert hat (Spalte «ISCO-Codes»); der CH-Sammelcode 7200 hat z. B.
keinen ISCO-08-Gegenwert.

- ρ prüft nur die **Reihenfolge** der Berufe, **nicht das Niveau**: Ein Score von 6 hier entspricht
  nicht einem bestimmten ILO-Wert, und Unterschiede in der Kalibrierung der Rubriken bleiben unsichtbar.
- **Einen Schweizer Benchmark gibt es nicht**; alle Vergleichswerte beruhen auf internationalen bzw.
  US-Tätigkeitsbeschreibungen, die auf CH-ISCO-19 übertragen wurden.
- Lizenzen: ILO-Daten [CC BY 4.0](https://github.com/pgmyrek/2025_GenAI_scores_ISCO08) (Adaption, nicht von
  der ILO geprüft); Eloundou et al. [MIT](https://github.com/openai/GPTs-are-GPTs) mit BLS-Crosswalk (public
  domain); Anthropic Economic Index [CC-BY](https://huggingface.co/datasets/Anthropic/EconomicIndex).
  Details in `data/processed/benchmarks_isco4.README.md`.
""")
else:
    st.info("Benchmark-Datei nicht verfügbar.")

st.subheader("Vergleich mit der früheren Methode")
if df is not None and df["legacy_score"].notna().any():
    alt_neu = df.dropna(subset=["legacy_score"]).assign(diff=lambda d: d["exposure"] - d["legacy_score"])
    rho_alt, n_alt = g.spearman(alt_neu["legacy_score"], alt_neu["exposure"])
    st.markdown(f"""
Bis Oktober 2026 bewertete ein Sprachmodell (Claude Sonnet 4.6) jeden Beruf **als Ganzes** nach fünf
Kriterien (digitaler Output, Wiederholbarkeit, physische Präsenz, Kreativität, soziale Interaktion;
Ansatz von Andrej Karpathy), dazu kamen Branchen- und Lohnzuschläge. Die Rangfolge der beiden
Methoden stimmt nur mässig überein: **Spearman ρ = {_f(rho_alt, 2)}** ({n_alt} Berufe, die damals
bewertet waren). Im Mittel liegt der neue Score tiefer ({_f(alt_neu['exposure'].mean())} statt
{_f(alt_neu['legacy_score'].mean())}), weil er nur die Zeit zählt, die generative KI tatsächlich
mindestens halbiert.
""")
    spalten = {"occupation": "Beruf", "legacy_score": "früher", "exposure": "neu", "diff": "Δ"}
    for titel, auswahl in (("Grösste Rückgänge", alt_neu.nsmallest(6, "diff")),
                           ("Grösste Zunahmen", alt_neu.nlargest(6, "diff"))):
        st.markdown(f"**{titel}**")
        st.dataframe(auswahl[list(spalten)].rename(columns=spalten).round(1), hide_index=True, width="stretch",
                     column_config={"Beruf": st.column_config.TextColumn("Beruf", width="large")})
    st.markdown("""
Δ = neu − früher (Skala 0–10).

**Warum sich die Werte verschieben:** Die alte Methode bewertete «Wiederholbarkeit» hoch — Routine
zählte als Exposition, auch wenn sie körperlich ist. Kassen-, Sortier-, Fahr- und Maschinenberufe
erhielten deshalb hohe Scores, obwohl ein Sprachmodell diese Arbeit nicht erledigt; ihre
Automatisierung durch Selbstbedienung, Sortieranlagen oder Robotik steht jetzt separat in der
**physischen Automatisierung**. Umgekehrt steigen Büro-, Analyse-, Beratungs- und Führungsberufe,
in denen viel Arbeitszeit auf Texte, Berichte, Auswertungen und Korrespondenz entfällt: Die
Tätigkeitsliste macht diese Anteile sichtbar, die eine Gesamtbeurteilung des Berufs oft unterschätzte
(z. B. durch einen Abzug für «soziale Interaktion»). Der alte Score steht als `legacy_score` in den
Daten, wird aber nirgends mehr angezeigt ausser hier.
""")

st.divider()

# ─── Anpassungsfähigkeit ──────────────────────────────────────────────────────
st.header("Anpassungsfähigkeits-Score (0–10)")

st.markdown("""
Der Anpassungsfähigkeits-Score (verwendet in der Matrix-Ansicht) misst, wie leicht
Berufsangehörige sich bei Automatisierungsdruck neu orientieren können.
Er basiert auf der Methodik der **Brookings Institution** und setzt sich zusammen aus:

| Kriterium | Max. Punkte | Quelle |
|---|---|---|
| Qualifikationsniveau | 4 | Bildungsniveau des Berufs (Tertiär 4, Sekundär II 3, keine Ausbildung 1) |
| Lohnniveau | 3 | LSE 2024 (höherer Lohn = mehr Ressourcen für Umschulung); feste Skala: 0 Punkte bis 50'000 CHF, linear bis 3 Punkte bei 150'000 CHF, darüber 3 |
| Branchenmobilität | 1 | Schätzung basierend auf Branchencharakteristika |

Die Summe (höchstens 8 Punkte) wird auf 0–10 skaliert (× 10/8). Skala: 0 = sehr schwer anzupassen,
10 = sehr flexibel.

Die Lohnskala ist fest (Lohnpunkte = 3 × (Lohn − 50'000) / 100'000, begrenzt auf 0–3) und
umschliesst die Spanne der LSE-2024-Mediane der Berufsgruppen (rund 53'000–130'000 CHF).
Die Lohnpunkte eines Berufs hängen damit nur von seinem eigenen Lohn ab — ein einzelner
Ausreisser (z. B. ein neuer Höchstlohn) verschiebt die Werte der übrigen Berufe nicht.
Beispiele: 75'000 CHF → 0.75, 100'000 CHF → 1.5, 125'000 CHF → 2.25 Punkte.

**Kein Kriterium «digitale Affinität» mehr:** Bis Oktober 2026 zählte es 2 Punkte, mit dem
Teilkriterium «digitaler Output» der früheren Bewertung als Proxy. Dieses gibt es nicht mehr; die
KI-Exposition als Ersatz wäre zirkulär — dieselbe Grösse stünde auf beiden Achsen der Matrix, und stark
exponierte Berufe würden automatisch als anpassungsfähiger gelten. Die übrigen Kriterien korrelieren
trotzdem mit der Exposition, weil Büro- und Wissensberufe meist höhere Bildung und Löhne haben.
""")

st.subheader("Kritische Zone: Schwellen und ihre Wirkung")
_schwelle = g.schwelle_anpassung(df)
_varianten = [
    (f"Anpassungsfähigkeit unter dem Median der Erwerbstätigen ({_schwelle:.1f}) — verwendet", _schwelle),
    (f"Anpassungsfähigkeit höchstens {_schwelle:.1f} (Median eingeschlossen)", _schwelle + 1e-9),
    (f"Anpassungsfähigkeit unter {g.SCHWELLE_ANPASSUNG_FEST:g} (feste Schwelle)", g.SCHWELLE_ANPASSUNG_FEST),
    ("Anpassungsfähigkeit unter 6 (feste Schwelle)", 6.0),
]
_zeilen = []
for _name, _s in _varianten:
    _k = g.kritische_zone(df, _s)
    _zeilen.append({"Abgrenzung (jeweils KI-Exposition > 6)": _name, "Berufe": len(_k),
                    "Erwerbstätige (Tsd.)": round(_k["employed_k"].sum()),
                    "Frauenanteil": g.prozent(g.gewichtet(_k, "women_pct")) if not _k.empty else "–"})
st.markdown(f"""
Die kritische Zone umfasst Berufe mit hoher KI-Exposition (Score > {g.SCHWELLE_EXPOSITION:g}) und
unterdurchschnittlicher Anpassungsfähigkeit. «Unterdurchschnittlich» ist relativ definiert: unter dem
beschäftigungsgewichteten Median aller Berufe ({_schwelle:.1f}), d. h. die Hälfte der Erwerbstätigen
arbeitet in Berufen mit tieferem Wert. Eine feste Zahl wäre willkürlicher, weil die Lage der Skala von
der Zusammensetzung der Kriterien abhängt.

Das Ergebnis reagiert stark auf diese Wahl — die Zone ist eine Lesehilfe, keine scharfe Grenze:
""")
st.dataframe(pd.DataFrame(_zeilen), hide_index=True, width="stretch")


st.divider()

# ─── Datenquellen ─────────────────────────────────────────────────────────────
st.header("Datenquellen")

st.subheader("Beschäftigungsdaten")
st.markdown(f"""
Die Beschäftigungszahlen und Frauenanteile stammen aus der offiziellen Schweizer Statistik:

- **Quelle:** Bundesamt für Statistik (BFS)
- **Erhebung:** Strukturerhebung (SE) 2024 (Stichprobenerhebung im Rahmen der jährlichen Volkszählung)
- **Tabelle:** *Ausgeübter Beruf (CH-ISCO-19) nach Geschlecht und Staatsangehörigkeit*
  (su-d-40.02.03.02.01.03.10, Blatt «2024»)
- **Download:** [bfs.admin.ch](https://www.bfs.admin.ch/bfs/de/home/statistiken/kataloge-datenbanken.assetdetail.36492006.html)
- **Einheit:** Erwerbstätige ab 15 Jahren, in 1'000 Personen
- **Grundgesamtheit:** Ständige Wohnbevölkerung in Privathaushalten — Grenzgänger/-innen
  sind nicht enthalten
- **Klassifikation:** CH-ISCO-19 (basiert auf ISCO-08), Ebene Berufsgattung (4-stellig);
  wo nötig Berufsart (5-stellig)

Die App umfasst **{n_berufe} Berufe** mit zusammen **{summe_text} Tsd.** Erwerbstätigen
(**{abdeckung_text}** der SE 2024 total: 4'584 Tsd.); alle sind aufgabenbasiert bewertet. Automatisch ergänzt wurden
Berufsgattungen mit mindestens **5'000 Erwerbstätigen** — ohne Restgruppen («onA» = ohne nähere
Angaben, «anderweitig nicht genannt»), ausser sie sind gross und inhaltlich klar (4419 Bürokräfte
a.n.g. = v. a. Verkaufsinnendienst, 9329 Hilfsarbeiter in der Produktion a.n.g.).

**Keine Doppelzählung:** Jede 4-stellige Berufsgattung zählt genau einmal mit ihrem SE-Wert.

- In der Regel entspricht ein Beruf einer Berufsgattung und erhält deren vollen Wert.
- Teilen sich mehrere Berufe eine Gattung, wird sie über die **5-stelligen Berufsarten** der SE
  aufgeteilt: 2330 Lehrkräfte im Sekundarbereich → Sekundarstufe I / Sekundarstufe II,
  5131 Service in Restaurants → Servicefachkräfte (inkl. Chefs de Service) / Servicehilfskräfte,
  5223 Verkäufer → Verkäufer in Handelsgeschäften / Drogisten. Der nicht zugeordnete Rest der
  Gattung (Berufsart «onA» = ohne nähere Angaben, nicht publizierte Kleinstwerte) wird
  proportional verteilt.
- Wo die SE die Berufe nicht trennt (z. B. Detailhandelsfachleute EFZ und Verkäufer/innen ohne
  Ausbildung, Softwareentwickler/innen und Informatiker/innen EFZ), sind sie zu **einem Eintrag
  mit der SE-Bezeichnung zusammengelegt** ({n_zusammen} Einträge aus {n_titel} bisherigen Titeln).
  Die bisherigen Titel bleiben in der Berufssuche als Synonyme auffindbar. Diese Einträge sind
  als Ganzes aufgabenbasiert bewertet.
- Die Zuordnung Beruf → Berufsgattung/Berufsart(en) ist mit Begründung versioniert
  (`data/processed/beruf_berufsart_mapping.csv`). Die ISCO-Codes aller Berufe wurden gegen die
  CH-ISCO-19-Bezeichnungen geprüft und, wo eindeutig falsch, korrigiert (z. B. Koch/Köchin EFZ:
  3434 Küchenchefs → 5120 Köche; Audit in `docs/audit_isco_codes.md`).
- Ist eine Gattung im Jahresblatt 2024 nicht publiziert (< 5 Beobachtungen), gilt der Wert der
  gepoolten Jahre 2022–2024; ebenso für den Frauenanteil.
- **Einschränkung:** Bei einigen Berufen ist der Titel enger als die Berufsgattung, deren vollen
  Wert sie tragen (z. B. Notar/in = Gattung «Juristen, anderweitig nicht genannt»,
  Zimmermann/-frau = Gattung inkl. Schreiner).
""")

st.subheader("Berufsbeschreibungen")
st.markdown(f"""
Für die Bewertung benötigt jeder Beruf eine inhaltliche Beschreibung seiner Kerntätigkeiten.
Die Beschreibungen werden in einem mehrstufigen Prozess ermittelt:

| Stufe | Quelle | Berufe |
|---|---|---|
| 1–3 | ESCO (Textsuche Deutsch/Englisch, Berufe der ISCO-Gruppe) | {n_esco} von {n_berufe} |
| 4 | berufsberatung.ch (Fallback bei keinem ESCO-Treffer) | {n_bb} |
| 5 | Wikipedia (zweiter Fallback) | {n_wiki} |
| 6 | KI-generierte Beschreibung (letzter Ausweg) | {n_fallback} |

Die verwendete Quelle ist in der Spalte `description_source` gespeichert und
wird bei der Berufssuche angezeigt.

**Match-Qualität** (Spalte `esco_match_quality`): Ein ESCO-Beruf wird nur übernommen, wenn
seine ISCO-Gruppe zum ISCO-Code des Berufs passt.

- **korrekt** ({n_korrekt}): gleiche 4-stellige ISCO-Gruppe, der ESCO-Beruf deckt die Tätigkeit ab
- **plausibel** ({n_plausibel}): gleiche 3-stellige Gruppe, dokumentierte Ausnahme (z. B. ESCO hat
  keinen Beruf für «Fachkräfte Gesundheit und Pflege», 3221) oder nur ein Teilgebiet des Berufs
- **fallback** ({n_fallback + n_bb + n_wiki}): kein passender ESCO-Beruf, eigene Beschreibung

Alle Zuordnungen wurden im Oktober 2026 geprüft und, wo falsch, korrigiert (vorher u. a.
«Dipl. Pflegefachperson» → Diplomat/in); Details in `docs/audit_esco_zuordnungen.md`.
Für jeden Beruf mit ESCO-Zuordnung sind zudem die ESCO-Kompetenzen (wesentlich/optional)
in `data/processed/esco_kompetenzen.csv` abgelegt; die wesentlichen Kompetenzen vom Typ «skill» sind
die wichtigste Grundlage der Tätigkeitsliste jedes Berufs.

- **ESCO:** [esco.ec.europa.eu](https://esco.ec.europa.eu/de/use-esco/esco-api), Version 1.2.1
  (API mit fester Version und CSV-Download)
- **Lizenz:** ESCO © Europäische Union, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/);
  Beschreibungen ggf. gekürzt/angepasst
- **Sprache:** Deutsch
""")

st.subheader("Lohndaten")
st.markdown("""
Der mediane Jahresbruttolohn (`wage_median_chf`) stammt aus der **BFS Lohnstrukturerhebung
(LSE) 2024**. Die Herkunft jedes Werts steht in der Spalte `wage_source`. Der Lohn geht nur in die
Anpassungsfähigkeit ein, nicht in die Exposition.

- **Quelle:** BFS, LSE 2024, Tabelle T17 «Monatlicher Bruttolohn (Zentralwert) nach
  Berufsgruppen, Lebensalter und Geschlecht — Privater und öffentlicher Sektor zusammen»
  (publiziert 2026). Die LSE weist Berufe nur **2-stellig** aus (CH-ISCO-19-Untergruppen).
- **Basis (`LSE2024_2d`):** Median der 2-stelligen Gruppe × 12. Der LSE-Wert ist ein
  standardisierter Vollzeit-Monatslohn und enthält bereits 1/12 des 13. Monatslohns und der
  Sonderzahlungen; deshalb × 12 und nicht × 13. Alle Berufe einer Gruppe erhalten zunächst
  denselben Lohn.
- **Fallback:** Für Gruppen ohne LSE-Wert (Armee 01–03, Selbstversorgung 63, Strassenhandel 95)
  gilt die 1-stellige Hauptgruppe (`LSE2024_1d`) bzw. der Gesamtmedian (`LSE2024_total`).
  Derzeit betrifft das keinen Beruf der App.
- **Heterogene Gruppen (`LSE2024_2d+Salarium`):** In den Gruppen 11–14 (Führungskräfte),
  22 (Gesundheitsberufe), 24 (Betriebswirtschaft, Finanzen) und 26 (Recht, Soziales, Kultur)
  liegen Berufe mit sehr unterschiedlichen Löhnen zusammen (z. B. Ärzte und Pflege).
  Hier wird der Gruppenmedian mit dem **BFS-Lohnrechner Salarium** (Modell auf Basis der
  LSE 2024) nach Ausbildung und Branche differenziert:

  *Lohn(Beruf j) = LSE-Gruppenmedian × 12 × S(j) / S̄(Gruppe)*

  *S̄(Gruppe) = Σ w(k)·S(k) / Σ w(k)* über alle Berufe k der Gruppe mit Salarium-Wert,
  *w(k)* = Beschäftigte (BFS SE 2024)

  - **S(j):** Salarium-Median für das Profil des Berufs — formale Pflichtausbildung
    (z. B. Medizinstudium, Pflege HF, Anwaltspatent) und NOGA-Abteilung der Hauptbranche,
    festgehalten mit Begründung in `data/processed/lohn_profile_salarium.csv`.
  - **Normprofil (für alle gleich):** 42 Jahre, 8 Dienstjahre, 40 Stunden, ohne Kaderfunktion,
    ohne Sonderzahlungen, Unternehmen ab 50 Beschäftigten.
  - **Normierung:** Das beschäftigungsgewichtete Mittel der Löhne einer Gruppe entspricht
    genau dem LSE-Gruppenmedian × 12. Salarium verteilt also nur innerhalb der Gruppe um
    (nach Ausbildung und Branche); das Lohnniveau stammt immer aus der LSE.
    Führungskräfte (in Salarium eine Gruppe 11–14) werden je LSE-Gruppe 11, 12, 13, 14 normiert.
  - **Regionen:** Salarium rechnet je Grossregion. Verwendet wird das Mittel über die
    7 Grossregionen, gewichtet mit den Vollzeitäquivalenten der jeweiligen Branche
    (BFS STATENT 2024).

  Die Werte sind **Modellschätzungen**, keine erhobenen Berufslöhne.
  Ausnahme: Für leitende Verwaltungsbedienstete (öffentliche Verwaltung) liefert Salarium
  keine Werte; sie erhalten den LSE-Gruppenmedian und zählen nicht in die Normierung.
- **Verhältniszahlen (`LSE2024_2d+Verhaeltnis`, Gruppe 22):** Wo eine belegte Relation zum
  LSE-Gruppenmedian vorliegt, ersetzt sie nach der Salarium-Kalibrierung den Salarium-Wert:
  *Lohn = Faktor × LSE-Gruppenmedian × 12* (Tabelle unten, `data/processed/lohn_verhaeltnisse.csv`).
  Grund: In der stark rechtsschiefen Gruppe 22 drückt die Normierung «Mittel = Median» alle Werte
  nach unten (Pflege vorher 89'800 statt belegter ~94'800 CHF, Ärzte nur 109'900 CHF).
  Die übrigen Berufe der Gruppe werden **ohne** die Override-Berufe normiert
  (ihr gewichtetes Mittel = Gruppenmedian), damit ein Override ihre Löhne nicht verschiebt.
  Die Werte sind **Schätzungen**; das Band zeigt die plausible Spannweite.
  Zahnärzte und Apotheker haben keine belegte Relation, behalten den Salarium-Wert und sind
  als **unsicher** markiert (Spalte `wage_uncertain`).
- **Einschränkungen:** nur 2-stellige LSE-Gruppen (eine 3-/4-stellige Auswertung wäre nur
  als kostenpflichtige BFS-Sonderauswertung erhältlich); Salarium bildet nur den
  **Privatsektor** ab; Spitzenlöhne werden unterschätzt (siehe «Einschränkungen & Hinweise»);
  **Selbständige** (z. B. Ärzte mit eigener Praxis, Anwälte, Landwirte) sind in der LSE
  nicht enthalten.
""")

# ─── Verhältniszahlen Gruppe 22 (aus lohn_verhaeltnisse.csv) ──────────────────
VERH_PATH = DATA_PATH.parent / "lohn_verhaeltnisse.csv"
LSE_PATH = DATA_PATH.parent / "lse2024_monatslohn_isco.csv"


@st.cache_data
def load_verhaeltnisse() -> pd.DataFrame | None:
    if not VERH_PATH.exists() or not LSE_PATH.exists():
        return None
    verh = pd.read_csv(VERH_PATH, dtype={"isco_code": str})
    lse = pd.read_csv(LSE_PATH, dtype={"isco_prefix": str}, keep_default_na=False)
    lse = dict(zip(lse["isco_prefix"], pd.to_numeric(lse["median_monthly"], errors="coerce")))
    basis = verh["isco_code"].str[:2].map(lse) * 12

    def _chf(x: pd.Series) -> pd.Series:
        return x.map(lambda v: "" if pd.isna(v) else f"{round(v, -2):,.0f}".replace(",", "'"))

    lohn = verh["factor_to_lse_group"] * basis
    band = _chf(verh["band_low"] * basis) + " – " + _chf(verh["band_high"] * basis)
    scores = pd.read_csv(DATA_PATH, dtype={"isco_code": str}) if DATA_PATH.exists() else None
    if scores is not None:  # ohne Faktor: Salarium-Wert aus scores.csv
        salarium = verh.merge(scores[["isco_code", "occupation", "wage_median_chf"]],
                              on=["isco_code", "occupation"], how="left")["wage_median_chf"]
        sal_text = _chf(salarium.astype(float)).map(lambda t: f"{t} (Salarium)" if t else "Salarium")
    else:
        sal_text = pd.Series("Salarium", index=verh.index)
    lohn_text = _chf(lohn).where(lohn.notna(), sal_text)
    return pd.DataFrame({
        "ISCO": verh["isco_code"],
        "Beruf": verh["occupation"],
        "Faktor": verh["factor_to_lse_group"].map(lambda v: "–" if pd.isna(v) else f"{v:.3f}"),
        "Lohn (CHF/Jahr)": lohn_text,
        "Band (CHF/Jahr)": band.where(verh["band_low"].notna(), "–"),
        "Unsicher": verh["wage_uncertain"].map({True: "ja", False: "nein"}),
        "Bemerkung": verh["note"].fillna(""),
    })


verh_tab = load_verhaeltnisse()
if verh_tab is not None and not verh_tab.empty:
    st.markdown("**Verhältniszahlen Gruppe 22 (Schätzung, Faktor × LSE-Gruppenmedian 96'000 CHF)**")
    st.dataframe(verh_tab, hide_index=True)
    st.markdown("""
- **Dipl. Pflege (0.987):** BFS-LSE-2018-Spezialauswertung für das BAG (Asset 19087994):
  diplomierte/spezialisierte Pflegefachkraft 7'429 CHF vs. Median Gruppe 22 7'526 CHF.
  Annahme: Die Relation gilt auch 2024.
- **Ärzte gesamt ≈ 1.6 × dipl. Pflege (Band 1.3–1.9):** BFS Krankenhausstatistik 2018–2022,
  Lohnaufwand pro VZÄ Ärzteschaft ÷ Pflegepersonal 2.03–2.07 (Mittelwerte, nur Spitäler),
  umgerechnet auf 40 h (Sollstunden 2'340 vs. 2'100), ohne Unterassistenten, auf dipl. Pflege
  und als Median (1.53–1.77); unabhängig gestützt durch eine Zerlegung der LSE-2024-Perzentile
  der Gruppe 22 (1.57–1.87). Eine Lohnskala allein (Assistenz-/Oberärzte) ergäbe 1.13–1.31
  (Untergrenze).
- **Aufteilung Allgemeinmedizin/Fachärzte:** BASS (2018) für das BAG zeigt für angestellte
  Fachärzt/innen 2014 Grundversorgung/Spezialisten ≈ 0.69; wegen der Assistenzärzte in beiden
  Gruppen ist 0.85 **angenommen**. Das beschäftigungsgewichtete Mittel (SE 2024) der beiden
  Faktoren entspricht 1.6 × Pflege.
- **Grenzen:** Spital-lastig; angestellte Praxisärzte und Selbständige fehlen; das Band der
  Fachärzte überspannt 150'000 CHF, die Obergrenze der Lohnpunkte in der Anpassungsfähigkeit. Präzise wäre nur eine LSE-Sonderauswertung
  der 3-Steller 221/222/226.
""")

st.subheader("Branchenzuordnung")
st.markdown("""
Jeder Beruf ist einer von 21 internen Branchen zugeordnet (Grundlage für KMU-Faktor,
Branchenmobilität und Branchenanalyse):

- **Kuratierte Berufe** (Kernliste): Branche manuell gesetzt.
- **Ergänzte BFS-SE-Berufe:** Zuordnung über den ISCO-Code, wobei der **spezifischste Präfix**
  gilt (4-stellig vor 3-stellig vor 2-stellig). So werden heterogene Gruppen wie die
  Führungskräfte (ISCO 13/14) nach Wirtschaftszweig aufgeteilt — z. B. Produktionsleitung →
  Industrie, Bau → Bau, ICT-Dienstleistungen → ICT, Bildungswesen → Bildung, Finanzdienstleistungen
  → Finanzen, Hotels/Restaurants → Gastgewerbe, Handel → Detailhandel.
- Die Abgrenzung orientiert sich an der NOGA-Zuordnung der Grenzgänger- und KMU-Daten
  (z. B. Grosshandel → Dienstleistungen, Heime → Soziales).
- **Limitation:** Ein Beruf wird genau einer Branche zugeordnet, auch wenn er in mehreren
  Wirtschaftszweigen ausgeübt wird (z. B. Einkäufer, Kranführer).
""")

st.subheader("Grenzgänger-Anteil (Kontext)")
st.markdown("""
Der Grenzgänger-Anteil pro Branche dient als zusätzlicher Kontext-Layer in der Branchenanalyse.

- **Zähler:** BFS Grenzgängerstatistik (GGS), Dataflow [`DF_GGS_4`](https://stats.swiss/vis?lc=de&df[ds]=ds%3Adisseminate&df[id]=DF_GGS_4&df[ag]=CH1.GGS&df[vs]=1.0.0&dq=..Q&lom=LASTNPERIODS&lo=5) —
  „Ausländische Grenzgänger/-innen nach Wirtschaftszweig und Erwerbsstatus" (Datenquelle ZEMIS/AHV),
  automatisch über die SDMX-Schnittstelle von stats.swiss geladen (`src/data/fetch_bgs.py`).
  Verwendet wird das **Jahresmittel 2025** (Mittel der vier Quartale, Erwerbsstatus total);
  die BFS-Werte ab 2024-Q3 sind **provisorisch**. Neuestes Quartal (2026-Q2) zum Vergleich in
  `grenzgaenger_anteil_branche.csv`. Gezählt werden Personen mit ausländischer
  Staatsangehörigkeit (Grenzgängerbewilligung), keine Vollzeitäquivalente.
- **Nenner:** BFS STATENT 2024 ([px-x-0602010000_101](https://www.pxweb.bfs.admin.ch/pxweb/de/px-x-0602010000_101/-/px-x-0602010000_101.px/),
  Stand 20.08.2026, Referenzmonat Dezember), Beobachtungseinheit «Beschäftigte», Schweiz total.
  STATENT ist **arbeitsortbasiert** und erfasst Beschäftigte über den AHV-pflichtigen Lohn
  (≥ 2'300 CHF/Jahr) — **Grenzgänger/-innen sind im Nenner enthalten**.
- **Definition:** Anteil Grenzgänger an den Beschäftigten der Branche =
  Σ Grenzgänger/-innen der NOGA-Abteilungen einer Branche / Σ STATENT-Beschäftigte derselben
  Abteilungen. Schweizweit rund 7 %.
- **Granularität:** NOGA-Wirtschaftsabteilungen (2-stellig), aggregiert auf die 21 internen Branchen
  (gleiches Mapping wie der KMU-Faktor). NOGA 97–99 (private Haushalte, exterritoriale
  Organisationen; rund 4'900 Grenzgänger/-innen) fehlen in STATENT und bleiben aussen vor.
- **Wichtig: fliesst weder in die Exposition noch in den Zeitrahmen ein** — rein additiver Kontext-Layer
- **Limitationen:** Kein Pro-Beruf-Mapping möglich; Zähler (2025) und Nenner (2024) liegen ein
  Jahr auseinander, bei leicht wachsendem Grenzgängerbestand ist der Anteil daher eher etwas zu
  hoch. STATENT zählt Personen mit Verträgen bei mehreren Unternehmen mehrfach, die GGS zählt
  Personen. Grenzgänger/-innen mit Schweizer Pass sind im Zähler nicht enthalten.
- **Frühere Werte:** Bis Oktober 2026 wurde der Anteil mit dem Nenner der Betriebszählung 2008
  berechnet (rund 4,2 statt 5,7 Mio. Beschäftigte); die Anteile lagen dadurch je nach Branche bis
  gut 7 Prozentpunkte zu hoch.
""")


st.divider()

# ─── Beobachtete Wirkung ──────────────────────────────────────────────────────
st.header("Was wir über die tatsächliche Wirkung wissen (Stand Oktober 2026)")

st.markdown("""
Die Scores dieser App messen die **Exposition**, also was generative KI technisch beschleunigen *könnte*.
Ob und wie stark sich das bereits auf dem Arbeitsmarkt zeigt, ist eine andere Frage.
Hier ist zusammengefasst, was die Forschung bisher beobachtet. Schweizer Zahlen und
internationale Befunde sind bewusst getrennt: Arbeitsmärkte, Daten und Definitionen
unterscheiden sich zu stark, als dass sich ausländische Zahlen auf die Schweiz übertragen liessen.
""")

st.subheader("Schweiz (Zahlen)")
st.markdown("""
- **KOF/ETH — Arbeitslosigkeit und Stelleninserate** (Kläui & Siegenthaler, Okt. 2025):
  Die Zahl der Arbeitslosen stieg in stark KI-exponierten Berufen um **bis zu 27 %** stärker
  als in wenig exponierten.
  *Definition:* 20- bis 49-Jährige, Sept. 2024 bis Aug. 2025 gegenüber Herbst 2022; oberstes vs.
  unterstes Drittel der Berufe nach dem Expositionsmass von Eloundou et al.
  Die Stelleninserate (Daten x28) in exponierten Berufen lagen zuletzt rund **38 %** tiefer
  (relativ zu wenig exponierten Berufen).
  *Einschränkung:* kein Kausalnachweis. Die Inserate in exponierten Berufen entwickelten sich
  laut den Autoren bereits **2020** signifikant schwächer, also vor ChatGPT.
- **EY AI Survey 2026** (Mai 2026): Von **604 Befragten** (Personen, nicht Firmen) geben
  **7 %** an, ihr Unternehmen habe wegen KI Stellen abgebaut, **11 %**, Stellen würden wegen KI
  nicht mehr nachbesetzt, und **18 %**, es seien neue KI-Stellen entstanden; **42 %** können es
  nicht einschätzen. **18 %** erwarten künftig einen Abbau.
  *Einschränkung:* nicht repräsentativ (23 % aus Banken, 55 % aus Firmen mit ≥ 1'000 Mitarbeitenden).
- **jobs.ch KI Report 2026** (JobCloud, Juni 2026): Der Anteil der Inserate für Berufseinsteiger
  sank im **Gesamtmarkt** 2025 um **32 %** gegenüber dem Durchschnitt 2019–2022.
  In den KI-exponierten Kategorien (IT, Administration/HR, Banking, Marketing, Einkauf, Vertrieb)
  weist der Report für Junior-Inserate **−16 %** und für Senior-Inserate **+26 %** aus.
  *Einschränkung:* Inserate einer Plattform, keine Einstellungen; keine Werte je Kategorie.
  Die −32 % beziehen sich auf den Gesamtmarkt, nicht auf KI-exponierte Berufe — so werden sie in
  einzelnen Sekundärquellen falsch wiedergegeben. Der Report-Text spricht von einem «weitaus
  stärkeren» Rückgang in exponierten Berufen; die ausgewiesenen Werte belegen das nicht eindeutig.
- **AXA KMU-Arbeitsmarktstudie 2026** (Sotomo, Befragung März 2026): **12 %** der KMU, die KI
  nutzen, erwarten, dank KI auf Personal verzichten zu können.
  *Einschränkung:* Erwartung, keine gemessene Entwicklung; N = 336 KMU.
- **einstAIn / Angestellte Schweiz** (Juni 2026): **28 %** der Schweizer Jobs gelten als
  hoch exponiert.
  *Einschränkung:* Wie diese App eine Expositionsschätzung, keine Wirkungsmessung; der
  Schwellenwert für «hoch exponiert» ist nicht dokumentiert.
- **HSLU AI Jobs Report 2026** (Okt. 2026): Ergänzende Perspektive auf die Gegenbewegung —
  die Nachfrage nach KI-Fachkräften in Stelleninseraten wächst, vor allem für erfahrene Profile.

**Zwischenfazit Schweiz:** In stark exponierten Berufen ist ein überdurchschnittlicher Anstieg
der Arbeitslosigkeit messbar (KOF). Befragungen deuten darauf hin, dass dies weniger über breite
Entlassungen als über **Nicht-Nachbesetzung** und **weniger Einstiegsstellen** geschieht.
Ein kausaler Nachweis fehlt.
""")

st.subheader("International (nur qualitativ — Zahlen nicht auf die Schweiz übertragbar)")
st.markdown("""
- **Stanford «Canaries in the Coal Mine?»** (Brynjolfsson, Chandar & Chen, Rev. Aug. 2026):
  In den USA entwickelt sich die Beschäftigung junger Berufseinsteiger in stark exponierten Berufen
  schwächer. Die Wirkung läuft über **weniger Einstellungen junger Beschäftigter**, nicht über
  Entlassungen — vor allem dort, wo KI Tätigkeiten automatisiert statt ergänzt. Beschreibend,
  nicht kausal.
- **Federal Reserve Bank of New York** (Unternehmensumfragen 2025/26): Firmen nutzen KI
  zunehmend, reagieren aber eher mit **Umschulung und weniger Neueinstellungen** als mit
  Entlassungen.
- **The Budget Lab at Yale** (Tracker, Update Sept. 2026): Gesamtwirtschaftlich gibt es in den USA
  bisher **keine klare Evidenz** für eine Verdrängung durch KI.
- **Oxford Economics** (Jan. 2026): Die Belege für einen KI-getriebenen Umbruch sind lückenhaft.
  Manche Firmen stellen Stellenabbau als positive KI-Story dar
  («dress up layoffs as a good news story»).
- **Economic Innovation Group** (Iscenko & Curto Millet, Jan. 2026): Die Inserate in exponierten
  Berufen erreichten ihren Höchststand bereits im Frühjahr 2022, also **vor ChatGPT** — ein
  Hinweis, dass der spätere Rückgang nicht allein auf KI zurückgeht.
""")

st.divider()

# ─── Kündigungsgründe ─────────────────────────────────────────────────────────
st.header("Warum wir keine Kündigungsgründe zählen")

st.markdown("""
Naheliegend wäre, Entlassungen zu zählen, die mit KI begründet werden. Das ergibt aus mehreren
Gründen kein verlässliches Bild:

- **Verdeckte KI-Effekte:** Ein grosser Teil der Wirkung taucht in keiner Kündigung auf —
  Stellen werden nicht nachbesetzt, Einstellungen gestoppt oder Abbau wird unter
  «Restrukturierung» oder «Kostendruck» kommuniziert.
- **KI als vorgeschobener Grund:** Umgekehrt wird KI mitunter genannt, obwohl andere Ursachen
  dahinterstehen (Nachfragerückgang, Überanstellung) — gegenüber Investoren klingt KI besser.
  In den Medien wird dies als «AI washing» bezeichnet.
- **Keine Schweizer Statistik:** Für die Schweiz gibt es keine Statistik der Kündigungsgründe.
  Die oft zitierten US-Zahlen (Challenger, Gray & Christmas) beruhen auf Selbstangaben der
  Unternehmen in Abbauankündigungen.

**Unser Ansatz:** Statt Gründe zu zählen, soll die Wirkung über **Ergebnisse je Beruf** gemessen
werden — z. B. die Entwicklung der Arbeitslosen und Stellensuchenden sowie der Einstiegsinserate,
jeweils exponierte im Vergleich zu wenig exponierten Berufen. Das erfasst KI-Effekte unabhängig
davon, welcher Grund genannt wird. Dafür sind nicht-öffentliche SECO-Daten nach CH-ISCO-19
(4-stellig) nötig; der Datenbezug ist **in Abklärung** (Issue #43).
""")

st.divider()

# ─── Einschränkungen ──────────────────────────────────────────────────────────
st.header("Einschränkungen & Hinweise")

st.markdown("""
- **KI-Bewertung ist keine exakte Wissenschaft.** Die Scores sind Einschätzungen zweier
  Sprachmodelle nach einer festen Rubrik, keine empirisch gemessenen Werte. Auch die Tätigkeitslisten
  und Zeitanteile sind modellgeneriert (aus ESCO und Berufswissen), nicht erhoben. Die Scores sollten
  als Orientierung, nicht als Prognose verstanden werden; unsichere Bewertungen sind markiert.
- **Stand der Technik Oktober 2026.** Die Rubrik bewertet, was heute kommerziell verfügbare
  generative KI kann; mit neuen Modellen und Werkzeugen können Tätigkeiten von E0 zu E1/E2 wechseln.
- **Exposition ≠ Jobverlust.** Ein hoher Score bedeutet, dass generative KI einen grossen Teil der
  Arbeitszeit beschleunigen *könnte* – nicht dass Jobs verschwinden; in den meisten Berufen überwiegt
  der Modus «delegierend» (der Mensch prüft jede Ausgabe). Viele Berufe wandeln sich.
  **Exposition** beschreibt die technische Möglichkeit; die **beobachtete Wirkung** ist die
  tatsächlich gemessene Entwicklung auf dem Arbeitsmarkt. Beides sind getrennte Grössen.
  Bisher wirkt KI in der Schweiz nach heutigem Wissensstand vor allem über **weniger
  Einstiegsstellen** und **Nicht-Nachbesetzung**, weniger über breite Entlassungen
  (siehe «Was wir über die tatsächliche Wirkung wissen»).
- **Datenbasis 2024.** Die Beschäftigungszahlen basieren auf der BFS Strukturerhebung (SE) 2024
  (Stichprobe; Werte kleiner Berufe sind entsprechend unsicher). Die KI-Landschaft
  verändert sich schnell; Bewertungen können in 1–2 Jahren bereits überholt sein.
- **ESCO-Matching nicht immer perfekt.** Für einige Schweizer Berufsbezeichnungen existiert
  kein exakter ESCO-Eintrag. Dann wurde ein ISCO-konsistenter, nahe verwandter Beruf verwendet
  (Match-Qualität «plausibel») oder eine eigene Beschreibung («fallback»). Die Zuordnungen wurden
  im Oktober 2026 korrigiert; die Bewertungen beruhen auf den korrigierten Beschreibungen und
  Kompetenzen (jede Bewertung ist über einen Hash an ihre Eingabedaten gebunden).
- **Löhne sind Gruppenwerte bzw. Modellschätzungen.** Die LSE 2024 weist nur 2-stellige
  Berufsgruppen aus (Median). Alle Berufe einer Gruppe haben deshalb denselben Lohn — ausser in
  den Gruppen 11–14, 22, 24 und 26, wo er mit Salarium-Profilen (Ausbildung, Branche)
  differenziert wird; für Pflege und Ärzte (Gruppe 22) gelten geschätzte Verhältniszahlen.
  Berufsindividuelle Löhne wurden nicht erhoben; Selbständige fehlen in der LSE, Salarium deckt
  nur den Privatsektor ab. Zahnärzte und Apotheker: Lohn unsicher (keine belegte Relation).
- **Spitzenlöhne (Kader, Private Banking, Kanzleien) werden unterschätzt:**
  Salarium kennt keine Kaderzuschläge, und das Normprofil enthält keine Kaderfunktion.
  Ärztelöhne sind seit Oktober 2026 über Verhältniszahlen geschätzt (Band ±20 %).
  Präzisere Werte erfordern eine BFS-Sonderauswertung der LSE auf 3-/4-stelliger Ebene.
""")

st.subheader("Weitere CH-spezifische Faktoren (nicht in den Score eingeflossen)")
st.markdown("""
Folgende Faktoren beeinflussen die KI-Exposition im Schweizer Kontext, sind aber in der
aktuellen Berechnung **nicht berücksichtigt**:

- **Sprachregionen:** Die verwendete SE-Tabelle ist nicht nach Sprachregion × Beruf aufgeschlüsselt.
  Deutschschweiz, Romandie und Tessin können strukturell unterschiedliche Expositionsmuster
  aufweisen.
- **Kantonale/regionale Lohnunterschiede:** Die LSE-Lohndaten sind national aggregiert
  (Salarium-Verhältnisse als gewichtetes Mittel der Grossregionen).
  Regionale Lohndisparitäten (z.B. Zürich vs. Wallis) fliessen nicht in die Anpassungsfähigkeit ein.
- **KMU-Adoptionsgeschwindigkeit:** Kleine und mittlere Unternehmen (KMU, > 99 % der CH-Firmen)
  adoptieren KI-Technologien typischerweise langsamer als Grossunternehmen. Der KMU-Adoptions-Faktor
  (BFS STATENT, siehe oben) bildet das nur grob ab: ±1 Zeitrahmen-Stufe je Branche, ohne
  Unterschiede innerhalb einer Branche und ohne den nicht-marktwirtschaftlichen Sektor.
- **Grenzgänger-Effekte:** Der Schweizer Arbeitsmarkt weist einen hohen Grenzgängeranteil auf.
  Grenzgänger konzentrieren sich auf bestimmte Branchen und Regionen; KI-Exposition dieser
  Gruppe kann vom inländischen Muster abweichen. Der Grenzgänger-Anteil je Branche (BFS GGS 2025 /
  STATENT 2024) wird in der Branchenanalyse nur als Kontext gezeigt, nicht im Score verrechnet.
""")

st.divider()

# ─── Referenzen ───────────────────────────────────────────────────────────────
st.header("Referenzen")

st.markdown("""
- Eloundou, T., Manning, S., Mishkin, P. & Rock, D. (2024). [GPTs are GPTs: Labor market impact potential of LLMs](https://doi.org/10.1126/science.adj0998), *Science* 384 — Rubrik E0/E1/E2 · [Daten](https://github.com/openai/GPTs-are-GPTs)
- Gmyrek, P. et al. (2025). *Generative AI and Jobs: A Refined Global Index of Occupational Exposure*, ILO Working Paper 140 · [Daten](https://github.com/pgmyrek/2025_GenAI_scores_ISCO08)
- Massenkoff, M. & McCrory, P. (März 2026). Anthropic Economic Index — beobachtete Exposition · [Daten](https://huggingface.co/datasets/Anthropic/EconomicIndex)
- Karpathy, A. (März 2026). [US Job Market Visualizer](https://karpathy.ai/jobs/) — Methodik-Impuls der ersten Version dieser App (342 US-Berufe, BLS-Daten, LLM-Scoring)
- Brookings Institution (2019). *Automation and Artificial Intelligence: How machines are affecting people and places*
- Webb, A. (2026). *Tech Trends Report* — Convergence-Ansatz für Branchenanalyse
- BFS (2026). [Strukturerhebung (SE) 2024 — Ausgeübter Beruf (CH-ISCO-19) nach Geschlecht und Staatsangehörigkeit](https://www.bfs.admin.ch/bfs/de/home/statistiken/kataloge-datenbanken.assetdetail.36492006.html) · [Über die Strukturerhebung](https://www.bfs.admin.ch/bfs/de/home/statistiken/bevoelkerung/erhebungen/se.html)
- Europäische Kommission (2023). [ESCO v1.2](https://esco.ec.europa.eu)
- BFS (2026). [LSE 2024, T17 — Monatlicher Bruttolohn nach Berufsgruppen, Lebensalter und Geschlecht, privater und öffentlicher Sektor zusammen](https://www.bfs.admin.ch/bfs/de/home/statistiken/kataloge-datenbanken.assetdetail.36355224.html) · [Über die Lohnstrukturerhebung](https://www.bfs.admin.ch/bfs/de/home/statistiken/arbeit-erwerb/loehne-erwerbseinkommen-arbeitskosten/lohnstruktur.html)
- BFS (2026). [Salarium — Statistischer Lohnrechner (LSE 2024)](https://www.salarium.bfs.admin.ch) — Profilverhältnisse für heterogene Berufsgruppen
- BFS. [LSE 2018 — Spezialauswertung Pflegepersonal für das BAG](https://www.bfs.admin.ch/bfs/de/home/statistiken/kataloge-datenbanken.assetdetail.19087994.html) (cc-d-03.04.01.90.01) — Verhältnis dipl. Pflege zum Median Gruppe 22
- BFS. Krankenhausstatistik, Standardtabellen 2018–2022 (VZÄ und Lohnaufwand nach Funktion) sowie Medienmitteilung vom 25.11.2025 (Sollstunden je Vollzeitstelle) — Verhältnis Ärzteschaft/Pflege
- Büro BASS im Auftrag des BAG (2018). *Einkommen der Ärzteschaft in der Schweiz 2009–2014* — Verhältnis Grundversorgung/Spezialisten
- BFS (2026). [Statistik der Unternehmensstruktur (STATENT) 2024 — Vollzeitäquivalente nach Kanton und Wirtschaftsabteilung](https://www.pxweb.bfs.admin.ch/pxweb/de/px-x-0602010000_101/-/px-x-0602010000_101.px/) — Regionsgewichte; Beschäftigte je Wirtschaftsabteilung als Nenner des Grenzgänger-Anteils
- BFS (2026). [Statistik der Unternehmensstruktur (STATENT) 2011–2024 — Marktwirtschaftliche Unternehmen nach Wirtschaftsabteilungen und Grössenklasse (ts-x-06.02.01.01)](https://www.bfs.admin.ch/bfs/de/home/statistiken/kataloge-datenbanken.assetdetail.36734598.html) — Grossfirmen-Anteil je Branche (KMU-Adoptions-Faktor)
- BFS (2026). [Grenzgängerstatistik (GGS) — Ausländische Grenzgänger/-innen nach Wirtschaftszweig und Erwerbsstatus (DF_GGS_4)](https://stats.swiss/vis?lc=de&df[ds]=ds%3Adisseminate&df[id]=DF_GGS_4&df[ag]=CH1.GGS&df[vs]=1.0.0&dq=..Q&lom=LASTNPERIODS&lo=5) · [Über die Grenzgängerstatistik](https://www.bfs.admin.ch/bfs/de/home/statistiken/arbeit-erwerb/erhebungen/ggs.html)
""")

st.subheader("Beobachtete Wirkung — Schweiz")
st.markdown("""
- Kläui, J. & Siegenthaler, M. (Okt. 2025). [KI und der Schweizer Arbeitsmarkt: Erste Evidenz zu Auswirkungen auf Arbeitslosigkeit und Stellenausschreibungen](https://doi.org/10.3929/ethz-c-000785283) — KOF Studien Nr. 186
- EY Schweiz (27.05.2026). [EY AI Survey 2026](https://www.ey.com/de_ch/newsroom/2026/05/artificial-intelligence-widely-established-in-swiss-companies-but-many-are-still-in-the-early-stages-of-scaling)
- JobCloud (Juni 2026). [jobs.ch KI Report 2026](https://www.jobcloud.ch/wp-content/uploads/2026/06/jobs.ch-KI-Report.pdf)
- AXA / Sotomo (2026). [AXA KMU-Arbeitsmarktstudie 2026](https://www.axa.ch/de/ueber-axa/medien/medienmitteilungen/aktuelle-medienmitteilungen/2026/20260915-kmu-arbeitsmarktstudie-kuenstliche-intelligenz.html)
- Derungs, C. et al. (08.10.2026). [HSLU AI Jobs Report 2026](https://www.hslu.ch/-/media/campus/common/files/dokumente/h/1-medienmitteilungen-und-news/2026/i/260922-hslu-ai-job-report-screen-def.pdf)
- einstAIn / Angestellte Schweiz (16.06.2026). [Nahezu jeder dritte Schweizer Job wegen KI unter Druck](https://angestellte.ch/medien/medienmitteilungen/nahezu-jeder-dritte-schweizer-job-wegen-ki-unter-druck)
- Lundsgaard-Hansen, C. / sparkr (Sept. 2026). [Künstliche Intelligenz und der Schweizer Arbeitsmarkt](https://sparkr.ch/wp-content/uploads/2026/09/Kuenstliche-Intelligenz-und-Schweizer-Arbeitsmarkt_sparkr_20260930.pdf)
""")

st.subheader("Beobachtete Wirkung — International")
st.markdown("""
- Iscenko, Z. & Curto Millet, F. (Jan. 2026). [Looking for the Ladder](https://eig.org/wp-content/uploads/2026/01/TAWP-Iscenko-Millet.pdf) — Economic Innovation Group
- Brynjolfsson, E., Chandar, B. & Chen, R. (12.08.2026). [Canaries in the Coal Mine?](https://digitaleconomy.stanford.edu/app/uploads/2026/08/Canaries_August2026.pdf)
- Abel, J. R. et al. (01.09.2026). [Businesses Are Using AI to Transform Work, Not Cut Jobs](https://libertystreeteconomics.newyorkfed.org/2026/09/businesses-are-using-ai-to-transform-work-not-cut-jobs/) — NY Fed
- The Budget Lab at Yale (Update 15.09.2026). [Tracking the Impact of AI on the Labor Market](https://budgetlab.yale.edu/research/tracking-impact-ai-labor-market)
- May, B. & Badawy, Y. (07.01.2026). [Evidence of an AI-driven shakeup of job markets is patchy](https://www.oxfordeconomics.com/wp-content/uploads/2026/01/Evidence-of-an-AI-driven-shakeup-of-job-markets-is-patchy.pdf) — Oxford Economics
- Challenger, Gray & Christmas (01.10.2026). [Challenger Report September 2026](https://www.challengergray.com/wp-content/uploads/2026/10/Challenger-Report-September-2026.pdf)
""")
