#!/usr/bin/env python3
"""Stage 1: crawl court portals. RUN FROM YOUR VPS ONLY."""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mariupol_seizures.crawl import court_crawler

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    court_crawler.run()
