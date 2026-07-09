#!/usr/bin/env python3
"""Scan mariupol.gosuslugi.ru's own "Распоряжения главы администрации города
Мариуполя" document listing for Распоряжение №264 (06.06.2024) -- the
inventory decree residents have cited on door-posted notices for a year but
that two independent residents report they could NOT find on this exact
portal (see docs/legal_mechanisms_review.md, the standing №264 open item).

This does NOT guess page IDs. The two individual decree pages already
captured this project (№619 = ID 503, №71 = ID 515, both on the OLD
mariupol-r897.gosweb.gosuslugi.ru host) don't follow a predictable ID<->date
mapping, so brute-forcing IDs is unreliable. Instead this walks the listing/
index page itself:

    https://mariupol.gosuslugi.ru/ofitsialno/dokumenty/
        rasporyazheniya-glavy-administratsii-goroda-mariupolya/

paginating the same way the already-captured "ownerless" listing does
(?cur_cc=<N>&curPos=<offset>), collecting every linked "..._NNN.html"
document page + its visible title/date/number text, and flagging any that
mention "264" or the date "06.06.2024" or the word "инвентаризац*".

Captures EVERY listing page it visits (even if 264 isn't found on it) plus
every individual decree page whose visible text matches the flags above --
so a negative result is still evidence (a complete, captured index that
truly does not contain №264), not just an unlogged dead end.

TLS note: this host previously needed verify=False due to a CA not in the
standard trust store (same as scripts/269-274) -- kept below for
consistency; SHA-256 in the raw store is what establishes forensic
integrity, not TLS trust.

Claude must NEVER run this -- it hits a DNR/occupation-administration web
property and must be run by you, from your own terminal (CLAUDE.md).

Usage:
    .venv312/bin/python scripts/289_scan_gosuslugi_for_rasporyazhenie_264.py
    .venv312/bin/python scripts/289_scan_gosuslugi_for_rasporyazhenie_264.py --max-pages 40
"""
import argparse
import logging
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
import urllib3
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE = "https://mariupol.gosuslugi.ru"
LISTING_PATH = "/ofitsialno/dokumenty/rasporyazheniya-glavy-administratsii-goroda-mariupolya/"

FLAG_RX = re.compile(r"264\b|06\.06\.2024|инвентаризац\w*", re.I)
DOC_LINK_RX = re.compile(r"rasporyazheniya-glavy-administratsii-goroda-mariupolya_\d+\.html")


def fetch(url: str) -> tuple[bytes, str, int]:
    for attempt in range(config.MAX_RETRIES):
        try:
            resp = requests.get(
                url, headers={"User-Agent": config.USER_AGENT},
                timeout=config.TIMEOUT, allow_redirects=True, verify=False,
            )
            return resp.content, resp.headers.get("Content-Type", "text/html"), resp.status_code
        except requests.exceptions.RequestException as exc:
            if attempt == config.MAX_RETRIES - 1:
                raise
            log.warning("transient error fetching %s (attempt %d/%d): %s -- retrying",
                        url, attempt + 1, config.MAX_RETRIES, exc)
            time.sleep(2.0 * (attempt + 1))


def visible_text(html_bytes: bytes) -> str:
    soup = BeautifulSoup(html_bytes, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    return soup.get_text("\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-pages", type=int, default=25,
                     help="max listing pages to paginate through (default 25)")
    args = ap.parse_args()

    con = forensics.open_state()
    seen_docs: set[str] = set()
    found_264 = False

    listing_url = urljoin(BASE, LISTING_PATH)
    page_urls = [listing_url]
    # the "ownerless" listing on this CMS paginates via ?cur_cc=<id>&curPos=<offset>;
    # cur_cc is page-specific and only discoverable from the first page's own
    # pagination links, so we resolve it dynamically below rather than guessing.
    cur_cc = None
    offset = 0
    visited_pages = 0

    while page_urls and visited_pages < args.max_pages:
        url = page_urls.pop(0)
        log.info("fetching listing page: %s", url)
        content, ctype, status = fetch(url)
        sha = forensics.capture_source(
            content, url=url, source_type="mariupol_gosuslugi_rasporyazhenie_listing",
            title=f"Распоряжения главы администрации г. Мариуполя -- listing page ({url})",
            description="Listing/index page scanned for Распоряжение №264 (06.06.2024). "
                         "Captured regardless of whether 264 is found on it, so a negative "
                         "result is itself evidence.",
            content_type=ctype, http_status=status, con=con,
        )
        visited_pages += 1
        log.info("captured listing page -> sha=%s status=%s (%d bytes)", sha[:12], status, len(content))

        if status != 200:
            log.warning("non-200 status for %s, stopping pagination", url)
            break

        soup = BeautifulSoup(content, "html.parser")

        # discover cur_cc from this page's own pagination links, first pass only
        if cur_cc is None:
            for a in soup.find_all("a", href=True):
                m = re.search(r"cur_cc=(\d+)", a["href"])
                if m:
                    cur_cc = m.group(1)
                    log.info("discovered cur_cc=%s from pagination links", cur_cc)
                    break

        # collect individual decree document links on this page
        doc_links = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if DOC_LINK_RX.search(href):
                doc_links.add(urljoin(BASE, href))

        if not doc_links:
            log.info("no decree document links found on this listing page -- "
                      "the listing may render via JS/AJAX, not static HTML; "
                      "manual inspection of the captured page is needed")

        for doc_url in sorted(doc_links):
            if doc_url in seen_docs:
                continue
            seen_docs.add(doc_url)
            content, ctype, status = fetch(doc_url)
            text = visible_text(content)
            flagged = bool(FLAG_RX.search(text))
            sha = forensics.capture_source(
                content, url=doc_url, source_type="mariupol_gosuslugi_rasporyazhenie",
                title=f"Распоряжение -- {doc_url}",
                description=("FLAGGED as matching 264/06.06.2024/инвентаризация -- "
                              if flagged else "Not flagged -- ") +
                             "captured during the No. 264 site-wide scan (scripts/289).",
                content_type=ctype, http_status=status, con=con,
            )
            if flagged:
                found_264 = True
                log.info("*** FLAGGED (264/06.06.2024/инвентаризация match): %s -> sha=%s",
                         doc_url, sha[:12])
            else:
                log.info("captured (no flag): %s -> sha=%s", doc_url, sha[:12])
            time.sleep(0.5)

        # queue next listing page if we have a cur_cc and this page had documents
        if cur_cc and doc_links:
            offset += 20
            page_urls.append(f"{listing_url}?cur_cc={cur_cc}&curPos={offset}")

        time.sleep(1.0)

    con.close()

    log.info("=" * 60)
    log.info("done. %d listing pages visited, %d unique decree documents captured.",
              visited_pages, len(seen_docs))
    if found_264:
        log.info("№264 (or a document mentioning 264/06.06.2024/инвентаризация) WAS "
                  "found -- review the FLAGGED entries above and tell Claude.")
    else:
        log.info("No document matching 264/06.06.2024/инвентаризация was found in "
                  "%d pages / %d documents scanned. This is itself useful: either "
                  "the decree isn't published on this listing (possible if it's an "
                  "internal/unpublished order, consistent with the two residents' "
                  "own negative searches already logged), or pagination stopped "
                  "short of covering it (rerun with --max-pages higher, or check "
                  "the raw captured listing pages by hand for a working pagination "
                  "pattern if 'no decree document links found' warnings appeared above).",
                  visited_pages, len(seen_docs))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
