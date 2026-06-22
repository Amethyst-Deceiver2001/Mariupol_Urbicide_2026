#!/usr/bin/env python3
"""Crawl mira-polis.com -- ЖК "Мираполис".

Already partially corroborated via ЕИСЖС (script 72):
  RPD 93-000023 (Ленина 127Б) -> pid=4438 -- developer СЗ МИРАСТРОЙ,
    ИНН 9303034407, 159 flats, 13 floors
  RPD 93-000015 (Ленина 129а) -> pid=4439 -- developer СЗ МИРАСТРОЙ 2,
    ИНН 9303036549, 130 flats, 17 floors
Both demolition+reallocation already loaded, neither has a land cadastral
number (land_order_cadastrals: None in both).

The site states the complex has 4 buildings / 655 apartments total --
only 2 RPDs/buildings are accounted for above (159+130=289 flats, not
655), so buildings 3 and 4 are likely a SEPARATE, not-yet-loaded gap.
Priority targets: find the addresses/cadastrals for the other two
buildings, and any cadastral numbers for the two already-known ones.

Site nav is mostly per-apartment listing pages (/flats/NNN) plus a few
static pages (/privacy-policy, /agreement, /cookie) and an external
наш.дом.рф link -- expect a flat-page-dominated crawl, similar to the
проектинвест.рф experience (script 120).

Same capture pattern as scripts 86/120/121/124/126-132: SHA-256 +
meta.json via forensics.capture_source, skips static asset extensions.
Can run in parallel with other crawls.

Claude must never run this. Run from project root:
    .venv312/bin/python scripts/133_crawl_mirapolis_site.py
    .venv312/bin/python scripts/133_crawl_mirapolis_site.py --max-pages 200
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

DOMAIN     = "mira-polis.com"
START_URLS = [f"https://{DOMAIN}/"]
SOURCE_TYPE_PAGE  = "mirapolis_page"
SOURCE_TYPE_PDF   = "mirapolis_pdf"
SOURCE_TYPE_ASSET = "mirapolis_asset"
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
    n_pages = n_pdfs = n_assets = n_skipped = n_errors = 0

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
            try:
                forensics.capture_source(
                    resp.content, url=url, source_type=SOURCE_TYPE_PDF,
                    title=f"mira-polis.com PDF: {parsed.path}",
                    description=f"PDF asset captured from {url}.",
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
                    title=f"mira-polis.com asset: {parsed.path}",
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
                title=f"mira-polis.com page: {parsed.path or '/'}",
                description=f"HTML page captured from {url}.",
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
            if absolute not in seen:
                queue.append(absolute)

    print(f"\n{'='*60}")
    print("mira-polis.com crawl complete")
    print(f"  Pages captured     : {n_pages}")
    print(f"  PDFs captured      : {n_pdfs}")
    print(f"  Other assets       : {n_assets}")
    print(f"  Already in store   : {n_skipped}")
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
