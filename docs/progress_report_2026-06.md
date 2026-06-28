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
[A]–[H]) now backed by primary captured text, a 370-node stakeholder network, and
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
| Stakeholder network | **370 nodes / 395 edges** | 184 persons + 180 orgs + bridge nodes; backfilled into `court_case`/`actor` from the district load 2026-06-28 (scripts/188-191), was stuck at the original 111/138 Mariupol-only snapshot |
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
| **[G] Housing** | 5,822/1,889 lists | ✅ ГКО №175/263 + №93-2/93-3 + Закон №269-РЗ | Good; 269-РЗ [CAPTURED] 2026-06-28 — note its 25 m² term is a max-excess cap on equivalent housing, not a flat ceiling (corrected from press reports, §5 item 10) |

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

0. ~~**Disaggregate the 9 remaining absorbed-jurisdiction towns**~~ — **SETTLED
   2026-06-28, negative.** `scripts/186`'s anchored-regex method found zero
   hits for these 9 (Aleksandrovsk, Dobropolye, Novogrodovka, Selydove →
   Voroshilovsky; Velyka Novosilka → Kirovsky; Toretsk, Lyman → Yenakievo;
   Druzhkivka, Kostiantynivka → Horlivka), unlike Avdiivka (8 cases recovered
   inside Yasynuvata's docket via the same method) — left inconclusive at the
   time pending a closer hand-read. That hand-read is now done: an unanchored
   substring scan (weaker than the anchored regex, so it would catch anything
   the anchor missed) was run against the **full population**, not a sample —
   all 503 vr--dnr, 184 kir--dnr, 478 enak--dnr, and 451 cg-gorl--dnr case
   texts, 1,616 cards total. Result: genuinely zero real hits for all 9 towns.
   vr--dnr and kir--dnr show no mention of their target towns in any form.
   enak--dnr's only "hits" are the venue-notice boilerplate itself (already a
   known false positive per `scripts/186`'s own comments). cg-gorl--dnr has
   exactly one hit for Konstantinovka, and it's a deceased party's
   *birthplace* — the identical false-positive shape `scripts/186` already
   flagged and excluded for the same town. Unlike Avdiivka's repeated,
   address-anchored signal, these 9 towns produce no real evidentiary trace
   in the absorbing courts' dockets at all. Source: ВС ДНР venue-reassignment
   notice, captured 2026-06-28 (`data/raw/6bb873cb...` + `.meta.json`).
0a. ~~`court_case` table stuck at the original 2,666/28-judge snapshot~~ —
   **DONE 2026-06-28.** `scripts/188_backfill_court_case_into_district.py`
   normalized the 5,646 net-new district cases' judge/petitioner data
   (previously only in `seizure_event.detail`) into `court_case`/`actor`,
   then `scripts/40` regenerated the network (111→370 nodes, 138→395 edges,
   28→33 judges), `scripts/189`/`191` re-embedded and re-bundled the exhibit
   (esbuild). Along the way found+fixed two more bugs surfaced only at the
   larger scale: (1) `scripts/40`'s petitioner fuzzy-matcher compared whole
   templated strings (`token_set_ratio`), so absorbed-jurisdiction courts'
   administrations (Торез, Дебальцево, Иловайск, Харцызск, ...) were wrongly
   bucketed into "Администрация городского округа Мариуполь" at 0.82-0.99
   similarity — fixed by isolating just the city token before fuzzing; (2)
   the exhibit's pan handler read a mutable ref inside a deferred React state
   updater, crashing under React 19 if mouseup fired mid-batch — fixed by
   capturing the values synchronously at event time. Visually verified
   (pan/zoom, node/edge counts) before commit.
1. ~~**Add ВЕРТИКАЛЬ ФОРТ-2 land grant**~~ — **DONE 2026-06-28.**
   `scripts/192_append_fort2_land_order.py` parses the already-OCR'd decree
   (Распоряжение №203/09.06.2026, просп. Победы 127, cadastral
   93:27:0010311:572, area 3,225 m², `denis_pushilin_land_grants_202606.jsonl`)
   and appends it as the 52nd row of `dnr_land_orders.jsonl` — this decree sits
   outside `scripts/11`'s rebuild scope (different `source_type`, captured by
   the Pushilin-site crawler not the land-order crawler), so it has to be
   appended by hand rather than picked up by a re-run; no beneficiary
   INN/OGRN found in the decree text or EGRUL, flagged `inn_missing`/
   `ogrn_missing`. Idempotent — re-running is a no-op.
2. ~~**Add Никоноров А.Ю. + «Оперативный штаб по восстановлению ДНР»**~~ —
   **DONE 2026-06-28.** Both added to Tier 2 of `docs/stakeholder_network.md`:
   Никоноров А.Ю. (Руководитель Администрации Главы ДНР) as the responsible
   official named in ГКО №1 (06.04.2022, the master demolish→land→rebuild
   predicate); the Operational HQ for DNR Reconstruction as the body that
   approves the site plan triggering private-plot seizure under ГКО №282
   (29.09.2022). Doc-only addition — neither actor is in the Postgres
   `actor`/`court_case` tables (no DB rows to back them), so they don't yet
   appear in the rendered stakeholder-network exhibit graph; that would need
   a manual insert into the graph data, not just the markdown doc.
3. ~~**Lifecycle QA cross-check**~~ — **DONE 2026-06-28.**
   `scripts/193_lifecycle_tenure_qa.py` checked all 988 decree rows
   (`ownerless_decrees.jsonl` + `demolition_decrees.jsonl`) against the three
   heads' tenure windows. **825 rows matched to Иващенко/Моргун/Кольцов by
   signing_official; 0 fell outside that signer's tenure window** —
   corroborates the appointment chronology (script 44) with no
   contradictions found. The other 163 rows are signed by subordinate
   officials (Перепечай 70, Дмитриев 55, Краснолуцкая 25, Матейко 8, 5
   unsigned) who aren't heads-of-administration and so are out of this
   check's scope, not failures. Violations (none found) would have written
   to `data/reports/lifecycle_tenure_qa_violations.jsonl`.
4. ~~**Re-parse EGRUL founders**~~ — **DONE 2026-06-28.** Added БРИК ИНВЕСТ
   (ИНН 9310017730) to `egrul_manual_inns.json`, user ran `scripts/20`
   (egrul.org fetch+capture) then `scripts/41` (local re-parse) — 30 founder
   records now captured (was 14/17, now the full set incl. this last hop).
   БРИК ИНВЕСТ's own founders: **Власов П.Н.** (70%, region-33) and
   **Лопухов К.К.** (30%, region-71) — both mainland Russia. Found a new
   cross-link along the way: Лопухов К.К. also founds ООО СЗ
   «РКС-Девелопмент» (2%) — the first individual-level link between two
   otherwise separate grant-recipient chains. Written up in
   `docs/stakeholder_network.md` "Founders / ownership chains"; not yet
   pushed into the rendered graph (doc-only, same as items 0a/2's caveat).
5. ~~**OCR Указ №40/2022's amendments**~~ — **DONE 2026-06-28**
   (`scripts/194_ocr_ukaz40_amendments.py`, local-only, both PDFs already in
   the raw store). **№657 (03.12.2024)**: institutional renaming pass
   (местная администрация → орган местного самоуправления) plus one
   substantive addition — §1.4.7 now explicitly ties demolition to cadastral
   de-registration/termination of recorded rights. **№513 (24.06.2025)**:
   removes the Operational HQ's gatekeeper role over the demolition list,
   replacing it with general "законодательству РФ и ДНР". Neither amendment
   references ГКО №162/205/245 — that relationship question is **still
   unresolved**, just no longer blocked on OCR. Side finding: confirmed
   institutional continuity of the «Оперативный штаб по восстановлению» —
   ГКО №75 (2022) → Указ №157 (2023) re-creation, same body — folded into
   `docs/stakeholder_network.md`'s entry for that actor (added per item 2
   above).
6. ~~**Decree-letterhead OCR**~~ — **DONE 2026-06-28**
   (`scripts/195_ocr_decree_signer_titles.py`, local-only; raw scans were
   already OCR'd from prior work, this read the signature blocks). All 4
   remaining signers' titles recovered: **Перепечай Б.Н.** and **Дмитриев
   А.В.** both "Начальник Управления ЖКХ" (Head, Housing & Utilities Dept.)
   — but with **overlapping** signing date ranges (19.08–17.10.2024 vs.
   16.08.2024–14.05.2025), not a clean handover, flagged for a closer look;
   **Краснолуцкая Т.Ю.** = Deputy Head of the same department; **Матейко
   В.А.** = Начальник Управления имущественных и земельных отношений (Head,
   Property & Land Relations Dept.) — a different department entirely.
   Written up in `docs/stakeholder_network.md` Tier 3.
7. ~~**Per-judge grant/denial rates** from the DB~~ — **DONE** 2026-06-28,
   `scripts/183` (89 named judges region-wide with ≥30 decided cases, grant
   rates 65–100%; 33 named judges in Mariupol specifically, up from ~27). See
   `docs/dnr_district_first_instance_2026-06.md`.
8. ~~**Screen the unreviewed `ukazy_glavy` 64-entry slice**~~ — **DONE
   2026-06-28** (title/description read, no OCR needed — already full text
   in script 43's index). **Confirmed low yield as expected**: pension/
   social-benefit payments, ministry liquidations (Industry & Trade,
   Prosecutor's Office), civil-service procedure (service IDs, performance
   reviews, bonuses), war-veteran/anniversary payments. Three borderline
   urban-planning-procedure decrees (№156/2023, №304/2023, №572/2025 —
   master-plan/градостроительная-documentation procedure) are generic
   planning regulation, not a seizure mechanism. **No new property-seizure
   or demolition pathway found** — script 46's priority/non-priority split
   holds up; nothing here needs folding into `legal_mechanisms_review.md`.

### B. Discovery questions (feasibility unknown — investigate before building)

9. ~~**Full-text court rulings via `ej.sudrf.ru/?fromOa=93RS0006`**~~ —
   **SETTLED 2026-06-28, dead end.** `scripts/196_probe_ej_sudrf_fulltext.py`
   (run by user, geoblocked portal) fetched the page: it's not a public
   full-text search form at all. Title "ГАС «Правосудие»", a single hidden
   `need_auth=1` + base64 `redirect_url` login-bounce form, and body text
   describing «Дела» (Cases) as where **a logged-in participant** tracks
   "судебным делам, участником которых вы являетесь" (cases *you* are a
   party to) — an authenticated personal-account portal, not a public
   search engine. `/index.php?fromOa=...` 404s. **No full-text path exists
   here for a non-party.** Combined with the 2026-06-13 finding (the
   docket-card page itself has no address field), the address gap on the
   2,657+ court islands is now **confirmed permanently unbridgeable through
   any sudrf.ru-family source** — both routes this project could try are
   closed. Future work on those islands needs an entirely different source
   family (Tier-3 satellite/registry corroboration only), not more court-
   portal crawling.
   **2026-06-13 update:** confirmed (sample case 9-36/2026, zhovtnevy_mariupol,
   property_id 1665) that the standard sudrf.ru docket-card page — the only page
   type captured for all 2,657 islands — has **no address field at all**: only
   case UID, category ("…признании права муниципальной собственности на
   бесхозяйную недвижимую вещь"), judge, dates, outcome, движение дела log, and
   parties (Администрация ГО Мариуполь + прокуратура). No attached
   исковое-заявление/решение PDF is exposed on this page either. This isn't a
   redaction *of* an address field — the field doesn't exist on this page type.
10. ~~**25 m² compensation cap**~~ — **CAPTURED + READ IN FULL 2026-06-28;
    CORRECTS the press paraphrase.** Source is Закон ДНР №269-РЗ, signed by
    Pushilin 03.04.2026, published 06.04.2026 — "Об особенностях
    распоряжения жилыми помещениями, имевшими признаки бесхозяйного
    имущества... а также условиях и порядке предоставления компенсации... и
    о внесении изменений в Закон ДНР №141-РЗ." Captured + OCR'd in full
    (`scripts/197`, both the DNR-side PDF and the federal `pravo.gov.ru`
    mirror — already ≥2-source before parsing). **Reading the primary text
    overturns the press framing** (mrpl.news/0629.com.ua/ZI.ua's "25 m²
    regardless of how large the destroyed home was" is a mischaracterization
    — flagged here so the project doesn't repeat it as fact): Статья 6 п.2
    and the Статья 10 amendment to №141-РЗ both define 25 m² as the maximum
    *excess* the replacement unit's area may exceed the lost unit's area by
    — i.e. equivalent-or-larger replacement, capped at +25 m² over the lost
    footprint, not a flat 25 m² ceiling on compensatory housing overall.
    Still a real, citable instrument, just a narrower claim than initially
    reported — update any case-study prose citing the press version. What
    the primary text **does** confirm exactly as reported: Статья 4 п.2
    permits using bezkhoz/"abandoned" housing acquired under 5-ФКЗ §21 as
    служебное жилье for officials/civil servants/military/police (incl.
    участковый уполномоченный) and education/medical staff, **until 1
    January 2028** — a direct, dated instrument for the Rome Statute art.
    8(2)(b)(viii) population-transfer framing; this part needs no
    correction. Also surfaces two new federal cross-references worth a
    future capture: Постановление Правительства РФ от 29.12.2022 №2501
    (DNR/LNR/Zaporizhzhia/Kherson federal-municipal property demarcation —
    the legal basis for transferring bezkhoz housing to *federal* ownership
    in some cases, Статья 3 п.2) and №2255 от 22.12.2023 (the federal
    reconstruction subsidy program funding the per-m² compensation rate,
    Статья 7 п.3) — not yet captured, not yet prioritized.
11. ~~**2% subsidized-mortgage law + Promsvyazbank trail**~~ — **PARTIALLY
    LOCATED 2026-06-28.** Confirmed: the program runs under federal
    government resolutions, with **Постановление Правительства РФ от
    15.12.2023 № 2166** verified on `pravo.gov.ru`
    (`publication.pravo.gov.ru/document/0001202312150019`, captured
    `scripts/197` — confirms title/number/date only, the page is a JS
    document-index shell, not the full text; full text needs the PDF
    download link, not yet chased) as an amendment to
    the housing/mortgage-lending rules covering ДНР/ЛНР/Запорожская/
    Херсонская — Промсвязьбанк confirmed as primary program operator
    (alongside Сбербанк/ВТБ), 2% rate, ≤6M ₽, ≥10% down, term extended (per
    Oct 2025 decision) to end-2030. **Still open:** the *original* launch
    resolution (signed by Mishustin, reported early Jan 2023, following
    Putin's 15.12.2022 strategic-council directive) — its number/date
    couldn't be pinned down from press coverage; №2166 is a confirmed later
    amendment, not the founding instrument. `scripts/197` also captures
    №2166's federal-portal page; finding the launch decree's exact number
    remains a residual sub-gap.
12. **Распоряжение №61** (Mariupol municipal lease rulebook, [CITED]) — PDF
    dead-linked on нпа.днронлайн; recoverable only via mariupol.gosuslugi.ru or the
    горуправление юстиции registry.

### C. Tier-3 corroboration layers never built (reconceptualization §3, Tier 3)

0. ~~**Bellingcat "Civilian Harm in Ukraine" timemap**~~ — **BUILT + LOADED
   2026-06-28** (user-supplied URL, not from the gap register — a new
   corroboration family). `scripts/198` captures the full feed (2,517
   records, country-wide, 2022-02-24→2025-07-09, hosted on a plain
   DigitalOcean CDN — not geoblocked, ran directly, no VPS handoff needed).
   `scripts/199` filters to the 21 Mariupol-tagged records and spatially
   joins to `property.geom`: **14 matched** within 100m (drama theatre,
   maternity hospital, "School 33," a kindergarten, several unnamed
   residential strikes — all March–June 2022, siege period), **7 correctly
   skipped** (mass graves, the airport, the seaport, a filtration camp, the
   Kuyindzhi gallery — all genuinely 150m–18km from the nearest spine
   property; force-matching these to a "nearest" property would have been
   false precision the source data doesn't support, so they're logged and
   excluded, not guessed). Loaded as `corroboration(kind='bellingcat_civharm')`,
   confidence capped at 0.4–0.6 (lower than UNOSAT's 0.8–0.95 — Bellingcat's
   geocoding is city-wide-approximate for most entries, not building-precise;
   this is corroborating *context* — independently OSINT-confirmed war damage
   near a property around a date — not a building-identity confirmation).
   `docs/STATS.md` regenerated: legal-grade 1,154→**1,156** (two properties
   newly cross the ≥2-source threshold). **This is the project's third fully
   independent provenance family**, alongside UNOSAT satellite analysis and
   the occupation/court/registry paper trail — sourced to Telegram/social-
   media/video evidence, with no relationship to either the occupier or to UN
   satellite imagery. Modest scope (siege-period general civilian harm, not
   seizure-specific) but genuinely new and already paying off at the margins.
0a. ~~**Eyes on Russia (CIR/Bellingcat/GeoConfirmed) map**~~ — **BUILT +
    LOADED 2026-06-28** (second user-supplied URL, same session). The
    documented public export (`eyesonrussia.org/events.geojson`, the route
    an archived community scraper repo relied on) is dead — that whole
    domain now 301s to a generic info-res.org landing page. The live map
    turned out to be an ArcGIS Experience Builder app; walked the public,
    unauthenticated ArcGIS sharing REST API from the Experience item down
    through its child web-map item to the actual data source — a public
    Feature Service, `EoR_completed_entries/FeatureServer/0`
    (services-eu1.arcgis.com), no API key or auth needed, not geoblocked.
    `scripts/200` captures a server-side-filtered query (Town_or_City LIKE
    Mariupol AND Primary_category='Civilian Infrastructure Damage' — 675
    records at capture time, deliberately excluding this feed's military-
    activity categories as out of scope for a property-seizure project).
    `scripts/201` spatially joins at the same 100m radius as the Bellingcat
    layer above, but with a higher confidence ceiling (0.5–0.7 vs 0.4–0.6)
    justified by a measured distance distribution (median nearest-property
    distance 28m, p90=121m — noticeably tighter geocoding than the
    Bellingcat feed). **491 matched across 358 distinct properties**, 184
    correctly skipped (beyond 100m, not force-matched). `docs/STATS.md`
    regenerated: legal-grade holds at 1,156 (this feed mostly lands on
    already-multi-sourced central-Mariupol properties rather than bridging
    new ones — real added evidentiary weight, just not new legal-grade
    crossings this round). **Fourth independent provenance family** —
    different organization (CIR, not Bellingcat alone), different
    underlying sourcing (mostly geolocated Twitter/X posts vs. Telegram),
    same independence from the occupier and from UN satellite imagery.
0b. ~~**GeoConfirmed Ukraine KML export**~~ — **BUILT + LOADED 2026-06-28**
    (sourced via the `osint-geo-extractor` PyPI package's downloader code,
    which documents the upstream feeds behind several of these maps —
    that package's own documented Bellingcat endpoint matched ours exactly,
    confirming both independently; its documented Cen4InfoRes/Eyes-on-
    Russia endpoint is the same dead route already found above). The
    package's documented GeoConfirmed endpoint
    (`/api/map/ExportAsKml/Ukraine`) is *also* dead — GeoConfirmed rebuilt
    their site as a Blazor app since that package's Jan-2024 release; the
    live equivalent (`/api/map/export/Ukraine`, found by probing plausible
    route variants) returns the same ZIP/KML shape. `scripts/202` captures
    the full country-wide export (57,561 placemarks). GeoConfirmed's feed
    is overwhelmingly front-line/military-movement tracking with no
    category field — `scripts/203` applies a Mariupol filter (474
    placemarks) AND a civilian-property-keyword filter
    (school/hospital/apartment/residential/building/church/civilian + RU
    equivalents) to stay in scope, narrowing to 94 candidates before any
    spatial join. Distance distribution measured first (median 79m,
    looser than Bellingcat/Eyes-on-Russia): confidence capped at 0.35–0.55.
    **56 matched, 38 correctly skipped** beyond the 100m radius. **Fifth
    independent provenance family.**
0c. ~~**Texty.org.ua "Under attack" shelling log**~~ — **BUILT + LOADED
    2026-06-28** (same package, `downloaders/texty.py`; public Google
    Sheets CSV export, not geoblocked). `scripts/204` captures the full
    country-wide CSV (~48,668 rows). `scripts/205` applies three filters
    before any join: Mariupol-mention (360 rows), a precision filter
    dropping whole-degree lat/lon rows (~21% of Mariupol rows are
    city-level-rounded, e.g. "47,38" — joining those would be the exact
    false-precision error this project's standing rule exists to prevent;
    284 rows survive), and Texty's own `civilian objects` flag (drops the
    airport and other military-infrastructure rows; 270 survive). Measured
    distance distribution is the loosest of any Tier-3 layer to date
    (median 161m, p90=1,504m — shelling-incident reporting, not
    photo-verified geolocation), so confidence is capped lowest yet
    (0.3–0.5). **98 matched, 172 correctly skipped.** The CSV's free-text
    `adress` column is carried into `detail` as context, not yet used for
    matching (candidate research-outsourcing task: a fuzzy-address pass
    against this field). **Sixth independent provenance family.**
    `docs/STATS.md` regenerated after all three new layers (202–205):
    legal-grade holds at 1,156 — these layers add corroborating weight to
    already-multi-sourced central-Mariupol properties rather than bridging
    new ones into legal-grade this round, consistent with 0a above.
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

16. **8,303 court-record islands** (region-wide, see `docs/STATS.md`) carry
    `<адрес>` redaction at source and no non-court record references the case
    number — unbridgeable by address/cadastral/geometry *via this portal*. They
    stand as primary evidence on the case record itself. (Item 9 is the only
    possible escape hatch.)
19. **The "already-transferred-via-court" population is invisible to the
    ownerless registry, by construction — not by overlap.** *(Recomputed
    2026-06-28 against the full region-wide population — supersedes the
    original Mariupol-only figures below.)* Of the 8,303 court-record islands,
    **7,052 reached `court_transfer`** (court ruled in favor of "признание права
    муниципальной собственности" — i.e. the unit left "ownerless" status via the
    now-abolished court route, *before* the live 12,948-entry / 1,637-property
    ownerless registry was even queried). Because these 7,052 rows carry no
    address (see item 9), they show **zero property overlap** with the
    1,637-property registry_inclusion set — confirmed again at full scale, so
    this is not an artifact of the smaller Mariupol-only sample: nothing to
    match on, not evidence the two populations are genuinely disjoint.
    Net effect: **we can state a count (≥7,052 units already converted to
    municipal property via the old route) but cannot map any of them to a
    specific address/RD4U category**, and the one register that could
    (Реестр муниципального имущества городского округа Мариуполь) is not
    publicly accessible. This is the accountability-side fact ("at least 7,052
    units stripped of owner status, region-wide") that currently has no
    restitution-side (per-property RD4U) counterpart. Closable only via item 9.
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

### 6a. Registry/decree feed freeze, 2026-06-06→06-28 — DOUBLE-CONFIRMED, unexplained

Two independent lines now agree: as of this report's writing (2026-06-28), the
expected pre-deadline acceleration (+100–200/week, §6 above) **has not materialized
— the opposite has happened.**

- **Mechanical (this project's own re-crawl, 2026-06-28).** Re-running
  `scripts/05_crawl_ownerless_lists.py` 19 days after the prior capture
  (2026-06-09) found **zero new content**: all four district registry XLSX
  files are byte-identical (same SHA-256 hashes, only `captured_at` advanced);
  every decree-type `source_document` count is unchanged (designation=36,
  removal=39, procedure=23, unknown=46, demolition_declaration=3), with raw
  capture timestamps still pinned at 2026-06-09. (The crawl log's "N new
  decrees" pagination counter is a within-run dedup artifact, not a novelty
  signal — see `src/mariupol_seizures/crawl/ownerless_lists.py`'s
  `forensics.is_done()` skip-logic; verified by direct code read, not
  assumption.) A follow-up OCR backlog pass (`scripts/06a_ocr_decrees.py`)
  confirms this: the 23 PDFs it OCR'd for the first time were all *already
  captured* on 2026-06-09 (dated mostly 2024–early 2025, two removal decrees
  dated 9 June 2026) — clearing a derived-text backlog, not discovering new
  source material.
- **Independent (user-sourced, Telegram).** The `@mariupol_nash` channel
  — not currently a tracked source in this project (absent from
  `src/mariupol_seizures/chat_buildings.py` and the channel docs) — last
  posted a fresh batch of "ownerless" (бесхозяйный) property listings on
  **2026-06-06**. The user confirmed this via a direct, бесхозяйный-scoped
  search of the channel (not a casual skim), and reports **no explanation
  given** for the silence since.

Two independent sources, three weeks apart in coverage, converge on the same
window. The one nuance the OCR pass surfaces: two removal decrees are dated
9 June 2026 — three days *after* mariupol_nash's last designation batch — so
the freeze appears specific to **new designations** (the front end of the
pipeline that mariupol_nash and the registry XLSX both track), not to
**removals** (the back end, transfer-consummation), which may still be
processing previously-designated cases. Neither source explains *why* new
designations stopped. Candidate explanations — administrative pause ahead of
the 1 July transition, a backlog being held for a post-deadline bulk release,
an unrelated publication outage — are all unverified speculation; this section
records the finding, not a cause. **Action:** keep the weekly re-snapshot
cadence (§6) running through and past 1 July specifically to catch whichever
of these it turns out to be — a sudden post-deadline surge would itself be
informative. Flag `@mariupol_nash` as a candidate addition to the tracked-channel
list — it independently corroborates the registry feed and may carry decree
detail the four-district XLSX doesn't.

---

## 7. Recommended priority order

1. **Stand up the post-1-July registry re-snapshot cadence** (§6) — time-critical;
   the wave is imminent and the window to capture it as a *flow* is now.
2. ~~**Resolve the `ej.sudrf.ru` discovery question**~~ — **SETTLED
   2026-06-28, negative** (§5 item 9). The 2,657+-island address gap is
   confirmed permanently unbridgeable through any sudrf.ru-family source;
   redirect remaining effort on those islands to Tier-3 corroboration
   (satellite/registry) instead.
3. ~~**Close the build-ready cluster**~~ — **DONE 2026-06-28** (§5 items
   0, 1, 2, 3, 4, 5, 6, 8 — see each item above). §5A is now fully closed.
4. ~~**Capture the two biggest uncaptured federal norms**~~ — **SOURCES
   LOCATED 2026-06-28** (§5 items 10–11). The 25 m² cap is Закон №269-РЗ
   (Rome Statute 8(2)(b)(viii)-relevant: 1 Jan 2028 deadline for issuing
   seized housing to officials/military/imported staff), already
   independently corroborated via the federal `pravo.gov.ru` mirror. The 2%
   mortgage program's confirmed amendment (Постановление №2166, 15.12.2023)
   is located; the original launch decree number is a residual sub-gap.
   `scripts/197` captures both PDFs — **handoff to user (VPS), not yet run.**
5. **Prototype the per-property RD4U dossier export** (§5 item 20) — turns the spine
   into the actual claimant deliverable.
6. **Tier-3 corroboration** (§5 items 13–14) and **parallel-dataset outreach**
   (§5 item 19) as parallel, lower-urgency tracks.

---

*Forensic note: every occupation/DNR/federal normative act and registration in this
project is evidence of the seizure system, NOT valid title. Ukraine does not
recognize them; neither do we. Capture before parse; SHA-256 + UTC timestamp +
source URL on every artifact (CLAUDE.md).*
