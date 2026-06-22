#!/usr/bin/env python3
"""Capture ЕИСЖС object detail for an explicit list of 5-digit object IDs.

Why: the existing scripts/17 crawl enumerates ЖК via the kn/devGk API
(place=0-1158), which only surfaces 5 ЖК / 20 objects -- far short of the 91
listings on the public "Новостройки в Мариуполе" catalog page
(https://xn--80az8a.xn--d1aqf.xn--p1ai/новостройки/...). Each card/pin on
that page links to /сервисы/каталог-новостроек/объект/<id>.

Usage:
    1. On the catalog page (in browser), collect object IDs, e.g. via the
       console snippet:
           [...new Set([...document.querySelectorAll('a[href*="/объект/"]')]
               .map(a => a.href.match(/объект\\/(\\d+)/)?.[1])
               .filter(Boolean))]
       (scroll/paginate through all 91 results first, repeat and merge sets
       as needed)
    2. Save the IDs one per line to a text file, e.g. data/manual/eisghs_object_ids.txt
    3. Run this script (from the Russia-routed VPS, per CLAUDE.md):
           python scripts/72_crawl_eisghs_by_ids.py data/manual/eisghs_object_ids.txt
    4. Re-run scripts/18_parse_eisghs_mariupol.py and scripts/71_export_eisghs_newbuilds.py

Output is captured into the same raw store / done-flags as scripts/17, so
re-running is safe and idempotent (already-captured IDs are skipped).
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
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} <ids_file.txt>")

    ids_path = Path(sys.argv[1])
    ids = [line.strip() for line in ids_path.read_text(encoding="utf-8").splitlines()]
    ids = [i for i in ids if i and i.isdigit()]
    if not ids:
        raise SystemExit(f"no numeric IDs found in {ids_path}")

    eisghs_mariupol.run_by_ids(ids)
