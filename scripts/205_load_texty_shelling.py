#!/usr/bin/env python3
"""Load the Mariupol/precise-coordinate/civilian-flagged subset of the
Texty.org.ua shelling dataset (scripts/204) as
corroboration(kind='texty_shelling') rows on the property spine.

Tier-3 corroboration layer (docs/tier3_corroboration_design.md) -- a SIXTH
independent provenance family: texty.org.ua's own incident log, sourced
from press/local reporting, distinct from this project's own crawls,
UNOSAT, Bellingcat, Eyes on Russia, and GeoConfirmed.

THREE filters are applied before any spatial join:

1. Mariupol filter: the `title`/`Назва` (place/area) column must mention
   "Маріуполь"/"Мариуполь" (360 of ~48,677 country-wide rows at capture
   time).
2. Precision filter: ~21% of Mariupol rows carry whole-degree lat/lon
   (e.g. "47,38" -- city-level, not strike-level). Rows whose lat/lon
   strings contain no decimal point are dropped before any join -- joining
   a degree-rounded coordinate to "nearest property" would be a textbook
   false-precision error (111km of latitude per whole degree). 284 of 360
   rows survive this filter.
3. Civilian-object filter: Texty's own `civilian objects` column (boolean,
   set by the source team) -- e.g. the Mariupol airport row has it unset.
   270 of the 284 precision-filtered rows are civilian-flagged; the
   remainder (airport, military infrastructure) are skipped as out of
   scope per CLAUDE.md's mission framing.

Distance-distribution check (run 2026-06-28 against the 284 precision-
filtered candidates, before the civilian-object cut): median nearest-
property distance 161m, p90=1,504m -- the loosest of the project's Tier-3
layers (this is shelling-incident reporting, not photo-verified
geolocation). Confidence is capped accordingly lower (0.5 at <=25m, 0.3 at
<=100m). Same no-false-precision rule as the other Tier-3 loaders:
candidates beyond the 100m radius are logged and SKIPPED, never
force-matched.

The CSV's free-text `adress` (sic) column is carried into `detail` as
context but NOT used for matching -- no fuzzy-address pass has been built
for it yet (a candidate for docs/research_outsourcing if useful).

Idempotent: dedup_key = 'texty_shelling:<row-hash>:<property_id>' (Texty
rows carry no stable id, so a hash of title+date+place_name+coordinates
stands in for one).

Run:
    PYTHONPATH=src python scripts/205_load_texty_shelling.py
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import psycopg2  # noqa: E402

from mariupol_seizures import config, forensics  # noqa: E402
from mariupol_seizures.db.load import _upsert_source_doc_by_sha  # noqa: E402

log = logging.getLogger("load_texty_shelling")

SOURCE_TYPE = "texty_shelling_csv"

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
    VALUES (%s, 'texty_shelling', %s, %s, %s, now(), %s, %s, 'confirms', %s, %s)
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

MARIUPOL_WORDS = ("маріуп", "мариуп")


def latest_capture(con) -> tuple[str, str]:
    cur = con.cursor()
    cur.execute(
        "SELECT sha256, raw_path FROM source_document WHERE source_type = ? "
        "ORDER BY captured_at DESC LIMIT 1",
        (SOURCE_TYPE,),
    )
    row = cur.fetchone()
    if not row:
        raise SystemExit(f"no {SOURCE_TYPE!r} capture found -- run scripts/204 first")
    return row[0], row[1]


def parse_date(date_str: str) -> str | None:
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    sqlite_con = forensics.open_state()
    sha256, raw_path = latest_capture(sqlite_con)
    log.info("Using capture sha=%s raw_path=%s", sha256[:16], raw_path)

    raw_text = Path(raw_path).read_text(encoding="utf-8")
    reader = csv.reader(io.StringIO(raw_text))
    next(reader)  # header

    n_total = 0
    n_mrpl = 0
    n_precise = 0
    civ_rows = []
    for row in reader:
        if len(row) < 17:
            continue
        n_total += 1
        title = row[0]
        if not any(w in title.lower() for w in MARIUPOL_WORDS):
            continue
        n_mrpl += 1
        lat_s, lon_s = row[1].strip(), row[2].strip()
        if "." not in lat_s or "." not in lon_s:
            continue
        try:
            lat, lon = float(lat_s), float(lon_s)
        except ValueError:
            continue
        n_precise += 1
        if not row[7].strip():  # 'civilian objects' column unset
            continue
        civ_rows.append((row, lat, lon))

    log.info("%d rows total, %d mention Mariupol, %d have precise coords, "
              "%d are civilian-flagged", n_total, n_mrpl, n_precise, len(civ_rows))

    pg = psycopg2.connect(config.DATABASE_URL)
    pg.autocommit = False
    cur = pg.cursor()
    for stmt in ALTER_STATEMENTS:
        cur.execute(stmt)

    source_doc_id = _upsert_source_doc_by_sha(cur, sha256)

    n_matched, n_skipped = 0, 0
    for row, lat, lon in civ_rows:
        cur.execute(SPATIAL_NEAREST_SQL, (lon, lat, lon, lat))
        result = cur.fetchone()
        if result is None:
            n_skipped += 1
            continue
        property_id, dist_m = result
        if dist_m > JOIN_RADIUS_M:
            n_skipped += 1
            continue

        title, _, _, date_raw, place_name, place_type = row[0:6]
        link, oblast, address = row[8], row[9], row[16]
        obs_date = parse_date(date_raw)
        confidence = 0.5 if dist_m <= HIGH_CONFIDENCE_RADIUS_M else 0.3
        row_hash = hashlib.sha1(
            f"{title}|{date_raw}|{place_name}|{lon},{lat}".encode("utf-8")
        ).hexdigest()[:16]
        dedup_key = f"texty_shelling:{row_hash}:{property_id}"
        detail = json.dumps({
            "title": title,
            "place_name": place_name,
            "place_type": place_type,
            "oblast": oblast,
            "address_freetext": address or None,
            "distance_m": round(dist_m, 1),
            "note": "texty.org.ua shelling-incident report, civilian-object-"
                    "flagged -- corroborates war-related damage near this "
                    "property around this date, not building identity. "
                    "address_freetext is informational only, not used for "
                    "matching.",
        }, ensure_ascii=False)
        cur.execute(UPSERT_CORRO_SQL, (
            property_id, link or None, detail, dedup_key,
            source_doc_id, confidence, obs_date, obs_date,
        ))
        n_matched += 1
        log.info("  MATCH %s -> property %d (%.0fm, conf=%.1f): %s",
                 row_hash, property_id, dist_m, confidence, (place_name or title)[:50])

    pg.commit()
    log.info("done: %d corroboration rows upserted, %d candidates skipped",
              n_matched, n_skipped)
    print(f"load_texty_shelling: {n_matched} matched, {n_skipped} skipped of {len(civ_rows)} civilian-flagged candidates "
          f"({n_precise} precise-coord, {n_mrpl} Mariupol, {n_total} country-wide)")


if __name__ == "__main__":
    main()
