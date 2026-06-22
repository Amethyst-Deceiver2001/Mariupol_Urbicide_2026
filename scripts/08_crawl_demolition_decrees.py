#!/usr/bin/env python3
"""Stage 1c: crawl demolition (снос) decrees from the Mariupol admin portal.

RUN FROM YOUR VPS ONLY — the portal is geoblocked outside Russia.

Captures the OLD-address side of the demolish→rebuild footprint crosswalk:
occupation administration постановления declaring buildings «аварийными и
подлежащими сносу» (emergency, subject to demolition), plus their scanned PDF
annexes listing the condemned addresses. These are the properties whose lots
are then handed to developer SPVs (e.g. ООО «СЗ-1 Порфир» / ЮгСтройИнвест)
without auction, and on which new buildings are erected under new addresses —
defeating RD4U restitution claims.

As of 2026-06-09: 6 decrees (2024-11 → 2026-05). Re-run weekly to catch new
demolition waves (the 1 July 2026 re-registration deadline is expected to
accelerate the cycle).

After running:
  1. PYTHONPATH=src python scripts/06a_ocr_decrees.py
     (now also handles demolition_decree_*_pdf source types)
  2. PYTHONPATH=src python scripts/09_parse_demolition_decrees.py  [to be built]

See src/mariupol_seizures/crawl/demolition_decrees.py for full design notes.
"""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures.crawl import demolition_decrees  # noqa: E402

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    demolition_decrees.run()
