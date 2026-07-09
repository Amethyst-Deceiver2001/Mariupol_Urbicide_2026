#!/usr/bin/env python3
"""Capture the Орджоникидзевский-район administration public notice (posted
2026-07-08, user-supplied text) scheduling door-to-door inventory for
29-30.05.2024 at eight named addresses, and its republish on the official
Мариуполь 24 TV Telegram channel.

Fourth corroborating source for the Распоряжение №619 personal-appearance/
title-document mechanism, logged in docs/legal_mechanisms_review.md
(2026-07-08). Uses the t.me/s/ embed-friendly path per this project's
established WebFetch-unreliability workaround for Telegram (see
memory/nakhimova82_testimony_addendum_2026-06.md): the raw t.me/<channel>/<id>
URL renders JS-heavy previews that summarizer tools mangle; /s/ + ?embed=1
returns a stable server-rendered HTML snapshot instead.
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
        "https://t.me/s/mariupol24tv/62295?embed=1",
        "Мариуполь 24 TV Telegram post #62295 -- republish of Орджоникидзевский "
        "district administration inventory notice (29-30.05.2024)",
        "User-supplied URL (2026-07-08). Republishes the district administration's "
        "door-to-door inventory schedule citing Закон ДНР №66-РЗ (21.03.2024) as "
        "legal basis; corroborates Распоряжение №619's personal-appearance/"
        "title-document mechanism seven months into its run.",
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
