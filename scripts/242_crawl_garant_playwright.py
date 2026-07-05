#!/usr/bin/env python3
"""Headless-browser follow-up to scripts/241, for what a plain `requests`
GET can't get past on GARANT. Two problems diagnosed via scripts/243's live
inspection (2026-07-04):

  1. **DDoS-Guard JS challenge** -- clears fine under a real (even headless)
     browser; confirmed empirically. The one URL this had blocked
     (Постановление №87-1) turned out to be a genuine 404 underneath once
     the challenge cleared -- the cited URL was simply wrong, not blocked.
  2. **JS-hash-routed search** -- base.garant.ru's own search box POSTs to
     `base.garant.ru/search/`, which just bounces (hidden form +
     `window.location.hash`) to `ivo.garant.ru/#/basesearch/<query>` -- a
     DIFFERENT subdomain running a client-rendered SPA. A plain GET to
     either URL never reaches real results (confirmed: identical tiny stub
     every time in scripts/241). The fix is to navigate straight to the
     `ivo.garant.ru` hash route with a real browser and let it render --
     confirmed working via scripts/243 (66 real hits rendered for a test
     query, ~3-4s after navigation). Individual results live at
     `ivo.garant.ru/#/document/<internal_id>/...` -- a third ID space,
     distinct from `base.garant.ru/NNNNN/` and
     `garant.ru/products/ipo/prime/doc/NNNNN/` used elsewhere in this project.

Install (one-time):
    pip install -e ".[browser]"
    playwright install chromium

Run:
    PYTHONPATH=src python scripts/242_crawl_garant_playwright.py
    PYTHONPATH=src python scripts/242_crawl_garant_playwright.py --headed   # visible browser, if headless gets flagged
    PYTHONPATH=src python scripts/242_crawl_garant_playwright.py --search-only   # just the 8 search targets (RETRY is currently empty)

Never auto-follows a search result and mislabels it as a specific decree --
it captures the rendered results page + the plain-text render, and prints
candidate `ivo.garant.ru/#/document/<id>/` links for you to confirm by eye
(read the saved `.rendered.txt` alongside each capture) before a follow-up
direct-fetch run.
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
log = logging.getLogger(__name__)

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
except ImportError:
    log.error("playwright not installed. Run: pip install -e '.[browser]' && playwright install chromium")
    sys.exit(1)


@dataclass
class RetryTarget:
    url: str
    source_type: str
    title: str
    description: str


@dataclass
class SearchTarget:
    query: str
    source_type: str
    title: str
    description: str


RETRY: list[RetryTarget] = [
    # (empty) -- the one RETRY candidate (Постановление №87-1) was confirmed
    # 2026-07-04 to be a genuine 404: the DDoS-Guard challenge cleared fine
    # under a real browser, but the destination itself doesn't exist. That
    # cited URL was simply wrong. Moved to SEARCH below to look it up properly
    # now that the real ivo.garant.ru search entry point is confirmed working.
]

SEARCH: list[SearchTarget] = [
    # The prior batch (№87-1, №38-7, №71-РЗ, №619, №1592, №493, №341, "Указ №307",
    # №594) is settled as of 2026-07-04 -- see docs/legal_mechanisms_review.md.
    # This batch targets foundational RF CODE articles that are only [REPORTED]/
    # cited-secondhand so far, never captured in their own right. Unlike the
    # commercial decrees above, codes are core public legal texts (freely
    # published, not subscription-gated) -- likely to render in full even
    # without a GARANT login.
    SearchTarget(
        query="Земельный кодекс Российской Федерации",
        source_type="search_zk_rf_code_itself",
        title="GARANT search (ivo) — Земельный кодекс РФ (the code itself, not diluted by 'без торгов')",
        description=(
            "Follow-up: the 'статья 39.6 39.7 39.8 без торгов' query's top hits were "
            "municipal regulations citing ЗК РФ, not the code itself -- this narrower "
            "query should surface ЗК РФ's own document ID directly, same pattern as "
            "ГК РФ (10164072), ГПК РФ (12128809), ЖК РФ (12138291) all found this way."
        ),
    ),
    # ГК РФ (10164072), ГПК РФ (12128809), ЖК РФ (12138291) already found in the
    # prior run's candidate-ID dumps -- queued directly in scripts/241 instead
    # of re-searching for them here.
]

# Confirmed 2026-07-04 via scripts/243's diagnostic run: base.garant.ru's own
# search box POSTs to https://base.garant.ru/search/ but that just bounces
# (via a hidden form + window.location.hash) to this exact hash route on a
# DIFFERENT subdomain -- ivo.garant.ru, a client-rendered Angular/React SPA.
# Navigating straight here skips the pointless intermediate hop.
IVO_SEARCH_URL = "https://ivo.garant.ru/#/basesearch/{query}"

# Individual hits render as https://ivo.garant.ru/#/document/<internal_id>/...
# -- a DIFFERENT ID space from base.garant.ru/NNNNN/ or the
# garant.ru/products/ipo/prime/doc/NNNNN/ URLs used elsewhere in this project.
DOC_LINK_RE = re.compile(r'/#/document/(\d+)/')


def _capture(con, content: bytes, *, url: str, source_type: str, title: str,
             description: str, content_type: str) -> str:
    sha = forensics.capture_source(
        content, url=url, source_type=source_type, title=title,
        description=description, content_type=content_type,
        http_status=200, con=con,
    )
    log.info("  -> sha=%s bytes=%d", sha[:16], len(content))
    return sha


def run_retry(page, con) -> None:
    log.info("=== RETRY (DDoS-Guard, %d target(s)) ===", len(RETRY))
    for t in RETRY:
        log.info("Navigating: %s", t.url)
        try:
            page.goto(t.url, timeout=30000, wait_until="domcontentloaded")
        except PWTimeout:
            log.warning("  navigation timed out, capturing whatever loaded")
        # DDoS-Guard's own copy says "wait a few seconds" -- give it room, then
        # check whether the challenge title is still present.
        for attempt in range(3):
            time.sleep(5)
            html = page.content()
            if "DDoS-Guard" not in html and "Checking your browser" not in html:
                break
            log.info("  still on challenge page, waiting more (attempt %d/3)", attempt + 1)
        else:
            log.warning("  challenge did not clear after 15s -- capturing final state anyway")
        _capture(con, page.content().encode("utf-8"), url=t.url, source_type=t.source_type,
                  title=t.title, description=t.description, content_type="text/html; charset=utf-8")


def run_search(page, con) -> None:
    log.info("=== SEARCH (ivo.garant.ru, %d target(s)) ===", len(SEARCH))
    for t in SEARCH:
        url = IVO_SEARCH_URL.format(query=quote(t.query))
        log.info("Query: %s", t.query)
        try:
            page.goto(url, timeout=30000, wait_until="networkidle")
        except PWTimeout:
            log.warning("  networkidle timeout on initial load, continuing anyway")
        except Exception as e:
            log.error("  navigation failed: %s -- skipping this query", e)
            continue

        # BUG FOUND 2026-07-04 (first live run): a fixed sleep captured the
        # PREVIOUS query's render, not this one -- confirmed by the "Текст
        # <query>" breadcrumb the SPA itself prints, which was consistently
        # one iteration behind. Root cause: this is a hash-only in-page
        # navigation reusing the same already-loaded SPA instance, and its
        # router+XHR+render cycle takes longer than any fixed sleep we tried
        # to guess. Fix: poll until THIS query's own breadcrumb actually
        # appears in the rendered text -- don't trust a timer at all.
        marker = t.query
        matched = False
        body_text = ""
        for attempt in range(10):
            page.wait_for_timeout(1500)
            body_text = page.inner_text("body")
            if marker in body_text:
                matched = True
                break
        if matched:
            page.wait_for_timeout(800)  # let the result list finish paginating in
            body_text = page.inner_text("body")
        else:
            log.warning("  query breadcrumb never appeared after ~15s -- capturing "
                        "current state anyway (may still be a stale previous-query render)")

        html = page.content()
        doc_ids = sorted(set(DOC_LINK_RE.findall(html)), key=int)

        sha = _capture(con, html.encode("utf-8"), url=url,
                        source_type=t.source_type, title=t.title, description=t.description,
                        content_type="text/html; charset=utf-8")

        txt_path = ROOT / "data" / "raw" / f"{sha}.rendered.txt"
        txt_path.write_text(body_text, encoding="utf-8")

        if doc_ids:
            log.info("  %d candidate document(s) found -- VERIFY BY EYE before treating as the answer:", len(doc_ids))
            log.info("  first 800 chars of rendered results: %s", body_text[:800].replace("\n", " | "))
            for doc_id in doc_ids[:10]:
                log.info("    https://ivo.garant.ru/#/document/%s/paragraph/1", doc_id)
        else:
            log.info("  no result documents found. Rendered text (first 500 chars): %s",
                      body_text[:500].replace("\n", " | "))
        log.info("  full rendered text saved: %s", txt_path)
        time.sleep(2)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true", help="run with a visible browser window")
    ap.add_argument("--retry-only", action="store_true")
    ap.add_argument("--search-only", action="store_true")
    args = ap.parse_args()

    con = forensics.open_state()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed)
        context = browser.new_context(
            locale="ru-RU",
            user_agent=config.USER_AGENT,
            viewport={"width": 1366, "height": 900},
        )
        page = context.new_page()

        if not args.search_only:
            run_retry(page, con)
        if not args.retry_only:
            run_search(page, con)

        browser.close()

    log.info("Done. For SEARCH targets, open the captured HTML/screenshots in data/raw/ "
              "and confirm any candidate links by eye -- then add confirmed URLs to "
              "scripts/241's DIRECT list and re-run with --direct-only.")


if __name__ == "__main__":
    main()
