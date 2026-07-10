#!/usr/bin/env python3
"""Build APPROXIMATE block polygons for the "territory bounded by streets X, Y,
Z…" land grants — a real footprint outline instead of scripts/254's single
centroid point.

WHY
---
20 of the 101 land-grant decrees describe the allocated parcel as a city block
bounded by named streets ("территория, ограниченная проспектом Металлургов,
улицей Кальчанской, улицей Артема, улицей Евпаторийской…"). scripts/254
collapses each to one centroid point. This instead fetches the actual OSM
geometry of each boundary street (Overpass), keeps the nodes that fall near the
grant's known approximate location, and takes their convex hull — an
approximate but honestly-bounded block outline.

NOT parcel-exact. For the ~26 grants (and 11 industrial parcels) that carry a
cadastral number, scripts/295/296 fetch the exact ЕГРН polygon from the
Rosreestr Public Cadastral Map (needs a VPS). This script is the best we can do
for the street-bounded parcels that have no cadastral number on file.

Overpass is a public OSM endpoint (not geoblocked), but this is still a
network job — run it yourself, not Claude, per project convention:
    .venv312/bin/python scripts/294_build_landgrant_block_polygons.py

Output:
    data/exports/qgis/land_grant_blocks.geojson       (Polygon per resolved grant)
    docs/exhibits/assets/map/land_grant_blocks.geojson (public copy)
Each polygon carries geocode_method='street_boundary_hull' and a confidence of
0.5 — approximate, for orientation, clearly labeled as such in the map popup.
"""
from __future__ import annotations

import json
import logging
import math
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402
# Reuse scripts/254's street extraction + declension helpers verbatim so the two
# stay in lockstep.
sys.path.insert(0, str(ROOT / "scripts"))
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "_s254", ROOT / "scripts" / "254_geocode_bounded_parcels.py")
_s254 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_s254)

log = logging.getLogger("landgrant_blocks")

LAND_ORDERS_PATH = ROOT / "data" / "parsed" / "dnr_land_orders.jsonl"
STREET_CACHE = ROOT / "data" / "parsed" / ".street_geocode_cache.json"
QGIS_OUT = ROOT / "data" / "exports" / "qgis" / "land_grant_blocks.geojson"
PUBLIC_OUT = ROOT / "docs" / "exhibits" / "assets" / "map" / "land_grant_blocks.geojson"

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
MIN_INTERVAL = 2.0
CLIP_RADIUS_M = 500  # keep street nodes within this radius of the grant centroid
_CONTACT = config.GEOCODE_CONTACT or "no-contact-set"
_UA = f"mariupol-property-seizures/1.0 (+contact: {_CONTACT})"


def _haversine_m(a, b):
    R = 6371000.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dphi = math.radians(b[0] - a[0])
    dl = math.radians(b[1] - a[1])
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def _convex_hull(points):
    """Andrew's monotone chain. points: list of (lat, lon). Returns hull as
    (lat, lon) list, CCW, no repeat of first point."""
    pts = sorted(set(points))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def _overpass_street_nodes(street_query: str, con) -> list[tuple[float, float]]:
    """Fetch all node coordinates of ways named like `street_query` in the
    Mariupol area from Overpass."""
    # area-bounded to Mariupol's bbox to keep the query cheap
    q = f"""
    [out:json][timeout:60];
    way["highway"]["name"~"{street_query}"]
        (47.03,37.42,47.23,37.76);
    (._;>;);
    out geom;
    """
    time.sleep(MIN_INTERVAL)
    r = requests.post(OVERPASS_URL, data={"data": q}, headers={"User-Agent": _UA}, timeout=90)
    r.raise_for_status()
    forensics.capture_source(
        r.content, url=f"{OVERPASS_URL}#{street_query}",
        source_type="overpass_street_geometry",
        title=f"Overpass street geometry: {street_query}",
        description="OSM street way geometry for a land-grant boundary street (block-polygon build)",
        content_type="application/json", http_status=r.status_code, con=con,
    )
    data = r.json()
    nodes = []
    for el in data.get("elements", []):
        if el.get("type") == "way" and "geometry" in el:
            for pt in el["geometry"]:
                nodes.append((pt["lat"], pt["lon"]))
        elif el.get("type") == "node" and "lat" in el:
            nodes.append((el["lat"], el["lon"]))
    return nodes


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    con = forensics.open_state()
    centroid_cache = json.loads(STREET_CACHE.read_text(encoding="utf-8")) if STREET_CACHE.exists() else {}

    rows = [json.loads(l) for l in LAND_ORDERS_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    targets = []
    for r in rows:
        addr = r.get("address_normalized") or r.get("address_raw") or ""
        if "ограничен" in addr.lower():
            streets = _s254.extract_streets(addr)
            if len(streets) >= 3:  # need >=3 streets to hull a block
                targets.append((r, streets))
    log.info("%d street-bounded grants with >=3 resolvable streets", len(targets))

    features = []
    for r, streets in targets:
        # approximate grant location = centroid of the individual street points
        # (reuse scripts/254's cached single-street geocodes where present)
        street_pts = []
        for s in streets:
            prefix, _, name = s.partition(" ")
            p = _s254.geocode_street_with_fallback(prefix, name, centroid_cache, con)
            if p:
                street_pts.append(tuple(p))
        _s254.save_cache(centroid_cache)
        if len(street_pts) < 3:
            log.info("  decree %s: <3 streets located, skipping", r.get("decree_number"))
            continue
        cx = sum(p[0] for p in street_pts) / len(street_pts)
        cy = sum(p[1] for p in street_pts) / len(street_pts)
        center = (cx, cy)

        all_nodes = []
        for s in streets:
            _, _, name = s.partition(" ")
            nom = _s254._to_nominative(name)
            pat = re.escape(name) + ("|" + re.escape(nom) if nom != name else "")
            try:
                nodes = _overpass_street_nodes(pat, con)
            except Exception as e:
                log.warning("  overpass failed for %r: %s", s, e)
                nodes = []
            # keep only nodes near the block centre
            near = [n for n in nodes if _haversine_m(center, n) <= CLIP_RADIUS_M]
            all_nodes.extend(near)

        if len(all_nodes) < 3:
            log.info("  decree %s: only %d clipped street nodes, skipping polygon",
                     r.get("decree_number"), len(all_nodes))
            continue
        hull = _convex_hull(all_nodes)
        if len(hull) < 3:
            continue
        # GeoJSON ring: [lon, lat], closed
        ring = [[round(lon, 6), round(lat, 6)] for lat, lon in hull]
        ring.append(ring[0])
        features.append({
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [ring]},
            "properties": {
                "decree_number": r.get("decree_number"),
                "decree_date": r.get("decree_date"),
                "beneficiary_name": r.get("beneficiary_name"),
                "project_name": r.get("project_name"),
                "boundary_streets": streets,
                "geocode_method": "street_boundary_hull",
                "geocode_confidence": 0.5,
                "note": "Approximate block outline from OSM street geometry — orientation only, not parcel-exact.",
            },
        })
        log.info("  decree %s: hull of %d street nodes (%d vertices)",
                 r.get("decree_number"), len(all_nodes), len(hull))

    fc = {"type": "FeatureCollection", "features": features}
    for out in (QGIS_OUT, PUBLIC_OUT):
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
    log.info("wrote %d block polygons -> %s (+ public copy)", len(features), QGIS_OUT)
    print(f"land_grant_blocks: {len(features)}/{len(targets)} street-bounded grants -> approximate block polygons")


if __name__ == "__main__":
    main()
