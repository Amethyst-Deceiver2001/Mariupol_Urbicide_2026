#!/usr/bin/env python3
"""Crawl ONLY the Mariupol-tagged section of vskmo.ru.

vskmo.ru is the corporate site of ППК "ВСК" (Публично-правовая компания
"Военно-строительная компания") -- the Russian Ministry of Defense's own
public-law military construction company, NOT a private real-estate
developer. Self-described as "национальный лидер в области строительства
специальных, стратегических и социально-значимых объектов Министерства
обороны России."

Confirmed finding (via manual fetch before this script was written): "По
решению президента России" (by decision of the President of Russia), ВСК
built a 560-cadet branch of the Нахимовское военно-морское училище
(Nakhimov Naval School) in Mariupol in a record 350 days -- the 5th branch
nationally (after St. Petersburg HQ, Vladivostok, Murmansk, Kaliningrad,
Sevastopol), on the Azov Sea. In Sept 2025 it was named for twice-Hero-of-
Russia Maj. Gen. Mikhail Gudkov, with a ceremony attended by the Navy
commander-in-chief and a DNR-government representative.

This is federal/Presidential-level state institution-building in occupied
territory -- directly relevant to the project's Rome Statute art.
8(2)(b)(viii) angle, distinct from the private-developer demolish-rebuild
pattern documented elsewhere this session. No address/footprint has been
confirmed yet -- finding the exact site (and any predecessor demolished
property) is the priority for this crawl.

The site gates all requests behind a JS cookie challenge (Beget hosting
anti-bot: sets cookie "beget=begetok" then reloads) -- handled here by
setting that cookie directly in the requests session rather than executing
JS.

Scope: seeded from https://vskmo.ru/tag/mariupol/ (10 pages of tag-archive
listing per a manual check) plus every article link discovered from those
pages. Does NOT crawl the rest of the site (other regions/projects are out
of scope per the Mariupol-only mandate for this investigation).

Same capture pattern as other developer-site scripts this session:
SHA-256 + meta.json via forensics.capture_source, skips static asset
extensions. Can run in parallel with other crawls.

Claude must never run this. Run from project root:
    .venv312/bin/python scripts/134_crawl_vskmo_mariupol.py
    .venv312/bin/python scripts/134_crawl_vskmo_mariupol.py --max-pages 200
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

DOMAIN = "vskmo.ru"
TAG_PAGES = [f"https://{DOMAIN}/tag/mariupol/"] + [
    f"https://{DOMAIN}/tag/mariupol/page/{i}/" for i in range(2, 11)
]
SOURCE_TYPE_PAGE = "vskmo_page"
SOURCE_TYPE_PDF  = "vskmo_pdf"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
REQUEST_DELAY_S = 1.0
SKIP_EXTS = (
    ".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
    ".woff", ".woff2", ".ttf", ".eot", ".map", ".mp4", ".webm",
)


def _cached_raw_path(con, url: str) -> str | None:
    """Return the on-disk raw_path for a previously-captured URL, or None."""
    row = con.execute(
        "SELECT raw_path FROM source_document WHERE url=?", (url,)
    ).fetchone()
    return row[0] if row else None


def _strip_fragment(url: str) -> str:
    return url.split("#", 1)[0]


def _is_article_or_tag_url(path: str) -> bool:
    """Only follow article permalinks (/YYYY/MM/DD/slug/) and tag-archive pages."""
    if path.startswith("/tag/mariupol"):
        return True
    parts = [p for p in path.strip("/").split("/") if p]
    return len(parts) >= 2 and parts[0].isdigit() and len(parts[0]) == 4


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
    session.cookies.set("beget", "begetok", domain=DOMAIN)

    seen: set[str] = set()
    queue: list[str] = list(TAG_PAGES)
    n_pages = n_pdfs = n_skipped = n_errors = n_out_of_scope = 0

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
        if not is_pdf_url and not _is_article_or_tag_url(parsed.path):
            n_out_of_scope += 1
            continue

        cached_path = _cached_raw_path(con, url)
        if cached_path:
            n_skipped += 1
            if is_pdf_url:
                # PDFs are leaves -- nothing further to discover.
                log.info("already captured (PDF), skipping: %s", url)
                continue
            # HTML page: already on disk, but its outbound links may never
            # have been enqueued (e.g. this run started fresh after a prior
            # run hit --max-pages). Re-parse the CACHED bytes for link
            # discovery -- no network fetch, no re-capture.
            try:
                cached_bytes = Path(cached_path).read_bytes()
                soup = BeautifulSoup(cached_bytes, "html.parser")
            except Exception:
                log.exception("failed to re-parse cached file for link discovery: %s", cached_path)
                continue
            log.info("already captured, re-parsing cached copy for links: %s", url)
            for tag in soup.find_all("a", href=True):
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
                if not p.path.lower().endswith(".pdf") and not _is_article_or_tag_url(p.path):
                    continue
                if absolute not in seen:
                    queue.append(absolute)
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
                    title=f"vskmo.ru PDF: {parsed.path}",
                    description=f"PDF asset captured from {url} (Mariupol-tag crawl).",
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
            continue

        try:
            forensics.capture_source(
                resp.content, url=url, source_type=SOURCE_TYPE_PAGE,
                title=f"vskmo.ru page: {parsed.path or '/'}",
                description=f"HTML page captured from {url} (Mariupol-tag crawl).",
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

        for tag in soup.find_all("a", href=True):
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
            if not p.path.lower().endswith(".pdf") and not _is_article_or_tag_url(p.path):
                continue
            if absolute not in seen:
                queue.append(absolute)

    print(f"\n{'='*60}")
    print("vskmo.ru (Mariupol tag only) crawl complete")
    print(f"  Pages captured       : {n_pages}")
    print(f"  PDFs captured        : {n_pdfs}")
    print(f"  Already in store     : {n_skipped}")
    print(f"  Out-of-scope skipped : {n_out_of_scope}")
    print(f"  Fetch errors         : {n_errors}")
    print(f"  Queue remaining      : {len(queue)} (raise --max-pages to continue)")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-pages", type=int, default=150,
                         help="max HTML pages to fetch this run (PDFs don't count)")
    args = parser.parse_args()
    run(max_pages=args.max_pages)
