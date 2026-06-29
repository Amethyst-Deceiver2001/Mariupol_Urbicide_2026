#!/usr/bin/env python3
"""Follow-up to scripts/212: that script's two ИПС search fetches each came
back as a tiny (~1.5-1.7KB) <frameset> shell, not the results -- the real
hit list lives in a child frame, loaded separately by the browser at

    ?searchlist=&bpas=cd00000&intelsearch=<query>&sort=7

(same path, same query string, just "searchlist" instead of "searchres" as
the first param name). scripts/212 captured the frameset wrapper; this
fetches the frame src URL directly to get the actual results list. Confirmed
by reading the captured frameset HTML: each one's
<frame src="?searchlist=...&intelsearch=...&sort=7" name="topmenu"> is the
results frame; the second <frame src="about:blank" name="contents"> is just
the (empty until a result is clicked) detail pane -- not fetchable
meaningfully on its own.

Run:
    PYTHONPATH=src python scripts/213_fetch_pravo_searchlist_results.py
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
        "source_type": "crimea_decree_201_searchlist",
        "title": "pravo.gov.ru ИПС searchlist -- Указ Президента РФ №201 от 20.03.2020",
        "description": "Q12 follow-up -- actual results frame, not the frameset shell scripts/212 got.",
    },
    {
        "q": "Федеральный конституционный закон 4 15.12.2025",
        "source_type": "fkz4_searchlist",
        "title": "pravo.gov.ru ИПС searchlist -- ФКЗ-4 от 15.12.2025",
        "description": "Q13 follow-up -- actual results frame, not the frameset shell scripts/212 got.",
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
        url = f"{BASE}?searchlist=&bpas=cd00000&intelsearch={quote(t['q'])}&sort=7"
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

    log.info("Done. Next: read each captured results-list HTML (windows-1251 "
              "encoded -- decode before grepping Cyrillic) for a document "
              "link/id matching the target instrument. Paste back what each "
              "one contains -- if it's a real hit list, the next script "
              "fetches the document's own page by that id; if it's still "
              "empty/no-match, that's also useful (confirms this search "
              "engine doesn't index decrees pre-dating some cutoff, or that "
              "the query phrasing needs adjusting).")


if __name__ == "__main__":
    main()
