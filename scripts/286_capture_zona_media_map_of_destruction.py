#!/usr/bin/env python3
"""Capture "Map of Destruction. How Occupied Mariupol Is Being Demolished and
Rebuilt" (Zona.Media, Alla Konstantinova, 29.01.2024).

Independent Russian-language investigative feature covering the same
lifecycle this project tracks (mobile-housing-fund decree, October 2023
inventory, bezkhoz/ownerless listings, demolition, RKS-Development resale)
via first-person resident testimony (Oksana, Aleksandr Borman) and named
construction-sector sources (Mikhail, "TekhnStroy" manager Ivan Orynchuk --
later arrested for embezzlement) not found in any occupation-official channel
already in this project's archive. Independent corroboration of the
demolition count (321/407 as of March 2023) and the RKS-Development resale
pricing (~150,000 RUB/m^2), both previously sourced only from
occupation-aligned channels/developer sites.

Usage:
    .venv312/bin/python scripts/286_capture_zona_media_map_of_destruction.py
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

URL = "https://zona.media/article/2024/01/29/mariupol"
TITLE = ("Zona.Media -- \"Карта разрушений. Как оккупированный Мариуполь "
         "сносят и отстраивают заново\" (Alla Konstantinova, 29.01.2024)")
DESCRIPTION = (
    "Independent Russian-language investigative feature: mobile-housing-fund "
    "decree (Oct 2022, 30-day documentation deadline), Oct 2023 inventory "
    "procedure, bezkhoz listings, demolition (321/407 houses as of Mar 2023, "
    "1,829 objects needing repair), RKS-Development resale pricing "
    "(~150,000 RUB/m^2, Дом с часами), first-person resident testimony "
    "(Oksana -- denied re-entry via Ivangorod citing \"undesirable contact\"; "
    "Aleksandr Borman, orphan-queue beneficiary denied reinstatement), "
    "construction-labor conditions (Mikhail, Novosibirsk migrant worker), "
    "and the Ivan Orynchuk (TekhnStroy) award-then-arrest episode."
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
