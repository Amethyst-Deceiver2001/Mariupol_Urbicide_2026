#!/usr/bin/env python3
"""Load the Eyes on Russia "Civilian Infrastructure Damage" feed
(scripts/200) as corroboration(kind='eyesonrussia_civharm') rows on the
property spine.

Tier-3 corroboration layer (docs/tier3_corroboration_design.md) -- a
FOURTH independent provenance family: CIR/Bellingcat/GeoConfirmed's open-
source verification, sourced to Twitter/social-media imagery, distinct
from this project's own crawls, UNOSAT satellite analysis, and the
Bellingcat civharm timemap (scripts/198-199) -- different organization,
different methodology, different underlying sourcing (mostly geolocated
Twitter posts here vs. Telegram for the other Bellingcat feed).

Distance-distribution check (run against the 388-record Civilian-property
subset before building this loader): median nearest-property distance 28m,
p90=121m, p95=202m -- noticeably tighter than scripts/199's Bellingcat
layer. Same 100m join radius for consistency across corroboration kinds,
but a higher confidence ceiling (0.5-0.7 vs scripts/199's 0.4-0.6) to
reflect the better empirical precision. Records beyond 100m from any
geocoded property are logged and SKIPPED, not force-matched -- same
no-false-precision rule as scripts/199.

Idempotent: dedup_key = 'eyesonrussia_civharm:<Entry_Number>:<property_id>'.

Run:
    PYTHONPATH=src python scripts/201_load_eyesonrussia_civharm.py
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import psycopg2  # noqa: E402

from mariupol_seizures import config, forensics  # noqa: E402
from mariupol_seizures.db.load import _upsert_source_doc_by_sha  # noqa: E402

log = logging.getLogger("load_eyesonrussia_civharm")

SOURCE_TYPE = "eyesonrussia_civharm"

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
    VALUES (%s, 'eyesonrussia_civharm', %s, %s, %s, now(), %s, %s, 'confirms', %s, %s)
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
        raise SystemExit(f"no {SOURCE_TYPE!r} capture found -- run scripts/200 first")
    return row[0], row[1]


def epoch_ms_to_date(ms) -> str | None:
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date().isoformat()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    sqlite_con = forensics.open_state()
    sha256, raw_path = latest_capture(sqlite_con)
    log.info("Using capture sha=%s raw_path=%s", sha256[:16], raw_path)

    geo = json.loads(Path(raw_path).read_text(encoding="utf-8"))
    features = geo["features"]
    log.info("%d Civilian Infrastructure Damage / Mariupol records", len(features))

    pg = psycopg2.connect(config.DATABASE_URL)
    pg.autocommit = False
    cur = pg.cursor()
    for stmt in ALTER_STATEMENTS:
        cur.execute(stmt)

    source_doc_id = _upsert_source_doc_by_sha(cur, sha256)

    n_matched, n_skipped = 0, 0
    for f in features:
        props = f["properties"]
        lon, lat = f["geometry"]["coordinates"]
        cur.execute(SPATIAL_NEAREST_SQL, (lon, lat, lon, lat))
        row = cur.fetchone()
        if row is None:
            n_skipped += 1
            continue
        property_id, dist_m = row
        if dist_m > JOIN_RADIUS_M:
            n_skipped += 1
            continue

        confidence = 0.7 if dist_m <= HIGH_CONFIDENCE_RADIUS_M else 0.5
        entry_no = props["Entry_Number"]
        dedup_key = f"eyesonrussia_civharm:{entry_no}:{property_id}"
        obs_date = epoch_ms_to_date(props.get("TIMESTAMP"))
        detail = json.dumps({
            "entry_number": entry_no,
            "description": props.get("Description"),
            "primary_category": props.get("Primary_category"),
            "secondary_category": props.get("Secondary_category"),
            "sector_affected": props.get("Sector_affected"),
            "link": props.get("Link"),
            "link_geolocation": props.get("Link_geolocation"),
            "credit": props.get("Credit"),
            "graphic_content_level": props.get("Graphic_content_level"),
            "distance_m": round(dist_m, 1),
            "note": "Eyes on Russia (CIR/Bellingcat/GeoConfirmed) OSINT geolocation -- "
                    "corroborates war damage near this property around this date, "
                    "not building identity.",
        }, ensure_ascii=False)
        cur.execute(UPSERT_CORRO_SQL, (
            property_id, props.get("Link"), detail, dedup_key,
            source_doc_id, confidence, obs_date, obs_date,
        ))
        n_matched += 1

    pg.commit()
    log.info("done: %d corroboration rows upserted, %d records skipped (no property within %dm)",
              n_matched, n_skipped, JOIN_RADIUS_M)
    print(f"load_eyesonrussia_civharm: {n_matched} matched, {n_skipped} skipped of {len(features)} records")


if __name__ == "__main__":
    main()
