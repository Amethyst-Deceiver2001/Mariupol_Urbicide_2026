#!/usr/bin/env python3
"""Stage 1i: capture Mariupol residential-apartment SALE listings (web marketplaces).

Demand-side [F]-resale evidence: seized/rebuilt flats being resold to the
occupier's population. Forensic capture only — the residential-apartment-only /
sell-only filter runs in scripts/51_parse_realestate_offers.py (capture before parse).

Targets, pagination, and caps live in config (REALESTATE_TARGETS,
REALESTATE_MAX_PAGES, REALESTATE_MAX_DETAIL). Most marketplaces are anti-bot and
geoblocked — RUN FROM THE VPS (config.PROXY). Claude must never run this (CLAUDE.md).

Usage (on the VPS):
    python3 scripts/49_crawl_realestate_listings.py            # all targets
    python3 scripts/49_crawl_realestate_listings.py avito cian # subset by key

Re-run periodically; the dated-snapshot sequence is a demand-velocity series.
"""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures.crawl import realestate_listings  # noqa: E402

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    only = sys.argv[1:] or None
    realestate_listings.run(only=only)
