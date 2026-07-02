#!/usr/bin/env python3
"""Stage 3 (batch loaders): load address_registry.jsonl, ownerless_decrees.jsonl
and ownerless_registry.jsonl into PostGIS as property / seizure_event rows.

Order matters: load_buildings() must run first so the property rows it
creates (keyed on building_id) exist for load_ownerless_decrees(),
load_ownerless_removals() and load_ownerless_registry() to attach
seizure_event rows to. load_ownerless_removals() reads the SAME
ownerless_decrees.jsonl (removal-kind rows) and attaches stage='reclaim'
events only to properties already on the spine (see its docstring). All are
idempotent (ON CONFLICT on building_id / dedup_key), so re-running this
script after re-running scripts 21/06/26 is safe.

NB: the 'reclaim' seizure_stage value must exist before this runs — apply
db/schema.sql first (its ALTER TYPE ... ADD VALUE IF NOT EXISTS 'reclaim').
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mariupol_seizures.db import load  # noqa: E402

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(message)s")
    load.load_buildings()
    load.load_ownerless_decrees()
    load.load_ownerless_removals()
    load.load_ownerless_registry()
