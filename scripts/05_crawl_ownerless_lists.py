#!/usr/bin/env python3
"""Stage 1b: crawl Tier-1 'ownerless property' registers. RUN FROM YOUR VPS ONLY.

Captures the upstream of the court docket: the Mariupol municipal
administration's own published "ownerless property" lists (district XLSX
registries + numbered designation/removal decrees). See
docs/pre_petition_sourcing.md for why this source matters and
src/mariupol_seizures/crawl/ownerless_lists.py for what gets captured.

Re-run periodically (e.g. weekly, matching the reported designation cadence)
— each run captures new dated snapshots without disturbing prior ones.
"""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures.crawl import ownerless_lists  # noqa: E402

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    ownerless_lists.run()
