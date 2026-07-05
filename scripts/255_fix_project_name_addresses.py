#!/usr/bin/env python3
"""Fix a real address-matching bug in scripts/253's reallocation load.

scripts/253's split_addr() finds the first comma-delimited segment that
STARTS WITH a street prefix (улица/проспект/etc.) -- correct for a normal
"ул. X, дом Y" address, but for the ~20 land-grant rows whose address_raw is
instead a "territory bounded by streets ..." superblock description, this
incidentally matches one of the BOUNDARY streets (e.g. "улица Казанцева" in
"...проспект Ленина, улица Казанцева, улица Апатова..."), fabricating a
bogus property keyed on a nonsense building_id ("STREET:казанцева|улица
апатова") that has nothing to do with the actual land grant.

Five such bogus properties were created. Two are fixable because the
decree's OWN `project_name` field (never read by scripts/253) names the
real, specific, house-numbered address:

  - decree 289            -> project_name gives "просп. Нахимова 82",
                             which is ALREADY the documented flagship
                             case-study property (id 5865) -- re-point.
  - decrees 390-394        -> project_name gives "просп. Строителей
                             88/80/78/76/74" (5 distinct buildings, wrongly
                             collapsed onto ONE bogus property) -- split
                             out into 5 correct properties.

The other three bogus properties (decree 448, decree 178/2025-05-26,
decrees 320+334) have no house-numbered address in project_name either
(named complex/microdistrict/"Литер N" only) and are left untouched --
building-level resolution isn't possible for them without a site plan.

Idempotent: re-running finds the events already re-pointed and does nothing.

    .venv/bin/python scripts/255_fix_project_name_addresses.py           # dry-run
    .venv/bin/python scripts/255_fix_project_name_addresses.py --apply
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import psycopg2  # noqa: E402

from mariupol_seizures import config  # noqa: E402
from mariupol_seizures.normalize.address import classify_street, compute_building_key  # noqa: E402
from mariupol_seizures.db.load import _find_or_create_property  # noqa: E402

log = logging.getLogger("fix_project_name_addresses")

# decree_number -> (street_raw, house) extracted by hand from project_name
# (see docstring; these are the only two fixable groups)
FIXES = {
    "289": ("проспект Нахимова", "82"),
    "390": ("проспект Строителей", "88"),
    "391": ("проспект Строителей", "80"),
    "392": ("проспект Строителей", "78"),
    "393": ("проспект Строителей", "76"),
    "394": ("проспект Строителей", "74"),
}

_HOUSE_RE = re.compile(r"^\d+[A-ZА-Яa-zа-я]?$")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")

    pg = psycopg2.connect(config.DATABASE_URL)
    pg.autocommit = False
    cur = pg.cursor()

    n_fixed = n_deleted_bogus = 0
    for decree_number, (street_raw, house) in FIXES.items():
        classified = classify_street(street_raw)
        if classified is None:
            log.warning("decree %s: could not classify street %r, skipping", decree_number, street_raw)
            continue
        building_id, _ = compute_building_key(classified.street_key, house)
        if building_id is None:
            log.warning("decree %s: could not compute building_id, skipping", decree_number)
            continue

        correct_property_id = _find_or_create_property(
            cur, building_id, occupation_address=f"{street_raw}, {house}")

        cur.execute(
            "SELECT id, property_id FROM seizure_event WHERE detail->>'decree_number' = %s "
            "AND stage = 'reallocation'",
            (decree_number,),
        )
        rows = cur.fetchall()
        for event_id, bogus_property_id in rows:
            if bogus_property_id == correct_property_id:
                log.info("decree %s: event %d already points at correct property %d, no-op",
                          decree_number, event_id, correct_property_id)
                continue
            log.info("decree %s: event %d  bogus property %d -> correct property %d (%s, %s)",
                      decree_number, event_id, bogus_property_id, correct_property_id, street_raw, house)
            if args.apply:
                cur.execute("UPDATE seizure_event SET property_id = %s WHERE id = %s",
                            (correct_property_id, event_id))
            n_fixed += 1

    # clean up any now-orphaned bogus properties (no remaining seizure_event/corroboration rows)
    cur.execute("""
        SELECT p.id, p.building_id FROM property p
        WHERE p.occupation_address ILIKE '%%ограничен%%'
          AND NOT EXISTS (SELECT 1 FROM seizure_event se WHERE se.property_id = p.id)
          AND NOT EXISTS (SELECT 1 FROM corroboration c WHERE c.property_id = p.id)
    """)
    for pid, bid in cur.fetchall():
        log.info("orphaned bogus property %d (%s) -- deleting", pid, bid)
        if args.apply:
            cur.execute("DELETE FROM property WHERE id = %s", (pid,))
        n_deleted_bogus += 1

    if args.apply:
        pg.commit()
        log.info("committed: %d events re-pointed, %d bogus properties deleted", n_fixed, n_deleted_bogus)
    else:
        pg.rollback()
        log.info("DRY RUN: %d events would be re-pointed, %d bogus properties would be deleted "
                  "-- re-run with --apply", n_fixed, n_deleted_bogus)

    print(f"fix_project_name_addresses: {n_fixed} events fixed, {n_deleted_bogus} bogus properties "
          f"{'deleted' if args.apply else 'would be deleted'}{'' if args.apply else ' (dry run)'}")


if __name__ == "__main__":
    main()
