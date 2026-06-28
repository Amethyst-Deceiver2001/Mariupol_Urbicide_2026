#!/usr/bin/env python3
"""Capture the Bellingcat "Civilian Harm in Ukraine" timemap dataset --
discovered 2026-06-28 (user-supplied URL), a structured, geocoded, dated,
sourced incident feed (id/date/location/lat/lon/description/impact/
weapon_system/sources/graphic), 2,517 records spanning 2022-02-24 to
2025-07-09 at capture time, country-wide.

Hosted on a plain DigitalOcean Spaces CDN -- NOT Russian/occupation
infrastructure, not geoblocked. Safe for Claude to run directly (unlike
court_crawler.py / ownerless_lists.py).

Tier-3 corroboration candidate (docs/tier3_corroboration_design.md) --
independent of UNOSAT, occupation records, and this project's own crawls.
21 of the 2,517 records explicitly name Mariupol (filtered by
scripts/199_load_bellingcat_civharm.py at load time; this script captures
the FULL feed verbatim, since it's small and re-running the filter later
costs nothing).

Caveat up front (see scripts/199 for the spatial-join handling): most
records carry city-wide approximate coordinates, not building-precise
geocoding -- several Mariupol records sit 1-18km from the nearest spine
property (mass graves, the airport, a filtration camp) and must NOT be
force-matched to a property. Treat any match beyond ~100m as noise.

Run:
    PYTHONPATH=src python scripts/198_fetch_bellingcat_civharm.py
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

URL = "https://bellingcat-embeds.ams3.cdn.digitaloceanspaces.com/production/ukr/timemap/api.json"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    con = forensics.open_state()
    s = requests.Session()
    s.headers.update({"User-Agent": config.USER_AGENT})

    log.info("Fetching %s", URL)
    r = s.get(URL, timeout=config.TIMEOUT)
    r.raise_for_status()

    sha = forensics.capture_source(
        r.content, url=URL, source_type="bellingcat_civharm_timemap",
        title="Bellingcat Civilian Harm in Ukraine -- timemap feed",
        description=(
            "Full country-wide incident feed, captured verbatim. Filtered to "
            "the Mariupol subset and spatially joined to the property spine "
            "by scripts/199_load_bellingcat_civharm.py."
        ),
        content_type=r.headers.get("Content-Type", "application/json"),
        http_status=r.status_code, con=con,
    )
    log.info("Captured sha=%s bytes=%d -> run scripts/199 next", sha[:16], len(r.content))


if __name__ == "__main__":
    main()
