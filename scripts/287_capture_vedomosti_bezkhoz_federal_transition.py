#!/usr/bin/env python3
"""Capture Vedomosti's report on the federal-law transition moving "ownerless"
housing in the newly annexed regions into state ownership.

Linked by @ssaniaworld/3341 (21.10.2025) alongside a claim that Mariupol
authorities have earmarked at least 5,700 real-estate objects for bezkhoz
seizure, and that FSB "filtration" screening is the practical barrier
preventing owners in Ukrainian-controlled territory or Europe from
personally appearing to save their property (the DNR Law No. 66 st.2
criteria vs. the incoming federal-law art. 225 GK RF "no known owner"
standard). Independent (non-Telegram) secondary-media corroboration of the
scale and legal-transition claims already logged from the Telegram sweep.

Usage:
    .venv312/bin/python scripts/287_capture_vedomosti_bezkhoz_federal_transition.py
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

URL = (
    "https://www.vedomosti.ru/society/articles/2025/10/21/"
    "1148414-beshozyainoe-zhile-v-novih-regionah-pereidet-v-gosudarstvennuyu-sobstvennost"
)
TITLE = (
    "Vedomosti -- \"Бесхозяйное жильё в новых регионах перейдёт в "
    "государственную собственность\" (21.10.2025)"
)
DESCRIPTION = (
    "Report on a pending federal-law change to the bezkhoz-housing "
    "designation standard in DNR/LNR/Zaporizhzhia/Kherson, moving it from "
    "DNR Law No. 66 st.2's broader local criteria (unpaid utilities, unsafe "
    "unit, owner self-removal) to Russian Civil Code art. 225's narrower "
    "\"no known owner\" standard. Linked by @ssaniaworld/3341 alongside a "
    "claim that Mariupol authorities have earmarked at least 5,700 "
    "real-estate objects for bezkhoz designation."
)


def fetch(url: str) -> tuple[bytes, str, int]:
    for attempt in range(config.MAX_RETRIES):
        try:
            resp = requests.get(
                url,
                headers={"User-Agent": config.USER_AGENT},
                timeout=config.TIMEOUT,
                allow_redirects=True,
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
        content, url=URL, source_type="independent_media_investigation",
        title=TITLE, description=DESCRIPTION,
        content_type=ctype, http_status=status, con=con,
    )
    log.info("captured %s -> sha=%s status=%s (%d bytes)", TITLE, sha[:12], status, len(content))
    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
