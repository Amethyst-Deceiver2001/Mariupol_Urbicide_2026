#!/usr/bin/env python3
"""Capture two primary legal instruments identified via discovery research
(progress_report_2026-06.md §5 items 10-11):

1. DNR Закон №269-РЗ (signed by Pushilin 03.04.2026, published 06.04.2026) --
   "Об особенностях распоряжения жилыми помещениями, имевшими признаки
   бесхозяйного имущества... а также условиях и порядке предоставления
   компенсации гражданам РФ, утратившим право собственности на такие жилые
   помещения, и о внесении изменений в Закон ДНР №141-РЗ". This is the
   primary source for the [REPORTED]-only 25 sq.m compensation cap and the
   1 Jan 2028 deadline for using seized/abandoned housing as служебное
   жилье -- amends Закон №141-РЗ (18.12.2024), already in the project's
   legal_mechanisms_review.md as [CITED].
   - DNR-side host: https://glavadnr.ru/doc/zakony/269rz.pdf
   - Federal official-publication mirror (independent corroboration, same
     ≥2-source rule as everything else):
     http://publication.pravo.gov.ru/document/8000202604060001

2. Постановление Правительства РФ от 15.12.2023 № 2166 -- the confirmed
   amendment to the 2% subsidized-mortgage-for-new-regions program
   (Промсвязьбанк as primary operator). The ORIGINAL launch resolution
   (signed by Mishustin, reported ~early Jan 2023, following Putin's
   15.12.2022 strategic-council directive) could not be pinned to a
   number/date from press coverage alone -- this captures the confirmed
   amendment; the launch decree remains an open sub-gap, flagged in
   docs/progress_report_2026-06.md.
   - http://publication.pravo.gov.ru/document/0001202312150019

WHY THIS IS USER-RUN-ONLY
--------------------------
pravo.gov.ru is the Russian Federal official legal-publication portal and
glavadnr.ru is DNR occupation-administration infrastructure -- both fall
under the same geoblocked-foreign-state-system rule as court_crawler.py and
ownerless_lists.py (see CLAUDE.md). Unlike denis-pushilin.ru (confirmed
directly reachable, no VPS, scripts/39), these two domains are UNTESTED for
direct reachability -- run this from the Russia-routed VPS to be safe; if it
turns out glavadnr.ru/pravo.gov.ru are directly reachable, no harm done,
exits the same way.

Run:
    PYTHONPATH=src python scripts/197_crawl_zakon269_and_mortgage_decree.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import requests  # noqa: E402
import urllib3  # noqa: E402

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

if not config.SSL_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TARGETS = [
    {
        "url": "https://glavadnr.ru/doc/zakony/269rz.pdf",
        "source_type": "dnr_law_269rz_pdf",
        "title": "Закон ДНР №269-РЗ от 03.04.2026 (DNR-side PDF)",
        "description": (
            "Primary source for the [REPORTED]-only 25 sq.m compensation cap "
            "and 1 Jan 2028 official-housing deadline; amends Закон №141-РЗ. "
            "progress_report_2026-06.md §5 item 10."
        ),
    },
    {
        "url": "http://publication.pravo.gov.ru/document/8000202604060001",
        "source_type": "dnr_law_269rz_federal_mirror",
        "title": "Закон ДНР №269-РЗ -- федеральная официальная публикация (pravo.gov.ru)",
        "description": (
            "Independent federal corroboration of the DNR-side PDF above -- "
            "satisfies the ≥2-source legal-grade rule for this instrument."
        ),
    },
    {
        "url": "http://publication.pravo.gov.ru/document/0001202312150019",
        "source_type": "federal_mortgage_decree_2166",
        "title": "Постановление Правительства РФ от 15.12.2023 № 2166",
        "description": (
            "Confirmed amendment to the 2% subsidized-mortgage-for-new-regions "
            "program (Промсвязьбанк). progress_report_2026-06.md §5 item 11. "
            "The original ~Jan-2023 launch resolution number is still "
            "unconfirmed -- a residual sub-gap, not closed by this capture."
        ),
    },
]


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": config.USER_AGENT, "Accept-Language": "ru,en;q=0.8"})
    if config.PROXY:
        s.proxies.update({"http": config.PROXY, "https": config.PROXY})
    return s


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    con = forensics.open_state()
    s = make_session()

    for t in TARGETS:
        log.info("Fetching %s", t["url"])
        try:
            r = s.get(t["url"], timeout=config.TIMEOUT, verify=config.SSL_VERIFY,
                      allow_redirects=True)
        except requests.RequestException as e:
            log.error("  FAILED: %s -- if this is a connection/TLS error, retry from the VPS", e)
            continue

        if r.status_code != 200:
            log.warning("  HTTP %d for %s -- captured anyway for the record", r.status_code, t["url"])

        sha = forensics.capture_source(
            r.content, url=t["url"], source_type=t["source_type"],
            title=t["title"], description=t["description"],
            content_type=r.headers.get("Content-Type", "application/octet-stream"),
            http_status=r.status_code, con=con,
        )
        log.info("  status=%d sha=%s bytes=%d", r.status_code, sha[:16], len(r.content))

    log.info("Done. Next: OCR any new PDFs (pattern: scripts/06a_ocr_decrees.py, "
              "PYTHONPATH=src .venv/bin/python3 -- ocrmypdf lives in .venv not .venv312) "
              "then parse/append findings to docs/legal_mechanisms_review.md.")


if __name__ == "__main__":
    main()
