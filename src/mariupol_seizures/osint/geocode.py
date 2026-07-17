"""Engine 2 — geocoding + point confidence (docs/address_osint_assistant_design.md).

Three independent geocoders, compared:
  1. Nominatim / OSM  — Ukrainian addressing (no key; usage policy needs a
     contact string, config.GEOCODE_CONTACT).
  2. Yandex Geocoder  — resolves RENAMED occupation-era addressing that
     Nominatim can't (free tier; config.YANDEX_GEOCODER_KEY).
  3. Visicom          — authoritative PRE-WAR Ukrainian spelling + a second
     independent footprint source; no public API (playwright reverse of
     maps.visicom.ua). Implemented in sources/visicom.py; this module calls
     it opportunistically and treats absence as "geocoder unavailable", not
     an error.

Agreement ≤30m across the geocoders that answered → high-confidence point.
Divergence >30m → the point is returned but flagged low-confidence for a
manual pin (no-false-precision rule — the points are NEVER averaged; the
best-confidence single source wins, ties broken Nominatim > Yandex).

Used by bundle.resolve_bundle() ONLY for off-spine addresses (a spine pid
already carries a geocoded point). Each geocoder that touches the network
is a slow/external call — per the project's standing rule this runs when
the user invokes the sweep, not silently inside a Claude turn.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .sources.base import haversine_m, http_headers

log = logging.getLogger(__name__)

AGREEMENT_M = 30.0


@dataclass
class GeocodeResult:
    lat: float
    lon: float
    source: str
    display_name: str = ""
    confidence: str = "single"          # single | agreed | divergent
    all_points: list[dict] = field(default_factory=list)
    max_spread_m: float | None = None


def _nominatim(address: str) -> dict | None:
    import requests

    from .. import config
    q = f"{address}, Маріуполь, Україна"
    ua = http_headers()
    if config.GEOCODE_CONTACT:
        ua["User-Agent"] = f"mariupol-property-seizures ({config.GEOCODE_CONTACT})"
    try:
        r = requests.get("https://nominatim.openstreetmap.org/search",
                         params={"q": q, "format": "json", "limit": 1},
                         headers=ua, timeout=30)
        r.raise_for_status()
        rows = r.json()
        if rows:
            return {"lat": float(rows[0]["lat"]), "lon": float(rows[0]["lon"]),
                    "source": "nominatim", "display_name": rows[0].get("display_name", "")}
    except Exception:  # noqa: BLE001
        log.warning("nominatim geocode failed for %r", address, exc_info=True)
    return None


def _yandex(address: str) -> dict | None:
    import requests

    from .. import config
    if not config.YANDEX_GEOCODER_KEY:
        return None
    try:
        r = requests.get("https://geocode-maps.yandex.ru/1.x/",
                         params={"apikey": config.YANDEX_GEOCODER_KEY,
                                 "geocode": f"Мариуполь, {address}",
                                 "format": "json", "results": 1, "lang": "ru_RU"},
                         headers=http_headers(), timeout=30)
        r.raise_for_status()
        members = (r.json()["response"]["GeoObjectCollection"]["featureMember"])
        if members:
            pos = members[0]["GeoObject"]["Point"]["pos"]  # "lon lat"
            lon, lat = (float(x) for x in pos.split())
            name = members[0]["GeoObject"].get("name", "")
            return {"lat": lat, "lon": lon, "source": "yandex", "display_name": name}
    except Exception:  # noqa: BLE001
        log.warning("yandex geocode failed for %r", address, exc_info=True)
    return None


def _visicom(address: str) -> dict | None:
    """Opportunistic — sources.visicom exposes geocode_one() when playwright
    is available; any failure (no playwright, ToS gate, timeout) degrades to
    None, i.e. "this geocoder didn't answer", never an error."""
    try:
        from .sources.visicom import geocode_one
        return geocode_one(address)
    except Exception:  # noqa: BLE001
        log.debug("visicom geocode unavailable for %r", address, exc_info=True)
        return None


def geocode(address: str) -> GeocodeResult | None:
    """Resolve an address through all available geocoders and reconcile."""
    points = [p for p in (_nominatim(address), _yandex(address), _visicom(address))
              if p is not None]
    if not points:
        return None

    # preference order for the single winning point
    order = {"nominatim": 0, "yandex": 1, "visicom": 2}
    points.sort(key=lambda p: order.get(p["source"], 9))
    best = points[0]

    spread = 0.0
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            spread = max(spread, haversine_m(points[i]["lat"], points[i]["lon"],
                                             points[j]["lat"], points[j]["lon"]))
    if len(points) == 1:
        conf = "single"
    elif spread <= AGREEMENT_M:
        conf = "agreed"
    else:
        conf = "divergent"
        log.warning("geocoders disagree by %.0fm for %r — using %s, flag for "
                    "manual pin", spread, address, best["source"])

    return GeocodeResult(
        lat=best["lat"], lon=best["lon"], source=best["source"],
        display_name=best.get("display_name", ""), confidence=conf,
        all_points=points, max_spread_m=round(spread, 1) if len(points) > 1 else None,
    )
