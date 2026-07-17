"""Source 6 — Wikimapia crowd descriptions of buildings near the address.

Wikimapia carries user-written descriptions of a building's PRE-WAR function
(dormitory, boiler house, kindergarten, clinic…) — exactly the context that
had to be reverse-engineered by hand for the Зелинского 19Б railway
dormitory / котельная №5. api.wikimapia.org needs a free key
(config.WIKIMAPIA_KEY); without one the module skips with a note (the public
"example" key is heavily rate-limited and unreliable, so we don't fall back
to it silently).

Two-step call (empirically confirmed 2026-07-16 — place.getbyarea returns a
bare `[]` for every bbox tried, including known-dense central Kyiv, so it
appears broken/deprecated on Wikimapia's side; place.getnearest works and
returns per-place `distance` in metres, but never a description field even
with data_blocks set — descriptions only come back from place.getbyid):
  1. place.getnearest(lat,lon,count) → candidate ids + distances, filtered
     to radius_m client-side (the API has no server-side radius param here).
  2. place.getbyid(id) for each candidate within radius → title + description.

Descriptions are CLAIMS (crowd-sourced, vandalism-prone post-2022) — logged
as corroboration candidates requiring the usual ≥2-source rule, never
standalone legal-grade.
"""
from __future__ import annotations

import logging

import requests

from ... import config, forensics
from .base import SourceResult, http_headers

log = logging.getLogger(__name__)

NAME = "wikimapia"
RUN = "C"
NETWORK = True
DESCRIPTION = "Wikimapia building descriptions (pre-war function/use) — key-gated"

API = "http://api.wikimapia.org/"
MAX_DETAIL_CALLS = 12  # cap place.getbyid lookups per sweep (rate-limit courtesy)


def plan(bundle) -> str:
    if not config.WIKIMAPIA_KEY:
        return "SKIP — no WIKIMAPIA_KEY in .env"
    return "place.getnearest (distance-filtered) then place.getbyid for descriptions"


def _call(function: str, con, bundle, **params) -> tuple[dict | None, str | None]:
    """One Wikimapia API call. Returns (parsed_json, capture_sha) or
    (None, sha) on request/parse failure — sha is still returned when we
    got bytes, so the failure itself is captured for chain of custody."""
    q = {"key": config.WIKIMAPIA_KEY, "function": function, "format": "json", **params}
    try:
        r = requests.get(API, params=q, headers=http_headers(), timeout=40)
    except requests.RequestException as e:
        log.warning("wikimapia %s failed: %s", function, e)
        return None, None
    sha = forensics.capture_source(
        r.content, url=r.url, source_type="osint_wikimapia",
        title=f"wikimapia {function} {bundle.slug}",
        description=f"Wikimapia {function} near pid={bundle.pid}.",
        content_type="application/json", http_status=r.status_code, con=con,
    )
    try:
        data = r.json()
    except ValueError:
        return None, sha
    if isinstance(data, dict) and "debug" in data:
        log.warning("wikimapia %s error: %s", function, data["debug"])
        return None, sha
    return data, sha


def fetch(bundle, con, radius_m: float = 150.0) -> SourceResult:
    if not config.WIKIMAPIA_KEY:
        return SourceResult(NAME, True, "skipped — no WIKIMAPIA_KEY set (free key: "
                                        "wikimapia.org/api)")
    findings: list[dict] = []
    captured: list[str] = []

    near, sha = _call("place.getnearest", con, bundle,
                      lat=bundle.lat, lon=bundle.lon, count=20,
                      data_blocks="location", language="ru")
    if sha:
        captured.append(sha)
    if not near:
        return SourceResult(NAME, True, "0 Wikimapia places (getnearest empty/failed)",
                            findings, captured)

    candidates = [p for p in near.get("places", [])
                  if (p.get("distance") or 1e9) <= radius_m]

    for place in candidates[:MAX_DETAIL_CALLS]:
        detail, sha = _call("place.getbyid", con, bundle,
                            id=place["id"], language="ru")
        if sha:
            captured.append(sha)
        if not detail:
            continue
        findings.append({
            "kind": "wikimapia_place",
            "id": detail.get("id"),
            "title": detail.get("title", ""),
            "description": (detail.get("description") or "")[:600],
            "distance_m": place.get("distance"),
            "url": f"https://wikimapia.org/{detail.get('id')}/",
        })

    return SourceResult(NAME, True, f"{len(findings)} Wikimapia places "
                        f"({len(candidates)} within {radius_m:.0f}m, "
                        f"{len(near.get('places', []))} scanned)",
                        findings, captured)
