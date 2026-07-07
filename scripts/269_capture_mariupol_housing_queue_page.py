#!/usr/bin/env python3
"""Capture the Mariupol occupation "housing queue" (жилищная очередь) explainer
page (user-supplied 2026-07-07): the published terms for compensational-housing
distribution to residents of demolished multi-apartment buildings, including
Nakhimova 82.

Cited in the Nakhimova 82 exhibit's "arithmetic of dispossession" section for
two claims: (1) the published terms name no right to choose which district the
replacement housing is allocated in, so district assignment functions as
effectively arbitrary; (2) eligibility for compensation is itself conditioned
on Russian citizenship.

mariupol.gosuslugi.ru is geoblocked from outside Russia (consistent with other
*.gosuslugi.ru captures in this project, e.g. minstroy-dpr.gosuslugi.ru in
docs/sources.md) -- this script must be run from the user's Russia-routed VPS,
per CLAUDE.md ("Claude never executes the crawler").
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

URL = "https://mariupol.gosuslugi.ru/dlya-zhiteley/poleznye-materialy/kvartirnaya-ochered/"


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

    content, ctype, status = fetch(URL)
    sha = forensics.capture_source(
        content, url=URL, source_type="gosuslugi_housing_queue_page",
        title="mariupol.gosuslugi.ru -- housing-queue (kvartirnaya ochered) explainer",
        description=(
            "Official occupation-administration explainer of the "
            "compensational-housing queue terms for residents of demolished "
            "multi-apartment buildings. Cited in the Nakhimova 82 exhibit's "
            "arithmetic section: the page states no right to choose a "
            "district for replacement housing, and conditions compensation "
            "eligibility on Russian citizenship."
        ),
        content_type=ctype, http_status=status, con=con,
    )
    log.info("captured mariupol.gosuslugi.ru housing-queue page -> sha=%s status=%s",
             sha[:12], status)

    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
