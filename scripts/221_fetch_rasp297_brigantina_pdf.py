#!/usr/bin/env python3
"""Capture Распоряжение Главы ДНР №297 (16.07.2024) -- the no-tender land
lease to ООО «СЗ "ГСА Девелопмент"» for ЖСК «Бригантина» (3 parcels,
15,253 m² total), the land-grant order that closes Q6 in
docs/research_outsourcing/OPEN_QUESTIONS.md and is the primary instrument
behind docs/research_outsourcing/brigantina_case_study.md.

URL supplied by the user (2026-06-29):
    https://glavadnr.ru/doc/rasp/rasporiazhglavaN297_16072024.pdf

Same glavadnr.ru/doc/ domain pattern as GKO №164/№263/№300 -- not
geoblocked, confirmed via direct probe (HTTP 200, ~424KB PDF).

The case study cites a different mirror (doc.dnronline.su) for the same
instrument and already quotes the full operative clause verbatim -- this
script captures our own copy into the forensic store for chain-of-custody,
independent of that secondary transcription.

Run:
    PYTHONPATH=src python scripts/221_fetch_rasp297_brigantina_pdf.py
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

URL = "https://glavadnr.ru/doc/rasp/rasporiazhglavaN297_16072024.pdf"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    con = forensics.open_state()
    s = requests.Session()
    s.headers.update({"User-Agent": config.USER_AGENT, "Accept-Language": "ru,en;q=0.8"})
    if config.PROXY:
        s.proxies.update({"http": config.PROXY, "https": config.PROXY})

    log.info("Fetching %s", URL)
    r = s.get(URL, timeout=config.TIMEOUT, verify=config.SSL_VERIFY, allow_redirects=True)
    if r.status_code != 200:
        log.warning("HTTP %d for %s -- captured anyway for the record", r.status_code, URL)
    sha = forensics.capture_source(
        r.content, url=URL, source_type="rasp_297_brigantina_pdf",
        title="Распоряжение Главы ДНР №297 (16.07.2024) -- ЖСК «Бригантина» land lease to ГСА Девелопмент",
        description=(
            "Q6 closure. No-tender lease of 3 parcels (15,253 m2 total) to "
            "OOO SZ GSA Development for a 62-unit townhouse settlement. URL "
            "supplied directly by the user, glavadnr.ru, not geoblocked."
        ),
        content_type=r.headers.get("Content-Type", "application/pdf"),
        http_status=r.status_code, con=con,
    )
    log.info("status=%d sha=%s bytes=%d", r.status_code, sha[:16], len(r.content))
    print(f"captured: sha={sha} bytes={len(r.content)} -- next: ocrmypdf --force-ocr -l rus "
          f"--sidecar <out>.txt <pdf-path> <out>.pdf")


if __name__ == "__main__":
    main()
