#!/usr/bin/env python3
"""Capture Постановление Правительства РФ №2565 (31.12.2022) -- the
"льготная ипотека 2%" decree for DNR/LNR/Zaporizhzhia/Kherson, the [F]-track
"[REPORTED]" item in docs/legal_mechanisms_review.md. Found via web search
(no exact number was on file yet): establishes DOM.RF-administered subsidies
to lenders so residents (and, per the decree's own text, ANY Russian citizen)
can borrow at <=2%/year to buy or build housing in the four annexed regions.

publication.pravo.gov.ru is NOT geoblocked -- confirmed directly (plain curl,
200, real content, no VPN/VPS needed) -- unlike mariupol.gosuslugi.ru/
gisnpa-dnr.ru elsewhere in this project. Safe to run from any machine.

Run:
    PYTHONPATH=src python scripts/246_capture_lgotnaya_ipoteka_2pct.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import requests  # noqa: E402

from mariupol_seizures import config, forensics  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
log = logging.getLogger(__name__)

TARGETS = [
    {
        "url": "http://publication.pravo.gov.ru/Document/View/0001202301030011",
        "source_type": "lgotnaya_ipoteka_2pct_landing",
        "title": "Постановление Правительства РФ №2565 (31.12.2022) -- official publication landing page",
        "description": (
            "Base decree establishing the 2%-rate subsidized mortgage program "
            "for housing purchase/construction in DNR/LNR/Zaporizhzhia/Kherson "
            "(open to any RF citizen, not just residents). Landing page only "
            "-- see the .pdf target below for the actual signed text."
        ),
        "content_type": "text/html",
    },
    {
        "url": "http://publication.pravo.gov.ru/file/pdf?eoNumber=0001202301030011",
        "source_type": "lgotnaya_ipoteka_2pct_pdf",
        "title": "Постановление Правительства РФ №2565 (31.12.2022) -- signed PDF, official gazette scan",
        "description": (
            "Full signed text (46pp, image-only ABBYY-style scan, Mishustin "
            "signature block on p.2). Confirmed via local OCR (.venv312, "
            "pytesseract rus) to contain the actual 2%-rate provision: "
            "'размер процентной ставки по кредитному договору составляет не "
            "более 2 процентов годовых' (p.~15 of the OCR text). Also sets "
            "loan/downpayment terms and the DOM.RF subsidy-disbursement "
            "mechanics to participating banks."
        ),
        "content_type": "application/pdf",
    },
    {
        "url": "http://publication.pravo.gov.ru/document/0001202312150019",
        "source_type": "lgotnaya_ipoteka_amendment_2166_landing",
        "title": "Постановление Правительства РФ №2166 (15.12.2023) -- amendment landing page",
        "description": (
            "Amendment decree -- 'О внесении изменений в некоторые акты "
            "Правительства Российской Федерации по вопросам жилищного "
            "(ипотечного) кредитования граждан Российской Федерации'. Per "
            "secondary reporting, mainly retools Far-Eastern/Arctic mortgage "
            "credit limits; captured for completeness since it amends the "
            "same family of DOM.RF mortgage-subsidy decrees as №2565 -- not "
            "yet confirmed whether it touches the DNR/LNR/Zaporizhzhia/"
            "Kherson provisions specifically. Read before citing as a §2565 "
            "amendment proper."
        ),
        "content_type": "text/html",
    },
]


def main() -> None:
    con = forensics.open_state()
    s = requests.Session()
    s.headers.update({"User-Agent": config.USER_AGENT, "Accept-Language": "ru,en;q=0.8"})
    if config.PROXY:
        s.proxies.update({"http": config.PROXY, "https": config.PROXY})

    for t in TARGETS:
        log.info("Fetching %s", t["url"])
        try:
            r = s.get(t["url"], timeout=max(config.TIMEOUT, 60), verify=config.SSL_VERIFY, allow_redirects=True)
        except requests.RequestException as e:
            log.error("  FAILED: %s", e)
            continue
        if r.status_code != 200:
            log.warning("  HTTP %d for %s -- captured anyway for the record", r.status_code, t["url"])
        sha = forensics.capture_source(
            r.content, url=t["url"], source_type=t["source_type"], title=t["title"],
            description=t["description"],
            content_type=r.headers.get("Content-Type", t["content_type"]),
            http_status=r.status_code, con=con,
        )
        log.info("  status=%d sha=%s bytes=%d", r.status_code, sha[:16], len(r.content))

    log.info("Done. №2565 PDF is image-only -- OCR before treating as claim-grade "
              "(see .venv312 pytesseract/pdf2image, lang='rus').")


if __name__ == "__main__":
    main()
