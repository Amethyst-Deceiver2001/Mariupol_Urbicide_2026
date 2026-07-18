#!/usr/bin/env python3
"""Spot-check: for a sample of registry buildings that have NO captured
decree citation (see scripts/357's overlap measurement), search the site's
own document index directly by STREET NAME (not gated on any "бесхоз"
keyword, unlike scripts/346's systematic crawl) to see whether a plausible
originating decree exists that we simply haven't found/captured yet, vs.
genuinely doesn't exist on the portal at all.

This does NOT auto-classify or load anything -- it just captures + logs
title/URL hits per street for manual review (paste the output back for
comparison against the specific house/apartment numbers from scripts/357's
sample).

Reuses scripts/346's fetch/HOSTS/SEARCH_PATH/SEARCH_CC/DOC_LINK_RX/ATTACH_RX
mechanics via import (same site, same CMS, same TLS-trust caveat).

Run (from the VPS, per project convention — this hits the geoblocked site):
    PYTHONPATH=src python scripts/358_spotcheck_registry_decree_gap.py
"""
from __future__ import annotations

import importlib.util
import logging
import re
import sys
import time
from urllib.parse import quote
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from bs4 import BeautifulSoup  # noqa: E402

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

_spec = importlib.util.spec_from_file_location(
    "m346", str(ROOT / "scripts" / "346_crawl_ownerless_designation_postanovleniya.py"))
m346 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m346)

HOSTS = m346.HOSTS
SEARCH_PATH = m346.SEARCH_PATH
SEARCH_CC = m346.SEARCH_CC
DOC_LINK_RX = m346.DOC_LINK_RX
ATTACH_RX = m346.ATTACH_RX
fetch = m346.fetch

# Sample pulled 2026-07-18 from scripts/357's overlap measurement: registry
# buildings with NO ownerless_designation/ownerless_registration event on
# the same property_id. (street_name, house, building_id) for reference —
# only street_name is used as the search term (house-number-scoped search
# isn't reliably supported by the portal's search box; broader by design).
SAMPLE = [
    ("1-й Кальчик", "42", "STREET:1 кальчик|42"),
    ("Кристальная", "20", "STREET:кристальная|20"),
    ("Горная", "9", "STREET:горная|9"),
    ("Победы", "78", "AVENUE:победы|78"),
    ("Азовстальская", "158а", "STREET:азовстальская|158а"),
    ("Красноармейская", "20а", "STREET:красноармейская|20а"),
    ("Биологический массив", "64а", "STREET:биологический массив|64а"),
    ("50 лет Октября (Меотиды)", "30/17", "STREET:50 лет октября|30/17"),
    ("Консервная", "9", "STREET:консервная|9"),
    ("Ленинградский", "8", "LANE:ленинградский|8"),
    ("Халхингольская", "36", "STREET:халхингольская|36"),
    ("Азовстальская", "99", "STREET:азовстальская|99"),
    ("Котовского", "132", "STREET:котовского|132"),
    ("Мариупольская", "44", "STREET:мариупольская|44"),
    ("Воинов-Освободителей", "2/3", "STREET:воинов-освободителей|2/3"),
]


def search_street(host_key: str, street: str, cur_pos: int = 0):
    host = HOSTS[host_key]
    url = (f"{host}{SEARCH_PATH}?cc={SEARCH_CC}&document_search={quote(street)}"
           f"&document_category=&document_publication_date=&curPos={cur_pos}")
    content, content_type, status = fetch(url)
    if status != 200 or "html" not in content_type:
        return []
    soup = BeautifulSoup(content, "html.parser")
    hits = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if DOC_LINK_RX.search(href) or ATTACH_RX.search(href):
            hits.append((a.get_text(" ", strip=True) or "(no text)", href))
    return hits


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    for street, house, building_id in SAMPLE:
        log.info("=== %s, %s (building_id=%s) ===", street, house, building_id)
        any_hit = False
        for host_key in ("new", "old"):
            try:
                hits = search_street(host_key, street)
            except Exception:
                log.exception("search failed: host=%s street=%s", host_key, street)
                continue
            for text, href in hits:
                any_hit = True
                log.info("  [%s] %s -> %s", host_key, text[:100], href)
            time.sleep(1.0)
        if not any_hit:
            log.info("  (no hits on either host for this street name)")

    log.info("done. Paste this output back for review against the specific "
             "house/apartment numbers above.")


if __name__ == "__main__":
    main()
