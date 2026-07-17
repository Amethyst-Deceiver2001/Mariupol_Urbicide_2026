"""Source 9 — Mapillary crowdsourced street-level imagery near the address.

Street-level photos (often pre-war) with capture dates, via the Mapillary
Graph API (config.MAPILLARY_TOKEN, free). Skips with a note if no token.
Captures each image's 2048px thumb + records capture date/coords.
"""
from __future__ import annotations

import logging
import time

import requests

from ... import config, forensics
from .base import SourceResult, http_headers

log = logging.getLogger(__name__)

NAME = "mapillary"
RUN = "C"
NETWORK = True
DESCRIPTION = "Mapillary street-level imagery (dated, often pre-war) — token-gated"

GRAPH = "https://graph.mapillary.com/images"
MAX_IMAGES = 20
PAUSE = 0.3


def plan(bundle) -> str:
    if not config.MAPILLARY_TOKEN:
        return "SKIP — no MAPILLARY_TOKEN in .env"
    return f"Graph API images?bbox=radius_m (default 150m), capture ≤{MAX_IMAGES} thumbs with dates"


def fetch(bundle, con, radius_m: float = 150.0) -> SourceResult:
    if not config.MAPILLARY_TOKEN:
        return SourceResult(NAME, True, "skipped — no MAPILLARY_TOKEN set (free: "
                                        "mapillary.com/dashboard/developers)")
    lat, lon = bundle.lat, bundle.lon
    import math
    lat_pad = radius_m / 111_320.0
    lon_pad = radius_m / (111_320.0 * math.cos(math.radians(lat)))
    bbox = f"{lon-lon_pad},{lat-lat_pad},{lon+lon_pad},{lat+lat_pad}"
    try:
        r = requests.get(GRAPH, params={
            "access_token": config.MAPILLARY_TOKEN,
            "fields": "id,captured_at,compass_angle,geometry,thumb_2048_url",
            "bbox": bbox, "limit": str(MAX_IMAGES),
        }, headers=http_headers(), timeout=40)
        r.raise_for_status()
    except requests.RequestException as e:
        return SourceResult(NAME, False, f"request failed: {e}")

    captured = [forensics.capture_source(
        r.content, url=f"{GRAPH}?bbox={bbox}",
        source_type="osint_mapillary_listing",
        title=f"mapillary listing {bundle.slug}",
        description=f"Mapillary images bbox around pid={bundle.pid}.",
        content_type="application/json", http_status=r.status_code, con=con,
    )]

    findings: list[dict] = []
    for img in r.json().get("data", []):
        ts = img.get("captured_at")
        # captured_at is epoch ms
        date = ""
        if ts:
            import datetime as _dt
            date = _dt.datetime.utcfromtimestamp(ts / 1000).strftime("%Y-%m-%d")
        rec = {
            "kind": "mapillary_image", "id": img.get("id"),
            "date": date, "compass": img.get("compass_angle"),
            "url": f"https://www.mapillary.com/app/?pKey={img.get('id')}",
        }
        thumb = img.get("thumb_2048_url")
        if thumb:
            try:
                ir = requests.get(thumb, headers=http_headers(), timeout=60)
                if ir.status_code == 200 and ir.content:
                    sha = forensics.capture_source(
                        ir.content, url=thumb,
                        source_type="osint_mapillary_image",
                        title=f"mapillary {img.get('id')} {date}",
                        description=(f"Mapillary street-level image near pid={bundle.pid}, "
                                     f"captured {date}. {rec['url']}"),
                        content_type=ir.headers.get("Content-Type", "image/jpeg"),
                        http_status=ir.status_code, con=con,
                    )
                    rec["sha256"] = sha
                    captured.append(sha)
                    time.sleep(PAUSE)
            except requests.RequestException:
                log.debug("mapillary thumb fetch failed", exc_info=True)
        findings.append(rec)

    return SourceResult(NAME, True, f"{len(findings)} Mapillary images", findings, captured)
