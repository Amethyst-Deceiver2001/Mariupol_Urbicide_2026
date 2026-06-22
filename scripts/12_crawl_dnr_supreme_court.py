#!/usr/bin/env python3
"""Stage 1e: capture DNR Supreme Court appellate rulings on housing/demolition disputes.

Captures case 33-2575/2025 (already identified by manual reconnaissance) plus
searches the civil docket for similar demolition/housing rights cases.

These rulings document the full demolish→rebuild lifecycle from the victim's
perspective and prove the occupation courts denied residents' property rights —
satisfying the Rome Statute exhaustion-of-remedies element.

After running:
  Build scripts/13_parse_dnr_supreme_court.py to extract the lifecycle facts,
  actor names, and GKO order references from the captured HTML.

See src/mariupol_seizures/crawl/dnr_supreme_court.py for full design notes.
"""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures.crawl import dnr_supreme_court  # noqa: E402

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    dnr_supreme_court.run()
