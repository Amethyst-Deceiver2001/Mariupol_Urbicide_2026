#!/usr/bin/env python3
"""Stage 1g: capture the DNR-level legal framework from publication.pravo.gov.ru
block region80 (Донецкая Народная Республика) — the laws / указы / распоряжения /
постановления that authorise each rung of the dispossession pipeline.

Claude must NEVER run this. publication.pravo.gov.ru serves a Russian-CA TLS cert
and is geoblocked — run from the Russia-routed VPS with SSL_VERIFY=false.

Recommended first run:
    PYTHONPATH=src python scripts/35_crawl_pravo_region80.py --probe
to confirm the listing-API shape, then a full run:
    PYTHONPATH=src python scripts/35_crawl_pravo_region80.py
(captures the COMPLETE region80 index + the dispossession-relevant PDF subset;
add --all-pdfs to fetch every PDF, or --html to use the HTML listing fallback).

See src/mariupol_seizures/crawl/pravo_region80.py for the full design notes.
"""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures.crawl import pravo_region80  # noqa: E402

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    pravo_region80.main()
