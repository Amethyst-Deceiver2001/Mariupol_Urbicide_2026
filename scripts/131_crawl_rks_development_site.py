#!/usr/bin/env python3
"""Crawl xn----dtbfw3ah.xn--p1ai -- ООО "РКС-Девелопмент".

Matches "РКС-НР", the general contractor named in the @Lenina106_Mariupol
chat (script 94 output): "представителями генерального подрядчика ООО
«РКС-НР»" doing repair work on apartments in the registry_inclusion
process. This site is RKS's own development-arm project page.

Flagship project: "Дом с часами" (House with Clocks) -- restoration of a
historically damaged landmark at пр. Нахимова, 39, featuring an art museum
dedicated to V. Arnaoutov, an observation deck, and a restored clock tower.
This is adaptive RESTORATION of a historic building, not a typical
demolish-rebuild new-construction case -- may warrant tracking as a
cultural-property matter alongside (or instead of) the standard RD4U
categories.

Adjacent spine property: pid=6088 ("Нахимова, 39") -- NO rd4u_category set,
NO seizure events at all. Complete gap; this crawl is the primary lead for
filling it.

No ИНН/ОГРН found on the homepage -- priority targets are the developer's
legal entity identifiers and any documentation of how this landmark came
under RKS's control (heritage designation, municipal transfer, etc.).

Same capture pattern as scripts 86/120/121/124/126/127/128/129/130:
SHA-256 + meta.json via forensics.capture_source, skips static asset
extensions. Can run in parallel with other crawls.

Claude must never run this. Run from project root:
    .venv312/bin/python scripts/131_crawl_rks_development_site.py
    .venv312/bin/python scripts/131_crawl_rks_development_site.py --max-pages 200
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

DOMAIN     = "xn----dtbfw3ah.xn--p1ai"
START_URLS = [f"https://{DOMAIN}/"]
SOURCE_TYPE_PAGE  = "rks_development_page"
SOURCE_TYPE_PDF   = "rks_development_pdf"
SOURCE_TYPE_ASSET = "rks_development_asset"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
REQUEST_DELAY_S = 1.0
SKIP_EXTS = (
    ".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico",
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
                    title=f"rks-development PDF: {parsed.path}",
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
                    title=f"rks-development asset: {parsed.path}",
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
                title=f"rks-development page: {parsed.path or '/'}",
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
    print("РКС-Девелопмент (Дом с часами) crawl complete")
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
