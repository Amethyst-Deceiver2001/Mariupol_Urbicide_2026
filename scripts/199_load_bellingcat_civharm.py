#!/usr/bin/env python3
"""Load the Mariupol subset of the Bellingcat Civilian Harm timemap
(scripts/198) as corroboration(kind='bellingcat_civharm') rows on the
property spine.

Tier-3 corroboration layer (docs/tier3_corroboration_design.md) -- a THIRD
independent provenance family alongside UNOSAT satellite damage and the
occupation/court/registry record itself: Bellingcat's own open-source
verification, sourced to Telegram/social-media/video evidence, not
satellite imagery or any Russian/occupation record.

CAVEAT, by design: Bellingcat's timemap pins are city-wide approximate
geocodes for most entries, not building-precise. A "nearest property" join
without a tight radius would silently misattribute a citywide incident
("damage to buildings in Mariupol") to whichever spine property happens to
sit closest -- a false precision the source data doesn't support. This
loader:
  1. Filters to the 21 (at capture time) records whose location/description
     names Mariupol.
  2. Spatially joins to property.geom with a tight ST_DWithin radius
     (100m -- looser than UNOSAT's 25m because Bellingcat's geocoding is
     coarser, but still building-scale, not block-scale).
  3. Confidence is capped lower than UNOSAT's (max 0.6 at <=25m, 0.4 at
     <=100m) to reflect that lower precision -- this is corroborating
     CONTEXT (the building was war-damaged, per an independent OSINT source,
     around this date) not a building-identity confirmation.
  4. Records with no match inside 100m (mass graves, the airport, the
     filtration camp, several "Mariupol" without a precise pin) are logged
     and SKIPPED, not force-matched to a distant property -- see the
     module docstring caveat above. This is expected and correct, not a bug.

Idempotent: dedup_key = 'bellingcat_civharm:<incident_id>:<property_id>'.

Run:
    PYTHONPATH=src python scripts/199_load_bellingcat_civharm.py
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import psycopg2  # noqa: E402
import psycopg2.extras  # noqa: E402

from mariupol_seizures import config, forensics  # noqa: E402
from mariupol_seizures.db.load import _upsert_source_doc_by_sha  # noqa: E402

log = logging.getLogger("load_bellingcat_civharm")

SOURCE_TYPE = "bellingcat_civharm_timemap"

ALTER_STATEMENTS = [
    "ALTER TABLE corroboration ADD COLUMN IF NOT EXISTS source_doc_id BIGINT REFERENCES source_document(id)",
    "ALTER TABLE corroboration ADD COLUMN IF NOT EXISTS confidence NUMERIC(3,2)",
    "ALTER TABLE corroboration ADD COLUMN IF NOT EXISTS verdict TEXT "
    "CHECK (verdict IN ('confirms','refutes','indeterminate'))",
    "ALTER TABLE corroboration ADD COLUMN IF NOT EXISTS observed_start DATE",
    "ALTER TABLE corroboration ADD COLUMN IF NOT EXISTS observed_end DATE",
]

JOIN_RADIUS_M = 100
HIGH_CONFIDENCE_RADIUS_M = 25

SPATIAL_NEAREST_SQL = """
    SELECT p.id, ST_Distance(p.geom::geography, ST_SetSRID(ST_MakePoint(%s,%s),4326)::geography) AS dist_m
    FROM property p
    WHERE p.geom IS NOT NULL
    ORDER BY p.geom <-> ST_SetSRID(ST_MakePoint(%s,%s),4326)
    LIMIT 1
"""

UPSERT_CORRO_SQL = """
    INSERT INTO corroboration
        (property_id, kind, reference, detail, dedup_key, captured_at,
         source_doc_id, confidence, verdict, observed_start, observed_end)
    VALUES (%s, 'bellingcat_civharm', %s, %s, %s, now(), %s, %s, 'confirms', %s, %s)
    ON CONFLICT (dedup_key) DO UPDATE
        SET reference      = EXCLUDED.reference,
            detail         = EXCLUDED.detail,
            captured_at    = now(),
            source_doc_id  = EXCLUDED.source_doc_id,
            confidence     = EXCLUDED.confidence,
            verdict        = EXCLUDED.verdict,
            observed_start = EXCLUDED.observed_start,
            observed_end   = EXCLUDED.observed_end
"""


def latest_capture(con) -> tuple[str, str]:
    cur = con.cursor()
    cur.execute(
        "SELECT sha256, raw_path FROM source_document WHERE source_type = ? "
        "ORDER BY captured_at DESC LIMIT 1",
        (SOURCE_TYPE,),
    )
    row = cur.fetchone()
    if not row:
        raise SystemExit(f"no {SOURCE_TYPE!r} capture found -- run scripts/198 first")
    return row[0], row[1]


def is_mariupol(rec: dict) -> bool:
    loc = (rec.get("location") or "").lower()
    desc = (rec.get("description") or "").lower()
    return "mariupol" in loc or "mariupol" in desc


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    sqlite_con = forensics.open_state()
    sha256, raw_path = latest_capture(sqlite_con)
    log.info("Using capture sha=%s raw_path=%s", sha256[:16], raw_path)

    data = json.loads(Path(raw_path).read_text(encoding="utf-8"))
    mrpl = [r for r in data if is_mariupol(r)]
    log.info("%d/%d records mention Mariupol", len(mrpl), len(data))

    pg = psycopg2.connect(config.DATABASE_URL)
    pg.autocommit = False
    cur = pg.cursor()
    for stmt in ALTER_STATEMENTS:
        cur.execute(stmt)

    source_doc_id = _upsert_source_doc_by_sha(cur, sha256)

    n_matched, n_skipped = 0, 0
    for rec in mrpl:
        lat, lon = rec["latitude"], rec["longitude"]
        cur.execute(SPATIAL_NEAREST_SQL, (lon, lat, lon, lat))
        row = cur.fetchone()
        if row is None:
            n_skipped += 1
            continue
        property_id, dist_m = row
        if dist_m > JOIN_RADIUS_M:
            log.info("  SKIP %s (%s) -- nearest property %.0fm away, beyond %dm radius",
                     rec["id"], rec["description"][:50], dist_m, JOIN_RADIUS_M)
            n_skipped += 1
            continue

        confidence = 0.6 if dist_m <= HIGH_CONFIDENCE_RADIUS_M else 0.4
        dedup_key = f"bellingcat_civharm:{rec['id']}:{property_id}"
        detail = json.dumps({
            "bellingcat_id": rec["id"],
            "description": rec["description"],
            "impact": rec.get("impact", []),
            "weapon_system": rec.get("weapon_system", []),
            "sources": rec.get("sources", []),
            "distance_m": round(dist_m, 1),
            "graphic": rec.get("graphic", False),
            "note": "City-wide-precision OSINT geocode, not building-confirmed -- "
                    "corroborates war damage near this property around this date, "
                    "not building identity.",
        }, ensure_ascii=False)
        cur.execute(UPSERT_CORRO_SQL, (
            property_id, rec.get("sources", [None])[0], detail, dedup_key,
            source_doc_id, confidence, rec["date"], rec["date"],
        ))
        n_matched += 1
        log.info("  MATCH %s -> property %d (%.0fm, conf=%.1f): %s",
                 rec["id"], property_id, dist_m, confidence, rec["description"][:60])

    pg.commit()
    log.info("done: %d corroboration rows upserted, %d records skipped (no property within %dm)",
              n_matched, n_skipped, JOIN_RADIUS_M)
    print(f"load_bellingcat_civharm: {n_matched} matched, {n_skipped} skipped of {len(mrpl)} Mariupol records")


if __name__ == "__main__":
    main()
