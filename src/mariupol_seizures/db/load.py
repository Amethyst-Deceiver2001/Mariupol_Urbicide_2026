"""Stage 3: load parsed JSONL rows into PostgreSQL/PostGIS.

Idempotent upserts keyed on case_uid / sha256. Owner data is written to the
minimized `owner` table only; never echoed to logs or shared outputs.
"""
from __future__ import annotations

import csv
import hashlib
import json
import logging
import re
import sqlite3
from collections import Counter
from pathlib import Path

import psycopg2

from .. import config
from ..normalize.address import (
    address_to_building_key,
    classify_street,
    compute_building_key,
    norm_commas,
    strip_garbage_prefix,
)

log = logging.getLogger(__name__)

PARSED_DIR = config.PROJECT_ROOT / "data" / "parsed"

# Roles we accept verbatim from a source; anything else is treated as a parser
# artifact and normalized by the caller (see load_demolition_decrees).
_VALID_ACTOR_ROLES = frozenset({
    "signing_official", "judge", "commission_member", "notary", "beneficiary",
})


def run(jsonl: str = "data/parsed_cases.jsonl") -> None:
    path = Path(config.PROJECT_ROOT / jsonl)
    if not path.exists():
        raise SystemExit(f"{path} not found — run scripts/02_parse.py first.")

    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()
    loaded = skipped = 0

    with path.open(encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            try:
                _load_record(cur, rec)
                loaded += 1
            except Exception:
                log.exception("failed to load case_uid=%s", rec.get("case_uid"))
                skipped += 1

    con.commit()
    cur.close()
    con.close()
    log.info("loaded %d cases, skipped %d  -> %s",
             loaded, skipped, config.DATABASE_URL.split("@")[-1])
    print(f"loaded {loaded} cases, skipped {skipped}")


def _fetch_log_meta(sha: str) -> tuple[str | None, str | None]:
    """Look up (url, court) for a SHA from the SQLite fetch_log."""
    try:
        con = sqlite3.connect(config.STATE_DB)
        row = con.execute(
            "SELECT url, court FROM fetch_log WHERE sha256 = ? LIMIT 1", (sha,)
        ).fetchone()
        return (row[0], row[1]) if row else (None, None)
    except Exception:
        return None, None


def _upsert_source_doc(cur, raw_path: str) -> int | None:
    """Insert the raw court-card HTML into source_document if not already there.

    Returns the source_document.id (needed for FK on court_case/seizure_event),
    or None if the file is missing.
    """
    p = Path(raw_path)
    if not p.exists():
        return None
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    url, court = _fetch_log_meta(sha)
    cur.execute(
        """INSERT INTO source_document (url, court, kind, sha256, raw_path, http_status, captured_at)
           VALUES (%s, %s, 'case_card', %s, %s, 200, now())
           ON CONFLICT (sha256) DO NOTHING""",
        (url, court, sha, raw_path),
    )
    cur.execute("SELECT id FROM source_document WHERE sha256 = %s", (sha,))
    row = cur.fetchone()
    return row[0] if row else None


def _fetch_source_doc_meta(sha: str) -> tuple | None:
    """Look up (url, source_type, raw_path, captured_at) for a SHA from the
    SQLite source_document table populated by capture_source()/
    capture_derived() in forensics.py (used for reference documents like
    ownerless-registry XLSX and OCR'd decree PDFs, as opposed to fetch_log
    which covers court case-card HTML)."""
    try:
        con = sqlite3.connect(config.STATE_DB)
        return con.execute(
            "SELECT url, source_type, raw_path, captured_at FROM source_document"
            " WHERE sha256 = ? LIMIT 1", (sha,)
        ).fetchone()
    except Exception:
        return None


def _upsert_source_doc_by_sha(cur, sha256: str | None) -> int | None:
    """Insert/locate a non-court-card source document (ownerless-registry
    XLSX, OCR'd decree PDF) in the postgres source_document table by SHA-256,
    using metadata from the SQLite forensic capture log. Returns
    source_document.id, or None if sha256 is missing or not found in the
    SQLite source_document table."""
    if not sha256:
        return None
    cur.execute("SELECT id FROM source_document WHERE sha256 = %s", (sha256,))
    row = cur.fetchone()
    if row:
        return row[0]
    meta = _fetch_source_doc_meta(sha256)
    if not meta:
        return None
    url, source_type, raw_path, captured_at = meta
    cur.execute(
        """INSERT INTO source_document (url, court, kind, sha256, raw_path, http_status, captured_at)
           VALUES (%s, NULL, %s, %s, %s, 200, %s)
           ON CONFLICT (sha256) DO NOTHING""",
        (url, source_type, sha256, raw_path, captured_at),
    )
    cur.execute("SELECT id FROM source_document WHERE sha256 = %s", (sha256,))
    row = cur.fetchone()
    return row[0] if row else None


def _upsert_actor(cur, full_name: str | None, role: str, org: str | None,
                  notes: str | None = None) -> int | None:
    """Insert a named occupation actor into `actor` if not already present
    (in scope for accountability per CLAUDE.md -- not minimized like living
    owners). Returns actor.id, or None if full_name is empty.

    SELECT-first, NOT a bare ON CONFLICT: the table's UNIQUE (full_name, role,
    org) does not dedupe rows with org IS NULL (Postgres treats NULLs as
    distinct, so ON CONFLICT never fires) -- without the explicit pre-check
    every call would insert a duplicate. The actor_null_org_uidx partial index
    enforces this at the DB level too, but the SELECT keeps the function
    correct regardless of which uniqueness path applies."""
    if not full_name or not full_name.strip():
        return None
    name = full_name.strip()
    # Reject parser artifacts: a real person/org name is never this long. Some
    # land-order rows leaked whole-decree prose (10-40 KB) into beneficiary_name;
    # such a value also overflows the btree index (max 8191 bytes). 250 chars
    # clears the longest legitimate name (full DNR ministry titles ~70 chars).
    if len(name) > 250:
        log.warning("skipping oversized actor name (len=%d, role=%s) -- parser artifact",
                    len(name), role)
        return None
    cur.execute(
        """SELECT id FROM actor WHERE full_name = %s AND role = %s
           AND org IS NOT DISTINCT FROM %s""",
        (name, role, org),
    )
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(
        """INSERT INTO actor (full_name, role, org, notes)
           VALUES (%s, %s, %s, %s)
           ON CONFLICT DO NOTHING
           RETURNING id""",
        (name, role, org, notes),
    )
    row = cur.fetchone()
    if row:
        return row[0]
    # Lost an insert race / conflict fired: re-select the surviving row.
    cur.execute(
        """SELECT id FROM actor WHERE full_name = %s AND role = %s
           AND org IS NOT DISTINCT FROM %s""",
        (name, role, org),
    )
    row = cur.fetchone()
    return row[0] if row else None


def _load_record(cur, rec: dict) -> None:
    case_uid = rec.get("case_uid")

    # ── Idempotency: reuse existing property_id if this case was already loaded ─
    cur.execute("SELECT property_id FROM court_case WHERE case_uid = %s", (case_uid,))
    existing = cur.fetchone()

    addr = rec["addresses"][0] if rec.get("addresses") else None
    prewar = rec.get("prewar_address_hint")
    notes = (
        f"from case {rec.get('case_number')} | type={rec.get('property_type')} "
        f"area={rec.get('area_sqm')}sqm"
    )

    # building_id groups this property with address_registry/load_buildings
    # rows for the same physical building. Currently 0/2666 cases have a
    # parseable addresses[0] (ruling text isn't OCR'd yet) -- this is
    # forward-looking infrastructure for when it is.
    building_id = None
    if addr:
        parts = [p.strip() for p in norm_commas(addr).split(",")]
        street = parts[0] if parts else None
        house = parts[1] if len(parts) > 1 else None
        building_id = address_to_building_key(street, house)

    if existing:
        property_id = existing[0]
        # Refresh address fields if parser extracted them this run.
        # building_id intentionally NOT touched here: changing it on an
        # already-loaded row could collide with a building_id assigned to a
        # different property row by load_buildings()/load_ownerless_*() --
        # that merge case is out of scope for now (0/2666 currently apply).
        if addr or prewar:
            cur.execute(
                """UPDATE property
                   SET occupation_address = COALESCE(%s, occupation_address),
                       prewar_address     = COALESCE(%s, prewar_address),
                       rd4u_category      = COALESCE(%s, rd4u_category)
                   WHERE id = %s""",
                (addr, prewar, rec.get("rd4u_category_hint"), property_id),
            )
    else:
        # ON CONFLICT (building_id): a NULL building_id never conflicts (the
        # common case today), so this is a plain insert. If a future OCR run
        # *does* compute a building_id that load_buildings()/
        # load_ownerless_*() already created a property row for, merge into
        # that row instead of erroring.
        cur.execute(
            """INSERT INTO property
                   (occupation_address, prewar_address, cadastral_no, building_id, rd4u_category, notes)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (building_id) DO UPDATE
                   SET occupation_address = COALESCE(EXCLUDED.occupation_address, property.occupation_address),
                       prewar_address     = COALESCE(EXCLUDED.prewar_address, property.prewar_address),
                       cadastral_no       = COALESCE(EXCLUDED.cadastral_no, property.cadastral_no),
                       rd4u_category      = COALESCE(EXCLUDED.rd4u_category, property.rd4u_category)
               RETURNING id""",
            (addr, prewar, rec.get("cadastral_no"), building_id,
             rec.get("rd4u_category_hint"), notes),
        )
        property_id = cur.fetchone()[0]

    # ── source_document (chain of custody link) ───────────────────────────────
    source_doc_id = _upsert_source_doc(cur, rec.get("raw_path", ""))

    # ── owner (sensitive — minimized, never logged) ───────────────────────────
    if rec.get("owner_sensitive") and rec.get("owner_raw"):
        pseudonym = f"OWN-{case_uid[:8]}"
        cur.execute(
            """INSERT INTO owner
                   (property_id, pseudonym, citizenship, source_ref, is_minimized)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT DO NOTHING""",
            (property_id, pseudonym, "UA", case_uid, True),
            # owner_raw is intentionally NOT written to the DB here;
            # store it separately in the encrypted identity layer.
        )

    # ── court_case ────────────────────────────────────────────────────────────
    cur.execute(
        """INSERT INTO court_case
               (property_id, court, case_number, case_uid, judge,
                legal_grounds, outcome, filed_date, decided_date,
                entered_force, source_doc_id)
           VALUES (%s, %s, %s, %s, %s, %s, %s,
                   to_date(%s, 'DD.MM.YYYY'),
                   to_date(%s, 'DD.MM.YYYY'),
                   to_date(%s, 'DD.MM.YYYY'),
                   %s)
           ON CONFLICT (case_uid) DO UPDATE
               SET judge          = EXCLUDED.judge,
                   legal_grounds  = EXCLUDED.legal_grounds,
                   outcome        = EXCLUDED.outcome,
                   filed_date     = EXCLUDED.filed_date,
                   decided_date   = EXCLUDED.decided_date,
                   entered_force  = EXCLUDED.entered_force,
                   source_doc_id  = EXCLUDED.source_doc_id""",
        (
            property_id,
            rec.get("court"),
            rec.get("case_number"),
            case_uid,
            rec.get("judge"),
            json.dumps(rec.get("legal_grounds", []), ensure_ascii=False),
            rec.get("outcome"),
            rec.get("filed_date"),
            rec.get("decided_date"),
            rec.get("entered_force_date"),
            source_doc_id,
        ),
    )

    # ── actor: judge ──────────────────────────────────────────────────────────
    # judge carries org=court (non-null) so the table UNIQUE dedupes it; the
    # petitioner has org=NULL and MUST go through _upsert_actor (SELECT-first)
    # or it duplicates on every record -- see _upsert_actor docstring.
    if rec.get("judge"):
        _upsert_actor(cur, rec["judge"], "judge", rec.get("court"))

    # ── actor: petitioner ─────────────────────────────────────────────────────
    if rec.get("petitioner"):
        _upsert_actor(cur, rec["petitioner"], "signing_official", None)

    # ── seizure_events: canonical court milestones (court_petition /
    #    court_transfer). One row per (case, stage); dedup_key makes re-runs
    #    idempotent (the stages loop previously had NO dedup_key and duplicated
    #    every row on a second load -- see db/schema.sql comment + memory). ────
    confidence = rec.get("parse_confidence", 0.7)
    for st in rec.get("stages", []):
        detail = {"source": "court_card", "event": st.get("event")}
        detail.update(st.get("detail", {}))
        dedup_key = f"court_case:{case_uid}:{st['stage']}"
        cur.execute(
            """INSERT INTO seizure_event
                   (property_id, stage, event_date, confidence, source_doc_id, detail, dedup_key)
               VALUES (%s, %s::seizure_stage, to_date(%s, 'DD.MM.YYYY'), %s, %s, %s, %s)
               ON CONFLICT (dedup_key) DO UPDATE
                   SET property_id   = EXCLUDED.property_id,
                       event_date    = EXCLUDED.event_date,
                       confidence    = EXCLUDED.confidence,
                       source_doc_id = EXCLUDED.source_doc_id,
                       detail        = EXCLUDED.detail""",
            (
                property_id,
                st["stage"],
                st["date"],
                confidence,
                source_doc_id,
                json.dumps(detail, ensure_ascii=False),
                dedup_key,
            ),
        )

    _load_complaints(cur, case_uid, property_id, source_doc_id, confidence,
                      rec.get("complaints", []))


def _load_complaints(cur, case_uid: str, property_id: int,
                      source_doc_id: int | None, confidence: float,
                      complaints: list[dict]) -> None:
    """seizure_event(stage='appeal') rows from cont4 ЖАЛОБА blocks.

    event_date prefers the decided date; falls back to when the higher
    court was scheduled to hear it, then the latest movement date, for
    complaints still pending. dedup_key makes re-runs (e.g. once a
    pending complaint is later decided) idempotent updates.
    """
    for c in complaints:
        event_date = c.get("decision_date") or c.get("scheduled_date")
        if not event_date and c.get("movement"):
            event_date = c["movement"][-1]["date"]
        detail = {
            "source": "court_card",
            "complaint_no": c.get("complaint_no"),
            "instance": c.get("instance"),
            "complaint_type_raw": c.get("complaint_type_raw"),
            "complainant_role": c.get("complainant_role"),
            "higher_court": c.get("higher_court"),
            "outcome_raw": c.get("outcome_raw"),
            "outcome": c.get("outcome", "pending"),
            "movement": c.get("movement", []),
        }
        dedup_key = f"court_case:{case_uid}:appeal:{c.get('complaint_no', '?')}"
        cur.execute(
            """INSERT INTO seizure_event
                   (property_id, stage, event_date, confidence, source_doc_id, detail, dedup_key)
               VALUES (%s, 'appeal'::seizure_stage, to_date(%s, 'DD.MM.YYYY'), %s, %s, %s, %s)
               ON CONFLICT (dedup_key) DO UPDATE
                   SET event_date    = EXCLUDED.event_date,
                       confidence    = EXCLUDED.confidence,
                       source_doc_id = EXCLUDED.source_doc_id,
                       detail        = EXCLUDED.detail""",
            (property_id, event_date, confidence, source_doc_id,
             json.dumps(detail, ensure_ascii=False), dedup_key),
        )


def load_appeals(jsonl: str = "data/parsed_cases.jsonl") -> None:
    """Load appeal/cassation seizure_events for cases already in court_case.

    Narrow companion to run()/_load_record() for re-parses that only touch
    cont4 (complaints) -- avoids re-running the stages loop in _load_record,
    which has no dedup_key and would duplicate the existing court_petition/
    court_transfer/entered_force events on a second pass.
    """
    path = Path(config.PROJECT_ROOT / jsonl)
    if not path.exists():
        raise SystemExit(f"{path} not found — run scripts/02_parse.py first.")

    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()
    loaded = skipped = no_case = 0

    with path.open(encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            complaints = rec.get("complaints")
            if not complaints:
                continue
            case_uid = rec["case_uid"]
            cur.execute(
                "SELECT property_id, source_doc_id FROM court_case WHERE case_uid = %s",
                (case_uid,),
            )
            row = cur.fetchone()
            if not row:
                no_case += 1
                continue
            property_id, source_doc_id = row
            try:
                _load_complaints(cur, case_uid, property_id, source_doc_id,
                                  rec.get("parse_confidence", 0.7), complaints)
                loaded += 1
            except Exception:
                log.exception("failed to load complaints for case_uid=%s", case_uid)
                skipped += 1

    con.commit()
    cur.close()
    con.close()
    log.info("loaded appeals for %d cases, skipped %d, %d not in court_case",
             loaded, skipped, no_case)
    print(f"loaded appeals for {loaded} cases, skipped {skipped}, "
          f"{no_case} not yet in court_case")


# Patterns for a 'reversed' appeal's outcome_raw -> court_case.final_outcome.
# Only consulted when court_case.outcome=='granted' (i.e. the appeal
# overturned a first-instance grant). Order matters: "БЕЗ РАССМОТРЕНИЯ" and
# "НОВОГО РЕШЕНИЯ" are mutually exclusive phrasings in this corpus.
_REVERSAL_FINAL_OUTCOME_MAP: list[tuple[re.Pattern, str]] = [
    (re.compile(r"БЕЗ\s+РАССМОТРЕНИ\w*", re.I), "left_without_consideration"),
    (re.compile(r"НОВ\w*\s+РЕШЕНИ\w*", re.I), "reversed_unknown"),
]


def reconcile_appeal_outcomes() -> None:
    """For court_case rows whose first-instance outcome=='granted' but a
    later appeal stage='reversed' it, record the post-appeal status in
    court_case.final_outcome and flag the corresponding court_transfer
    seizure_event as superseded.

    `outcome` is left untouched -- it is the evidentiary record of what the
    occupation court itself ruled (the unlawful act). `final_outcome`
    records what is currently known about whether that ruling stands:
      - 'left_without_consideration': the appellate court reversed the grant
        and left the petition without a merits decision -- the title
        transfer via THIS case did not become final.
      - 'reversed_unknown': the appellate court reversed and substituted its
        own decision, but its content is not captured in our source data --
        needs manual review of the appellate ruling text.

    Cases whose first-instance outcome was never 'granted' (e.g.
    'discontinued') are left alone: there is no court_transfer to supersede,
    and the first-instance outcome is already the final known status.

    rd4u_category is intentionally NOT touched here: it reflects the
    property's physical loss of access under occupation, not the fate of any
    single court case.

    Idempotent: re-running re-derives the same final_outcome and overwrites
    the same detail keys.
    """
    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()

    cur.execute("ALTER TABLE court_case ADD COLUMN IF NOT EXISTS final_outcome TEXT")

    cur.execute(
        """SELECT dedup_key, detail->>'outcome_raw'
               FROM seizure_event
               WHERE stage = 'appeal' AND detail->>'outcome' = 'reversed'"""
    )
    reversed_appeals = cur.fetchall()

    updated = skipped_not_granted = unmatched = 0
    for appeal_dedup_key, outcome_raw in reversed_appeals:
        case_uid = appeal_dedup_key.split(":")[1]

        cur.execute("SELECT outcome FROM court_case WHERE case_uid = %s", (case_uid,))
        row = cur.fetchone()
        if not row:
            log.warning("reversed appeal %s: no court_case for case_uid=%s",
                         appeal_dedup_key, case_uid)
            continue
        first_instance_outcome, = row
        if first_instance_outcome != "granted":
            log.info("case_uid=%s: outcome=%s (not 'granted'), no court_transfer "
                     "to reconcile -- leaving final_outcome unset",
                     case_uid, first_instance_outcome)
            skipped_not_granted += 1
            continue

        final_outcome = None
        for pat, value in _REVERSAL_FINAL_OUTCOME_MAP:
            if pat.search(outcome_raw or ""):
                final_outcome = value
                break
        if final_outcome is None:
            log.warning("case_uid=%s: reversed appeal outcome_raw=%r matched no "
                         "known pattern -- defaulting to 'reversed_unknown'",
                         case_uid, outcome_raw)
            final_outcome = "reversed_unknown"
            unmatched += 1

        cur.execute(
            "UPDATE court_case SET final_outcome = %s WHERE case_uid = %s",
            (final_outcome, case_uid),
        )
        cur.execute(
            """UPDATE seizure_event
                   SET detail = detail || %s::jsonb
                   WHERE dedup_key = %s""",
            (json.dumps({
                "superseded_by_appeal": True,
                "final_status": final_outcome,
                "appeal_dedup_key": appeal_dedup_key,
            }, ensure_ascii=False),
             f"court_case:{case_uid}:court_transfer"),
        )
        if cur.rowcount == 0:
            log.warning("case_uid=%s: outcome='granted' but no court_transfer "
                         "seizure_event found to flag", case_uid)
        updated += 1

    con.commit()
    cur.close()
    con.close()
    log.info("reconciled %d reversed-appeal cases (%d not 'granted', "
             "%d unmatched outcome_raw)", updated, skipped_not_granted, unmatched)
    print(f"reconciled {updated} reversed-appeal cases "
          f"({skipped_not_granted} not 'granted', {unmatched} unmatched outcome_raw)")


def _load_geocode_index() -> dict[str, tuple[float, float]]:
    """building_key -> (lat, lon), merging geocoded_buildings.jsonl (Nominatim/
    Overpass/Google) and manual_geocode_overrides.jsonl (Yandex-Maps-verified),
    filtered to geocode_confidence >= 0.8 (claim-grade per CLAUDE.md).
    low_confidence_buildings.jsonl (<0.8) is intentionally excluded."""
    index: dict[str, tuple[float, float]] = {}
    for fname in ("geocoded_buildings.jsonl", "manual_geocode_overrides.jsonl"):
        path = PARSED_DIR / fname
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            if d.get("geocode_confidence", 0) >= 0.8:
                index[d["building_key"]] = (d["lat"], d["lon"])
    return index


def load_buildings(jsonl: str = "data/parsed/address_registry.jsonl") -> None:
    """Load address_registry.jsonl buildings as property rows keyed on
    building_id, with geom from geocoded_buildings.jsonl /
    manual_geocode_overrides.jsonl (>=0.8) or, for the small set of buildings
    that were already geocoded at registry-build time (building_key contains
    '|@lat,lon', sourced from eisghs_наш.дом.рф), from address_registry.jsonl
    itself. Idempotent via the property_building_id_uidx unique index."""
    path = Path(config.PROJECT_ROOT / jsonl)
    if not path.exists():
        raise SystemExit(f"{path} not found — run scripts/21_build_address_registry.py first.")

    geocodes = _load_geocode_index()

    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()
    loaded = with_geom = 0

    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            building_id = d["building_key"]

            if d.get("house_no"):
                occupation_address = f"{d['street_occupation']}, {d['house_no']}"
                prewar_address = (f"{d['prewar_name']}, {d['house_no']}"
                                  if d.get("prewar_name") else None)
            else:
                occupation_address = d["street_occupation"]
                prewar_address = d.get("prewar_name")

            cadastral_no = (", ".join(d["cadastral_numbers"])
                            if d.get("cadastral_numbers") else None)

            already = d.get("already_geocoded")
            if already:
                lat, lon = already["lat"], already["lon"]
            else:
                lat, lon = geocodes.get(building_id, (None, None))

            if lat is not None:
                with_geom += 1
                cur.execute(
                    """INSERT INTO property
                           (building_id, occupation_address, prewar_address, cadastral_no, geom)
                       VALUES (%s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                       ON CONFLICT (building_id) DO UPDATE
                           SET occupation_address = EXCLUDED.occupation_address,
                               prewar_address     = COALESCE(EXCLUDED.prewar_address, property.prewar_address),
                               cadastral_no       = COALESCE(EXCLUDED.cadastral_no, property.cadastral_no),
                               geom               = COALESCE(property.geom, EXCLUDED.geom)""",
                    (building_id, occupation_address, prewar_address, cadastral_no, lon, lat),
                )
            else:
                cur.execute(
                    """INSERT INTO property
                           (building_id, occupation_address, prewar_address, cadastral_no)
                       VALUES (%s, %s, %s, %s)
                       ON CONFLICT (building_id) DO UPDATE
                           SET occupation_address = EXCLUDED.occupation_address,
                               prewar_address     = COALESCE(EXCLUDED.prewar_address, property.prewar_address),
                               cadastral_no       = COALESCE(EXCLUDED.cadastral_no, property.cadastral_no)""",
                    (building_id, occupation_address, prewar_address, cadastral_no),
                )
            loaded += 1

    con.commit()
    cur.close()
    con.close()
    log.info("load_buildings: %d buildings (%d with geom)", loaded, with_geom)
    print(f"load_buildings: {loaded} buildings ({with_geom} with geom)")


def load_ownerless_decrees(jsonl: str = "data/parsed/ownerless_decrees.jsonl") -> None:
    """Load ownerless_decrees.jsonl rows (row_confidence >= 0.8, claim-grade
    per CLAUDE.md) as seizure_event(stage='ownerless_designation') rows, and
    upsert the signing official into `actor` (in scope for accountability).
    The address is parsed into (street, house) exactly as
    scripts/21_build_address_registry.py's _from_ownerless_decrees does, so
    the resulting building_id matches the property row created by
    load_buildings(). Idempotent via dedup_key."""
    path = Path(config.PROJECT_ROOT / jsonl)
    if not path.exists():
        raise SystemExit(f"{path} not found — run scripts/06_parse_ownerless_decrees.py first.")

    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()
    loaded = skipped_conf = skipped_addr = skipped_prop = skipped_kind = 0

    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            # Only designation decrees are 'ownerless_designation' events.
            # removal-kind rows («снятие с учёта») are the lifecycle-COMPLETION
            # act (post-court-transfer de-listing) and need their own stage +
            # loader; procedure-kind rows are machinery, not per-property acts.
            if d.get("decree_kind") != "designation":
                skipped_kind += 1
                continue
            if d.get("row_confidence", 0) < 0.8:
                skipped_conf += 1
                continue

            addr = strip_garbage_prefix(norm_commas(d.get("address_raw") or ""))
            parts = [p.strip() for p in addr.split(",")]
            street = parts[0] if parts else None
            house = None
            for p in parts[1:]:
                if re.match(r"д\.?\s*\d", p, re.I):
                    house = p
                    break
            building_id = address_to_building_key(street, house)
            if building_id is None:
                skipped_addr += 1
                continue

            cur.execute("SELECT id FROM property WHERE building_id = %s", (building_id,))
            row = cur.fetchone()
            if not row:
                log.warning("ownerless_decrees seq_no=%s: no property for building_id=%s "
                            "(run load_buildings() first?)", d.get("seq_no"), building_id)
                skipped_prop += 1
                continue
            property_id = row[0]

            source_doc_id = _upsert_source_doc_by_sha(cur, d.get("source_sha256"))
            actor_id = _upsert_actor(cur, d.get("signing_official"), "signing_official", None)

            dedup_key = f"ownerless_decrees:{d['source_sha256']}:{d['seq_no']}"
            detail = {
                "source": "ownerless_decrees",
                "decree_number": d.get("decree_number"),
                "decree_kind": d.get("decree_kind"),
                "rosreestr_order_ref": d.get("rosreestr_order_ref"),
                "rosreestr_order_date": d.get("rosreestr_order_date"),
                "rosreestr_reg_date": d.get("rosreestr_reg_date"),
                "cadastral_number": d.get("cadastral_number"),
                "property_type": d.get("property_type"),
                "area_sqm": d.get("area_sqm"),
                "address_raw": d.get("address_raw"),
            }
            cur.execute(
                """INSERT INTO seizure_event
                       (property_id, stage, event_date, source_doc_id, confidence, detail, dedup_key)
                   VALUES (%s, 'ownerless_designation'::seizure_stage, %s, %s, %s, %s, %s)
                   ON CONFLICT (dedup_key) DO UPDATE
                       SET event_date    = EXCLUDED.event_date,
                           source_doc_id = EXCLUDED.source_doc_id,
                           confidence    = EXCLUDED.confidence,
                           detail        = EXCLUDED.detail
                   RETURNING id""",
                (property_id, d.get("decree_date"), source_doc_id,
                 d.get("row_confidence"), json.dumps(detail, ensure_ascii=False), dedup_key),
            )
            event_id = cur.fetchone()[0]

            if actor_id:
                cur.execute(
                    """INSERT INTO event_actor (seizure_event_id, actor_id)
                       VALUES (%s, %s) ON CONFLICT DO NOTHING""",
                    (event_id, actor_id),
                )

            loaded += 1

    con.commit()
    cur.close()
    con.close()
    log.info("load_ownerless_decrees: %d events, skipped %d non-designation kind, "
             "%d low-confidence, %d unparseable address, %d no matching property",
             loaded, skipped_kind, skipped_conf, skipped_addr, skipped_prop)
    print(f"load_ownerless_decrees: {loaded} events "
          f"(skipped: {skipped_kind} non-designation kind, {skipped_conf} low-confidence, "
          f"{skipped_addr} unparseable address, {skipped_prop} no matching property)")


def load_ownerless_registry(jsonl: str = "data/parsed/ownerless_registry.jsonl") -> None:
    """Load ownerless_registry.jsonl rows (row_confidence >= 0.8) as
    seizure_event(stage='registry_inclusion') rows. Per the Dec-2025 ФКЗ-4
    pivot, inclusion in this registry IS the title-transfer act, so this also
    bumps property.rd4u_category to 'A3.6' (loss of access to property in
    occupied territory) when not already set by case-level evidence.
    Idempotent via dedup_key."""
    path = Path(config.PROJECT_ROOT / jsonl)
    if not path.exists():
        raise SystemExit(f"{path} not found — run scripts/26_parse_ownerless_registry.py first.")

    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()
    loaded = skipped_conf = skipped_addr = skipped_prop = 0

    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            if d.get("row_confidence", 0) < 0.8:
                skipped_conf += 1
                continue

            building_id = address_to_building_key(d.get("street_raw"), d.get("house_raw"))
            if building_id is None:
                skipped_addr += 1
                continue

            cur.execute("SELECT id FROM property WHERE building_id = %s", (building_id,))
            row = cur.fetchone()
            if not row:
                log.warning("ownerless_registry seq_no=%s: no property for building_id=%s "
                            "(run load_buildings() first?)", d.get("seq_no"), building_id)
                skipped_prop += 1
                continue
            property_id = row[0]

            apt_raw = d.get("apt_raw")
            unit_id = None
            if apt_raw:
                unit_id = _find_or_create_unit(cur, property_id, apt_raw.strip(), d.get("apt_kind"))

            source_doc_id = _upsert_source_doc_by_sha(cur, d.get("source_sha256"))

            dedup_key = f"ownerless_registry:{d['source_sha256']}:{d['seq_no']}"
            detail = {
                "source": "ownerless_registry",
                "address_raw": d.get("address_raw"),
                "settlement_raw": d.get("settlement_raw"),
                "apt_raw": d.get("apt_raw"),
                "apt_kind": d.get("apt_kind"),
                "recognition_marker": d.get("recognition_marker"),
                "district_key": d.get("district_key"),
            }
            cur.execute(
                """INSERT INTO seizure_event
                       (property_id, unit_id, stage, source_doc_id, confidence, detail, dedup_key)
                   VALUES (%s, %s, 'registry_inclusion'::seizure_stage, %s, %s, %s, %s)
                   ON CONFLICT (dedup_key) DO UPDATE
                       SET unit_id       = EXCLUDED.unit_id,
                           source_doc_id = EXCLUDED.source_doc_id,
                           confidence    = EXCLUDED.confidence,
                           detail        = EXCLUDED.detail""",
                (property_id, unit_id, source_doc_id, d.get("row_confidence"),
                 json.dumps(detail, ensure_ascii=False), dedup_key),
            )

            cur.execute(
                "UPDATE property SET rd4u_category = COALESCE(rd4u_category, 'A3.6') WHERE id = %s",
                (property_id,),
            )

            loaded += 1

    con.commit()
    cur.close()
    con.close()
    log.info("load_ownerless_registry: %d events, skipped %d low-confidence, "
             "%d unparseable address, %d no matching property",
             loaded, skipped_conf, skipped_addr, skipped_prop)
    print(f"load_ownerless_registry: {loaded} events "
          f"(skipped: {skipped_conf} low-confidence, {skipped_addr} unparseable address, "
          f"{skipped_prop} no matching property)")


def backfill_registry_units(apply: bool = False) -> None:
    """One-off backfill: promote apt_raw/apt_kind already sitting in
    seizure_event.detail (stage='registry_inclusion' rows loaded before the
    `unit` table existed) into structural unit rows + seizure_event.unit_id.

    Reuses _find_or_create_unit -- no duplicated SQL. Idempotent: a re-run
    after --apply finds 0 rows left to fix (the WHERE clause only selects
    unit_id IS NULL rows). Touches no other stage or table.
    Default is a dry-run report; pass apply=True to write changes."""
    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()

    cur.execute(
        """SELECT id, property_id, detail->>'apt_raw', detail->>'apt_kind'
               FROM seizure_event
               WHERE stage = 'registry_inclusion'::seizure_stage
                 AND unit_id IS NULL
                 AND detail->>'apt_raw' IS NOT NULL"""
    )
    rows = cur.fetchall()
    print(f"backfill_registry_units: {len(rows)} registry_inclusion events to backfill")

    if not apply:
        cur.close()
        con.close()
        print("Dry run only -- pass apply=True / --apply to write changes.")
        return

    fixed = 0
    for event_id, property_id, apt_raw, apt_kind in rows:
        unit_id = _find_or_create_unit(cur, property_id, apt_raw.strip(), apt_kind)
        cur.execute("UPDATE seizure_event SET unit_id = %s WHERE id = %s", (unit_id, event_id))
        fixed += 1

    con.commit()
    cur.close()
    con.close()
    log.info("backfill_registry_units: %d events backfilled", fixed)
    print(f"backfill_registry_units: {fixed} events backfilled")


# ── Gap 3: demolish -> rebuild address-laundering modality ────────────────────
# Old side (a war-damaged building placed on a demolition register and razed)
# and new side (a developer SPV builds on the cleared footprint under a new
# address) are DISTINCT property rows -- the address change is the point. The
# bridge between them is cadastral/decree provenance (corroboration), never a
# shared building_id. Officials and developer beneficiaries are in scope for
# accountability per CLAUDE.md (not minimized).

def _find_or_create_property(cur, building_id: str, occupation_address: str | None = None,
                             cadastral_no: str | None = None,
                             lonlat: tuple[float, float] | None = None) -> int:
    """Return property.id for building_id, creating a minimal row if absent.
    Idempotent via property_building_id_uidx. Does not overwrite an existing
    row's fields (load_buildings() is the authority for geom/address); only
    fills NULLs via COALESCE on create-conflict."""
    cur.execute("SELECT id FROM property WHERE building_id = %s", (building_id,))
    row = cur.fetchone()
    if row:
        return row[0]
    if lonlat is not None:
        cur.execute(
            """INSERT INTO property (building_id, occupation_address, cadastral_no, geom)
               VALUES (%s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
               ON CONFLICT (building_id) DO UPDATE
                   SET occupation_address = COALESCE(property.occupation_address, EXCLUDED.occupation_address)
               RETURNING id""",
            (building_id, occupation_address, cadastral_no, lonlat[0], lonlat[1]),
        )
    else:
        cur.execute(
            """INSERT INTO property (building_id, occupation_address, cadastral_no)
               VALUES (%s, %s, %s)
               ON CONFLICT (building_id) DO UPDATE
                   SET occupation_address = COALESCE(property.occupation_address, EXCLUDED.occupation_address)
               RETURNING id""",
            (building_id, occupation_address, cadastral_no),
        )
    return cur.fetchone()[0]


def _find_or_create_unit(cur, property_id: int, apt_no: str, apt_kind: str | None = None) -> int:
    """Return unit.id for (property_id, apt_no), creating a minimal row if
    absent. Idempotent via unit_property_apt_uidx. Mirrors
    _find_or_create_property's create-once pattern -- one row per distinct
    apartment under a building, never overwritten once created beyond
    filling a previously-NULL apt_kind."""
    cur.execute("SELECT id FROM unit WHERE property_id = %s AND apt_no = %s",
                (property_id, apt_no))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(
        """INSERT INTO unit (property_id, apt_no, apt_kind)
           VALUES (%s, %s, %s)
           ON CONFLICT (property_id, apt_no) DO UPDATE
               SET apt_kind = COALESCE(unit.apt_kind, EXCLUDED.apt_kind)
           RETURNING id""",
        (property_id, apt_no, apt_kind),
    )
    return cur.fetchone()[0]


def _upsert_beneficiary(cur, name: str | None, inn: str | None = None,
                        ogrn: str | None = None, ceo: str | None = None,
                        extra: str | None = None) -> int | None:
    """Upsert a developer/beneficiary SPV into `actor` (role='beneficiary').
    Identity is the INN where present (one actor per legal entity even across
    name-string variants -- 'СЗ РКС-Девелопмент' vs 'Специализированный
    застройщик «РКС-Девелопмент»'); falls back to the name string otherwise.
    INN/OGRN/CEO are recorded in notes (actor has no structured INN column)."""
    if not name or not name.strip():
        return None
    name = name.strip()
    if inn:
        cur.execute(
            "SELECT id FROM actor WHERE role = 'beneficiary' AND notes LIKE %s LIMIT 1",
            (f"%ИНН {inn}%",),
        )
        row = cur.fetchone()
        if row:
            return row[0]
    note_parts = []
    if inn:
        note_parts.append(f"ИНН {inn}")
    if ogrn:
        note_parts.append(f"ОГРН {ogrn}")
    if ceo:
        note_parts.append(f"руководитель: {ceo}")
    if extra:
        note_parts.append(extra)
    notes = " | ".join(note_parts) or None
    return _upsert_actor(cur, name, "beneficiary", None, notes=notes)


def load_demolition_register(jsonl: str = "data/parsed/minstroy_demolition_register.jsonl") -> None:
    """Load the MinStroy/ГКО demolition register (Mariupol rows) as
    seizure_event(stage='demolition') -- the old-side razing designation of
    the demolish->rebuild modality. Building keys reproduce
    scripts/21_build_address_registry.py's _from_minstroy extractor exactly, so
    events attach to the property rows load_buildings() created. Idempotent via
    dedup_key."""
    path = Path(config.PROJECT_ROOT / jsonl)
    if not path.exists():
        raise SystemExit(f"{path} not found — run scripts/15_parse_minstroy_demolition_register.py first.")

    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()
    loaded = skipped_city = skipped_addr = 0

    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            if (d.get("address_city") or "").strip().lower() != "мариуполь":
                skipped_city += 1
                continue
            building_id = address_to_building_key(d.get("address_street"), d.get("address_building"))
            if building_id is None:
                skipped_addr += 1
                continue

            occ = d.get("address_raw") or f"{d.get('address_street')}, {d.get('address_building')}"
            property_id = _find_or_create_property(cur, building_id, occupation_address=occ)
            source_doc_id = _upsert_source_doc_by_sha(cur, d.get("source_sha256"))

            dedup_key = (f"minstroy_demolition:{d.get('source_sha256')}:"
                         f"{building_id}:{d.get('order_number')}")
            detail = {
                "source": "minstroy_demolition_register",
                "order_reference_raw": d.get("order_reference_raw"),
                "order_authority": d.get("order_authority"),
                "order_number": d.get("order_number"),
                "order_date": d.get("order_date"),
                "district": d.get("district_normalized"),
                "building_type": d.get("building_type"),
                "address_raw": d.get("address_raw"),
            }
            cur.execute(
                """INSERT INTO seizure_event
                       (property_id, stage, event_date, source_doc_id, confidence, detail, dedup_key)
                   VALUES (%s, 'demolition'::seizure_stage,
                           NULLIF(%s,'')::date, %s, %s, %s, %s)
                   ON CONFLICT (dedup_key) DO UPDATE
                       SET event_date = EXCLUDED.event_date,
                           detail     = EXCLUDED.detail,
                           source_doc_id = EXCLUDED.source_doc_id""",
                (property_id, d.get("order_date"), source_doc_id, 0.9,
                 json.dumps(detail, ensure_ascii=False), dedup_key),
            )
            loaded += 1

    con.commit()
    cur.close()
    con.close()
    log.info("load_demolition_register: %d demolition events (skipped %d non-Mariupol, "
             "%d unparseable address)", loaded, skipped_city, skipped_addr)
    print(f"load_demolition_register: {loaded} demolition events "
          f"(skipped: {skipped_city} non-Mariupol, {skipped_addr} unparseable address)")


def load_demolition_decrees(jsonl: str = "data/parsed/demolition_decrees.jsonl") -> None:
    """Load Mariupol-admin demolition decrees ('о сносе' / 'подлежащими сносу')
    as seizure_event(stage='demolition') + their signing officials as actors.
    Prose-extracted (one building per decree row). Idempotent via dedup_key."""
    path = Path(config.PROJECT_ROOT / jsonl)
    if not path.exists():
        raise SystemExit(f"{path} not found — run scripts/09_parse_demolition_decrees.py first.")

    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()
    loaded = skipped_addr = 0

    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            addr = norm_commas(d.get("address_raw") or "")
            parts = [p.strip() for p in addr.split(",")]
            street = parts[0] if parts else None
            house = parts[1] if len(parts) > 1 else None
            building_id = address_to_building_key(street, house)
            if building_id is None:
                skipped_addr += 1
                continue

            property_id = _find_or_create_property(cur, building_id, occupation_address=addr)
            source_doc_id = _upsert_source_doc_by_sha(cur, d.get("source_sha256"))

            dedup_key = f"demolition_decree:{d.get('source_sha256')}:{building_id}"
            detail = {
                "source": "demolition_decrees",
                "decree_number": d.get("decree_number"),
                "decree_kind": d.get("decree_kind"),
                "amends_decree": d.get("amends_decree"),
                "legal_basis": d.get("legal_basis"),
                "address_raw": d.get("address_raw"),
            }
            cur.execute(
                """INSERT INTO seizure_event
                       (property_id, stage, event_date, source_doc_id, confidence, detail, dedup_key)
                   VALUES (%s, 'demolition'::seizure_stage,
                           NULLIF(%s,'')::date, %s, %s, %s, %s)
                   ON CONFLICT (dedup_key) DO UPDATE
                       SET event_date = EXCLUDED.event_date,
                           detail     = EXCLUDED.detail,
                           source_doc_id = EXCLUDED.source_doc_id
                   RETURNING id""",
                (property_id, d.get("decree_date"), source_doc_id, 0.85,
                 json.dumps(detail, ensure_ascii=False), dedup_key),
            )
            event_id = cur.fetchone()[0]

            # signing officials (in scope for accountability). The parser's
            # per-official `role` is unreliable -- it frequently captured an
            # org-name fragment ("городского округа Мариуполь...") split off
            # "Глава Администрации ... — Цыба Л.В.". Whitelist it; everything
            # else is a signatory on the demolition decree -> signing_official.
            officials = d.get("officials") or []
            if not officials and d.get("signing_official"):
                officials = [{"name": d["signing_official"], "role": "signing_official"}]
            for off in officials:
                raw_role = (off.get("role") or "").strip()
                role = raw_role if raw_role in _VALID_ACTOR_ROLES else "signing_official"
                actor_id = _upsert_actor(cur, off.get("name"), role, None)
                if actor_id:
                    cur.execute(
                        """INSERT INTO event_actor (seizure_event_id, actor_id)
                           VALUES (%s, %s) ON CONFLICT DO NOTHING""",
                        (event_id, actor_id),
                    )
            loaded += 1

    con.commit()
    cur.close()
    con.close()
    log.info("load_demolition_decrees: %d demolition events (skipped %d unparseable address)",
             loaded, skipped_addr)
    print(f"load_demolition_decrees: {loaded} demolition events "
          f"(skipped: {skipped_addr} unparseable address)")


def _eisghs_building_key(d: dict) -> str | None:
    """Reproduce scripts/21_build_address_registry.py's _from_eisghs keying
    EXACTLY so new-build events attach to the same property rows load_buildings()
    created: classify street, then house-number key, else (no house) the
    '<street_key>|@<lat>,<lon>' already-geocoded form, else None (bare
    'г. Мариуполь' rows that script 21 skips as no_street)."""
    addr = d.get("address") or ""
    parts = [p.strip() for p in norm_commas(addr).split(",")]
    parts = [p for p in parts if not re.match(r"^г\.?\s*мариуполь", p, re.I)]
    if not parts:
        return None
    street = parts[0]
    house = None
    for p in parts[1:]:
        m = re.search(r"(?:д\.?\s*|литера\s*)(\S+)", p, re.I)
        if m:
            house = m.group(0)
            break
    classified = classify_street(street)
    if classified is None:
        return None
    building_key, _ = compute_building_key(classified.street_key, house)
    if building_key:
        return building_key
    try:
        lat, lon = float(d["lat"]), float(d["lon"])
    except (KeyError, TypeError, ValueError):
        return None
    return f"{classified.street_key}|@{lat:.4f},{lon:.4f}"


def load_eisghs_newbuilds(jsonl: str = "data/parsed/eisghs_mariupol_objects.jsonl") -> None:
    """Load ЕИСЖС/наш.дом.рф new-builds (the rebuild endpoint) as property rows
    + seizure_event(stage='reallocation') carrying developer + sales data +
    the developer beneficiary actor (linked via event_actor). The reallocation
    event records disposal of appropriated land/footprint to the occupier's
    construction sector (Rome Statute art. 8(2)(b)(xvi)). Idempotent via
    dedup_key keyed on the stable eisghs_id."""
    path = Path(config.PROJECT_ROOT / jsonl)
    if not path.exists():
        raise SystemExit(f"{path} not found — run scripts/18_parse_eisghs_mariupol.py first.")

    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()
    loaded = skipped_nokey = 0

    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            building_id = _eisghs_building_key(d)
            if building_id is None:
                skipped_nokey += 1
                continue

            try:
                lonlat = (float(d["lon"]), float(d["lat"]))
            except (KeyError, TypeError, ValueError):
                lonlat = None
            cad = (d.get("rpd_cadastral_match") or {}).get("cadastral_numbers") or []
            cadastral_no = ", ".join(cad) if cad else None
            property_id = _find_or_create_property(
                cur, building_id, occupation_address=d.get("address"),
                cadastral_no=cadastral_no, lonlat=lonlat)

            source_doc_id = _upsert_source_doc_by_sha(cur, d.get("source_sha256"))
            lo = d.get("land_order_match") or {}
            beneficiary_id = _upsert_beneficiary(
                cur, d.get("dev_name_short") or d.get("dev_name_full"),
                inn=d.get("dev_inn"), ogrn=d.get("dev_ogrn"), ceo=d.get("dev_ceo"),
                extra=(f"ЕИСЖС dev_id {d.get('dev_id')}" if d.get("dev_id") else None))

            event_date = d.get("commissioned_dt") or d.get("obj_publ_dt")
            dedup_key = f"eisghs_reallocation:{d.get('eisghs_id')}"
            detail = {
                "source": "eisghs_mariupol_objects",
                "eisghs_id": d.get("eisghs_id"),
                "project_name": d.get("nameObj"),
                "developer": d.get("dev_name_short"),
                "developer_inn": d.get("dev_inn"),
                "obj_status": d.get("obj_status_desc"),
                "commissioned_dt": d.get("commissioned_dt"),
                "flat_cnt": d.get("flat_cnt"),
                "floor_cnt": d.get("floor_cnt"),
                "area_sqm_living": d.get("area_sqm_living"),
                "sold_out_perc": d.get("sold_out_perc"),
                "land_order_decree": lo.get("decree_number"),
                "land_order_date": lo.get("decree_date"),
                "land_order_beneficiary": lo.get("beneficiary_name"),
                "land_order_cadastrals": lo.get("cadastral_numbers"),
                "land_order_project_name": lo.get("project_name"),
                "rpd_num": d.get("rpd_num"),
                "rpd_project_title": (d.get("rpd_cadastral_match") or {}).get("project_title_in_pdf"),
                "legal_grade": d.get("legal_grade"),
            }
            confidence = 0.9 if d.get("legal_grade") else 0.7
            cur.execute(
                """INSERT INTO seizure_event
                       (property_id, stage, event_date, source_doc_id, confidence, detail, dedup_key)
                   VALUES (%s, 'reallocation'::seizure_stage,
                           NULLIF(%s,'')::date, %s, %s, %s, %s)
                   ON CONFLICT (dedup_key) DO UPDATE
                       SET event_date = EXCLUDED.event_date,
                           detail     = EXCLUDED.detail,
                           confidence = EXCLUDED.confidence,
                           source_doc_id = EXCLUDED.source_doc_id
                   RETURNING id""",
                (property_id, event_date, source_doc_id, confidence,
                 json.dumps(detail, ensure_ascii=False), dedup_key),
            )
            event_id = cur.fetchone()[0]
            if beneficiary_id:
                cur.execute(
                    """INSERT INTO event_actor (seizure_event_id, actor_id)
                       VALUES (%s, %s) ON CONFLICT DO NOTHING""",
                    (event_id, beneficiary_id),
                )
            loaded += 1

    con.commit()
    cur.close()
    con.close()
    log.info("load_eisghs_newbuilds: %d reallocation events (skipped %d no building key)",
             loaded, skipped_nokey)
    print(f"load_eisghs_newbuilds: {loaded} reallocation events "
          f"(skipped: {skipped_nokey} no building key)")


def load_land_order_beneficiaries(jsonl: str = "data/parsed/dnr_land_orders.jsonl") -> None:
    """Load DNR head's land-allocation orders as the beneficiary roster:
    each SPV that received Mariupol land without auction becomes an
    actor(role='beneficiary') with INN/OGRN/cadastrals/decree in notes. This
    is the standalone accountability roster (no property anchor required) --
    most orders describe parcels by territorial prose, not a single building,
    and many have no commissioned new-build yet. Idempotent via INN identity."""
    path = Path(config.PROJECT_ROOT / jsonl)
    if not path.exists():
        raise SystemExit(f"{path} not found — run scripts/11_parse_dnr_land_orders.py first.")

    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()
    loaded = skipped = 0
    seen_inns: set[str] = set()

    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            name = d.get("beneficiary_name")
            if not name or len(name) > 250:
                # missing, or whole-decree prose leaked into the field (decree
                # 77-6 ДОМ.РФ program text, 331 Автодор text) -- not real grants.
                skipped += 1
                continue
            decree = d.get("decree_number")
            cads = d.get("cadastral_numbers") or []
            extra_bits = []
            if decree:
                extra_bits.append(f"распоряжение №{decree} от {d.get('decree_date')}")
            if cads:
                extra_bits.append(f"кадастр: {', '.join(cads)}")
            beneficiary_id = _upsert_beneficiary(
                cur, name, inn=d.get("beneficiary_inn"), ogrn=d.get("beneficiary_ogrn"),
                extra="; ".join(extra_bits) or None)
            if beneficiary_id:
                loaded += 1
                if d.get("beneficiary_inn"):
                    seen_inns.add(d["beneficiary_inn"])

    con.commit()
    cur.close()
    con.close()
    log.info("load_land_order_beneficiaries: %d order rows -> beneficiaries "
             "(%d distinct INNs), skipped %d no-beneficiary",
             loaded, len(seen_inns), skipped)
    print(f"load_land_order_beneficiaries: {loaded} order rows processed "
          f"({len(seen_inns)} distinct INNs), skipped {skipped} no-beneficiary")


def load_housing_distribution(jsonl: str = "data/parsed/housing_distribution.jsonl") -> None:
    """Load the occupation housing-distribution list as BUILDING-LEVEL
    displacement aggregates into corroboration -- one row per building with a
    household count, district, and source.

    PRIVACY (CLAUDE.md hard rule): this loader deliberately ingests ONLY the
    aggregate count per building. The per-household hex IDs and exact apartment
    numbers in housing_distribution.jsonl's `claimant` objects are sensitive
    personal data about living displaced persons and are NEVER written to the
    DB here (they stay in the gitignored parsed file pending a secured,
    encrypted owner-identity layer). A count of displaced households per
    building is non-identifying and is direct A3.6 (loss-of-access) evidence.
    Idempotent via dedup_key."""
    path = Path(config.PROJECT_ROOT / jsonl)
    if not path.exists():
        raise SystemExit(f"{path} not found — run scripts/29_parse_housing_queue.py first.")

    # Aggregate per building (count households; never retain per-person detail).
    agg: dict[str, dict] = {}
    source_sha = None
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            source_sha = d.get("source_sha256") or source_sha
            bk = d.get("building_key")
            if not bk:
                continue
            a = agg.setdefault(bk, {
                "count": 0,
                "street_raw": d.get("street_raw"),
                "house_raw": d.get("house_raw"),
                "district_key": d.get("district_key"),
            })
            a["count"] += 1

    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()
    source_doc_id = _upsert_source_doc_by_sha(cur, source_sha)
    loaded = 0
    for bk, a in agg.items():
        property_id = _find_or_create_property(
            cur, bk,
            occupation_address=(f"{a['street_raw']}, {a['house_raw']}"
                                if a.get("house_raw") else a.get("street_raw")))
        dedup_key = f"housing_distribution:{source_sha}:{bk}"
        reference = (f"{a['count']} household(s) on occupation housing-distribution "
                     f"list (lost-access claims); district={a.get('district_key')}")
        detail = {
            "source": "housing_distribution_list",
            "households_displaced": a["count"],
            "district_key": a.get("district_key"),
            "source_doc_id": source_doc_id,
        }
        cur.execute(
            """INSERT INTO corroboration (property_id, kind, reference, detail, dedup_key, captured_at)
               VALUES (%s, 'displacement_claim', %s, %s, %s, now())
               ON CONFLICT (dedup_key) DO UPDATE
                   SET reference = EXCLUDED.reference,
                       detail    = EXCLUDED.detail,
                       captured_at = now()""",
            (property_id, reference, json.dumps(detail, ensure_ascii=False), dedup_key),
        )
        loaded += 1

    con.commit()
    cur.close()
    con.close()
    total = sum(a["count"] for a in agg.values())
    log.info("load_housing_distribution: %d buildings (%d households aggregated), "
             "no per-person PII loaded", loaded, total)
    print(f"load_housing_distribution: {loaded} buildings, {total} households aggregated "
          f"(no PII loaded)")


def load_damage_assessment(jsonl: str = "data/parsed/damage_assessment.jsonl") -> None:
    """Load the Russian federal damage/reconstruction tracker (1,941 Mariupol
    buildings) as corroboration(kind='mirror_source') rows -- one per building,
    matched to the property spine by building_key.

    This is an INDEPENDENT occupation/federal source: an official Russian
    reconstruction-priority list naming each building's destruction %,
    construction phase, and the contractor assigned to it. It corroborates,
    from a documentary angle distinct from the court/ownerless/registry/
    demolition tracks, that the building was war-damaged and is being acted on
    by the occupation administration. ~99.7% of keyable rows already exist as
    property rows (their addresses were folded into the address_registry
    baseline by script 21), so this mostly ENRICHES existing properties with a
    damage-attestation marker rather than creating new rows; the handful that
    don't match are created via _find_or_create_property.

    destruction_pct here is the strongest single signal we have for RD4U damage
    categories A3.1/A3.2/A3.3 (vs A3.6 loss-of-access) -- captured in detail for
    a downstream categorization pass, but NOT used to mutate rd4u_category here
    (that stays a deliberate, separately-reviewed step). contractor /
    responsible_executor are accountability-relevant beneficiaries captured in
    detail (actor enrichment is a possible follow-up). Idempotent via dedup_key.
    """
    path = Path(config.PROJECT_ROOT / jsonl)
    if not path.exists():
        raise SystemExit(f"{path} not found — run scripts/07_parse_damage_assessment.py first.")

    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()
    loaded = skipped_street = skipped_house = 0
    created = matched = 0

    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)

            street_raw = " ".join(
                x for x in (d.get("street_type"), d.get("street_name")) if x)
            classified = classify_street(street_raw)
            if classified is None:
                # microdistrict-only / unclassifiable street -- rather miss than
                # collide (CLAUDE.md). Logged in the aggregate count.
                skipped_street += 1
                continue
            building_id, _ = compute_building_key(
                classified.street_key, d.get("building_no"))
            if building_id is None:
                skipped_house += 1
                continue

            cur.execute("SELECT 1 FROM property WHERE building_id = %s", (building_id,))
            pre_exists = cur.fetchone() is not None
            property_id = _find_or_create_property(
                cur, building_id, occupation_address=d.get("address_raw"))
            if pre_exists:
                matched += 1
            else:
                created += 1

            source_doc_id = _upsert_source_doc_by_sha(cur, d.get("source_sha256"))
            dedup_key = f"damage_assessment:{d['source_sha256']}:{d['seq_no']}"
            detail = {
                "source": "damage_assessment",
                "destruction_pct": d.get("destruction_pct"),
                "priority_phase": d.get("priority_phase"),
                "property_type": d.get("property_type"),
                "building_class": d.get("building_class"),
                "floors": d.get("floors"),
                "entrances": d.get("entrances"),
                "apartments": d.get("apartments"),
                "contractor": d.get("contractor"),
                "responsible_executor": d.get("responsible_executor"),
                "district_key": d.get("district_key"),
                "microdistrict": d.get("microdistrict"),
                "address_raw": d.get("address_raw"),
                "source_doc_id": source_doc_id,
            }
            pct = d.get("destruction_pct")
            pct_txt = f"{pct:g}% destruction" if pct is not None else "destruction n/a"
            reference = (
                f"Russian federal damage/reconstruction tracker: {pct_txt}, "
                f"phase {d.get('priority_phase') or '?'}, "
                f"contractor {d.get('contractor') or 'n/a'}")
            cur.execute(
                """INSERT INTO corroboration
                       (property_id, kind, reference, detail, dedup_key, captured_at)
                   VALUES (%s, 'mirror_source', %s, %s, %s, now())
                   ON CONFLICT (dedup_key) DO UPDATE
                       SET reference   = EXCLUDED.reference,
                           detail      = EXCLUDED.detail,
                           captured_at = now()""",
                (property_id, reference, json.dumps(detail, ensure_ascii=False), dedup_key),
            )
            loaded += 1

    con.commit()
    cur.close()
    con.close()
    log.info("load_damage_assessment: %d corroboration rows (%d matched existing "
             "property, %d created), skipped %d no-street-class, %d no-house",
             loaded, matched, created, skipped_street, skipped_house)
    print(f"load_damage_assessment: {loaded} corroboration rows "
          f"({matched} matched existing property, {created} created); "
          f"skipped {skipped_street} no-street-class, {skipped_house} no-house")


# Tables carrying a property_id FK that must be re-pointed when a duplicate
# property row is merged into its survivor (db/schema.sql lines 38, 68, 88,
# 137, 151). None of these have a UNIQUE constraint that includes property_id,
# so re-pointing rows from the loser to a survivor that already has rows of
# its own cannot collide.
_PROPERTY_FK_TABLES = ("owner", "seizure_event", "court_case", "financial", "corroboration")


def merge_duplicate_properties(
    apply: bool = False,
    candidates_csv: str = "data/reports/corroboration_candidates.csv",
) -> None:
    """Re-derive building_id for every property from occupation_address using
    the now-fixed classify_street/address_to_building_key (2026-06-11
    normalization fixes -- see normalize/address.py and normalize/toponym.py),
    and reconcile rows whose recomputed building_id changes:

      - no other property already has the new building_id -> rename in place.
      - another property already has it (or two+ rows now converge on a
        brand-new key) -> merge the extra row(s) into a survivor: re-point
        every _PROPERTY_FK_TABLES.property_id reference, combine scalar
        fields (COALESCE for prewar_address/geom/rd4u_category; concatenate
        cadastral_no/notes if both sides differ), then delete the loser row.

    `candidates_csv` (scripts/33_corroboration_report.py's near-miss output)
    is used purely as a safety cross-check: any merge group whose members
    weren't ALL flagged there as a near-miss pair is an UNREVIEWED merge the
    address.py fixes produced as a side effect, not one of the 98 candidates
    individually reviewed for this migration. Per CLAUDE.md ("rather miss a
    match than collide two different addresses"), unreviewed groups are
    always reported but only merged in apply mode if `candidates_csv` is
    missing entirely (nothing to cross-check against).

    Idempotent: after applying, every remaining row's stored building_id
    equals its recomputed building_id, so a re-run finds 0 renames/merges.
    Default is a dry-run report; pass apply=True to write changes.
    """
    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()

    cur.execute(
        """SELECT id, building_id, occupation_address FROM property
               WHERE building_id IS NOT NULL AND occupation_address IS NOT NULL"""
    )
    rows = cur.fetchall()

    cur.execute("SELECT property_id, count(*) FROM seizure_event GROUP BY property_id")
    event_counts = dict(cur.fetchall())
    cur.execute("SELECT property_id, count(*) FROM corroboration GROUP BY property_id")
    corrob_counts = dict(cur.fetchall())

    # Building_ids whose merges are pre-approved through alias documentation in
    # normalize/address.py rather than through the near-miss candidates CSV.
    # Each entry is a (loser_old_bid, survivor_old_bid) pair confirmed safe.
    # К.Либкнехта 94/100/102/110/110а: abbreviation alias "к.либкнехта" →
    # "карла либкнехта" is documented in address.py. The 5 collisions arise
    # because some buildings were loaded under both forms before the alias was
    # added. Geom-confirmed (same coords) and cross-checked 2026-06-16.
    _ALIAS_REVIEWED: frozenset[str] = frozenset({
        # К.Либкнехта abbreviation → Карла Либкнехта (documented in address.py,
        # geom-confirmed, 2026-06-16)
        "STREET:к.либкнехта|94",   "STREET:карла либкнехта|94",
        "STREET:к.либкнехта|100",  "STREET:карла либкнехта|100",
        "STREET:к.либкнехта|102",  "STREET:карла либкнехта|102",
        "STREET:к.либкнехта|110",  "STREET:карла либкнехта|110",
        "STREET:к.либкнехта|110а", "STREET:карла либкнехта|110а",
        # Format-variant pairs: postal-code prefix, comma-position, "дом №" suffix,
        # microdistrict/settlement name variants. All losers have 0 events + 0 corrob.
        # Reviewed 2026-06-16.
        "UNKNOWN:87504, г. мариуполь, ул. бодрова|2",
        "UNKNOWN:87504|г. мариуполь, ул. бодрова, 2",
        "BOULEVARD:хмельницкого, дом №|22",
        "BOULEVARD:богдана хмельницкого|22",
        "UNKNOWN:поселок каменск, улица каменская|146",
        "UNKNOWN:поселок каменск|улица каменская, 146",
        "BOULEVARD:хмельницкого,64|16",
        "BOULEVARD:богдана хмельницкого|64, 16",
        "STREET:орджоникидзе,12|52",
        "STREET:орджоникидзе|12, 52",
        "STREET:панфилова,12|76",
        "STREET:панфилова|12, 76",
        "UNKNOWN:азовский жилмассив,5|9",
        "MICRODISTRICT:азовский|5, 9",
        "UNKNOWN:поселок старый крым, улица гранитная|55б",
        "UNKNOWN:поселок старый крым|улица гранитная, 55б",
        "UNKNOWN:87526, улица межевая|9",
        "UNKNOWN:87526|улица межевая, 9",
        "STREET:первая слободка, дом №|165",
        "STREET:первая слободка|165",
    })

    reviewed_bids: set[str] = set(_ALIAS_REVIEWED)
    csv_path = Path(config.PROJECT_ROOT / candidates_csv)
    if csv_path.exists():
        with csv_path.open(encoding="utf-8") as fh:
            for csv_row in csv.DictReader(fh):
                reviewed_bids.add(csv_row["building_id_a"])
                reviewed_bids.add(csv_row["building_id_b"])
    else:
        log.warning("%s not found -- skipping the reviewed-pair cross-check", csv_path)

    groups: dict[str, list[tuple[int, str]]] = {}
    unparseable: list[tuple[int, str, str]] = []
    for pid, old_bid, occ_addr in rows:
        new_bid = None
        if "," in occ_addr:
            # Split on the FIRST comma: occupation_address is built as
            # "<street>, <house>" (db.load.load_buildings et al.), and
            # <house> itself may contain commas for корпус/литера/apartment
            # notations ("Эллинская, 24, лит. К-1" -> street="Эллинская",
            # house="24, лит. К-1"). rsplit(",", 1) was tried and reverted:
            # it split those house-side commas into the street, corrupting
            # street_key with an embedded house number.
            street, house = occ_addr.split(",", 1)
            # If the "house" part starts with a street-type keyword the split
            # landed on a city/district prefix (e.g. "г. Мариуполь, ул Зелинского"
            # splits to street="г. Мариуполь", house="ул Зелинского"). These are
            # EISGHS objects with no house number; treat as UNPARSEABLE so their
            # coordinate-based building_ids are not overwritten by a shared key.
            if re.match(
                r"^\s*(ул\.?|улица|пр\.?|пр-кт\.?|проспект|б-р\.?|бульвар|"
                r"пер\.?|переулок|пл\.?|площадь|наб\.?|набережная)\b",
                house, re.I | re.UNICODE,
            ) and not re.search(r"\d", house):
                # Only skip when the house part is a bare street name with no
                # house number (e.g. "ул Зелинского"). If it has a digit it
                # may still be a parseable "ул. Артема, 73"-style address.
                new_bid = None
            else:
                new_bid = address_to_building_key(street.strip(), house.strip())
        if new_bid is None:
            unparseable.append((pid, old_bid, occ_addr))
            continue
        groups.setdefault(new_bid, []).append((pid, old_bid))

    no_op = 0
    rename_plans: list[tuple[int, str, str]] = []
    merge_plans: list[tuple[str, tuple[int, str], list[tuple[int, str]], bool]] = []

    for new_bid, members in groups.items():
        if len(members) == 1:
            pid, old_bid = members[0]
            if old_bid == new_bid:
                no_op += 1
            else:
                rename_plans.append((pid, old_bid, new_bid))
            continue

        unchanged = [m for m in members if m[1] == new_bid]
        if len(unchanged) > 1:
            log.error("merge_duplicate_properties: %d properties already share "
                      "building_id=%s (%s) -- this should be impossible under "
                      "property_building_id_uidx, skipping group",
                      len(unchanged), new_bid, [m[0] for m in unchanged])
            continue
        survivor = unchanged[0] if unchanged else min(members, key=lambda m: m[0])
        losers = [m for m in members if m[0] != survivor[0]]
        all_reviewed = all(m[1] in reviewed_bids for m in members)
        merge_plans.append((new_bid, survivor, losers, all_reviewed))

    print(f"merge_duplicate_properties: {len(rows)} properties with "
          f"building_id + occupation_address")
    print(f"  no-op (already correct):       {no_op}")
    print(f"  simple renames (no collision): {len(rename_plans)}")
    print(f"  merge groups:                  {len(merge_plans)}")
    if unparseable:
        print(f"  UNPARSEABLE (kept as-is, investigate!): {len(unparseable)}")
        for pid, old_bid, occ_addr in unparseable:
            print(f"    property {pid}: {old_bid!r} <- {occ_addr!r}")

    if rename_plans:
        print("\n-- renames --")
        for pid, old_bid, new_bid in rename_plans:
            print(f"  property {pid}: {old_bid} -> {new_bid}")

    unreviewed_groups = 0
    if merge_plans:
        print("\n-- merges --")
        for new_bid, survivor, losers, all_reviewed in merge_plans:
            tag = "" if all_reviewed else "  [UNREVIEWED -- not in corroboration_candidates.csv]"
            if not all_reviewed:
                unreviewed_groups += 1
            s_pid, s_old = survivor
            print(f"  -> {new_bid}{tag}")
            print(f"     survivor property {s_pid} (was {s_old}) "
                  f"events={event_counts.get(s_pid, 0)} corrob={corrob_counts.get(s_pid, 0)}")
            for l_pid, l_old in losers:
                print(f"     + loser property {l_pid} (was {l_old}) "
                      f"events={event_counts.get(l_pid, 0)} corrob={corrob_counts.get(l_pid, 0)}")

    if not apply:
        cur.close()
        con.close()
        print("\nDry run only -- pass apply=True / --apply to write changes.")
        return

    skip_unreviewed = bool(reviewed_bids) and unreviewed_groups > 0

    applied_renames = 0
    for pid, old_bid, new_bid in rename_plans:
        cur.execute("UPDATE property SET building_id = %s WHERE id = %s", (new_bid, pid))
        applied_renames += 1

    applied_merges = applied_groups = skipped_groups = 0
    for new_bid, survivor, losers, all_reviewed in merge_plans:
        if skip_unreviewed and not all_reviewed:
            skipped_groups += 1
            continue
        s_pid, _ = survivor
        for l_pid, _ in losers:
            for table in _PROPERTY_FK_TABLES:
                cur.execute(
                    f"UPDATE {table} SET property_id = %s WHERE property_id = %s",
                    (s_pid, l_pid),
                )
            # `unit` is NOT in _PROPERTY_FK_TABLES -- a blind property_id
            # re-point could violate unit_property_apt_uidx if the survivor
            # already has a unit with the same apt_no as one of the loser's.
            # Move non-colliding loser units directly; for genuine collisions,
            # re-point the affected seizure_event.unit_id to the survivor's
            # matching unit, then drop the now-orphaned loser unit. Collision
            # rate is expected near-zero (these merges are address-alias/typo
            # fixes between rows already pointing at the same building, not
            # large multi-unit buildings splitting -- see _ALIAS_REVIEWED).
            cur.execute(
                """UPDATE unit AS loser_u
                       SET property_id = %s
                   WHERE loser_u.property_id = %s
                     AND NOT EXISTS (
                         SELECT 1 FROM unit survivor_u
                         WHERE survivor_u.property_id = %s
                           AND survivor_u.apt_no = loser_u.apt_no
                     )""",
                (s_pid, l_pid, s_pid),
            )
            cur.execute(
                """UPDATE seizure_event se
                       SET unit_id = su.id
                   FROM unit lu
                   JOIN unit su ON su.property_id = %s AND su.apt_no = lu.apt_no
                   WHERE se.unit_id = lu.id AND lu.property_id = %s""",
                (s_pid, l_pid),
            )
            cur.execute("DELETE FROM unit WHERE property_id = %s", (l_pid,))
            cur.execute(
                """UPDATE property AS survivor
                       SET prewar_address = COALESCE(survivor.prewar_address, loser.prewar_address),
                           geom           = COALESCE(survivor.geom, loser.geom),
                           rd4u_category  = COALESCE(survivor.rd4u_category, loser.rd4u_category),
                           cadastral_no = CASE
                               WHEN survivor.cadastral_no IS NULL THEN loser.cadastral_no
                               WHEN loser.cadastral_no IS NULL
                                    OR survivor.cadastral_no = loser.cadastral_no
                                   THEN survivor.cadastral_no
                               ELSE survivor.cadastral_no || ', ' || loser.cadastral_no
                           END,
                           notes = CASE
                               WHEN survivor.notes IS NULL THEN loser.notes
                               WHEN loser.notes IS NULL OR survivor.notes = loser.notes
                                   THEN survivor.notes
                               ELSE survivor.notes || ' | ' || loser.notes
                           END
                       FROM property AS loser
                       WHERE survivor.id = %s AND loser.id = %s""",
                (s_pid, l_pid),
            )
            cur.execute("DELETE FROM property WHERE id = %s", (l_pid,))
            applied_merges += 1
        if survivor[1] != new_bid:
            cur.execute("UPDATE property SET building_id = %s WHERE id = %s", (new_bid, s_pid))
        applied_groups += 1

    con.commit()
    cur.close()
    con.close()
    log.info("merge_duplicate_properties: %d renames, %d merge groups applied "
             "(%d property rows merged away), %d unreviewed groups skipped",
             applied_renames, applied_groups, applied_merges, skipped_groups)
    print(f"\nApplied: {applied_renames} renames, {applied_groups} merge groups "
          f"({applied_merges} property rows merged away)"
          + (f", {skipped_groups} UNREVIEWED groups skipped" if skipped_groups else ""))


# RD4U claim categories (Council of Europe Register of Damage for Ukraine):
#   A3.1 - damage/destruction of RESIDENTIAL immovable property
#   A3.2 - damage/destruction of NON-RESIDENTIAL immovable property
#   A3.3 - loss of housing/residence
#   A3.6 - loss of access/control of property in occupied territory (the
#          seizure-pipeline category this whole project documents)
#
# A property can support more than one claim type at once (e.g. a demolished
# apartment building supports both A3.1 -- physical destruction -- and A3.6 --
# the demolition order is itself an act of loss-of-control). rd4u_category is
# therefore stored as a comma-separated, sorted list (e.g. "A3.1,A3.6"), not a
# single value.
#
# A3.6 ("the property cannot be used, transferred, or sold without relying on
# Russian authorities" -- rd4u.coe.int/en/a3.6-...) triggers on any
# seizure_event stage that is itself an administrative or judicial act
# putting the property under occupation control: ownerless designation,
# registry inclusion, the court-transfer lifecycle, or demolition (you cannot
# even access the cleared site without going through the occupation's
# reconstruction apparatus). Pre-petition lifecycle steps
# (utility_cutoff/notice/inspection) are not checked separately: they always
# co-occur with court_petition on the same case and add no new signal.
#
# `reallocation`/`resale` are deliberately EXCLUDED here: those seizure_event
# rows are typically attached to the NEW-BUILD property record (the rebuilt
# address), which has no displaced owner of its own to lose access -- they are
# Rome-accountability evidence (named beneficiary, population transfer) for
# the *original* property's claim, not an RD4U category for this record. See
# docs/legal_mechanisms_review.md endpoint table.
_A36_TRIGGER_STAGES = frozenset({
    "ownerless_designation", "registry_inclusion",
    "court_petition", "court_transfer", "appeal", "entered_force",
    "demolition",
})

# A3.1/A3.2 ("damage or destruction of residential/non-residential immovable
# property"): a `demolition` seizure_event is itself direct destruction
# evidence -- a building doesn't reach the demolition register without being
# war-damaged -- independent of whether it also has a mirror_source
# (federal damage-tracker) row. Defaults to A3.1 (residential): every
# demolition-register row matched to this project's spine so far is an МКЖД
# apartment building (mirror_source property_type is "жилое" for 100% of the
# 1,766 matched rows; the 172 "нежилое" tracker rows, mostly hospitals/clinics,
# did not match a street-addressable property and are out of this project's
# residential-housing scope).
_A31_DIRECT_STAGES = frozenset({"demolition"})


def categorize_rd4u(apply: bool = False) -> None:
    """Compute property.rd4u_category from the seizure_event/corroboration
    evidence already loaded, and write it as a comma-separated set of A3.x
    codes (see _A36_TRIGGER_STAGES comment above for the rules).

    A3.1/A3.2 come from `mirror_source` corroboration (the Russian federal
    damage/reconstruction tracker, loaded by load_damage_assessment): its
    `property_type` field ("жилое"/"нежилое") splits residential vs
    non-residential. A property with a mirror_source row but no captured
    property_type defaults to A3.1 (residential) -- 91% of the tracker's rows
    are "жилое" and this project's spine is apartment buildings.

    A3.3 comes from `displacement_claim` corroboration (occupation
    housing-distribution lists, loaded by load_housing_distribution):
    households displaced from this building are documented as having lost
    their residence there.

    Properties with no qualifying evidence at all keep rd4u_category = NULL.

    Writes a per-property audit CSV to data/reports/rd4u_categorization.csv
    (every property that gets a non-NULL category, old vs new value + the
    evidence basis). Idempotent: a re-run after --apply finds 0 changes.
    Default is a dry-run report; pass apply=True to write changes.
    """
    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()

    cur.execute("SELECT id, occupation_address, prewar_address, building_id, "
                 "rd4u_category FROM property")
    props = {}
    for pid, occ, pre, bid, cur_cat in cur.fetchall():
        props[pid] = {
            "occupation_address": occ, "prewar_address": pre, "building_id": bid,
            "current": cur_cat, "stages": set(), "ptypes": set(),
            "has_displacement": False,
        }

    cur.execute("SELECT property_id, stage FROM seizure_event")
    for pid, stage in cur.fetchall():
        p = props.get(pid)
        if p is not None:
            p["stages"].add(stage)

    cur.execute("SELECT property_id, kind, detail FROM corroboration")
    for pid, kind, detail in cur.fetchall():
        p = props.get(pid)
        if p is None:
            continue
        if kind == "mirror_source":
            p["ptypes"].add((detail or {}).get("property_type"))
        elif kind == "displacement_claim":
            p["has_displacement"] = True

    rows = []          # audit CSV rows (every property with a non-NULL new category)
    changes = []        # (property_id, new_value) for --apply
    counts_old = Counter()
    counts_new = Counter()
    for pid, p in props.items():
        cats = set()
        if (p["stages"] & _A36_TRIGGER_STAGES) or p["has_displacement"]:
            cats.add("A3.6")
        if p["stages"] & _A31_DIRECT_STAGES:
            cats.add("A3.1")
        if p["ptypes"]:
            if any(pt != "нежилое" for pt in p["ptypes"]):
                cats.add("A3.1")
            if "нежилое" in p["ptypes"]:
                cats.add("A3.2")
        if p["has_displacement"]:
            cats.add("A3.3")

        new_val = ",".join(sorted(cats)) if cats else None
        counts_old[p["current"]] += 1
        counts_new[new_val] += 1
        if new_val != p["current"]:
            changes.append((pid, new_val))
        if new_val is not None:
            rows.append({
                "property_id": pid,
                "building_id": p["building_id"],
                "occupation_address": p["occupation_address"],
                "prewar_address": p["prewar_address"],
                "current_rd4u_category": p["current"],
                "new_rd4u_category": new_val,
                "evidence_stages": "+".join(sorted(p["stages"] & _A36_TRIGGER_STAGES)),
                "property_types": "+".join(sorted(t for t in p["ptypes"] if t)) or "",
                "displacement_claim": "yes" if p["has_displacement"] else "",
            })

    outdir = config.PROJECT_ROOT / "data" / "reports"
    outdir.mkdir(parents=True, exist_ok=True)
    out_csv = outdir / "rd4u_categorization.csv"
    rows.sort(key=lambda r: r["property_id"])
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "property_id", "building_id", "occupation_address", "prewar_address",
            "current_rd4u_category", "new_rd4u_category", "evidence_stages",
            "property_types", "displacement_claim"])
        w.writeheader()
        w.writerows(rows)

    log.info("categorize_rd4u: %d properties, %d category changes "
             "(%d -> non-NULL category)", len(props), len(changes), len(rows))
    print(f"categorize_rd4u: {len(props)} properties total, "
          f"{len(rows)} get a non-NULL rd4u_category, "
          f"{len(changes)} changed vs current value")
    print("\nNew category distribution:")
    for cat, n in sorted(counts_new.items(), key=lambda kv: (kv[0] or "", -kv[1])):
        print(f"  {cat or '(none)':<14} {n}")
    print(f"\nAudit CSV: {out_csv}")

    if apply:
        for pid, new_val in changes:
            cur.execute("UPDATE property SET rd4u_category = %s WHERE id = %s",
                         (new_val, pid))
        con.commit()
        print(f"\nApplied: {len(changes)} property rows updated.")
    else:
        print(f"\nDry run -- {len(changes)} rows would be updated. Pass --apply to write.")

    cur.close()
    con.close()
