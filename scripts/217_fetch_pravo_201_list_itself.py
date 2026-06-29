#!/usr/bin/env python3
"""Follow-up to scripts/215's refined Decree No. 201 query -- same
frameset->searchlist->list_itself nesting as scripts/212-214, this time for
the refined query (naming Decree No. 26/09.01.2011, the decree No. 201 is
recalled to amend) instead of the original bare-numbers query that got
buried under unrelated newer "№ 201" acts.

Run:
    PYTHONPATH=src python scripts/217_fetch_pravo_201_list_itself.py
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
Q = ("Указ Президента 201 20.03.2020 26 09.01.2011 иностранные граждане "
     "земельные участки приграничные territории")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    con = forensics.open_state()
    s = requests.Session()
    s.headers.update({"User-Agent": config.USER_AGENT, "Accept-Language": "ru,en;q=0.8"})
    if config.PROXY:
        s.proxies.update({"http": config.PROXY, "https": config.PROXY})

    url = f"{BASE}?list_itself=&bpas=cd00000&intelsearch={quote(Q)}&sort=7&page=firstlast"
    log.info("Fetching %s", url)
    try:
        r = s.get(url, timeout=config.TIMEOUT, verify=config.SSL_VERIFY, allow_redirects=True)
    except requests.RequestException as e:
        log.error("  FAILED: %s -- retry from the VPS if connection/TLS error", e)
        return
    if r.status_code != 200:
        log.warning("  HTTP %d -- captured anyway for the record", r.status_code)
    sha = forensics.capture_source(
        r.content, url=url, source_type="crimea_decree_201_refined_list_itself",
        title="pravo.gov.ru ИПС list_itself (refined query) -- Указ №201 20.03.2020",
        description="Q12 -- actual hit list for the Decree No. 26-naming refined query.",
        content_type=r.headers.get("Content-Type", "text/html"),
        http_status=r.status_code, con=con,
    )
    log.info("  status=%d sha=%s bytes=%d", r.status_code, sha[:16], len(r.content))
    log.info("Done. Decode windows-1251, look for a row dated 20.03.2020.")


if __name__ == "__main__":
    main()
