#!/usr/bin/env python3
"""Export this session's three new finding-sets as one QGIS-ready GeoJSON.

Layers (one FeatureCollection, `finding_type` attribute distinguishes them so
QGIS categorized styling can colour them independently):

  gap_register        - 211 buildings (script 150): apartments present in the
                         Jan-2025 ownerless snapshot, absent from the current
                         registry, with NO disposition marker and NO spine
                         seizure_event yet -- undocumented-disappearance leads.
  media_arc           - 22 buildings (script 151) with a full demolition ->
                         construction/new_build VISUAL arc in chat photos/video.
  corroborated_seizure - buildings (script 150) where the disappearance IS
                         already explained: either an explicit occupation
                         "Муницип.Жилье" admission, or a matching
                         demolition/reallocation/registry_inclusion event
                         already in the spine.

Geometry is resolved building_key -> data/parsed/geocoded_buildings.jsonl
first (covers buildings with no property row yet), falling back to the
property table's own geom for matched buildings. Buildings with neither are
still written as features with geometry=null (visible in the QGIS attribute
table, not the map) so nothing silently disappears from the export.

Read-only: no DB writes. Converts to GeoPackage via ogr2ogr if available.

Output:
  data/exports/qgis/session_2026-06_findings.geojson
  data/exports/qgis/session_2026-06_findings.gpkg   (if ogr2ogr present)

Run:
    PYTHONPATH=src python scripts/154_export_session_findings_qgis.py
"""
import json
import logging
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402

log = logging.getLogger(__name__)

OUT_DIR = ROOT / "data" / "exports" / "qgis"
GEOJSON_PATH = OUT_DIR / "session_2026-06_findings.geojson"
GPKG_PATH = OUT_DIR / "session_2026-06_findings.gpkg"

GAP_CSV = ROOT / "data" / "parsed" / "gap_register_undocumented_disappearance.csv"
DIFF_RECORDS = ROOT / "data" / "parsed" / "ownerless_differential_records.jsonl"
CANDIDATES = ROOT / "data" / "parsed" / "case_study_candidates.jsonl"
GEOCODED = ROOT / "data" / "parsed" / "geocoded_buildings.jsonl"
MANUAL_OVERRIDES = ROOT / "data" / "parsed" / "manual_geocode_overrides.jsonl"


def load_geocode_index():
    idx = {}
    if GEOCODED.exists():
        for line in GEOCODED.open(encoding="utf-8"):
            d = json.loads(line)
            idx[d["building_key"]] = (d["lon"], d["lat"], d.get("geocode_confidence"))
    # manual overrides take precedence (user-verified beats nominatim)
    if MANUAL_OVERRIDES.exists():
        for line in MANUAL_OVERRIDES.open(encoding="utf-8"):
            d = json.loads(line)
            idx[d["building_key"]] = (d["lon"], d["lat"], d.get("geocode_confidence"))
    return idx


def load_property_geom():
    out = {}
    try:
        import psycopg2
        con = psycopg2.connect(config.DATABASE_URL)
        cur = con.cursor()
        cur.execute("SELECT building_id, ST_X(geom), ST_Y(geom) FROM property "
                    "WHERE geom IS NOT NULL AND building_id IS NOT NULL")
        for bid, lon, lat in cur.fetchall():
            out[bid] = (lon, lat, 1.0)
        con.close()
    except Exception as e:
        log.warning("DB unreachable for property geom fallback (%s)", e)
    return out


def _feature(building_key, lon, lat, props):
    geom = {"type": "Point", "coordinates": [lon, lat]} if (lon is not None) else None
    return {"type": "Feature", "geometry": geom,
            "properties": {"building_key": building_key, **props}}


def main() -> None:
    geocode = load_geocode_index()
    prop_geom = load_property_geom()

    def latlon(bk):
        if bk in geocode:
            return geocode[bk][0], geocode[bk][1], geocode[bk][2]
        if bk in prop_geom:
            return prop_geom[bk]
        return None, None, None

    features = []
    n_geocoded = n_null = 0

    # ── gap_register ────────────────────────────────────────────────────────
    if GAP_CSV.exists():
        import csv
        with GAP_CSV.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                bk = row["building_key"]
                lon, lat, conf = latlon(bk)
                (n_geocoded := n_geocoded + 1) if lon is not None else (n_null := n_null + 1)
                features.append(_feature(bk, lon, lat, {
                    "finding_type": "gap_register",
                    "street": row["street"], "house": row["house"],
                    "district": row["district"],
                    "n_apartments_missing": int(row["n_apartments_missing"]),
                    "snapshot_date": row["snapshot_date"],
                    "geocode_confidence": conf,
                }))

    # ── media_arc (from case_study_candidates if present, else media manifest) ─
    if CANDIDATES.exists():
        for line in CANDIDATES.open(encoding="utf-8"):
            d = json.loads(line)
            if not d["has_visual_arc"]:
                continue
            bk = d["building_key"]
            lon, lat, conf = latlon(bk) if bk else (None, None, None)
            (n_geocoded := n_geocoded + 1) if lon is not None else (n_null := n_null + 1)
            features.append(_feature(bk, lon, lat, {
                "finding_type": "media_arc",
                "building_title": d["building_title"],
                "media_legs": ",".join(d["media_legs"]),
                "has_db_chain": d["has_db_chain"],
                "score": d["score"],
                "geocode_confidence": conf,
            }))

    # ── corroborated_seizure ────────────────────────────────────────────────
    if DIFF_RECORDS.exists():
        by_bk = defaultdict(list)
        for line in DIFF_RECORDS.open(encoding="utf-8"):
            d = json.loads(line)
            if d["classification"] in ("seized_municipal", "seized_court"):
                by_bk[d["building_key"]].append(d)
        for bk, items in by_bk.items():
            lon, lat, conf = latlon(bk)
            (n_geocoded := n_geocoded + 1) if lon is not None else (n_null := n_null + 1)
            features.append(_feature(bk, lon, lat, {
                "finding_type": "corroborated_seizure",
                "street": items[0]["street"], "house": items[0]["house"],
                "n_apartments": len(items),
                "classification": items[0]["classification"],
                "spine_stages": ",".join(sorted(set(
                    s for it in items for s in (it.get("spine_stages") or [])))),
                "geocode_confidence": conf,
            }))

    fc = {"type": "FeatureCollection", "features": features}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    GEOJSON_PATH.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")

    print(f"\n{'='*64}")
    print("SESSION FINDINGS QGIS EXPORT")
    print(f"  features written : {len(features)}")
    print(f"  geocoded (mapped) : {n_geocoded}")
    print(f"  no geometry       : {n_null}  (still in attribute table)")
    by_type = defaultdict(int)
    for f in features:
        by_type[f["properties"]["finding_type"]] += 1
    for t, n in by_type.items():
        print(f"    {t:22s} {n}")
    print(f"  GeoJSON → {GEOJSON_PATH}")

    try:
        subprocess.run(
            ["ogr2ogr", "-f", "GPKG", "-overwrite", str(GPKG_PATH), str(GEOJSON_PATH),
             "-nln", "session_2026_06_findings"],
            check=True, capture_output=True, text=True,
        )
        print(f"  GeoPackage → {GPKG_PATH}")
    except FileNotFoundError:
        print("  (ogr2ogr not found -- GeoJSON only; QGIS can load it directly)")
    except subprocess.CalledProcessError as e:
        log.warning("ogr2ogr failed: %s", e.stderr)
    print(f"{'='*64}\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
