#!/usr/bin/env python3
"""Capture a "Черный Список | Мариуполь" (@BLMariupol) Telegram post
(user-supplied, 2026-07-08) reporting that проспект/улица Зелинского, 13 --
a building residents fought to save from demolition and got restored -- has
had nearly all of its 74 still-uninhabitable apartments placed into bezkhoz
status, despite residents already having gone through a February 2024
document-verification commission (waiting hours in freezing cold) and a
subsequent kilometer-long queue to file restoration paperwork in summer heat.

Значение: this is the same restoration-without-restitution modality already
documented for пр. Ленина 104/106/108/110
(docs/case_studies/lenina_104_106_108_110_restoration_without_restitution.md)
-- a second building where the sequence is demolition-threat -> resident
campaign -> restoration granted -> ownership stripped via the ownerless
registry anyway, with residents made to repeatedly personally appear with
documents (matching the №619/№1223 inventory-commission mechanism already
logged in docs/legal_mechanisms_review.md) only to still lose their units to
bezkhoz designation. Worth a building-ID cross-check against the property
spine and a look at whether this qualifies as a second case-study candidate
alongside Ленина 106.

Note: memory/usi_mariupol_site_crawl_2026-06.md already flagged Зелинского
23 (different house number, same street) as a separate demolish-rebuild
finding (confidence 0.9, ЮгСтройИнвест) -- do not conflate the two addresses.

Uses the t.me/s/ + ?embed=1 stable-render path per this project's
established Telegram-capture pattern (see
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
        "https://t.me/s/BLMariupol/19588?embed=1",
        "Черный Список | Мариуполь @BLMariupol post #19588 -- Зелинского 13, "
        "74 restored-but-uninhabitable apartments placed into bezkhoz",
        "User-supplied URL (2026-07-08). Reports the building was saved "
        "from demolition by resident campaign and restored, but 74 "
        "apartments remain uninhabitable; nearly all were placed into "
        "bezkhoz status despite residents already appearing before a "
        "February 2024 document-verification commission and a subsequent "
        "kilometer-long registration queue. Second candidate for the "
        "restoration-without-restitution modality alongside Ленина 106.",
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
