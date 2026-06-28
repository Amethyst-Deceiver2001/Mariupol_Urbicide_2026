#!/usr/bin/env python3
"""Capture the Eyes on Russia map's underlying ArcGIS feature service --
discovered 2026-06-28 (user-supplied URL to the map's landing page; the
old documented public export, eyesonrussia.org/events.geojson, is dead --
that whole domain now 301s to a generic info-res.org WordPress landing
page). The live map is an ArcGIS Experience Builder app
(experience.arcgis.com/experience/0e25a82c2c284768b9492c2a8d39b9b0,
item owner cir.maps) wrapping a public web map (item
008e1405253545bc869c131939f1659d on info-res.maps.arcgis.com) whose actual
event data lives in a public ArcGIS Online Feature Service:

    https://services-eu1.arcgis.com/06WOSMGHsCnaFyMp/arcgis/rest/services/
    EoR_completed_entries/FeatureServer/0

Found by walking the public, unauthenticated ArcGIS sharing REST API: the
Experience item's /data endpoint names its child WEB_MAP itemId, and that
web map's /data endpoint lists its operationalLayers (a "World countries"
basemap layer, a "Ukraine Oblast boundaries" layer, and "Event data" --
the FeatureServer above). No API key, no auth, no rate-limit friction
encountered. Hosted on Esri/ArcGIS Online infrastructure, not Russian/
occupation infrastructure -- not geoblocked, safe for Claude to run
directly.

Schema (30,929 country-wide records at capture time): Entry_Number,
Description, Link, Link_geolocation, Credit, Primary_category,
Secondary_category, Sector_affected, Town_or_City, country, province,
latitude, longitude, TIMESTAMP (epoch ms), Graphic_content_level.

This script captures the FULL Mariupol-filtered query result (server-side
WHERE Town_or_City LIKE '%Mariupol%' AND Primary_category='Civilian
Infrastructure Damage' -- 675 records at capture time; deliberately
excludes the project's "Russian Military Presence/Losses", "Ground
Battle", "Firing Positions", "Munitions" categories, which document
military activity, not civilian property damage, and are out of scope per
CLAUDE.md's mission framing). scripts/201 does the spatial join + load.

Distance-distribution sanity check before picking a join radius (run
2026-06-28 against the then-current 388-record Civilian-property subset):
median nearest-property distance 28m, p90=121m, p95=202m -- materially
tighter than the Bellingcat civharm layer (scripts/198-199), which is why
this loader (scripts/201) uses the same 100m cutoff but a slightly higher
confidence ceiling.

Run:
    PYTHONPATH=src python scripts/200_fetch_eyesonrussia_civharm.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import requests  # noqa: E402

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

FEATURE_SERVER = (
    "https://services-eu1.arcgis.com/06WOSMGHsCnaFyMp/arcgis/rest/services/"
    "EoR_completed_entries/FeatureServer/0/query"
)
WHERE = "Town_or_City LIKE '%Mariupol%' AND Primary_category='Civilian Infrastructure Damage'"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    con = forensics.open_state()
    s = requests.Session()
    s.headers.update({"User-Agent": config.USER_AGENT})

    params = {
        "where": WHERE,
        "outFields": "*",
        "f": "geojson",
        "resultRecordCount": 2000,
    }
    url = f"{FEATURE_SERVER}?{urlencode(params)}"
    log.info("Fetching %s", url)
    r = s.get(url, timeout=config.TIMEOUT)
    r.raise_for_status()

    sha = forensics.capture_source(
        r.content, url=url, source_type="eyesonrussia_civharm",
        title="Eyes on Russia (CIR/Bellingcat/GeoConfirmed) -- Mariupol civilian infrastructure damage",
        description=(
            "Server-side filtered query of the public EoR_completed_entries "
            "ArcGIS Feature Service: Town_or_City LIKE Mariupol AND "
            "Primary_category='Civilian Infrastructure Damage'. Spatially "
            "joined to the property spine by scripts/201."
        ),
        content_type=r.headers.get("Content-Type", "application/geo+json"),
        http_status=r.status_code, con=con,
    )
    log.info("Captured sha=%s bytes=%d -> run scripts/201 next", sha[:16], len(r.content))


if __name__ == "__main__":
    main()
