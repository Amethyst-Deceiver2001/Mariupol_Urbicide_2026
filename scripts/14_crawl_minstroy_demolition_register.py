#!/usr/bin/env python3
"""Stage 1g: capture DNR Ministry of Construction Unified Demolition Register.

Source: https://minstroy-dpr.gosuslugi.ru/opendata/
Dataset: 7710474375-minstroydpropendatasnos («Единый реестр зданий и сооружений,
подлежащих сносу»)

Key findings (confirmed 09.06.2026 reconnaissance):
  - 637 rows in current version (March 2026); 525 are Mariupol buildings
  - GKO ДНР Распоряжение №56 (29.09.2022): 177 Mariupol buildings fully listed
  - пр-т Нахимова д.82 confirmed in №56 (row 295) — Нахимова→Черноморский 1Б crosswalk
  - 12 пр-т Ленина buildings under №56 (rows 247–258, Жовтневый district)
    are the candidate addresses for ТСЖ «Троянда-М» (case 2-259/2025 et al.)
  - Files are accessible without Russian routing (unlike court portals)
    but captured via VPS for uniform provenance

After capturing, run 15_parse_minstroy_demolition_register.py to load the
address list into the demolition_decree table and run the crosswalk join.

See src/mariupol_seizures/crawl/minstroy_demolition_register.py for details.
"""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures.crawl import minstroy_demolition_register  # noqa: E402

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    minstroy_demolition_register.run()
