#!/usr/bin/env python3
"""Crawl mar-s.group — МАР-С (developer entities ООО "СЗ ТЕМП" / "СЗ ТЕМП 80").

Three Mariupol projects, already partially corroborated against ЕИСЖС data
(script 72):
  - "Нахимов" — пр. Ленина 101Б + ул. Апатова 121А
      adjacent spine: pid=4414 (Ленина,101, 14 registry_inclusion events),
      pid=13980 (Апатова,121, demolished) — NO reallocation event linked yet,
      unlike the other two projects below. Priority gap to close.
  - "Кипарис" — пр. Ленина 96А
      adjacent spine: pid=4497 (Ленина,96) — demolition + reallocation
      already loaded (ЕИСЖС id=62540, СЗ ТЕМП, ИНН 9310011351, 101 flats,
      16 floors, RPD project title "Жилой комплекс «Кипарис»... д. 96 А")
  - "Горизонт" — пр. Ленина 86А + б-р Б.Хмельницкого 33Б
      adjacent spine: pid=4484 (Ленина,86) — demolition + reallocation
      already loaded (ЕИСЖС id=62714, СЗ ТЕМП-80, ИНН 9310011376, 257 flats,
      10 floors); pid=7241 (Ленина,86а/1, registry_inclusion) and pid=4333
      (Хмельницкого,33, demolished) — neither has a reallocation event for
      the Хмельницкого address specifically.

Site navigation includes a "Документация"/documentation page per the
homepage fetch — priority target for project declarations, land cadastral
numbers, and confirmation of the developer entity registration details
already known (ИНН 9310011351/9310011376, ОГРН 1239300017197/1239300017230).

Same pattern as scripts 86/120/121: same-domain BFS crawl, capture-before-
parse, SHA-256 + meta.json sidecar via forensics.capture_source, skips
static asset extensions. Can run in parallel with Telegram crawls or other
developer-site crawls (separate network targets; shared SQLite state DB
handles brief concurrent-write contention via its default busy-timeout).

Claude must never run this. Run from project root:
    .venv312/bin/python scripts/124_crawl_mars_group_site.py
    .venv312/bin/python scripts/124_crawl_mars_group_site.py --max-pages 200
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

DOMAIN     = "mar-s.group"
START_URLS = [f"https://{DOMAIN}/"]
SOURCE_TYPE_PAGE  = "mars_group_page"
SOURCE_TYPE_PDF   = "mars_group_pdf"
SOURCE_TYPE_ASSET = "mars_group_asset"
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
                    title=f"mar-s.group PDF: {parsed.path}",
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
                    title=f"mar-s.group asset: {parsed.path}",
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
                title=f"mar-s.group page: {parsed.path or '/'}",
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
    print("mar-s.group crawl complete")
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
