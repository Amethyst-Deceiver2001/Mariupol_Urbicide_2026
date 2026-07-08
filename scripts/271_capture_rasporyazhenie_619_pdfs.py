#!/usr/bin/env python3
"""Capture the actual PDF text of Распоряжение №619 (12.10.2023) and its
amendment №71 (07.02.2024), both from mariupol-r897.gosweb.gosuslugi.ru.

scripts/270 captured the landing pages, which revealed this is a DIFFERENT
instrument than the one currently cited in dispossession-pipeline-ru.html
("Распоряжение №264 от 06.06.2024" -- known only via a resident complaint's
paraphrase, still uncaptured). №619's title ("сплошная инвентаризация
объектов недвижимого имущества -- многоквартирных жилых домов и
индивидуального жилого строительства") is close in subject but not
identical in scope, number, or date to №264. Do not assume they're the same
act -- read both texts once available and reconcile.

Same TLS trust-store situation as scripts/269/270: verification disabled
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
        f"{BASE}/netcat_files/401/4727/619.pdf",
        "Распоряжение главы администрации г. Мариуполя №619 (12.10.2023) -- "
        "о проведении сплошной инвентаризации объектов недвижимого "
        "имущества (МКД и ИЖС)",
        (
            "Base act PDF, linked from the landing page captured in "
            "scripts/270 (17c241f9d42865...). Full primary text of the "
            "citywide real-estate inventory order."
        ),
    ),
    (
        f"{BASE}/netcat_files/401/4727/71.pdf",
        "Распоряжение №71 (07.02.2024) -- поправка к Распоряжению №619",
        (
            "Amendment PDF, linked from the landing page captured in "
            "scripts/270 (dff7951be1544c...). Amends Распоряжение №619 "
            "(12.10.2023)."
        ),
    ),
]


def fetch(url: str) -> tuple[bytes, str, int]:
    for attempt in range(config.MAX_RETRIES):
        try:
            resp = requests.get(
                url, headers={"User-Agent": config.USER_AGENT},
                timeout=config.TIMEOUT, allow_redirects=True, verify=False,
            )
            resp.raise_for_status()
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
        sha = forensics.capture_source(
            content, url=url, source_type="mariupol_gosuslugi_rasporyazhenie_pdf",
            title=title, description=description,
            content_type=ctype, http_status=status, con=con,
        )
        log.info("captured %s -> sha=%s status=%s (%d bytes)", title, sha[:12], status, len(content))
        time.sleep(1.0)

    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
