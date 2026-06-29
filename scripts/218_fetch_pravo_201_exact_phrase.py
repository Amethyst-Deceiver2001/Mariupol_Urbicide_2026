#!/usr/bin/env python3
"""Follow-up to scripts/217: that refined query's hit list (20 results,
read directly) turned out to be EVERY federal act dated 20.03.2020 --
orders, government resolutions, directives -- with no Presidential decree
among them at all. The free-text scoring is matching the bare date token
across thousands of unrelated documents; adding more keywords didn't help
because they're being OR'd in, not required.

This tries an exact double-quoted phrase instead (many ИПС/ConsultantPlus-
style engines support "..." for phrase match, which should target the
specific title format directly rather than scoring loose keyword overlap).

Run:
    PYTHONPATH=src python scripts/218_fetch_pravo_201_exact_phrase.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import requests  # noqa: E402
import urllib3  # noqa: E402

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

if not config.SSL_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE = "http://pravo.gov.ru/proxy/ips/"

QUERIES = [
    '"Указ Президента Российской Федерации от 20 марта 2020 г. № 201"',
    '"Указ Президента Российской Федерации от 20.03.2020 № 201"',
]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    con = forensics.open_state()
    s = requests.Session()
    s.headers.update({"User-Agent": config.USER_AGENT, "Accept-Language": "ru,en;q=0.8"})
    if config.PROXY:
        s.proxies.update({"http": config.PROXY, "https": config.PROXY})

    for i, q in enumerate(QUERIES):
        # Go straight for list_itself -- skip the frameset/searchlist hops,
        # they're just chrome wrappers around this same query string.
        url = f"{BASE}?list_itself=&bpas=cd00000&intelsearch={quote(q)}&sort=7&page=first"
        log.info("Fetching %s", url)
        try:
            r = s.get(url, timeout=config.TIMEOUT, verify=config.SSL_VERIFY, allow_redirects=True)
        except requests.RequestException as e:
            log.error("  FAILED: %s -- retry from the VPS if connection/TLS error", e)
            continue
        if r.status_code != 200:
            log.warning("  HTTP %d -- captured anyway for the record", r.status_code)
        sha = forensics.capture_source(
            r.content, url=url, source_type=f"crimea_decree_201_exact_phrase_{i}",
            title=f"pravo.gov.ru ИПС list_itself (exact phrase {i}) -- Указ №201 20.03.2020",
            description="Q12 -- exact double-quoted phrase attempt, after free-text scoring failed in scripts/217.",
            content_type=r.headers.get("Content-Type", "text/html"),
            http_status=r.status_code, con=con,
        )
        log.info("  status=%d sha=%s bytes=%d", r.status_code, sha[:16], len(r.content))

    log.info("Done. If both come back empty/no-match (a real possibility -- "
              "the engine may not support quoted phrases, or my recollection "
              "that No. 201 amends No. 26/09.01.2011 may be wrong), the next "
              "step is a HUMAN browser session over the VPS rather than more "
              "scripted query guessing -- diminishing returns past this "
              "point.")


if __name__ == "__main__":
    main()
