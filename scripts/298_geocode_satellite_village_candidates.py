#!/usr/bin/env python3
"""Stage 4d (geocoding fallback): Tier A3 -- re-query Nominatim/Google for a
small, independently-confirmed set of buildings whose street name AND whose
existing (sub-claim-grade) coordinate both point at one of Mariupol's
occupation-merged satellite settlements, using the CORRECT locality name
instead of "Мариуполь".

WHY THIS EXISTS
---------------
scripts/23 (Overpass addr-tag lookup) was extended 2026-07-10 to search these
settlements too (see data/boundaries/mariupol_okrug_extended_boundary.geojson)
and correctly upgraded a couple of buildings -- but most of this candidate
list has NO addr:housenumber tag in OSM at all for that specific house
(confirmed by direct inspection: house 47 does not exist anywhere among
OSM's 123 tagged "Лафазана" entries, etc). That's a real OSM data-density
gap in rural/village areas, not a bug.

The root cause for most of these buildings is different and more fixable:
scripts/22/24 always append ", Мариуполь, Украина" to every query, but these
streets are in a DIFFERENT locality that OSM/Nominatim files separately --
Сартана/Талаківка/Гнутове/Ломакине/Калинівка pre-war belonged to a distinct
hromada (Сартанська селищна громада) that the occupation's 06.04.2023
"городской округ Мариуполь" municipal reform merged in; Старий Крим is a
pre-war Mariupol exclave outside our original hand-captured boundary. Asking
Nominatim/Google for "improved query + correct locality name" instead of
"+ Мариуполь" should resolve house-level matches Nominatim's own search
ranking already has, just filed under the right place name.

SCOPE -- deliberately narrow and hardcoded, not a broad fuzzy re-scan:
Many satellite-village street names (Комсомольская, Шевченко, Спортивная,
Суворова, Школьная, Пушкина, Торговая, Университетская, Челюскинцев,
Котовского, Богдана Хмельницкого...) are generic Soviet-era names that
ALSO exist in inner Mariupol at high confidence already -- a broad
name-only fuzzy match against village street lists produces false
positives (confirmed 2026-07-10: 16 of 18 initial fuzzy-name candidates
turned out to already have unrelated high-confidence matches elsewhere in
the city). This script instead only touches the 18 building_keys below,
each independently confirmed by BOTH street-name AND existing-coordinate
proximity (<2km) to a real village centroid -- see
memory/satellite_villages_geocoding_2026-07-10.md for the full derivation.

Only overwrites a row if the new result's confidence is STRICTLY HIGHER than
its current value (same convention as scripts/24).

Run locally, no VPS needed:
  python3 scripts/298_geocode_satellite_village_candidates.py
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

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger("village_geocode")

PARSED_DIR = config.PROJECT_ROOT / "data" / "parsed"
GEO_PATH = PARSED_DIR / "geocoded_buildings.jsonl"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
GOOGLE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
MIN_INTERVAL = 1.1

_CONTACT = config.GEOCODE_CONTACT or "no-contact-set"
_USER_AGENT = f"mariupol-property-seizures/1.0 (+contact: {_CONTACT})"

_HOUSE_TYPES = {"building", "house", "apartments", "residential", "yes"}
_STREET_TYPES = {"road", "highway", "residential_road", "street", "tertiary",
                 "secondary", "primary", "unclassified"}

# building_key -> (street name to search, house no, correct locality for the query)
# Derived 2026-07-10: street name matches an OSM-confirmed street in the
# settlement AND the building's existing (sub-claim-grade) coordinate sits
# within 2km of that settlement's centroid. See module docstring.
#
# Second batch (2026-07-10, same session): user pointed out "25 партсъезда"
# (Talakivka) was missed -- our building_key uses an Arabic numeral ("25")
# which doesn't character-fuzzy-match the Roman numeral OSM/dokladno.com
# spells it with ("XXV Партсъезда"), so the original distance+name filter
# silently dropped it. Re-scanned all remaining sub-0.9 rows against street
# names confirmed present in each settlement via ru.dokladno.com (a KLADR-
# style settlement/street directory: Талаковка np=164, Ломакино np=166,
# Старый Крым np=163, raj=343 "г. Мариуполь") crossed with the Overpass
# street list already fetched. NOTE: dokladno.com's per-street "house
# number" links are a generic 1-100 sequential range-picker (search-assist
# UI), NOT real address data -- only the STREET NAME index is trustworthy,
# confirmed by manually checking the underlying HTML. House-level
# confirmation still comes only from Nominatim/Google/OSM tags, same as the
# first batch.
CANDIDATES: dict[str, tuple[str, str, str]] = {
    "LANE:восточный|11б": ("переулок Восточный", "11б", "Гнутове"),
    "LANE:восточный|1а": ("переулок Восточный", "1а", "Гнутове"),
    "LANE:восточный|21": ("переулок Восточный", "21", "Гнутове"),
    "LANE:восточный|21а": ("переулок Восточный", "21а", "Гнутове"),
    "STREET:азовская|70": ("улица Азовская", "70", "Ломакине"),
    "STREET:азовская|94": ("улица Азовская", "94", "Ломакине"),
    "STREET:малосадовая|51": ("улица Малосадовая", "51", "Ломакине"),
    "STREET:малосадовая|42а": ("улица Малосадовая", "42а", "Ломакине"),  # currently 0.8 (fuzzy OSM tag), try to push to exact 0.9
    "STREET:1 мая|58": ("улица 1 Мая", "58", "Сартана"),
    "STREET:лафазана|47": ("улица Лафазана", "47", "Сартана"),
    "STREET:октябрьская|23а": ("улица Октябрьская", "23а", "Сартана"),
    "STREET:октябрьская|45а": ("улица Октябрьская", "45а", "Сартана"),
    "STREET:октябрьская|8б": ("улица Октябрьская", "8б", "Сартана"),
    "STREET:эллинская|24, лит. к-1": ("улица Эллинская", "24", "Сартана"),
    "STREET:ленина|110/1": ("улица Ленина", "110/1", "Старий Крим"),
    "STREET:рабочая остановка|41": ("улица Рабочая Остановка", "41", "Старий Крим"),
    "UNKNOWN:поселок старый крым, улица гранитная|55б": ("улица Гранитная", "55б", "Старий Крим"),
    # -- second batch --
    "STREET:25 партсъезда|6": ("улица XXV Партсъезда", "6", "Талаківка"),
    "STREET:25 партсъезда|23": ("улица XXV Партсъезда", "23", "Талаківка"),
    "STREET:25 партсъезда|25": ("улица XXV Партсъезда", "25", "Талаківка"),
    "STREET:25 партсъезда|34": ("улица XXV Партсъезда", "34", "Талаківка"),
    "STREET:25 партсъезда|36": ("улица XXV Партсъезда", "36", "Талаківка"),
    "STREET:25 партсъезда|43": ("улица XXV Партсъезда", "43", "Талаківка"),
    "STREET:25 партсъезда|45": ("улица XXV Партсъезда", "45", "Талаківка"),
    "STREET:25 партсъезда|50": ("улица XXV Партсъезда", "50", "Талаківка"),
    "STREET:кирова|18а": ("улица Кирова", "18а", "Старий Крим"),
    "STREET:кирова|27а": ("улица Кирова", "27а", "Старий Крим"),
    "STREET:кирова|36а": ("улица Кирова", "36а", "Старий Крим"),
    "STREET:комсомольская|38а": ("улица Комсомольская", "38а", "Старий Крим"),
    "STREET:комсомольская|60б": ("улица Комсомольская", "60б", "Старий Крим"),
    "STREET:комсомольская|61а": ("улица Комсомольская", "61а", "Старий Крим"),
    "STREET:комсомольская|110": ("улица Комсомольская", "110", "Старий Крим"),
    "STREET:комсомольская|21": ("улица Комсомольская", "21", "Старий Крим"),
    "STREET:комсомольская|70": ("улица Комсомольская", "70", "Старий Крим"),
    "STREET:крупской|73б": ("улица Крупской", "73б", "Старий Крим"),
    "STREET:крупской|104": ("улица Крупской", "104", "Старий Крим"),
    "STREET:крупской|17": ("улица Крупской", "17", "Старий Крим"),
    "STREET:крупской|67": ("улица Крупской", "67", "Старий Крим"),
    "STREET:куйбышева|123": ("улица Куйбышева", "123", "Старий Крим"),
    "STREET:куйбышева|126": ("улица Куйбышева", "126", "Старий Крим"),
    "STREET:куйбышева|82а": ("улица Куйбышева", "82а", "Старий Крим"),
    "STREET:куйбышева|50": ("улица Куйбышева", "50", "Старий Крим"),
    "STREET:рабочая остановка|17": ("улица Рабочая Остановка", "17", "Старий Крим"),
    "STREET:рабочая остановка|19": ("улица Рабочая Остановка", "19", "Старий Крим"),
    "STREET:рабочая остановка|7": ("улица Рабочая Остановка", "7", "Старий Крим"),
    "STREET:спортивная|22а": ("улица Спортивная", "22а", "Ломакине"),
    "STREET:спортивная|4а": ("улица Спортивная", "4а", "Ломакине"),
    "STREET:спортивная|6а": ("улица Спортивная", "6а", "Ломакине"),
    "STREET:университетская|4а": ("улица Университетская", "4а", "Ломакине"),
    # dokladno.com lists this as "Котовского переулок" (LANE) in Lomakine,
    # but our building_key class is STREET -- try the confirmed real type.
    "STREET:котовского|101 а-1": ("переулок Котовского", "101 а-1", "Ломакине"),
    "STREET:котовского|32 б-1": ("переулок Котовского", "32 б-1", "Ломакине"),
}


def _house_matches(requested: str, returned: str | None) -> bool:
    if not returned:
        return False
    a = requested.strip().lower().replace(" ", "").replace("-", "/")
    b = returned.strip().lower().replace(" ", "").replace("-", "/")
    if a == b:
        return True
    return bool(set(a.split("/")) & set(b.split("/")))


def _query_nominatim(q: str, con) -> list[dict] | None:
    params = {"q": q, "format": "jsonv2", "addressdetails": 1, "limit": 3, "countrycodes": "ua"}
    headers = {"User-Agent": _USER_AGENT, "Accept-Language": "uk,ru;q=0.8"}
    for attempt in range(1, 3):
        try:
            r = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=config.TIMEOUT)
            r.raise_for_status()
            forensics.capture_source(
                r.content, url=r.url, source_type="nominatim_geocode",
                title=f"Nominatim search (satellite-village retry): {q}",
                description="OSM Nominatim geocoding result, locality-corrected retry for a satellite-village building",
                content_type="application/json", http_status=r.status_code, con=con,
            )
            return r.json()
        except (requests.RequestException, ValueError) as e:
            log.warning("Nominatim query failed (attempt %d/2) for %r: %s", attempt, q, e)
            time.sleep(2)
    return None


def _score_nominatim(row: dict, house_no: str) -> tuple[float, dict]:
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


def _query_google(q: str, con) -> dict | None:
    if not config.GOOGLE_MAPS_API_KEY:
        return None
    params = {"address": q, "key": config.GOOGLE_MAPS_API_KEY, "region": "ua", "language": "ru"}
    try:
        r = requests.get(GOOGLE_URL, params=params, timeout=config.TIMEOUT)
        r.raise_for_status()
        forensics.capture_source(
            r.content, url=r.url.split("key=")[0] + "key=REDACTED", source_type="google_geocode",
            title=f"Google geocode (satellite-village retry): {q}",
            description="Google Geocoding API result, locality-corrected retry for a satellite-village building",
            content_type="application/json", http_status=r.status_code, con=con,
        )
        data = r.json()
        if data.get("status") != "OK" or not data.get("results"):
            return None
        result = data["results"][0]
        loc = result["geometry"]["location"]
        house_matched = any(
            c.get("types") == ["street_number"] for c in result.get("address_components", [])
        )
        conf = 0.9 if house_matched else 0.5
        return {"lat": loc["lat"], "lon": loc["lng"], "confidence": conf,
                "matched_house_number": house_matched}
    except requests.RequestException as e:
        log.warning("Google query failed for %r: %s", q, e)
        return None


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    if not config.GEOCODE_CONTACT:
        log.warning("GEOCODE_CONTACT not set in .env -- Nominatim may rate-limit requests")

    if not GEO_PATH.exists():
        log.error("%s not found -- run scripts/22 first", GEO_PATH)
        sys.exit(1)

    rows = [json.loads(l) for l in GEO_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    by_key = {r["building_key"]: r for r in rows}

    con = forensics.open_state()
    n_upgraded = 0
    for building_key, (street, house, locality) in CANDIDATES.items():
        row = by_key.get(building_key)
        if not row:
            log.warning("building_key %r not found in geocoded_buildings.jsonl, skipping", building_key)
            continue
        current_conf = row.get("geocode_confidence", 0)

        query = f"{street} {house}, {locality}, Маріупольський район, Донецька область, Україна"
        time.sleep(MIN_INTERVAL)
        results = _query_nominatim(query, con) or []
        best = None
        for r in results:
            conf, meta = _score_nominatim(r, house)
            if best is None or conf > best[0]:
                best = (conf, {"lat": float(r["lat"]), "lon": float(r["lon"]),
                               "geocode_source": "nominatim_village_retry", **meta})

        if (not best or best[0] < 0.9) and config.GOOGLE_MAPS_API_KEY:
            time.sleep(MIN_INTERVAL)
            g = _query_google(query, con)
            if g and (best is None or g["confidence"] > best[0]):
                best = (g["confidence"], {"lat": g["lat"], "lon": g["lon"],
                                          "geocode_source": "google_village_retry",
                                          "matched_house_number": g["matched_house_number"]})

        if best and best[0] > current_conf:
            log.info("UPGRADED %s: %.2f (%s) -> %.2f (%s)", building_key, current_conf,
                     row.get("geocode_source"), best[0], best[1]["geocode_source"])
            row["previous_geocode"] = {
                "lat": row.get("lat"), "lon": row.get("lon"),
                "geocode_confidence": current_conf, "geocode_source": row.get("geocode_source"),
            }
            row["lat"] = best[1]["lat"]
            row["lon"] = best[1]["lon"]
            row["geocode_confidence"] = best[0]
            row["geocode_source"] = best[1]["geocode_source"]
            row["query_used"] = query
            n_upgraded += 1
        else:
            log.info("no improvement for %s (current %.2f, best found %s)",
                     building_key, current_conf, best[0] if best else None)

    with GEO_PATH.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    log.info("Upgraded %d / %d satellite-village candidates", n_upgraded, len(CANDIDATES))
    con.close()


if __name__ == "__main__":
    main()
