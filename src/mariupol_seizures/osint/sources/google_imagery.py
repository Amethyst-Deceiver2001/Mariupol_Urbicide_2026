"""Source 11 — Google Street View metadata + Places, for the address.

The Street View metadata endpoint is FREE and returns whether panorama
coverage exists at the point and its capture date — a cheap way to learn
"Google has a pre-war street-level pano here, dated YYYY-MM" without paying
for the image. Actual pano/Places imagery is billed (~$7/1k) and is left to
the user to pull deliberately. Uses config.GOOGLE_MAPS_API_KEY (already used
by scripts/24). Marked RUN=U ($ + external); skips with a note if no key.
"""
from __future__ import annotations

import logging

import requests

from ... import config, forensics
from .base import SourceResult, http_headers

log = logging.getLogger(__name__)

NAME = "google_imagery"
RUN = "U"
NETWORK = True
DESCRIPTION = "Google Street View coverage/date metadata (free) + Places lookup — $ key"

SV_META = "https://maps.googleapis.com/maps/api/streetview/metadata"
PLACES = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"


def plan(bundle) -> str:
    if not config.GOOGLE_MAPS_API_KEY:
        return "SKIP — no GOOGLE_MAPS_API_KEY in .env"
    return "Street View metadata (free: has-coverage + date) + Places nearbysearch"


def fetch(bundle, con, radius_m: float = 50.0) -> SourceResult:
    if not config.GOOGLE_MAPS_API_KEY:
        return SourceResult(NAME, True, "skipped — no GOOGLE_MAPS_API_KEY set")
    findings: list[dict] = []
    captured: list[str] = []

    try:
        r = requests.get(SV_META, params={
            "location": f"{bundle.lat},{bundle.lon}",
            "key": config.GOOGLE_MAPS_API_KEY, "radius": str(int(radius_m)),
        }, headers=http_headers(), timeout=30)
        r.raise_for_status()
        captured.append(forensics.capture_source(
            r.content, url=f"{SV_META}?loc={bundle.lat},{bundle.lon}",
            source_type="osint_google_sv_metadata",
            title=f"google SV metadata {bundle.slug}",
            description=f"Street View coverage metadata at pid={bundle.pid}.",
            content_type="application/json", http_status=r.status_code, con=con,
        ))
        meta = r.json()
        status = meta.get("status")
        if status == "OK":
            note = "panorama exists — pull the image manually if needed (billed)"
        elif status == "ZERO_RESULTS":
            note = "no Street View coverage at this point"
        else:
            note = (f"API error ({status}): {meta.get('error_message', '')} — "
                    "not a coverage result, check API key/enabled-APIs in "
                    "Google Cloud Console")
        findings.append({
            "kind": "streetview_coverage",
            "status": status,
            "date": meta.get("date", ""),
            "pano_id": meta.get("pano_id", ""),
            "note": note,
        })
    except requests.RequestException as e:
        log.warning("SV metadata failed: %s", e)
        findings.append({"kind": "error", "stage": "streetview", "error": str(e)})

    try:
        r = requests.get(PLACES, params={
            "location": f"{bundle.lat},{bundle.lon}", "radius": str(int(radius_m)),
            "key": config.GOOGLE_MAPS_API_KEY,
        }, headers=http_headers(), timeout=30)
        r.raise_for_status()
        places_data = r.json()
        if places_data.get("status") not in ("OK", "ZERO_RESULTS"):
            findings.append({"kind": "error", "stage": "places",
                             "error": f"{places_data.get('status')}: "
                                      f"{places_data.get('error_message', '')}"})
        for pl in places_data.get("results", [])[:10]:
            findings.append({
                "kind": "google_place",
                "name": pl.get("name", ""),
                "types": pl.get("types", []),
                "vicinity": pl.get("vicinity", ""),
                "place_id": pl.get("place_id", ""),
            })
    except requests.RequestException as e:
        log.warning("Places failed: %s", e)

    n_place = sum(1 for f in findings if f["kind"] == "google_place")
    cov = next((f for f in findings if f["kind"] == "streetview_coverage"), {})
    return SourceResult(NAME, True,
                        f"Street View: {cov.get('status','?')} ({cov.get('date','') or 'no date'}), "
                        f"{n_place} nearby places",
                        findings, captured)
