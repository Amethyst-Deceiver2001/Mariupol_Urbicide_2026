#!/usr/bin/env python3
"""Extract parcel polygons from the Rosreestr/NSPD responses captured by
scripts/295 and write them as a GeoJSON polygon layer for the interactive map.

Tolerant by design — the exact response shape of the geoblocked NSPD/PKK APIs
can't be verified from Claude's side, so this walks whatever JSON came back and
pulls the first Polygon/MultiPolygon geometry it finds, reprojecting from Web
Mercator (EPSG:3857) to WGS84 (EPSG:4326) when the coordinate magnitude says so
(both portals historically return 3857 metres). If a captured response has an
unexpected shape, it's logged and skipped — tell Claude and the extractor can
be tightened to match.

Runs locally, no network (reads the raw store):
    .venv312/bin/python scripts/296_parse_cadastral_parcels.py

Output:
    data/exports/qgis/cadastral_parcels.geojson
    docs/exhibits/assets/map/cadastral_parcels.geojson
"""
from __future__ import annotations

import json
import logging
import math
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402

log = logging.getLogger("cadastral_parse")

QGIS_OUT = ROOT / "data" / "exports" / "qgis" / "cadastral_parcels.geojson"
PUBLIC_OUT = ROOT / "docs" / "exhibits" / "assets" / "map" / "cadastral_parcels.geojson"


def _merc_to_wgs84(x: float, y: float) -> tuple[float, float]:
    """EPSG:3857 metres -> (lon, lat) degrees."""
    lon = (x / 20037508.34) * 180.0
    lat = (y / 20037508.34) * 180.0
    lat = 180.0 / math.pi * (2.0 * math.atan(math.exp(lat * math.pi / 180.0)) - math.pi / 2.0)
    return lon, lat


def _looks_mercator(coord) -> bool:
    # a single [x, y] pair; |x|>180 means it's metres, not degrees
    return abs(coord[0]) > 180 or abs(coord[1]) > 90


def _reproject_ring(ring):
    out = []
    for pt in ring:
        x, y = pt[0], pt[1]
        if _looks_mercator(pt):
            lon, lat = _merc_to_wgs84(x, y)
        else:
            lon, lat = x, y
        out.append([round(lon, 6), round(lat, 6)])
    return out


def _normalise_geometry(geom):
    """Return a GeoJSON Polygon/MultiPolygon in WGS84, or None."""
    t = geom.get("type")
    if t == "Polygon":
        return {"type": "Polygon",
                "coordinates": [_reproject_ring(r) for r in geom["coordinates"]]}
    if t == "MultiPolygon":
        return {"type": "MultiPolygon",
                "coordinates": [[_reproject_ring(r) for r in poly] for poly in geom["coordinates"]]}
    return None


def _find_geometry(obj):
    """Depth-first search for the first dict with a Polygon/MultiPolygon
    'type' + 'coordinates' (handles NSPD GeoJSON, PKK {feature:{geometry}}, etc.)."""
    if isinstance(obj, dict):
        if obj.get("type") in ("Polygon", "MultiPolygon") and "coordinates" in obj:
            return obj
        # PKK stores rings under feature.geometry.coordinates with type sometimes absent
        for key in ("geometry", "feature", "features", "data", "geo"):
            if key in obj:
                g = _find_geometry(obj[key])
                if g:
                    return g
        for v in obj.values():
            g = _find_geometry(v)
            if g:
                return g
    elif isinstance(obj, list):
        for v in obj:
            g = _find_geometry(v)
            if g:
                return g
    return None


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    con = sqlite3.connect(config.STATE_DB)
    rows = con.execute(
        "SELECT sha256, url, title FROM source_document "
        "WHERE source_type = 'rosreestr_cadastral_parcel' ORDER BY captured_at"
    ).fetchall()
    con.close()
    if not rows:
        log.warning("No rosreestr_cadastral_parcel captures found — run scripts/295 from the VPS first.")
        return

    features = []
    seen_cad = set()
    ok = skipped = 0
    for sha, url, title in rows:
        cad = title.replace("Cadastral parcel — ", "").split(" ", 1)[-1].strip()
        if cad in seen_cad:
            continue
        path = config.RAW_DIR / f"{sha}.json"
        if not path.exists():
            # content-type may have stored it without .json
            candidates = list(config.RAW_DIR.glob(f"{sha}.*"))
            path = candidates[0] if candidates else None
        if not path or not path.exists():
            skipped += 1
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except (json.JSONDecodeError, ValueError):
            skipped += 1
            continue
        geom = _find_geometry(data)
        if not geom:
            skipped += 1
            continue
        norm = _normalise_geometry(geom)
        if not norm:
            skipped += 1
            continue
        seen_cad.add(cad)
        features.append({
            "type": "Feature", "geometry": norm,
            "properties": {"cadastral_no": cad, "source": "rosreestr_pkk_nspd",
                           "geocode_method": "cadastral_polygon", "geocode_confidence": 0.95},
        })
        ok += 1

    fc = {"type": "FeatureCollection", "features": features}
    for out in (QGIS_OUT, PUBLIC_OUT):
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
    log.info("wrote %d cadastral polygons (%d responses skipped/unparseable) -> %s",
             ok, skipped, QGIS_OUT)
    print(f"cadastral_parcels: {ok} exact polygons extracted, {skipped} skipped")


if __name__ == "__main__":
    main()
