#!/usr/bin/env python3
"""Stage 3d: spatially match every ЕИСЖС new-construction object's own
geocoded point against demolished properties on the spine.

WHY THIS EXISTS
---------------
scripts/18 already parses each ЕИСЖС object's objLkLatitude/objLkLongitude
into data/exports/qgis/eisghs_newbuilds.geojson — no new capture needed, that
data has been on file since the original June 2026 crawl. What was missing
was actually USING it: for objects whose ЕИСЖС `address` field is street-only
("б-р Богдана Хмельницкого", no house number), the existing address-fuzzy-
match crosswalk logic in scripts/18/164 has nothing to join on and silently
drops them into the unmatched newbuilds layer.

This script computes, for every ЕИСЖС object, the nearest demolished
property (property with a seizure_event.stage='demolition') by geographic
distance — formalizing the 2026-07-14 ad-hoc analysis that found object
66544 sitting 9m from Богдана Хмельницкого 12's own geocoded point, later
confirmed independently by the developer's own construction-photo caption
naming it "12А" (see scripts/314/315).

This does NOT add anything to scripts/164's DEMOLITION_NEWBUILD_CROSSWALK —
it only produces the candidate list. A sub-30m match is a strong signal but
not sufficient on its own (see that file's Жукова 90Б rejection); pair it
with scripts/315's OCR corroboration (Porfir objects) or independent
decree/INN evidence (all developers) before adding an entry.

Purely local: reads the already-generated GeoJSON + a read-only DB query.
No network, no crawl — safe to run directly, any time.

OUTPUT
------
data/reports/eisghs_coordinate_matches.csv
  One row per ЕИСЖС object (all 91, not just unaddressed ones — a close
  match on an already-addressed object is also worth knowing about, e.g.
  as an independent confirmation of an existing address-based match).
  Columns: eisghs_id, declared_address, dev, has_house_number,
  nearest_demolished_pid, nearest_demolished_building_id, dist_m,
  match_tier, shares_pid_with_n_other_objects

  match_tier: exact (<5m) / strong (<30m) / weak (<100m) / none (>=100m)

  shares_pid_with_n_other_objects flags objects converging on the same
  demolished property — likely several new corpuses built across one large
  demolished footprint (subdivision), not a clean 1:1 replacement; these
  need disaggregating before any crosswalk entry, not blind linking.
"""
from __future__ import annotations

import csv
import json
import logging
import os
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402

log = logging.getLogger(__name__)

try:
    import psycopg2
    from dotenv import load_dotenv
    _PSYCOPG2 = True
except ImportError:
    _PSYCOPG2 = False

_HAS_HOUSE_NO = re.compile(r"д\.|литера|лит\.")


def _tier(dist_m: float | None) -> str:
    if dist_m is None:
        return "none"
    if dist_m < 5:
        return "exact"
    if dist_m < 30:
        return "strong"
    if dist_m < 100:
        return "weak"
    return "none"


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                         format="%(asctime)s %(levelname)s %(message)s")

    if not _PSYCOPG2:
        log.error("psycopg2/dotenv not available — run inside .venv312")
        return

    gj_path = config.PROJECT_ROOT / "data" / "exports" / "qgis" / "eisghs_newbuilds.geojson"
    if not gj_path.exists():
        log.error("%s not found — run scripts/17+18 first.", gj_path)
        return
    gj = json.loads(gj_path.read_text(encoding="utf-8"))
    features = gj["features"]
    log.info("Loaded %d ЕИСЖС objects from %s", len(features), gj_path.name)

    load_dotenv()
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        log.error("DATABASE_URL not set")
        return
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    rows: list[dict] = []
    for f in features:
        p = f["properties"]
        lon, lat = f["geometry"]["coordinates"]
        addr = p.get("address") or ""
        cur.execute(
            """
            SELECT p.id, p.building_id,
                   ST_Distance(p.geom::geography,
                               ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography)
            FROM property p
            JOIN seizure_event se
              ON se.property_id = p.id AND se.stage = 'demolition'
            WHERE p.geom IS NOT NULL
            ORDER BY p.geom <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)
            LIMIT 1
            """,
            (lon, lat, lon, lat),
        )
        r = cur.fetchone()
        pid, bid, dist = (r if r else (None, None, None))
        rows.append({
            "eisghs_id": p["eisghs_id"],
            "declared_address": addr,
            "dev": p.get("dev_name_short"),
            "has_house_number": bool(_HAS_HOUSE_NO.search(addr)),
            "nearest_demolished_pid": pid,
            "nearest_demolished_building_id": bid,
            "dist_m": round(dist, 1) if dist is not None else None,
            "match_tier": _tier(dist),
        })
    conn.close()

    pid_counts = Counter(r["nearest_demolished_pid"] for r in rows if r["nearest_demolished_pid"])
    for r in rows:
        r["shares_pid_with_n_other_objects"] = max(0, pid_counts.get(r["nearest_demolished_pid"], 0) - 1)

    out_dir = config.PROJECT_ROOT / "data" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "eisghs_coordinate_matches.csv"
    fieldnames = ["eisghs_id", "declared_address", "dev", "has_house_number",
                  "nearest_demolished_pid", "nearest_demolished_building_id",
                  "dist_m", "match_tier", "shares_pid_with_n_other_objects"]
    rows.sort(key=lambda r: (r["dist_m"] if r["dist_m"] is not None else 1e9))
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    tiers = Counter(r["match_tier"] for r in rows)
    no_house = [r for r in rows if not r["has_house_number"]]
    no_house_tiers = Counter(r["match_tier"] for r in no_house)
    shared = [r for r in rows if r["shares_pid_with_n_other_objects"] > 0]

    log.info("── Summary ─────────────────────────────────────────────")
    log.info("  Objects total:                %d", len(rows))
    log.info("  Match tiers (all objects):    %s", dict(tiers))
    log.info("  Objects lacking a house no.:  %d", len(no_house))
    log.info("  Match tiers (no house no.):   %s", dict(no_house_tiers))
    log.info("  Objects sharing a nearest pid with >=1 other object: %d "
             "(likely multi-corpus subdivisions — disaggregate before linking)",
             len(shared))
    log.info("  Output: %s", out_path)
    log.info("Next: cross-reference 'strong'/'exact' rows with scripts/315's OCR "
             "output (Porfir) or independent decree/INN evidence (all developers) "
             "before adding to scripts/164's DEMOLITION_NEWBUILD_CROSSWALK.")


if __name__ == "__main__":
    main()
