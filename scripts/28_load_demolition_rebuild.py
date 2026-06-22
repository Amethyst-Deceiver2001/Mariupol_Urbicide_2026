#!/usr/bin/env python3
"""Stage 3 (demolish->rebuild modality): load the address-laundering track.

Old side  -> seizure_event(stage='demolition'):
  - MinStroy/ГКО demolition register (the structured bulk, ~525 Mariupol bldgs)
  - Mariupol-admin demolition decrees ('о сносе') + their signing officials
New side  -> seizure_event(stage='reallocation') + beneficiary actors:
  - ЕИСЖС/наш.дом.рф new-builds (developer + sales data, footprint endpoint)
  - DNR land-allocation orders (the SPV beneficiary roster, INN-keyed)

Displacement impact -> corroboration(kind='displacement_claim'), BUILDING-LEVEL
counts only (no per-person PII; see db/load.load_housing_distribution). Runs
only if scripts/29 has produced housing_distribution.jsonl.

Run AFTER scripts/27 (load_buildings creates the property rows these events
attach to). All loaders are idempotent (dedup_key / INN identity), so re-running
after re-parsing any source is safe.
"""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures.db import load  # noqa: E402

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(message)s")
    load.load_demolition_register()
    load.load_demolition_decrees()
    load.load_eisghs_newbuilds()
    load.load_land_order_beneficiaries()
    # Displacement aggregates (privacy-gated) -- only if scripts/29 has run.
    if (ROOT / "data" / "parsed" / "housing_distribution.jsonl").exists():
        load.load_housing_distribution()
    else:
        logging.info("housing_distribution.jsonl absent -- run scripts/29 to load "
                     "building-level displacement aggregates; skipping.")
