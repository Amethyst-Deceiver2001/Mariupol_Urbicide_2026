#!/usr/bin/env python3
"""Stage 3 (companion): load the Russian federal damage/reconstruction tracker
(data/parsed/damage_assessment.jsonl) as corroboration(kind='mirror_source')
rows on the property spine. Idempotent via dedup_key; safe to re-run after
scripts/27_load_registry.py (which creates the address baseline most rows match).
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
    load.load_damage_assessment()
