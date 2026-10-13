"""
Seite 5: Methodik & Quellen
"""

from pathlib import Path

import pandas as pd
import streamlit as st

st.title("Methodik & Quellen")

DATA_PATH = Path(__file__).parent.parent.parent.parent / "data" / "processed" / "scores.csv"


@st.cache_data
def load_data() -> pd.DataFrame | None:
    if not DATA_PATH.exists():
        return None
    return pd.read_csv(DATA_PATH)


df = load_data()
n_berufe = len(df) if df is not None else 0
if df is not None and "beschreibung_quelle" in df.columns:
    n_esco = int((df["beschreibung_quelle"] == "ESCO").sum())
    n_fallback = n_berufe - n_esco
else:
    n_esco = n_fallback = 0
if df is not None and "synonyme" in df.columns:
    syn = df["synonyme"].fillna("").astype(str).str.strip()
    n_zusammen = int((syn != "").sum())
    n_titel = int(syn[syn != ""].str.split(";").str.len().sum())
else:
    n_zusammen = n_titel = 0
summe_tsd = float(df["beschaeftigte_1000"].sum()) if df is not None else 0.0
summe_text = f"{summe_tsd:,.0f}".replace(",", "'")

# ─── KMU-Adoptions-Faktor: STATENT-Anteile, Vergleich mit Betriebszählung 2008 ──
KMU_PATH = DATA_PATH.parent / "kmu_anteil_branche.csv"
# Schwellen wie in src/scoring/ch_adjustments.py (GROSSFIRMEN_SCHWELLE_HOCH / _TIEF)
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


@st.cache_data
def load_kmu() -> pd.DataFrame | None:
    if not KMU_PATH.exists():
        return None
    return pd.read_csv(KMU_PATH)


kmu_df = load_kmu()
KMU_JAHR = int(kmu_df["jahr"].iloc[0]) if kmu_df is not None and "jahr" in kmu_df else "2024"
KMU_MITTEL = (kmu_df["beschaeftigte_gross"].sum() / kmu_df["beschaeftigte_total"].sum()
              if kmu_df is not None else float("nan"))
KMU_MITTEL_TEXT = "–" if pd.isna(KMU_MITTEL) else f"{KMU_MITTEL * 100:.0f} %"
kmu_vergleich = None
if kmu_df is not None:
    zeilen = [
        f"| Branche | STATENT {KMU_JAHR} (Unternehmen) | Verschiebung | BZ 2008 (Arbeitsstätten) "
        "| Verschiebung bisher | Abdeckung |",
        "|---|---:|:---:|---:|:---:|---:|",
    ]
    for _, r in kmu_df.sort_values("grossfirmen_anteil", ascending=False,
                                    na_position="last").iterrows():
        alt = BZ2008_ANTEIL.get(r["branche"], float("nan"))
        abdeckung = r.get("abdeckung", float("nan"))
        zeilen.append(
            f"| {r['branche']} | {_prozent(r['grossfirmen_anteil'])} "
            f"| {_verschiebung(r['grossfirmen_anteil'], KMU_SCHWELLE_HOCH, KMU_SCHWELLE_TIEF)} "
            f"| {_prozent(alt)} | {_verschiebung(alt, 0.40, 0.10)} "
            f"| {'–' if pd.isna(abdeckung) else f'{abdeckung * 100:.0f} %'} |"
        )
    kmu_vergleich = "\n".join(zeilen)

st.markdown("""
Diese Seite erklärt, wie die KI-Expositions-Scores berechnet wurden und woher die Daten stammen.
""")

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
(SE 2024 total: 4'584 Tsd.). Automatisch ergänzt wurden Berufsgattungen mit mindestens
**5'000 Beschäftigten**.

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
  Die bisherigen Titel bleiben in der Berufssuche als Synonyme auffindbar. Die Scores dieser
  Einträge sind vorläufig das beschäftigungsgewichtete Mittel der bisherigen Einzelberufe;
  eine Neubewertung folgt.
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
Für das KI-Scoring benötigt jeder Beruf eine inhaltliche Beschreibung seiner Kerntätigkeiten.
Die Beschreibungen werden in einem mehrstufigen Prozess ermittelt:

| Stufe | Quelle | Berufe |
|---|---|---|
| 1–3 | ESCO API (ISCO-Code + Textsuche, Deutsch/Englisch) | {n_esco} von {n_berufe} |
| 4 | berufsberatung.ch (Fallback bei keinem ESCO-Treffer) | — |
| 5 | Wikipedia (zweiter Fallback) | — |
| 6 | Claude Haiku (generierte Beschreibung als letzter Ausweg) | {n_fallback} von {n_berufe} |

Die verwendete Quelle ist in der Spalte `beschreibung_quelle` gespeichert und
wird bei der Berufssuche angezeigt.

- **ESCO:** [esco.ec.europa.eu](https://esco.ec.europa.eu/de/use-esco/esco-api), Version 1.2
- **Sprache:** Deutsch, Fallback Englisch
""")

st.subheader("Lohndaten")
st.markdown("""
Der mediane Jahresbruttolohn (`lohn_median_chf`) stammt aus der **BFS Lohnstrukturerhebung
(LSE) 2024**. Die Herkunft jedes Werts steht in der Spalte `lohn_quelle`.

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
- **Einschränkungen:** nur 2-stellige LSE-Gruppen (eine 3-/4-stellige Auswertung wäre nur
  als kostenpflichtige BFS-Sonderauswertung erhältlich); Salarium bildet nur den
  **Privatsektor** ab; Spitzenlöhne werden unterschätzt (siehe «Einschränkungen & Hinweise»);
  **Selbständige** (z. B. Ärzte mit eigener Praxis, Anwälte, Landwirte) sind in der LSE
  nicht enthalten.
""")

st.subheader("Branchenzuordnung")
st.markdown("""
Jeder Beruf ist einer von 21 internen Branchen zugeordnet (Grundlage für Brancheneffekt,
KMU-Faktor und Branchenanalyse):

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
- **Wichtig: fliesst nicht in score_ch oder zeitrahmen ein** — rein additiver Kontext-Layer
- **Limitationen:** Kein Pro-Beruf-Mapping möglich; Zähler (2025) und Nenner (2024) liegen ein
  Jahr auseinander, bei leicht wachsendem Grenzgängerbestand ist der Anteil daher eher etwas zu
  hoch. STATENT zählt Personen mit Verträgen bei mehreren Unternehmen mehrfach, die GGS zählt
  Personen. Grenzgänger/-innen mit Schweizer Pass sind im Zähler nicht enthalten.
- **Frühere Werte:** Bis Oktober 2026 wurde der Anteil mit dem Nenner der Betriebszählung 2008
  berechnet (rund 4,2 statt 5,7 Mio. Beschäftigte); die Anteile lagen dadurch je nach Branche bis
  gut 7 Prozentpunkte zu hoch.
""")

st.divider()

# ─── Scoring-Methodik ─────────────────────────────────────────────────────────
st.header("KI-Expositions-Score (0–10)")

st.markdown("""
Die Scoring-Methodik folgt dem Ansatz von **Andrej Karpathy (März 2026)** und der
**Brookings Institution**, adaptiert für den Schweizer Kontext.

Für jeden Beruf wird Claude (claude-sonnet-4-6) beauftragt, anhand der ESCO-Berufsbeschreibung
fünf Kriterien auf einer Skala von 0–10 zu bewerten:
""")

st.markdown("""
| Kriterium | Gewichtung | Beschreibung |
|---|---|---|
| Digitaler Output | 25 % | Arbeitet der Beruf primär mit digitalen Informationen, Texten oder Daten? |
| Wiederholbarkeit | 25 % | Sind die Kerntätigkeiten strukturiert, vorhersehbar und regelbasiert? |
| Physische Präsenz | 20 % | Je mehr körperliche Präsenz nötig, desto **tiefer** der Score |
| Kreativität | 15 % | Je mehr originelles Denken gefragt, desto **tiefer** der Score |
| Soziale Interaktion | 15 % | Je mehr Empathie und Vertrauen nötig, desto **tiefer** der Score |

Der **Rohscore** ergibt sich aus der gewichteten Summe dieser Kriterien.
""")

st.subheader("Schweiz-spezifische Anpassungen")
st.markdown("""
Auf den Rohscore werden CH-spezifische Faktoren angewendet, die den lokalen Arbeitsmarktkontext
berücksichtigen. Alle 21 Branchen aus dem Datensatz sind explizit bewertet:

**Brancheneffekte** (Deltawert auf den Rohscore):

| Branche | Delta | Begründung |
|---|---|---|
| Versicherungen | **+0.4** | Sehr standardisierte Prozesse, hoher Digitalisierungsgrad |
| Finanzen | **+0.3** | Bankplatz CH: hoher Automatisierungsdruck |
| Beratung | **+0.2** | Wissensarbeit: KI augmentiert Analyse & Strategie |
| Detailhandel | **+0.2** | E-Commerce-Druck, Self-Checkout, Logistikautomation |
| Recht | **+0.2** | LegalTech wächst; Dokumentenanalyse automatisierbar |
| Immobilien | **+0.1** | PropTech, Bewertungs-KI, digitale Plattformen |
| Medien | **+0.1** | KI-generierte Inhalte, aber Kreativität dämpft |
| Verwaltung | **+0.1** | Private Administration: strukturierte Büroprozesse |
| Dienstleistungen | **0.0** | Zu heterogen für einheitlichen Effekt |
| Transport | **0.0** | Physisch, aber autonomes Fahren mittelfristig |
| Umwelt | **0.0** | Spezialisiert; Monitoring-KI vs. Feldarbeit neutral |
| Gastgewerbe | **−0.1** | Serviceorientiert, Kundenkontakt; Buchungs-KI marginal |
| Industrie | **−0.1** | MEM/Pharma: Fachkräftemangel als Puffer |
| Landwirtschaft | **−0.1** | Precision Farming wächst, aber physische Arbeit dominiert |
| Öff. Verwaltung | **−0.1** | Öffentl. Sektor: langsame Adoption, politische Rahmenbedingungen |
| Sicherheit | **−0.1** | Physische Präsenz erforderlich; Überwachungs-KI ergänzt nur |
| Bau | **−0.2** | Stark physisch, handwerklich; Digitalisierung langsam |
| Bildung | **−0.2** | Gesellschaftlicher Konsens über menschliche Lehrvermittlung |
| ICT | **−0.2** | KI-Fachkräfte adaptiv; treiben Wandel selbst |
| Gesundheit | **−0.3** | Regulierung, Fachkräftemangel, Pflegekomponente als Bremse |
| Soziales | **−0.3** | Hoher Empathiebedarf, Schutzinteressen; ähnlich Gesundheit |

**Lohneffekte** (Deltawert auf den Rohscore):

| Lohnklasse (Jahresbruttolohn) | Delta | Begründung |
|---|---|---|
| > 150'000 CHF | **+0.4** | Sehr hoher ROI für Automatisierungsinvestitionen |
| 100'000–150'000 CHF | **+0.2** | Stärkerer wirtschaftlicher Anreiz zur Automatisierung |
| 60'000–100'000 CHF | **0.0** | Neutral |
| < 60'000 CHF | **−0.2** | Geringerer ROI; manuelle Arbeit oft günstiger |

Die Klassengrenzen sind seit der Umstellung auf die LSE 2024 unverändert (nicht um die
Lohnentwicklung von +3,5 % seit 2022 angehoben; das würde nur 2 Berufe knapp über 100'000 CHF
verschieben). Weil die LSE nur Gruppenmediane liefert, liegt derzeit kein Beruf über 150'000 CHF.

Der finale **score_ch** wird auf den Bereich 0–10 begrenzt.
""")

st.subheader("KMU-Adoptions-Faktor (Zeitrahmen)")
st.markdown(f"""
Grossunternehmen führen KI in der Regel schneller ein als KMU. Der Faktor verschiebt deshalb den
vom Scoring geschätzten Zeitrahmen (`zeitrahmen_roh`) je Branche um eine Stufe — er wirkt auf
das **Wann**, nicht auf die Höhe der Exposition (`score_ch` bleibt unverändert). Das Ergebnis steht
in `zeitrahmen`, die Verschiebung in `zeitrahmen_kmu_delta`.

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

# ─── Anpassungsfähigkeit ──────────────────────────────────────────────────────
st.header("Anpassungsfähigkeits-Score (0–10)")

st.markdown("""
Der Anpassungsfähigkeits-Score (verwendet in der Matrix-Ansicht) misst, wie leicht
Berufsangehörige sich bei Automatisierungsdruck neu orientieren können.
Er basiert auf der Methodik der **Brookings Institution** und setzt sich zusammen aus:

| Kriterium | Max. Punkte | Quelle |
|---|---|---|
| Qualifikationsniveau | 4 | BFS SAKE (Bildungsabschluss nach ISCO) |
| Lohnniveau | 3 | LSE 2024 (höherer Lohn = mehr Ressourcen für Umschulung) |
| Digitale Affinität | 2 | KI-Score Teilkriterium «Digitaler Output» |
| Branchenmobilität | 1 | Schätzung basierend auf Branchencharakteristika |

Skala: 0 = sehr schwer anzupassen, 10 = sehr flexibel
""")

st.divider()

# ─── Beobachtete Wirkung ──────────────────────────────────────────────────────
st.header("Was wir über die tatsächliche Wirkung wissen (Stand Oktober 2026)")

st.markdown("""
Die Scores dieser App messen die **Exposition**, also was KI technisch übernehmen *könnte*.
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
- **KI-Scoring ist keine exakte Wissenschaft.** Die Scores sind Einschätzungen eines
  Sprachmodells, keine empirisch gemessenen Werte. Sie sollten als Orientierung, nicht als
  Prognose verstanden werden.
- **Exposition ≠ Jobverlust.** Ein hoher Score bedeutet, dass Teile des Berufs automatisierbar
  *sein könnten* – nicht dass Jobs verschwinden. Viele Berufe wandeln sich.
  **Exposition** beschreibt die technische Möglichkeit; die **beobachtete Wirkung** ist die
  tatsächlich gemessene Entwicklung auf dem Arbeitsmarkt. Beides sind getrennte Grössen.
  Bisher wirkt KI in der Schweiz nach heutigem Wissensstand vor allem über **weniger
  Einstiegsstellen** und **Nicht-Nachbesetzung**, weniger über breite Entlassungen
  (siehe «Was wir über die tatsächliche Wirkung wissen»).
- **Datenbasis 2024.** Die Beschäftigungszahlen basieren auf der BFS Strukturerhebung (SE) 2024
  (Stichprobe; Werte kleiner Berufe sind entsprechend unsicher). Die KI-Landschaft
  verändert sich schnell; Scores können in 1–2 Jahren bereits überholt sein.
- **ESCO-Matching nicht immer perfekt.** Für einige Schweizer Berufsbezeichnungen existiert
  kein exakter ESCO-Eintrag. In diesen Fällen wurde der nächstähnliche Beruf verwendet.
- **Löhne sind Gruppenwerte bzw. Modellschätzungen.** Die LSE 2024 weist nur 2-stellige
  Berufsgruppen aus (Median). Alle Berufe einer Gruppe haben deshalb denselben Lohn — ausser in
  den Gruppen 11–14, 22, 24 und 26, wo er mit Salarium-Profilen (Ausbildung, Branche)
  differenziert wird. Berufsindividuelle Löhne wurden nicht erhoben; Selbständige fehlen in der
  LSE, Salarium deckt nur den Privatsektor ab.
- **Spitzenlöhne (Ärzteschaft, Kader, Private Banking, Kanzleien) werden unterschätzt:**
  Salarium kennt keine Facharzt- oder Kaderzuschläge, und das Normprofil enthält keine
  Kaderfunktion. Präzisere Werte erfordern eine BFS-Sonderauswertung der LSE auf
  3-/4-stelliger Ebene.
""")

st.subheader("Weitere CH-spezifische Faktoren (nicht in Score eingeflossen)")
st.markdown("""
Folgende Faktoren beeinflussen die KI-Exposition im Schweizer Kontext, sind aber in der
aktuellen Berechnung **nicht berücksichtigt**:

- **Sprachregionen:** Die verwendete SE-Tabelle ist nicht nach Sprachregion × Beruf aufgeschlüsselt.
  Deutschschweiz, Romandie und Tessin können strukturell unterschiedliche Expositionsmuster
  aufweisen.
- **Kantonale/regionale Lohnunterschiede:** Die LSE-Lohndaten sind national aggregiert
  (Salarium-Verhältnisse als gewichtetes Mittel der Grossregionen).
  Regionale Lohndisparitäten (z.B. Zürich vs. Wallis) fliessen nicht ins Scoring ein.
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
- Karpathy, A. (März 2026). [US Job Market Visualizer](https://karpathy.ai/jobs/) — Methodik-Impuls (342 US-Berufe, BLS-Daten, LLM-Scoring)
- Brookings Institution (2019). *Automation and Artificial Intelligence: How machines are affecting people and places*
- Webb, A. (2026). *Tech Trends Report* — Convergence-Ansatz für Branchenanalyse
- BFS (2026). [Strukturerhebung (SE) 2024 — Ausgeübter Beruf (CH-ISCO-19) nach Geschlecht und Staatsangehörigkeit](https://www.bfs.admin.ch/bfs/de/home/statistiken/kataloge-datenbanken.assetdetail.36492006.html) · [Über die Strukturerhebung](https://www.bfs.admin.ch/bfs/de/home/statistiken/bevoelkerung/erhebungen/se.html)
- Europäische Kommission (2023). [ESCO v1.2](https://esco.ec.europa.eu)
- BFS (2026). [LSE 2024, T17 — Monatlicher Bruttolohn nach Berufsgruppen, Lebensalter und Geschlecht, privater und öffentlicher Sektor zusammen](https://www.bfs.admin.ch/bfs/de/home/statistiken/kataloge-datenbanken.assetdetail.36355224.html) · [Über die Lohnstrukturerhebung](https://www.bfs.admin.ch/bfs/de/home/statistiken/arbeit-erwerb/loehne-erwerbseinkommen-arbeitskosten/lohnstruktur.html)
- BFS (2026). [Salarium — Statistischer Lohnrechner (LSE 2024)](https://www.salarium.bfs.admin.ch) — Profilverhältnisse für heterogene Berufsgruppen
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
