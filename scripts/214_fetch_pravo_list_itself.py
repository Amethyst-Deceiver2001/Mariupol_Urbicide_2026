#!/usr/bin/env python3
"""Follow-up to scripts/213: that script's "searchlist" fetch turned out to
be ANOTHER frame wrapper, not the results -- it embeds a third, nested
iframe:

    <iframe id="list" src="?list_itself=&bpas=cd00000&intelsearch=<query>&sort=7&page=first">

(confirmed by reading the captured searchlist HTML directly -- this is the
actual document hit list; "searchlist" was the results-PAGE chrome,
"list_itself" is the list content). This is the pravo.gov.ru ИПС engine's
three-frame nesting: frameset (212) -> searchlist page chrome (213) ->
list_itself results (this script). If this STILL turns out to be another
wrapper, read it the same way before assuming it's final.

Run:
    PYTHONPATH=src python scripts/214_fetch_pravo_list_itself.py
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
    {
        "q": "Указ Президента 201 20.03.2020",
        "source_type": "crimea_decree_201_list_itself",
        "title": "pravo.gov.ru ИПС list_itself -- Указ Президента РФ №201 от 20.03.2020",
        "description": "Q12 follow-up -- the actual document hit list (3rd-level frame).",
    },
    {
        "q": "Федеральный конституционный закон 4 15.12.2025",
        "source_type": "fkz4_list_itself",
        "title": "pravo.gov.ru ИПС list_itself -- ФКЗ-4 от 15.12.2025",
        "description": "Q13 follow-up -- the actual document hit list (3rd-level frame).",
    },
]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    con = forensics.open_state()
    s = requests.Session()
    s.headers.update({"User-Agent": config.USER_AGENT, "Accept-Language": "ru,en;q=0.8"})
    if config.PROXY:
        s.proxies.update({"http": config.PROXY, "https": config.PROXY})

    for t in QUERIES:
        url = f"{BASE}?list_itself=&bpas=cd00000&intelsearch={quote(t['q'])}&sort=7&page=first"
        log.info("Fetching %s", url)
        try:
            r = s.get(url, timeout=config.TIMEOUT, verify=config.SSL_VERIFY, allow_redirects=True)
        except requests.RequestException as e:
            log.error("  FAILED: %s -- retry from the VPS if connection/TLS error", e)
            continue

        if r.status_code != 200:
            log.warning("  HTTP %d for %s -- captured anyway for the record", r.status_code, url)

        sha = forensics.capture_source(
            r.content, url=url, source_type=t["source_type"],
            title=t["title"], description=t["description"],
            content_type=r.headers.get("Content-Type", "text/html"),
            http_status=r.status_code, con=con,
        )
        log.info("  status=%d sha=%s bytes=%d", r.status_code, sha[:16], len(r.content))

    log.info("Done. Decode windows-1251 before reading. Look for individual "
              "document rows (title/date/number text + a real document link, "
              "likely /document/view/<id> or similar) -- that link is the "
              "next and hopefully final fetch target.")


if __name__ == "__main__":
    main()
