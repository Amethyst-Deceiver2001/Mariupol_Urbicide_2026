#!/usr/bin/env python3
"""Geocode DNR land-allocation orders (data/parsed/dnr_land_orders.jsonl) for
a "Land grants for redevelopment" point layer in QGIS.

Cadastral-parcel polygon outlines were attempted first (Rosreestr PKK /
nspd.gov.ru), but both block datacenter/VPS IP ranges at the TLS/TCP level
regardless of proxy or fingerprint -- not viable. This falls back to
approximate points: geocode each decree's address text via OpenStreetMap
Nominatim (same as scripts/22_geocode_addresses.py, not geoblocked).

Many decree addresses are vague ("квартал между ул...", "территория,
ограниченная улицами..."), so most results will be street- or area-level
(confidence 0.5), not house-level. Records that don't geocode at all are
skipped and counted.

Run locally, no VPS needed:
  .venv312/bin/python scripts/68_geocode_land_order_grants.py

Output:
  data/exports/qgis/land_order_grants.geojson
  data/exports/qgis/land_order_grants.gpkg  (layer "land_order_grants")

Resumable: queries are cached in data/parsed/.land_order_geocode_cache.json
and forensically captured (SHA-256 + source_document, source_type=
nominatim_geocode), same as scripts/22.
"""
from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger("fetch_land_order_grants")

LAND_ORDERS_PATH = config.DATA_DIR / "parsed" / "dnr_land_orders.jsonl"
CACHE_PATH = config.DATA_DIR / "parsed" / ".land_order_geocode_cache.json"
OUT_DIR = config.PROJECT_ROOT / "data" / "exports" / "qgis"
GEOJSON_PATH = OUT_DIR / "land_order_grants.geojson"
GPKG_PATH = OUT_DIR / "land_order_grants.gpkg"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
MIN_INTERVAL = 1.1  # Nominatim policy: max 1 req/s

_CONTACT = config.GEOCODE_CONTACT or "no-contact-set"
_USER_AGENT = f"mariupol-property-seizures/1.0 (+contact: {_CONTACT})"

_HOUSE_TYPES = {"building", "house", "apartments", "residential", "yes"}
_STREET_TYPES = {"road", "highway", "residential_road", "street", "tertiary",
                 "secondary", "primary", "unclassified"}

# Vague decree address text starts with these -- not geocodable as-is, but
# often contains a recognizable street further in (extracted below).
_STREET_RE = re.compile(
    r"(улиц[аы]|проспект|бульвар|переулок|площадь)\s+[^,]+", re.IGNORECASE)


def _load_cache() -> dict:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {}


def _save_cache(cache: dict) -> None:
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")


def _query_nominatim(q: str, con) -> list[dict] | None:
    params = {"q": q, "format": "jsonv2", "addressdetails": 1, "limit": 3,
              "countrycodes": "ua"}
    headers = {"User-Agent": _USER_AGENT, "Accept-Language": "uk,ru;q=0.8"}
    for attempt in range(1, 3):
        try:
            r = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=config.TIMEOUT)
            r.raise_for_status()
            forensics.capture_source(
                r.content, url=r.url, source_type="nominatim_geocode",
                title=f"Nominatim search: {q}",
                description="OSM Nominatim geocoding result for a DNR land-allocation order",
                content_type="application/json", http_status=r.status_code, con=con,
            )
            return r.json()
        except (requests.RequestException, ValueError) as e:
            log.warning("Nominatim query failed (attempt %d/2) for %r: %s", attempt, q, e)
            time.sleep(2)
    return None


def _score(row: dict) -> tuple[float, str | None]:
    addr = row.get("address") or {}
    rtype = row.get("addresstype") or row.get("type")
    if addr.get("house_number") and rtype in _HOUSE_TYPES:
        return 0.7, rtype
    if rtype in _STREET_TYPES:
        return 0.5, rtype
    return 0.3, rtype


def _build_queries(address_normalized: str | None) -> list[str]:
    """Best-first list of query strings to try for a decree's address text."""
    queries = []
    addr = (address_normalized or "").strip()
    if addr:
        queries.append(f"{addr}, Мариуполь")
        m = _STREET_RE.search(addr)
        if m:
            queries.append(f"{m.group(0).strip()}, Мариуполь")
    queries.append("Мариуполь")  # last resort: city centroid, confidence 0.1
    return queries


def geocode(record: dict, cache: dict, con) -> dict | None:
    addr = record.get("address_normalized")
    for i, q in enumerate(_build_queries(addr)):
        is_fallback_city = (i == len(_build_queries(addr)) - 1) and q == "Мариуполь" and addr
        if q in cache:
            results = cache[q]
        else:
            results = _query_nominatim(q, con)
            time.sleep(MIN_INTERVAL)
            cache[q] = results or []
            _save_cache(cache)
        if not results:
            continue
        row = results[0]
        conf, osm_type = _score(row)
        if is_fallback_city:
            conf = 0.1
        return {
            "lon": float(row["lon"]), "lat": float(row["lat"]),
            "geocode_query": q, "geocode_confidence": conf, "osm_addresstype": osm_type,
        }
    return None


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not config.GEOCODE_CONTACT:
        log.warning("GEOCODE_CONTACT not set in .env -- Nominatim may rate-limit "
                    "or block requests with no contact info in the User-Agent.")

    if not LAND_ORDERS_PATH.exists():
        raise SystemExit(f"{LAND_ORDERS_PATH} not found -- run scripts/11_parse_dnr_land_orders.py first")

    cache = _load_cache()
    con = forensics.open_state()

    records = [json.loads(l) for l in LAND_ORDERS_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    log.info("loaded %d land-order records from %s", len(records), LAND_ORDERS_PATH)

    features = []
    n_geocoded = n_skipped = 0
    for i, rec in enumerate(records):
        log.info("[%d/%d] decree %s (%s)", i + 1, len(records), rec.get("decree_number"), rec.get("decree_date"))
        geo = geocode(rec, cache, con)
        if geo is None:
            n_skipped += 1
            continue
        n_geocoded += 1
        properties = {
            "decree_number": rec.get("decree_number"),
            "decree_date": rec.get("decree_date"),
            "issuing_body": rec.get("issuing_body"),
            "beneficiary_name": rec.get("beneficiary_name"),
            "project_name": rec.get("project_name"),
            "address_normalized": rec.get("address_normalized"),
            "address_raw": rec.get("address_raw"),
            "cadastral_numbers": "+".join(rec.get("cadastral_numbers") or []) or None,
            "area_sqm": rec.get("area_sqm"),
            "geocode_query": geo["geocode_query"],
            "geocode_confidence": geo["geocode_confidence"],
            "osm_addresstype": geo["osm_addresstype"],
        }
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [geo["lon"], geo["lat"]]},
            "properties": properties,
        })

    geojson = {"type": "FeatureCollection", "features": features}
    GEOJSON_PATH.write_text(json.dumps(geojson, ensure_ascii=False), encoding="utf-8")
    log.info("wrote %s (%d geocoded, %d skipped)", GEOJSON_PATH, n_geocoded, n_skipped)

    if features:
        if GPKG_PATH.exists():
            GPKG_PATH.unlink()
        subprocess.run(
            ["ogr2ogr", "-f", "GPKG", str(GPKG_PATH), str(GEOJSON_PATH),
             "-nln", "land_order_grants", "-nlt", "PROMOTE_TO_MULTI"],
            check=True,
        )
        log.info("wrote %s", GPKG_PATH)

    print(f"fetch_land_order_grants: {n_geocoded} geocoded ({len(records)} total records, {n_skipped} skipped)")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    main()
