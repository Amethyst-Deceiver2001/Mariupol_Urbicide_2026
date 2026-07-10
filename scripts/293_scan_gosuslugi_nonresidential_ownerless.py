#!/usr/bin/env python3
"""Scan the Mariupol administration document portal for the NON-RESIDENTIAL and
combined residential/non-residential "ownerless-signs" lists that the project
currently holds only as June-2023 MinStroy attachments and poor phone-photos.

WHY THIS EXISTS (the gap this closes)
-------------------------------------
Two things point to a newer, official, primary source we do NOT yet hold:

  1. @mrpl_besxozxata/94813 (05.06.2026) quotes an administration постановление
     listing objects "имеющих признаки бесхозяйного (жилой/нежилой фонд) по
     состоянию на 05.06.2026" and requiring a выписка из ЕГРН — i.e. a COMBINED
     residential + non-residential ownerless list, more recent than anything
     loaded. We hold only three resident phone-screenshots of it (94810-94812),
     too low-resolution to OCR.

  2. The commercial/industrial "признаки бесхозности" lists we DO hold
     (@minstroydnr 3063/3227/3235) are from June 2023 and may have been
     superseded by a newer administration edition.

This walks the administration's own постановления document-search endpoint for
non-residential / ownerless search terms, capturing every listing page and
every linked document page + PDF/XLSX/DOCX attachment whose visible text
matches — so the primary source (wherever it lives on the portal) lands in the
raw store with full chain of custody, and a negative result is itself a
captured, complete index.

TLS note: this host uses a CA not in the standard trust store (same as
scripts/269-274/289); verify=False is intentional — SHA-256 in the raw store,
not TLS trust, establishes forensic integrity.

Claude must NEVER run this — it hits a DNR/occupation-administration web
property and must be run by you, from your own Russia-routed terminal
(CLAUDE.md). Everything it captures is append-only and idempotent by SHA.

Usage:
    .venv312/bin/python scripts/293_scan_gosuslugi_nonresidential_ownerless.py
    .venv312/bin/python scripts/293_scan_gosuslugi_nonresidential_ownerless.py --max-pages 40
"""
import argparse
import logging
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, quote

import requests
import urllib3
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE = "https://mariupol-r897.gosweb.gosuslugi.ru"
# The постановления document-search endpoint (cc=469 is the postановления
# category, confirmed from the already-captured "подлежащими сносу" search).
SEARCH_PATH = "/ofitsialno/dokumenty/"
SEARCH_CC = "469"

# Search terms most likely to surface the combined / non-residential lists.
SEARCH_TERMS = [
    "бесхоз",
    "нежилой",
    "нежилого",
    "коммерческих объектов",
    "признаки бесхозяйного",
    "не функционирующих",
]

# Flag any captured document whose visible text matches these (non-residential
# or combined ownerless language, or the specific 05.06.2026 snapshot date).
FLAG_RX = re.compile(
    r"нежил\w*|коммерческ\w*|промышленн\w*|признак\w*\s+бесхоз|05\.06\.2026", re.I
)
DOC_LINK_RX = re.compile(r"postanovleniya-administratsii-gorodskogo-okruga-mariupol_\d+\.html")
ATTACH_RX = re.compile(r"\.(pdf|xlsx|docx|xls|doc)(\?|$)", re.I)


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


def visible_text(html_bytes: bytes) -> str:
    soup = BeautifulSoup(html_bytes, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    return soup.get_text("\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-pages", type=int, default=25,
                    help="max listing pages per search term (default 25)")
    args = ap.parse_args()

    con = forensics.open_state()
    seen_docs: set[str] = set()
    seen_attach: set[str] = set()
    flagged_hits: list[str] = []

    for term in SEARCH_TERMS:
        log.info("=== search term: %r ===", term)
        offset = 0
        visited = 0
        while visited < args.max_pages:
            url = (f"{BASE}{SEARCH_PATH}?cc={SEARCH_CC}"
                   f"&document_search={quote(term)}"
                   f"&document_category=&document_publication_date="
                   + (f"&curPos={offset}" if offset else ""))
            log.info("listing: %s", url)
            content, ctype, status = fetch(url)
            forensics.capture_source(
                content, url=url,
                source_type="mariupol_gosuslugi_nonres_search_listing",
                title=f"Postanovleniya search '{term}' — listing (offset {offset})",
                description=("Non-residential/ownerless list scan (scripts/293). "
                             "Captured regardless of hits so a negative result is "
                             "itself a complete, captured index."),
                content_type=ctype, http_status=status, con=con,
            )
            visited += 1
            if status != 200:
                log.warning("non-200 (%s) — stopping this term", status)
                break

            soup = BeautifulSoup(content, "html.parser")
            doc_links = {urljoin(BASE, a["href"]) for a in soup.find_all("a", href=True)
                         if DOC_LINK_RX.search(a["href"])}
            if not doc_links:
                log.info("no document links on this page — listing may be JS-rendered "
                         "or the term has no matches; check the captured page by hand")
                break

            for doc_url in sorted(doc_links):
                if doc_url in seen_docs:
                    continue
                seen_docs.add(doc_url)
                dcontent, dctype, dstatus = fetch(doc_url)
                dtext = visible_text(dcontent)
                flagged = bool(FLAG_RX.search(dtext))
                sha = forensics.capture_source(
                    dcontent, url=doc_url,
                    source_type="mariupol_gosuslugi_nonres_postanovlenie",
                    title=f"Постановление — {doc_url}",
                    description=("FLAGGED non-residential/ownerless match — " if flagged
                                 else "captured (no flag) — ")
                                + "non-residential list scan (scripts/293).",
                    content_type=dctype, http_status=dstatus, con=con,
                )
                if flagged:
                    flagged_hits.append(doc_url)
                    log.info("*** FLAGGED: %s -> %s", doc_url, sha[:12])

                # capture attachments (the actual list is usually a PDF/XLSX annex)
                dsoup = BeautifulSoup(dcontent, "html.parser")
                for a in dsoup.find_all("a", href=True):
                    href = a["href"]
                    if ATTACH_RX.search(href):
                        att_url = urljoin(BASE, href)
                        if att_url in seen_attach:
                            continue
                        seen_attach.add(att_url)
                        acontent, actype, astatus = fetch(att_url)
                        asha = forensics.capture_source(
                            acontent, url=att_url,
                            source_type="mariupol_gosuslugi_nonres_attachment",
                            title=f"Attachment — {att_url}",
                            description="Attachment to a postановление surfaced by the "
                                        "non-residential list scan (scripts/293).",
                            content_type=actype, http_status=astatus, con=con,
                        )
                        log.info("    attachment %s -> %s (%d bytes)",
                                 att_url.rsplit('/', 1)[-1], asha[:12], len(acontent))
                        time.sleep(0.4)
                time.sleep(0.5)

            offset += 20
            time.sleep(1.0)

    con.close()
    log.info("=" * 60)
    log.info("done. %d unique documents, %d attachments captured; %d flagged.",
             len(seen_docs), len(seen_attach), len(flagged_hits))
    if flagged_hits:
        log.info("FLAGGED documents (review these + tell Claude):")
        for u in flagged_hits:
            log.info("   %s", u)
    else:
        log.info("No non-residential/ownerless-flagged document found in the scanned "
                 "listings. Either the 05.06.2026 combined list lives elsewhere "
                 "(e.g. a МИЗО/MinStroy Telegram post, not the postановления portal), "
                 "or the search endpoint renders results via JS — inspect the captured "
                 "listing pages by hand and tell Claude what host/path actually serves it.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
