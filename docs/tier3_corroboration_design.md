# Tier-3 Corroboration Layer — Design (2026-06-12)

Design for the never-built Tier-3 layer from `docs/reconceptualization_2026.md`
§3 ("Tier 3 — Corroboration sources") and gap-register items 13–14 in
`docs/progress_report_2026-06.md`. Script numbers 52–58 are reserved by this
document.

**Status (2026-06-13): S1 (scripts 52–53, UNOSAT ingest, wave 2) is BUILT +
RUN** — see §3 S1 and §6 wave 2 for results (594 new `unosat_damage`
corroboration rows; legal-grade count 881 → **1154**). S2/S3 wave-1 pilots
(satellite bracketing + Wayback hi-res, ~10 flagship AOIs) were also built+run
in a prior session under different script numbers (54–58) — see
`tier3_wave1_satellite_pipeline.md` / `tier3_wayback_hires_pipeline.md` in
project memory; reconciling those script numbers against this document's
table (§5) is follow-on work. S4–S7 remain design-only.

---

## 1. The problem this layer solves

The evidentiary spine (5,964 properties, 39,061 raw artifacts) is built almost
entirely from **the perpetrator's own records**: occupation courts, occupation
registries, occupation decrees, Russian federal trackers. That is its great
strength — the records are self-incriminating, dated, and signed — and its one
structural weakness: **everything shares a single provenance family.** A
defense (or a skeptical Claims Commission reviewer) can attack the whole
edifice with one argument: "these are unverified enemy-side documents."

The `corroboration` table already exists in `db/schema.sql` and holds 2,196
rows — but on inspection **every one of them is also occupation-provenance**:

| kind | rows | actual source |
|---|---|---|
| `mirror_source` | 1,766 | Russian federal damage/reconstruction tracker (script 32) |
| `displacement_claim` | 430 | occupation housing-distribution lists (script 28/29 path) |

These are *cross-source* corroboration (different occupation organs agreeing),
which is valuable, but they are not *independent* corroboration. Tier-3's job
is to add a **second, independent provenance family** — UN analysts, satellite
sensors operated by ESA, pre-war Ukrainian data, published testimony — that
either confirms or refutes what the occupation paper trail asserts.

What independent corroboration buys, per endpoint:

- **RD4U / Claims Commission:** A3.1 (destruction) claims are routinely
  supported by remote-sensing evidence; an UNOSAT damage point + a dated
  satellite pair attached to a property turns "the occupation's own tracker
  says 60% destroyed" into a two-family evidence package. A3.6 (loss of
  access) benefits from the *intactness* finding (building stands, owner
  locked out).
- **Rome Statute:** art. 8(2)(a)(iv) / (b)(xiii) require proof of the
  *physical element* — that destruction/appropriation actually occurred, when,
  and at scale. Imagery dates the demolition between two scenes; UNOSAT dates
  the war damage; together they prove the sequence *war-damaged → standing →
  administratively razed → rebuilt for the occupier's market* that no paper
  record alone can.

**Core epistemic rule:** a corroboration row never asserts ownership or legal
state. It asserts either *physical state at time T* (intact / damaged / rubble
/ cleared / new structure) or *independent attestation* (a UN analyst, a
witness, a Ukrainian registry said X about this address). `indeterminate` is a
recorded verdict, not a discard — and `refutes` is a first-class finding (if
imagery shows a building standing that the demolition register says was razed,
we need to know).

---

## 2. Ground truth this design stands on (verified 2026-06-12)

**Internal (queried from the live DB):**

- 1,961 / 5,964 properties have `geom`. Coverage is very uneven by track:
  - demolition cohort: **282 / 294 geocoded (96%)** — satellite-ready today;
  - reallocation (land grants): 16 / 16;
  - registry_inclusion buildings: 520 geocoded;
  - ownerless_designation: 59;
  - the broader multi-stage court cohort is mostly *un*geocoded (67 / 2,284) —
    geocoding (scripts 22–25, user-run) is the bottleneck for any expansion
    beyond the cohorts above.
- Demolition `event_date` spans **2022-08-09 → 2026-05-20**, all 294 dated —
  ideal for before/after bracketing.
- Flagship coordinates on file: Нахимова 82 / Черноморский 1Б =
  `47.0760, 37.5125` (case study `nakhimova_82_chernomorsky_1b.md`, which
  already lists its needed imagery checks in "what would complete the exhibit").

**External (checked live):**

- **UNOSAT building-damage datasets for Mariupol exist on HDX** (CC-BY-style,
  shapefile/geodatabase, building-level vectors digitized by UN analysts from
  WorldView imagery). Three relevant releases:
  1. 14 Mar 2022 imagery — Livoberezhnyi+Zhovtnevyi districts, 773 damaged
     structures (62 destroyed / 315 severe / 321 moderate / 75 possible);
  2. 26 Mar 2022 imagery — citywide 500 m grid (triage-grade only);
  3. **7/8/12 May 2022 imagery — citywide building-level, 5,647 damaged
     structures (315 destroyed / 2,132 severe / 3,002 moderate / 194
     possible)** — the headline dataset for this layer.
- **Sentinel-2 L2A COGs via the `earth-search` AWS STAC API**
  (`https://earth-search.aws.element84.com/v1`, collection `sentinel-2-l2a`)
  — verified live, free, no auth, supports HTTP-range windowed reads.
  Continuous Mariupol coverage since 2015, ~5-day revisit, 10 m GSD.
- **Maxar Open Data Program: NO Ukraine collection.** Verified against the
  live events catalog (54 collections, none Ukraine). Maxar's 2022 Ukraine
  releases went through its news bureau, not the open ARD program. **Do not
  design against it.**

---

## 3. Sub-layers

Priority order is also build order. S1 and S2 are the layer's substance; the
rest extend it.

### S1 — UNOSAT damage-assessment ingest 〔P0 — cheapest, highest yield〕

Ingest the three HDX datasets (capture-before-parse: download the zipped
shapefiles/GDB as raw artifacts with SHA-256 + `.meta.json`, record the HDX
dataset page URL, resource URL, version/date, and license string verbatim).

Parse the building-level vectors (May-2022 release first), then **spatial-join
in PostGIS** against `property.geom`:

- match rule: `ST_DWithin(property.geom, unosat_point, 25 m)`, nearest-wins;
- confidence scored by distance (≤10 m → 0.95, ≤25 m → 0.8, else no row) —
  consistent with the project's ≥0.8 claim-grade threshold;
- one `corroboration` row per match, `kind='unosat_damage'`, detail carrying
  damage class, sensor date, UNOSAT feature id, distance.

Evidentiary effect: each match is a **United Nations analyst attestation of
war damage at a specific date** — independent A3.1 support, and it timestamps
the damage *before* the administrative demolition decision (May 2022 imagery
vs demolition register dates starting Aug 2022+), proving the sequence
"damaged in the assault → later razed by the occupation administration," which
defeats the "we only cleared dangerous ruins, nothing was taken" framing when
combined with the reallocation/new-build records.

Expected match volume: the May-2022 dataset has 5,647 damaged structures; our
geocoded cohorts (demolition 282, registry buildings 520) sit in the most
heavily assessed districts. Even a 50% hit rate would add hundreds of
independent-source rows and materially move the 819 legal-grade count.

**RESULT (2026-06-13, scripts 52–53 run):** all 3 HDX releases captured to the
raw store (5 zips, `data/parsed/unosat_manifest.json`); only the headline
12-May-2022 DA layer parsed so far (5,660 features → 5,643 building-level after
excluding 17 impact-crater features). Spatial join against the 1,961 geocoded
properties: **594 matches within 25 m** (266 at ≤10 m / confidence 0.95, 328 at
≤25 m / confidence 0.80) — a **30.3% hit rate** on the geocoded cohort. All
loaded as `corroboration(kind='unosat_damage', verdict='confirms')`. Re-running
script 33: `independent_corroboration` now covers 594 properties, legal-grade
(≥2 families) **881 → 1154** (+273), and 18 previously zero-source properties
now have their first family. March-2022 and 26-March-2022-RDA datasets remain
captured-but-unparsed (lower priority per design above).

### S2 — Sentinel-2 date-bracketing 〔P0 — the workhorse〕

**Target set (wave order, §6):** 282 geocoded demolition properties + 16
reallocation parcels + ЕИСЖС new-build sites + flagships + a sample of the 520
geocoded registry buildings (for *intactness*, see below). ~300–800 AOIs.

**Acquisition.** For each property: a 200×200 m AOI around `geom` (replaced by
the real footprint once S4 lands). Query `earth-search` for `sentinel-2-l2a`
items intersecting the AOI at the needed dates; filter `eo:cloud_cover` ≤ 30
then verify per-AOI clearness via the SCL band. Scene set per property:

| label | when | what it should show |
|---|---|---|
| T0 baseline | summer 2021 (cloud-free) | building intact, pre-war |
| T1 post-assault | May–Sep 2022 | damaged/standing state |
| T2/T3 event bracket | nearest clear scenes ≤45 days before / after each dated paper event (demolition-register date; ЕИСЖС commissioning date) | the physical change the paper asserts |

Downloads are **windowed COG reads** (rasterio over HTTP range): RGB+NIR for
the AOI only — a few hundred KB per scene, never the ~1 GB full tile. ~300
AOIs × ≤6 scenes ≈ well under 1 GB total. The 8 GB / ~$0 envelope holds.

**Forensics (documented deviation from byte-verbatim capture).** A windowed
read is a derived artifact, not a verbatim HTTP body. The protocol:

- store the **STAC item JSON verbatim** (it is the provenance record: scene
  ID, sensing time, processing baseline, asset URLs, provider checksums) as a
  `source_document` (kind `stac_item`);
- store each clipped GeoTIFF as a `source_document` (kind `image_clip`) with
  SHA-256, plus a sidecar recording the exact request (asset URL, AOI bounds,
  pixel window, bands, rasterio/GDAL versions) so the clip is **reproducible
  bit-for-bit by a third party** from the provider's canonical scene, which
  remains permanently addressable at ESA/AWS under its scene ID. This is the
  Berkeley Protocol-conformant pattern for remote sensing: chain of custody =
  provider authenticity chain + documented, replayable acquisition method.

**Analysis — human verdicts only.** No automated conclusions enter the DB.
Simple band math (ΔNDVI, brightness/texture change between pairs) is computed
solely to **rank the review queue**. The deliverable to the analyst (the user)
is an HTML review sheet of before/after chips per property per event; the
analyst records `confirms | refutes | indeterminate` + a free-text note, and
only those verdicts are loaded as `corroboration` rows (`kind='satellite_pair'`,
confidence set by the analyst, default 0.8 for a clean confirm).

**Resolution honesty (hard rule for the doc and the loader).** At 10 m GSD a
nine-storey slab (70–100 m) spans 7–10 px — demolition/clearing/new-roof
changes at that scale are reliably visible. A detached house (~10 m) is ~1 px
— **not resolvable**; such properties get `indeterminate-by-resolution`
automatically (footprint area from S4 drives the cutoff, threshold ~400 m²)
and are routed to S3 instead. We never claim more than the sensor can show.

**The intactness finding.** For the mass-registry track (e.g. the three
buildings in `case_studies/mass_registry_to_resale.md`), the expected result
is *no change*: the building stands intact while its flats are expropriated on
paper and resold. A dated "intact throughout" satellite series is affirmative
evidence that **physical destruction is not the seizure mechanism** — it
corroborates A3.6 (the property exists; the owner is excluded) and blocks any
"the building was a ruin anyway" defense. Same pipeline, verdict
`confirms-intact` recorded in `detail`.

### S3 — High-resolution exhibits for flagship cases 〔P1〕

With Maxar Open Data ruled out, the realistic paths, in order of forensic
strength:

1. **Esri World Imagery Wayback** (`wayback.maptiles.arcgis.com`) — versioned
   snapshots of the World Imagery basemap, each with explicit version dates
   and per-tile capture metadata. Tiles are plain HTTP artifacts → they fit
   the verbatim raw-store capture model exactly (URL + bytes + SHA-256 +
   version ID). Sub-meter where Maxar supplied the basemap. **First thing to
   check per flagship AOI: which Wayback versions actually refreshed over
   Mariupol and when.** Coverage/refresh over occupied territory is the risk.
2. **Google Earth Pro historical timeline** — screenshot-grade, no raw pixels,
   so weaker chain of custody; admissible-in-practice in HR reporting when the
   method is affidavited (slider date, imagery credit line, eye altitude,
   capture procedure). Use only to *illustrate* a change already confirmed by
   an S2 pair; confidence ≤0.6; `kind='hires_exhibit'`, detail records the
   full method.
3. **Planet Education & Research program** — 3 m PlanetScope, daily revisit,
   free quota by application. The single application worth making: it closes
   the small-building gap (S2's 400 m² cutoff) for the whole demolition
   cohort. User action: apply; pipeline treats it as a second STAC source.
4. **Umbra / Capella SAR open data** — sub-meter SAR; Mariupol coverage
   unverified. One-time check, no dependency.

Flagship list (in exhibit order): Нахимова 82 → Черноморский 1Б (three precise
change windows already documented: damaged by mid-2022; razed between GKO
listing and the 14.09.2023 ЕИСЖС construction photos; new building by the
29.12.2023 commissioning); the Троянда-М / пр-т Ленина candidates; the three
mass-registry buildings (intactness exhibits); the 16 reallocation parcels.

### S4 — Building-footprint layer 〔P1 — multiplies S2's value〕

Two free sources, both pre-war-aware:

- **OSM via Overpass** (infrastructure already exists — script 23): Mariupol
  was well-mapped pre-2022; polygons carry building type/levels.
- **Microsoft GlobalMLBuildingFootprints** (Ukraine tiles, ODbL-compatible
  license, derived from pre-war imagery).

Point-in-polygon against `property.geom` → store the matched footprint polygon
+ source + area in `corroboration` (`kind='footprint'`, geometry in `detail`
as GeoJSON, or a `geom_footprint` column on `property` if preferred at
implementation time — decide then; the row form keeps schema churn zero).

What footprints buy: (a) real AOIs for S2 instead of blind 200 m boxes;
(b) the **area input for the resolution-honesty cutoff**; (c) the geometric
form of the address-laundering proof — today Нахимова 82 ↔ Черноморский 1Б
rests on geocode proximity (~10 m); footprint-overlap percentage between the
demolished building and the ЕИСЖС new-build is the rigorous version, computable
in PostGIS once both polygons exist.

### S5 — Testimony references & Ukrainian-side mirrors 〔P2〕

Reference-only — **we do not collect testimony** (scope + ethics). A manually
curated CSV (`data/curated/testimony_refs.csv`, loader script) of published,
citable accounts naming spine addresses: HRW's Mariupol reporting, AP/Frontline
("20 Days in Mariupol", "Erasing Mariupol"), OSCE/Moscow-mechanism reports,
Ukrainian prosecutorial announcements, Mariupol City Council (in exile)
publications. Each row → `corroboration` `kind='testimony_ref'` or
`'ua_registry_mirror'`, with the published source captured into the raw store
(URL + SHA-256 + archive snapshot) like any artifact.

Privacy: victims/witnesses in shared outputs follow the owner-PII rule
(pseudonymize); officials stay named.

### S6 — Utility-disconnection signal 〔P2 — reuses script 50〕

The recon doc lists utility cut-offs as the leading indicator of the pipeline
(`utility_cutoff` is a `seizure_stage` with **0 rows today**). Occupation
utility operators (водоканал / теплосеть / горгаз) announce planned cut-offs
on Telegram. Action: add their channels to `config.TELEGRAM_CHANNELS`, re-run
script 50 (user-run, same MTProto session), and write a small parser for
address-bearing cut-off notices → `seizure_event` stage `utility_cutoff`.
Strictly speaking Tier-1 lifecycle evidence, not corroboration — listed here
because the recon doc filed it under Tier 3 and it shares the build moment.

### S7 — Filtration / entry-ban systemic context 〔P2 — manual acquisition〕

East SOS data (~30,000 Ukrainians refused entry Oct 2023–Apr 2025, 20–50-year
bans) proves the "appear in person within 30 days" re-registration requirement
is *designed to be impossible* — the sham-process argument that elevates every
A3.6 claim. This is **systemic, not per-property**: no spatial join. Design:
capture East SOS publications into the raw store, summarize in a standing doc
(`docs/systemic_context.md`), and cite from case studies. If East SOS shares
structured data (user outreach required), a `context_metric` loader can be
added later; do not build speculatively.

---

## 4. Data model

The existing `corroboration` table nearly suffices. Additions (idempotent
`ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, appended to `db/schema.sql` at
implementation time):

```sql
ALTER TABLE corroboration ADD COLUMN IF NOT EXISTS source_doc_id  BIGINT;          -- -> source_document.id (chain of custody; legacy rows NULL)
ALTER TABLE corroboration ADD COLUMN IF NOT EXISTS confidence     NUMERIC(3,2);    -- 0..1, same semantics as seizure_event
ALTER TABLE corroboration ADD COLUMN IF NOT EXISTS verdict        TEXT
    CHECK (verdict IN ('confirms','refutes','indeterminate'));                     -- NULL for non-verdict kinds (footprint, testimony_ref)
ALTER TABLE corroboration ADD COLUMN IF NOT EXISTS observed_start DATE;            -- bracketing window actually achieved
ALTER TABLE corroboration ADD COLUMN IF NOT EXISTS observed_end   DATE;
```

Controlled `kind` vocabulary (documented, not enum-enforced, to spare legacy
rows): `unosat_damage | satellite_pair | hires_exhibit | footprint |
testimony_ref | ua_registry_mirror | utility_signal | mirror_source (legacy:
occupation-side) | displacement_claim (legacy: occupation-side)`.

**No new tables.** Imagery scenes and clips are `source_document` rows
(kinds `stac_item`, `image_clip`, `unosat_shapefile`, `wayback_tile`) — the
existing chain-of-custody table already models exactly this. A satellite-pair
corroboration row's `detail` JSONB carries
`{before: {scene_id, source_doc_id, sensed}, after: {…}, aoi: …, method: …,
ranking_signal: …, analyst_note: …}`.

**Counting rule for script 33 (cross-source corroboration / legal-grade):**

- a corroboration row counts toward `n_sources` **only if** `verdict='confirms'`
  AND `confidence ≥ 0.8` AND its provenance family is independent (i.e. kinds
  `unosat_damage`, `satellite_pair`, `testimony_ref`, `ua_registry_mirror` —
  never the legacy occupation-side kinds, which script 33 already counts
  through their own source paths);
- it corroborates **physical claims only** (destruction, demolition,
  new construction, intactness) — never title, registry, or court events;
- `verdict='refutes'` rows feed a mandatory review report (paper-vs-imagery
  contradictions are findings, possibly data errors, possibly significant).

---

## 5. Pipeline — scripts 52–58

Same three-stage discipline (crawl → parse → load); network scripts are
**user-run** per standing convention. None of these touch geoblocked Russian
state systems — no VPS needed; they run from the Mac on home internet (HDX,
AWS, Overpass are all Western open-data services).

| # | script | stage | network | what it does |
|---|---|---|---|---|
| 52 | `52_fetch_unosat_damage.py` | crawl | yes (HDX) | download the 3 HDX datasets → raw store + `source_document` |
| 53 | `53_load_unosat_damage.py` | parse+load | no | read shapefiles from raw store (pyshp), PostGIS spatial join, write `unosat_damage` corroboration rows |
| 54 | `54_build_satellite_worklist.py` | plan | no | read DB → per-property AOI + labeled date windows → `data/parsed/satellite_worklist.json` (reviewable before any fetch) |
| 55 | `55_fetch_satellite_pairs.py` | crawl | yes (AWS STAC) | STAC search + windowed COG reads per worklist entry → raw store (`stac_item` + `image_clip` docs); resumable, streams, ≤1 GB total |
| 56 | `56_render_review_chips.py` | parse | no | before/after PNG chips + change-ranking → `data/reports/satellite_review/index.html` + a verdict template CSV |
| 57 | `57_load_satellite_verdicts.py` | load | no | read analyst-filled verdict CSV → `satellite_pair` corroboration rows; refutes-report |
| 58 | `58_fetch_building_footprints.py` | crawl+load | yes (Overpass / MS) | footprints for geocoded properties → `footprint` rows; re-emits the worklist with true AOIs |

New dependencies — one optional extras group in `pyproject.toml`,
`[imagery]`: `rasterio` (windowed COG reads; the one heavy dep, wheels are
fine on macOS arm64), `pyshp` (UNOSAT shapefiles), `Pillow` + `numpy` (chips).
Spatial joins happen in PostGIS, not Python — no geopandas/shapely needed.

S3 (Wayback/GE Pro) and S5/S7 (curated CSVs) are deliberately script-light:
manual acquisition with raw-store capture, plus small loaders folded into 57's
pattern when they materialize.

---

## 6. Rollout waves & acceptance criteria

| wave | scope | scripts | done when |
|---|---|---|---|
| 1 | **Flagships** (~10 AOIs): Нахимова 82, Троянда-М candidates, 3 mass-registry buildings | 54–57 (manual-grade), S3 checks | each of the 3 case studies gains an imagery annex: dated pair(s) or intactness series, with analyst verdicts loaded |
| 2 | **UNOSAT ingest** (citywide) | 52–53 | **DONE 2026-06-13** — 594/1,961 geocoded properties matched (30.3%); legal-grade re-measured 881 → 1154 |
| 3 | **Demolition cohort** (282 AOIs) | 54–57 full run | every dated demolition event has a verdict (confirms / refutes / indeterminate-by-resolution); refutes-report reviewed |
| 4 | **New-builds + parcels** (16 reallocation + ЕИСЖС sites) | 54–57 | construction-start/completion bracketed; footprint overlaps computed where S4 polygons exist |
| 5 | **Registry intactness sample** (~50 of 520 geocoded registry buildings) | 54–57 | intactness series loaded; A3.6 narrative in the progress report cites it |

KPI for the progress report: **"properties with independent (non-occupation)
corroboration"** — was **0**, now **594** after wave 2 (2026-06-13).

---

## 7. Rejected alternatives

- **Maxar Open Data** — verified: no Ukraine collection. Out.
- **Sentinel-1 SAR coherence change detection** — SLC pairs are GBs each and
  need SNAP/ISCE processing; breaks the 8 GB/streaming envelope and adds an
  expertise dependency. Optical suffices in this climate (dry-steppe coast,
  abundant clear scenes). Revisit only if a specific date window is hopelessly
  cloudy.
- **ML damage classifiers (xView2 etc.)** — black-box inference undermines
  court admissibility and invites Daubert-style challenges. Human analyst
  verdicts only; the queue-ranking signal stays to transparent band math.
- **Google Earth Engine** — redistribution-restrictive TOS plus an account
  dependency; raw COG range-reads are more forensically transparent and
  reproducible.
- **Paid tasking / commercial archive purchase** — outside the ~$0–20
  envelope; the Planet research application is the sanctioned free path.

---

## 8. Risks

| risk | mitigation |
|---|---|
| geocode error → AOI misses the building | S4 footprints; manual-override file pattern already exists (script 25); flagships verified by hand |
| cloud cover breaks a ±45-day bracket | widen window stepwise, record the *achieved* bracket in `observed_start/end` — honesty over neatness |
| Wayback refresh over occupied Mariupol is sparse/stale | check per-AOI before promising any S3 exhibit; GE Pro fallback |
| 10 m GSD over-claiming | hard `indeterminate-by-resolution` rule keyed to footprint area (§3-S2); stated in every output |
| HDX/UNOSAT datasets withdrawn or moved | capture now (wave 2 is cheap; nothing blocks running 52 immediately) |
| courtroom provenance challenge to derived clips | STAC item JSON verbatim + replayable windowed-read method + provider's permanent scene IDs (§3-S2 forensics) |
| misreading "intact" as "no crime" | doc + report language fixed in §3-S2: intactness corroborates A3.6 exclusion, never innocence |

---

## 9. Out of scope (stays out)

Drone/ground imagery acquisition; any contact with persons in occupied
territory; automated damage classification; real-time monitoring/alerting;
non-Mariupol AOIs. Per CLAUDE.md, anything not moving a property toward RD4U
or Rome-Statute endpoints is excluded — every sub-layer above maps to one or
both (§1).
