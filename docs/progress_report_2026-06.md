# Project Progress Report — June 2026

*A full-project review of collected assets, coverage by pipeline rung, linkage
state, and the remaining gaps / open follow-ups. Companion to
`docs/reconceptualization_2026.md` (strategy) and `docs/legal_mechanisms_review.md`
(instrument catalogue). Compiled 2026-06-12, last figures refresh 2026-06-28 —
all project-total numbers below are sourced from `docs/STATS.md`
(`scripts/187_generate_stats.py`); re-run that script and re-sync this section
after any load script rather than hand-editing a number here.*

---

## 1. Where the project stands, in one paragraph

The project has moved past its original framing as a single court-portal scraper.
It is now a **multi-source evidentiary spine**: 8,271 occupation court cases across
26 DNR courts (the original 2,666 Mariupol cases + 5,646 net-new loaded June 2026), a
12,948-entry ownerless registry, the 1,941-building Russian federal reconstruction
tracker, demolition registers, DNR land-grant orders, housing-distribution lists,
the ЕИСЖС new-build registry, a 30+-instrument legal-mechanism catalogue (rungs
[A]–[H]) now backed by primary captured text, a 111-node stakeholder network, and
EGRUL ownership extracts — all loaded onto the canonical `property` spine in
PostgreSQL/PostGIS, all forensically captured (**353,587** raw artifacts / 91 GB
on disk, **8,655** DB-registered source documents, SHA-256 + custody throughout —
see `docs/STATS.md` for the full breakdown and the raw-store-vs-DB-registered
distinction). **11,730 properties sit on the spine; 1,156 clear the ≥2-source
legal-grade bar; 206 remain RD4U-uncategorized** (not "every property," as an
earlier draft of this paragraph claimed). The four original Mariupol district
court dockets are saturated; the layer has since expanded region-wide (§2). The
dominant remaining limits are *structural* (court-record address redaction) rather
than *coverage* — but several discrete, build-ready follow-ups remain, and the
1 July 2026 re-registration deadline (≈3 weeks out) will open a new capture wave.

---

## 2. Asset inventory (as collected)

### Raw / custody layer
| Asset | Count | Notes |
|---|---|---|
| Raw artifacts (`data/raw/`) | **353,587 files / 91 GB** | append-only, SHA-256-keyed, `.meta.json` sidecars (was 39,061/5.6GB — stale, see `docs/STATS.md`) |
| Registered source documents (`source_document` table) | **8,655** | chain-of-custody, incl. derived OCR artifacts (was 6,784) |
| PostgreSQL/PostGIS | **live** (loaded) | spine populated; script 33 runs read-only against it |

### Primary occupation sources (the four independent streams + extensions)
| Source | Parsed records | Status |
|---|---|---|
| Occupation court docket (26 DNR courts) | **8,271 cases** | Expanded June 2026 from 4 Mariupol courts to all 26 DNR courts returning records; 5,646 net-new loaded (`scripts/182`–`185`, no double-count). **87.1% granted** at first instance; spine now holds 8,303 `court_petition` + 7,052 `court_transfer` events. Of 15 enabled-but-zero courts: 10 had jurisdiction formally transferred elsewhere (cases not actually zero — `scripts/186` recovers 8 confirmed Avdiivka cases hidden in Yasynuvata's docket), 5 are genuine building-relocated ghost/destroyed courts (venue notice captured 2026-06-28, see §5) |
| Mariupol ownerless registry (4-district master list) | **12,948** | the ФКЗ-4 registry-as-title master list |
| Mariupol ownerless decrees (постановления) | **968** | signers identified (Кольцов 652, Моргун 156, …) |
| Demolition decrees (Mariupol admin) | **20** | + MinStroy register **637** rows (525 Mariupol buildings) |
| Russian federal damage/reconstruction tracker (XLSX) | **1,941 buildings** | contractor + destruction-% map |
| DNR head land-allocation orders | **51** | no-auction КРТ grants to developer SPVs |
| Housing queue / distribution lists | **5,822 / 1,889** | displaced-persons demand side |
| ЕИСЖС new-build objects + crosswalk | **20 / 40** | demolish→rebuild address-laundering evidence |

### Derived / analytical layer
| Asset | Count | Notes |
|---|---|---|
| Address registry | 3,150 | normalized + raw, confidence-scored |
| Geocoded buildings | 2,027 | + 53 low-confidence held back |
| RD4U-categorized properties | **11,524** of 11,730 | A3.1/A3.2/A3.3/A3.6 comma-sets (script 36); 206 uncategorized, mostly new reallocation-stage rows — re-run script 36 |
| Legal-grade properties (≥2 sources) | **1,156** | corroboration report (script 33), re-run 2026-06-28 post district-load |
| Stakeholder network | **111 nodes / 138 edges** | 52 persons + 53 orgs + bridge nodes |
| DNR region80 normative index / relevant subset | 2,221 / **395** | enabling-norm layer (scripts 35/37) |
| denis-pushilin.ru archive index | **2,878 / 2,894 PDFs** | full Акты Главы ДНР archive |
| Legal-mechanism instruments catalogued | **30+** | rungs [A]–[H]; 14 newly [CAPTURED] in the 2026-06-12 scaffolding scan |
| EGRUL INN lookups / founder extracts | **17 / 14** | all known developer INNs verified |

---

## 3. Coverage by pipeline rung

Using the `docs/legal_mechanisms_review.md` framework. "Operational" = per-property
records; "Norm" = the enabling instrument's primary text.

| Rung | Operational records | Enabling norm captured? | Assessment |
|---|---|---|---|
| **Framework** | — | ✅ ГКО №1, Указ №73, №162/205, ФКЗ-4 implementing laws, №279-РЗ | Strong |
| **[A] Ownerless** | 968 decrees + 12,948 registry | ✅ №66-РЗ family + ГКО №300/153/515 | Strong; pre-petition rungs thin (see §5) |
| **[B] Court transfer** | 8,271 cases · 26 courts | ✅ ГПК гл.33 | Region-wide; 87.1% granted; Mariupol conveyor now shut down (ФКЗ-4) |
| **[C] Demolition** | 20 decrees + 637 register | ✅ ГКО №162/205/245 + Указ №40 | Strong; №56 list internal/unrecoverable |
| **[D] Land reallocation** | 51 land orders | ✅ №39-РЗ + ГКО №282 | Good; 1 new grant unadded (§5) |
| **[E] Rebuild** | 20 ЕИСЖС objects | ✅ Указ №290 + ГКО №175 §5.3 | Good (small N — few completed rebuilds exist yet) |
| **[F] Resale** | sold-out % per object | ⚠️ 2% mortgage law [REPORTED] only | Federal norm uncaptured |
| **[G] Housing** | 5,822/1,889 lists | ✅ ГКО №175/263 + №93-2/93-3 | Good; 25 m² cap still [REPORTED] |
| **[H] Toponymy** | toponyms.csv | ✅ Указ №301 | Decrees themselves not on any portal |

**The command chain is fully dated and primary-sourced:** Пушилин (apex; every
appointment + 50/51 land grants) → Иващенко (2022) → Моргун (2023–25) → **Кольцов
(2025–present)** → signing officials → commission members → developer SPVs
(all mainland-Russia beneficial owners) → federal contractors. This is the
strongest part of the Rome Statute art. 28 / 25(3)(b) case.

---

## 4. Linkage / corroboration state

- **11,730** properties on spine · **1,156** legal-grade (≥2 independent families) ·
  **8,303** court-record islands · **117** with no source family yet. (Court-islands
  jumped from 2,657 to 8,303 with the June 2026 district-court load — almost all
  net-new district-court properties are single-source islands, which is why
  legal-grade barely moved despite the spine nearly doubling.)
- Strongest co-occurrences: damage_assessment ⋈ ownerless_registry (514),
  damage_assessment ⋈ housing_distribution (226), demolition ⋈ housing_distribution
  (184).
- Flagship multi-source property: **пр. Ленина 98** (4 families).

---

## 5. Gaps & open follow-ups

Grouped by tractability. **Build-ready** = clear next step, no discovery needed.
**Discovery** = must investigate feasibility first. **Hard limit** = structural,
not closable. **Deferred** = low marginal value.

### A. Build-ready (clear, bounded next steps)

0. **Disaggregate the 9 remaining absorbed-jurisdiction towns** (Aleksandrovsk,
   Dobropolye, Novogrodovka, Selydove → Voroshilovsky; Velyka Novosilka → Kirovsky;
   Toretsk, Lyman → Yenakievo; Druzhkivka, Kostiantynivka → Horlivka) the way
   `scripts/186` already did for Avdiivka (8 cases recovered inside Yasynuvata's
   docket). Zero hits so far for these 9 under the current anchored-regex method —
   inconclusive, not proof those territories produce no bezkhoz activity; worth a
   closer read of a sample of each absorbing court's full caseload by hand before
   concluding either way. Source: ВС ДНР venue-reassignment notice, captured
   2026-06-28 (`data/raw/6bb873cb...` + `.meta.json`).
0a. **`court_case` table is stuck at the original 2,666/28-judge snapshot** and
   was never touched by the June 2026 district load (`scripts/182`–`185` write
   to `seizure_event.detail`, a different table entirely). This backs
   `scripts/40_build_stakeholder_network.py` and the public stakeholder-network
   exhibit/doc, so the judge rankings shown there are stale (e.g. Романов
   288→291, 28→33 named judges region-wide-Mariupol). Either write a new loader
   pass into `court_case` from the district population, or rewrite script 40 to
   read `seizure_event.detail->>'judge'` instead, then rebuild the exhibit's JS
   bundle (esbuild). `docs/stakeholder_network.md`'s prose numbers were
   hand-corrected 2026-06-28; the exhibit's embedded bundle data was not.
1. **Add ВЕРТИКАЛЬ ФОРТ-2 land grant** (Распоряжение №203/09.06.2026, просп. Победы
   127, cadastral 93:27:0010311:572) as the 52nd row of `dnr_land_orders.jsonl` —
   confirmed NEW beneficiary, still unadded. *(verified absent 2026-06-12.)*
2. **Add Никоноров А.Ю. + «Оперативный штаб по восстановлению ДНР»** to
   `docs/stakeholder_network.md` — new actors surfaced in the scaffolding scan
   (ГКО №1 / №282), not yet in the network doc.
3. **Lifecycle QA cross-check** — validate decree-signing date ranges in
   `ownerless_decrees.jsonl` / `demolition_decrees.jsonl` against the now-known
   tenure windows (Иващенко/Моргун/Кольцов) as a corroboration pass. (Never run.)
4. **Re-parse EGRUL founders** for the full 17-INN set (currently 14 founder
   records vs 17 lookups) and take the one open ownership hop: **ООО «УК БРИК
   ИНВЕСТ»** (ИНН 9310017730, 100% owner of НОВОЕ ВРЕМЯ 3) — its own founders
   unknown. *(Phase-2 INN lookups themselves are now DONE — supersedes the stale
   "9 pending" note in memory.)*
5. **OCR Указ №40/2022's amendments** (№657/2024, №513/2025) to resolve its
   relationship to ГКО №162/205/245 in rung [C]. Titles indexed; PDFs not yet OCR'd.
6. **Decree-letterhead OCR** to recover position titles for the 6 ownerless-decree
   signers (Перепечай, Дмитриев, Краснолуцкая, Матейко, …). Raw scans in store.
7. ~~**Per-judge grant/denial rates** from the DB~~ — **DONE** 2026-06-28,
   `scripts/183` (89 named judges region-wide with ≥30 decided cases, grant
   rates 65–100%; 33 named judges in Mariupol specifically, up from ~27). See
   `docs/dnr_district_first_instance_2026-06.md`.
8. **Screen the unreviewed `ukazy_glavy` 64-entry slice** of script 46's "remaining
   100" non-priority lexicon entries — lower yield expected, but unscreened.

### B. Discovery questions (feasibility unknown — investigate before building)

9. **Full-text court rulings via `ej.sudrf.ru/?fromOa=93RS0006`** — the one
   unexplored path that could close the **address gap on the 2,657 court islands**.
   Open question (pre_petition_sourcing §4): do особое-производство full texts get
   published online at all, or are they redacted/withheld for named individuals?
   *Settle this before assuming the islands are permanently unbridgeable.*
   **2026-06-13 update:** confirmed (sample case 9-36/2026, zhovtnevy_mariupol,
   property_id 1665) that the standard sudrf.ru docket-card page — the only page
   type captured for all 2,657 islands — has **no address field at all**: only
   case UID, category ("…признании права муниципальной собственности на
   бесхозяйную недвижимую вещь"), judge, dates, outcome, движение дела log, and
   parties (Администрация ГО Мариуполь + прокуратура). No attached
   исковое-заявление/решение PDF is exposed on this page either. This isn't a
   redaction *of* an address field — the field doesn't exist on this page type.
   Item 9 (`ej.sudrf.ru` full-text search) remains the only possible escape
   hatch; this finding just confirms the docket-card route is a dead end, not
   that full-text search is.
10. **25 m² compensation cap** — confirmed a *different* instrument from ГКО №175
    (whose norms are 33/42/+18/150 m²). Likely a служебное/маневренное-жильё
    allocation norm. Needs primary capture; source not yet located.
11. **2% subsidized-mortgage law + Promsvyazbank trail** ([F]/[F]-resale,
    population-transfer engine) — [REPORTED] only. Federal pravo.gov.ru capture
    target; the single biggest uncaptured *federal* norm in the chain.
12. **Распоряжение №61** (Mariupol municipal lease rulebook, [CITED]) — PDF
    dead-linked on нпа.днронлайн; recoverable only via mariupol.gosuslugi.ru or the
    горуправление юстиции registry.

### C. Tier-3 corroboration layers never built (reconceptualization §3, Tier 3)

13. **Satellite before/after** (Sentinel-2 free) for demolition + re-addressing
    cases — would physically confirm the paper transfers (esp. Нахимова 82 →
    Черноморский 1Б). Only the *paper* damage-tracker mirror is used today.
14. **Filtration / entry-ban data** (East SOS: 30k denied, 20–50-yr bans) — proves
    the "appear in person within 30 days" requirement is *designed* to be
    impossible. Central to the "sham process" argument; no data ingested.
15. **Utility-disconnection signal** — leading indicator (recited inside inspection
    acts as "отсутствие потребления ресурсов"); the only realistic source is
    derived text, not a standalone series.

### D. Structural hard limits (document, don't chase)

16. **2,657 court-record islands** carry `<адрес>` redaction at source and no
    non-court record references the case number — unbridgeable by address/cadastral/
    geometry *via this portal*. They stand as primary evidence on the case record
    itself. (Item 9 is the only possible escape hatch.)
19. **The "already-transferred-via-court" population is invisible to the
    ownerless registry, by construction — not by overlap.** *(Note: this item's
    base population is the original 2,657 Mariupol court islands, computed
    before the June 2026 district-court load grew court-islands to 8,303
    region-wide — the finding's logic likely still holds region-wide but has
    not been recomputed against the larger population; treat the specific
    counts below as the Mariupol-only historical figure, not current.)* Of the
    2,657 islands,
    **2,192 reached `court_transfer`** (court ruled in favor of "признание права
    муниципальной собственности" — i.e. the unit left "ownerless" status via the
    now-abolished court route, *before* the live 12,948-entry / 1,637-property
    ownerless registry was even queried). Because these 2,192 rows carry no
    address (see item 9), they show **zero property overlap** with the
    1,637-property registry_inclusion set — but that's an artifact of having
    nothing to match on, not evidence the two populations are genuinely disjoint.
    Net effect: **we can state a count (≥2,192 units already converted to
    municipal property via the old route) but cannot map any of them to a
    specific address/RD4U category**, and the one register that could
    (Реестр муниципального имущества городского округа Мариуполь) is not
    publicly accessible. This is the accountability-side fact ("at least 2,192
    units stripped of owner status") that currently has no restitution-side
    (per-property RD4U) counterpart. Closable only via item 9.
17. **Распоряжение ГКО №56** (Mariupol demolition list) — confirmed absent from all
    three normative-acts portals (region80, нпа.днронлайн, denis-pushilin); an
    internal operational order, likely no online primary text exists.
18. **`utility_cutoff` rung** — no public per-property series anywhere; only ever a
    finding recited inside the inspection act.

### E. External / strategic (not code)

19. **Parallel-dataset outreach** — Leibniz-IfL/KonKoop VisLab (already geocoding
    the ownerless lists) and Dossier Center (beneficiary-matching). Collaborate /
    data-exchange rather than rebuild; licensing terms unconfirmed.
20. **Per-property evidence-dossier export** (PDF for a claimant/investigator) —
    reconceptualization step 5; the actual deliverable for RD4U, not yet prototyped.
21. **RD4U A3.6 evidentiary-requirement scoping** — category definitions verified
    against the claim forms; the *per-property dossier* requirements for a filed
    A3.6 claim are not yet pinned down.

### F. Loose ends

22. **150 spine properties with zero source family** — orphans; investigate origin.
23. **971 damage-tracker-only properties** — war-damaged but not linked to any
    seizure act; good A3.6-evidence research candidates.
24. **Near-miss merges** — 16 of 56 candidate pairs would strengthen corroboration;
    квартал-zone + 50/60-лет-СССР pairs are matcher false positives (resolved);
    Машиностроителей/Строителей + Черноморская/Морская still need a map check.
25. **Court case `c0771eb2`** — flagged for manual ruling-text review (reversed-
    appeal final-outcome reconciliation; 5/6 done, this one outstanding).

---

## 6. The 1 July 2026 deadline & flow-capture posture

The Dec-2025 federal amendment (ФКЗ-4) pulled the re-registration deadline forward
to **1 July 2026 — ≈3 weeks from this report** — and abolished the court stage
(registry inclusion now = title). Consequences for the project:

- The **court docket is a closing corpus** — that case type ends with ФКЗ-4. In
  Mariupol it has already stopped (filings/decisions → 0 by mid-2026, the registry
  pivot); the rest of DNR is still producing first-instance cases as of mid-2026, so
  the region-wide 8,271 will keep growing modestly until each municipality completes
  the same transition. The historical Mariupol stock is the original 2,666.
- The **new flow moves to the registry**: the 12,948-entry ownerless registry is
  now the live front line. Andriushchenko reports +100–200 designations/week and a
  designations spike is expected on/after 1 July. **The highest-value recurring
  capture is re-snapshotting the four district registry XLSX + the municipal
  designation/removal decrees on a weekly cadence** (keep every dated snapshot;
  lists are edited/removed).
- **Removal decrees («снятие с учёта»)** are accelerating (9 found Mar–Jun 2026) and
  mark the transfer-consummated endpoint — worth a dedicated watch.

---

## 7. Recommended priority order

1. **Stand up the post-1-July registry re-snapshot cadence** (§6) — time-critical;
   the wave is imminent and the window to capture it as a *flow* is now.
2. **Resolve the `ej.sudrf.ru` discovery question** (§5 item 9) — it gates whether
   the 2,657-island address gap is closable; cheap to check, high payoff if yes.
3. **Close the build-ready cluster** (§5 items 1–7) — bounded, no blockers, each
   strengthens an existing lane (land grants, stakeholder net, QA, ownership chain).
4. **Capture the two biggest uncaptured federal norms** (§5 items 10–11: 25 m² cap,
   2% mortgage law) — the remaining [REPORTED] holes in rungs [F]/[G].
5. **Prototype the per-property RD4U dossier export** (§5 item 20) — turns the spine
   into the actual claimant deliverable.
6. **Tier-3 corroboration** (§5 items 13–14) and **parallel-dataset outreach**
   (§5 item 19) as parallel, lower-urgency tracks.

---

*Forensic note: every occupation/DNR/federal normative act and registration in this
project is evidence of the seizure system, NOT valid title. Ukraine does not
recognize them; neither do we. Capture before parse; SHA-256 + UTC timestamp +
source URL on every artifact (CLAUDE.md).*
