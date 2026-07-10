#!/usr/bin/env python3
"""Stage 3 (non-residential track): load commercial/industrial seizures.

Loads the two non-residential source families onto the same building spine the
residential pipeline uses, tagging genuinely non-residential buildings with
property.property_kind and recording each object's premises class / object type
in the seizure_event detail:

  ownerless-signs designation -> seizure_event(stage='ownerless_designation'):
    - MinStroy commercial/industrial "признаки бесхозности" lists (scripts/290)
      1,277 objects: shops/cafes/salons embedded in residential buildings +
      standalone commercial + 11 industrial parcels with cadastral numbers.

  demolition -> seizure_event(stage='demolition'):
    - Citywide non-residential demolition list «Снос.pdf» (scripts/291)
      42 objects: shopping centres, hotels, warehouses, a bakery, a telecoms
      building, an entertainment complex, a DOSAAF building.

Run AFTER scripts/27 (load_buildings) so events attach to existing property
rows where the address already matches a residential building; otherwise a
minimal property row is created. Both loaders are idempotent (dedup_key), so
re-running after re-parsing is safe.

Requires the property.property_kind column — apply db/schema.sql first
(it carries the idempotent ALTER TABLE ... ADD COLUMN IF NOT EXISTS migration).
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
    load.load_nonresidential_ownerless()
    load.load_nonresidential_demolition()
