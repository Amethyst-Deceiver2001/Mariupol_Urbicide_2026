# Mariupol Property-Seizure Documentation

Forensic evidence pipeline documenting Russian occupation authorities' seizure of
Ukrainian-owned property in Mariupol, built to feed (1) restitution claims (Council
of Europe Register of Damage for Ukraine) and (2) criminal accountability. Mission
and rules live in [`CLAUDE.md`](./CLAUDE.md); strategy in
[`docs/reconceptualization_2026.md`](./docs/reconceptualization_2026.md).

## Public exhibits

A set of standalone, source-hashed visual exhibits is published from [`docs/`](./docs/)
(GitHub Pages): a [master dossier](./docs/exhibits/mariupol-master-dossier.html), the
[dispossession-pipeline system map](./docs/exhibits/dispossession-pipeline.html), an
[interactive map](./docs/exhibits/interactive-map.html) of every documented case against
the geocoded property spine, four documented case studies
([Nakhimova 82](./docs/exhibits/nakhimova-82-exhibit.html) — demolish→rebuild→resell
address-laundering,
[registry-to-resale](./docs/exhibits/case-study-II-registry-resale.html) — flat-by-flat
registry sweep,
[Stroiteley 74–88](./docs/exhibits/case-study-III-stroiteley.html) — block-level
demolition onto one developer,
[the court docket](./docs/exhibits/case-study-IV-court-docket.html) — 28 judges, 2,666
rulings, no named address), the deep-dive
[Lenina 104–110 exhibit](./docs/exhibits/lenina-104-106-108-110-exhibit.html), an
interactive [stakeholder network](./docs/exhibits/stakeholder-network.html), a
[sources catalogue](./docs/exhibits/sources.html) of every source category behind the
archive, and an [about/methodology page](./docs/exhibits/about.html). Entry point:
[`docs/index.html`](./docs/index.html). Presentation rules in
[`docs/exhibits/STYLE_GUIDE.md`](./docs/exhibits/STYLE_GUIDE.md).

## Status (June 2026)

Multi-source evidentiary spine, all forensically captured and loaded to
PostgreSQL/PostGIS. Full review: [`docs/progress_report_2026-06.md`](./docs/progress_report_2026-06.md).

- **~211,900** registered source documents / ~71 GB raw store (SHA-256 + chain of custody)
- **6,084** properties on spine · **1,155** legal-grade (≥2 independent sources) · all RD4U-categorized
- **11,521** corroboration rows (mirror sources, UNOSAT damage, displacement claims, market listings, ownerless-registry disposition, lifecycle media)
- **2,666** occupation court cases (4 Mariupol district courts — **saturated**) · **12,948**-entry ownerless registry · **968** ownerless decrees · **1,941**-building federal damage tracker · **51** DNR land-grant orders · **5,822/1,889** housing queue/distribution
- Legal-mechanism catalogue (rungs [A]–[H], 30+ instruments) — [`docs/legal_mechanisms_review.md`](./docs/legal_mechanisms_review.md)
- Stakeholder network (111 nodes / 138 edges; Пушилин→Иващенко→Моргун→Кольцов command chain dated) — [`docs/stakeholder_network.md`](./docs/stakeholder_network.md)
- 28 building-chat Telegram corpus (~145K messages) deep-mined for cross-building actors/decrees/process-events, 118 primary-source documents (decrees, court rulings, dated ownerless snapshots), a temporal ownerless-registry differential (64 occupation-admitted municipal seizures, 1,610 owner-returns, 207-building undocumented-disappearance gap register), and a media lifecycle manifest (22 buildings with a confirmed demolition→rebuild visual arc) — see `memory/deep_chat_corpus_analysis_2026-06.md` if using Claude Code, else `scripts/148`–`151`
- Case studies: [`docs/case_studies/`](./docs/case_studies/) — four documented seizure modalities: demolish→rebuild→resell address-laundering ([`nakhimova_82_chernomorsky_1b.md`](./docs/case_studies/nakhimova_82_chernomorsky_1b.md)); flat-by-flat registry sweep into live resale ([`mass_registry_to_resale.md`](./docs/case_studies/mass_registry_to_resale.md)); block-level demolition of five buildings onto one developer ([`death_sites_new_construction.md`](./docs/case_studies/death_sites_new_construction.md)); and restoration-without-restitution, where a building is decreed for demolition but never razed while ownership is stripped via the registry anyway ([`lenina_104_106_108_110_restoration_without_restitution.md`](./docs/case_studies/lenina_104_106_108_110_restoration_without_restitution.md))
- QGIS findings layer (`data/exports/qgis/session_2026-06_findings.geojson`) — gap-register, media-arc, and corroborated-seizure buildings, 264/271 geocoded

**Next:** the 1 July 2026 re-registration deadline opens a new designation wave —
the live front line has moved from the (now-closed) court docket to weekly
re-snapshotting of the ownerless registry. See the progress report's gap list.

## Pipeline

```
[occupation court portals]                     ← geoblocked; VPS only
        │  scripts/01_crawl.py  (capture before parse, SHA-256 + custody)
        ▼
   data/raw/  (immutable raw store + .meta.json sidecars)
        │  scripts/02_parse.py  (offline, re-runnable extraction)
        ▼
   data/parsed_cases.jsonl
        │  scripts/03_load.py
        ▼
 PostgreSQL + PostGIS  (db/schema.sql — lifecycle spine)
```

Each stage is independent and re-runnable. Parsing never re-hits the courts.

The court docket above is the spine's origin, but the evidence base now spans
several independent occupation/federal streams, each with its own crawl→parse→load
scripts (numbered in `scripts/`): the Mariupol ownerless registry + decrees
(05/06/26/27), the federal damage tracker (07/32), demolition decrees + MinStroy
register (08/09/14/15), DNR land-grant orders (10/11), housing queue/distribution
(16/29), the ЕИСЖС new-build registry (17/18), DNR/federal normative acts
(13/35/37/38/39), EGRUL ownership (20/41), and the stakeholder network (40). RD4U
categorization (36) and cross-source corroboration (33) run read-only over the
loaded spine.

A separate building-chat Telegram stream (crawlers 74-147) feeds a deep-analysis
program (148 cross-chat intel, 149 document inventory, 150 ownerless temporal
differential, 151 media lifecycle manifest) and a loader (152) that brings those
findings into `corroboration`. Script 153 scores candidates for case-study
write-up by combining visual + documentary + disposition evidence; 154 exports
a QGIS findings layer; 155 is a small targeted Nominatim pass for buildings the
other scripts reference but `geocoded_buildings.jsonl` doesn't yet cover.

## Setup

```bash
cp .env.example .env          # fill PROJECT_ROOT, COURT_PROXY, DATABASE_URL, RESULTS_TEMPLATE
make setup                    # venv + editable install ([geo,dev])
createdb mariupol_seizures && psql "$DATABASE_URL" -f db/schema.sql
make test
```

## Run

```bash
# 1) CRAWL — run ONLY from your Russia-routed VPS. Fill crawl/courts.py first,
#    and paste a real ГАС «Правосудие» results URL into RESULTS_TEMPLATE.
make crawl

# 2) PARSE (offline) and 3) LOAD
make parse
make load

# integrity check: re-hash the raw store against the custody log
make verify
```

## Before first crawl — two unknowns to confirm

1. **Court directory.** `src/mariupol_seizures/crawl/courts.py` is seeded with the
   confirmed DNR Supreme Court portal (`supcourt-dpr.su`) and the Mariupol courts
   named in HRW rulings (Primorskyi, Pershotravnevyi, Telmanovskiy). Enumerate the
   full 25 (23 district + 2 regional, DNR/LNR) and verify each serves
   `modules.php?name=sud_delo`.
2. **Search form fields.** ГАС «Правосудие» GET field names vary by build. Run one
   manual "ownerless" search, copy the results URL from DevTools, and paste it into
   `RESULTS_TEMPLATE` with `{court} {date_from} {date_to} {page}` placeholders.

## Guardrails

- **Capture before parse**; raw store is append-only; everything hashed.
- **Owner PII is minimized** in shared outputs and gitignored. Officials/judges/
  beneficiaries in official capacity are in scope for accountability.
- Occupation rulings are evidence of the *act of seizure*, never valid title.
- Claude does not run the crawler — only the user, from their VPS.

## Contact & support

If you have a professional interest in this archive, you can get in touch with the
author at [kovalever@gmail.com](mailto:kovalever@gmail.com). You can also donate to
help keep this project alive and regularly updated, to
[kovalever@googlemail.com](mailto:kovalever@googlemail.com) (PayPal), or, if you are
US-based, to the Building Democracy Foundation, a 501(c)(3) registered NGO, via
[PayPal](https://www.paypal.com/donate/?hosted_button_id=TQ6VZ7CFSHTHW).
