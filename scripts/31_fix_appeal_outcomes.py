#!/usr/bin/env python3
"""Stage 3 (companion): reconcile court_case.outcome with later appeal
results. Adds court_case.final_outcome (NULL = unchanged from outcome) and
flags any court_transfer seizure_event whose underlying grant was reversed
on appeal. Idempotent; safe to re-run after re-loading appeals (script 30).
Run AFTER scripts/30_load_appeals.py.
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
    load.reconcile_appeal_outcomes()
