#!/usr/bin/env python3
"""Crawl ONLY the Mariupol section of sadovoe-kolco.ru (ГК "Садовое кольцо").

Multi-region developer (1.3M m² portfolio, 9 business lines). Two Mariupol
projects found via ?city=mariupol:

  - "Дом у моря" — ул. Адмирала Лунина, 25 (pid=5807, demolished, no
    reallocation event yet). Same street as the already-processed
    "Лунина 9а" chat (pid=5816).
  - "Садовые кварталы" — ул. Артёма, 98а / 88а / 110 (three buildings,
    747 apartments total):
      pid=4768 (Артема, 98, demolished, no reallocation)
      pid=4764 (Артема, 88, demolished, no reallocation)
      Артема, 110 -- NOT on the spine at all, a gap to flag if confirmed

Per user direction, this crawl is restricted to the Mariupol section only
-- /projects/mariupol/* paths -- plus any PDF/document links discovered
from those pages (which live under /upload/iblock/... regardless of page
path, so PDFs are allowed through even though their URL path doesn't start
with /projects/mariupol/). Other-region project pages are explicitly
excluded from the crawl scope.

Known entry points (seed the queue with these so we don't depend on the
homepage's ?city=mariupol query-param routing, which may be JS-driven):
  /projects/mariupol/house-by-the-sea
  /projects/mariupol/sadovyekvartaly

Same capture pattern as scripts 86/120/121/124/126: SHA-256 + meta.json via
forensics.capture_source, skips static asset extensions. Can run in
parallel with other crawls.

Claude must never run this. Run from project root:
    .venv312/bin/python scripts/127_crawl_sadovoe_kolco_mariupol.py
    .venv312/bin/python scripts/127_crawl_sadovoe_kolco_mariupol.py --max-pages 200
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

DOMAIN = "sadovoe-kolco.ru"
START_URLS = [
    f"https://{DOMAIN}/?city=mariupol",
    f"https://{DOMAIN}/projects/mariupol/house-by-the-sea",
    f"https://{DOMAIN}/projects/mariupol/sadovyekvartaly",
]
# Only follow non-PDF page links whose path starts with one of these prefixes.
ALLOWED_PAGE_PREFIXES = ("/projects/mariupol", "/")  # "/" only matches the bare homepage query
SOURCE_TYPE_PAGE  = "sadovoe_kolco_page"
SOURCE_TYPE_PDF   = "sadovoe_kolco_pdf"
SOURCE_TYPE_ASSET = "sadovoe_kolco_asset"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
REQUEST_DELAY_S = 1.0
SKIP_EXTS = (
    ".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
    ".woff", ".woff2", ".ttf", ".eot", ".map", ".mp4", ".webm",
)


def _already_captured(con, url: str) -> bool:
    row = con.execute(
        "SELECT 1 FROM source_document WHERE url=?", (url,)
    ).fetchone()
    return row is not None


def _strip_fragment(url: str) -> str:
    return url.split("#", 1)[0]


def _in_scope(path: str) -> bool:
    """Mariupol-only scope for HTML page links (PDFs are always allowed through)."""
    if path == "/" or path.startswith("/projects/mariupol"):
        return True
    return False


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
    n_pages = n_pdfs = n_assets = n_skipped = n_errors = n_out_of_scope = 0

    while queue and n_pages < max_pages:
        url = _strip_fragment(queue.pop(0))
        if url in seen:
            continue
        seen.add(url)

        parsed = urlparse(url)
        if parsed.netloc and DOMAIN not in parsed.netloc:
            continue
        path_lower = parsed.path.lower()
        if path_lower.endswith(SKIP_EXTS):
            continue

        is_pdf_url = path_lower.endswith(".pdf")
        if not is_pdf_url and not _in_scope(parsed.path):
            n_out_of_scope += 1
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

        if is_pdf_url or "application/pdf" in content_type:
            try:
                forensics.capture_source(
                    resp.content, url=url, source_type=SOURCE_TYPE_PDF,
                    title=f"sadovoe-kolco.ru PDF: {parsed.path}",
                    description=f"PDF asset captured from {url} (Mariupol-section crawl).",
                    content_type="application/pdf", http_status=resp.status_code,
                    con=con,
                )
            except Exception:
                log.exception("capture failed (will retry on next run): %s", url)
                continue
            n_pdfs += 1
            log.info("[PDF %d] %s", n_pdfs, url)
            continue

        if "text/html" not in content_type:
            try:
                forensics.capture_source(
                    resp.content, url=url, source_type=SOURCE_TYPE_ASSET,
                    title=f"sadovoe-kolco.ru asset: {parsed.path}",
                    description=f"Non-HTML/PDF asset captured from {url} (content_type={content_type}).",
                    content_type=content_type or "application/octet-stream",
                    http_status=resp.status_code, con=con,
                )
            except Exception:
                log.exception("capture failed (will retry on next run): %s", url)
                continue
            n_assets += 1
            continue

        try:
            forensics.capture_source(
                resp.content, url=url, source_type=SOURCE_TYPE_PAGE,
                title=f"sadovoe-kolco.ru page: {parsed.path or '/'}",
                description=f"HTML page captured from {url} (Mariupol-section crawl).",
                content_type="text/html", http_status=resp.status_code, con=con,
            )
        except Exception:
            log.exception("capture failed (will retry on next run): %s", url)
            continue
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
            # PDFs always allowed through scope filter; pages must stay in /projects/mariupol.
            if not p.path.lower().endswith(".pdf") and not _in_scope(p.path):
                continue
            if absolute not in seen:
                queue.append(absolute)

    print(f"\n{'='*60}")
    print("sadovoe-kolco.ru (Mariupol-only) crawl complete")
    print(f"  Pages captured     : {n_pages}")
    print(f"  PDFs captured      : {n_pdfs}")
    print(f"  Other assets       : {n_assets}")
    print(f"  Already in store   : {n_skipped}")
    print(f"  Out-of-scope skipped: {n_out_of_scope}")
    print(f"  Fetch errors       : {n_errors}")
    print(f"  Queue remaining    : {len(queue)} (raise --max-pages to continue)")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-pages", type=int, default=100,
                         help="max HTML pages to fetch this run (PDFs/assets don't count)")
    args = parser.parse_args()
    run(max_pages=args.max_pages)
