#!/usr/bin/env python3
"""Capture Постановление Администрации №1727 (12.11.2025) and №1740
(14.11.2025), both amendments to №1223 (05.08.2025, "Порядок инвентаризации
недвижимого имущества..." -- the post-court-transfer movable-property
inventory procedure, already captured/OCR'd/logged in
docs/legal_mechanisms_review.md).

URLs guessed from the consistent netcat_files/396/4721/p.<NNNN>.pdf pattern
already observed for other 2025-era decrees in this series (e.g. p.1223.pdf,
p.1565.pdf) -- NOT independently confirmed via a landing-page link the way
scripts/270/271 were. If either URL 404s, the guess is wrong and the actual
landing page needs to be found via the site's document listing/search first
(https://mariupol-r897.gosweb.gosuslugi.ru/ofitsialno/dokumenty/
postanovleniya-administratsii-gorodskogo-okruga-mariupol/), then the real
PDF link read off that page (same approach as scripts/270).

Same TLS trust-store situation as scripts/269-271: verification disabled
below since forensic integrity comes from the recorded SHA-256, not TLS
trust.
"""
import logging
import sys
import time
from pathlib import Path

import requests
import urllib3

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE = "https://mariupol-r897.gosweb.gosuslugi.ru"

TARGETS = [
    (
        f"{BASE}/netcat_files/396/4721/p.1727.pdf",
        "Постановление Администрации №1727 (12.11.2025) -- поправка к №1223",
        "Amendment PDF (URL guessed from the p.<NNNN>.pdf pattern -- "
        "verify status code before trusting this capture).",
    ),
    (
        f"{BASE}/netcat_files/396/4721/p.1740.pdf",
        "Постановление Администрации №1740 (14.11.2025) -- поправка к №1223",
        "Amendment PDF (URL guessed from the p.<NNNN>.pdf pattern -- "
        "verify status code before trusting this capture).",
    ),
]


def fetch(url: str) -> tuple[bytes, str, int]:
    for attempt in range(config.MAX_RETRIES):
        try:
            resp = requests.get(
                url, headers={"User-Agent": config.USER_AGENT},
                timeout=config.TIMEOUT, allow_redirects=True, verify=False,
            )
            return resp.content, resp.headers.get("Content-Type", "application/pdf"), resp.status_code
        except requests.exceptions.RequestException as exc:
            if attempt == config.MAX_RETRIES - 1:
                raise
            log.warning("transient error fetching %s (attempt %d/%d): %s -- retrying",
                        url, attempt + 1, config.MAX_RETRIES, exc)
            time.sleep(2.0 * (attempt + 1))


def main() -> None:
    con = forensics.open_state()

    for url, title, description in TARGETS:
        content, ctype, status = fetch(url)
        if status != 200:
            log.warning("SKIP (status %d, guessed URL likely wrong): %s", status, url)
            continue
        sha = forensics.capture_source(
            content, url=url, source_type="mariupol_gosuslugi_postanovlenie_pdf",
            title=title, description=description,
            content_type=ctype, http_status=status, con=con,
        )
        log.info("captured %s -> sha=%s status=%s (%d bytes)", title, sha[:12], status, len(content))
        time.sleep(1.0)

    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
