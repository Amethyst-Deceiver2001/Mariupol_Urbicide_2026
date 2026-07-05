#!/usr/bin/env python3
"""Load the FULL reconciled land-grant set (data/parsed/dnr_land_orders.jsonl
after scripts/252) onto the property spine as seizure_event(stage=
'reallocation') -- the same stage load_eisghs_newbuilds() uses for disposal of
appropriated land/footprint to the occupier's construction sector (Rome Statute
art. 8(2)(b)(xvi)).

Supersedes scripts/251 (which loaded only the denis-pushilin.ru subset). This
loads every land-grant row -- the rasp-archive population AND the earlier
нпа.днронлайн/glavadnr batches that had beneficiary actors but were never on
the spine as events (the 2026-07-05 audit gap).

Idempotent, no double-loading of the events scripts/251 already created:
  - rows sourced from the rasp archive (source_portal='denis-pushilin.ru',
    always have number+date) reuse scripts/251's EXACT dedup_key
    'pushilin_land_grant_reallocation:<num>:<date>' -> the ~39 already-loaded
    events UPDATE in place; the newly-recovered archive grants INSERT.
  - carried-over non-archive rows (нпа/glavadnr, may be undated) key on
    'dnr_land_grant_reallocation:<source_sha256>' (sha is always present and
    unique per capture).

Property resolution is by building_id, so a grant for a building the ЕИСЖС
loader already created attaches to that SAME property row (no duplicate
property); the land-grant event and any ЕИСЖС reallocation event coexist as
independent source families -- that corroboration is intentional, not a dup.

Rows with no usable single street+house address are skipped (same policy as
scripts/251): multi-parcel/area-description decrees and OCR-blank addresses.

Run (after scripts/252 --apply):
    PYTHONPATH=src python scripts/253_load_all_land_grants_reallocation.py
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
    _find_or_create_property, _upsert_beneficiary, _upsert_source_doc_by_sha,
)

log = logging.getLogger("load_all_land_grants_reallocation")
JSONL_PATH = ROOT / "data" / "parsed" / "dnr_land_orders.jsonl"

_STREET_PREFIXES = ("улица", "проспект", "бульвар", "переулок")
_HOUSE_PREFIX_RE = re.compile(r"^(дом|земельный участок)\s*", re.I)


def split_addr(address_raw: str) -> tuple[str | None, str | None]:
    parts = [p.strip() for p in address_raw.split(",")]
    for i, p in enumerate(parts):
        if p.lower().startswith(_STREET_PREFIXES):
            house = None
            if i + 1 < len(parts):
                house = _HOUSE_PREFIX_RE.sub("", parts[i + 1]).strip()
            return p, house
    return None, None


UPSERT_EVENT_SQL = """
    INSERT INTO seizure_event
        (property_id, stage, event_date, source_doc_id, confidence, detail, dedup_key)
    VALUES (%s, 'reallocation'::seizure_stage, NULLIF(%s,'')::date, %s, %s, %s, %s)
    ON CONFLICT (dedup_key) DO UPDATE
        SET event_date=EXCLUDED.event_date, source_doc_id=EXCLUDED.source_doc_id,
            confidence=EXCLUDED.confidence, detail=EXCLUDED.detail
    RETURNING id
"""
INSERT_EVENT_ACTOR_SQL = """
    INSERT INTO event_actor (seizure_event_id, actor_id) VALUES (%s, %s) ON CONFLICT DO NOTHING
"""


def _dedup_key(r: dict) -> str:
    if r.get("source_portal") == "denis-pushilin.ru" and r.get("decree_number") and r.get("decree_date"):
        return f"pushilin_land_grant_reallocation:{r['decree_number']}:{r['decree_date']}"
    return f"dnr_land_grant_reallocation:{r['source_sha256']}"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    rows = [json.loads(l) for l in JSONL_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    log.info("%d land-grant rows in %s", len(rows), JSONL_PATH)

    pg = psycopg2.connect(config.DATABASE_URL)
    pg.autocommit = False
    cur = pg.cursor()

    n_loaded = n_new = n_existing = n_skip = 0
    for r in rows:
        addr = r.get("address_raw")
        street, house = split_addr(addr) if addr else (None, None)
        if not street or not house:
            n_skip += 1
            continue
        classified = classify_street(street)
        if classified is None:
            n_skip += 1
            continue
        building_id, _ = compute_building_key(classified.street_key, house)
        if building_id is None:
            n_skip += 1
            continue

        cur.execute("SELECT id FROM property WHERE building_id = %s", (building_id,))
        existed = cur.fetchone() is not None
        cad = r.get("cadastral_numbers") or []
        property_id = _find_or_create_property(
            cur, building_id, occupation_address=addr, cadastral_no=(cad[0] if cad else None))
        n_existing += 1 if existed else 0
        n_new += 0 if existed else 1

        source_doc_id = _upsert_source_doc_by_sha(cur, r.get("source_sha256"))
        confidence = 0.85 if not r.get("flags") else 0.7
        detail = {
            "source": "dnr_land_orders (reconciled, scripts/252)",
            "decree_number": r.get("decree_number"), "decree_date": r.get("decree_date"),
            "beneficiary_name": r.get("beneficiary_name"), "project_name": r.get("project_name"),
            "cadastral_numbers": cad, "area_sqm": r.get("area_sqm"),
            "source_portal": r.get("source_portal"), "flags": r.get("flags"), "address_raw": addr,
        }
        cur.execute(UPSERT_EVENT_SQL, (
            property_id, r.get("decree_date"), source_doc_id, confidence,
            json.dumps(detail, ensure_ascii=False), _dedup_key(r)))
        event_id = cur.fetchone()[0]
        if r.get("beneficiary_name"):
            bid = _upsert_beneficiary(cur, r["beneficiary_name"], inn=r.get("beneficiary_inn"))
            if bid:
                cur.execute(INSERT_EVENT_ACTOR_SQL, (event_id, bid))
        n_loaded += 1

    pg.commit()
    log.info("done: %d events (%d new properties, %d matched existing), %d skipped (no usable address)",
             n_loaded, n_new, n_existing, n_skip)
    print(f"load_all_land_grants_reallocation: {n_loaded} loaded "
          f"({n_new} new properties, {n_existing} matched existing), {n_skip} skipped")


if __name__ == "__main__":
    main()
