#!/usr/bin/env python3
"""Targeted Nominatim geocode pass for buildings this session's findings
reference that aren't in data/parsed/geocoded_buildings.jsonl or the
property table yet.

Triggered by the pre-mapping check (2026-06-18): before exporting the QGIS
findings layer (script 154), 9 distinct building_keys surfaced by the
ownerless differential (script 150) / gap register / media-lifecycle chat
resolution had no coordinates anywhere -- 6 are real new street references
(Карла Либкнехта 1/23/31, Комсомольский 24/13 + 38, Сеченова 12), one is
50 лет Октября 40/41 + 71 (the Меотиды-block boulevard), and one is проспект
Мира 133 (chat "Lenina133" / "Пр.Мира 133").

This is a SMALL, EXPLICIT list (not a full address_registry.jsonl re-run
like script 22) -- scoped to exactly what this session's outputs reference,
so it finishes in well under a minute even at Nominatim's 1 req/s policy.

APPENDS to geocoded_buildings.jsonl (loads existing rows first, merges,
writes back) -- never overwrites script 22's output. Shares the same
.geocode_cache.json so a building geocoded here is not re-queried by a
future script 22 run.

Network call to openstreetmap.org (not geoblocked) -- per CLAUDE.md
conventions, only the user runs this, not Claude.

Run:
    python scripts/155_geocode_session_gaps.py
"""
import json
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

PARSED_DIR = ROOT / "data" / "parsed"
GEOCODED_PATH = PARSED_DIR / "geocoded_buildings.jsonl"
CACHE_PATH = PARSED_DIR / ".geocode_cache.json"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
MIN_INTERVAL = 1.1

_CONTACT = config.GEOCODE_CONTACT or "no-contact-set"
_USER_AGENT = f"mariupol-property-seizures/1.0 (+contact: {_CONTACT})"
_HOUSE_TYPES = {"building", "house", "apartments", "residential", "yes"}
_STREET_TYPES = {"road", "highway", "residential_road", "street", "tertiary",
                 "secondary", "primary", "unclassified"}

# (building_key, street_query, house_no) -- street_query is the canonical
# full-word form so Nominatim resolves house-level (abbreviated prefixes
# like "б-р"/"пр-т" return zero results empirically; see normalize/address.py).
#
# "BOULEVARD:50 лет октября|71" deliberately excluded: user-verified
# (2026-06-18) that no such house exists on this street/block -- the
# besx_08.12.2025.pdf row is almost certainly a table-extraction artifact
# (OCR/positional misread), not a real disappeared property. Left out of the
# geocoded set on purpose; do not re-add without independent confirmation a
# building with that number exists.
# 4th field (alt_street) is an alternate query name to try when the primary
# street name returns only a street-level (no house-number) hit -- used for
# Карла Либкнехта, whose prewar/Ukrainian name "Митрополитская" is what OSM
# actually carries house-level tags under (per data/toponyms.csv and the
# "ул К. Либкнехта(Митрополитская)" parenthetical already seen in the
# 2025-01-13 ownerless snapshot). Still stored under the existing
# STREET:карла либкнехта|N building_key -- this is a query-string fallback
# only, not a rename.
TARGETS = [
    ("STREET:карла либкнехта|1",        "улица Карла Либкнехта", "1",  "улица Митрополитская"),
    ("STREET:карла либкнехта|23",       "улица Карла Либкнехта", "23", "улица Митрополитская"),
    ("STREET:карла либкнехта|31",       "улица Карла Либкнехта", "31", "улица Митрополитская"),
    ("BOULEVARD:комсомольский|24/13",   "бульвар Комсомольский", "24/13", None),
    ("BOULEVARD:комсомольский|38",      "бульвар Комсомольский", "38", None),
    ("STREET:сеченова|12",              "улица Сеченова", "12", None),
    ("AVENUE:мира|133",                 "проспект Мира", "133", None),
]

# Mariupol bounding box (computed from the existing 3,113-point geocoded set,
# 2026-06-18), used to bias/bound retries for street-level-only hits towards
# house-level precision.
MARIUPOL_VIEWBOX = "37.10,47.35,37.82,46.90"  # left,top,right,bottom (lon,lat)


def _load_jsonl(path: Path) -> dict:
    out = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                d = json.loads(line)
                out[d["building_key"]] = d
    return out


def _load_cache(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _save_cache(path: Path, cache: dict) -> None:
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")


def _query_nominatim(q: str, con) -> list[dict] | None:
    import requests
    params = {"q": q, "format": "jsonv2", "addressdetails": 1, "limit": 3,
              "countrycodes": "ua"}
    headers = {"User-Agent": _USER_AGENT, "Accept-Language": "uk,ru;q=0.8"}
    for attempt in range(1, 3):
        try:
            r = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=30)
            r.raise_for_status()
            forensics.capture_source(
                r.content, url=r.url, source_type="nominatim_geocode",
                title=f"Nominatim search: {q}",
                description="OSM Nominatim geocoding result (script 155 targeted gap pass)",
                content_type="application/json", http_status=r.status_code, con=con,
            )
            return r.json()
        except Exception as e:
            log.warning("Nominatim query failed (attempt %d/2) for %r: %s", attempt, q, e)
            time.sleep(2)
    return None


def _query_nominatim_structured(street_house: str, con) -> list[dict] | None:
    """Structured + viewbox-bounded retry for street-level-only hits. Nominatim
    sometimes resolves house numbers better via the `street=` structured field
    + a tight bounding box than via free-text `q=`, when the free-text result
    only matched the street centroid."""
    import requests
    params = {
        "street": street_house, "city": "Мариуполь", "country": "Украина",
        "format": "jsonv2", "addressdetails": 1, "limit": 3,
        "viewbox": MARIUPOL_VIEWBOX, "bounded": 1,
    }
    headers = {"User-Agent": _USER_AGENT, "Accept-Language": "uk,ru;q=0.8"}
    try:
        r = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=30)
        r.raise_for_status()
        forensics.capture_source(
            r.content, url=r.url, source_type="nominatim_geocode",
            title=f"Nominatim structured search: {street_house}",
            description="OSM Nominatim structured+bounded retry (script 155)",
            content_type="application/json", http_status=r.status_code, con=con,
        )
        return r.json()
    except Exception as e:
        log.warning("structured retry failed for %r: %s", street_house, e)
        return None


def _house_matches(requested: str, returned: str | None) -> bool:
    if not returned:
        return False
    a = requested.strip().lower().replace(" ", "").replace("-", "/")
    b = returned.strip().lower().replace(" ", "").replace("-", "/")
    return a == b or bool(set(a.split("/")) & set(b.split("/")))


def _score(row: dict, house_no: str) -> tuple[float, dict]:
    addr = row.get("address") or {}
    house = addr.get("house_number")
    rtype = row.get("addresstype") or row.get("type")
    if _house_matches(house_no, house):
        return 0.9, {"matched_house_number": True, "osm_addresstype": rtype}
    if rtype in _HOUSE_TYPES:
        return 0.7, {"matched_house_number": False, "osm_addresstype": rtype}
    if rtype in _STREET_TYPES:
        return 0.5, {"matched_house_number": False, "osm_addresstype": rtype}
    return 0.3, {"matched_house_number": False, "osm_addresstype": rtype}


def main() -> None:
    if not config.GEOCODE_CONTACT:
        log.warning("GEOCODE_CONTACT not set in .env -- Nominatim may rate-limit.")

    existing = _load_jsonl(GEOCODED_PATH)
    cache = _load_cache(CACHE_PATH)
    con = forensics.open_state()

    n_already = n_new = n_failed = 0
    last_query_at = 0.0
    for bk, street, house, alt_street in TARGETS:
        # re-attempt anything below house-level confidence (0.5 street-only
        # hits from a prior run), not just genuinely-missing entries
        if bk in existing and existing[bk].get("geocode_confidence", 0) >= 0.7:
            n_already += 1
            continue
        variants = [(f"{street} {house}, Мариуполь, Украина", street),
                    (f"{street}, Мариуполь, Украина", street)]
        if alt_street:
            variants = [(f"{alt_street} {house}, Мариуполь, Украина", alt_street),
                        (f"{alt_street}, Мариуполь, Украина", alt_street)] + variants
        for variant, variant_street in variants:
            if variant in cache:
                payload = cache[variant]
            else:
                wait = MIN_INTERVAL - (time.time() - last_query_at)
                if wait > 0:
                    time.sleep(wait)
                payload = _query_nominatim(variant, con)
                last_query_at = time.time()
                cache[variant] = payload
            if not payload:
                continue
            best = None
            for row in payload:
                conf, meta = _score(row, house)
                if best is None or conf > best[0]:
                    best = (conf, row, meta)
            if best and best[0] >= 0.5:
                conf, row, meta = best
                used_variant = variant
                # street-only match: retry structured+bounded for house-level
                if conf < 0.7:
                    wait = MIN_INTERVAL - (time.time() - last_query_at)
                    if wait > 0:
                        time.sleep(wait)
                    retry_payload = _query_nominatim_structured(f"{house} {variant_street}", con)
                    last_query_at = time.time()
                    if retry_payload:
                        retry_best = None
                        for r2 in retry_payload:
                            c2, m2 = _score(r2, house)
                            if retry_best is None or c2 > retry_best[0]:
                                retry_best = (c2, r2, m2)
                        if retry_best and retry_best[0] > conf:
                            conf, row, meta = retry_best
                            used_variant = f"structured:{house} {street}"
                            log.info("  structured retry improved %s: 0.5 -> %.1f", bk, conf)
                existing[bk] = {
                    "building_key": bk, "lat": float(row["lat"]), "lon": float(row["lon"]),
                    "geocode_confidence": conf, "geocode_source": "nominatim",
                    "query_used": used_variant, "variant_index": 0,
                    "osm_place_id": row.get("place_id"),
                    "display_name": row.get("display_name"),
                    **meta,
                }
                n_new += 1
                log.info("geocoded %s -> conf=%.1f (%s)", bk, conf, used_variant)
                break
        else:
            n_failed += 1
            log.warning("no usable result for %s (%s %s)", bk, street, house)

    _save_cache(CACHE_PATH, cache)
    with GEOCODED_PATH.open("w", encoding="utf-8") as fh:
        for bk in sorted(existing):
            fh.write(json.dumps(existing[bk], ensure_ascii=False) + "\n")

    print(f"\n{'='*60}")
    print("SESSION-GAP TARGETED GEOCODE")
    print(f"  already geocoded (skipped) : {n_already}")
    print(f"  newly geocoded             : {n_new}")
    print(f"  failed / no match          : {n_failed}")
    print(f"  geocoded_buildings.jsonl now has {len(existing)} total entries")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
