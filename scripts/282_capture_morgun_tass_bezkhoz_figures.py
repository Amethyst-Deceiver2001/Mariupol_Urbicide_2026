#!/usr/bin/env python3
"""Capture two TASS-sourced statements by Олег Моргун (acting head of the
Mariupol city administration) with official bezkhoz-registry figures,
republished on two Telegram channels (user-supplied, 2026-07-08).

Post 1 (@novosti_mariupol1/25839, 04.04.2025) -- Moргун, speaking at the
"Интеграция-2025" forum in Rostov-on-Don: municipally-owned bezkhoz units
will grow 5.5x to ~750 objects; currently only 142 units (~2%) are formally
municipal property, but 600 court decisions have already entered into
force. Quote: "На каждой стадии инвентаризации - от момента расклейки
объявления, до вступления в силу решения суда, собственник если
обращается, мы снимаем с жилье с реестра" (at every stage of the
inventory -- from posting the notice to the court decision taking effect --
if the owner comes forward, we remove the unit from the registry) -- an
official admission that the opt-out exists in principle at every stage, to
be read against how burdensome that opt-out is in practice (documents,
personal appearance, cold/heat queues -- see the №619/№1223 entries in
docs/legal_mechanisms_review.md).

Post 2 (@mariupol24tv/91856, 20.05.2025) -- Moргун: ~3,800 bezkhoz
apartments/houses recorded citywide (~3,000 registered in ЕГРН as
bezkhoz, ~800 confirmed via court, out of ~1,000 court petitions filed --
courts denied ~200 when the owner or a representative appeared with
documents). States the legal basis is DNR Law №66-РЗ (already tracked,
docs/legal_mechanisms_review.md, tied to the Орджоникидзевский-district
enforcement notice logged 2026-07-08). Gives an official rationale:
"antiterror" (unsupervised empty housing in high-rises) plus municipal
utility obligations (heating/water system access ahead of the
autumn-winter season). References Putin's 04.02.2025 directive to house
Mariupol residents whose homes cannot be restored, and states that of
10,400+ residents who joined the compensation-housing queue since 2022,
5,600+ remain queued -- to be housed via new construction AND bezkhoz
apartments (explicit official confirmation of the compensation-via-bezkhoz
mechanism already flagged via the Овсиенко quote, @mrpl_ctzn/15533).

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
        "https://t.me/s/novosti_mariupol1/25839?embed=1",
        "Мой Мариуполь @novosti_mariupol1 post #25839 (04.04.2025) -- "
        "Моргун/TASS: municipal bezkhoz units to grow 5.5x to ~750; 142 "
        "current, 600 court decisions in force",
        "User-supplied URL (2026-07-08). TASS-sourced quote from Мариуполь "
        "acting head Олег Моргун at the \"Интеграция-2025\" forum "
        "(Rostov-on-Don): bezkhoz units transferred to municipal ownership "
        "will grow 5.5x to ~750; currently 142 (~2%), but 600 court "
        "decisions already in force. States owners can have a unit removed "
        "from the registry at any inventory stage if they come forward.",
    ),
    (
        "https://t.me/s/mariupol24tv/91856?embed=1",
        "МАРИУПОЛЬ 24 @mariupol24tv post #91856 (20.05.2025) -- "
        "Моргун/TASS: ~3,800 bezkhoz units citywide, legal basis "
        "Закон ДНР №66-РЗ, 10,400+ queued for compensation housing since "
        "2022, 5,600+ still queued",
        "User-supplied URL (2026-07-08). TASS-sourced statement from "
        "Моргун: ~3,800 bezkhoz apartments/houses recorded citywide "
        "(~3,000 in ЕГРН, ~800 court-confirmed of ~1,000 petitions, ~200 "
        "denied when the owner appeared with documents). Cites Закон ДНР "
        "№66-РЗ as legal basis; gives antiterror + utility-access "
        "rationale. References Putin's 04.02.2025 housing directive and "
        "states 10,400+ residents queued for compensation housing since "
        "2022, 5,600+ still queued, to be housed via new construction and "
        "bezkhoz apartments.",
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
