#!/usr/bin/env python3
"""Crawl evoinfo.ru — ГК "Эволюция".

Operates in Orenburg, Buzuluk, and Mariupol. Mariupol project: "Авторский
дом «Мари»" at ул. Миклухо-Маклая, 3а — immediately adjacent to pid=5423
(ул. Миклухо-Маклая, 3, demolished, rd4u=A3.1,A3.3,A3.6). Another candidate
demolish-rebuild pair, same pattern as ПОРФИР/Зелинского-23 and the
Хмельницкого 20->16а case.

Goals for this crawl:
  - Find the developer's ИНН/ОГРН (not disclosed on the homepage)
  - Find any project declaration / legal documents pages
  - Find exact address/cadastral for "Мари" and confirm the 3 vs 3а overlap
  - Discover any other Mariupol projects beyond "Мари"
  - Check evopartners.ru (linked as a sales-agency partner site) for
    additional legal/project details not on the main site

Same pattern as scripts 86/120: same-domain BFS crawl, capture-before-parse,
SHA-256 + meta.json sidecar via forensics.capture_source, skips static asset
extensions so the queue isn't wasted on template files.

Can run in parallel with an active Telegram chat crawl or the proektinvest
site crawl (different process, different network target). The only shared
resource is the SQLite forensics state DB; sqlite3's default busy-timeout
handles brief concurrent-write contention. Capture failures are logged and
skipped rather than crashing the run — safe to re-run later to pick up
anything missed.

Claude must never run this. Run from project root:
    .venv312/bin/python scripts/121_crawl_evoinfo_site.py
    .venv312/bin/python scripts/121_crawl_evoinfo_site.py --max-pages 200
    .venv312/bin/python scripts/121_crawl_evoinfo_site.py --domain evopartners.ru
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

SOURCE_TYPE_PAGE  = "evoinfo_page"
SOURCE_TYPE_PDF   = "evoinfo_pdf"
SOURCE_TYPE_ASSET = "evoinfo_asset"
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


def run(domain: str, max_pages: int) -> None:
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        log.error("requests / beautifulsoup4 not installed")
        return

    con = forensics.open_state()
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    start_url = f"https://{domain}/"
    seen: set[str] = set()
    queue: list[str] = [start_url]
    n_pages = n_pdfs = n_assets = n_skipped = n_errors = 0

    while queue and n_pages < max_pages:
        url = _strip_fragment(queue.pop(0))
        if url in seen:
            continue
        seen.add(url)

        parsed = urlparse(url)
        if parsed.netloc and domain not in parsed.netloc:
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
                    title=f"evoinfo PDF: {parsed.path}",
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
                    title=f"evoinfo asset: {parsed.path}",
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
                title=f"evoinfo page: {parsed.path or '/'}",
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
            if p.netloc and domain not in p.netloc:
                continue
            if p.path.lower().endswith(SKIP_EXTS):
                continue
            if absolute not in seen:
                queue.append(absolute)

    print(f"\n{'='*60}")
    print(f"{domain} crawl complete")
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
    parser.add_argument("--domain", default="evoinfo.ru",
                         help="domain to crawl (default evoinfo.ru; pass evopartners.ru for the partner site)")
    args = parser.parse_args()
    run(domain=args.domain, max_pages=args.max_pages)
