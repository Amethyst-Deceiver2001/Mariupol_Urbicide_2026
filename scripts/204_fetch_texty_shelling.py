#!/usr/bin/env python3
"""Capture the Texty.org.ua "Under attack: what and when Russia shelled
Ukraine" dataset -- discovered 2026-06-28 via the `osint-geo-extractor`
PyPI package's downloader source (github.com/conflict-investigations/
osint-geo-extractor/blob/master/geo_extractor/downloaders/texty.py), which
documents the live public Google Sheets CSV export behind the project:

    https://texty.org.ua/projects/107577/under-attack-what-and-when-russia-shelled-ukraine/

texty.org.ua is a Ukrainian data-journalism outlet; this is a country-wide,
ongoing, sourced incident log distinct in methodology and team from every
other Tier-3 layer this project has built (own crawls, UNOSAT, Bellingcat,
Eyes on Russia, GeoConfirmed) -- a SIXTH independent provenance family.
Notably it carries a free-text `adress` (sic) column, unlike the other
feeds, which is informational context in the loader (scripts/205) but not
used for matching (no rapidfuzz pass yet -- see docs/research_outsourcing
candidates).

Hosted on docs.google.com -- not Russian/occupation infrastructure, not
geoblocked, safe for Claude to run directly. CAVEAT, confirmed at capture
time: roughly a fifth of Mariupol rows carry whole-degree lat/lon (e.g.
"47,38" -- city-level, not strike-level precision); scripts/205 filters
those out before any spatial join.

Run:
    PYTHONPATH=src python scripts/204_fetch_texty_shelling.py
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

URL = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vSyFuA7nxANnn7BwXn7az5D5L-V7yKnETgTybfKSIGmoYz2qVkc6FWSH7f0l-1Gt_dML1VpywPUzXwp/"
    "pub?gid=1376631421&single=true&output=csv"
)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    con = forensics.open_state()
    s = requests.Session()
    s.headers.update({"User-Agent": config.USER_AGENT})

    log.info("Fetching %s", URL)
    r = s.get(URL, timeout=config.TIMEOUT, allow_redirects=True)
    r.raise_for_status()

    sha = forensics.capture_source(
        r.content, url=URL, source_type="texty_shelling_csv",
        title="Texty.org.ua -- Under attack: what and when Russia shelled Ukraine",
        description=(
            "Full country-wide CSV export, captured verbatim. Filtered to "
            "the Mariupol/precise-coordinate subset and spatially joined "
            "to the property spine by scripts/205_load_texty_shelling.py."
        ),
        content_type=r.headers.get("Content-Type", "text/csv"),
        http_status=r.status_code, con=con,
    )
    log.info("Captured sha=%s bytes=%d -> run scripts/205 next", sha[:16], len(r.content))


if __name__ == "__main__":
    main()
