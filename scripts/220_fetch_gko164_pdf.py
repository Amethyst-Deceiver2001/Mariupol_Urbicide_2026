#!/usr/bin/env python3
"""Capture Постановление ГКО ДНР №164 -- the "1-year temporary use" predecessor
stage referenced inside GKO №300's own body text (see legal_mechanisms_review.md's
№300 row). URL supplied directly by the user (2026-06-29):

    https://glavadnr.ru/doc/GKO/post/Post_GKO_164.pdf

Same domain/path pattern as №263 and №300 (both already captured from
glavadnr.ru) -- not geoblocked, fetchable directly (confirmed via a prior
WebFetch probe: HTTP 200, ~740KB scanned-image PDF, 1275x1752px).

This closes the primary-text half of Q7 in
docs/research_outsourcing/OPEN_QUESTIONS_2026-06-29.md. After capture, OCR
with the project's standard pipeline (ocrmypdf --force-ocr -l rus, .venv not
.venv312) and read the text to confirm/refute the "1-year temporary use"
characterization and check for any named addresses (the actual point of Q7).

Run:
    PYTHONPATH=src python scripts/220_fetch_gko164_pdf.py
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

URL = "https://glavadnr.ru/doc/GKO/post/Post_GKO_164.pdf"


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
        r.content, url=URL, source_type="gko_164_pdf",
        title="Постановление ГКО ДНР №164 -- PDF (user-supplied URL, 2026-06-29)",
        description=(
            "Q7 follow-up. Referenced inside GKO No.300's own body text as the "
            "1-year 'temporary use' predecessor stage. URL supplied directly by "
            "the user, same glavadnr.ru/doc/GKO/post/ pattern as No.263/No.300."
        ),
        content_type=r.headers.get("Content-Type", "application/pdf"),
        http_status=r.status_code, con=con,
    )
    log.info("status=%d sha=%s bytes=%d", r.status_code, sha[:16], len(r.content))
    print(f"captured: sha={sha} bytes={len(r.content)} -- next: ocrmypdf --force-ocr -l rus "
          f"--sidecar <out>.txt <pdf-path> <out>.pdf (find path via the sha in data/raw/)")


if __name__ == "__main__":
    main()
