"""Source 16 — Flickr geo-search near the address.

Pre-war tourist/architecture photography, EXIF-rich (camera date + often
GPS). flickr.photos.search with a lat/lon/radius and a pre-2022 upload
window (config.FLICKR_API_KEY, free). Skips with a note if no key.
"""
from __future__ import annotations

import logging
import time

import requests

from ... import config, forensics
from .base import SourceResult, http_headers

log = logging.getLogger(__name__)

NAME = "flickr"
RUN = "C"
NETWORK = True
DESCRIPTION = "Flickr geo-search (pre-war, EXIF-rich) — key-gated"

REST = "https://api.flickr.com/services/rest/"
MAX_PHOTOS = 20
PAUSE = 0.3


def plan(bundle) -> str:
    if not config.FLICKR_API_KEY:
        return "SKIP — no FLICKR_API_KEY in .env"
    return f"photos.search geo radius≤{min(150,32000)/1000}km, capture ≤{MAX_PHOTOS} originals"


def fetch(bundle, con, radius_m: float = 150.0) -> SourceResult:
    if not config.FLICKR_API_KEY:
        return SourceResult(NAME, True, "skipped — no FLICKR_API_KEY set (free: "
                                        "flickr.com/services/apps/create)")
    try:
        r = requests.get(REST, params={
            "method": "flickr.photos.search", "api_key": config.FLICKR_API_KEY,
            "lat": f"{bundle.lat}", "lon": f"{bundle.lon}",
            "radius": f"{max(0.1, radius_m/1000):.2f}", "radius_units": "km",
            "extras": "date_taken,geo,url_o,url_l,owner_name,license",
            "per_page": str(MAX_PHOTOS), "format": "json", "nojsoncallback": "1",
            "sort": "date-taken-asc",
        }, headers=http_headers(), timeout=40)
        r.raise_for_status()
    except requests.RequestException as e:
        return SourceResult(NAME, False, f"request failed: {e}")

    captured = [forensics.capture_source(
        r.content, url=f"{REST}#search/{bundle.slug}",
        source_type="osint_flickr_listing",
        title=f"flickr search {bundle.slug}",
        description=f"Flickr photos.search geo around pid={bundle.pid}.",
        content_type="application/json", http_status=r.status_code, con=con,
    )]

    findings: list[dict] = []
    for p in r.json().get("photos", {}).get("photo", []):
        rec = {
            "kind": "flickr_photo", "id": p.get("id"),
            "title": p.get("title", ""), "date_taken": p.get("datetaken", ""),
            "owner": p.get("ownername", ""),
            "url": f"https://www.flickr.com/photos/{p.get('owner')}/{p.get('id')}",
        }
        dl = p.get("url_o") or p.get("url_l")
        if dl:
            try:
                ir = requests.get(dl, headers=http_headers(), timeout=60)
                if ir.status_code == 200 and ir.content:
                    sha = forensics.capture_source(
                        ir.content, url=dl,
                        source_type="osint_flickr_photo",
                        title=f"flickr {p.get('id')}: {p.get('title','')[:60]}",
                        description=(f"Flickr photo near pid={bundle.pid}, taken "
                                     f"{p.get('datetaken','')}, by {p.get('ownername','')}. "
                                     f"{rec['url']}"),
                        content_type=ir.headers.get("Content-Type", "image/jpeg"),
                        http_status=ir.status_code, con=con,
                    )
                    rec["sha256"] = sha
                    rec["image_url"] = dl  # stable staticflickr URL for reverse-image pivot
                    captured.append(sha)
                    time.sleep(PAUSE)
            except requests.RequestException:
                log.debug("flickr photo fetch failed", exc_info=True)
        findings.append(rec)

    return SourceResult(NAME, True, f"{len(findings)} Flickr photos", findings, captured)
