#!/usr/bin/env python3
"""Capture the SIGNED PDFs for the three federal Постановления identified by
scripts/207 -- that script's pravo.gov.ru fetches only captured the JS-
rendered document-index SHELL (confirmed by inspection: the HTML is an
Angular/React SPA wrapper, no document text, just a title + metadata).

Discovery: each shell page embeds a real download link of the form

    /file/pdf?eoNumber=<eoNumber>

where <eoNumber> is the same publication id used in the View URL (e.g.
eoNumber=0001202301030011 for №2565). Found by grepping the captured shell
HTML for "eoNumber=" -- `href="/file/pdf?eoNumber=...""`. This resolves the
"full text needs the PDF download link, not yet chased" gap noted in
scripts/197's docstring for №2166, and the same gap for №2565/№2501/№2255
here.

Page counts confirmed via pdfinfo before committing to OCR: №2565 = 46pp,
№2501 = 17pp, №2255 = 67pp (a full госпрограмма with multiple appendices --
Приложение №4, the per-m² compensation annex this capture exists to read,
is somewhere inside).

Run:
    PYTHONPATH=src python scripts/208_fetch_federal_decree_pdfs.py
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
        "eo_number": "0001202301030011",
        "source_type": "federal_mortgage_decree_2565_pdf",
        "title": "Постановление Правительства РФ от 31.12.2022 № 2565 -- signed PDF (46pp)",
        "description": "Full signed text of the 2% mortgage founding decree (Q1).",
    },
    {
        "eo_number": "0001202212300029",
        "source_type": "federal_property_demarcation_2501_pdf",
        "title": "Постановление Правительства РФ от 29.12.2022 № 2501 -- signed PDF (17pp)",
        "description": "Full signed text of the property-demarcation framework (Q2).",
    },
    {
        "eo_number": "0001202312290053",
        "source_type": "federal_reconstruction_program_2255_pdf",
        "title": "Постановление Правительства РФ от 22.12.2023 № 2255 -- signed PDF (67pp, госпрограмма + annexes)",
        "description": (
            "Full signed text of the reconstruction госпрограмма, INCLUDING "
            "Приложение №4 -- the per-m² compensation annex (Q3). Priority "
            "read after OCR: confirm or correct the 51,500 ₽/m² figure "
            "deduced (not read) from an amendment draft by the first "
            "research batch."
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
        url = f"http://publication.pravo.gov.ru/file/pdf?eoNumber={t['eo_number']}"
        log.info("Fetching %s", url)
        try:
            r = s.get(url, timeout=config.TIMEOUT, verify=config.SSL_VERIFY, allow_redirects=True)
        except requests.RequestException as e:
            log.error("  FAILED: %s -- if this is a connection/TLS error, retry from the VPS", e)
            continue

        if r.status_code != 200:
            log.warning("  HTTP %d for %s -- captured anyway for the record", r.status_code, url)

        sha = forensics.capture_source(
            r.content, url=url, source_type=t["source_type"],
            title=t["title"], description=t["description"],
            content_type=r.headers.get("Content-Type", "application/pdf"),
            http_status=r.status_code, con=con,
        )
        log.info("  status=%d sha=%s bytes=%d", r.status_code, sha[:16], len(r.content))

    log.info("Done. Next: OCR each PDF (ocrmypdf --force-ocr -l rus, .venv not "
              ".venv312) then grep the №2255 text for 'приложение' / 'N 4' / "
              "'приложение 4' to locate and read the per-m2 annex.")


if __name__ == "__main__":
    main()
