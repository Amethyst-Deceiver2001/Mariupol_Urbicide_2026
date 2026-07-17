# Per-address OSINT sweep assistant — design (2026-07-16, updated 2026-07-16)

> **Status (2026-07-16): FULLY BUILT AND LIVE-VALIDATED — all 27 sources.**
> `src/mariupol_seizures/osint/` (variants, bundle, ledger, geocode Engine 2,
> and 27 source modules) + `scripts/324_osint_sweep.py` (orchestrator,
> `--plan` default, `--allow C,U,V` run-class gate) +
> `scripts/325_osint_dossier.py`. Plus two standalone verification tools
> that sit outside the per-address sweep architecture (see their own
> section below): `scripts/326_rekognition_photo_triage.py` (AWS OCR/label
> triage over already-captured images) and `scripts/327_shadow_angle_dating.py`
> (solar-position date/time verification from a shadow angle).
>
> **Run classes** — `C` Claude-safe (19: local_evidence, telegram_local,
> death_records, eyesonrussia, wikidata, pastvu, commons, osm, wayback_tiles,
> realestate_prewar, archives, wikimapia, mapillary, flickr, google_earth_kml,
> panoramax, kartaview, visicom, reverse_image), `U` user-terminal (6:
> google_imagery, sentinel2, youtube, telegram_channels, telegram_global,
> yandex_maps), `V` VPS (2: vk, resale). `scripts/324 --sources claude`
> (default) runs only C; the user runs U/V with `--allow C,U,V`. Key-gated
> sources (wikimapia/mapillary/flickr/google/vk/visicom/yandex-geocoder) skip
> cleanly with a note when their key is unset. **Visicom moved U→C mid-build**:
> found a real documented REST API (`api.visicom.ua/data-api/5.0`) partway
> through, replacing the originally-planned playwright/XHR-sniffing approach
> — no browser automation needed for it after all.
>
> **Validated end-to-end, all 27 sources, real results on pid 4837**
> (Зелинского 17а) — not just the C tier: every U/V source has now actually
> been run by the user with real output (YouTube candidates, Telegram
> channel/global hits, Yandex Maps XHR, VK photos/posts, resale board
> captures), not just compile-checked. The comprehensive Telegram-corpus
> search (215,696 raw files, thread-pooled + byte-prefiltered, ~43s)
> surfaced a NEW lead — @nmrpl/4095 bezkhoz-list naming 17а — beyond the
> 2026-07-15 manual pass. All `.env` keys configured and working: Visicom,
> Wikimapia, Mapillary, VK (24h-lived token — regenerate per session), AWS
> (Rekognition triage).
>
> **Real bugs found + fixed during calibration** (all via live user-run
> testing, not caught by compile-check alone): `telegram_global`'s
> `SearchGlobalRequest` needed `types.InputPeerEmpty()`/
> `InputMessagesFilterEmpty()`, not bare `None`; `google_imagery` mislabeled
> `REQUEST_DENIED` API errors as "no coverage" (that phrasing belongs to
> `ZERO_RESULTS`); `resale` silently dropped a board with zero logged
> findings when all 3 query-param variants returned non-200 without an
> exception; `mapillary`'s `radius_m` argument was accepted but never
> actually used (hardcoded ~100m bbox regardless); `wikimapia`'s
> `place.getbyarea` endpoint is dead/broken on Wikimapia's own side (bare
> `[]` for every bbox tried, including known-dense central Kyiv) — rewritten
> to `place.getnearest` + `place.getbyid`.

## Purpose

Given one Mariupol property (a spine `property_id`, or a raw address not yet
on the spine), sweep every reachable platform for media and content about
that building — historical photos, siege-era footage, street-level imagery,
crowd descriptions, satellite timelines, resale listings, mentions in
channels — capture everything forensically, and assemble a per-address
evidence dossier that feeds the existing `corroboration` layer and case
studies. Endpoint fit (CLAUDE.md): every artifact either documents the
property's pre-war existence/condition/value (RD4U damage/loss quantum) or
its post-seizure lifecycle (demolition, rebuild, resale — Rome Statute
art. 8(2)(b)(viii) / appropriation).

This is a *generalization of things the project already does one-off by
hand*: the Зелинского cluster review (2026-07-15) manually combined chat-corpus
greps, the victims TSV, two YouTube walkthroughs, Telegram channel pulls,
decree text, and DMS coordinates — exactly the sweep this assistant should
run from a single command.

## Inputs and the two shared engines

**Input resolution.** `--pid 4837` (spine lookup: both address forms +
geocoded point) or `--address "ул. Зелинского 17а"` (geocode first, warn if
off-spine). Every source module receives the same resolved bundle:
`(point, prewar_address, occupation_address, building_id, pid)`.

### Engine 1 — query-variant expansion (`osint/variants.py`)

The single most important shared component. From one address produce the
full search-string set:

- **House-number forms**: `17а`, `17-а`, `17 а`, `17А`, `д. 17а`, `д.17-А`,
  `17/1`, corpus forms (`17 корп. 1`) — the same variant family already
  used ad hoc in the 2026-07-15 death-record greps.
- **Street-name duality**: pre-war Ukrainian name, Russian name, AND
  occupation rename both directions (Азовстальская ↔ пр. Тульский etc.),
  resolved through the existing toponyms/`_STREET_KEY_ALIASES` machinery —
  a search that misses the renamed form silently loses the post-2023 record.
- **Language/script**: RU («улица Зелинского»), UA («вулиця Зелінського»),
  translit (`Zelinskogo`, `Zelinskoho`) for YouTube/Western platforms.
- **Type-word forms**: ул./улица/omitted; пр./просп./проспект; б-р/бульвар.

Output is a ranked list (most-specific first) so budget-limited sources
(Telegram global search) spend quota on the best queries.

### Engine 2 — geocoding + point confidence (`osint/geocode.py`)

Three independent geocoders, compared:
1. **Nominatim/OSM** (exists — scripts/22, Ukrainian addressing).
2. **Yandex Geocoder API** (free tier ~1000/day; covers occupied-territory
   Russian addressing, so it resolves *renamed* streets Nominatim can't).
3. **Visicom** (`api.visicom.ua`) — Ukrainian commercial GIS provider;
   authoritative for **pre-war Ukrainian street-name spelling** (their
   geocoder/address base predates 2022 and isn't overwritten by occupation
   renaming the way live Russian-side sources are) and carries building
   footprint polygons keyed to Ukrainian cadastral data, a second footprint
   source independent of OSM/Overpass. Turned out to have a documented REST
   Data API (`/data-api/5.0/{lang}/geocode` + `/feature/{id}`, key-gated,
   found 2026-07-16) — no browser automation needed, unlike Yandex below.

Store all points; agreement ≤30m across sources used → high-confidence
point; divergence >30m → flag for manual pin (no-false-precision rule —
never average). Overpass (scripts/23) and Visicom both supply building
*footprint polygons* where available, which is what tile/photo queries
should actually use, not a point — prefer OSM's footprint, fall back to
Visicom's, flag if the two disagree on footprint shape/extent (itself a
signal — e.g. a footprint that changed between the two datasets' capture
dates).

## Source matrix

Legend — Run: C = Claude may run directly (local or quick non-geoblocked
fetch), U = user runs (long/network per standing rule), V = user's
Russia-routed VPS (geoblocked). Existing: script that already solves part.

| # | Source | Yields | Method / endpoint | Quota / auth | Run | Existing |
|---|--------|--------|-------------------|--------------|-----|----------|
| 0 | **Local evidence base** | everything already held: spine events, 6 corroboration families, chat corpus (~200K+ msgs), victims TSV, decree/court/registry rows, damage tracker | SQL + jsonl grep | — | C | the 2026-07-15 manual workflow |
| 1 | **Telegram — local corpus** | mentions in all already-captured channels | grep `data/parsed/*.jsonl` + raw store | free, unlimited | C | 148–151, 224, 303 |
| 2 | **Telegram — in-channel search** | mentions in known channels *beyond* captured history / uncaptured channels | telethon `messages.Search` per channel (q=variant), over the ~40-channel list from the fwd-graph (230/259) | **not** budget-limited | U | telethon patterns everywhere |
| 3 | **Telegram — global post search** | discovery of *unknown* channels mentioning the address | Premium global post search, ~10 queries/day | **hard 10/day ledger** | U | none — new |
| 4 | **YouTube** | walkthroughs, siege footage, drone flyovers | `yt-dlp ytsearchN:"<variant>"` → existing download/transcribe/stills pipeline | free | U | **321/322 wholesale** |
| 5 | **PastVu** | pre-war/historical photos, geotagged + dated | `pastvu.com/api2?method=photo.giveNearestPhotos&params={"geo":[lat,lon],...}` | free, no key | C | 159 (one-off) |
| 6 | **Wikimapia** | crowd descriptions of buildings — pre-war *function* (dormitory, boiler house №5, kindergarten…) | `api.wikimapia.org` `place.getbyarea`/`getnearest` | free key | C | none |
| 7 | **OpenStreetMap** | footprint, tags (levels, name, addr), **history** (deleted/retagged post-war), Notes | Overpass (current) + ohsome API (history) + Notes API | free | C | 23 (Overpass) |
| 7b | **Visicom** | pre-war Ukrainian street-name spelling (geocoder Engine 2 #3 above); second independent building-footprint polygon (real geometry, not just centroid) | documented REST API, `api.visicom.ua/data-api/5.0/{lang}/geocode` + `/feature/{id}` — keyed, no browser automation needed | free key | C | none |
| 8 | **Wikimedia Commons** | geotagged photos (often EXIF intact) | `action=query&list=geosearch&gscoord=…` | free | C | none |
| 9 | **Mapillary** | crowdsourced street-level imagery, dated | Graph API `images?bbox=` (free token); thumbnail fields currently gated pending Mapillary app review — metadata (dates/geometry) works now | free token | C | none |
| 9b | **Panoramax** | crowdsourced street-level imagery, OSM Foundation-backed, fully open alternative — added specifically because Mapillary's thumbnail access is gated | STAC-based REST `/api/search`, keyless, `properties["geovisio:thumbnail"/"geovisio:image"]` direct-downloadable | free, no key | C | none |
| 9c | **Kartaview** | crowdsourced street-level imagery (formerly OpenStreetCam), independent contributor pool from Mapillary/Panoramax | `api.openstreetcam.org/2.0/photo/?lat&lng&radius` | free, no key | C | none |
| 10 | **Yandex Maps photos + panoramas** | pre-war AND post-war street-level; panorama time machine | no public API → playwright capture of photo layer / pano URLs (schema: `yandex.com/maps/?l=pht&…photos[point]=lon,lat`) | free, ToS-gray | U | 242 (playwright) |
| 11 | **Google Street View / Places** | metadata: does coverage exist + dates (free); imagery (paid, ~$7/1k) | SV metadata endpoint; Places photos | $ credit | U | none |
| 12 | **Google Earth Pro (manual assist)** | historical satellite slider | generate per-address KML placemark; user reviews manually | free | C (KML gen) | — |
| 13 | **Esri Wayback satellite tiles** | dated hi-res tile timeline: intact → damaged → cleared → rebuilt | generalize scripts/57: tile math from footprint, walk releases | free, no key | U | **57/58** |
| 14 | **Sentinel-2** | 10m change detection where Wayback thin | existing pipeline | free | U | 54–56 |
| 14b | **Eyes on Russia (CIR)** | independent civilian-damage verification (4th corroboration family) — usually already loaded project-wide, but re-query live per-address for post-load-date freshness | ArcGIS FeatureServer, spatial WHERE on point/radius — same endpoint as scripts/200, no auth | free, no key | C | **200/201 (project-wide load already exists — this is a live per-address re-query on top)** |
| 15 | **VK** | siege photo albums, local-group posts, resident comments | `photos.search` (geo radius) + `newsfeed.search` (q=variant), user token | free w/ account | V | none |
| 16 | **Flickr** | pre-war tourist/architecture photos, EXIF-rich | API geo search, free key | free | C | none |
| 17 | **Occupation resale market** | current listings for the address = post-seizure resale evidence | avito/local boards per-address query | free | V | 158/159/161, 181 |
| 18 | **Pre-war Ukrainian listings (Wayback CDX)** | interior photos, declared area/price pre-war — private-ownership + value evidence | archive.org CDX API over URL patterns: `dom.ria.com/*<slug>*`, `olx.ua`, `lun.ua`, `mesto.ua` | free | U | none |
| 19 | **Wayback Machine general** | any dead page mentioning the address (school sites, news, forums) | CDX + snapshot fetch | free | U | sources.md precedent |
| 20 | **Wikidata/Wikipedia** | notable-building metadata | SPARQL / API | free | C | none |
| 21 | **Reverse-image pivot (manual assist)** | more copies/originals of best finds | emit "pivot sheet": top N images + Yandex-Images/Google-Lens links | free | C (sheet gen) | — |
| 22 | **Death records — cross-source aggregator** | named victims/deaths/burials tied to this address, deduped across sources | see dedicated section below | free | C (local) + U (new sources) | **299–313 (3 of the ~5 sources already integrated)** |

Everything is $0 except optional Google imagery — fits the project's $0–20
envelope. The only paid asset already owned is the user's Telegram Premium.

## Death records — cross-source aggregator (`osint/sources/death_records.py`)

The Зелинского cluster review (2026-07-15) already ran this by hand across
three sources for one street; this module generalizes it to any address,
one query.

**Sources already captured/integrated — query locally, no network:**
1. **Mariupol Destruction and Victims Map TSV** (scripts/299) — 4,521-row
   citywide named-victims spreadsheet, `место проживания`/`место смерти`
   columns.
2. **memorial.ua obituaries** (scripts/305–307) — independent named-victim
   corpus, already cross-referenced to the spine.
3. **@mariupolRIP channel** (scripts/302–304, 309–313) — the dominant
   primary source behind #1; full-channel scan + informal-burial
   extraction + grave-site master list already exist.

All three already feed `data/reports/grave_sites_master_evidence.csv` /
`data/parsed/master_grave_site_list.jsonl` (scripts/308) — the aggregator's
local tier is mostly "filter what's already merged by address-match,"
reusing the `TYPED_RE` address-extraction + `address_to_building_key()`
match pattern proven in scripts/309/323 (fixed 2026-07-15 to capture the
street-**type** word so `classify_street()` resolves correctly — reuse that
fixed regex, not scripts/309's original).

**Candidate sources not yet integrated, worth probing at build time:**
4. **@kadryVoynyMariypol2022** (scripts/317–320, 323 — just built) — heavy
   "Известные имена погибших" record density, per-address matching already
   proven (177 hits, §Case 2 cluster).
5. Other war-footage/memorial channels surfaced but not yet fully scanned
   (`@ssaniaworld` follow-ups, `@allmarinews` casualty posts) — same
   TYPED_RE sweep, cheap to point at any already-captured channel.
6. **ICRC Restoring Family Links** — missing-persons tracing database;
   PRIVACY-SENSITIVE (living/searching relatives, not public record) —
   evaluate against the project's PRIVACY rule before any capture; likely
   out of scope as a bulk source, but a single confirmed-address lookup
   may be legitimate corroboration if the user already holds a specific
   case reference.
7. Any Ukrainian government/municipal "книга пам'яті" (book of memory) or
   similar official registry, if one with per-address or per-victim
   detail becomes publicly locatable — currently unconfirmed to exist for
   Mariupol specifically; treat as a standing watch item, not a build task.

**Output**: per-address dedup across sources by name + date-of-death
proximity (±3 days, same fuzzy-match discipline as everywhere else in this
project — confidence-score, never silently merge two different people with
similar names). Feeds directly into the same `docs/case_studies/
death_sites_new_construction.md`-style write-up this project already
produces by hand.

## Telegram budget strategy (the scarce resource)

Three tiers, cheapest first; the sweep NEVER burns a global search on a
query a cheaper tier can answer:

1. **Tier 0 — local corpus** (free, instant): all variants × all captured
   channels. This alone answered most of the Зелинского cluster questions.
2. **Tier 1 — in-channel API search** (free, unlimited): telethon
   `messages.Search(q=…)` against every channel in the project's known-
   channel list — searches the channel's *full* history server-side,
   including channels we only text-crawled partially and the ~15 fwd-graph
   channels never crawled at all.
3. **Tier 2 — global post search** (10/day, ledgered): only the top-ranked
   1–3 variants per address, only after tiers 0–1 ran. Ledger table
   `osint_search_ledger(day, source, query, spent, results_json)` in
   `state.sqlite`; the runner refuses to exceed the daily budget and keeps
   a persistent priority queue so tomorrow's budget resumes automatically.
   Implementation note: the exact TL method for Premium post search must be
   probed at build time (layer-dependent); **fallback path that needs zero
   API work** — the user performs the 10 searches in the Telegram app and
   forwards hits to a private intake channel, which a standard crawler
   (317-pattern) ingests with full provenance.

## Architecture

```
src/mariupol_seizures/osint/
    __init__.py
    variants.py        # Engine 1
    geocode.py         # Engine 2 (wraps existing + Yandex)
    ledger.py          # quota bookkeeping (state.sqlite)
    sources/
        base.py        # fetch(bundle, con, budget) -> [sha256]; every module
        pastvu.py      #   captures via forensics.capture_source() BEFORE parse
        wikimapia.py
        commons.py
        osm.py
        mapillary.py
        flickr.py
        wayback_tiles.py   # generalized scripts/57
        wayback_cdx.py
        youtube.py         # search only; hands off to 321/322 pipeline
        telegram_local.py
        telegram_channels.py
        telegram_global.py
        yandex_maps.py     # playwright — no documented API for the photo layer
        visicom.py         # REST API (geocode Engine 2 #3 + footprint), not playwright
        eyesonrussia.py    # live per-address FeatureServer re-query (200's endpoint)
        death_records.py   # cross-source aggregator, see dedicated section above
        vk.py
        resale.py
        panoramax.py       # keyless STAC API, added 2026-07-16
        kartaview.py       # keyless, added 2026-07-16
scripts/
    324_osint_sweep.py     # orchestrator: --pid/--address --sources a,b,c
                           #   --plan (dry-run: print what would run, what
                           #   needs the user/VPS, quota state) — default
    325_osint_dossier.py   # assemble captures -> per-address dossier (local)
    326_rekognition_photo_triage.py  # standalone: AWS OCR/label triage over
                                     #   already-captured images, see below
    327_shadow_angle_dating.py       # standalone: solar-position date/time
                                     #   verification, see below
```

The dossier->corroboration loader sketched in the original design (once
numbered 326) was never built — every source this project has actually
promoted to `corroboration` so far has gone through a dedicated per-family
loader (scripts/199-205 pattern), and OSINT-sweep findings are still a
manual promote-by-hand step (read the dossier, confirm, write the case
study/loader row yourself) rather than an automatic bulk load — consistent
with the no-fuzzy-merge/confidence-score rule. Revisit if promoting sweep
findings by hand becomes a real bottleneck.

## Two standalone verification tools (outside the sweep architecture)

Neither of these fetches new external data — both operate on evidence the
sweep (or the project generally) already captured, so they don't fit the
`sources/` module contract (`plan()`/`fetch(bundle, con, radius_m)`) and
aren't in `REGISTRY`. Run them by hand, pointed at a specific batch.

- **`scripts/326_rekognition_photo_triage.py`** — AWS Rekognition
  `DetectText` + `DetectLabels` over images already captured (by pid's
  sweep, or any raw-store `source_type`). Flags OCR lines matching an
  address-shaped pattern or "паспорт объект*", and labels of interest
  (Rubble, Demolition, Construction Crane, Sign, Plaque, …). Writes a
  review CSV — never auto-loads to the DB or a case study. `--dry-run`
  shows scope + exact API-call cost before any spend. Needs a scoped IAM
  user (`rekognition:DetectText`/`DetectLabels` only) and
  `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`/`AWS_DEFAULT_REGION` in
  `.env`. Free tier: 5,000 images/month per API, first 12 months.
- **`scripts/327_shadow_angle_dating.py`** — given a KNOWN location (pid or
  lat/lon) and a shadow measurement (object height + shadow length, or a
  directly-measured sun altitude), either `verify`s whether a claimed UTC
  timestamp on a photo/video is physically consistent with the shadow, or
  `scan`s a day for the time windows that ARE consistent. Solves the
  inverse of Bellingcat's ShadowFinder (which finds an unknown LOCATION
  given a known time) — our use case is the known-location/disputed-time
  direction, via `pysolar`. No network, no key.

Key orchestrator behaviors:
- `--plan` first (default): prints per-source what will run, which runner
  (C/U/V) it needs, and current quota state — respecting the standing rule
  that the user runs network jobs. Claude-safe sources can then run with
  `--run local`; the rest emit ready-to-paste commands.
- Idempotent per `(source, query|tile|photo_id)` — same `done`-ledger
  pattern as every crawler in this project; interrupt/resume free.
- Every capture: `forensics.capture_source()` (or `capture_derived` for
  stills/crops), `source_type='osint_<source>'`, URL + timestamp + SHA-256.

## Parse/enrichment stage (all local, Claude-runnable) — NOT YET BUILT

Everything below this line is still aspirational — none of it exists yet.
The one enrichment capability actually built (2026-07-16) is
`scripts/326_rekognition_photo_triage.py` (OCR + label detection via AWS,
see above), which covers part of the OCR item below but not EXIF/pHash/
video-timecoding.

- **EXIF/geotag extraction** on every image (Commons/Flickr/VK keep EXIF;
  Telegram strips it) → verify geotag against the building point; >100m →
  skip-beyond-100m rule (same as osint-geo-extractor precedent).
- **Perceptual-hash dedup** (`imagehash` pHash): cluster the same photo
  reposted across platforms → provenance chains ("this VK photo = this
  Telegram photo posted 3 days earlier") instead of duplicate rows.
- **Burned-in caption OCR** where applicable — reuse the red-channel-mask
  technique from scripts/315 (already proven Porfir-specific there; generic
  date-stamp OCR still useful on dashcam/CCTV-style footage).
- **Address-mention timecoding** for video — reuse scripts/322 wholesale.

## Dossier output

`data/reports/osint/<pid>_<slug>/`:
- `dossier.md` — human-readable: timeline-ordered media table (pre-war →
  siege → clearance → rebuild → resale), each row hyperlinked to source URL
  + raw-store SHA, with the address's spine summary (seizure events,
  corroboration families already present) at top so *new* finds are
  visually separated from *already-held* evidence.
- `manifest.csv` — machine row per artifact: sha256, source, url, date
  (claimed/EXIF/release), lat/lon if any, dedup-cluster id, confidence.
- optional `dossier.qgs`-ready GeoJSON of geotagged finds.

A future dossier->corroboration loader (kinds: `historical_photo`,
`street_imagery`, `crowd_description`, `osm_history`,
`resale_listing_prewar`) is sketched but NOT built — see the note above the
architecture tree. Promotion is manual for now.

## Privacy & forensics constraints (unchanged, restated)

- Owner-identifying content (names in listings, faces, phone numbers in
  resale ads) stays in the raw store / `owner`-table domain; dossier.md is
  an internal working doc, but anything promoted to an exhibit passes the
  existing minimization rules.
- Occupation-platform content (VK, avito, Yandex) is evidence of the *act*,
  never authoritative title.
- Geoblocked/RU-jurisdiction fetches (VK, avito, gosuslugi-adjacent) run
  from the user's VPS only; Claude never executes them.

## Phasing — ALL COMPLETE as of 2026-07-16

P0/P1/P2 below are the original plan, kept as a historical record of build
order. All three are done — Visicom did NOT stay deferred to playwright as
P0 assumed (see the REST-API status note at the top); everything else
shipped roughly as planned, plus two unplanned additions (Panoramax,
Kartaview) and two standalone tools outside this phasing (Rekognition
triage, shadow-angle dating).

**P0 (one session):** `variants.py` + `geocode.py` (Nominatim + Yandex only —
Visicom deferred to P1, its playwright reverse-engineering isn't a quick
add) + orchestrator skeleton with `--plan`, plus the free/keyless
C-runnable sources: local-evidence assembly, **death_records local tier**
(the 3 already-integrated corpora — pure reuse of the fixed scripts/323
TYPED_RE match), **eyesonrussia live re-query** (already-public endpoint,
zero new auth), pastvu, Commons, OSM(+history), wayback_tiles
generalization. Dossier generator with whatever P0 captured. *Immediately
useful, and death-records + EoR alone would have shortened the 2026-07-15
cluster review by most of a session.*

**P1:** Telegram tiers 0–2 (ledger + intake-channel fallback), YouTube
search hand-off, Wayback CDX pre-war listings, wikimapia + mapillary +
flickr (key signup), Yandex + Visicom playwright capture,
death_records candidate-source probes (#4–7 in that section).

**P2:** VK module, occupation resale module, Google paid imagery,
reverse-image pivot sheets, pHash dedup polish.

## Open questions

1. ~~Telegram global-search TL method vs. intake-channel fallback~~
   **RESOLVED 2026-07-16**: `SearchGlobalRequest` works — needed
   `types.InputPeerEmpty()`/`InputMessagesFilterEmpty()` instead of bare
   `None` (a telethon cast requirement, not an API-availability question).
   Live-validated: 43 message hits + channel discovery on one run.
2. ~~Yandex pano "time machine" URL schema~~ **PARTIALLY RESOLVED
   2026-07-16**: the user ran `yandex_maps` live and it captured 2 photo/pano
   XHR responses + 1 screenshot successfully. Parsing is still flagged
   provisional (the XHR body shape hasn't been hand-verified field-by-field
   against the captured JSON) — the raw capture is the durable artifact
   regardless, so this is a "tighten the parser later" item, not a blocker.
3. Wikimapia data quality post-2022 (vandalism/renames) — treat
   descriptions as claims requiring the usual ≥2-source rule, never
   standalone legal-grade. Separately, `place.getbyarea` (the originally
   planned endpoint) turned out to be dead on Wikimapia's own side —
   rewritten to `place.getnearest` + `place.getbyid` 2026-07-16.
4. Whether per-address sweeps should auto-enqueue every crosswalk property
   (batch mode) or stay strictly on-demand — start on-demand; batch is one
   loop later. Still open — no sweep has been run in batch mode yet.
5. **NEW**: Bellingcat OSM Search (from The-Osint-Toolbox/Geolocation-OSINT
   list) turned out to be a street-*intersection* finder requiring a Bearer
   auth token, not a general place-name search — solves "unknown location,
   known intersection," the opposite of this project's "known address"
   starting point. Not built. Revisit only if a future case genuinely starts
   from an unidentified photo rather than a known address.
