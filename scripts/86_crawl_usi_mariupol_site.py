#!/usr/bin/env python3
"""Crawl usi-mariupol.ru — ЮгСтройИнвест's Mariupol new-build marketing site.

We already found and forensically captured one PDF from this site (the АУРА
DDU template, bul. Bogdana Khmelnitskogo 16a — developer OOO SZ-1 Porfir,
INN 9310009271, OGRN 1239300008870). This script does a same-domain BFS crawl
to discover and capture everything else: other project pages, other DDU
templates / PDFs, contact/legal pages, additional cadastral numbers and
addresses, additional named officials/signatories.

Capture-before-parse: every page and PDF is written verbatim to data/raw/,
SHA-256 keyed, with a .meta.json sidecar, before anything is parsed. Re-runs
are incremental (skips URLs already in the source_document log).

Claude must never run this. Run from project root:
    .venv312/bin/python scripts/86_crawl_usi_mariupol_site.py
    .venv312/bin/python scripts/86_crawl_usi_mariupol_site.py --max-pages 200
"""
import argparse
import logging
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import forensics  # noqa: E402

log = logging.getLogger(__name__)

DOMAIN     = "usi-mariupol.ru"
START_URLS = [f"https://{DOMAIN}/"]
SOURCE_TYPE_PAGE = "usi_mariupol_page"
SOURCE_TYPE_PDF  = "usi_mariupol_pdf"
SKIP_EXTS = (
    ".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
    ".woff", ".woff2", ".ttf", ".eot", ".map", ".mp4", ".webm",
)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
REQUEST_DELAY_S = 1.0  # be polite; this is a small commercial site, not a CDN


def _already_captured(con, url: str) -> bool:
    row = con.execute(
        "SELECT 1 FROM source_document WHERE url=?", (url,)
    ).fetchone()
    return row is not None


def _strip_fragment(url: str) -> str:
    return url.split("#", 1)[0]


def run(max_pages: int) -> None:
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        log.error("requests / beautifulsoup4 not installed")
        return

    con = forensics.open_state()
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    seen: set[str] = set()
    queue: list[str] = list(START_URLS)
    n_pages = n_pdfs = n_skipped = n_errors = 0

    while queue and n_pages < max_pages:
        url = _strip_fragment(queue.pop(0))
        if url in seen:
            continue
        seen.add(url)

        parsed = urlparse(url)
        if parsed.netloc and DOMAIN not in parsed.netloc:
            continue
        path_no_query = parsed.path.lower()
        if path_no_query.endswith(SKIP_EXTS):
            continue
        if "/assets/templates/" in path_no_query:
            continue

        if _already_captured(con, url):
            n_skipped += 1
            log.info("already captured, skipping fetch: %s", url)
            continue

        try:
            resp = session.get(url, timeout=30, verify=True)
        except Exception:
            log.exception("fetch failed: %s", url)
            n_errors += 1
            continue

        time.sleep(REQUEST_DELAY_S)
        content_type = resp.headers.get("Content-Type", "").lower()

        if url.lower().endswith(".pdf") or "application/pdf" in content_type:
            forensics.capture_source(
                resp.content, url=url, source_type=SOURCE_TYPE_PDF,
                title=f"usi-mariupol PDF: {parsed.path}",
                description=f"PDF asset captured from {url}.",
                content_type="application/pdf", http_status=resp.status_code,
                con=con,
            )
            n_pdfs += 1
            log.info("[PDF %d] %s", n_pdfs, url)
            continue

        if "text/html" not in content_type:
            # Unknown binary type — capture as-is, don't try to parse links from it.
            forensics.capture_source(
                resp.content, url=url, source_type="usi_mariupol_asset",
                title=f"usi-mariupol asset: {parsed.path}",
                description=f"Non-HTML/PDF asset captured from {url} (content_type={content_type}).",
                content_type=content_type or "application/octet-stream",
                http_status=resp.status_code, con=con,
            )
            continue

        forensics.capture_source(
            resp.content, url=url, source_type=SOURCE_TYPE_PAGE,
            title=f"usi-mariupol page: {parsed.path or '/'}",
            description=f"HTML page captured from {url}.",
            content_type="text/html", http_status=resp.status_code, con=con,
        )
        n_pages += 1
        log.info("[page %d] %s", n_pages, url)

        try:
            soup = BeautifulSoup(resp.content, "html.parser")
        except Exception:
            log.exception("HTML parse failed for link discovery: %s", url)
            continue

        for tag in soup.find_all(["a", "link"], href=True):
            href = tag["href"]
            if href.startswith(("mailto:", "tel:", "javascript:")):
                continue
            absolute = urljoin(url, href)
            absolute = _strip_fragment(absolute)
            p = urlparse(absolute)
            if p.netloc and DOMAIN not in p.netloc:
                continue
            if p.path.lower().endswith(SKIP_EXTS):
                continue
            if "/assets/templates/" in p.path.lower():
                continue
            if absolute not in seen:
                queue.append(absolute)

    print(f"\n{'='*60}")
    print("usi-mariupol.ru crawl complete")
    print(f"  Pages captured   : {n_pages}")
    print(f"  PDFs captured    : {n_pdfs}")
    print(f"  Already in store : {n_skipped}")
    print(f"  Fetch errors     : {n_errors}")
    print(f"  Queue remaining  : {len(queue)} (raise --max-pages to continue)")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-pages", type=int, default=100,
                         help="max HTML pages to fetch this run (PDFs/assets don't count)")
    args = parser.parse_args()
    run(max_pages=args.max_pages)
