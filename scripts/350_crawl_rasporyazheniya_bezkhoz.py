#!/usr/bin/env python3
"""Systematic crawl of mariupol.gosuslugi.ru's РАСПОРЯЖЕНИЯ (Directives of
the Head of Administration) document family for ownerless-related content —
a SEPARATE document series from scripts/346's ПОСТАНОВЛЕНИЯ (Decrees of the
Administration) target, never previously crawled at all.

User-flagged 2026-07-17: the same subject matter ("О признании объектов
недвижимого имущества бесхозяйными и включении их в Реестр объектов
бесхозяйного имущества") is ALSO issued as a Распоряжение, e.g.
    https://mariupol.gosuslugi.ru/ofitsialno/dokumenty/
        rasporyazheniya-glavy-administratsii-goroda-mariupolya/
        rasporyazheniya-glavy-administratsii-goroda-mariupolya_1447.html
— a completely different URL path/landing-page slug than постановления, so
scripts/346's DOC_LINK_RX never matched any of these and this whole document
family was invisible to every prior crawl.

Reuses scripts/346's classification logic (_classify/_page_title/
_row_text_for/fetch and all its regex constants) via import rather than
duplicating it — only the URL-building and landing-page-slug regex differ
here. Mirrors the SIMPLER per-category listing search pattern the user's own
example URL confirmed works (`<slug>.html?document_search=<term>&curPos=<n>`)
rather than scripts/346's global cc=469-scoped endpoint, since the correct
"cc" category code for распоряжения is unknown and this pattern needs none.

RUN=U: same geoblocked Russian-infra host as scripts/346 — user-run, per
this project's standing rule.

Run:
    PYTHONPATH=src python scripts/350_crawl_rasporyazheniya_bezkhoz.py
"""
from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from urllib.parse import quote, urljoin

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import re
from bs4 import BeautifulSoup

from mariupol_seizures import forensics  # noqa: E402

import importlib.util
_spec = importlib.util.spec_from_file_location(
    "m346", str(ROOT / "scripts" / "346_crawl_ownerless_designation_postanovleniya.py"))
m346 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m346)  # noqa: E402

log = logging.getLogger(__name__)

HOSTS = m346.HOSTS
SEARCH_TERMS = m346.SEARCH_TERMS
_classify = m346._classify
_page_title = m346._page_title
_row_text_for = m346._row_text_for
fetch = m346.fetch
ATTACH_RX = m346.ATTACH_RX
PDF_LINK_RX = m346.PDF_LINK_RX

SLUG = "rasporyazheniya-glavy-administratsii-goroda-mariupolya"
LISTING_PATH = f"/ofitsialno/dokumenty/{SLUG}/{SLUG}.html"
DOC_LINK_RX = re.compile(rf"{SLUG}_\d+\.html")


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-pages", type=int, default=30,
                    help="max listing pages per (host, search term) pair (default 30)")
    ap.add_argument("--hosts", choices=["both", "new", "old"], default="both")
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
                url = (f"{base}{LISTING_PATH}?document_search={quote(term)}"
                      f"&document_publication_date="
                      + (f"&curPos={offset}" if offset else ""))
                log.info("listing: %s", url)
                content, ctype, status = fetch(url)
                forensics.capture_source(
                    content, url=url,
                    source_type="mariupol_gosuslugi_rasporyazheniya_listing",
                    title=f"Rasporyazheniya search '{term}' ({host_key} host) — listing (offset {offset})",
                    description=("Ownerless-related rasporyazhenie listing scan (scripts/350) — "
                                 "a SEPARATE document family from scripts/346's постановления, "
                                 "never previously crawled. Captured regardless of hits so a "
                                 "negative page is itself a complete, captured index."),
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

                # PRIMARY PATH: landing pages, classify by the page's own title.
                for doc_url in doc_links:
                    if doc_url in seen_pages:
                        continue
                    seen_pages.add(doc_url)
                    dcontent, dctype, dstatus = fetch(doc_url)
                    title_text = _page_title(dcontent)
                    attachment_source_type, classified_as = _classify(title_text)
                    page_source_type = ("mariupol_gosuslugi_ownerless_rasporyazhenie_page"
                                        if classified_as else "mariupol_gosuslugi_rasporyazhenie_page")
                    forensics.capture_source(
                        dcontent, url=doc_url, source_type=page_source_type,
                        title=f"Распоряжение — {title_text[:150] or doc_url}",
                        description=(f"Landing page captured by scripts/350, host={host_key}, "
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
                            title=f"Распоряжение [PDF] — {att_url.rsplit('/', 1)[-1]}"
                                 + (f" — {title_text[:120]}" if title_text else ""),
                            description=(f"Attachment of {doc_url}, classified via that "
                                         f"page's own title (scripts/350). "
                                         + (f"Classified {classified_as}." if classified_as
                                            else "Generic rasporyazhenie catch-all.")),
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

                # SUPPLEMENTARY PATH: direct PDF links with no landing page.
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
                        title=f"Распоряжение [PDF] — {pdf_url.rsplit('/', 1)[-1]}"
                             + (f" — {row_text[:120]}" if row_text else ""),
                        description=(f"Captured by the rasporyazhenie listing crawl "
                                     f"(scripts/350), host={host_key}, search term={term!r}, "
                                     f"no landing page found — classified from listing row "
                                     f"text (best-effort). "
                                     + (f"Listing row text: {row_text[:300]}. " if row_text
                                        else "No listing row text recovered. ")
                                     + (f"Classified {classified_as}." if classified_as else
                                        "Not classified — generic catch-all, needs manual triage.")),
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
             "as ownerless (designation/registration/removal), %d left as "
             "generic rasporyazhenie catch-all for manual triage.",
             len(seen_pages), len(seen_pdfs), n_residential, n_other)
    log.info("Next: PYTHONPATH=src python scripts/06a_ocr_decrees.py")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
