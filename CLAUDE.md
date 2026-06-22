# CLAUDE.md — Mariupol Property-Seizure Documentation

Project memory for Claude Code. Read this first every session.

## Mission
Build a verifiable, queryable, court-admissible evidence base linking **specific
Mariupol properties** to **specific unlawful seizure acts** by **named Russian
occupation actors**, structured to feed two downstream consumers:
1. **Restitution** — Council of Europe Register of Damage for Ukraine (RD4U) /
   future Claims Commission. Map each property to a claim category
   (A3.1/A3.2/A3.3/A3.6 — A3.6 = loss of access to property in occupied territory).
2. **Criminal accountability** — Rome Statute art. 8(2)(b)(viii) (transfer of the
   occupier's own population) and unlawful appropriation of property.

If a feature does not move a property toward one of those two endpoints, it is out
of scope. Full rationale: `docs/reconceptualization_2026.md`.

## Current state (June 2026) — see `docs/progress_report_2026-06.md` for the full review
The project is now a **multi-source evidentiary spine** loaded to PostgreSQL/PostGIS,
not a single court scraper. Snapshot: 6,084 properties on spine · 11,517
corroboration rows · all RD4U-categorized · 39,061+ raw artifacts. The four
Mariupol district court dockets are **saturated** (2,666 cases) and, with
ФКЗ-4 (Dec 2025) abolishing the court stage, that case type is closed going forward —
the live front line has moved to the 12,948-entry **ownerless registry** ahead of the
**1 July 2026** re-registration deadline. Gaps & follow-ups: progress report §5.

A 28-building-chat Telegram corpus (~145K messages) has been deep-mined
(`scripts/148`–`151`) for cross-chat intel, primary-source documents posted by
residents, a temporal differential against dated ownerless-registry snapshots,
and a photo/video lifecycle manifest; findings are loaded into `corroboration`
(`scripts/152`) and scored for case-study write-up (`scripts/153`). Two
documented seizure modalities now exist in `docs/case_studies/`: demolish→
rebuild→resell address-laundering (Нахимова 82) and **restoration-without-
restitution** (Ленина 106 — a demolition decree on file, the building actually
restored not razed, ownership stripped via the registry regardless). See
`memory/deep_chat_corpus_analysis_2026-06.md` and
`memory/session_evidence_load_and_qgis_2026-06.md`.

## Primary data sources
1. Occupation **court records** (ГАС «Правосудие» portals, DNR/LNR — ~25 courts, HRW
   2026). Case type: особое производство → *признание права муниципальной
   собственности на бесхозяйную недвижимую вещь* (ГПК РФ гл. 33). Each case is a
   dated, self-incriminating lifecycle: utility cut-off → "ownerless" notice →
   inspection → designation → court petition → transfer → entry into force →
   reallocation. Directory: `src/mariupol_seizures/crawl/courts.py`. **Saturated.**
2. **Ownerless registry + municipal decrees** (Mariupol gosuslugi) — the now-live
   front line; 12,948 registry entries + 968 decrees.
3. **Federal damage/reconstruction tracker** (1,941 buildings), **demolition
   registers** (MinStroy + municipal), **DNR land-grant orders** (developer SPVs),
   **housing queue/distribution**, **ЕИСЖС** new-build registry.
4. **Legal-mechanism scaffolding** (DNR/federal normative acts, rungs [A]–[H]) +
   **stakeholder network** + **EGRUL** ownership. See `docs/legal_mechanisms_review.md`,
   `docs/stakeholder_network.md`.

## Pipeline (three stages, each re-runnable; per-source scripts numbered in `scripts/`)
1. **Crawl** (`scripts/01_crawl.py` + per-source crawlers 05/07/08/10/13/14/16/17/35/39)
   — harvest raw HTML/PDF/XLSX; capture forensically; never parse during fetch.
2. **Parse** (`scripts/02_parse.py` + per-source parsers) — extract fields from the
   *raw store*; safe to iterate without re-hitting sources.
3. **Load** (`scripts/03_load.py` + 27/28/30/32) — load parsed rows into
   PostgreSQL/PostGIS (`db/schema.sql`). Read-only analytics: 33 (corroboration),
   36 (RD4U), 40 (stakeholder network).

Building-chat deep-analysis stream (148-155, no `db/schema.sql` changes —
findings land in existing `corroboration` rows, kinds `ownerless_disposition`/
`cited_legal_instrument`/`lifecycle_media`): 148 cross-chat intel, 149 document
inventory, 150 ownerless temporal differential, 151 media lifecycle manifest,
152 loader, 153 case-study candidate scorer, 154 QGIS findings export, 155
targeted geocoder. `src/mariupol_seizures/chat_buildings.py` holds the
verified chat→spine-pid mapping these scripts resolve through — extend it
when adding a new per-chat parser; never re-derive a chat's building from its
free-text title when this table already has the chat.

## NON-NEGOTIABLE forensic rules
- **Capture before parse.** Every HTTP body is written verbatim to `data/raw/`,
  keyed by SHA-256, with an ISO-8601 UTC timestamp + source URL in a sidecar
  `.meta.json`, BEFORE any parsing. The raw store is append-only and immutable.
- **SHA-256 everything.** No file or record enters the pipeline without a hash.
- **Chain of custody.** Berkeley Protocol. Every transformation is logged with
  inputs, outputs, hashes, timestamps. Reproducible from raw → DB.
- **Occupation records are evidence of the *act*, not valid title.** Never present
  an occupation registration/ruling as authoritative ownership. Ukraine does not
  recognize them; neither do we.

## PRIVACY (hard rule)
Lawful owners who are living private individuals are **minimized/pseudonymized** in
any shared output. Owner identity lives only in the secured `owner` table (treat as
sensitive personal data; encrypt at rest; never commit). Named **occupation
officials, judges, beneficiaries acting in official capacity** are in scope for
accountability and are not minimized.

## Workflow conventions (carried from the project's standing rules)
- **Generate scripts; do NOT auto-run pandas/analysis.** Let the user execute.
  Crawling hits a geoblocked foreign state system — only the user runs it, from
  their own Russia-routed VPS. Claude never executes the crawler.
- Use `PROJECT_ROOT` + config (`src/mariupol_seizures/config.py`); no hardcoded paths.
- Comprehensive error handling + logging in every script.
- Resource envelope: 8 GB RAM, ~$0–20 total. Stream, don't batch. The one
  justified recurring cost is the VPS for geoblocked access.
- No regex-only address normalization as the final step — keep raw + normalized;
  confidence-score every fuzzy match (≥0.8 to be claim-grade); require ≥2
  independent sources for legal-grade linkage rows.

## Security / safety
- `.env`, `data/`, anything with owner PII, and the raw evidence store are
  **gitignored**. Verify before any commit.
- Do not commit court session cookies, proxy credentials, or API keys.

## Stack
Python 3.11+, requests + BeautifulSoup/lxml (crawl/parse), PostgreSQL 15 + PostGIS
(store), rapidfuzz (matching), psycopg2. See `pyproject.toml`.
