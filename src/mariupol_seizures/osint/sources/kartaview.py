"""Source 22 — Kartaview (formerly OpenStreetCam) street-level imagery.

Second independent crowd-sourced street-level imagery platform, keyless
REST API at api.openstreetcam.org (the underlying API host kept its old
name; the consumer site rebranded to kartaview.org). Found via
The-Osint-Toolbox/Geolocation-OSINT list 2026-07-16 — added as coverage
redundancy alongside Mapillary (thumbnail access currently gated) and
Panoramax; each crowd-sourced imagery platform has different, non-
overlapping contributor coverage, so checking all three costs nothing
(all keyless/free) and only adds candidates.
"""
from __future__ import annotations

import logging
import time

import requests

from ... import forensics
from .base import SourceResult, http_headers

log = logging.getLogger(__name__)

NAME = "kartaview"
RUN = "C"
NETWORK = True
DESCRIPTION = "Kartaview/OpenStreetCam street-level imagery (open, keyless)"

SEARCH = "https://api.openstreetcam.org/2.0/photo/"
MAX_IMAGES = 20
PAUSE = 0.3


def plan(bundle) -> str:
    return f"/2.0/photo/?lat&lng&radius (default 150m), capture ≤{MAX_IMAGES} thumbs with dates"


def fetch(bundle, con, radius_m: float = 150.0) -> SourceResult:
    try:
        r = requests.get(SEARCH, params={
            "lat": bundle.lat, "lng": bundle.lon, "radius": radius_m,
        }, headers=http_headers(), timeout=40)
        r.raise_for_status()
    except requests.RequestException as e:
        return SourceResult(NAME, False, f"request failed: {e}")

    captured = [forensics.capture_source(
        r.content, url=r.url, source_type="osint_kartaview_listing",
        title=f"kartaview search {bundle.slug}",
        description=f"Kartaview images near pid={bundle.pid}.",
        content_type="application/json", http_status=r.status_code, con=con,
    )]

    findings: list[dict] = []
    try:
        rows = r.json().get("result", {}).get("data") or []
    except ValueError:
        rows = []

    for row in rows[:MAX_IMAGES]:
        date = (row.get("dateAdded") or "")[:10]
        photo_id = row.get("id") or row.get("sequenceId")
        rec = {
            "kind": "kartaview_image", "id": photo_id,
            "date": date, "distance_m": row.get("distance"),
            "url": f"https://kartaview.org/details/{row.get('sequenceId')}/{row.get('sequenceIndex', '')}",
        }
        thumb = row.get("fileurlLTh") or row.get("fileurlTh")
        if thumb:
            try:
                ir = requests.get(thumb, headers=http_headers(), timeout=60)
                if ir.status_code == 200 and ir.content:
                    sha = forensics.capture_source(
                        ir.content, url=thumb, source_type="osint_kartaview_image",
                        title=f"kartaview {photo_id} {date}",
                        description=(f"Kartaview street-level image near pid={bundle.pid}, "
                                     f"captured {date}. {rec['url']}"),
                        content_type=ir.headers.get("Content-Type", "image/jpeg"),
                        http_status=ir.status_code, con=con,
                    )
                    rec["sha256"] = sha
                    captured.append(sha)
                    time.sleep(PAUSE)
            except requests.RequestException:
                log.debug("kartaview thumb fetch failed", exc_info=True)
        findings.append(rec)

    return SourceResult(NAME, True, f"{len(findings)} Kartaview images", findings, captured)
