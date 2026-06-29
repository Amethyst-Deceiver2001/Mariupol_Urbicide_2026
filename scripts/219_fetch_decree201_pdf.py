#!/usr/bin/env python3
"""Capture Presidential Decree No. 201 (20.03.2020) -- the Crimea
border-territory foreign-ownership ban, genealogical first step in
docs/exhibits/two-property-systems.html (Q12,
docs/research_outsourcing/OPEN_QUESTIONS_2026-06-29.md).

After scripts/212-218's free-text search engine couldn't surface it (the
ИПС full-text search scores loose keyword overlap, not phrase/field match,
and got swamped by every unrelated document sharing a date or number
token), the publication id was found via a NON-geoblocked web search
(title + decree number), confirming the exact instrument:

    "О внесении изменений в перечень приграничных территорий, на которых
    иностранные граждане, лица без гражданства и иностранные юридические
    лица не могут обладать на праве собственности земельными участками,
    утвержденный Указом Президента Российской Федерации от 9 января 2011 г.
    № 26" -- i.e. confirmed: it IS an amendment to Decree No. 26 (09.01.2011),
    as recalled.

    publication.pravo.gov.ru/Document/View/0001202003200021

Same two-step pattern as scripts/207/208: the View page is likely a JS-shell
SPA wrapper (no document text) -- fetch it first, then grep the captured
HTML for "eoNumber=" to find the real PDF link
(/file/pdf?eoNumber=0001202003200021, by analogy with scripts/208, though
confirm rather than assume since the eoNumber doesn't always equal the
publication id verbatim).

Run:
    PYTHONPATH=src python scripts/219_fetch_decree201_pdf.py
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

PUB_ID = "0001202003200021"

TARGETS = [
    {
        "url": f"http://publication.pravo.gov.ru/document/view/{PUB_ID}",
        "source_type": "crimea_decree_201_view",
        "title": "Указ Президента РФ от 20.03.2020 № 201 -- View page",
        "description": (
            "Q12. View-page shell, likely JS SPA wrapper (same pattern as "
            "scripts/207's pravo.gov.ru fetches) -- grep for 'eoNumber=' "
            "afterward to find the real PDF link."
        ),
    },
    {
        # Try the direct PDF pattern immediately too (scripts/208's pattern) --
        # if the eoNumber equals the publication id verbatim, this saves a hop.
        "url": f"http://publication.pravo.gov.ru/file/pdf?eoNumber={PUB_ID}",
        "source_type": "crimea_decree_201_pdf_guess",
        "title": "Указ Президента РФ от 20.03.2020 № 201 -- direct PDF guess",
        "description": (
            "Q12. Speculative direct-PDF fetch assuming eoNumber == "
            "publication id (true for the scripts/207/208 GKO decrees) -- "
            "verify page count with pdfinfo before treating as confirmed."
        ),
    },
]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    con = forensics.open_state()
    s = requests.Session()
    s.headers.update({"User-Agent": config.USER_AGENT, "Accept-Language": "ru,en;q=0.8"})
    if config.PROXY:
        s.proxies.update({"http": config.PROXY, "https": config.PROXY})

    for t in TARGETS:
        log.info("Fetching %s", t["url"])
        try:
            r = s.get(t["url"], timeout=config.TIMEOUT, verify=config.SSL_VERIFY, allow_redirects=True)
        except requests.RequestException as e:
            log.error("  FAILED: %s -- retry from the VPS if connection/TLS error", e)
            continue
        if r.status_code != 200:
            log.warning("  HTTP %d for %s -- captured anyway for the record", r.status_code, t["url"])
        sha = forensics.capture_source(
            r.content, url=t["url"], source_type=t["source_type"], title=t["title"],
            description=t["description"],
            content_type=r.headers.get("Content-Type", "application/octet-stream"),
            http_status=r.status_code, con=con,
        )
        log.info("  status=%d sha=%s bytes=%d", r.status_code, sha[:16], len(r.content))

    log.info("Done. If the PDF guess returned a real PDF (check via "
              "`file <path>` -- should say 'PDF document'), OCR it next "
              "(ocrmypdf --force-ocr -l rus, .venv not .venv312, same as "
              "every other captured decree this session). If it's HTML/JSON "
              "instead, read the View-page shell for the real eoNumber.")


if __name__ == "__main__":
    main()
