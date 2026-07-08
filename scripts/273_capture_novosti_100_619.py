#!/usr/bin/env python3
"""Capture the Mariupol gosuslugi news article confirming Распоряжение №619
(12.10.2023) as *the* operative citywide housing-inventory instrument
(user-supplied URL, 2026-07-08) -- context for the entry already logged in
docs/legal_mechanisms_review.md (captured via scripts/270/271).

Same TLS situation as scripts/269 (mariupol.gosuslugi.ru): a prior curl
probe failed with SSL_ERROR_SYSCALL even with verification disabled, but
Python's requests library succeeded for this exact domain in scripts/269 --
worth testing for real here rather than assuming a hard block from curl's
failure alone.
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

URL = "https://mariupol.gosuslugi.ru/dlya-zhiteley/novosti-i-reportazhi/novosti_100.html"


def fetch(url: str) -> tuple[bytes, str, int]:
    for attempt in range(config.MAX_RETRIES):
        try:
            resp = requests.get(
                url, headers={"User-Agent": config.USER_AGENT},
                timeout=config.TIMEOUT, allow_redirects=True, verify=False,
            )
            resp.raise_for_status()
            return resp.content, resp.headers.get("Content-Type", "text/html"), resp.status_code
        except requests.exceptions.RequestException as exc:
            if attempt == config.MAX_RETRIES - 1:
                raise
            log.warning("transient error fetching %s (attempt %d/%d): %s -- retrying",
                        url, attempt + 1, config.MAX_RETRIES, exc)
            time.sleep(2.0 * (attempt + 1))


def main() -> None:
    con = forensics.open_state()

    content, ctype, status = fetch(URL)
    sha = forensics.capture_source(
        content, url=URL, source_type="mariupol_gosuslugi_news",
        title="mariupol.gosuslugi.ru novosti_100 -- news article confirming "
              "Распоряжение №619 as the operative housing-inventory instrument",
        description=(
            "User-supplied (2026-07-08), confirming Распоряжение №619 "
            "(12.10.2023) is the real/operative citywide inventory act, "
            "context for the entry in docs/legal_mechanisms_review.md."
        ),
        content_type=ctype, http_status=status, con=con,
    )
    log.info("captured novosti_100 -> sha=%s status=%s", sha[:12], status)

    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
