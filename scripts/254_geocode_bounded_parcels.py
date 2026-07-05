#!/usr/bin/env python3
"""Resolve the "territory bounded by streets X, Y, Z..." land-grant addresses
that scripts/68's whole-string Nominatim query can only fall back to the
Mariupol city centroid for (conf 0.1-0.3, osm_addresstype='city').

These addresses are NOT actually vague -- "территория, ограниченная
проспектом Металлургов, улицей Кальчанской, улицей Артема..." precisely
describes one city block to anyone who knows the street grid (confirmed by
inspection against satellite imagery, 2026-07-05). The generic geocoder just
can't parse a multi-street polygon description as a single query. This
script instead geocodes each named boundary street separately (Nominatim
resolves individual streets fine) and takes their centroid -- a real
approximation of the enclosed block, not a city-wide fallback.

Not parcel-exact (no cadastral polygon source is reachable without a VPS,
per scripts/68's docstring), but a material precision improvement over the
city-centroid fallback for the ~14 records that use this address shape.

Run locally, no VPS needed (same Nominatim endpoint as scripts/22/68):
    .venv312/bin/python scripts/254_geocode_bounded_parcels.py

Output: data/exports/qgis/land_order_grants_bounded_fix.geojson
        (the corrected subset only; merge into land_order_grants.geojson by hand
        or re-run scripts/68 after this lands upstream)
"""
from __future__ import annotations

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

log = logging.getLogger("geocode_bounded_parcels")

LAND_ORDERS_PATH = ROOT / "data" / "parsed" / "dnr_land_orders.jsonl"
CACHE_PATH = ROOT / "data" / "parsed" / ".street_geocode_cache.json"
OUT_PATH = ROOT / "data" / "exports" / "qgis" / "land_order_grants_bounded_fix.geojson"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
MIN_INTERVAL = 1.1
_CONTACT = config.GEOCODE_CONTACT or "no-contact-set"
_USER_AGENT = f"mariupol-property-seizures/1.0 (+contact: {_CONTACT})"

# Matches "территория, ограниченная <streets...>" / "территория ограничена <streets...>"
_BOUNDED_RE = re.compile(r"территория[,]?\s*ограничен\w*\s*:?\s*(.+)", re.I)
_STREET_TOKEN_RE = re.compile(
    r"(проспект(?:ом)?|бульвар(?:ом)?|улиц\w*|переулк?\w*|шоссе)\s+([А-ЯЁ][\w\-]*(?:\s+[А-ЯЁ]?[\w\-]*)?)",
    re.I,
)
_PREFIX_NORM = {
    "проспектом": "проспект", "бульваром": "бульвар", "улицей": "улица",
    "улицы": "улица", "переулком": "переулок",
}


def extract_streets(addr: str) -> list[str]:
    m = _BOUNDED_RE.search(addr)
    if not m:
        return []
    tail = m.group(1)
    out = []
    for pm in _STREET_TOKEN_RE.finditer(tail):
        prefix = pm.group(1).lower()
        prefix = _PREFIX_NORM.get(prefix, prefix)
        name = pm.group(2).strip().rstrip(",")
        # drop trailing junk a greedy match can pick up (next street's connector words)
        name = re.split(r"\s+(?:и|улиц|проспект|бульвар|переулок|шоссе)\b", name, flags=re.I)[0].strip()
        if name and len(name) > 2:
            out.append(f"{prefix} {name}")
    return out


def load_cache() -> dict:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {}


def save_cache(cache: dict) -> None:
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")


def _to_nominative(name: str) -> str:
    """Best-effort instrumental/genitive -> nominative for Russian adjectival
    street names. The decree text declines the street name to agree with the
    preposition ("ограниченная ... улицей Кальчанской"), but Nominatim/OSM
    stores the nominative form ("Кальчанская") -- confirmed empirically: every
    adjectival street name failed to geocode in its declined form (Кальчанской,
    Евпаторийской, Греческой, Митрополитской, Фонтанной, Солнечной, Гранитной,
    Черноморской, Кронштадтской), while name-based streets (Артема, Урицкого,
    which don't decline the same way) resolved fine. Feminine adjectives ending
    -ой/-ей in the declined form end -ая/-яя in the nominative."""
    if name.endswith("ой"):
        return name[:-2] + "ая"
    if name.endswith("ей"):
        return name[:-2] + "яя"
    return name


def geocode_street(query: str, cache: dict, sqlite_con) -> tuple[float, float] | None:
    if query in cache:
        return cache[query]
    time.sleep(MIN_INTERVAL)
    params = {"q": f"{query}, Мариуполь", "format": "jsonv2", "limit": 1}
    r = requests.get(NOMINATIM_URL, params=params, headers={"User-Agent": _USER_AGENT}, timeout=15)
    r.raise_for_status()
    results = r.json()
    forensics.capture_source(
        r.content, url=r.url, source_type="nominatim_geocode_street",
        title=f"Nominatim search: {query}",
        description="OSM Nominatim geocoding result for a land-grant boundary street",
        content_type="application/json", http_status=r.status_code, con=sqlite_con,
    )
    if not results:
        cache[query] = None
        return None
    lat, lon = float(results[0]["lat"]), float(results[0]["lon"])
    cache[query] = [lat, lon]
    return lat, lon


def geocode_street_with_fallback(prefix: str, name: str, cache: dict, sqlite_con) -> tuple[float, float] | None:
    """Try the street name as it literally appears in the decree first (correct
    for name-based streets like "Строителей", "Артема", which don't decline the
    way adjectival names do); only if that fails, retry with the adjectival
    instrumental->nominative conversion (needed for "Кальчанской"->"Кальчанская"
    etc.). Trying raw-first avoids _to_nominative corrupting an
    already-correct name (its blind "-ей"->"-яя" rule turns "Строителей" into
    the nonsense "Строителяя")."""
    p = geocode_street(f"{prefix} {name}", cache, sqlite_con)
    if p:
        return p
    nom = _to_nominative(name)
    if nom != name:
        return geocode_street(f"{prefix} {nom}", cache, sqlite_con)
    return None


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    sqlite_con = forensics.open_state()
    cache = load_cache()

    rows = [json.loads(l) for l in LAND_ORDERS_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    targets = []
    for r in rows:
        addr = r.get("address_normalized") or r.get("address_raw") or ""
        if "ограничен" in addr.lower():
            streets = extract_streets(addr)
            if len(streets) >= 2:
                targets.append((r, streets))

    log.info("%d records with a resolvable street-boundary description", len(targets))

    features = []
    for r, streets in targets:
        pts = []
        for s in streets:
            prefix, _, name = s.partition(" ")
            try:
                p = geocode_street_with_fallback(prefix, name, cache, sqlite_con)
            except Exception as e:
                log.warning("  geocode failed for %r: %s", s, e)
                p = None
            if p:
                pts.append(p)
        save_cache(cache)
        if len(pts) < 2:
            log.info("  decree %s: only %d/%d streets resolved, skipping",
                     r.get("decree_number"), len(pts), len(streets))
            continue
        lat = sum(p[0] for p in pts) / len(pts)
        lon = sum(p[1] for p in pts) / len(pts)
        log.info("  decree %s: centroid of %d/%d streets -> %.5f,%.5f (streets: %s)",
                 r.get("decree_number"), len(pts), len(streets), lat, lon, "; ".join(streets))
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "decree_number": r.get("decree_number"),
                "decree_date": r.get("decree_date"),
                "beneficiary_name": r.get("beneficiary_name"),
                "project_name": r.get("project_name"),
                "address_normalized": r.get("address_normalized"),
                "boundary_streets": streets,
                "boundary_streets_resolved": len(pts),
                "boundary_streets_total": len(streets),
                "geocode_method": "street_boundary_centroid",
                "geocode_confidence": 0.55,
            },
        })

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps({"type": "FeatureCollection", "features": features},
                                    ensure_ascii=False, indent=1), encoding="utf-8")
    log.info("wrote %d resolved parcels to %s", len(features), OUT_PATH)
    print(f"geocode_bounded_parcels: {len(features)}/{len(targets)} resolved via street-boundary centroid")


if __name__ == "__main__":
    main()
