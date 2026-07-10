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
from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402
from mariupol_seizures.normalize import toponym  # noqa: E402
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

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
MIN_INTERVAL = 5.0
MAX_RETRIES = 6
CLIP_RADIUS_M = 500  # keep street nodes within this radius of the grant centroid
_CONTACT = config.GEOCODE_CONTACT or "no-contact-set"
_UA = f"mariupol-property-seizures/1.0 (+contact: {_CONTACT})"
NODE_CACHE = ROOT / "data" / "parsed" / ".overpass_street_nodes_cache.json"
GOOGLE_STREET_CACHE = ROOT / "data" / "parsed" / ".google_street_bounds_cache.json"
GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


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


_last_request_ts = 0.0


def _fetch_all_mariupol_highways(con) -> list[dict]:
    """Fetch every named highway way in the Mariupol bbox in ONE Overpass
    query, cached to disk. Per-street regex queries against the public
    instance were timing out (504) / getting rate-limited (429) under load —
    one broad query is cheaper server-side than N narrow ones and only needs
    to succeed once per machine."""
    if NODE_CACHE.exists():
        cached = json.loads(NODE_CACHE.read_text(encoding="utf-8"))
        # guard against a stale cache in the old per-street dict format
        if isinstance(cached, list) and (not cached or isinstance(cached[0], dict)):
            return cached
        log.warning("  ignoring stale/incompatible cache at %s, re-fetching", NODE_CACHE)

    q = """
    [out:json][timeout:180];
    way["highway"]["name"]
        (47.03,37.42,47.23,37.76);
    out geom;
    """
    last_exc = None
    for attempt in range(MAX_RETRIES):
        url = OVERPASS_URLS[attempt % len(OVERPASS_URLS)]
        wait = max(0.0, MIN_INTERVAL - (time.monotonic() - _last_request_ts))
        if wait:
            time.sleep(wait)
        try:
            log.info("  fetching all Mariupol-area named highways from %s (attempt %d/%d)...",
                      url, attempt + 1, MAX_RETRIES)
            r = requests.post(url, data={"data": q}, headers={"User-Agent": _UA}, timeout=200)
            globals()["_last_request_ts"] = time.monotonic()
            if r.status_code in (429, 504, 502, 503):
                backoff = min(90, 10 * (2 ** attempt))
                log.warning("  %s on %s, retrying in %ds", r.status_code, url, backoff)
                time.sleep(backoff)
                continue
            r.raise_for_status()
        except requests.RequestException as e:
            last_exc = e
            backoff = min(90, 10 * (2 ** attempt))
            log.warning("  overpass error on %s: %s, retrying in %ds", url, e, backoff)
            time.sleep(backoff)
            continue

        forensics.capture_source(
            r.content, url=f"{url}#mariupol_highways",
            source_type="overpass_street_geometry",
            title="Overpass street geometry: all named Mariupol-area highways",
            description="OSM highway way geometry for the Mariupol bbox (land-grant block-polygon build)",
            content_type="application/json", http_status=r.status_code, con=con,
        )
        data = r.json()
        ways = []
        for el in data.get("elements", []):
            if el.get("type") == "way" and "geometry" in el and el.get("tags", {}).get("name"):
                ways.append({
                    "name": el["tags"]["name"],
                    "nodes": [(pt["lat"], pt["lon"]) for pt in el["geometry"]],
                })
        NODE_CACHE.write_text(json.dumps(ways, ensure_ascii=False), encoding="utf-8")
        log.info("  fetched %d named highway ways", len(ways))
        return ways

    log.error("  giving up on highway fetch after %d attempts: %s", MAX_RETRIES, last_exc)
    return []


FUZZY_THRESHOLD = 78


def _street_nodes_matching(pattern: str, ways: list[dict]) -> list[tuple[float, float]]:
    rx = re.compile(pattern, re.IGNORECASE)
    nodes = []
    for w in ways:
        if rx.search(w["name"]):
            nodes.extend(tuple(p) for p in w["nodes"])
    return nodes


def _resolve_osm_nodes_for_street(street_name: str, ways: list[dict], way_names: list[str]) -> list[tuple[float, float]]:
    """Occupation-era decrees name streets by their Russian/Soviet name;
    Mariupol OSM still carries the pre-war Ukrainian toponym (either a
    genuinely different decommunized name, e.g. "проспект Ленина" -> "просп.
    Миру", or just a Ukrainian-orthography spelling of the same root, e.g.
    "Металлургов" -> "Металургів"). Try, in order: (1) exact substring match
    on the raw name (rare but cheap), (2) the project's curated
    occupation->prewar crosswalk (data/toponyms.csv) for actually-renamed
    streets, (3) fuzzy match against all OSM way names for same-root
    Ukrainian-orthography spellings."""
    exact = _street_nodes_matching(re.escape(street_name), ways)
    if exact:
        return exact

    hit = toponym.normalize_address(f"{street_name}, 1")
    if hit.get("prewar_name"):
        exact = _street_nodes_matching(re.escape(hit["prewar_name"].split(" ", 1)[-1]), ways)
        if exact:
            return exact

    best_score, best_name = 0.0, None
    for name in way_names:
        score = fuzz.token_sort_ratio(street_name, name)
        if score > best_score:
            best_score, best_name = score, name
    if best_name and best_score >= FUZZY_THRESHOLD:
        log.info("  fuzzy-matched %r -> OSM %r (score %.0f)", street_name, best_name, best_score)
        return [tuple(p) for w in ways if w["name"] == best_name for p in w["nodes"]]
    return []


def _google_street_corner_nodes(street_name: str, con, cache: dict) -> list[tuple[float, float]]:
    """Fallback when OSM has no geometry for a street: geocode it via Google
    (already configured, GOOGLE_MAPS_API_KEY in .env) and use its viewport/
    bounds corners as pseudo street-extent points for the hull. Coarser than
    real way geometry but keeps the block roughly bounded instead of dropping
    the grant entirely."""
    if street_name in cache:
        return [tuple(p) for p in cache[street_name]]
    if not config.GOOGLE_MAPS_API_KEY:
        return []
    params = {
        "address": f"{street_name}, Мариуполь",
        "key": config.GOOGLE_MAPS_API_KEY,
        "region": "ua",
        "language": "ru",
    }
    try:
        r = requests.get(GOOGLE_GEOCODE_URL, params=params, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        log.warning("  google geocode failed for %r: %s", street_name, e)
        return []
    forensics.capture_source(
        r.content, url=f"{GOOGLE_GEOCODE_URL}?address={street_name}",
        source_type="google_geocode_street_bounds",
        title=f"Google geocode street bounds: {street_name}",
        description="Google Geocoding API viewport/bounds for a land-grant boundary street (Overpass fallback)",
        content_type="application/json", http_status=r.status_code, con=con,
    )
    data = r.json()
    results = data.get("results") or []
    nodes = []
    if results:
        geom = results[0].get("geometry", {})
        vp = geom.get("bounds") or geom.get("viewport")
        if vp:
            ne, sw = vp["northeast"], vp["southwest"]
            nodes = [
                (ne["lat"], ne["lng"]), (sw["lat"], sw["lng"]),
                (ne["lat"], sw["lng"]), (sw["lat"], ne["lng"]),
            ]
    cache[street_name] = nodes
    GOOGLE_STREET_CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    return nodes


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    con = forensics.open_state()
    centroid_cache = json.loads(STREET_CACHE.read_text(encoding="utf-8")) if STREET_CACHE.exists() else {}
    google_cache = json.loads(GOOGLE_STREET_CACHE.read_text(encoding="utf-8")) if GOOGLE_STREET_CACHE.exists() else {}
    ways = _fetch_all_mariupol_highways(con)
    way_names = sorted(set(w["name"] for w in ways))

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

        street_nodes = []  # list of (unclipped_nodes) per street, reused across radius attempts
        for s in streets:
            nodes = _resolve_osm_nodes_for_street(s, ways, way_names)
            if not nodes:
                _, _, name = s.partition(" ")
                nodes = _google_street_corner_nodes(name, con, google_cache)
                if nodes:
                    log.info("  %r: no OSM/toponym match, used Google bounds fallback", s)
            street_nodes.append((s, nodes))

        total_unclipped = sum(len(n) for _, n in street_nodes)
        # The centroid of individually-geocoded street anchor points can be
        # off-center for long avenues (e.g. проспект Ленина spans the whole
        # city), which under a fixed clip radius silently drops all of that
        # street's nodes. Escalate the radius rather than guessing one value.
        all_nodes = []
        for radius in (CLIP_RADIUS_M, CLIP_RADIUS_M * 2, CLIP_RADIUS_M * 4):
            all_nodes = [n for _, nodes in street_nodes for n in nodes if _haversine_m(center, n) <= radius]
            if len(all_nodes) >= 3:
                if radius != CLIP_RADIUS_M:
                    log.info("  decree %s: needed radius %dm (%d/%d nodes within)",
                             r.get("decree_number"), radius, len(all_nodes), total_unclipped)
                break

        if len(all_nodes) < 3:
            log.info("  decree %s: only %d clipped street nodes (of %d total across streets), skipping polygon",
                     r.get("decree_number"), len(all_nodes), total_unclipped)
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
