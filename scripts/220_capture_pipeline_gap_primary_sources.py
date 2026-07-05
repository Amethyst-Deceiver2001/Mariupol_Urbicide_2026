#!/usr/bin/env python3
"""Capture the primary-source documents identified while reviewing
docs/research_outsourcing/dispossession_pipeline_gaps_results.md against
RESEARCH_BRIEF.md's rank-1/2 bar. The outsourced deliverable closed Tasks 6
(Постановление №2501) and 9 (Указ №1103) on rank-3/4 paraphrase only
(GARANT/Kontur/ppt.ru summaries); this script fetches the actual rank-1 texts
found during review, plus one dead-link correction and one already-verified
PDF that was never run through the forensic capture pipeline.

Targets:
    1. Постановление Правительства РФ №2501 (30.12.2022) -- full text,
       pravo.gov.ru official publication (Task 6).
    2. Указ Президента РФ №1103 (24.12.2024) -- full text, pravo.gov.ru
       official publication (Task 9) -- also resolves the title/scope
       question (whether "нотариальных действий" belongs to №1103 itself
       or a later amendment).
    3. Закон ДНР №71-РЗ (amendment to №52-РЗ) -- corrected gb-dnr.ru URL;
       the researcher's cited link 404s.
    4. Закон ДНР №52-РЗ -- denis-pushilin.ru PDF (Task 7). Already verified
       ad hoc via curl -k during review; captured here properly with a
       hash + chain-of-custody record. config.SSL_VERIFY defaults to False,
       so no extra cert handling is needed in the crawler itself.

pravo.gov.ru is a JS-rendered SPA shell over plain GET -- if the captured
bytes don't contain "Статья"/"ПОСТАНОВЛЯЕТ" etc. after this fetch, retry
with the print-view/RTF technique in scripts/216 before trusting the text.

Run (from the user's own terminal -- gb-dnr.ru and denis-pushilin.ru may
need the VPS if geoblocked from here; pravo.gov.ru has resolved directly
in past sessions):
    PYTHONPATH=src python scripts/220_capture_pipeline_gap_primary_sources.py
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
        "url": "http://publication.pravo.gov.ru/Document/View/0001202212300029",
        "source_type": "gko_rf_resolution_2501",
        "title": "Постановление Правительства РФ №2501 от 30.12.2022 -- official publication",
        "description": (
            "Task 6 follow-up: dispossession_pipeline_gaps_results.md closed this "
            "on GARANT/zakonrf.info paraphrase only, admitting the full text was "
            "'behind GARANT's interface'. This is the rank-1 primary text found "
            "during review."
        ),
        "content_type": "text/html",
    },
    {
        "url": "http://publication.pravo.gov.ru/document/0001202412240001",
        "source_type": "presidential_decree_1103",
        "title": "Указ Президента РФ №1103 от 24.12.2024 -- official publication",
        "description": (
            "Task 9 follow-up: dispossession_pipeline_gaps_results.md closed this "
            "on ppt.ru/Kontur paraphrase only. Also resolves whether the clause "
            "'совершения отдельных нотариальных действий' belongs to №1103 itself "
            "or was conflated from a later amendment (likely №1006) -- grep the "
            "captured text for that phrase to check."
        ),
        "content_type": "text/html",
    },
    {
        "url": "http://www.gb-dnr.ru/normativno-pravovye-akty/14696/384859/",
        "source_type": "dnr_law_71rz_amendment",
        "title": "Закон ДНР №71-РЗ (amendment to №52-РЗ) -- corrected gb-dnr.ru URL",
        "description": (
            "Task 7 follow-up: the deliverable's cited URL "
            "(gb-dnr.ru/normativno-pravovye-akty/15217/) 404s. This corrected "
            "URL was found via WebSearch during review and returns 301/200."
        ),
        "content_type": "text/html",
    },
    {
        "url": "https://denis-pushilin.ru/doc/zakony/52rz.pdf",
        "source_type": "dnr_law_52rz",
        "title": "Закон ДНР №52-РЗ -- full text PDF",
        "description": (
            "Task 7: verified during review (curl -k, 200, 194KB, 17pp, "
            "pdftotext confirms genuine 'Статья 1...' operative text). "
            "denis-pushilin.ru serves a self-signed cert -- not geoblocked, "
            "just cert-quirky; config.SSL_VERIFY=False handles this by default."
        ),
        "content_type": "application/pdf",
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
            content_type=r.headers.get("Content-Type", t["content_type"]),
            http_status=r.status_code, con=con,
        )
        log.info("  status=%d sha=%s bytes=%d", r.status_code, sha[:16], len(r.content))

    log.info(
        "Done. For the two pravo.gov.ru targets, grep the captured file for "
        "'Статья'/'ПОСТАНОВЛЯЕТ' -- if empty (JS-shell-only), re-fetch with "
        "the print-view/RTF technique from scripts/216 before treating as text."
    )


if __name__ == "__main__":
    main()
