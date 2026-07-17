#!/usr/bin/env python3
"""Systematic crawl of mariupol.gosuslugi.ru's own document-search listing for
ownerless-related постановления — closing a real gap: this project had only
21 decrees under source_type='ownerless_decree_designation_pdf', ALL
captured via one-off, hand-targeted scripts (271/272/274/289/293) triggered
by a specific number surfacing in a Telegram citation or OCR review — never
a systematic walk of the portal's own listing.

TWO DISTINCT decree types live under "ownerless", confirmed from already-
captured examples (docs/legal_mechanisms_review.md) — this crawler captures
and classifies BOTH, not just the first:
  1. RECOGNITION/inclusion — "О признании объектов недвижимого имущества
     бесхозяйными и включении их в Реестр объектов бесхозяйного недвижимого
     имущества..." -> source_type='ownerless_decree_designation_pdf'
     (existing tag, already wired into scripts/06a's OCR discovery).
  2. REGISTRATION — "О постановке на учет недвижимой вещи в качестве
     бесхозяйной" (a DIFFERENT grammatical inflection — genitive/dative
     singular "бесхозяйной" vs. instrumental plural "бесхозяйными" — that a
     search/classifier tuned only for form (1) will silently miss, exactly
     as user-flagged 2026-07-17) -> source_type='ownerless_decree_
     registration_pdf' (NEW tag this script introduces, added to scripts/
     06a's OCR_SOURCE_TYPES in the same commit so it's not an orphaned tag).

ROOT CAUSE FOUND 2026-07-17: the portal MIGRATED HOSTS. Every prior listing/
search crawler (271/272/274/289/293) targets the OLD host,
mariupol-r897.gosweb.gosuslugi.ru. A user-flagged decree (№1468) turned out
to live at mariupol.gosuslugi.ru/netcat_files/396/4721/1468.pdf — the NEW
host (no "-r897.gosweb" segment) — which nobody had pointed a systematic
crawler at. Both hosts serve the same underlying netcat_files/396/4721/
document store, so this walks BOTH: content may be split across the
migration, not simply mirrored.

Reuses the exact search-listing mechanics scripts/293 already proved work
(cc=469 = постановления category; ?document_search=<term>&curPos=<offset>,
offset increments of 20) — same host family, same CMS. Search terms cover
BOTH decree types' distinct wordings ("бесхозяйными", "бесхозяйной",
"постановке на учет"), distinct from scripts/293's non-residential-tuned
terms ("нежилой", "коммерческих объектов", etc.) — some overlap with
scripts/293's already-captured 91 mariupol_gosuslugi_nonres_postanovlenie
docs is expected and fine (idempotent by SHA-256).

Unlike scripts/289/293 (which fetch an HTML landing page per decree, then
look for a PDF attachment inside it), the already-captured
ownerless_decree_designation_pdf/ownerless_decree_registration_pdf URLs are
ALL direct /netcat_files/396/4721/*.pdf links with no separate landing page
in the store — strong evidence the search-listing page links straight to
the PDF. This crawler captures those direct PDF links itself, tags each by
matching the listing row's own visible text (a scanned decree's PDF text
often isn't machine-readable, so classification must happen on the
readable listing HTML, not the PDF binary) into one of the two decree types
above, or a generic 'mariupol_gosuslugi_postanovlenie_pdf' catch-all
(already an existing source_type) for manual triage otherwise.

Captures EVERY listing page regardless of hits, so a negative page is
itself evidence of a complete, captured index — same convention as
scripts/289/293.

TLS note: same CA-not-in-trust-store situation as scripts/269-274/289/293;
verify=False is intentional — SHA-256 in the raw store establishes
forensic integrity, not TLS trust.

Claude must NEVER run this — it hits a DNR/occupation-administration web
property and must be run by you, from your own Russia-routed terminal
(CLAUDE.md). Everything captured is append-only and idempotent by SHA.

Usage:
    .venv312/bin/python scripts/346_crawl_ownerless_designation_postanovleniya.py
    .venv312/bin/python scripts/346_crawl_ownerless_designation_postanovleniya.py --max-pages 40
    .venv312/bin/python scripts/346_crawl_ownerless_designation_postanovleniya.py --hosts new  # skip the old host
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote, urljoin

import requests
import urllib3
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HOSTS = {
    "new": "https://mariupol.gosuslugi.ru",
    "old": "https://mariupol-r897.gosweb.gosuslugi.ru",
}
SEARCH_PATH = "/ofitsialno/dokumenty/"
SEARCH_CC = "469"  # постановления category — confirmed working, scripts/293

# Two DISTINCT decree types live under "ownerless", confirmed from already-
# captured examples (docs/legal_mechanisms_review.md):
#   1. RECOGNITION/inclusion — "О признании объектов недвижимого имущества
#      бесхозяйными и включении их в Реестр объектов бесхозяйного
#      недвижимого имущества..." (instrumental plural "бесхозяйными")
#   2. REGISTRATION — "О постановке на учет недвижимой вещи в качестве
#      бесхозяйной" (genitive/dative singular "бесхозяйной", a DIFFERENT
#      inflection the recognition-decree search term does NOT substring-
#      match) — directs УИЗО to register with Роскадастр; earlier pipeline
#      stage, e.g. №1592 (17.10.2025). User-flagged 2026-07-17: the
#      original SEARCH_TERMS list only covered form (1) and would have
#      silently under-covered form (2) even after fixing the host gap.
SEARCH_TERMS = ["бесхозяйными", "бесхозяйной", "бесхозяйного недвижимого",
                "постановке на учет"]

PDF_LINK_RX = re.compile(r"/netcat_files/\d+/\d+/[^\"'?#]+\.pdf", re.I)
# landing-page pattern confirmed on BOTH hosts 2026-07-17 (user found decree
# №1468's own landing page at .../postanovleniya-administratsii-gorodskogo-
# okruga-mariupol_1463.html on the NEW host) — same slug scripts/293 already
# uses for the OLD host. The page's own <title> is a far more reliable
# classification signal than scraping row text off a search-results listing
# (which the original version of this script relied on exclusively).
DOC_LINK_RX = re.compile(r"postanovleniya-administratsii-gorodskogo-okruga-mariupol_\d+\.html")
ATTACH_RX = re.compile(r"\.(pdf|xlsx|docx|xls|doc)(\?|$)", re.I)
NONRES_RX = re.compile(r"нежил\w*|коммерческ\w*|промышленн\w*", re.I)
REGISTRATION_RX = re.compile(r"постановке\s+на\s+учет.{0,40}бесхозяйн\w*", re.I)
RESIDENTIAL_OWNERLESS_RX = re.compile(r"бесхозяйн\w*", re.I)


def _classify(text: str) -> tuple[str, str | None]:
    is_nonres = bool(NONRES_RX.search(text))
    is_registration = bool(REGISTRATION_RX.search(text)) and not is_nonres
    is_designation = (bool(RESIDENTIAL_OWNERLESS_RX.search(text))
                      and not is_nonres and not is_registration)
    if is_registration:
        return "ownerless_decree_registration_pdf", "REGISTRATION (постановка на учет)"
    if is_designation:
        return "ownerless_decree_designation_pdf", "DESIGNATION (признание... и включение в Реестр)"
    return "mariupol_gosuslugi_postanovlenie_pdf", None


def _page_title(content: bytes) -> str:
    soup = BeautifulSoup(content, "html.parser")
    parts = []
    if soup.title and soup.title.string:
        parts.append(soup.title.string.strip())
    h1 = soup.find(["h1", "h2"])
    if h1:
        parts.append(h1.get_text(" ", strip=True))
    return " | ".join(p for p in parts if p)


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


def _row_text_for(soup: BeautifulSoup, pdf_basename: str) -> str:
    """Best-effort: grab the text of the anchor's containing row/paragraph
    for classification, since the linked PDF itself is often a scanned
    image with no extractable text layer at capture time.

    Matches by SUBSTRING containment of the PDF's basename against every
    anchor's href, not exact equality — an exact soup.find(href=...) lookup
    was observed 2026-07-17 to fail on ALL 90/90 captured PDFs in a real
    run (0 classified), because the regex that finds PDF links operates on
    raw page text and can reconstruct a URL form (absolute vs relative,
    encoding) that doesn't byte-for-byte match the actual href attribute
    BeautifulSoup parses, even though both refer to the same link."""
    for a in soup.find_all("a", href=True):
        if pdf_basename.lower() in a["href"].lower():
            row = a.find_parent(["tr", "li", "p", "div"])
            return (row or a).get_text(" ", strip=True)
    return ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-pages", type=int, default=30,
                    help="max listing pages per (host, search term) pair (default 30)")
    ap.add_argument("--hosts", choices=["both", "new", "old"], default="both",
                    help="which host(s) to crawl (default both)")
    args = ap.parse_args()

    hosts = HOSTS.items() if args.hosts == "both" else [(args.hosts, HOSTS[args.hosts])]

    con = forensics.open_state()
    seen_pages: set[str] = set()
    seen_pdfs: set[str] = set()
    n_residential = 0
    n_other = 0

    for host_key, base in hosts:
        for term in SEARCH_TERMS:
            log.info("=== host=%s term=%r ===", host_key, term)
            offset = 0
            visited = 0
            while visited < args.max_pages:
                url = (f"{base}{SEARCH_PATH}?cc={SEARCH_CC}"
                       f"&document_search={quote(term)}"
                       f"&document_category=&document_publication_date="
                       + (f"&curPos={offset}" if offset else ""))
                log.info("listing: %s", url)
                content, ctype, status = fetch(url)
                forensics.capture_source(
                    content, url=url,
                    source_type="mariupol_gosuslugi_ownerless_designation_listing",
                    title=f"Postanovleniya search '{term}' ({host_key} host) — listing (offset {offset})",
                    description=("Ownerless-designation постановление listing scan "
                                 "(scripts/346), closing the gap left by prior "
                                 "single-decree captures (271/272/274/289/293) — "
                                 "captured regardless of hits so a negative page is "
                                 "itself a complete, captured index."),
                    content_type=ctype, http_status=status, con=con,
                )
                visited += 1
                if status != 200:
                    log.warning("non-200 (%s) for %s host — stopping this term", status, host_key)
                    break

                content_str = content.decode("utf-8", "ignore")
                soup = BeautifulSoup(content, "html.parser")
                doc_links = sorted({urljoin(base, a["href"])
                                    for a in soup.find_all("a", href=True)
                                    if DOC_LINK_RX.search(a["href"])})
                pdf_links = sorted({urljoin(base, m.group(0))
                                    for m in PDF_LINK_RX.finditer(content_str)})
                if not doc_links and not pdf_links:
                    log.info("no document/PDF links on this page (host=%s term=%r "
                             "offset=%d) — stopping pagination for this term",
                             host_key, term, offset)
                    break

                # PRIMARY PATH: landing pages — classify by the page's own
                # <title>, which is authoritative (unlike scraping row text
                # off a search-results listing).
                for doc_url in doc_links:
                    if doc_url in seen_pages:
                        continue
                    seen_pages.add(doc_url)
                    dcontent, dctype, dstatus = fetch(doc_url)
                    title_text = _page_title(dcontent)
                    attachment_source_type, classified_as = _classify(title_text)
                    page_source_type = ("mariupol_gosuslugi_ownerless_designation_page"
                                        if classified_as else "mariupol_gosuslugi_postanovlenie_page")
                    forensics.capture_source(
                        dcontent, url=doc_url, source_type=page_source_type,
                        title=f"Постановление — {title_text[:150] or doc_url}",
                        description=(f"Landing page captured by scripts/346, host={host_key}, "
                                     f"search term={term!r}. "
                                     + (f"Classified {classified_as} from page title."
                                        if classified_as else
                                        "Not classified as ownerless-related from page title.")),
                        content_type=dctype, http_status=dstatus, con=con,
                    )
                    if dstatus != 200:
                        continue
                    dsoup = BeautifulSoup(dcontent, "html.parser")
                    for a in dsoup.find_all("a", href=True):
                        href = a["href"]
                        if not ATTACH_RX.search(href):
                            continue
                        att_url = urljoin(doc_url, href)
                        if att_url in seen_pdfs:
                            continue
                        seen_pdfs.add(att_url)
                        acontent, actype, astatus = fetch(att_url)
                        sha = forensics.capture_source(
                            acontent, url=att_url, source_type=attachment_source_type,
                            title=f"Постановление [PDF] — {att_url.rsplit('/', 1)[-1]}"
                                 + (f" — {title_text[:120]}" if title_text else ""),
                            description=(f"Attachment of {doc_url}, classified via that "
                                         f"page's own title (scripts/346). "
                                         + (f"Classified {classified_as}." if classified_as
                                            else "Generic postановление catch-all.")),
                            content_type=actype, http_status=astatus, con=con,
                        )
                        if classified_as:
                            n_residential += 1
                        else:
                            n_other += 1
                        log.info("  [page-title] %s -> sha=%s [%s]%s",
                                 att_url.rsplit('/', 1)[-1], sha[:12], attachment_source_type,
                                 f" *** {classified_as}" if classified_as else "")
                        time.sleep(0.3)
                    time.sleep(0.3)

                # SUPPLEMENTARY PATH: direct PDF links on the listing with no
                # discoverable landing page (observed 2026-07-16/17 on the
                # new host's "бесхозяйными" search) — fall back to row-text
                # classification (best-effort, less reliable than a title).
                for pdf_url in pdf_links:
                    if pdf_url in seen_pdfs:
                        continue
                    seen_pdfs.add(pdf_url)
                    pdf_basename = pdf_url.rsplit("/", 1)[-1]
                    row_text = _row_text_for(soup, pdf_basename)
                    source_type, classified_as = _classify(row_text)

                    pcontent, pctype, pstatus = fetch(pdf_url)
                    sha = forensics.capture_source(
                        pcontent, url=pdf_url, source_type=source_type,
                        title=f"Постановление [PDF] — {pdf_url.rsplit('/', 1)[-1]}"
                             + (f" — {row_text[:120]}" if row_text else ""),
                        description=(f"Captured by the ownerless-designation postановление "
                                     f"listing crawl (scripts/346), host={host_key}, "
                                     f"search term={term!r}, no landing page found for this "
                                     f"link — classified from listing row text (best-effort). "
                                     + (f"Listing row text: {row_text[:300]}. " if row_text
                                        else "No listing row text recovered for classification. ")
                                     + (f"Classified {classified_as}." if classified_as else
                                        "Not classified as ownerless-related — generic "
                                        "postановление catch-all, needs manual triage.")),
                        content_type=pctype, http_status=pstatus, con=con,
                    )
                    if classified_as:
                        n_residential += 1
                    else:
                        n_other += 1
                    log.info("  [row-text] %s -> sha=%s [%s]%s", pdf_url.rsplit('/', 1)[-1], sha[:12],
                             source_type, f" *** {classified_as}" if classified_as else "")
                    time.sleep(0.4)

                offset += 20
                time.sleep(1.0)

    con.close()
    log.info("=" * 60)
    log.info("done. %d landing pages + %d unique PDFs captured — %d classified "
             "as designation/registration ownerless decrees "
             "(ownerless_decree_designation_pdf or ownerless_decree_"
             "registration_pdf), %d left as generic postановление catch-all "
             "for manual triage.",
             len(seen_pages), len(seen_pdfs), n_residential, n_other)
    log.info("Next: PYTHONPATH=src python scripts/06a_ocr_decrees.py — extend/"
             "re-run OCR over any newly-captured ownerless_decree_designation_pdf/"
             "ownerless_decree_registration_pdf rows (06a's OCR_SOURCE_TYPES "
             "already includes 'ownerless_decree_registration_pdf').")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
