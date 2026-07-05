#!/usr/bin/env python3
"""Load the 47 new denis-pushilin.ru land-grant decrees (scripts/250,
data/parsed/dnr_land_orders.jsonl, source_portal='denis-pushilin.ru') onto
the property spine as seizure_event(stage='reallocation') -- the SAME stage
load_eisghs_newbuilds() already uses for "disposal of appropriated land/
footprint to the occupier's construction sector" (Rome Statute art.
8(2)(b)(xvi)). No schema change needed: 'reallocation' already covers this
exact scenario (checked against db/schema.sql's seizure_stage enum and
load.py:1263 before writing this script).

Address-spine check (2026-07-05, exact street+house-number match via
classify_street/compute_building_key): 6 of 42 addressed decrees match an
EXISTING property row -- 3 of those (decrees 398/399/258 -> пр. Ленина
87А/89, пр. Лунина 25) already carry a recorded demolition event, i.e.
three MORE demolish-→rebuild address-laundering cases alongside
Нахимова 82 (see docs/demolition_rebuild_address_laundering.md). The
remaining 36 addressed decrees have no prior spine footprint -- these get a
NEW property row created, same as load_eisghs_newbuilds() does for
new-builds on land with no pre-existing building record. 5 decrees have no
extractable address at all (9, 115, 314, 341, plus 8/10/266 which are area
descriptions, not a single street+house) -- these are SKIPPED, not guessed.

Idempotent: dedup_key = 'pushilin_land_grant_reallocation:<decree_number>:<decree_date>'
(date included because decree numbers repeat across years on this portal --
see scripts/250's docstring). Beneficiary linked via the SAME
_upsert_beneficiary() helper load_land_order_beneficiaries() already uses,
so no duplicate actor rows are created for entities already loaded.

Run:
    PYTHONPATH=src python scripts/251_load_pushilin_land_grants_reallocation.py
"""
from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import psycopg2  # noqa: E402

from mariupol_seizures import config  # noqa: E402
from mariupol_seizures.normalize.address import classify_street, compute_building_key  # noqa: E402
from mariupol_seizures.db.load import (  # noqa: E402
    _find_or_create_property,
    _upsert_beneficiary,
    _upsert_source_doc_by_sha,
)

log = logging.getLogger("load_pushilin_land_grants_reallocation")

JSONL_PATH = ROOT / "data" / "parsed" / "dnr_land_orders.jsonl"

_STREET_PREFIXES = ("улица", "проспект", "бульвар", "переулок")
_HOUSE_PREFIX_RE = re.compile(r"^(дом|земельный участок)\s*", re.I)


def split_addr(address_raw: str) -> tuple[str | None, str | None]:
    """Best-effort street/house split of this portal's full-address strings
    ('Российская Федерация, ДНР, городской округ Мариуполь, город Мариуполь,
    [район,] <улица|проспект|бульвар> <name>, [дом|земельный участок] <house>').
    Returns (street, house); either may be None if the address doesn't fit
    this shape (multi-parcel or bare-area descriptions -- caller skips those)."""
    parts = [p.strip() for p in address_raw.split(",")]
    for i, p in enumerate(parts):
        if p.lower().startswith(_STREET_PREFIXES):
            street = p
            house = None
            if i + 1 < len(parts):
                house = _HOUSE_PREFIX_RE.sub("", parts[i + 1]).strip()
            return street, house
    return None, None


UPSERT_EVENT_SQL = """
    INSERT INTO seizure_event
        (property_id, stage, event_date, source_doc_id, confidence, detail, dedup_key)
    VALUES (%s, 'reallocation'::seizure_stage, NULLIF(%s,'')::date, %s, %s, %s, %s)
    ON CONFLICT (dedup_key) DO UPDATE
        SET event_date    = EXCLUDED.event_date,
            source_doc_id = EXCLUDED.source_doc_id,
            confidence    = EXCLUDED.confidence,
            detail        = EXCLUDED.detail
    RETURNING id
"""

INSERT_EVENT_ACTOR_SQL = """
    INSERT INTO event_actor (seizure_event_id, actor_id)
    VALUES (%s, %s)
    ON CONFLICT DO NOTHING
"""


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")

    rows = []
    with JSONL_PATH.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    new_rows = [r for r in rows if r.get("source_portal") == "denis-pushilin.ru"]
    log.info("%d new pushilin land-grant rows in %s", len(new_rows), JSONL_PATH)

    pg = psycopg2.connect(config.DATABASE_URL)
    pg.autocommit = False
    cur = pg.cursor()

    n_loaded = n_new_property = n_existing_property = n_skipped_no_addr = 0

    for r in new_rows:
        addr = r.get("address_raw")
        if not addr:
            n_skipped_no_addr += 1
            log.info("  SKIP decree %s -- no address in OCR text", r.get("decree_number"))
            continue

        street, house = split_addr(addr)
        if not street or not house:
            n_skipped_no_addr += 1
            log.info("  SKIP decree %s -- address doesn't fit single street+house shape: %s",
                     r.get("decree_number"), addr)
            continue

        classified = classify_street(street)
        if classified is None:
            n_skipped_no_addr += 1
            log.info("  SKIP decree %s -- unclassifiable street %r", r.get("decree_number"), street)
            continue
        building_id, _ = compute_building_key(classified.street_key, house)
        if building_id is None:
            n_skipped_no_addr += 1
            log.info("  SKIP decree %s -- unclassifiable house %r", r.get("decree_number"), house)
            continue

        cur.execute("SELECT id FROM property WHERE building_id = %s", (building_id,))
        existed = cur.fetchone() is not None

        cad = r.get("cadastral_numbers") or []
        property_id = _find_or_create_property(
            cur, building_id, occupation_address=addr,
            cadastral_no=(cad[0] if cad else None))

        if existed:
            n_existing_property += 1
        else:
            n_new_property += 1

        source_doc_id = _upsert_source_doc_by_sha(cur, r.get("source_sha256"))
        confidence = 0.85 if not r.get("flags") else 0.7
        dedup_key = f"pushilin_land_grant_reallocation:{r['decree_number']}:{r.get('decree_date')}"
        detail = {
            "source": "denis-pushilin.ru rasp folder",
            "decree_number": r.get("decree_number"),
            "decree_date": r.get("decree_date"),
            "beneficiary_name": r.get("beneficiary_name"),
            "project_name": r.get("project_name"),
            "cadastral_numbers": cad,
            "area_sqm": r.get("area_sqm"),
            "flags": r.get("flags"),
            "address_raw": addr,
        }
        cur.execute(UPSERT_EVENT_SQL, (
            property_id, r.get("decree_date"), source_doc_id, confidence,
            json.dumps(detail, ensure_ascii=False), dedup_key,
        ))
        event_id = cur.fetchone()[0]

        if r.get("beneficiary_name"):
            beneficiary_id = _upsert_beneficiary(
                cur, r["beneficiary_name"], inn=r.get("beneficiary_inn"))
            if beneficiary_id:
                cur.execute(INSERT_EVENT_ACTOR_SQL, (event_id, beneficiary_id))

        n_loaded += 1
        log.info("  decree %s -> property %d (%s), %s", r["decree_number"], property_id,
                 "existing" if existed else "NEW", addr)

    pg.commit()
    log.info("done: %d events loaded (%d new properties, %d matched existing), %d skipped (no usable address)",
              n_loaded, n_new_property, n_existing_property, n_skipped_no_addr)
    print(f"load_pushilin_land_grants_reallocation: {n_loaded} loaded "
          f"({n_new_property} new properties, {n_existing_property} matched existing), "
          f"{n_skipped_no_addr} skipped")


if __name__ == "__main__":
    main()
