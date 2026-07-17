#!/usr/bin/env python3
"""Stage 3 (batch loaders): load address_registry.jsonl, ownerless_decrees.jsonl,
ownerless_registry.jsonl, and avariinoe_decrees.jsonl into PostGIS as
property / seizure_event rows.

Order matters: load_buildings() must run first so the property rows it
creates (keyed on building_id) exist for load_ownerless_decrees(),
load_ownerless_removals(), load_ownerless_registry() and
load_avariinoe_designation() to attach seizure_event rows to.
load_ownerless_removals() reads the SAME ownerless_decrees.jsonl
(removal-kind rows) and attaches stage='reclaim' events only to properties
already on the spine (see its docstring). All are idempotent (ON CONFLICT
on building_id / dedup_key), so re-running this script after re-running
scripts 21/06/26/354 is safe.

NB: the 'reclaim'/'avariinoe_designation' seizure_stage values must exist
before this runs — apply db/schema.sql first (its ALTER TYPE ...
ADD VALUE IF NOT EXISTS statements).

load_avariinoe_designation() is skipped (with a log line) if
data/parsed/avariinoe_decrees.jsonl doesn't exist yet — scripts/351/354 are
optional and newer than the rest of this pipeline.
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mariupol_seizures import config  # noqa: E402
from mariupol_seizures.db import load  # noqa: E402

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(message)s")
    load.load_buildings()
    load.load_ownerless_decrees()
    load.load_ownerless_removals()
    load.load_ownerless_registry()
    if (config.PROJECT_ROOT / "data" / "parsed" / "avariinoe_decrees.jsonl").exists():
        load.load_avariinoe_designation()
    else:
        logging.getLogger(__name__).info(
            "data/parsed/avariinoe_decrees.jsonl not found — skipping "
            "load_avariinoe_designation (run scripts/351 + scripts/354 first)")
