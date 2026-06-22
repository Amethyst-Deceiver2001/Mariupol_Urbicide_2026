#!/usr/bin/env python3
"""Stage 2i/2j: parse captured listings → residential-apartment SALE offers (Mariupol).

Reads the forensically-captured web listings (scripts/49) + Telegram messages
(scripts/50) out of the state DB and emits a unified offer record per item, keeping
ONLY offers to SELL a residential apartment in Mariupol (studios included; rooms,
houses, land, garages, commercial, rentals, and "wanted/куплю/сниму" are filtered
to an audit file). Local, no network — safe to iterate.

Outputs (data/parsed/, gitignored):
  - realestate_offers.jsonl    — the kept apartment-sale offers (with building_key
                                 join to the seizure spine + on_seizure_spine flag)
  - realestate_rejected.jsonl  — everything filtered out + the reason (filter audit)
  - data/reports/realestate_offers_report.md — counts, price stats, spine hits

PRIVACY: seller contact (phone/@username) is isolated under each offer's nested
`contact` object, marked `sensitive` for private individuals — drop wholesale in
any shared export (CLAUDE.md). data/ is gitignored.

    python3 scripts/51_parse_realestate_offers.py
"""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures.parse import realestate_offers  # noqa: E402

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    realestate_offers.run()
