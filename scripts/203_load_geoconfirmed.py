#!/usr/bin/env python3
"""Load the Mariupol/civilian subset of GeoConfirmed's Ukraine KML export
(scripts/202) as corroboration(kind='geoconfirmed') rows on the property
spine.

Tier-3 corroboration layer (docs/tier3_corroboration_design.md) -- a FIFTH
independent provenance family: GeoConfirmed's open-source geolocation
verification, methodologically distinct from Bellingcat/Eyes-on-Russia
(separate team, separate sourcing pipeline, mostly X/Twitter-geolocated
imagery).

TWO filters are applied before any spatial join, both load-bearing:

1. Mariupol filter: placemark name+description must mention
   "Mariupol"/"Мариуп*" (474 of 57,561 country-wide placemarks at capture
   time).
2. CIVILIAN-SCOPE filter: GeoConfirmed's KML is overwhelmingly front-line/
   military-movement tracking (soldiers, drones, equipment, troop
   positions) with NO category field to distinguish that from civilian
   property damage -- unlike Bellingcat's "impact" tags or Eyes on
   Russia's "Primary_category". Per CLAUDE.md's mission framing (named
   seizure acts against specific PROPERTIES, not general war-monitoring),
   placemarks are kept only if name+description contain a civilian-
   property keyword (school/hospital/apartment/residential/house/
   building/church/civilian or the RU/UK equivalents). This cut 474 ->
   94 candidates at capture time. Everything dropped by this filter is
   genuinely out of scope, not a false negative -- it is front-line/
   military content this project does not corroborate.

Distance-distribution check (run 2026-06-28 against the 94 civilian-
filtered candidates): median nearest-property distance 78.6m, p90=585m,
p95=1,398m -- markedly looser than Bellingcat (scripts/199) or Eyes on
Russia (scripts/201). Confidence is capped lower accordingly (0.55 at
<=25m, 0.35 at <=100m) to reflect that coarser precision. Same no-false-
precision rule as the other Tier-3 loaders: candidates beyond the 100m
radius are logged and SKIPPED, never force-matched.

Idempotent: dedup_key = 'geoconfirmed:<placemark-hash>:<property_id>'
(GeoConfirmed KML placemarks carry no stable id, so a hash of
name+description+coordinates stands in for one).

Run:
    PYTHONPATH=src python scripts/203_load_geoconfirmed.py
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import sys
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import psycopg2  # noqa: E402

from mariupol_seizures import config, forensics  # noqa: E402
from mariupol_seizures.db.load import _upsert_source_doc_by_sha  # noqa: E402

log = logging.getLogger("load_geoconfirmed")

SOURCE_TYPE = "geoconfirmed_kml"

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
    VALUES (%s, 'geoconfirmed', %s, %s, %s, now(), %s, %s, 'confirms', %s, %s)
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

MARIUPOL_RE = re.compile(r"mariupol|мариуп", re.IGNORECASE)
CIVILIAN_RE = re.compile(
    r"school|hospital|apartment|residential|house|civilian|building|church|"
    r"дом|здани|школ|больниц|жил|квартир|церков|граждан|многоэтаж|многоквартир",
    re.IGNORECASE,
)
PLACEMARK_RE = re.compile(r"<Placemark>(.*?)</Placemark>", re.S)
NAME_RE = re.compile(r"<name><!\[CDATA\[(.*?)\]\]></name>", re.S)
DESC_RE = re.compile(r"<description><!\[CDATA\[(.*?)\]\]></description>", re.S)
COORD_RE = re.compile(r"<coordinates><!\[CDATA\[([\-\d.]+),([\-\d.]+)")
DATE_RE = re.compile(r"(\d{1,2})\s+([A-Z]{3})\s+(\d{4})")
MONTHS = {
    "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04", "MAY": "05", "JUN": "06",
    "JUL": "07", "AUG": "08", "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12",
}


def latest_capture(con) -> tuple[str, str]:
    cur = con.cursor()
    cur.execute(
        "SELECT sha256, raw_path FROM source_document WHERE source_type = ? "
        "ORDER BY captured_at DESC LIMIT 1",
        (SOURCE_TYPE,),
    )
    row = cur.fetchone()
    if not row:
        raise SystemExit(f"no {SOURCE_TYPE!r} capture found -- run scripts/202 first")
    return row[0], row[1]


def parse_date(name: str) -> str | None:
    m = DATE_RE.search(name.upper())
    if not m:
        return None
    day, mon, year = m.groups()
    mon_num = MONTHS.get(mon)
    if not mon_num:
        return None
    return f"{year}-{mon_num}-{int(day):02d}"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    sqlite_con = forensics.open_state()
    sha256, raw_path = latest_capture(sqlite_con)
    log.info("Using capture sha=%s raw_path=%s", sha256[:16], raw_path)

    zip_bytes = Path(raw_path).read_bytes()
    with ZipFile(BytesIO(zip_bytes)) as zf:
        kml_text = zf.read("doc.kml").decode("utf-8")

    all_placemarks = PLACEMARK_RE.findall(kml_text)
    log.info("%d placemarks country-wide", len(all_placemarks))

    mrpl = [p for p in all_placemarks if MARIUPOL_RE.search(p)]
    log.info("%d placemarks mention Mariupol", len(mrpl))

    civ = [p for p in mrpl if CIVILIAN_RE.search(p)]
    log.info("%d civilian-property-scoped of %d Mariupol placemarks "
             "(rest dropped as out-of-scope front-line/military content)",
             len(civ), len(mrpl))

    pg = psycopg2.connect(config.DATABASE_URL)
    pg.autocommit = False
    cur = pg.cursor()
    for stmt in ALTER_STATEMENTS:
        cur.execute(stmt)

    source_doc_id = _upsert_source_doc_by_sha(cur, sha256)

    n_matched, n_skipped = 0, 0
    for p in civ:
        coord_m = COORD_RE.search(p)
        if not coord_m:
            n_skipped += 1
            continue
        lon, lat = float(coord_m.group(1)), float(coord_m.group(2))

        cur.execute(SPATIAL_NEAREST_SQL, (lon, lat, lon, lat))
        row = cur.fetchone()
        if row is None:
            n_skipped += 1
            continue
        property_id, dist_m = row
        if dist_m > JOIN_RADIUS_M:
            n_skipped += 1
            continue

        name_m = NAME_RE.search(p)
        desc_m = DESC_RE.search(p)
        name = name_m.group(1).strip() if name_m else ""
        description = desc_m.group(1).strip() if desc_m else ""
        obs_date = parse_date(name)

        confidence = 0.55 if dist_m <= HIGH_CONFIDENCE_RADIUS_M else 0.35
        placemark_hash = hashlib.sha1(
            f"{name}|{description}|{lon},{lat}".encode("utf-8")
        ).hexdigest()[:16]
        dedup_key = f"geoconfirmed:{placemark_hash}:{property_id}"
        detail = json.dumps({
            "name": name,
            "description": description,
            "distance_m": round(dist_m, 1),
            "note": "GeoConfirmed OSINT geolocation, civilian-property-keyword-"
                    "filtered from the country-wide front-line/military "
                    "feed -- corroborates war-related activity near this "
                    "property around this date, not building identity.",
        }, ensure_ascii=False)
        cur.execute(UPSERT_CORRO_SQL, (
            property_id, None, detail, dedup_key,
            source_doc_id, confidence, obs_date, obs_date,
        ))
        n_matched += 1
        log.info("  MATCH %s -> property %d (%.0fm, conf=%.2f): %s",
                 placemark_hash, property_id, dist_m, confidence, name[:40])

    pg.commit()
    log.info("done: %d corroboration rows upserted, %d candidates skipped",
              n_matched, n_skipped)
    print(f"load_geoconfirmed: {n_matched} matched, {n_skipped} skipped of {len(civ)} civilian-scoped candidates "
          f"({len(mrpl)} Mariupol placemarks, {len(all_placemarks)} country-wide)")


if __name__ == "__main__":
    main()
