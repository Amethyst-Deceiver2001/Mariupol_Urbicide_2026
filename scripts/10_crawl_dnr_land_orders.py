#!/usr/bin/env python3
"""Stage 1d: crawl DNR head's land-allocation распоряжения for Mariupol.

Captures the RIGHT-HAND side of the demolish→rebuild footprint crosswalk:
распоряжения Главы ДНР allocating cleared Mariupol land parcels to developer
SPVs without auction ("в аренду без проведения торгов").

Each order names a beneficiary (accountability-track subject), a cadastral
number, and a land parcel address — the same footprint that previously held
a designated-ownerless or demolished building.

The portal (https://xn--80azg.xn--80ahqgjaddr.xn--p1ai/) is not geoblocked,
but run from the VPS to keep all capture provenance uniform.

Developer beneficiaries found by reconnaissance (2026-06-09):
  ООО СЗ ЭВОЛДОМ-5              ≥7 orders (2025-06 → 2025-11)
  АО «ЭВЕРЕСТ ДОМОСТРОЕНИЕ»      распоряжение №192, 05.06.2026
                                  cadastral 93:37:0010318:779
                                  ул. Станиславского 56, 17 552 m²

Also captures Указ №420 (30.07.2022) «концепция разработки генплана
Мариуполя» — the top-of-chain legal authority for the programme.

After running:
  Build scripts/11_parse_dnr_land_orders.py to extract beneficiary + cadastral
  from source_type='dnr_land_order' and load into the actor / financial tables.

See src/mariupol_seizures/crawl/dnr_land_orders.py for full design notes.
"""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures.crawl import dnr_land_orders  # noqa: E402

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    dnr_land_orders.run()
