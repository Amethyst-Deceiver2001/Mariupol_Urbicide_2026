#!/usr/bin/env python3
"""Capture 6 text-only mariupolRIP posts identified 2026-07-21 while
following up on a pattern the user flagged: captionless photo albums are
often followed immediately by a separate text post narrating the same
grave (address, names, circumstances) -- e.g. msg 24395 (5 caption-less
grave photos) is explained by msg 24401 ("Мира 42, возле памятника
Шевченко..."). Checking the message immediately after each album already
loaded by scripts/405 surfaced:
  - 15685: confirms Демченко address ("ул. Арх Нильсона 73")
  - 17772: confirms Галстян's address (бульвар Шевченко, 64а)
  - 24401: precisely locates the 5-grave cluster (Мира 42, у памятника Шевченко)
  - 56251: confirms Данилова's patronymic (Ломизова 1 group)
  - 18683: a NEW, unrelated lead -- Солнцев Алексей Леонидович, Бульвар Морской 20а
  - 33110: a NEW, unrelated lead -- Пухова Нина Александровна, проспект Победы 75 кв.53

Public, unauthenticated t.me embed widget -- same precedent as
scripts/239/397/400/401. These are individually identified single posts
(not a systematic crawl), so captured directly.
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

REQUEST_PAUSE_S = 1.0

POSTS = [
    ("https://t.me/mariupolRIP/15685", "confirms Демченко address (ул. Арх Нильсона 73)"),
    ("https://t.me/mariupolRIP/17772", "confirms Галстян address (бульвар Шевченко, 64а)"),
    ("https://t.me/mariupolRIP/24401", "locates 5-grave cluster (Мира 42, у памятника Шевченко)"),
    ("https://t.me/mariupolRIP/56251", "confirms Данилова patronymic (Ломизова 1 group)"),
    ("https://t.me/mariupolRIP/18683", "NEW lead: Солнцев Алексей Леонидович, Бульвар Морской 20а"),
    ("https://t.me/mariupolRIP/33110", "NEW lead: Пухова Нина Александровна, проспект Победы 75 кв.53"),
    ("https://t.me/mariupolRIP/33106", "confirms Маринец landmark (возле левобережного РОВД)"),
    ("https://t.me/mariupolRIP/20086", "NEW lead: Бухтоярова Ольга Яковлевна, бул. Меотиды 4"),
    ("https://t.me/mariupolRIP/18679", "NEW lead: Рудаков Николай, старое кладбище Новоселовки"),
    ("https://t.me/mariupolRIP/21705", "NEW lead: Зименко Николай + Зименко Нина Андреевна, Московская 15 кв.20"),
]


def fetch(url: str) -> tuple[bytes, str, int]:
    for attempt in range(config.MAX_RETRIES):
        try:
            resp = requests.get(
                url, headers={"User-Agent": config.USER_AGENT},
                timeout=config.TIMEOUT, allow_redirects=True,
            )
            resp.raise_for_status()
            return resp.content, resp.headers.get("Content-Type", "application/octet-stream"), resp.status_code
        except requests.exceptions.RequestException as exc:
            if attempt == config.MAX_RETRIES - 1:
                raise
            log.warning("transient error fetching %s (attempt %d/%d): %s -- retrying",
                        url, attempt + 1, config.MAX_RETRIES, exc)
            time.sleep(2.0 * (attempt + 1))


def main() -> None:
    con = forensics.open_state()
    shas = []
    for url, desc in POSTS:
        content, ctype, status = fetch(f"{url}?embed=1")
        sha = forensics.capture_source(
            content, url=url, source_type="telegram_post",
            title=f"mariupolRIP narrative follow-up -- {desc}",
            description=(f"Text-only post immediately following a "
                          f"caption-less grave-photo album, {desc}. "
                          f"Found 2026-07-21 following up on a "
                          f"user-identified recurring pattern."),
            content_type=ctype, http_status=status, con=con,
        )
        shas.append(sha)
        log.info("captured -> sha=%s status=%s (%s)", sha[:12], status, desc)
        time.sleep(REQUEST_PAUSE_S)

    con.close()
    log.info("=== SHA-256 SUMMARY ===")
    for sha, (url, desc) in zip(shas, POSTS):
        log.info("%r  # %s -- %s", sha, url, desc)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
