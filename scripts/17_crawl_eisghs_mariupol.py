#!/usr/bin/env python3
"""Stage 1i: capture Mariupol new-construction objects from ЕИСЖС (наш.дом.рф).

Source: xn--80az8a.xn--d1aqf.xn--p1ai (наш.дом.рф)
        /новостройки/мариуполь/  — geoblocked; run from Russia-routed VPS only.

What this captures:
  1. All МКД construction objects in ДНР (region 93) matching Мариуполь
  2. Objects by РКС-Девелопмент ИНН 9310007980 (decree №291 / Дом с часами)
  3. Objects on the three target cadastrals (93:37:0010106:91, :92, :107:91)
  4. Project name search for «Дом с часами»
  5. Full object detail for every discovered object

Primary goal: identify the postal address of the replacement building on the
ТСЖ «Троянда-М» demolition site, then back-trace to confirm which of the 12
пр-т Ленина candidates (GKO №56) is the original building.

After capture, run 18_parse_eisghs_mariupol.py to extract the address table
and join it against minstroy_demolition_register.jsonl + dnr_land_orders.jsonl.
"""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures.crawl import eisghs_mariupol  # noqa: E402

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    eisghs_mariupol.run()
