"""Source 14b — Eyes on Russia (CIR) live per-address re-query.

The project-wide EoR load exists (scripts/200/201, corroboration kind
'eyesonrussia_civharm'); this module re-queries the same public ArcGIS
FeatureServer live, spatially, for THIS address — catching entries added
after the last project-wide load. Same endpoint, no auth, not geoblocked
(Esri infrastructure) — Claude-runnable per scripts/200's own precedent.
"""
from __future__ import annotations

import json
import logging

import requests

from ... import forensics
from .base import SourceResult, haversine_m, http_headers

log = logging.getLogger(__name__)

NAME = "eyesonrussia"
RUN = "C"
NETWORK = True
DESCRIPTION = "live per-address re-query of the EoR ArcGIS FeatureServer (scripts/200 endpoint)"

FEATURESERVER = (
    "https://services-eu1.arcgis.com/06WOSMGHsCnaFyMp/arcgis/rest/services/"
    "EoR_completed_entries/FeatureServer/0/query"
)


def plan(bundle) -> str:
    return f"FeatureServer spatial query, point ±{150}m, capture JSON"


def fetch(bundle, con, radius_m: float = 150.0) -> SourceResult:
    params = {
        "f": "json",
        "where": "1=1",
        "geometry": json.dumps({"x": bundle.lon, "y": bundle.lat,
                                "spatialReference": {"wkid": 4326}}),
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "distance": str(radius_m),
        "units": "esriSRUnit_Meter",
        "outFields": "*",
        "outSR": "4326",
        "resultRecordCount": "200",
    }
    try:
        resp = requests.get(FEATURESERVER, params=params,
                            headers=http_headers(), timeout=45)
        resp.raise_for_status()
    except requests.RequestException as e:
        return SourceResult(NAME, False, f"request failed: {e}")

    sha = forensics.capture_source(
        resp.content, url=resp.url,
        source_type="osint_eyesonrussia_query",
        title=f"EoR live query {bundle.slug}",
        description=(f"Eyes on Russia FeatureServer spatial query, point "
                     f"({bundle.lat:.6f},{bundle.lon:.6f}) r={radius_m}m, "
                     f"pid={bundle.pid}."),
        content_type="application/json", http_status=resp.status_code, con=con,
    )

    findings = []
    try:
        data = resp.json()
        for feat in data.get("features", []):
            a = feat.get("attributes", {})
            g = feat.get("geometry") or {}
            lat, lon = g.get("y"), g.get("x")
            d = (round(haversine_m(bundle.lat, bundle.lon, lat, lon), 1)
                 if lat is not None else None)
            ts = a.get("TIMESTAMP")
            findings.append({
                "kind": "eor_event",
                "entry": a.get("Entry_Number"),
                "date": (__import__("datetime").datetime.utcfromtimestamp(ts / 1000)
                         .strftime("%Y-%m-%d") if ts else ""),
                "category": a.get("Primary_category"),
                "description": (a.get("Description") or "")[:300],
                "link": a.get("Link") or "",
                "distance_m": d,
            })
    except Exception:  # noqa: BLE001
        log.warning("EoR response parse failed", exc_info=True)
        return SourceResult(NAME, False, "captured but parse failed", [], [sha])

    return SourceResult(NAME, True,
                        f"{len(findings)} EoR events within {radius_m:.0f}m",
                        findings, [sha])
