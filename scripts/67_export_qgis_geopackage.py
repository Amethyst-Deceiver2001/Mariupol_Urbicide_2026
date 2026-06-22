#!/usr/bin/env python3
"""Export a GeoPackage snapshot of the property spine for QGIS.

Read-only: queries the loaded PostgreSQL/PostGIS DB, writes one GeoJSON with
one feature per property (geometry=null for the ~4,094 properties without a
geocoded point -- they still appear in the attribute table, just not on the
map), then converts to GeoPackage via ogr2ogr (layer "property_spine").

Per-property attributes replicate scripts/33_corroboration_report.py's family
logic (SEIZURE_FAMILY / CORRO_FAMILY / INDEPENDENT_CORRO_KINDS) so the
legal-grade (>=2 independent source families) status can be styled directly
in QGIS, plus stage/date/corroboration summaries for filtering and timeline
styling.

PRIVACY: no owner-table data is included (owner is sensitive/PII and not
joined here at all).

Output: data/exports/qgis/mariupol_property_spine.gpkg
"""
from __future__ import annotations

import json
import logging
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402
from mariupol_seizures.normalize.toponym import load_toponyms, _toponym_match_key  # noqa: E402

log = logging.getLogger("export_qgis_geopackage")

OUT_DIR = config.PROJECT_ROOT / "data" / "exports" / "qgis"
GEOJSON_PATH = OUT_DIR / "mariupol_property_spine.geojson"
GPKG_PATH = OUT_DIR / "mariupol_property_spine.gpkg"

# Mirrors scripts/33_corroboration_report.py
SEIZURE_FAMILY = {
    "court_petition": "court_case",
    "court_transfer": "court_case",
    "appeal": "court_case",
    "entered_force": "court_case",
    "ownerless_designation": "ownerless_decree",
    "registry_inclusion": "ownerless_registry",
    "demolition": "demolition",
    "reallocation": "reallocation",
}
CORRO_FAMILY = {
    "displacement_claim": "housing_distribution",
    "mirror_source": "damage_assessment",
}
INDEPENDENT_CORRO_KINDS = {"unosat_damage", "satellite_pair", "testimony_ref", "ua_registry_mirror"}
INDEPENDENT_FAMILY = "independent_corroboration"

KEY_STAGES = ["ownerless_designation", "registry_inclusion", "demolition", "court_transfer"]


def _load_geocode_index() -> dict[str, tuple[float, str]]:
    """building_key -> (geocode_confidence, geocode_source), mirroring
    db/load.py's _load_geocode_index() plus address_registry.jsonl's
    already_geocoded (eisghs_наш.дом.рф, confidence 1.0)."""
    index: dict[str, tuple[float, str]] = {}

    with (config.PROJECT_ROOT / "data" / "parsed" / "address_registry.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            already = d.get("already_geocoded")
            if already:
                index[d["building_key"]] = (1.0, already.get("source", "eisghs_наш.дом.рф"))

    for fname in ("geocoded_buildings.jsonl", "manual_geocode_overrides.jsonl"):
        path = config.PROJECT_ROOT / "data" / "parsed" / fname
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                if d.get("geocode_confidence", 0) >= 0.8:
                    index[d["building_key"]] = (d["geocode_confidence"], d.get("geocode_source"))

    return index


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    geocode_index = _load_geocode_index()

    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()

    cur.execute("""
        SELECT id, building_id, occupation_address, prewar_address,
               cadastral_no, rd4u_category,
               ST_X(geom), ST_Y(geom)
        FROM property
    """)
    props = {}
    for pid, bid, occ, pre, cad, rd4u, lon, lat in cur.fetchall():
        props[pid] = {
            "id": pid, "building_id": bid, "occupation_address": occ,
            "prewar_address": pre, "cadastral_no": cad, "rd4u_category": rd4u,
            "lon": lon, "lat": lat,
            "families": set(), "stages": set(), "stage_dates": {},
            "corroboration_kinds": set(), "n_seizure_events": 0,
            "n_corroboration": 0, "destruction_pct": None,
        }

    cur.execute("SELECT property_id, stage, event_date FROM seizure_event")
    for pid, stage, ev in cur.fetchall():
        p = props.get(pid)
        if not p:
            continue
        p["n_seizure_events"] += 1
        p["stages"].add(stage)
        fam = SEIZURE_FAMILY.get(stage)
        if fam:
            p["families"].add(fam)
        if ev and (stage not in p["stage_dates"] or ev < p["stage_dates"][stage]):
            p["stage_dates"][stage] = ev

    cur.execute("SELECT property_id, kind, detail, verdict, confidence FROM corroboration")
    for pid, kind, detail, verdict, confidence in cur.fetchall():
        p = props.get(pid)
        if not p:
            continue
        p["n_corroboration"] += 1
        p["corroboration_kinds"].add(kind)
        fam = CORRO_FAMILY.get(kind)
        if fam:
            p["families"].add(fam)
        elif kind in INDEPENDENT_CORRO_KINDS and verdict == "confirms" and (confidence or 0) >= Decimal("0.80"):
            p["families"].add(INDEPENDENT_FAMILY)
        if kind == "mirror_source" and detail:
            pct = detail.get("destruction_pct")
            if pct is not None:
                p["destruction_pct"] = max(p["destruction_pct"] or 0, float(pct))

    cur.close()
    con.close()

    toponyms = load_toponyms()

    features = []
    n_geom = 0
    n_renamed = 0
    for p in props.values():
        if p["lon"] is not None and p["lat"] is not None:
            geometry = {"type": "Point", "coordinates": [p["lon"], p["lat"]]}
            n_geom += 1
        else:
            geometry = None

        street_part = (p["occupation_address"] or "").split(",", 1)[0]
        toponym_hit = toponyms.get(_toponym_match_key(street_part))
        street_renamed = toponym_hit is not None and toponym_hit.kind in ("rename", "translit")
        if street_renamed:
            n_renamed += 1

        geocode_confidence, geocode_source = geocode_index.get(p["building_id"], (None, None))

        properties = {
            "id": p["id"],
            "building_id": p["building_id"],
            "occupation_address": p["occupation_address"],
            "prewar_address": p["prewar_address"],
            "cadastral_no": p["cadastral_no"],
            "rd4u_category": p["rd4u_category"],
            "n_families": len(p["families"]),
            "families": "+".join(sorted(p["families"])) or None,
            "legal_grade": len(p["families"]) >= 2,
            "n_seizure_events": p["n_seizure_events"],
            "stages": "+".join(sorted(p["stages"])) or None,
            "n_corroboration": p["n_corroboration"],
            "corroboration_kinds": "+".join(sorted(p["corroboration_kinds"])) or None,
            "destruction_pct": p["destruction_pct"],
            "street_renamed": street_renamed,
            "prewar_street_name": toponym_hit.prewar_name if toponym_hit else None,
            "toponym_source_ref": toponym_hit.source_ref if toponym_hit else None,
            "geocode_confidence": geocode_confidence,
            "geocode_source": geocode_source,
        }
        for stage in KEY_STAGES:
            d = p["stage_dates"].get(stage)
            properties[f"{stage}_date"] = d.isoformat() if d else None

        features.append({"type": "Feature", "geometry": geometry, "properties": properties})

    geojson = {"type": "FeatureCollection", "features": features}
    GEOJSON_PATH.write_text(json.dumps(geojson, ensure_ascii=False), encoding="utf-8")
    log.info("wrote %s (%d properties, %d with geometry, %d on a renamed street)",
             GEOJSON_PATH, len(features), n_geom, n_renamed)

    if GPKG_PATH.exists():
        GPKG_PATH.unlink()
    subprocess.run(
        ["ogr2ogr", "-f", "GPKG", str(GPKG_PATH), str(GEOJSON_PATH),
         "-nln", "property_spine", "-nlt", "PROMOTE_TO_MULTI"],
        check=True,
    )
    log.info("wrote %s", GPKG_PATH)
    print(f"wrote {GPKG_PATH} ({len(features)} properties, {n_geom} with geometry, "
          f"{n_renamed} on a renamed street)")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    main()
