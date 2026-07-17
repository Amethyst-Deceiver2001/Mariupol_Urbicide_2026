#!/usr/bin/env python3
"""Broad capture-first crawl of mariupol.gosuslugi.ru's dokumenty-all.html
listing for "аварийн*" (emergency/dilapidated building status) documents —
a NEW subject matter for this project, distinct from the bezkhoz (ownerless)
decree family scripts/346/350 target. User-flagged 2026-07-17:
    https://mariupol.gosuslugi.ru/ofitsialno/dokumenty/dokumenty-all.html
        ?cc=469&document_search=аварийн&document_category=&document_publication_date=

"Аварийное" (emergency/dilapidated) status declarations are a documented
precursor justification for demolition elsewhere in this project's lifecycle
(see docs/case_studies/) — worth capturing, but this project has NO existing
classification scheme for this document family's internal sub-types (unlike
bezkhoz's registration/designation/removal split, which took real content
inspection to establish 2026-07-17). So this crawler captures BROADLY and
tags everything generically (mariupol_gosuslugi_avariinoe_page/_pdf) for
manual review — refine classification once real documents have been read,
same as the bezkhoz crawlers' own history.

Uses the GENERIC dokumenty-all.html?cc=469 endpoint (not one document-family
slug like scripts/346/350) since "аварийное" status can plausibly be
declared via EITHER постановления or распоряжения (or another document type
entirely) — so DOC_LINK_RX here matches ANY document landing-page slug
ending in _<digits>.html under /ofitsialno/dokumenty/, not one hardcoded
family name.

Reuses scripts/346's fetch/_page_title/_row_text_for via import.

RUN=U: same geoblocked Russian-infra host as scripts/346/350 — user-run.

Run:
    PYTHONPATH=src python scripts/351_crawl_avariinoe_status.py
"""
from __future__ import annotations

import importlib.util
import logging
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote, urljoin

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from bs4 import BeautifulSoup

from mariupol_seizures import forensics  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "m346", str(ROOT / "scripts" / "346_crawl_ownerless_designation_postanovleniya.py"))
m346 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m346)  # noqa: E402

log = logging.getLogger(__name__)

HOSTS = m346.HOSTS
fetch = m346.fetch
_page_title = m346._page_title
_row_text_for = m346._row_text_for
ATTACH_RX = m346.ATTACH_RX
PDF_LINK_RX = m346.PDF_LINK_RX

SEARCH_PATH = "/ofitsialno/dokumenty/dokumenty-all.html"
SEARCH_CC = "469"
# broad root, not "аварийное"/"аварийный"/etc individually — same lesson
# learned from the bezkhoz crawl's "бесхоз" broad-term fix 2026-07-17.
SEARCH_TERMS = ["аварийн"]

# any document-family landing page under /ofitsialno/dokumenty/, not one
# hardcoded slug — this search can plausibly surface multiple families.
DOC_LINK_RX = re.compile(r"/ofitsialno/dokumenty/[\w-]+/[\w-]+_\d+\.html")


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-pages", type=int, default=30)
    ap.add_argument("--hosts", choices=["both", "new", "old"], default="both")
    args = ap.parse_args()

    hosts = HOSTS.items() if args.hosts == "both" else [(args.hosts, HOSTS[args.hosts])]

    con = forensics.open_state()
    seen_pages: set[str] = set()
    seen_pdfs: set[str] = set()

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
                    source_type="mariupol_gosuslugi_avariinoe_listing",
                    title=f"Avariinoe search '{term}' ({host_key} host) — listing (offset {offset})",
                    description=("Broad capture-first scan for emergency/dilapidated-status "
                                 "documents (scripts/351) — NEW subject matter, no "
                                 "classification scheme established yet. Captured regardless "
                                 "of hits so a negative page is itself a complete index."),
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

                for doc_url in doc_links:
                    if doc_url in seen_pages:
                        continue
                    seen_pages.add(doc_url)
                    dcontent, dctype, dstatus = fetch(doc_url)
                    title_text = _page_title(dcontent)
                    forensics.capture_source(
                        dcontent, url=doc_url, source_type="mariupol_gosuslugi_avariinoe_page",
                        title=f"Аварийное — {title_text[:150] or doc_url}",
                        description=(f"Landing page captured by scripts/351, host={host_key}, "
                                     f"search term={term!r}. No sub-classification yet — "
                                     "manual review needed to establish this document "
                                     "family's internal types (see module docstring)."),
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
                            acontent, url=att_url, source_type="mariupol_gosuslugi_avariinoe_pdf",
                            title=f"Аварийное [PDF] — {att_url.rsplit('/', 1)[-1]}"
                                 + (f" — {title_text[:120]}" if title_text else ""),
                            description=(f"Attachment of {doc_url} (scripts/351). "
                                         "Unclassified — needs manual review."),
                            content_type=actype, http_status=astatus, con=con,
                        )
                        log.info("  [page-title] %s -> sha=%s", att_url.rsplit('/', 1)[-1], sha[:12])
                        time.sleep(0.3)
                    time.sleep(0.3)

                for pdf_url in pdf_links:
                    if pdf_url in seen_pdfs:
                        continue
                    seen_pdfs.add(pdf_url)
                    pdf_basename = pdf_url.rsplit("/", 1)[-1]
                    row_text = _row_text_for(soup, pdf_basename)
                    pcontent, pctype, pstatus = fetch(pdf_url)
                    sha = forensics.capture_source(
                        pcontent, url=pdf_url, source_type="mariupol_gosuslugi_avariinoe_pdf",
                        title=f"Аварийное [PDF] — {pdf_url.rsplit('/', 1)[-1]}"
                             + (f" — {row_text[:120]}" if row_text else ""),
                        description=(f"Captured by scripts/351, host={host_key}, "
                                     f"search term={term!r}, no landing page found — "
                                     f"row text: {row_text[:300] if row_text else '(none)'}. "
                                     "Unclassified — needs manual review."),
                        content_type=pctype, http_status=pstatus, con=con,
                    )
                    log.info("  [row-text] %s -> sha=%s", pdf_url.rsplit('/', 1)[-1], sha[:12])
                    time.sleep(0.4)

                offset += 20
                time.sleep(1.0)

    con.close()
    log.info("=" * 60)
    log.info("done. %d landing pages + %d unique PDFs captured — all "
             "unclassified, needs manual review to establish this document "
             "family's internal sub-types before building a parser.",
             len(seen_pages), len(seen_pdfs))
    log.info("Next: inspect a sample (OCR + read), then decide classification "
             "scheme, mirroring how scripts/346's registration/designation/"
             "removal split was established.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
