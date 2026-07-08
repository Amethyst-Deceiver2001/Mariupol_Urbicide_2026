#!/usr/bin/env python3
"""Capture the primary text of Распоряжение главы администрации г. Мариуполя
№264 (06.06.2024) "О проведении всеобщей инвентаризации муниципального
жилищного фонда" -- the citywide door-to-door housing inventory order,
so far only known through a resident collective-complaint citation
(@mrpl_besxozxata/34504, see docs/legal_mechanisms_review.md) -- plus its
amendments, both from the Mariupol municipal gosuslugi portal (user-supplied
URLs, 2026-07-08).

mariupol-r897.gosweb.gosuslugi.ru's TLS chain roots at a CA not in standard
trust stores (same class of issue as mariupol.gosuslugi.ru in scripts/269,
handled the same way below: verification disabled for this one capture,
since forensic integrity comes from the SHA-256 recorded by
forensics.capture_source(), not from TLS trust). A prior curl probe from
this machine with verification disabled still saw the connection drop mid-
handshake (SSL_ERROR_SYSCALL), which would indicate real geoblocking rather
than a trust-store gap -- but that was curl, not this exact client/library,
so it needs to be tested for real. If this script still fails after the
verify=False fix below, that confirms geoblocking and it needs to be run
from the user's Russia-routed VPS instead.
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

TARGETS = [
    (
        "https://mariupol-r897.gosweb.gosuslugi.ru/ofitsialno/dokumenty/"
        "rasporyazheniya-glavy-administratsii-goroda-mariupolya/"
        "rasporyazheniya-glavy-administratsii-goroda-mariupolya_503.html",
        "Распоряжение №264 (06.06.2024) -- всеобщая инвентаризация "
        "муниципального жилищного фонда (base act)",
        (
            "Citywide door-to-door housing-stock inventory order. Cited "
            "(not yet primary-text-captured) inside a resident collective "
            "complaint template (@mrpl_besxozxata/34504) as the instrument "
            "authorising personal-appearance-only inspections with original "
            "title documents, used to place non-appearing apartments onto "
            "the bezkhoz list. See docs/legal_mechanisms_review.md and the "
            "dispossession-pipeline-ru.html chip citing this order."
        ),
    ),
    (
        "https://mariupol-r897.gosweb.gosuslugi.ru/ofitsialno/dokumenty/"
        "rasporyazheniya-glavy-administratsii-goroda-mariupolya/"
        "rasporyazheniya-glavy-administratsii-goroda-mariupolya_515.html",
        "Amendment(s) to Распоряжение №264 (06.06.2024)",
        "Amending instrument to Распоряжение №264, user-supplied URL "
        "(2026-07-08). Number/date of the amendment itself to be read off "
        "the captured page.",
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
            return resp.content, resp.headers.get("Content-Type", "text/html"), resp.status_code
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
            content, url=url, source_type="mariupol_gosuslugi_rasporyazhenie",
            title=title, description=description,
            content_type=ctype, http_status=status, con=con,
        )
        log.info("captured %s -> sha=%s status=%s", title, sha[:12], status)
        time.sleep(1.0)

    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
