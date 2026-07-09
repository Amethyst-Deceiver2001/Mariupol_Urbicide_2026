#!/usr/bin/env python3
"""Capture an ASTRA (independent Russian investigative outlet,
@astrapress) report (15.03.2025) on homeless Mariupol residents from
проспект Победы 55/61 who recorded another video appeal to Putin holding
"БОМЖИ" (homeless) signs, in their third year waiting for promised housing.

Значение: ASTRA reports the residents' own figures -- of 362 demolished
buildings in Mariupol, only 71 have been rebuilt, leaving an approximately
18,000-apartment shortfall -- and quotes residents directly: "Власти «ДНР»
решили просто отнимать квартиры у живых собственников и называть их
бесхозными" (DNR authorities decided to simply take apartments from living
owners and call them ownerless) -- a self-incriminating characterization of
the exact bezkhoz mechanism this project documents, from the residents'
video appeal itself, reported by an independent outlet. The appeal lists
five specific unresolved compensation failures: (1) no equivalent
compensation housing in the same district as the lost home; (2) share-
ownership (доля) holders excluded because their share doesn't match new
unit sizes; (3) people with positive housing decisions who died waiting,
leaving families homeless; (4) families whose housing was registered to
now-deceased parents with no prospect of recovery; (5) unresolved status
for never-privatized housing. ASTRA also references its own earlier
(19.06.2024) investigation into mortgage construction on the seized land
of demolished buildings' historic-center lots.

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
        "https://t.me/s/astrapress/76631?embed=1",
        "ASTRA @astrapress post #76631 (15.03.2025) -- Mariupol residents' "
        "\"БОМЖИ\" video appeal to Putin: 362 demolished / 71 rebuilt, "
        "~18,000-apartment shortfall",
        "User-supplied URL (2026-07-08). Reports residents of пр. Победы "
        "55/61 recorded a video appeal to Putin holding homeless signs, "
        "third year waiting; quotes them: DNR authorities \"decided to "
        "simply take apartments from living owners and call them "
        "ownerless\". Lists five unresolved compensation-housing failures. "
        "References ASTRA's own 19.06.2024 investigation into mortgage "
        "construction on the seized land of demolished buildings.",
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
