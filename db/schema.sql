-- db/schema.sql
-- Lifecycle-centered schema for Mariupol property-seizure evidence.
-- Postgres 15 + PostGIS. Run: psql "$DATABASE_URL" -f db/schema.sql
--
-- Design: the spine is `property`; every source plugs in as seizure_event /
-- actor / court_case / financial / corroboration rows hanging off a property.
-- See docs/reconceptualization_2026.md §4 and docs/data_model.md.

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- for hashing / optional column crypto

-- ---------------------------------------------------------------------------
-- Canonical property (the spine)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS property (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    prewar_address  TEXT,                      -- Ukrainian, pre-2022
    occupation_address TEXT,                   -- Russian/occupation-era
    cadastral_no    TEXT,                       -- Ukrainian cadastre id, if known
    building_id     TEXT,                       -- groups apartments in a building
    geom            geometry(Point, 4326),      -- WGS84
    rd4u_category   TEXT,                        -- comma-separated set of A3.1/A3.2/A3.3/A3.6, or NULL (scripts/36)
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS property_geom_gix ON property USING gist (geom);
-- NULL building_id (court-case rows not yet linked to a building) doesn't
-- conflict with itself under a plain UNIQUE index -- only non-null
-- duplicates do, which is what load_buildings()'s ON CONFLICT relies on.
CREATE UNIQUE INDEX IF NOT EXISTS property_building_id_uidx ON property (building_id);

-- ---------------------------------------------------------------------------
-- Unit — apartment-level granularity under a building (`property`). The
-- spine (`property`) stays building-level for geocoding, corroboration,
-- RD4U categorization, and presentation; `unit` exists only so the DNR
-- ownerless-registry source (which is genuinely apartment-level, every row
-- carries apt_raw) doesn't lossily collapse 12,948 rows onto 1,637
-- buildings. Added 2026-06-29; see scripts/210.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS unit (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    property_id     BIGINT NOT NULL REFERENCES property(id) ON DELETE CASCADE,
    apt_no          TEXT NOT NULL,              -- normalized apt_raw (trimmed)
    apt_kind        TEXT,                       -- carried from registry apt_kind, informational
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS unit_property_apt_uidx ON unit (property_id, apt_no);
CREATE INDEX IF NOT EXISTS unit_property_ix ON unit(property_id);

-- ---------------------------------------------------------------------------
-- Owner — SENSITIVE. Minimize/encrypt. Never expose in shared outputs.
-- Living private individuals only; officials/beneficiaries go in `actor`.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS owner (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    property_id     BIGINT REFERENCES property(id) ON DELETE CASCADE,
    pseudonym       TEXT NOT NULL,              -- safe handle used everywhere public
    identity_enc    BYTEA,                      -- encrypted real identity (optional)
    citizenship     TEXT,                       -- e.g. 'UA'
    source_ref      TEXT,
    is_minimized    BOOLEAN NOT NULL DEFAULT true
);

-- ---------------------------------------------------------------------------
-- Seizure lifecycle events (1..n per property)
-- ---------------------------------------------------------------------------
-- 'ownerless_designation' = pre-petition step under the old (pre-ФКЗ-4) court
-- process (occupation_decrees designating a property "бесхозяйное").
-- 'registry_inclusion' = the post-ФКЗ-4 (15.12.2025) mechanism, where
-- inclusion in the ownerless-property registry IS itself the title transfer
-- (the court "признание права муниципальной собственности" stage was
-- abolished). Kept distinct: same evidentiary family, different legal act.
-- 'demolition' = the demolish->rebuild address-laundering track: a war-damaged
-- building is placed on an administrative demolition register (ГКО/MinStroy
-- order or Mariupol-admin "о сносе" decree) and razed, severing the address
-- chain before the cleared land is reallocated ('reallocation') to a developer
-- SPV without auction. Distinct legal act from the ownerless/court track.
-- 'expropriation' = a NAMED GKO decree directly seizing specific addressed
-- properties (no ownerless designation, no court) -- e.g. Постановление ГКО
-- №263 (29.09.2022), which forcibly expropriates 8 privately-owned buildings
-- with compensation contingent on a 30-day document deadline, and transfers
-- 5 former-Ukrainian-state buildings to municipal ownership outright. Added
-- 2026-06-29 (db/schema.sql ALTER TYPE; see scripts/209).
-- 'temporary_use' = the one-year administrative custody period between a
-- bezkhoz public notice going unanswered and the unit converting to
-- municipal ownership (Постановление ГКО №300, 29.09.2022, §2.7.1/2.16) --
-- distinct from 'ownerless_designation' (the notice/inspection act) and from
-- the eventual 'registry_inclusion'/'court_transfer' (the conversion act).
-- Added 2026-06-29; no dated per-property records loaded yet (the decree is
-- a procedural framework, not a named list) -- reserved for when one is found.
-- 'reclaim' = a REVERSAL, not a seizure: the administration struck a unit from
-- the ownerless register because a living owner/heir surfaced with proof of
-- title ("О снятии с учёта..."/"Об исключении... из Реестра", under Закон ДНР
-- №66-РЗ 21.03.2024). The counter-signal to the whole pipeline -- kept on the
-- spine ONLY where the property already carries a seizure-forward event, so a
-- designated-then-reclaimed unit reads as knowing dispossession that was later
-- undone. Isolated from every seizure analytic (RD4U categorization, STATS
-- seizure counts) by never appearing in their explicit stage sets. Added
-- 2026-07-02 (ALTER TYPE migration below; loader load_ownerless_removals()).
CREATE TYPE seizure_stage AS ENUM (
    'utility_cutoff', 'notice', 'inspection', 'ownerless_designation',
    'demolition', 'court_petition', 'court_transfer', 'appeal', 'entered_force',
    'reallocation', 'resale', 'registry_inclusion', 'expropriation',
    'temporary_use', 'reclaim'
);

CREATE TABLE IF NOT EXISTS seizure_event (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    property_id     BIGINT NOT NULL REFERENCES property(id) ON DELETE CASCADE,
    unit_id         BIGINT REFERENCES unit(id) ON DELETE SET NULL,
                                                  -- set only for stage='registry_inclusion'
                                                  -- rows whose source carries an apartment
                                                  -- number; NULL for every other stage.
    stage           seizure_stage NOT NULL,
    event_date      DATE,
    source_doc_id   BIGINT,                     -- -> source_document.id
    confidence      NUMERIC(3,2),               -- 0..1
    detail          JSONB,
    dedup_key       TEXT,                       -- e.g. 'ownerless_registry:<sha256>:<seq_no>'
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- For an already-existing table (pre-2026-06-29 deployments), CREATE TABLE IF
-- NOT EXISTS above is a no-op, so the new column needs its own idempotent
-- migration statement:
ALTER TABLE seizure_event ADD COLUMN IF NOT EXISTS unit_id BIGINT REFERENCES unit(id) ON DELETE SET NULL;
-- Enum values added after the original CREATE TYPE need their own idempotent
-- migration for pre-existing deployments (CREATE TYPE above is a no-op once the
-- type exists). ADD VALUE IF NOT EXISTS is PG 12+ and safe outside a txn block.
ALTER TYPE seizure_stage ADD VALUE IF NOT EXISTS 'reclaim';
CREATE INDEX IF NOT EXISTS seizure_event_prop_ix ON seizure_event(property_id);
CREATE INDEX IF NOT EXISTS seizure_event_stage_ix ON seizure_event(stage);
CREATE INDEX IF NOT EXISTS seizure_event_unit_ix ON seizure_event(unit_id) WHERE unit_id IS NOT NULL;
-- NULL dedup_key (court-case lifecycle stages) doesn't conflict with itself;
-- only batch-loaded rows (which always set dedup_key) get idempotent re-runs.
CREATE UNIQUE INDEX IF NOT EXISTS seizure_event_dedup_uidx ON seizure_event (dedup_key);

-- ---------------------------------------------------------------------------
-- Court cases (0..1 per seizure chain; the crown-jewel record)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS court_case (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    property_id     BIGINT REFERENCES property(id) ON DELETE SET NULL,
    court           TEXT NOT NULL,
    case_number     TEXT,
    case_uid        TEXT UNIQUE,                -- ГАС Правосудие uid
    judge           TEXT,
    legal_grounds   TEXT,                       -- usually 'нет регистрации в ЕГРН'
    outcome         TEXT,                       -- first-instance result; the
                                                  -- evidentiary record of the
                                                  -- occupation court's act --
                                                  -- never overwritten by appeal
    final_outcome   TEXT,                       -- post-appeal status, set by
                                                  -- reconcile_appeal_outcomes()
                                                  -- when an appeal reversed a
                                                  -- 'granted' outcome; NULL
                                                  -- means "outcome stands"
    filed_date      DATE,
    decided_date    DATE,
    entered_force   DATE,
    source_doc_id   BIGINT
);

-- ---------------------------------------------------------------------------
-- Actors — officials, judges, commissions, notaries, beneficiaries (in scope)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS actor (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    full_name       TEXT,
    role            TEXT,    -- signing_official|judge|commission_member|notary|beneficiary
    org             TEXT,
    notes           TEXT,
    UNIQUE (full_name, role, org)
);
-- The UNIQUE above does NOT dedupe rows with org IS NULL (Postgres treats
-- NULLs as distinct), so petitioners/signing-officials inserted with a NULL
-- org would duplicate on every record. This partial index enforces one row
-- per (full_name, role) when org is null. See db/load.py:_upsert_actor.
CREATE UNIQUE INDEX IF NOT EXISTS actor_null_org_uidx
    ON actor (full_name, role) WHERE org IS NULL;
CREATE TABLE IF NOT EXISTS event_actor (
    seizure_event_id BIGINT REFERENCES seizure_event(id) ON DELETE CASCADE,
    actor_id         BIGINT REFERENCES actor(id) ON DELETE CASCADE,
    PRIMARY KEY (seizure_event_id, actor_id)
);

-- ---------------------------------------------------------------------------
-- Financial layer
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS financial (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    property_id     BIGINT REFERENCES property(id) ON DELETE CASCADE,
    kind            TEXT,    -- mortgage_program|sale|budget_allocation
    amount          NUMERIC,
    currency        TEXT,
    bank            TEXT,
    counterparty    TEXT,
    source_doc_id   BIGINT
);

-- ---------------------------------------------------------------------------
-- Corroboration
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS corroboration (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    property_id     BIGINT REFERENCES property(id) ON DELETE CASCADE,
    kind            TEXT,    -- satellite_pair|testimony|mirror_source|utility_signal|displacement_claim|unosat_damage
    reference       TEXT,
    detail          JSONB,
    dedup_key       TEXT,    -- e.g. 'housing_distribution:<sha256>:<building_key>'
    captured_at     TIMESTAMPTZ,
    -- Tier-3 independent-corroboration columns (docs/tier3_corroboration_design.md),
    -- added idempotently by scripts/53_load_unosat_damage.py. NULL/unset for the
    -- pre-existing mirror_source/displacement_claim rows.
    source_doc_id   BIGINT REFERENCES source_document(id),
    confidence      NUMERIC(3,2),               -- 0..1
    verdict         TEXT CHECK (verdict IN ('confirms','refutes','indeterminate')),
    observed_start  DATE,                       -- start of the period the independent
                                                  -- attestation covers (e.g. satellite sensor date)
    observed_end    DATE
);
CREATE UNIQUE INDEX IF NOT EXISTS corroboration_dedup_uidx ON corroboration (dedup_key);

-- ---------------------------------------------------------------------------
-- Source documents — chain of custody for every raw artifact
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS source_document (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    url             TEXT,
    court           TEXT,
    kind            TEXT,                       -- results|case_card|act|list|pdf
    sha256          TEXT NOT NULL,
    raw_path        TEXT NOT NULL,
    http_status     INT,
    captured_at     TIMESTAMPTZ NOT NULL,
    UNIQUE (sha256)
);

-- Toponymic join table: prewar Ukrainian <-> occupation address ----------------
CREATE TABLE IF NOT EXISTS toponym (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    prewar_name     TEXT,
    occupation_name TEXT,
    kind            TEXT,                        -- rename | readdress (post-demolition)
    -- TEXT, not DATE: rename dates are historically partial. 92/107 source
    -- rows know only the year ("2022"), 3 the month ("2022-11"); only 12
    -- carry a full ISO date. A DATE column would force false precision
    -- (year -> Jan 1) or drop the value. TEXT preserves each source's actual
    -- precision verbatim (ISO-8601: "2022" | "2022-11" | "2022-11-21").
    changed_on      TEXT,
    source_ref      TEXT
);
