#!/usr/bin/env python3
"""Compute property.rd4u_category (A3.1/A3.2/A3.3/A3.6, comma-separated) from
the seizure_event/corroboration evidence already loaded. See
db.load.categorize_rd4u for the full categorization rules. Idempotent; safe to
re-run. Default is a dry-run report (writes data/reports/rd4u_categorization.csv);
pass --apply to write property.rd4u_category.
"""
import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures.db import load  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="write changes (default: dry-run report only)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(message)s")
    load.categorize_rd4u(apply=args.apply)
