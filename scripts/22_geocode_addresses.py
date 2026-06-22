#!/usr/bin/env python3
"""Stage 4b (geocoding): resolve address_registry.jsonl buildings to WGS84
points via OpenStreetMap Nominatim.

Tier A of two-tier geocoding. Tier B (Rosreestr PKK cadastral-number lookup
for dnr_land_orders.jsonl parcels) is a separate, VPS-routed follow-up -- not
this script.

For each unique building, tries the query variants from
address_registry.jsonl in order (prewar Ukrainian name first, then the
occupation-era Russian name; house-number form before street-only form),
stops at the first house-level match, and otherwise keeps the
highest-confidence result seen. ЕИСЖС rows that already carry coordinates
(from наш.дом.рф) pass straight through with confidence 1.0.

Resumable + cached: every unique query string is forensically captured once
(SHA-256 + source_document row, source_type=nominatim_geocode) and cached in
data/parsed/.geocode_cache.json, so reruns after extending the registry don't
re-query already-resolved buildings.

Nominatim usage policy: max 1 request/second, identifying User-Agent. Set
GEOCODE_CONTACT in .env (an email or project URL); Nominatim may otherwise
rate-limit or block requests.

Output: data/parsed/geocoded_buildings.jsonl

Run locally, no VPS needed (openstreetmap.org is not geoblocked):
  python3 scripts/22_geocode_addresses.py
Expect ~1-1.5s per live query; a few thousand unique buildings -> 30-60 min.
Safe to Ctrl-C and rerun -- the cache picks up where it left off.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402
from mariupol_seizures import forensics  # noqa: E402

log = logging.getLogger(__name__)

PARSED_DIR = config.PROJECT_ROOT / "data" / "parsed"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
MIN_INTERVAL = 1.1  # seconds; Nominatim policy = max 1 req/s

_CONTACT = config.GEOCODE_CONTACT or "no-contact-set"
_USER_AGENT = f"mariupol-property-seizures/1.0 (+contact: {_CONTACT})"

_HOUSE_TYPES = {"building", "house", "apartments", "residential", "yes"}
_STREET_TYPES = {"road", "highway", "residential_road", "street", "tertiary",
                 "secondary", "primary", "unclassified"}


def _load_cache(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _save_cache(path: Path, cache: dict) -> None:
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")


def _query_nominatim(q: str, con) -> list[dict] | None:
    params = {"q": q, "format": "jsonv2", "addressdetails": 1, "limit": 3,
              "countrycodes": "ua"}
    headers = {"User-Agent": _USER_AGENT, "Accept-Language": "uk,ru;q=0.8"}
    for attempt in range(1, 3):
        try:
            r = requests.get(NOMINATIM_URL, params=params, headers=headers,
                             timeout=config.TIMEOUT)
            r.raise_for_status()
            forensics.capture_source(
                r.content, url=r.url, source_type="nominatim_geocode",
                title=f"Nominatim search: {q}",
                description="OSM Nominatim geocoding result for address registry building",
                content_type="application/json", http_status=r.status_code, con=con,
            )
            return r.json()
        except (requests.RequestException, ValueError) as e:
            log.warning("Nominatim query failed (attempt %d/2) for %r: %s", attempt, q, e)
            time.sleep(2)
    return None


def _house_matches(requested: str, returned: str | None) -> bool:
    if not returned:
        return False
    # Occupation-era sources use "-" for combined-building numbers (e.g.
    # "40-42"); OSM/Nominatim uses "/" (e.g. "40/42"). Normalize both to "/"
    # and compare as sets so either side matching any part counts as a match.
    a = requested.strip().lower().replace(" ", "").replace("-", "/")
    b = returned.strip().lower().replace(" ", "").replace("-", "/")
    if a == b:
        return True
    return bool(set(a.split("/")) & set(b.split("/")))


def _score_result(row: dict, house_no: str | None) -> tuple[float, dict]:
    addr = row.get("address") or {}
    house = addr.get("house_number")
    rtype = row.get("addresstype") or row.get("type")
    if house_no and _house_matches(house_no, house):
        return 0.9, {"matched_house_number": True, "osm_addresstype": rtype}
    if rtype in _HOUSE_TYPES:
        return 0.7, {"matched_house_number": False, "osm_addresstype": rtype}
    if rtype in _STREET_TYPES:
        return 0.5, {"matched_house_number": False, "osm_addresstype": rtype}
    return 0.3, {"matched_house_number": False, "osm_addresstype": rtype}


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(message)s")
    if not config.GEOCODE_CONTACT:
        log.warning("GEOCODE_CONTACT not set in .env -- Nominatim may rate-limit "
                    "or block requests with no contact info in the User-Agent.")

    reg_path = PARSED_DIR / "address_registry.jsonl"
    if not reg_path.exists():
        log.error("%s not found -- run scripts/21_build_address_registry.py first", reg_path)
        sys.exit(1)

    cache_path = PARSED_DIR / ".geocode_cache.json"
    cache = _load_cache(cache_path)
    con = forensics.open_state()

    rows = [json.loads(l) for l in reg_path.read_text(encoding="utf-8").splitlines()
            if l.strip()]
    out_path = PARSED_DIR / "geocoded_buildings.jsonl"
    results: list[dict] = []

    try:
        _geocode_all(rows, results, cache, con)
    except KeyboardInterrupt:
        log.warning("interrupted -- saving cache and partial results so far")
    finally:
        _save_cache(cache_path, cache)
        with out_path.open("w", encoding="utf-8") as fh:
            for r in results:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        log.info("Wrote %d/%d buildings -> %s", len(results), len(rows), out_path)

    by_conf: dict[float, int] = {}
    for r in results:
        by_conf[r["geocode_confidence"]] = by_conf.get(r["geocode_confidence"], 0) + 1
    for conf, n in sorted(by_conf.items(), reverse=True):
        log.info("  confidence %.1f: %d", conf, n)


def _geocode_all(rows: list[dict], results: list[dict], cache: dict, con) -> None:
    cache_path = PARSED_DIR / ".geocode_cache.json"
    n_queried = 0
    for row in rows:
        bk = row["building_key"]
        if row.get("already_geocoded"):
            g = row["already_geocoded"]
            results.append({
                "building_key": bk, "lat": g["lat"], "lon": g["lon"],
                "geocode_confidence": 1.0, "geocode_source": g["source"],
                "query_used": None, "variant_index": None,
            })
            continue

        house_no = row.get("house_no")
        best = None
        for i, q in enumerate(row.get("geocode_query_variants", [])):
            if q in cache:
                payload = cache[q]
            else:
                payload = _query_nominatim(q, con)
                n_queried += 1
                time.sleep(MIN_INTERVAL)
                if payload is not None:
                    # Cache successes only -- a None means both fetch attempts
                    # failed (transient), so retry it on the next run.
                    cache[q] = payload
            if not payload:
                continue
            top = payload[0]
            conf, extra = _score_result(top, house_no)
            cand = {
                "building_key": bk, "lat": float(top["lat"]), "lon": float(top["lon"]),
                "geocode_confidence": conf, "geocode_source": "nominatim",
                "query_used": q, "variant_index": i,
                "osm_place_id": top.get("place_id"), "osm_class": top.get("class"),
                "display_name": top.get("display_name"), **extra,
            }
            if best is None or cand["geocode_confidence"] > best["geocode_confidence"]:
                best = cand
            if conf >= 0.9:
                break

        if best is None:
            best = {"building_key": bk, "lat": None, "lon": None,
                    "geocode_confidence": 0.0, "geocode_source": "nominatim",
                    "query_used": None, "variant_index": None,
                    "geocode_failed": True}
        results.append(best)

        if n_queried and n_queried % 25 == 0:
            _save_cache(cache_path, cache)
            log.info("  ... %d/%d buildings, %d live queries so far",
                     len(results), len(rows), n_queried)

    log.info("Live Nominatim queries this run: %d", n_queried)


if __name__ == "__main__":
    main()
