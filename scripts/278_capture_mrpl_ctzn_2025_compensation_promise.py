#!/usr/bin/env python3
"""Capture a "Гражданин Мариуполя" (@mrpl_ctzn) Telegram post (11.01.2025)
quoting Игорь Овсиенко, head of the Орджоникидзевский district
administration, on the presidential deadline to distribute all compensation
housing by end of 2025.

Значение: the quote explicitly ties the inventory campaign (Распоряжение
№619 et seq., docs/legal_mechanisms_review.md) to the compensation-housing
shortfall -- Овсиенко states the inventory's purpose is to determine how
many residents can be housed via bezkhoz/ownerless stock versus how much new
compensation housing must still be built. As of this capture (2026-07-08),
over 18 months past the stated 2025 deadline, the promise is unfulfilled --
see docs/dossier_center_mariupol_peredel.md (5,141-unit shortfall) and
docs/housing_queue_distribution.md (5,822 queued/1,889 distributed) for the
project's existing shortfall figures this quote directly explains.

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
        "https://t.me/s/mrpl_ctzn/15533?embed=1",
        "Гражданин Мариуполя @mrpl_ctzn post #15533 (11.01.2025) -- "
        "Овсиенко on the presidential 2025 compensation-housing deadline",
        "User-supplied URL (2026-07-08). Quotes Игорь Овсиенко (head of "
        "Орджоникидзевский district administration): the task to distribute "
        "all compensation housing in 2025 was set by the President; the "
        "ongoing housing inventory exists to determine how many residents "
        "can be housed via ownerless/bezkhoz stock versus how much new "
        "compensation housing must be built. Deadline unfulfilled as of "
        "capture date.",
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
