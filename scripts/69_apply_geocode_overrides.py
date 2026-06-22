#!/usr/bin/env python3
"""Force-apply data/parsed/manual_geocode_overrides.jsonl onto property.geom.

scripts/27_load_registry.py's load_buildings() only fills geom via
COALESCE(property.geom, EXCLUDED.geom) -- it never overwrites an existing
(possibly wrong) geom. Manual overrides are user-verified corrections to
*existing* geoms (often by tens of meters to several km off, or split
duplicate geoms shared by two distinct buildings), so they must win
unconditionally over whatever is currently stored.

Idempotent: re-running re-applies the same coordinates. Only touches
property rows whose building_id matches a building_key in
manual_geocode_overrides.jsonl with geocode_confidence >= 0.8.
"""
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import psycopg2  # noqa: E402

from mariupol_seizures import config  # noqa: E402

log = logging.getLogger("apply_geocode_overrides")

OVERRIDES_PATH = config.PROJECT_ROOT / "data" / "parsed" / "manual_geocode_overrides.jsonl"


def main() -> None:
    if not OVERRIDES_PATH.exists():
        raise SystemExit(f"{OVERRIDES_PATH} not found")

    overrides = []
    with OVERRIDES_PATH.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            if d.get("geocode_confidence", 0) >= 0.8:
                overrides.append(d)

    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()

    updated = 0
    missing = []
    for d in overrides:
        cur.execute(
            """UPDATE property
                   SET geom = ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                   WHERE building_id = %s""",
            (d["lon"], d["lat"], d["building_key"]),
        )
        if cur.rowcount:
            updated += cur.rowcount
        else:
            missing.append(d["building_key"])

    con.commit()
    cur.close()
    con.close()

    log.info("applied %d/%d overrides (%d building_key not found in property)",
             updated, len(overrides), len(missing))
    print(f"applied {updated}/{len(overrides)} overrides")
    for bk in missing:
        print(f"  NOT FOUND: {bk}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    main()
