#!/usr/bin/env python3
"""Export ЕИСЖС new-construction objects (scripts/17+18) as a QGIS layer.

Each object in eisghs_mariupol_objects.jsonl already carries developer-supplied
lat/lon (objLkLatitude/objLkLongitude) -- no geocoding needed. All 20 are
legal_grade (INN/cadastral cross-confirmed against dnr_land_orders +
RPD PDF), so this is a pure read of already-parsed data.

obj_status_desc distinguishes commissioned (finished) vs under_construction
vs suspended -- styled in property_spine_eisghs_newbuilds.qml.

Output: data/exports/qgis/eisghs_newbuilds.gpkg (layer "eisghs_newbuilds")
"""
import json
import logging
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402

log = logging.getLogger("export_eisghs_newbuilds")

OUT_DIR = config.PROJECT_ROOT / "data" / "exports" / "qgis"
GEOJSON_PATH = OUT_DIR / "eisghs_newbuilds.geojson"
GPKG_PATH = OUT_DIR / "eisghs_newbuilds.gpkg"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    in_path = config.PROJECT_ROOT / "data" / "parsed" / "eisghs_mariupol_objects.jsonl"
    if not in_path.exists():
        raise SystemExit(f"{in_path} not found -- run scripts/18_parse_eisghs_mariupol.py first")

    features = []
    n_with_geom = 0
    with in_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            lat, lon = d.get("lat"), d.get("lon")
            if lat is None or lon is None:
                geometry = None
            else:
                geometry = {"type": "Point", "coordinates": [float(lon), float(lat)]}
                n_with_geom += 1

            lo = d.get("land_order_match") or {}
            rpd = d.get("rpd_cadastral_match") or {}

            properties = {
                "eisghs_id": d.get("eisghs_id"),
                "nameObj": d.get("nameObj"),
                "address": d.get("address"),
                "obj_status_desc": d.get("obj_status_desc"),
                "obj_publ_dt": d.get("obj_publ_dt"),
                "commissioned_dt": d.get("commissioned_dt"),
                "flat_cnt": d.get("flat_cnt"),
                "floor_cnt": d.get("floor_cnt"),
                "area_sqm_living": d.get("area_sqm_living"),
                "sold_out_perc": d.get("sold_out_perc"),
                "dev_name_short": d.get("dev_name_short"),
                "dev_inn": d.get("dev_inn"),
                "legal_grade": d.get("legal_grade"),
                "flags": "+".join(d.get("flags") or []) or None,
                "decree_number": lo.get("decree_number"),
                "decree_date": lo.get("decree_date"),
                "decree_address": lo.get("address_normalized"),
                "cadastral_overlap": "+".join(rpd.get("cadastral_overlap_with_land_order") or []) or None,
            }
            features.append({"type": "Feature", "geometry": geometry, "properties": properties})

    geojson = {"type": "FeatureCollection", "features": features}
    GEOJSON_PATH.write_text(json.dumps(geojson, ensure_ascii=False), encoding="utf-8")
    log.info("wrote %s (%d objects, %d with geometry)", GEOJSON_PATH, len(features), n_with_geom)

    if GPKG_PATH.exists():
        GPKG_PATH.unlink()
    subprocess.run(
        ["ogr2ogr", "-f", "GPKG", str(GPKG_PATH), str(GEOJSON_PATH),
         "-nln", "eisghs_newbuilds", "-nlt", "PROMOTE_TO_MULTI"],
        check=True,
    )
    log.info("wrote %s", GPKG_PATH)
    print(f"wrote {GPKG_PATH} ({len(features)} objects, {n_with_geom} with geometry)")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    main()
