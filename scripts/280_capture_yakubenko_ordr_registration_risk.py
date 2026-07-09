#!/usr/bin/env python3
"""Capture a professional legal post by Борис Якубенко (DNR-licensed
lawyer, @yakubenko_pravo_dnr) explaining that receiving a compensation-
housing ордер (warrant) does NOT confer ownership -- title only vests upon
the recipient's own Rosreestr registration -- and warning that failure to
register creates a real risk of the unit reverting to municipal ownership.

Значение: independently corroborates the "ордер-is-not-title" finding
already documented for МКР «Невский»
(memory/nevsky_case_study_built_2026-07-04.md), from a working lawyer's own
professional advisory post citing a real client matter (an heir who cannot
obtain an inheritance certificate because the deceased compensation
recipient never registered ownership in two years). Якубенко states plainly
that non-registration risks "возврата... квартиры обратно в муниципальную
собственность" (the apartment reverting back to municipal property) --
i.e. the same Rosreestr-registration-as-precondition-for-title mechanism
that strips displaced original owners of their pre-war homes also threatens
compensation-housing recipients who don't actively register. This is the
seizure pipeline's registration trap operating symmetrically on the
"remedy" side of the process, not just the "harm" side.

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
        "https://t.me/s/yakubenko_pravo_dnr/263?embed=1",
        "ЮРИСТ | Якубенко Борис Александрович @yakubenko_pravo_dnr post "
        "#263 -- compensation-housing ордер is not title; non-registration "
        "risks reversion to municipal ownership",
        "User-supplied URL (2026-07-08). DNR-licensed lawyer's professional "
        "advisory post: ownership of compensation housing only vests upon "
        "the recipient's own Rosreestr registration, not upon receipt of "
        "the ордер; cites a real client case (heir blocked from an "
        "inheritance certificate because the deceased never registered "
        "ownership in two years) and warns non-registration risks the "
        "unit reverting to municipal property.",
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
