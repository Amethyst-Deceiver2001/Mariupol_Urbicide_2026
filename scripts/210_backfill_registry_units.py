#!/usr/bin/env python3
"""One-off backfill: promote apt_raw/apt_kind already sitting in
seizure_event.detail JSONB (stage='registry_inclusion' rows loaded before the
`unit` table existed, db/schema.sql 2026-06-29) into structural `unit` rows +
seizure_event.unit_id. See db.load.backfill_registry_units for the full
docstring. Idempotent; safe to re-run. Default is a dry-run report; pass
--apply to write changes.

Run order: psql "$DATABASE_URL" -f db/schema.sql  (adds the unit table + column)
           PYTHONPATH=src python scripts/210_backfill_registry_units.py --apply
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
    load.backfill_registry_units(apply=args.apply)
