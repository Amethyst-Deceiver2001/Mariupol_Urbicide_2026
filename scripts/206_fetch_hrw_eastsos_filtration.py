#!/usr/bin/env python3
"""Capture the HRW property-seizure report and the East SOS entry-ban
appeal -- the primary sources behind the project's "sham process" /
filtration argument (reconceptualization_2026.md Tier 3, S7), resolved
2026-06-28 from the outsourced research report
(docs/research_outsourcing/mariupol_urbicide_research_aggregation.md Q5).

Two captures, both reachable Western-NGO sites (hrw.org / east-sos.org --
NOT Russian/occupation infrastructure, not geoblocked, safe for Claude to
run directly):

1. Human Rights Watch, "Ukraine: Russia Illegally Seizing Property in
   Occupied Areas" (26 May 2026). This is far more than the entry-ban
   citation: HRW independently describes the SAME seizure lifecycle this
   project documents (property designated "ownerless" -> owner must appear
   in person with Russian citizenship to contest -> court transfers title
   to the municipality -> reassignment to Russian citizens), and states it
   "reviewed approximately 8,000 such court cases filed between March 2024
   and January 2026" -- an external, independent corroboration of this
   project's own ~8,300-case court corpus. It is the source that REPORTS,
   and correctly attributes, the entry-ban figures:

     - "Russian authorities reported that between October 2023 and April
       2025, 30,000 Ukrainians were denied entry and issued entry bans
       ranging from 20 to 50 years." (attributed to RUSSIAN AUTHORITIES --
       a self-incrimination figure, not an NGO estimate)
     - "According to the Ukrainian civil society group East SOS, only one
       out of every four people undergoing this 'filtration' process is
       allowed to proceed." (the 1-in-4 ratio -- attributed to East SOS)

   This CORRECTS reconceptualization_2026.md:85, which had attributed BOTH
   figures to East SOS. See the doc edit accompanying this script.

2. East SOS, "APPEAL on entry restrictions for Ukrainian citizens from
   third countries by the Russian Federation" (16 Oct 2023). Per the
   research report, this is narrative context on the route closures
   (Sheremetyevo-only entry), NOT a structured dataset and NOT the source
   of the 30k/ban-length numbers. Captured as primary context for the
   entry-restriction regime; do not cite it for the numeric figures.

Run:
    PYTHONPATH=src python scripts/206_fetch_hrw_eastsos_filtration.py
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

SOURCES = [
    {
        "url": "https://www.hrw.org/news/2026/05/26/"
               "ukraine-russia-illegally-seizing-property-in-occupied-areas",
        "source_type": "hrw_property_seizure_report",
        "title": "HRW -- Ukraine: Russia Illegally Seizing Property in Occupied Areas (26 May 2026)",
        "description": (
            "Independent HRW documentation of the same ownerless->court->"
            "reassignment seizure lifecycle this project tracks; reports "
            "reviewing ~8,000 such court cases (Mar 2024-Jan 2026); reports "
            "the Russian-authorities 30,000-denied-entry / 20-50-yr-ban "
            "figure and the East SOS 1-in-4 filtration ratio. Primary source "
            "for reconceptualization_2026.md Tier-3 S7."
        ),
    },
    {
        "url": "https://east-sos.org/en/publications/"
               "appeal-on-entry-restrictions-for-ukrainian-citizens-"
               "from-third-countries-by-the-russian-federation/",
        "source_type": "eastsos_entry_restrictions_appeal",
        "title": "East SOS -- Appeal on entry restrictions for Ukrainian citizens (16 Oct 2023)",
        "description": (
            "East SOS narrative appeal on Russia restricting Ukrainian entry "
            "to occupied territory to Sheremetyevo-only routes. Context for "
            "the entry-restriction regime; NOT a structured dataset and NOT "
            "the source of the 30k/ban-length numbers (those are Russian-"
            "authorities figures via HRW)."
        ),
    },
]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    con = forensics.open_state()
    s = requests.Session()
    s.headers.update({"User-Agent": config.USER_AGENT})

    for src in SOURCES:
        log.info("Fetching %s", src["url"])
        try:
            r = s.get(src["url"], timeout=config.TIMEOUT, allow_redirects=True)
            r.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            log.error("FAILED %s -- %s", src["url"], exc)
            continue
        sha = forensics.capture_source(
            r.content, url=src["url"], source_type=src["source_type"],
            title=src["title"], description=src["description"],
            content_type=r.headers.get("Content-Type", "text/html"),
            http_status=r.status_code, con=con,
        )
        log.info("Captured sha=%s bytes=%d (%s)", sha[:16], len(r.content), src["source_type"])


if __name__ == "__main__":
    main()
