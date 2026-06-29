#!/usr/bin/env python3
"""Capture the journalism/reference sources cited in Case Study III
(docs/exhibits/case-study-III-stroiteley.html / -ru.html) into the forensic
raw store, so the source-catalogue hyperlinks being added to both exhibit
pages are backed by a SHA-256 + UTC chain-of-custody record, not just a
live link to someone else's server.

URLs supplied directly by the user (2026-06-30) except the mariupolRIP
channel root, already on file as a known project source (docs/exhibits/
sources.html). None of these are geoblocked Russian-state portals -- all
ordinary public journalism/reference sites -- confirmed via direct probe,
so this script is run directly rather than handed to the user.

Two sources cited in the case study are deliberately NOT captured here:
- LLC "SZ-1 Porfir" corporate record (INN 9310009271 / OGRN 1239300008870):
  no working rusprofile/checko/EGRUL URL found (rusprofile search returned
  HTTP 404 from this environment) -- not linked in the exhibit pending a
  verified URL.
- Court case 33-2575/2025 (cited for Directive No. 56): lives on the
  geoblocked vs--dnr.sudrf.ru portal: needs the user's own VPS crawl
  (see src/mariupol_seizures/crawl/dnr_supreme_court.py), not fetched here.

Run:
    PYTHONPATH=src python scripts/222_fetch_stroiteley_iii_sources.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import requests  # noqa: E402
import urllib3  # noqa: E402

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

if not config.SSL_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SOURCES = [
    {
        "url": "https://meduza.io/feature/2022/06/10/kazhdyy-den-prosypaeshsya-i-ty-kto-to-novyy-segodnya-ty-mogilschik",
        "source_type": "meduza_gravedigger_feature",
        "title": "Meduza, «Каждый день просыпаешься, и ты — кто-то новый. Сегодня ты — могильщик» (10.06.2022)",
        "description": "Independent Russian-language journalism, gravedigger eyewitness cross-section of Mariupol streets including Stroiteley Avenue, cited in Case Study III.",
    },
    {
        "url": "https://apnews.com/article/russia-ukraine-war-erasing-mariupol-499dceae43ed77f2ebfe750ea99b9ad9",
        "source_type": "ap_erasing_mariupol_feature",
        "title": "AP Special Projects, \"Russia scrubs Mariupol's Ukraine identity, builds on death\" (Dec 2022)",
        "description": "AP investigation on demolition/reconstruction over courtyard graves, cited in Case Study III.",
    },
    {
        "url": "https://www.hrw.org/feature/russia-ukraine-war-mariupol/counting-the-dead",
        "source_type": "hrw_counting_the_dead",
        "title": "Human Rights Watch, \"Counting the Dead: Documenting Loss in Mariupol\" (2024)",
        "description": "HRW forensic feature on Mariupol death toll and burial-site documentation, cited in Case Study III.",
    },
    {
        "url": "https://uk.wikipedia.org/wiki/%D0%9F%D1%80%D0%BE%D1%81%D0%BF%D0%B5%D0%BA%D1%82_%D0%91%D1%83%D0%B4%D1%96%D0%B2%D0%B5%D0%BB%D1%8C%D0%BD%D0%B8%D0%BA%D1%96%D0%B2_(%D0%9C%D0%B0%D1%80%D1%96%D1%83%D0%BF%D0%BE%D0%BB%D1%8C)",
        "source_type": "ukwiki_budivelnykiv_avenue",
        "title": "Ukrainian Wikipedia, Проспект Будівельників (Маріуполь) -- street history",
        "description": "Context source for the avenue's Soviet-era construction history, cited in Case Study III.",
    },
    {
        "url": "https://novayagazeta.eu/articles/2024/02/22/dostupnoe-zakhvachennoe-zhile",
        "source_type": "novaya_europe_compensation_piece",
        "title": "Novaya Gazeta Europe, «Доступное захваченное жильё» (22.02.2024)",
        "description": "Independent Russian-language reporting on a Mariupol resident's denied compensation claim, cited in Case Study III.",
    },
    {
        "url": "https://t.me/mariupolRIP",
        "source_type": "mariupolrip_channel_root",
        "title": "t.me/mariupolRIP -- pre-war/post-war memorial comparison channel (root)",
        "description": "The civilian Telegram documentation channel cited generically in Case Study III for the five Stroiteley courtyard burial records; already listed as a project source in docs/exhibits/sources.html. No message-level link specific to the five Stroiteley addresses has been pinned down -- this captures the channel root only.",
    },
]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    con = forensics.open_state()
    s = requests.Session()
    s.headers.update({"User-Agent": config.USER_AGENT, "Accept-Language": "ru,uk,en;q=0.8"})
    if config.PROXY:
        s.proxies.update({"http": config.PROXY, "https": config.PROXY})

    for src in SOURCES:
        url = src["url"]
        log.info("Fetching %s", url)
        try:
            r = s.get(url, timeout=config.TIMEOUT, verify=config.SSL_VERIFY, allow_redirects=True)
        except requests.RequestException as exc:
            log.error("FAILED %s: %s", url, exc)
            continue
        if r.status_code != 200:
            log.warning("HTTP %d for %s -- captured anyway for the record", r.status_code, url)
        sha = forensics.capture_source(
            r.content, url=url, source_type=src["source_type"],
            title=src["title"], description=src["description"],
            content_type=r.headers.get("Content-Type", "text/html"),
            http_status=r.status_code, con=con,
        )
        log.info("status=%d sha=%s bytes=%d -- %s", r.status_code, sha[:16], len(r.content), src["source_type"])
        print(f"{src['source_type']}: status={r.status_code} sha={sha[:16]} bytes={len(r.content)}")


if __name__ == "__main__":
    main()
