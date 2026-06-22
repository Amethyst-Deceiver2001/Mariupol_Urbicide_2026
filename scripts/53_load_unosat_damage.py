#!/usr/bin/env python3
"""Load the UNOSAT 12-May-2022 building damage assessment (Mariupol,
Livoberezhnyi/Zhovtnevyi districts) as corroboration(kind='unosat_damage')
rows on the property spine.

Tier-3 corroboration layer, sub-layer S1 (docs/tier3_corroboration_design.md
section 3, "wave 1"). This is the project's FIRST *independent* provenance
family: a UN satellite-imagery analyst's building-by-building damage call,
made from commercial satellite imagery with no relationship to the occupation
administration or Russian federal records. It does not speak to the seizure
act itself -- only to whether the building was war-damaged -- but a property
that is BOTH (a) seized/reallocated per the occupation-side record AND (b)
independently confirmed war-damaged by a UN analyst is materially stronger
for RD4U categories A3.1/A3.2/A3.3 than occupation-side records alone.

Source: data/raw/<sha256>.zip, captured by scripts/52_fetch_unosat_damage.py
(manifest data/parsed/unosat_manifest.json). Only the headline 12-May-2022
dataset's Damage Assessment (DA) layer is loaded here; the same zip's AOI
boundary layer, and the March-2022 / 26-March-2022-RDA datasets (also
captured), are out of scope for this pass.

Pipeline:
  1. Idempotent `ALTER TABLE corroboration ADD COLUMN IF NOT EXISTS` for
     source_doc_id, confidence, verdict, observed_start, observed_end
     (docs/tier3_corroboration_design.md section 4 schema additions).
  2. Extract the *_DA_12May2022.{shp,shx,dbf,prj} members from the captured
     zip (pyshp), keeping only the 4 building-level damage classes (Destroyed
     / Severe / Moderate / Possible Damage) -- excludes 17 "Impact Crater"
     features (road/field, not buildings). ~5,643 features remain, matching
     the dataset's documented "5,647 structures" headline to within rounding.
  3. Reproject each point EPSG:3857 -> EPSG:4326 (pyproj) and load into a
     TEMP TABLE.
  4. Spatial-join against property.geom: ST_DWithin(..., 25m), nearest-wins
     per property (DISTINCT ON property.id, ORDER BY distance).
  5. INSERT ... ON CONFLICT (dedup_key) DO UPDATE corroboration rows:
       kind='unosat_damage', verdict='confirms',
       confidence = 0.95 (<=10m) or 0.80 (<=25m),
       observed_start = observed_end = the 12-May-2022 sensor date,
       detail = full UNOSAT attestation (damage class, analyst, confidence
       label, distance, plus chain-of-custody: sha256/raw_path/HDX URL/license).

Idempotent / re-runnable: dedup_key = 'unosat_damage:<sha256>:<property_id>:<feature_idx>'.
"""
from __future__ import annotations

import json
import logging
import sys
import tempfile
import zipfile
from pathlib import Path

import psycopg2
import psycopg2.extras
import pyproj
import shapefile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402
from mariupol_seizures.db.load import _upsert_source_doc_by_sha  # noqa: E402

log = logging.getLogger("load_unosat_damage")

MANIFEST_PATH = config.DATA_DIR / "parsed" / "unosat_manifest.json"
HDX_DATASET = "mariupol-updated-building-damage-assessment-overview-map-livoberezhnyi-and-zhovtnevyi-dist"

# Building-level damage classes from the 12-May-2022 DA layer. Excludes
# "Impact Crater (Damage to Road)" / "Impact Crater (Damage to Field)"
# (17 features) -- those are not buildings and would create spurious
# property-level matches.
BUILDING_DAMAGE_CLASSES = {"Destroyed", "Severe Damage", "Moderate Damage", "Possible Damage"}

DA_LAYER_SUFFIX = "_DA_12May2022.shp"
DA_LAYER_EXTS = (".shp", ".shx", ".dbf", ".prj", ".cpg")

JOIN_RADIUS_M = 25
HIGH_CONFIDENCE_RADIUS_M = 10

ALTER_STATEMENTS = [
    "ALTER TABLE corroboration ADD COLUMN IF NOT EXISTS source_doc_id BIGINT REFERENCES source_document(id)",
    "ALTER TABLE corroboration ADD COLUMN IF NOT EXISTS confidence NUMERIC(3,2)",
    "ALTER TABLE corroboration ADD COLUMN IF NOT EXISTS verdict TEXT "
    "CHECK (verdict IN ('confirms','refutes','indeterminate'))",
    "ALTER TABLE corroboration ADD COLUMN IF NOT EXISTS observed_start DATE",
    "ALTER TABLE corroboration ADD COLUMN IF NOT EXISTS observed_end DATE",
]

CREATE_TEMP_TABLE = """
    CREATE TEMP TABLE unosat_points (
        idx                     INT PRIMARY KEY,
        geom                    geometry(Point, 4326),
        damage_class            TEXT,
        damage_class_march      TEXT,
        sensor_date             DATE,
        sensor_date_march       DATE,
        confidence_label        TEXT,
        confidence_label_march  TEXT,
        sensor                  TEXT,
        field_validation        TEXT,
        damage_status           TEXT,
        analyst                 TEXT,
        site_type               TEXT,
        settlement              TEXT,
        neighborhood            TEXT,
        notes                   TEXT,
        event_code              TEXT
    )
"""

INSERT_TEMP_ROWS = """
    INSERT INTO unosat_points
        (idx, geom, damage_class, damage_class_march, sensor_date, sensor_date_march,
         confidence_label, confidence_label_march, sensor, field_validation,
         damage_status, analyst, site_type, settlement, neighborhood, notes, event_code)
    VALUES %s
"""
INSERT_TEMP_TEMPLATE = (
    "(%s, ST_SetSRID(ST_MakePoint(%s,%s),4326), %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
)

SPATIAL_JOIN_SQL = """
    SELECT DISTINCT ON (p.id)
        p.id AS property_id, u.idx, u.damage_class, u.damage_class_march,
        u.sensor_date, u.sensor_date_march, u.confidence_label,
        u.confidence_label_march, u.sensor, u.field_validation,
        u.damage_status, u.analyst, u.site_type, u.settlement, u.neighborhood,
        u.notes, u.event_code,
        ST_Distance(p.geom::geography, u.geom::geography) AS dist_m
    FROM property p
    JOIN unosat_points u
      ON ST_DWithin(p.geom::geography, u.geom::geography, %s)
    WHERE p.geom IS NOT NULL
    ORDER BY p.id, dist_m ASC
"""

UPSERT_CORRO_SQL = """
    INSERT INTO corroboration
        (property_id, kind, reference, detail, dedup_key, captured_at,
         source_doc_id, confidence, verdict, observed_start, observed_end)
    VALUES (%s, 'unosat_damage', %s, %s, %s, now(), %s, %s, 'confirms', %s, %s)
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


def load_manifest_resource() -> tuple[dict, dict]:
    if not MANIFEST_PATH.exists():
        raise SystemExit(f"{MANIFEST_PATH} not found -- run scripts/52_fetch_unosat_damage.py first.")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    ds = next((d for d in manifest["datasets"] if d["hdx_dataset"] == HDX_DATASET), None)
    if ds is None:
        raise SystemExit(f"{HDX_DATASET!r} not found in {MANIFEST_PATH}")
    res = next((r for r in ds["resources"] if r["role"] == "primary"), None)
    if res is None or not res.get("raw_path"):
        raise SystemExit(f"no captured primary SHP resource for {HDX_DATASET!r}")
    return ds, res


def iter_da_features(zip_path: Path):
    """Yield (idx, x, y, record_dict) for every feature in the *_DA_12May2022
    layer of the captured zip (POINT shapefile, EPSG:3857)."""
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        da_member = next((n for n in names if n.endswith(DA_LAYER_SUFFIX)), None)
        if da_member is None:
            raise SystemExit(f"no *{DA_LAYER_SUFFIX} member found in {zip_path}")
        stem = da_member[: -len(".shp")]
        with tempfile.TemporaryDirectory() as tmpdir:
            for ext in DA_LAYER_EXTS:
                member = stem + ext
                if member in names:
                    zf.extract(member, tmpdir)
            reader = shapefile.Reader(str(Path(tmpdir) / stem))
            for idx, sr in enumerate(reader.iterShapeRecords()):
                x, y = sr.shape.points[0]
                yield idx, x, y, sr.record.as_dict()


def main() -> None:
    ds, res = load_manifest_resource()
    sha256 = res["sha256"]
    zip_path = config.PROJECT_ROOT / res["raw_path"]
    log.info("Dataset: %s", ds["title"])
    log.info("Resource: %s (sha256=%s)", res["name"], sha256)

    transformer = pyproj.Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)

    rows = []
    n_total = 0
    n_buildings = 0
    for idx, x, y, rec in iter_da_features(zip_path):
        n_total += 1
        damage_class = rec.get("d_Main_D_1")
        if damage_class not in BUILDING_DAMAGE_CLASSES:
            continue
        n_buildings += 1
        lon, lat = transformer.transform(x, y)
        sensor_date = rec.get("SensorDa_1")
        sensor_date_march = rec.get("SensorDate")
        rows.append((
            idx, lon, lat,
            damage_class, rec.get("d_Main_Dam"),
            sensor_date.isoformat() if sensor_date else None,
            sensor_date_march.isoformat() if sensor_date_march else None,
            rec.get("d_Confid_1"), rec.get("d_Confiden"),
            rec.get("d_Sensor_1"), rec.get("d_FieldVal"), rec.get("d_Damage_S"),
            rec.get("d_Analyst"), rec.get("d_SiteID"), rec.get("Settlement"),
            rec.get("Neighborho"), rec.get("Notes") or None, rec.get("EventCode"),
        ))
    log.info("Parsed %d DA features (%d building-damage, %d excluded craters/other)",
             n_total, n_buildings, n_total - n_buildings)

    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()

    for stmt in ALTER_STATEMENTS:
        cur.execute(stmt)
    log.info("corroboration schema columns ensured (source_doc_id, confidence, "
             "verdict, observed_start, observed_end)")

    source_doc_id = _upsert_source_doc_by_sha(cur, sha256)
    log.info("source_document id for %s -> %s", sha256, source_doc_id)

    cur.execute(CREATE_TEMP_TABLE)
    psycopg2.extras.execute_values(cur, INSERT_TEMP_ROWS, rows, template=INSERT_TEMP_TEMPLATE)
    log.info("loaded %d UNOSAT points into temp table", len(rows))

    cur.execute(SPATIAL_JOIN_SQL, (JOIN_RADIUS_M,))
    matches = cur.fetchall()
    log.info("spatial join: %d/%d geocoded properties within %dm of a UNOSAT "
             "damage point", len(matches), _count_geocoded(cur), JOIN_RADIUS_M)

    n_high = n_low = 0
    for (property_id, idx, damage_class, damage_class_march, sensor_date,
         sensor_date_march, confidence_label, confidence_label_march, sensor,
         field_validation, damage_status, analyst, site_type, settlement,
         neighborhood, notes, event_code, dist_m) in matches:

        if dist_m <= HIGH_CONFIDENCE_RADIUS_M:
            confidence = 0.95
            n_high += 1
        else:
            confidence = 0.80
            n_low += 1

        detail = {
            "source": "unosat_damage",
            "unosat_code": event_code,
            "feature_idx": idx,
            "settlement": settlement,
            "neighborhood": neighborhood,
            "site_type": site_type,
            "damage_class": damage_class,
            "damage_class_march": damage_class_march,
            "sensor_date": sensor_date.isoformat() if sensor_date else None,
            "sensor_date_march": sensor_date_march.isoformat() if sensor_date_march else None,
            "confidence_label": confidence_label,
            "confidence_label_march": confidence_label_march,
            "sensor": sensor,
            "field_validation": field_validation,
            "damage_status": damage_status,
            "analyst": analyst,
            "notes": notes,
            "distance_m": round(float(dist_m), 1),
            "dataset_title": ds["title"],
            "hdx_url": ds["hdx_url"],
            "license": ds["license"],
            "unosat_dataset_imagery_dates": ds["imagery_dates"],
            "source_sha256": sha256,
            "source_raw_path": res["raw_path"],
        }
        reference = (
            f"UNOSAT building damage assessment ({detail['sensor_date']}): "
            f"{damage_class} ({detail['distance_m']}m from property point, "
            f"analyst {analyst}, confidence {confidence_label})"
        )
        dedup_key = f"unosat_damage:{sha256}:{property_id}:{idx}"
        cur.execute(UPSERT_CORRO_SQL, (
            property_id, reference, json.dumps(detail, ensure_ascii=False), dedup_key,
            source_doc_id, confidence, detail["sensor_date"], detail["sensor_date"],
        ))

    con.commit()
    cur.close()
    con.close()
    log.info("upserted %d unosat_damage corroboration rows (%d at <=%dm/conf=0.95, "
             "%d at <=%dm/conf=0.80)",
             len(matches), n_high, HIGH_CONFIDENCE_RADIUS_M, n_low, JOIN_RADIUS_M)
    print(f"load_unosat_damage: {len(matches)} corroboration rows "
          f"({n_high} high-confidence <={HIGH_CONFIDENCE_RADIUS_M}m, "
          f"{n_low} <={JOIN_RADIUS_M}m); parsed {n_buildings}/{n_total} building-damage features")


def _count_geocoded(cur) -> int:
    cur.execute("SELECT count(*) FROM property WHERE geom IS NOT NULL")
    return cur.fetchone()[0]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    main()
