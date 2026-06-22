#!/usr/bin/env python3
"""Stage 4d (geocoding fallback): Tier A3 -- Google Geocoding API for
buildings still below claim-grade (geocode_confidence < 0.8) after
scripts/22 (Nominatim) and scripts/23 (Overpass OSM-tag index).

For each such building, tries the same geocode_query_variants used by
scripts/22 (prewar name, alt name, occupation-era canonical/raw, each with
house number then street-only), in order, and stops at the first ROOFTOP
result whose address_components street_number matches the requested house
number.

Confidence mapping (Google's geometry.location_type):
  ROOFTOP            + house number matches  -> 0.9
  RANGE_INTERPOLATED + house number matches  -> 0.8 (CLAUDE.md claim-grade
                                                  floor -- interpolated, not
                                                  rooftop)
  ROOFTOP / RANGE_INTERPOLATED, no house match,
  or GEOMETRIC_CENTER                        -> 0.5 (street/area only)
  APPROXIMATE                                -> 0.3
A row is only overwritten if the new confidence is STRICTLY HIGHER than its
current value (never downgrades); previous_geocode is preserved on any row
this script upgrades.

LICENSING NOTE: Google Maps Platform's Terms of Service impose caching/
storage restrictions on geocoding results that are stricter than OSM's ODbL
(already used by scripts/22-23). Rows upgraded here are tagged
geocode_source="google_geocode" so they can be filtered, reviewed, or
re-sourced separately before any public RD4U/court submission.

Setup: create a Google Cloud project, enable the "Geocoding API", create an
API key, and set GOOGLE_MAPS_API_KEY in .env. Check your project's current
Geocoding API pricing/free-tier terms before running on the full backlog --
use --limit to test on a handful first (~282 buildings below claim-grade as
of 2026-06-10; each needs 1-4 queries, with an early break on a confident
match).

Forensics: every Google response is captured (SHA-256 + sidecar,
source_type=google_geocode, with the API key redacted from the logged URL)
and cached in data/parsed/.google_geocode_cache.json (definitive results
only -- OVER_QUERY_LIMIT/transient errors are retried on the next run).

Run:
  .venv/bin/python3 scripts/24_geocode_google.py [--limit N]
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

PARSED_DIR = config.PROJECT_ROOT / "data" / "parsed"
DEFAULT_BOUNDARY = config.PROJECT_ROOT / "data" / "boundaries" / "mariupol_hromada_boundary.geojson"

GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
MIN_INTERVAL = 0.2  # seconds; well under Google's default per-project QPS

_LOCATION_TYPE_SCORE = {
    "ROOFTOP": 0.9,
    "RANGE_INTERPOLATED": 0.8,
    "GEOMETRIC_CENTER": 0.5,
    "APPROXIMATE": 0.3,
}


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _load_cache(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _save_cache(path: Path, cache: dict) -> None:
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")


def _load_boundary_bbox(path: Path) -> tuple[float, float, float, float] | None:
    """Return (south, west, north, east) from the first polygon ring in
    `path`, or None if missing -- bounds is a soft hint to Google, not a
    hard filter, so it's safe to omit."""
    if not path.exists():
        log.warning("Boundary file %s not found -- querying without bounds bias", path)
        return None
    geojson = json.loads(path.read_text(encoding="utf-8"))
    features = geojson.get("features", [geojson])
    geom = features[0].get("geometry", features[0])
    ring = geom["coordinates"][0]
    lons = [pt[0] for pt in ring]
    lats = [pt[1] for pt in ring]
    return min(lats), min(lons), max(lats), max(lons)


def _house_matches(requested: str, returned: str | None) -> bool:
    """Same normalization as scripts/22._house_matches, plus stripping
    trailing punctuation -- some address_registry house_no values carry a
    stray ")" from "н/д (ул. X 36а)"-style raw inputs."""
    if not returned:
        return False
    a = requested.strip().lower().rstrip("()., ").replace(" ", "").replace("-", "/")
    b = returned.strip().lower().rstrip("()., ").replace(" ", "").replace("-", "/")
    if a == b:
        return True
    return bool(set(a.split("/")) & set(b.split("/")))


def _street_number(components: list[dict]) -> str | None:
    for c in components:
        if "street_number" in c.get("types", []):
            return c.get("long_name")
    return None


def _query_google(q: str, bbox: tuple[float, float, float, float] | None, con) -> dict | None:
    params = {"address": q, "key": config.GOOGLE_MAPS_API_KEY, "region": "ua", "language": "ru"}
    if bbox:
        s, w, n, e = bbox
        params["bounds"] = f"{s},{w}|{n},{e}"
    for attempt in range(1, 3):
        try:
            r = requests.get(GOOGLE_GEOCODE_URL, params=params, timeout=config.TIMEOUT)
            r.raise_for_status()
            redacted_url = re.sub(r"key=[^&]+", "key=REDACTED", r.url)
            forensics.capture_source(
                r.content, url=redacted_url, source_type="google_geocode",
                title=f"Google geocode: {q}",
                description="Google Geocoding API result for address registry building",
                content_type="application/json", http_status=r.status_code, con=con,
            )
            payload = r.json()
            status = payload.get("status")
            if status in ("OK", "ZERO_RESULTS"):
                return payload
            if status == "REQUEST_DENIED":
                log.error("Google geocode REQUEST_DENIED: %s -- check GOOGLE_MAPS_API_KEY / "
                          "billing / Geocoding API enablement",
                          payload.get("error_message", ""))
                sys.exit(1)
            if status == "OVER_QUERY_LIMIT":
                log.warning("OVER_QUERY_LIMIT (attempt %d/2) for %r -- backing off", attempt, q)
                time.sleep(5)
                continue
            log.warning("Google geocode status=%s for %r: %s", status, q,
                         payload.get("error_message", ""))
            return None
        except (requests.RequestException, ValueError) as e:
            log.warning("Google geocode request failed (attempt %d/2) for %r: %s", attempt, q, e)
            time.sleep(2)
    return None


def _score_result(result: dict, house_no: str | None) -> tuple[float, dict]:
    loc_type = result.get("geometry", {}).get("location_type")
    house = _street_number(result.get("address_components", []))
    house_match = bool(house_no) and _house_matches(house_no, house)
    conf = _LOCATION_TYPE_SCORE.get(loc_type, 0.3)
    if loc_type in ("ROOFTOP", "RANGE_INTERPOLATED") and not house_match:
        conf = min(conf, 0.5)
    return conf, {
        "location_type": loc_type,
        "matched_house_number": house_match,
        "google_house_number": house,
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=None,
                    help="process at most N buildings (for testing/cost control)")
    ap.add_argument("--boundary", type=Path, default=DEFAULT_BOUNDARY,
                    help=f"GeoJSON Polygon used for bounds bias (default: {DEFAULT_BOUNDARY})")
    args = ap.parse_args()

    if not config.GOOGLE_MAPS_API_KEY:
        log.error("GOOGLE_MAPS_API_KEY not set in .env")
        sys.exit(1)

    reg_path = PARSED_DIR / "address_registry.jsonl"
    geo_path = PARSED_DIR / "geocoded_buildings.jsonl"
    if not reg_path.exists() or not geo_path.exists():
        log.error("missing inputs -- run scripts/21, 22, 23 first")
        sys.exit(1)

    bbox = _load_boundary_bbox(args.boundary)
    registry = {row["building_key"]: row for row in _read_jsonl(reg_path)}
    geocoded = _read_jsonl(geo_path)
    cache_path = PARSED_DIR / ".google_geocode_cache.json"
    cache = _load_cache(cache_path)
    con = forensics.open_state()

    below = [r for r in geocoded if r["geocode_confidence"] < 0.8]
    targets = below[: args.limit] if args.limit else below
    target_keys = {r["building_key"] for r in targets}
    log.info("%d buildings below claim-grade; processing %d%s",
             len(below), len(targets), " (--limit)" if args.limit else "")

    n_queried = 0
    n_upgraded = 0
    # Pre-fill with the original rows (full length, in order) so a fatal
    # error mid-loop (e.g. sys.exit on REQUEST_DENIED) can't truncate the
    # output in the `finally` block -- only entries we actually upgrade get
    # replaced below.
    results: list[dict] = list(geocoded)
    try:
        for idx, row in enumerate(geocoded):
            if row["building_key"] not in target_keys:
                continue
            reg_row = registry.get(row["building_key"])
            house_no = reg_row.get("house_no") if reg_row else None
            best = None
            for i, q in enumerate(reg_row.get("geocode_query_variants", []) if reg_row else []):
                if q in cache:
                    payload = cache[q]
                else:
                    payload = _query_google(q, bbox, con)
                    n_queried += 1
                    time.sleep(MIN_INTERVAL)
                    if payload is not None:
                        cache[q] = payload
                if not payload or payload.get("status") != "OK":
                    continue
                top = payload["results"][0]
                conf, extra = _score_result(top, house_no)
                loc = top["geometry"]["location"]
                cand = {
                    "lat": loc["lat"], "lon": loc["lng"],
                    "geocode_confidence": conf, "geocode_source": "google_geocode",
                    "query_used": q, "variant_index": i,
                    "formatted_address": top.get("formatted_address"), **extra,
                }
                if best is None or cand["geocode_confidence"] > best["geocode_confidence"]:
                    best = cand
                if conf >= 0.9:
                    break

            if best and best["geocode_confidence"] > row["geocode_confidence"]:
                new_row = dict(row)
                new_row["previous_geocode"] = {
                    "lat": row.get("lat"), "lon": row.get("lon"),
                    "geocode_confidence": row["geocode_confidence"],
                    "geocode_source": row.get("geocode_source"),
                }
                new_row.update(best)
                results[idx] = new_row
                n_upgraded += 1

            if n_queried and n_queried % 25 == 0:
                _save_cache(cache_path, cache)
                log.info("  ... %d live queries so far, %d upgraded", n_queried, n_upgraded)
    except KeyboardInterrupt:
        log.warning("interrupted -- saving cache and partial results so far")
    finally:
        _save_cache(cache_path, cache)
        with geo_path.open("w", encoding="utf-8") as fh:
            for r in results:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    log.info("Live Google geocode queries this run: %d -- check this against your "
             "GCP project's current Geocoding API pricing/free-tier terms", n_queried)
    log.info("Upgraded %d buildings", n_upgraded)
    by_conf: dict[float, int] = {}
    for r in results:
        by_conf[r["geocode_confidence"]] = by_conf.get(r["geocode_confidence"], 0) + 1
    for conf, n in sorted(by_conf.items(), reverse=True):
        log.info("  confidence %.1f: %d", conf, n)


if __name__ == "__main__":
    main()
