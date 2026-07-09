#!/usr/bin/env python3
"""Capture a community-sourced post from БЮРО (Подслушано в Мариуполе,
@Mariupol_Buro) showing a photographed physical notice affixed to gates in
the Гавань and Слободка neighborhoods, asking owners to report to the
administration for inventory.

Unlike the admin-channel/TV reposts of announcement text already captured
(scripts/273/275), this is street-level photographic evidence of the notice
actually physically posted -- a distinct corroboration type (enforcement
artifact, not announcement text) for the Распоряжение №619 /
Закон ДНР №66-РЗ door-to-door inventory mechanism logged in
docs/legal_mechanisms_review.md. Not yet geolocated to a specific address --
"Гавань"/"Слободка" are neighborhood names, not a street address; if a
building/street can be read off the photo itself once captured, update this
docstring and the research doc entry accordingly.

User-supplied URL (2026-07-08). Uses the t.me/s/ + ?embed=1 stable-render
path per this project's established Telegram-capture pattern (see
memory/nakhimova82_testimony_addendum_2026-06.md).
"""
import logging
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

TARGETS = [
    (
        "https://t.me/s/Mariupol_Buro/64646?embed=1",
        "БЮРО (Подслушано в Мариуполе) @Mariupol_Buro post #64646 -- "
        "photo of a physical inventory notice posted on gates in Гавань "
        "and Слободка",
        "User-supplied URL (2026-07-08). Community-sourced photographic "
        "evidence of the Распоряжение №619 / Закон ДНР №66-РЗ door-to-door "
        "inventory notice physically posted at residential gates, asking "
        "owners to report to the administration for inventory.",
    ),
]


def fetch(url: str) -> tuple[bytes, str, int]:
    for attempt in range(config.MAX_RETRIES):
        try:
            resp = requests.get(
                url, headers={"User-Agent": config.USER_AGENT},
                timeout=config.TIMEOUT, allow_redirects=True,
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
            content, url=url, source_type="telegram_channel_post",
            title=title, description=description,
            content_type=ctype, http_status=status, con=con,
        )
        log.info("captured %s -> sha=%s status=%s (%d bytes)", title, sha[:12], status, len(content))
        time.sleep(1.0)

    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
