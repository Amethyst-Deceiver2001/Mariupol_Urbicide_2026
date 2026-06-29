#!/usr/bin/env python3
"""Follow-up to scripts/215: the "docbody" fetch for ФКЗ-4 (nd=609234940)
returned only toolbar/JS chrome, no article text -- confirmed by reading the
captured HTML directly (no "Статья" string anywhere, no document-text div
populated). The page's own UI loads the real text two other ways, both
visible as literal links/onclick handlers in that same captured HTML:

    print:  ?docview&page=1&print=1&nd=609234940&rdk=0&&empire=
    RTF:    ?savertf=&link_id=3&nd=609234940&bpa=cd00000&bpas=cd00000
            &intelsearch=<query>&firstDoc=1&page=all

Try both -- whichever returns real article text (grep for "Статья 1" etc
after decoding) is the one to standardize on for future pravo.gov.ru
captures via this ИПС engine.

Run:
    PYTHONPATH=src python scripts/216_fetch_pravo_doc_rtf_print.py
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
ND = "609234940"
Q = quote("Федеральный конституционный закон 4 15.12.2025")

TARGETS = [
    {
        "url": f"{BASE}?docview&page=1&print=1&nd={ND}&rdk=0&&empire=",
        "source_type": "fkz4_print_view",
        "title": "ФКЗ-4 от 15.12.2025 -- print view (attempt at real text)",
        "content_type": "text/html",
    },
    {
        "url": f"{BASE}?savertf=&link_id=3&nd={ND}&bpa=cd00000&bpas=cd00000&intelsearch={Q}&firstDoc=1&page=all",
        "source_type": "fkz4_rtf_export",
        "title": "ФКЗ-4 от 15.12.2025 -- RTF export (attempt at real text)",
        "content_type": "application/rtf",
    },
]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    con = forensics.open_state()
    s = requests.Session()
    s.headers.update({"User-Agent": config.USER_AGENT, "Accept-Language": "ru,en;q=0.8"})
    if config.PROXY:
        s.proxies.update({"http": config.PROXY, "https": config.PROXY})

    for t in TARGETS:
        log.info("Fetching %s", t["url"])
        try:
            r = s.get(t["url"], timeout=config.TIMEOUT, verify=config.SSL_VERIFY, allow_redirects=True)
        except requests.RequestException as e:
            log.error("  FAILED: %s -- retry from the VPS if connection/TLS error", e)
            continue
        if r.status_code != 200:
            log.warning("  HTTP %d for %s -- captured anyway for the record", r.status_code, t["url"])
        sha = forensics.capture_source(
            r.content, url=t["url"], source_type=t["source_type"], title=t["title"],
            description="Q13 -- attempting to retrieve FKZ-4's actual article text.",
            content_type=r.headers.get("Content-Type", t["content_type"]),
            http_status=r.status_code, con=con,
        )
        log.info("  status=%d sha=%s bytes=%d", r.status_code, sha[:16], len(r.content))

    log.info("Done. Check both for real article text (grep 'Статья 1' after "
              "decoding -- RTF needs an RTF-to-text tool, not iconv alone).")


if __name__ == "__main__":
    main()
