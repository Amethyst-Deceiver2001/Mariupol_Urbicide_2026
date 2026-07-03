#!/usr/bin/env python3
"""One-off, narrowly-scoped merge: fold the stale UNKNOWN:*квартал*/UNKNOWN:
кв-л* property rows (left behind by the pre-fix load, before "квартал"/"кв-л"
were added to toponym._CLASS_MAP as MICRODISTRICT) into the correctly-
classified MICRODISTRICT: property rows that load_buildings() just created
for the same building.

Deliberately NOT using db.load.merge_duplicate_properties() here: that
function re-derives building_id for EVERY property and would also surface
~20 unrelated merge groups (a pre-existing "Карла Либкнехта" spelling typo,
"воинов-освободителей" hyphenation, etc.) that haven't been reviewed for
this change -- out of scope for the квартал fix. This script only touches
rows whose OLD building_id matches the квартал/кв-л pattern, reusing the
same safe merge mechanics (FK re-point across _PROPERTY_FK_TABLES, plus the
unit-collision-aware handling merge_duplicate_properties() uses, since 68
unit rows are attached to these properties and unit.property_id cascades on
delete).

Idempotent: a re-run after --apply finds 0 candidates (no property with a
квартал/кв-л-pattern building_id remains once merged).

Run:
    PYTHONPATH=src python scripts/237_merge_kvartal_properties.py           # dry run
    PYTHONPATH=src python scripts/237_merge_kvartal_properties.py --apply
"""
from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import psycopg2  # noqa: E402

from mariupol_seizures import config  # noqa: E402
from mariupol_seizures.db.load import _PROPERTY_FK_TABLES  # noqa: E402
from mariupol_seizures.normalize.address import address_to_building_key  # noqa: E402

log = logging.getLogger(__name__)

_STALE_RE = re.compile(r"^UNKNOWN:.*(квартал|кв-л)", re.I)


def main(apply: bool) -> None:
    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()

    cur.execute("SELECT id, building_id, occupation_address FROM property")
    stale = [(pid, bid, addr) for pid, bid, addr in cur.fetchall()
             if bid and _STALE_RE.match(bid)]

    print(f"Found {len(stale)} stale квартал/кв-л property rows.")
    if not stale:
        cur.close()
        con.close()
        return

    plans = []
    for pid, old_bid, occ_addr in stale:
        parts = [p.strip() for p in (occ_addr or "").split(",")]
        # occupation_address here is stored as "<street>, <house>" (see
        # load_buildings) -- last comma-separated part is the house.
        street = ", ".join(parts[:-1]) if len(parts) > 1 else (parts[0] if parts else None)
        house = parts[-1] if len(parts) > 1 else None
        new_bid = address_to_building_key(street, house)
        if new_bid is None or new_bid == old_bid:
            print(f"  SKIP property {pid}: could not recompute a different "
                  f"building_id from occupation_address={occ_addr!r} (old={old_bid!r})")
            continue
        cur.execute("SELECT id FROM property WHERE building_id = %s", (new_bid,))
        row = cur.fetchone()
        if not row:
            print(f"  SKIP property {pid}: recomputed {new_bid!r} but no "
                  f"matching property exists yet (run load_buildings() first)")
            continue
        survivor_pid = row[0]
        if survivor_pid == pid:
            continue
        plans.append((pid, old_bid, survivor_pid, new_bid))

    print(f"\n{len(plans)} merge(s) to apply:")
    for l_pid, old_bid, s_pid, new_bid in plans:
        print(f"  loser {l_pid} ({old_bid}) -> survivor {s_pid} ({new_bid})")

    if not apply:
        cur.close()
        con.close()
        print("\nDry run only -- pass --apply to write changes.")
        return

    for l_pid, old_bid, s_pid, new_bid in plans:
        for table in _PROPERTY_FK_TABLES:
            cur.execute(
                f"UPDATE {table} SET property_id = %s WHERE property_id = %s",
                (s_pid, l_pid),
            )
        # unit-collision-aware re-point (unit is NOT in _PROPERTY_FK_TABLES --
        # see merge_duplicate_properties() for the identical pattern/rationale).
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

    con.commit()
    cur.close()
    con.close()
    print(f"\nApplied: {len(plans)} property rows merged away.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main(apply="--apply" in sys.argv)
