#!/usr/bin/env python3
"""Stage 3 (companion): re-derive building_id for every property using the
2026-06-11 normalization fixes (normalize/address.py, normalize/toponym.py)
and merge/rename rows whose recomputed building_id now matches another row --
the 40 (of 98) corroboration_candidates.csv near-miss pairs that converged.
See db.load.merge_duplicate_properties for the full algorithm. Idempotent;
safe to re-run. Default is a dry-run report; pass --apply to write changes.
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
    load.merge_duplicate_properties(apply=args.apply)
