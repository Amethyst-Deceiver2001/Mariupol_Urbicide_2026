#!/usr/bin/env python3
"""Stage 3 (companion): load appeal/cassation seizure_events (cont4 ЖАЛОБА
blocks) for cases already in court_case. Idempotent via dedup_key; safe to
re-run after re-parsing data/parsed_cases.jsonl. Run AFTER scripts/03_load.py.
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
    load.load_appeals()
