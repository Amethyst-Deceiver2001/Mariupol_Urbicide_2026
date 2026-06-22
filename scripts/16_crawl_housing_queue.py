#!/usr/bin/env python3
"""Stage 1h: capture Mariupol occupation housing queue and distribution lists.

Source: mariupol-r897.gosweb.gosuslugi.ru/dlya-zhiteley/poleznye-materialy/kvartirnaya-ochered/

Two living documents (overwritten in place, dated filename changes each update):
  1. Квартирная очередь (queue list) — XLSX + PDF
     Occupation's own acknowledgment that specific persons lost housing.
     PRIVACY: contains victim PII → secured owner table; never commit.

  2. Распределение жилья (distribution list) — XLSX + PDF
     Who was allocated what replacement unit — the output of the demolish→rebuild
     pipeline.  Parsing this closes the old-address → new-address chain for
     cases like ТСЖ «Троянда-М».

Not geoblocked, but run via VPS for uniform provenance.
Re-run at minimum weekly; daily in July 2026 (01.07.2026 re-registration deadline).

After capturing, run 17_parse_housing_queue.py to extract the distribution
address table and join it against minstroy_demolition_register.jsonl.
"""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures.crawl import housing_queue  # noqa: E402

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    housing_queue.run()
