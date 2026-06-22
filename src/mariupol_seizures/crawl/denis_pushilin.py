"""Stage 1i: capture denis-pushilin.ru — the official site of Denis Pushilin
(Head of the DNR occupation administration, signatory of Указ №301 and many
other acts already cited in docs/legal_mechanisms_review.md).

Reachable over HTTPS with verify=False (ddos-guard self-signed cert — same
SSL_VERIFY=False pattern used elsewhere in this project) — **no VPS needed**,
confirmed 2026-06-12 from outside Russia.

WHAT THIS CAPTURES
------------------
Two crawl modes, both date-filterable via --date-from (default 2022-01-01):

1. SITEMAP-DRIVEN (general site content). `/sitemap.xml` lists ~4,157 URLs
   (news, press, photo, video, document pages) back to 2017, each with a
   <lastmod> date. Filtered to lastmod >= --date-from: ~2,006 pages
   (2022-2026). Captures the sitemap itself
   (source_type `denis_pushilin_sitemap`), each matching page
   (`denis_pushilin_page`), and any PDF linked from a page
   (`denis_pushilin_pdf`).

2. DOCUMENT ARCHIVES (primary-source legal PDFs):
   - `/akty-glavy-dnr/ukazy/` — Указы Главы ДНР, 2,268 PDFs. Filenames embed
     a `_DDMMYYYY.pdf` date suffix (e.g. `Ukaz_N301_20062022.pdf` = №301,
     20.06.2022 — the renaming-delegation decree behind gap [H]). Filtered
     to >= --date-from: ~1,553 PDFs (2022-2026).
   - `/akty-glavy-dnr/rasporyazheniya/` — Распоряжения Главы ДНР, 908 PDFs,
     same date-suffix filtering: ~730 PDFs (2022-2026).
   - `/akty-glavy-dnr/akty-edinogo-ekonomicheskogo-soveta/` — 96 PDFs
     (Решения Единого экономического совета), no date in filename — captured
     in full as a bounded reference set, regardless of --date-from.
   - `/zakony/` — DNR laws, 367 PDFs (`*rz.pdf`), no date in filename —
     captured in full.
   - `/postanovleniya-gosudarstvennogo-komiteta-oborony/` — 137 PDFs incl.
     Постановления ГКО ДНР №162/205/245 (the demolition-procedure framework
     already [CAPTURED] via region80/нпа.днронлайн.рф, scripts 13/35/37) —
     captured in full for corroboration.
   - `/rasporyazheniya-gosudarstvennogo-komiteta-oborony/` — 8 PDFs (№51, 28,
     10, 9, 8, 5, 2, 1). Confirmed 2026-06-12: `Rasp_GKO_56.pdf` (the
     Mariupol demolition list, gap [C]) returns HTTP 404 — corroborates the
     region80 and npa.dnronline.su negative findings (scripts 35/37/38).
     Captured in full for the audit trail.

   Archive listing pages -> `denis_pushilin_doc_index`; each PDF ->
   `denis_pushilin_doc_pdf`.

SCALE / RUNTIME
---------------
Full run (sitemap + all archives, --date-from 2022-01-01) is ~4,900 items.
At config.REQUEST_DELAY (4-9s/request) that's roughly 8-9 hours. Fully
resumable via forensics.is_done — safe to Ctrl-C and rerun. Use
--archives-only to skip the ~2,006 general sitemap pages and capture just the
~2,890 primary-source legal PDFs (~5-6 hours) — highest signal for
docs/legal_mechanisms_review.md.
"""
from __future__ import annotations

import argparse
import logging
import re
import time
from urllib.parse import urljoin

import requests
import urllib3
from bs4 import BeautifulSoup

from .. import config, forensics

log = logging.getLogger(__name__)

if not config.SSL_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ORIGIN = "https://denis-pushilin.ru"
DEFAULT_DATE_FROM = "2022-01-01"

# Archive listing pages whose linked PDF filenames embed a _DDMMYYYY date
# suffix -- filterable by --date-from.
DATED_ARCHIVE_SLUGS = [
    "akty-glavy-dnr/ukazy",
    "akty-glavy-dnr/rasporyazheniya",
]

# Archive listing pages with no per-PDF date in the filename -- bounded
# reference sets, always captured in full.
UNDATED_ARCHIVE_SLUGS = [
    "akty-glavy-dnr/akty-edinogo-ekonomicheskogo-soveta",
    "zakony",
    "postanovleniya-gosudarstvennogo-komiteta-oborony",
    "rasporyazheniya-gosudarstvennogo-komiteta-oborony",
]

_SITEMAP_ENTRY_RE = re.compile(
    r"<url>\s*<loc>(.*?)</loc>\s*<lastmod>(\d{4}-\d{2}-\d{2})", re.S
)
_PDF_DATE_RE = re.compile(r"_(\d{2})(\d{2})(\d{4})\.pdf$", re.I)


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": config.USER_AGENT,
        "Accept-Language": "ru,en;q=0.8",
    })
    if config.PROXY:
        s.proxies.update({"http": config.PROXY, "https": config.PROXY})
    return s


def polite_sleep() -> None:
    time.sleep(2.0)


def _get(s: requests.Session, url: str):
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            return s.get(url, timeout=config.TIMEOUT, verify=config.SSL_VERIFY)
        except requests.RequestException as e:
            wait = min(60, 2 ** attempt)
            log.warning("GET %s failed (%d/%d): %s; wait %ds",
                        url, attempt, config.MAX_RETRIES, e, wait)
            time.sleep(wait)
    log.error("giving up on %s", url)
    return None


def _extract_pdf_links(soup: BeautifulSoup, page_url: str) -> list[str]:
    urls = []
    for a in soup.find_all("a", href=re.compile(r"\.pdf", re.I)):
        href = a.get("href", "")
        if href:
            urls.append(href if href.startswith("http") else urljoin(page_url, href))
    return urls


def _pdf_date(url: str) -> str | None:
    """Parse a trailing _DDMMYYYY.pdf date suffix into an ISO date string."""
    m = _PDF_DATE_RE.search(url)
    if not m:
        return None
    dd, mm, yyyy = m.groups()
    return f"{yyyy}-{mm}-{dd}"


def _capture_pdf(s: requests.Session, con, pdf_url: str, *,
                  source_type: str, title: str, description: str,
                  key_prefix: str) -> None:
    key = f"{key_prefix}::{pdf_url}"
    if forensics.is_done(con, key):
        return
    pr = _get(s, pdf_url)
    polite_sleep()
    if pr is None or pr.status_code != 200:
        log.warning("PDF not fetched (HTTP %s): %s",
                     pr.status_code if pr else "N/A", pdf_url)
        return
    forensics.capture_source(
        pr.content, url=pdf_url,
        source_type=source_type,
        title=title,
        description=description,
        content_type=pr.headers.get("Content-Type", "application/pdf"),
        http_status=pr.status_code, con=con,
    )
    forensics.mark_done(con, key)
    log.info("captured PDF: %s", pdf_url)


def crawl_sitemap_pages(s: requests.Session, con, date_from: str) -> None:
    """Capture sitemap.xml + every listed page (and its PDFs) with lastmod >= date_from."""
    sitemap_url = f"{ORIGIN}/sitemap.xml"
    r = _get(s, sitemap_url)
    polite_sleep()
    if r is None or r.status_code != 200:
        log.error("sitemap not fetched (HTTP %s)", r.status_code if r else "N/A")
        return

    forensics.capture_source(
        r.content, url=sitemap_url,
        source_type="denis_pushilin_sitemap",
        title="denis-pushilin.ru sitemap.xml",
        description=(
            "Full sitemap index for denis-pushilin.ru (official site of "
            "Denis Pushilin, Head of the DNR occupation administration). "
            "Forensic manifest of all URLs known to the site's sitemap "
            "generator, with <lastmod> dates."
        ),
        content_type=r.headers.get("Content-Type", "application/xml"),
        http_status=r.status_code, con=con,
    )

    entries = _SITEMAP_ENTRY_RE.findall(r.text)
    selected = [(url, lastmod) for url, lastmod in entries if lastmod >= date_from]
    log.info("sitemap: %d total entries, %d with lastmod >= %s",
             len(entries), len(selected), date_from)

    for url, lastmod in selected:
        key = f"denis_pushilin_page::{url}"
        if forensics.is_done(con, key):
            continue
        pr = _get(s, url)
        polite_sleep()
        if pr is None or pr.status_code != 200:
            log.warning("page not fetched (HTTP %s): %s",
                         pr.status_code if pr else "N/A", url)
            continue
        forensics.capture_source(
            pr.content, url=url,
            source_type="denis_pushilin_page",
            title=url,
            description=f"denis-pushilin.ru page, sitemap lastmod={lastmod}.",
            content_type=pr.headers.get("Content-Type", "text/html"),
            http_status=pr.status_code, con=con,
        )
        soup = BeautifulSoup(pr.text, "lxml")
        for pdf_url in _extract_pdf_links(soup, url):
            _capture_pdf(
                s, con, pdf_url,
                source_type="denis_pushilin_pdf",
                title=pdf_url,
                description=f"PDF linked from {url} (sitemap lastmod={lastmod}).",
                key_prefix="denis_pushilin_pdf",
            )
        forensics.mark_done(con, key)
        log.info("captured page: %s", url)


def crawl_doc_archive(s: requests.Session, con, slug: str,
                       date_from: str | None) -> None:
    """Capture an archive listing page and its linked PDFs.

    If date_from is set, PDFs whose filename embeds a _DDMMYYYY date are
    filtered to that date; PDFs with no parseable date are always captured
    (small fraction, erring toward over-capture).
    """
    url = f"{ORIGIN}/{slug}/"
    key = f"denis_pushilin_doc_index::{url}"
    r = _get(s, url)
    polite_sleep()
    if r is None or r.status_code != 200:
        log.error("archive not fetched (HTTP %s): %s",
                  r.status_code if r else "N/A", url)
        return

    if not forensics.is_done(con, key):
        forensics.capture_source(
            r.content, url=url,
            source_type="denis_pushilin_doc_index",
            title=f"denis-pushilin.ru /{slug}/ — document archive listing",
            description=(
                f"Archive listing page for /{slug}/ on denis-pushilin.ru, "
                "the official site of Denis Pushilin (Head of the DNR "
                "occupation administration). Forensic manifest of all PDF "
                "documents linked from this category."
            ),
            content_type=r.headers.get("Content-Type", "text/html"),
            http_status=r.status_code, con=con,
        )
        forensics.mark_done(con, key)

    soup = BeautifulSoup(r.text, "lxml")
    pdf_urls = _extract_pdf_links(soup, url)
    n_total = len(pdf_urls)
    n_captured = 0
    n_skipped = 0
    for pdf_url in pdf_urls:
        pdf_date = _pdf_date(pdf_url)
        if date_from is not None and pdf_date is not None and pdf_date < date_from:
            n_skipped += 1
            continue
        desc = f"Primary-source PDF from denis-pushilin.ru /{slug}/."
        if pdf_date:
            desc += f" Filename date: {pdf_date}."
        _capture_pdf(
            s, con, pdf_url,
            source_type="denis_pushilin_doc_pdf",
            title=pdf_url.rsplit("/", 1)[-1],
            description=desc,
            key_prefix="denis_pushilin_doc_pdf",
        )
        n_captured += 1
    log.info("archive /%s/: %d PDFs total, %d in scope, %d filtered out by date",
             slug, n_total, n_captured, n_skipped)


def run(date_from: str = DEFAULT_DATE_FROM,
        do_sitemap: bool = True,
        do_dated_archives: bool = True,
        do_undated_archives: bool = True) -> None:
    con = forensics.open_state()
    s = make_session()
    try:
        if do_sitemap:
            crawl_sitemap_pages(s, con, date_from)
        if do_dated_archives:
            for slug in DATED_ARCHIVE_SLUGS:
                crawl_doc_archive(s, con, slug, date_from)
        if do_undated_archives:
            for slug in UNDATED_ARCHIVE_SLUGS:
                crawl_doc_archive(s, con, slug, date_from=None)
    except KeyboardInterrupt:
        log.warning("interrupted — state saved, safe to rerun.")

    n = con.execute(
        "SELECT COUNT(*) FROM source_document "
        "WHERE source_type LIKE 'denis_pushilin%'"
    ).fetchone()[0]
    log.info("done; %d denis-pushilin.ru artifacts in store", n)


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--date-from", default=DEFAULT_DATE_FROM,
                    help=f"ISO date (YYYY-MM-DD); default {DEFAULT_DATE_FROM}. "
                         "Applies to sitemap <lastmod> and to dated-archive "
                         "PDF filename suffixes.")
    p.add_argument("--skip-sitemap", action="store_true",
                    help="Skip the general sitemap-driven page crawl.")
    p.add_argument("--skip-dated-archives", action="store_true",
                    help="Skip /akty-glavy-dnr/ukazy/ and /rasporyazheniya/.")
    p.add_argument("--skip-undated-archives", action="store_true",
                    help="Skip the bounded zakony/GKO/EES archive categories.")
    p.add_argument("--archives-only", action="store_true",
                    help="Shorthand for --skip-sitemap.")
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_arg_parser().parse_args(argv)
    run(
        date_from=args.date_from,
        do_sitemap=not (args.skip_sitemap or args.archives_only),
        do_dated_archives=not args.skip_dated_archives,
        do_undated_archives=not args.skip_undated_archives,
    )
