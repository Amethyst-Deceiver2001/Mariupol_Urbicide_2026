#!/usr/bin/env python3
"""Stage 4c (geocoding fallback): Tier A2 -- resolve remaining sub-claim-grade
buildings against a local index of OSM addr:housenumber/addr:street tags for
Mariupol, fetched once via the Overpass API.

Why: scripts/21+22 (Tier A, Nominatim free-text search) leave a residue of
buildings where Nominatim's *search ranking* returns only a street/road-level
result (confidence 0.5) or nothing (0.0), even though the underlying OSM data
may carry a node/way with addr:housenumber + addr:street tags for that exact
building -- search ranking and raw tag presence are not the same thing. This
script fetches every addr-tagged element in a bounding box around Mariupol in
ONE Overpass query, builds a local street-key -> house-number -> coordinate
index, and does a direct tag lookup (no search ranking involved) for every
building still below claim-grade (geocode_confidence < 0.9).

Matching:
  Pass 1 (exact):  toponym._toponym_match_key(candidate_street_name) ==
                    toponym._toponym_match_key(addr:street) AND house numbers
                    match (same "-"/"/" combined-number normalization as
                    scripts/22's _house_matches) -> confidence 0.9,
                    geocode_source="overpass_osm_tags".
  Pass 2 (fuzzy):  same street CLASS, rapidfuzz.fuzz.ratio >= 90 on the
                    folded stem, AND house numbers match -> confidence 0.8
                    (the CLAUDE.md claim-grade floor), geocode_source=
                    "overpass_osm_tags_fuzzy", with fuzzy_ratio recorded for
                    audit.
Candidates tried per building, in the same priority order as
geocode_query_variants: prewar_name, street_alt_canonical, street_canonical,
street_occupation.

Rows already >= 0.9 pass through unchanged. Rows with no match pass through
unchanged (still candidates for Tier B / manual review).

Output: overwrites data/parsed/geocoded_buildings.jsonl in place, preserving
every existing field and adding `previous_geocode` (the prior lat/lon/
confidence/source) on any row this script upgrades.

Area: the query is constrained to data/boundaries/mariupol_hromada_boundary.geojson
(Overpass `poly:` filter on the polygon's vertices), not a hand-drawn bbox --
override with --boundary if the file moves. Falls back to a hand-eyeballed
bbox if the boundary file is missing.

Forensics: the Overpass response is captured (SHA-256 + sidecar,
source_type=overpass_addr_index) and cached in
data/parsed/.overpass_cache.json (keyed to a hash of the area filter, so a
changed boundary file triggers a re-fetch automatically); pass --refresh to
force one regardless.

Run locally, no VPS needed (overpass-api.de is not geoblocked):
  python3 scripts/23_geocode_overpass.py
Single Overpass query (~1-2 min); matching against ~2000 buildings is
near-instant.
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402
from mariupol_seizures.normalize.toponym import _CLASS_UNKNOWN, _toponym_match_key  # noqa: E402

try:
    from rapidfuzz import fuzz, process as rf_process
except ImportError:
    sys.exit("rapidfuzz not installed — run: .venv/bin/pip install rapidfuzz")

log = logging.getLogger(__name__)

PARSED_DIR = config.PROJECT_ROOT / "data" / "parsed"

_CONTACT = config.GEOCODE_CONTACT or "no-contact-set"
_USER_AGENT = f"mariupol-property-seizures/1.0 (+contact: {_CONTACT})"

_OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

DEFAULT_BOUNDARY = config.PROJECT_ROOT / "data" / "boundaries" / "mariupol_hromada_boundary.geojson"

# Fallback bounding box (south, west, north, east), used only if the
# boundary GeoJSON is missing -- a hand-eyeballed box covering greater
# Mariupol with margin.
_FALLBACK_BBOX = (47.05, 37.42, 47.20, 37.65)

_QUERY_TEMPLATE = """
[out:json][timeout:180];
(
  node["addr:housenumber"]["addr:street"]({area});
  way["addr:housenumber"]["addr:street"]({area});
  relation["addr:housenumber"]["addr:street"]({area});
);
out center tags;
""".strip()

_FUZZY_THRESHOLD = 90


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _area_filter(boundary_path: Path) -> str:
    """Build the Overpass spatial filter: poly:"lat lon lat lon ..." from the
    first polygon ring in `boundary_path`, or a fallback bbox filter if the
    file doesn't exist."""
    if not boundary_path.exists():
        log.warning("Boundary file %s not found -- using fallback bbox %s",
                     boundary_path, _FALLBACK_BBOX)
        s, w, n, e = _FALLBACK_BBOX
        return f"{s},{w},{n},{e}"

    geojson = json.loads(boundary_path.read_text(encoding="utf-8"))
    features = geojson.get("features", [geojson])
    geom = features[0].get("geometry", features[0])
    ring = geom["coordinates"][0]
    # GeoJSON rings are [lon, lat] and closed (first == last); Overpass poly:
    # wants "lat lon lat lon ..." and doesn't need the closing duplicate.
    if ring[0] == ring[-1]:
        ring = ring[:-1]
    pts = " ".join(f"{lat:.7f} {lon:.7f}" for lon, lat in ring)
    return f'poly:"{pts}"'


def _house_matches(requested: str, returned: str | None) -> bool:
    """Same normalization as scripts/22._house_matches: occupation-era
    sources use "-" for combined-building numbers (e.g. "40-42"); OSM uses
    "/" (e.g. "40/42"). Normalize both to "/" and compare as sets."""
    if not returned:
        return False
    a = requested.strip().lower().replace(" ", "").replace("-", "/")
    b = returned.strip().lower().replace(" ", "").replace("-", "/")
    if a == b:
        return True
    return bool(set(a.split("/")) & set(b.split("/")))


def _fetch_osm_elements(con, boundary_path: Path, refresh: bool) -> list[dict]:
    area = _area_filter(boundary_path)
    area_sha = forensics.sha256_bytes(area.encode("utf-8"))
    query = _QUERY_TEMPLATE.format(area=area)

    cache_path = PARSED_DIR / ".overpass_cache.json"
    if cache_path.exists() and not refresh:
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        if cached.get("area_sha256") == area_sha:
            log.info("Using cached Overpass response: %s (pass --refresh to re-fetch)", cache_path)
            return cached["elements"]
        log.info("Boundary/area filter changed since last cache -- re-fetching")

    headers = {"User-Agent": _USER_AGENT}
    last_err: Exception | None = None
    for endpoint in _OVERPASS_ENDPOINTS:
        for attempt in range(1, 3):
            try:
                log.info("Querying %s (attempt %d/2)...", endpoint, attempt)
                r = requests.post(endpoint, data={"data": query}, headers=headers, timeout=200)
                r.raise_for_status()
                forensics.capture_source(
                    r.content, url=r.url, source_type="overpass_addr_index",
                    title="Overpass addr:housenumber/addr:street index for Mariupol hromada",
                    description=f"Overpass QL query, area filter from {boundary_path.name}",
                    content_type="application/json", http_status=r.status_code, con=con,
                )
                payload = r.json()
                cache_path.write_text(
                    json.dumps({"area_sha256": area_sha, "elements": payload["elements"]},
                               ensure_ascii=False),
                    encoding="utf-8",
                )
                log.info("Fetched %d elements", len(payload.get("elements", [])))
                return payload["elements"]
            except (requests.RequestException, ValueError) as e:
                last_err = e
                log.warning("Overpass query failed (%s, attempt %d/2): %s", endpoint, attempt, e)
                time.sleep(5 * attempt)
    log.error("All Overpass endpoints failed: %s", last_err)
    sys.exit(1)


def _build_osm_index(elements: list[dict]) -> dict[str, list[dict]]:
    """Map toponym._toponym_match_key(addr:street) -> [{house_no, lat, lon, osm_type, osm_id}, ...]."""
    index: dict[str, list[dict]] = defaultdict(list)
    skipped_no_coord = 0
    for el in elements:
        tags = el.get("tags") or {}
        street = tags.get("addr:street")
        house = tags.get("addr:housenumber")
        if not street or not house:
            continue
        if el.get("type") == "node":
            lat, lon = el.get("lat"), el.get("lon")
        else:
            center = el.get("center") or {}
            lat, lon = center.get("lat"), center.get("lon")
        if lat is None or lon is None:
            skipped_no_coord += 1
            continue
        key = _toponym_match_key(street)
        index[key].append({
            "house_no": house, "lat": lat, "lon": lon,
            "osm_type": el.get("type"), "osm_id": el.get("id"),
        })
    if skipped_no_coord:
        log.warning("Skipped %d addr-tagged elements with no coordinates", skipped_no_coord)
    return dict(index)


def _candidate_keys(reg_row: dict) -> list[str]:
    """Street-name candidates to look up, in the same priority order as
    geocode_query_variants: prewar Ukrainian name first (OSM is mapped mostly
    in Ukrainian), then the alt-name annotation, then the occupation-era
    canonical/raw name. Deduplicated by _toponym_match_key()."""
    names = [
        reg_row.get("prewar_name"),
        reg_row.get("street_alt_canonical"),
        reg_row.get("street_canonical"),
        reg_row.get("street_occupation"),
    ]
    seen: set[str] = set()
    keys: list[str] = []
    for name in names:
        if not name:
            continue
        k = _toponym_match_key(name)
        if k not in seen:
            seen.add(k)
            keys.append(k)
    return keys


def _house_exact(requested: str, returned: str | None) -> bool:
    """Stricter than _house_matches: full-string equality after normalizing
    "-"/"/" for combined-building numbers, no set-intersection. Used for the
    fuzzy street-name pass, where _house_matches' set-intersection (e.g.
    "40-1" vs "26/1" sharing the trailing "1") would compound an already
    uncertain street match into a false positive on a different building."""
    if not returned:
        return False
    a = requested.strip().lower().replace(" ", "").replace("-", "/")
    b = returned.strip().lower().replace(" ", "").replace("-", "/")
    return a == b


def _digits(s: str) -> set[str]:
    return set(re.findall(r"\d+", s))


def _match_osm(reg_row: dict, osm_index: dict[str, list[dict]]) -> dict | None:
    house_no = reg_row.get("house_no")
    if not house_no:
        return None
    candidates = _candidate_keys(reg_row)

    # Pass 1: exact key match (class + folded stem).
    for key in candidates:
        for entry in osm_index.get(key, []):
            if _house_matches(house_no, entry["house_no"]):
                return {
                    "lat": entry["lat"], "lon": entry["lon"],
                    "confidence": 0.9, "source": "overpass_osm_tags",
                    "osm_type": entry["osm_type"], "osm_id": entry["osm_id"],
                    "matched_key": key, "house_no": entry["house_no"],
                }

    # Pass 2: fuzzy stem match within the same street class.
    for key in candidates:
        cls, _, stem = key.partition(":")
        if cls == _CLASS_UNKNOWN or not stem:
            continue
        same_class = [k for k in osm_index if k.startswith(f"{cls}:")]
        if not same_class:
            continue
        stems = [k.partition(":")[2] for k in same_class]
        best = rf_process.extractOne(stem, stems, scorer=fuzz.ratio, score_cutoff=_FUZZY_THRESHOLD)
        if not best:
            continue
        match_stem, score, idx = best
        # Numeric street names ("50 лет СССР" vs "60 лет СССР", "9 Мая" vs
        # "1 Мая") fuzzy-match each other at >90 ratio despite being
        # different streets -- a digit mismatch always means a different
        # street, regardless of ratio.
        if _digits(stem) != _digits(match_stem):
            continue
        match_key = same_class[idx]
        for entry in osm_index.get(match_key, []):
            if _house_exact(house_no, entry["house_no"]):
                return {
                    "lat": entry["lat"], "lon": entry["lon"],
                    "confidence": 0.8, "source": "overpass_osm_tags_fuzzy",
                    "osm_type": entry["osm_type"], "osm_id": entry["osm_id"],
                    "matched_key": match_key, "house_no": entry["house_no"],
                    "fuzzy_ratio": score,
                }
    return None


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--refresh", action="store_true",
                    help="re-fetch from Overpass even if a cached response exists")
    ap.add_argument("--boundary", type=Path, default=DEFAULT_BOUNDARY,
                    help=f"GeoJSON Polygon to constrain the Overpass query "
                         f"(default: {DEFAULT_BOUNDARY})")
    args = ap.parse_args()

    reg_path = PARSED_DIR / "address_registry.jsonl"
    geo_path = PARSED_DIR / "geocoded_buildings.jsonl"
    if not reg_path.exists() or not geo_path.exists():
        log.error("missing inputs -- run scripts/21 and scripts/22 first")
        sys.exit(1)

    con = forensics.open_state()
    elements = _fetch_osm_elements(con, args.boundary, args.refresh)
    osm_index = _build_osm_index(elements)
    log.info("OSM tag index: %d distinct street keys from %d addr-tagged elements",
             len(osm_index), len(elements))

    registry = {row["building_key"]: row for row in _read_jsonl(reg_path)}
    geocoded = _read_jsonl(geo_path)

    n_exact = 0
    n_fuzzy = 0
    results: list[dict] = []
    for row in geocoded:
        if row["geocode_confidence"] >= 0.9:
            results.append(row)
            continue
        reg_row = registry.get(row["building_key"])
        match = _match_osm(reg_row, osm_index) if reg_row else None
        if not match:
            results.append(row)
            continue
        new_row = dict(row)
        new_row["previous_geocode"] = {
            "lat": row.get("lat"), "lon": row.get("lon"),
            "geocode_confidence": row["geocode_confidence"],
            "geocode_source": row.get("geocode_source"),
        }
        new_row.update({
            "lat": match["lat"], "lon": match["lon"],
            "geocode_confidence": match["confidence"],
            "geocode_source": match["source"],
            "osm_type": match["osm_type"], "osm_id": match["osm_id"],
            "matched_street_key": match["matched_key"],
            "matched_house_number": match["house_no"],
        })
        if "fuzzy_ratio" in match:
            new_row["fuzzy_ratio"] = match["fuzzy_ratio"]
        if match["confidence"] >= 0.9:
            n_exact += 1
        else:
            n_fuzzy += 1
        results.append(new_row)

    with geo_path.open("w", encoding="utf-8") as fh:
        for r in results:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    log.info("Upgraded %d buildings via exact OSM-tag match (-> 0.9)", n_exact)
    log.info("Upgraded %d buildings via fuzzy OSM-tag match (-> 0.8)", n_fuzzy)
    by_conf: dict[float, int] = {}
    for r in results:
        by_conf[r["geocode_confidence"]] = by_conf.get(r["geocode_confidence"], 0) + 1
    for conf, n in sorted(by_conf.items(), reverse=True):
        log.info("  confidence %.1f: %d", conf, n)


if __name__ == "__main__":
    main()
