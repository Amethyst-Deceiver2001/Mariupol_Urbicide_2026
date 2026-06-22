# Integrity review — visual-narrative exhibits (2026-06-13, rev. 2)

**Rev. 2 note:** the original review (same day) found F4's UNOSAT claim
undone. UNOSAT ingest has since been BUILT + RUN (scripts 52–53) and F4 is
now **RESOLVED** with real numbers — see the updated F4 below. This also
moves F1's legal-grade figure a second time (881 → **1154**) and adds a third
family to F3's picture. No exhibit files have been edited yet — this document
is still the thing to paste back to the conversation iterating on the
artifacts, now current as of the UNOSAT run.

Reviewed against the live PostgreSQL evidence spine (`mariupol_seizures` @
`localhost:5433`), `data/parsed/*.jsonl`, and project memory/docs. Files now
live in `docs/exhibits/`:

- `00_preamble_archons_house.md`
- `mariupol-master-dossier.html`
- `nakhimova-82-exhibit.html` ("Exhibit A")
- `case-study-II-registry-resale.html` ("Exhibit B")
- `dispossession-pipeline.html` (self-labels "Exhibit B" — collision, see F9)
- `stakeholder-network.jsx` ("Exhibit C")

This doc is written so it can be pasted back to the conversation that is
iterating on these artifacts. Each item: **what's there now → what's wrong →
what it should say**, with the evidentiary basis.

---

## CRITICAL — factual corrections

### F1. Stale hero numbers in `mariupol-master-dossier.html`
Banner (`<div class="bstat">` ×2, lines ~379/573) and stat cards read:
- `5,964` "properties on the evidence spine"
- `819` "legal-grade · 2+ independent sources"

**Current DB state (rev. 2, 2026-06-13 post-UNOSAT):** `property` count =
**6,055** (unchanged); legal-grade (≥2-source corroboration) = **1154**. The
number has now moved *twice* today: 819 → 881 (MinStroy demolition-parser
fix, earlier today) → **1154** (UNOSAT ingest, scripts 52–53, this run — see
F4). The exhibit predates both.

**Fix:** `data-count="5964">5,964` → `data-count="6055">6,055`; `819` →
**`1154`** (all instances, including the JS `countUp` `data-count`
attributes). If there's any appetite for it, this is the second time this
exact stat has drifted within one day — consider computing it from a small
JSON sidecar written by script 33 at publish time rather than hardcoding it.

### F2. "2,666 occupation court transfers" mislabels case *count* as *outcome*
Banner stat + timeline card (master dossier, lines ~381, ~512) both say
**"2,666 court transfers"** / "occupation court transfers".

**Reality:** 2,666 is `court_case` total (all dockets, any outcome). The
`court_transfer` (granted) stage count is **2,192**. Conflating the two
overstates the granted-transfer figure by ~22%.

**Fix:** relabel to **"2,666 court cases"** (matches
`dispossession-pipeline.html`'s own stage-B card, which already correctly
says "Court cases · 2,666 cases" — the two exhibits currently disagree with
each other on this).

### F3. "2 provenance families … UN damage data + satellite" mischaracterizes the corroboration that actually backs the legal-grade count
Two locations in the master dossier make this claim:
- Section 07 stat card: *"Corroboration · 2 provenance families · Occupation
  records cross-checked against an independent family — UN damage data +
  satellite — so the case does not rest on enemy paperwork alone."*
- Section 10, RD4U row: *"A3.1 / A3.2 … the demolition track, corroborated by
  UN & satellite data."*

**Reality at original review time** (per `cross_source_corroboration.md`): the
two families that produced the 881 legal-grade properties were `mirror_source`
(the **Russian federal damage/reconstruction tracker**, 1,766 rows) and
`displacement_claim` (housing-distribution lists, 430 rows). Both
occupation/federal-side — **not** independent UN or satellite data. The
genuinely independent satellite/UN layer was a separate, near-empty effort
(see F4).

**Rev. 2 update (post-UNOSAT, this run):** F4 is now resolved, so there
genuinely IS a third, independent `independent_corroboration` family
(`unosat_damage`, 594 properties) — but it is **one of three** families in
play, not a clean "2 families" story, and most of the 1154 legal-grade total
still comes from the *occupation-side* pair above. Family co-occurrence among
legal-grade properties (script 33, this run): `damage_assessment` ×
`ownerless_registry` = 514, `damage_assessment` × `independent_corroboration`
= 491, `demolition` × `housing_distribution` = 291 — i.e. the UNOSAT family
pairs heavily with the federal damage tracker (491 properties), but the
federal-tracker/registry pair (514) and demolition/housing pair (291) remain
larger or comparable, and are occupation-side-only.

**Fix:**
- Section 07 card → don't claim "2 provenance families" generally. Either (a)
  describe the real occupation-side pair as in the original fix *and* add a
  **separate, additional** sentence/badge for the new UNOSAT family — e.g.
  *"Of the 1154 legal-grade properties, 491 are additionally confirmed by an
  independent UN satellite damage assessment (UNOSAT, 12 May 2022)"* — or (b)
  reframe the card around "up to 3 independent families" with a short
  breakdown. Don't drop the UN/satellite claim entirely as the original F3
  fix suggested — it's now true for a real subset, just not the whole 1154.
- Section 10's A3.1/A3.2 row → *"the demolition track, corroborated by the
  federal damage tracker and, for 193 of those properties, an independent
  UNOSAT satellite damage assessment"* (the 193 figure is the
  `demolition` × `independent_corroboration` co-occurrence count).

### F4. UNOSAT "spatially joined to each property" presents undone work as done — **RESOLVED 2026-06-13 (rev. 2)**
Section 08 ("Independent verification", correctly badged "Wave 1 · in
progress") includes the card: *"UN damage attestation — UNOSAT
building-level vectors (May 2022, 5,647 structures) spatially joined to each
property — an independent UN analyst record of war damage at a fixed date."*

**Original finding:** no UNOSAT data had been acquired — `tier3_corroboration_
design.md` recorded UNOSAT/HDX scripts (52–58) as "reserved, NOT implemented."
Independent satellite corroboration covered **2 of ~6,055 properties** (the
Wayback/Sentinel pilot AOIs).

**Now true** (scripts 52–53, built + run this session): the 12-May-2022
UNOSAT building damage assessment (HDX/CERN, dataset code CE20220223UKR,
CC-BY-SA) was captured forensically (SHA-256 + `.meta.json`, 5 zips in
`data/raw/`) and spatially joined to `property.geom` (`ST_DWithin` 25m,
nearest-wins). Results, loaded as `corroboration(kind='unosat_damage',
verdict='confirms')`:

- **5,643** building-level damage features parsed (of 5,660 total in the
  layer; 17 "Impact Crater" road/field features excluded as non-buildings —
  the dataset's documented "5,647 structures" headline is within 4 of this).
- **594 / 1,961** geocoded properties matched within 25m (**30.3% hit rate**):
  266 at ≤10m (confidence 0.95), 328 at ≤25m (confidence 0.80).
- Each match carries the UNOSAT damage class (Destroyed / Severe / Moderate /
  Possible), analyst, confidence label, and the 12-May-2022 sensor date.

**Fix:** the card's *premise* is now correct — change "Wave 1 · in progress"
to "Wave 1 · done" (or similar) for this card specifically (other section-08
cards, e.g. satellite-pair bracketing, are still pilot-stage and should keep
their in-progress badge), and replace the text with the real figures, e.g.:

> *"UN damage attestation — UNOSAT building-level damage assessment (12 May
> 2022, ~5,647 structures), spatially joined to the property spine: **594 of
> 1,961 geocoded properties** (30.3%) matched within 25m to an independently
> assessed war-damaged structure — an independent UN analyst record of war
> damage at a fixed date, with no relationship to the occupation
> administration."*

Do not say "joined to each property" (594, not all 6,055/1,961) or imply
March-2022/26-March datasets are also loaded — only the 12-May-2022 layer is.

### F6. `nakhimova-82-exhibit.html` "06 · Legal mapping" RD4U categories are wrong
Currently: *"Category A3.6 — loss of access… Categories A3.1 / A3.2 —
destruction of residential property."*

**Reality:** property 5865's stored `rd4u_category` = **`A3.1,A3.3,A3.6`**.
A3.2 (non-residential destruction) does not apply to a residential building;
A3.3 (loss of housing) is the actual second category and is missing entirely.

**Fix:** *"A3.1 — destruction of residential property. A3.3 — loss of
housing/residence. A3.6 — loss of access to property in occupied
territory."*

### F7. (NEW) `case-study-II-registry-resale.html` "[RENAMED · Указ №301]" overstates the rename's provenance
Building 02 (просп. Ленина 100, property 7242) is tagged *"← prewar: просп.
Миру, 100 [RENAMED · Указ №301]"*, and the narrative says the rename is
"exactly as documented in the toponymy layer (rung [H])."

**Reality:** Указ Главы ДНР №301 (20.06.2022) is the **DNR-wide
renaming-*authority* framework** — it delegates renaming power to city
administrations but does not itself rename any street. Per
`docs/legal_mechanisms_review.md` (line 199), the actual **Mariupol
street-renaming decrees are confirmed absent** from every searched portal —
they're a documented crawl gap. The toponym table *does* carry a
Миру→Ленина "rename" row, but its `source_ref` is a **Bellingcat article**,
not Указ №301 or any captured decree.

**Fix:** retag as *"[RENAMED · per Bellingcat / toponymy layer — underlying
Mariupol decree not yet captured]"*, or simply *"[RENAMED]"* with the
Bellingcat citation in the source line. Don't cite Указ №301 against this
specific street — it's the enabling framework, not the act. (This exhibit's
own caution is otherwise good — `dispossession-pipeline.html`'s stage-H card
already correctly badges the street-renaming decrees as "Reported"/"Crawl
gap"; this tag should match that honesty level.)

---

## MEDIUM

### F5. Raw-artifact volume stat is stale and will keep drifting
Master dossier says **"39,061 raw artifacts · 5.6 GB raw store"** (banner +
section 07 card) — this matches CLAUDE.md's last recorded snapshot, but a
live count at original-review time was **44,142 files / 5.9 GB** (~13% growth
from that session's new Sentinel-2 + Esri Wayback tile captures).

**Rev. 2:** drifted again (as predicted) — now **44,147 files / 5.9 GB** (+5
from this session's UNOSAT zip captures). Same-day, third distinct value for
one stat is the demonstration case for the fix below.

**Fix:** either recompute at publish time (`find data/raw -type f ! -name
"*.meta.json" | wc -l` and `du -sh data/raw`), or — since the banner already
has a "The record — accumulating" live `countUp` treatment and a countdown
timer — make this stat genuinely live-computed rather than a hardcoded
constant, so it doesn't silently go stale again.

### F8. Stage F "Resale" claims DB residency it doesn't have yet
`dispossession-pipeline.html`'s endpoint table lists stage **F · Resale → DB
stages: `resale`**, and the master dossier's footer says *"Property,
registry, court, land-order, and resale evidence: the project's captured
artifact store and **PostGIS evidence spine**."*

**Reality:** `resale` *is* a defined value in the `seizure_stage` enum
(`db/schema.sql`), but **0 rows** in `seizure_event` currently carry it. The
225 on-spine Telegram offers (and the Nakhimova "94.3% sold" figure) live
only in `data/parsed/realestate_offers.jsonl` / the ЕИСЖС registry record —
they have not been loaded into Postgres.

**Fix (pick one):**
- Exhibit-side (quick): annotate stage F's source-status badge as "Captured
  + parsed — not yet loaded to spine" rather than implying parity with the
  other DB-resident stages; soften the dossier footer's "resale evidence: …
  PostGIS evidence spine" claim.
- Pipeline-side (better, but separate task): write a loader (next free script
  slot, 59+) that inserts `stage='resale'` `seizure_event` rows from
  `realestate_offers.jsonl` for the 225 on-spine offers, with `event_actor`
  links where a seller/agency is identifiable. This would make F8 disappear
  and slightly increase legal-grade/corroboration counts.

### F9. "Exhibit B" labeling collision
Both `dispossession-pipeline.html` and `case-study-II-registry-resale.html`
self-identify as **"Exhibit B"**. `nakhimova-82-exhibit.html` = Exhibit A,
`stakeholder-network.jsx` = Exhibit C.

**Fix:** `case-study-II-registry-resale.html` is the natural "Exhibit B"
(parallel case study to A) — leave it. Relabel
`dispossession-pipeline.html`, which is shared scaffolding referenced by both
case studies ("Trace a real building" links from A and B point into it), as
**"Exhibit D"** or drop the letter entirely (e.g. "System Map" / "Reference:
The Dispossession Pipeline").

---

## MINOR / cosmetic

- **94% vs 94.3% (Нахимова exhibit):** the summary/hero sections (lines ~26,
  41, 139–140) round to "94%" while the stage-05 detail (lines ~93–94) uses
  the precise "94.3%" — both correct, but inconsistent in a forensic
  document where every other figure is exact. Standardize on **94.3%**
  throughout.
- **"225 … across 70 buildings"** (case-study-II footer, and
  dispossession-pipeline). Recomputing `building_key` distinctness on the 225
  on-spine offers in `realestate_offers.jsonl` gives **66**, not 70. Minor
  (~6%) drift, likely from an earlier scan iteration — recompute at publish
  time.
- **"~27 named judges"** (master dossier §06) vs. the 28 judicial-tier
  `person` nodes actually present in `stakeholder-network.jsx`'s embedded
  `NETWORK.nodes`. Within "~" tolerance, but if precision is wanted, it's 28.
- **Beneficiary director-name conflict not surfaced.** Nakhimova exhibit
  "05 · Beneficiary of record" presents ООО «СЗ-1 «Порфир»» facts
  unconditionally, but `demolition_rebuild_address_laundering.md` flags an
  unresolved EGRUL director-name conflict (Рассказов Богдан Денисович vs.
  Карпов Владимир Николаевич) for this entity. Doesn't need to go in the
  public exhibit, but if a footnote caveat is added elsewhere in the project
  for this beneficiary, this exhibit should match it.

---

## External/historical citations — outside DB-verification scope

Items 09 ("Not an aberration. A method.") and the Loizidou/Crimea/Rosreestr
section, plus the RIA Novosti / Regina Orekhova / Alexey Kovalev citations in
section 01.5, cite external sources (ECHR case law, Crimea land-ownership
figures, Rosreestr/Le Figaro totals, a named RIA Novosti documentary and a
Kovalev analysis piece). These are **not derivable from this project's
data** and I cannot fact-check them without web access this session.
Loizidou v. Turkey (ECHR, merits judgment 1996, continuing-violation holding
on property denied since 1974) is consistent with general legal knowledge.
The rest — exact Crimea ownership figures (13,859 → ~5,500), the "~550,000"
Rosreestr/occupied-Ukraine total, "~13,000" Le Figaro Mariupol figure, and the
RIA Novosti documentary's exact title/date/award — are plausible and
internally well-attributed, but **the design layer should independently
verify these citations before publication**, since they're presented with
the same evidentiary weight as the project's own SHA-256-backed claims.

---

## Pipeline-side gap surfaced during this review (not an exhibit error)

While checking master-dossier §06 ("Who operates it" — Кольцов "652
ownerless + 16 demolition decrees", Моргун "156 ownerless decrees"): **these
numbers are correct** relative to source (`data/parsed/ownerless_decrees.jsonl`:
652 Кольцов / 156 Моргун of 968 total; `demolition_decrees.jsonl`: 16/1 of
20). **Do not change them.**

But cross-checking against `seizure_event`/`event_actor` found only **604**
`ownerless_designation` events total, **all** attributed to Кольцов — **zero**
attributed to Моргун. His entire ~2.5-year tenure (23.01.2023–12.06.2025,
156 decrees) is currently invisible in the property-level seizure timeline,
and 48 of Кольцов's 652 (≈7%) are also missing. Demolition linkage (16+1=17)
is fine.

This sits awkwardly next to the dossier's "loaded to PostgreSQL/PostGIS"
framing, but fixing it is a **loader task** (likely script 27/28 area per
`db_loader_architecture.md`), not an exhibit-text change — flagging here so
it isn't lost, separate from F1–F9 above. Loading the missing 364 decrees
(156 Моргун + 48 Кольцов + 160 other-signer) would likely add new
`seizure_event` rows, and possibly new properties/legal-grade rows, which
would in turn bump F1's 6,055/881 again.

---

# Rev. 3 update (2026-06-14) — status check + new material

**Status check on rev. 2:** re-ran script 33 live against the DB today.
`properties=6055`, `legal-grade(>=2 families)=1154`, `court-islands=2657`,
family coverage unchanged from rev. 2's figures. **No DB-side changes since
rev. 2** — F1's target numbers (6,055 / 1154) are still correct.

**None of F1–F9's fixes have been applied to the exhibit files yet** (checked
by grep: master dossier still says "5,964"/"819"/"2,666 court transfers";
`nakhimova-82-exhibit.html` still says "A3.1 / A3.2" not "A3.1 / A3.3";
`case-study-II-registry-resale.html` still cites "Указ №301"). All of F1–F9
remain outstanding and should be batched with the new items below.

This section adds **new material gathered 2026-06-13/14**, for the same
paste-back conversation. Nothing below has touched the exhibit files either —
this is a punch list of new content + where it should go.

## A1. New stakeholder-network nodes/edges (Exhibit C, `stakeholder-network.jsx`)

From the @Lenina133 resident-chat scrape (1311 msgs / 487 media, scripts
62–63; see project memory `lenina133_resident_chat_scrape_2026-06`). Current
network = **111 nodes / 138 edges / 52 persons**. New named individuals not
yet present:

- **Татаренко Владислав Вячеславович** — ФКРМО ЦУП project lead (ООО
  «РКС-НР»). Identity now confirmed by **two independent sources**: the
  npa.dnronline.su decree (found earlier this project) and the Lenina133
  chat itself (msg 1363, 25 Mar 2026). Accused of certifying a
  тепловой-контур-only repair (ПВР-grade) as a full "СТРОИТЕЛЬСТВО" project
  passport, then handing the building to city balance with known structural
  defects in 2023, shortly before Моргун (existing node) was replaced.
  **Edge candidates:** `Татаренко -[project_lead]-> ООО «РКС-НР»`,
  `Татаренко -[handed_building_to]-> Моргун О.В.` (existing node).
- **Климов Вячеслав Александрович** — специалист отдела земельных отношений,
  Администрация ГО Мариуполь. Led a 4-person visit pressuring an elderly
  resident (separate apartment, open inheritance case) into signing a
  municipal-property statement (Nov 2025). **Not the same person** as the
  existing node "Климова С.Ю." — different patronymic, different role; verify
  before any merge.
- **Солодуха Галина Юрьевна** — gave Климов phone instructions during the
  same incident.
- **Бакушин** (surname only) — named as responsible for misrepresenting
  facade-work status; allegedly absent from the prosecutor's-office oversight
  file (Филимонов/Савранский/Гнездилов — Гнездилов already a network node).
- **Калачева** (surname only) — named alongside Дмитриев in a Dec 2025
  written response from "администрации Кольцова". New node.
- **Дмитриев А.В.** — **already a network node** (ownerless-decree signer).
  This is an additional citation of the same person in a different context
  (Dec 2025 response, Kolʹtsov administration) — add as a new edge/evidence
  item on the existing node, not a new node. (Verify same person, not a
  namesake, before merging the citation.)
- **Шихов** (surname only) — МК ГРУПП representative who submitted the
  "стяжка on sand-core walls" repair project for approval (sister-building
  Строителей 101 defect pattern, see `lenina133_resident_chat_scrape_2026-06`
  finding 6).

### Privacy flag — do NOT add as named accountability nodes without minimization
Two more names appear in the same material but **fail CLAUDE.md's privacy
test** (they are residents/occupants, not "occupation officials, judges, or
beneficiaries acting in official capacity"):

- **Полозенко** — a resident who self-appointed as "старшая по дому" (no
  legal standing per the chat) and signed a contractor-liability waiver "on
  behalf of residents" (Oct 2025).
- **Голубченко** — reportedly the occupant of apt 19 (sealed Oct 2025,
  corroboration id 5417) as of Mar 2026, a friend of Полозенко, said to be
  directing restoration negotiations.

Both are *relevant to the reallocation/[F] narrative* (Rome 8(2)(b)(viii)),
but as private individuals they should be **pseudonymized/generalized** in
any public-facing exhibit — e.g. "a resident who self-appointed as the
building's representative" / "an unidentified occupant of the sealed unit,
reportedly a contact of the self-appointed representative" — with full names
kept only in internal memory/case-study drafts, not in `stakeholder-network.jsx`
or any HTML exhibit.

## A2. New case-study material for building 4442 (пр. Ленина/Мира 133) — not yet in any exhibit

`docs/case_studies/lenina133_apt19_sealing.md` already exists (Exhibit-adjacent,
not yet surfaced in the HTML exhibits) and has a 2026-06-13 addendum resolving
the "100% destruction" conflict (corroboration 5418, `verdict='refutes'`).
New material from 2026-06-14 triage, **not yet written into any addendum or
loaded to `corroboration`**:

- Apts **2 and 33** (in addition to 19) were also sealed "ОПЕЧАТАНО" around
  23 Oct 2025, with the same vacate-notice phone number, which was later
  disconnected. Apt 2 is already `seizure_event` id 37358
  (registry_inclusion); apt 20 remains unaccounted for.
- A **city-wide systemic-fraud allegation**: fake general-meetings used across
  "ВСЕ АВАРИЙНЫЕ ДОМА МАРИУПОЛЯ" to certify substandard repairs and appoint
  illegitimate "старшие по дому" (generalizes the Lenina-133-specific waiver
  story to a citywide pattern — cf. sister building **пр. Строителей, 101**,
  same contractor МК ГРУПП, independent wall-defect complaint, ~2 years in
  court).
- A **funds-diversion narrative**: the building's official "паспорт объекта"
  was issued for full "СТРОИТЕЛЬСТВО" (new construction — same passport as
  corroboration 5418/1412) while the delivered scope was only the
  тепловой-контур (ПВР-grade), then handed to city balance in 2023.
- An **escheated-property fraud-scheme warning** ("СКОРО В МАРИУПОЛЕ", 26 Nov
  2025) describing a St. Petersburg "lzhe-vnuk" scheme as a preview for
  Mariupol, plus an active prosecutor's-office ownership survey of residents
  (Jan 2026) and a resident's own estimate that "half the city's housing"
  remains formally `бесхоз` because Ukrainian owners lack RF passports.

**Where this goes:** a second addendum to `lenina133_apt19_sealing.md`
("Addendum 2: systemic fraud + funds diversion") is the natural home; the
apt 2/33/20 sealing detail and the Голубченко reallocation lead could also
support a new section in `dispossession-pipeline.html`'s stage-F (reallocation)
card, **with the privacy caveat from A1 applied**. None of this is loaded to
`corroboration` yet (verdict would be `indeterminate` — allegations not yet
independently verified).

## A3. Нахимова 82 testimony addendum — ready-to-paste Exhibit A additions

`docs/exhibits/nakhimova82_testimony_addendum.md` (captured 2026-06-13,
script 59) is **fully drafted and ready to insert** into
`nakhimova-82-exhibit.html` ("Exhibit A"):

- New timeline marker, **27 Dec 2023** — a resident's first-person Telegram
  complaint (180K views, t.me/olegtsarov/9754) describing exactly the
  demolish→mortgage-sale pattern the administrative chain (legs 3–5) proves
  from the other direction — two days *before* the replacement building's
  29 Dec 2023 commissioning date.
- New timeline marker, **3 Oct 2025** — AGO Mariupol's head of
  city-planning/architecture, **Наталья Клочкова**, publicly cites the
  *replacement* building (named "Нахимова, 82") winning an architecture-award
  bronze diploma, with a quote about "transforming Mariupol into a modern
  comfortable **Russian city**" — a named official, on the record, directly
  usable for the Rome Statute 8(2)(b)(viii) framing.
- Suggested pull-quote location: master dossier / preamble, near the existing
  population-transfer framing.

This is the lowest-effort high-value item in this update — content is
already written, just needs to be placed into the HTML.

## A4. Tier-3 imagery — section 08 status (do not overclaim)

- **`volgodonska_azovstalska_block`** (Esri Wayback hi-res, scripts 57–58,
  ~0.81m/px): visually striking before/during/after sequence (intact green
  block 2022-02-24 → scorched/rubble 2023-06-13 → partial repair 2026-05-28),
  matching the kind of image the project owner asked for — but **verdicts are
  not yet human-reviewed or loaded as `corroboration`**. Of its 13 member
  properties, 6/13 now have demolition-track linkage (post MinStroy-parser
  fix); the other 7 plausibly damaged-but-retained, not razed.
- **Two new demolish→rebuild pairs** found in the wave-1 satellite worklist
  (scripts 54–56): `artema_150_metallurgov_1` (props 4741↔6341, → ЖК
  "Ленинградский квартал") and `kuprina_69_lazurnye_berega` (props 4947↔6336,
  → ЖК "Лазурные берега") — candidates for their own mini-case-study cards
  alongside Nakhimova 82, but **not yet written up**.
- **Fix guidance:** if section 08 is updated this pass, keep its "Wave 1 · in
  progress" badge for these items (only the UNOSAT card, F4, is "done"). Do
  not present the Wayback chips or the two new pairs as loaded/verified —
  they are pilot imagery awaiting `scripts/59_load_satellite_verdicts.py`
  (not yet written; next free slot is 64+, since 59–63 are now used by the
  Lenina133/Nakhimova work).

## A5. Mass registry-to-resale — fully-written case study with no exhibit yet

`docs/case_studies/mass_registry_to_resale.md` is complete: 3 buildings
(просп. Строителей 108 / просп. Ленина 100 / ул. Сеченова 54), **131
individually-registered "ownerless" flats**, with specific units reposted
8–20× on Telegram resale channels May–Jun 2026 (one unit reposted 13× across
two channels). This has **no corresponding HTML exhibit** — candidate for a
new exhibit (the natural next letter is "Exhibit E", since D is reserved for
`dispossession-pipeline.html` per F9) or a new stage-F section in
`dispossession-pipeline.html`, with the same **F8 caveat** (resale data is
captured/parsed, not yet loaded to `corroboration`/`seizure_event`).

## Suggested batching for the app-designer pass

1. **Mechanical, low-risk:** F1, F2, F5 (numeric/label drift — recompute and
   replace).
2. **Narrative rewrites:** F3, F4 (section 07/08 provenance-family framing).
3. **Targeted fixes:** F6, F7, F9 (Exhibit A RD4U categories, Exhibit B
   toponym citation, Exhibit D relabeling).
4. **A3** — drop the two ready-made Nakhimova timeline markers + Klochkova
   pull-quote into Exhibit A. Lowest effort, highest narrative value.
5. **A1** — add the 6 new stakeholder-network nodes/edges (Татаренко,
   Климов, Солодуха, Бакушин, Калачева, Шихов) to Exhibit C, **applying the
   A1 privacy flag** (do not add Полозенко/Голубченко by name).
6. **A2 / A5** — largest net-new content (new addendum + new exhibit); do as
   a separate pass once 1–5 are settled.
7. **A4** — defer until satellite verdicts are human-reviewed and loaded;
   don't reference in this pass beyond the "in progress" badge.
