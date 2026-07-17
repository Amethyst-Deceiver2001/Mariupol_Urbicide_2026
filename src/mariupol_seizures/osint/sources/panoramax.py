"""Source 21 — Panoramax crowdsourced street-level imagery near the address.

OSM Foundation-backed, fully open alternative to Mapillary/Kartaview
(https://panoramax.fr / api.panoramax.xyz). STAC-based REST API, keyless,
no app-review gate — found via The-Osint-Toolbox/Geolocation-OSINT list
2026-07-16, added specifically because Mapillary's own thumbnail access is
currently stuck behind an app-review gate (metadata works, images don't).

/api/search returns GeoJSON features; each has properties["geovisio:image"]
(full-res) and properties["geovisio:thumbnail"] (thumb) — both directly
downloadable, no auth. Also carries pre-computed content annotations
(properties["annotations"], e.g. detected traffic signs) when the instance
ran its detection pipeline on that image — surfaced as a bonus signal for
signage.
"""
from __future__ import annotations

import logging
import math
import time

import requests

from ... import forensics
from .base import SourceResult, http_headers

log = logging.getLogger(__name__)

NAME = "panoramax"
RUN = "C"
NETWORK = True
DESCRIPTION = "Panoramax street-level imagery (open, keyless, OSM Foundation-backed)"

SEARCH = "https://api.panoramax.xyz/api/search"
MAX_IMAGES = 20
PAUSE = 0.3


def plan(bundle) -> str:
    return f"/api/search?bbox=radius_m (default 150m), capture ≤{MAX_IMAGES} thumbs with dates"


def fetch(bundle, con, radius_m: float = 150.0) -> SourceResult:
    lat, lon = bundle.lat, bundle.lon
    lat_pad = radius_m / 111_320.0
    lon_pad = radius_m / (111_320.0 * math.cos(math.radians(lat)))
    bbox = f"{lon-lon_pad},{lat-lat_pad},{lon+lon_pad},{lat+lat_pad}"
    try:
        r = requests.get(SEARCH, params={"bbox": bbox, "limit": str(MAX_IMAGES)},
                         headers=http_headers(), timeout=40)
        r.raise_for_status()
    except requests.RequestException as e:
        return SourceResult(NAME, False, f"request failed: {e}")

    captured = [forensics.capture_source(
        r.content, url=r.url, source_type="osint_panoramax_listing",
        title=f"panoramax search {bundle.slug}",
        description=f"Panoramax images bbox around pid={bundle.pid}.",
        content_type="application/geo+json", http_status=r.status_code, con=con,
    )]

    findings: list[dict] = []
    for feat in r.json().get("features", []):
        props = feat.get("properties", {})
        date = (props.get("datetime") or "")[:10]
        signs = [a for a in props.get("annotations", [])
                if any(s.get("key", "").startswith("osm|traffic_sign")
                       for s in a.get("semantics", []))]
        rec = {
            "kind": "panoramax_image", "id": feat.get("id"),
            "date": date, "azimuth": props.get("view:azimuth"),
            "n_sign_detections": len(signs),
            "url": f"https://api.panoramax.xyz/#focus=pic&pic={feat.get('id')}",
        }
        thumb = props.get("geovisio:thumbnail")
        if thumb:
            try:
                ir = requests.get(thumb, headers=http_headers(), timeout=60)
                if ir.status_code == 200 and ir.content:
                    sha = forensics.capture_source(
                        ir.content, url=thumb, source_type="osint_panoramax_image",
                        title=f"panoramax {feat.get('id')} {date}",
                        description=(f"Panoramax street-level image near pid={bundle.pid}, "
                                     f"captured {date}. {rec['url']}"),
                        content_type=ir.headers.get("Content-Type", "image/jpeg"),
                        http_status=ir.status_code, con=con,
                    )
                    rec["sha256"] = sha
                    captured.append(sha)
                    time.sleep(PAUSE)
            except requests.RequestException:
                log.debug("panoramax thumb fetch failed", exc_info=True)
        findings.append(rec)

    return SourceResult(NAME, True, f"{len(findings)} Panoramax images", findings, captured)
