#!/usr/bin/env python3
"""Capture the GeoConfirmed Ukraine KML export -- discovered 2026-06-28 via
the `osint-geo-extractor` PyPI package's downloader source
(github.com/conflict-investigations/osint-geo-extractor/blob/master/
geo_extractor/downloaders/geoconfirmed.py), which documents the live
endpoint behind GeoConfirmed's public KML/Google-Earth export:

    https://geoconfirmed.org/api/map/ExportAsKml/Ukraine

GeoConfirmed (@GeoConfirmed) is an open-source geolocation-verification
group, methodologically similar to Bellingcat/Cen4InfoRes but a fully
distinct team/process -- a FIFTH independent provenance family for this
project's Tier-3 corroboration layer (after the project's own crawls,
UNOSAT satellite analysis, Bellingcat's civharm timemap, and Eyes on
Russia/Cen4InfoRes).

The endpoint returns a ZIP (Google Earth's native KMZ-style export)
containing doc.kml (placemarks: name, HTML description, Point coordinates)
plus a folder of static circle/marker images. Hosted on geoconfirmed.org's
own infrastructure -- not Russian/occupation infrastructure, not
geoblocked, safe for Claude to run directly.

This script captures the full country-wide ZIP verbatim (~6MB at capture
time, no server-side filter available). scripts/203 unzips, parses the
KML, filters to Mariupol + civilian-property scope, and does the spatial
join + load.

NOTE 2026-06-28: the osint-geo-extractor package's documented endpoint
(`/api/map/ExportAsKml/Ukraine`) returns 404 -- GeoConfirmed rebuilt their
site as a Blazor WASM app since that package's last release (Jan 2024) and
the route changed. The live equivalent, found by probing plausible
variants, is `/api/map/export/Ukraine` (lowercase, no "As"). Same ZIP/KML
shape (doc.kml + icon images), confirmed by inspection.

Run:
    PYTHONPATH=src python scripts/202_fetch_geoconfirmed_kml.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import requests  # noqa: E402

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

URL = "https://geoconfirmed.org/api/map/export/Ukraine"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    con = forensics.open_state()
    s = requests.Session()
    s.headers.update({"User-Agent": config.USER_AGENT})

    log.info("Fetching %s", URL)
    r = s.get(URL, timeout=config.TIMEOUT)
    r.raise_for_status()

    sha = forensics.capture_source(
        r.content, url=URL, source_type="geoconfirmed_kml",
        title="GeoConfirmed -- Ukraine KML export (Google Earth)",
        description=(
            "Full country-wide KML/ZIP export, captured verbatim. Filtered "
            "to the Mariupol subset and spatially joined to the property "
            "spine by scripts/203_load_geoconfirmed.py."
        ),
        content_type=r.headers.get("Content-Type", "application/zip"),
        http_status=r.status_code, con=con,
    )
    log.info("Captured sha=%s bytes=%d -> run scripts/203 next", sha[:16], len(r.content))


if __name__ == "__main__":
    main()
