#!/usr/bin/env python3
"""Capture sources for the civilian-casualty record at prosp. Metallurgov, 47
(ТСЖ «Троянда-М» / Metallurgov 47 case study; user-supplied 2026-07-03).

Sources:
  1. mariupoldestruction.com's published victims spreadsheet -- "Поименный
     список жертв" (List of victims by name), a Google Sheets TSV export
     linked directly from https://www.mariupoldestruction.com. 4,515 rows
     citywide; confirmed on capture to include all 8 Metallurgov-47 rows the
     user quoted verbatim from an XLSX copy of the same underlying data.
     This is the ATTRIBUTING source for the whole record, matching the
     user's request to credit "Mariupol Destruction and Victims Map."
  2. memorial.ua obituary for Фёдорова Надежда (individual page).
  3. t.me/mariupolRIP posts 19075, 19202, 25434, 30852, 44164, 44185 -- the
     six distinct Telegram citations across the 8 named rows (19202 covers
     both Тёрин siblings; 30852 covers both Паскаль/Галушко; 19075 and
     44185 both cited for Иванов Максим).

Public/unauthenticated, non-geoblocked sources (Google Sheets TSV export,
t.me embed widget, memorial.ua) -- same precedent as scripts/159/160/161/162,
Claude runs this directly, no VPS needed.
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

TELEGRAM_POSTS = [
    (
        "https://t.me/mariupolRIP/19075",
        "mariupolRIP -- Иванов Максим Владимирович (1 of 2 posts), died пр. Металлургов 47",
        "Иванов Максим Владимирович, погиб 17.03.2022 в результате авианалета "
        "вместе с мамой Людмилой. Металлургов, 47. First of two mariupolRIP "
        "posts cited for this entry (see also /44185).",
    ),
    (
        "https://t.me/mariupolRIP/19202",
        "mariupolRIP -- Тёрин Александр Евгеньевич + Тёрина Елена Александровна, ул. Металлургов 47",
        "Тёрин Александр Евгеньевич and Тёрина Елена Александровна -- их тела "
        "нашли при разборе завалов, ул. Металлургов, 47. Single post cited "
        "for both names.",
    ),
    (
        "https://t.me/mariupolRIP/25434",
        "mariupolRIP -- Харакоз Наталья Георгиевна, Металлургов 47 (courtyard grave, later reburied)",
        "Харакоз Наталья Георгиевна (13.07.1935-29.03.2022), известная в "
        "Мариуполе писательница и журналистка. Умерла от стресса, условий, "
        "нехватки медикаментов. Похоронена в общей могиле во дворе "
        "Металлургов, 47; позднее перезахоронена на Старокрымском кладбище "
        "(сектор 17, квадрат 25, крайний ряд, могила 6) -- ее могилу смогли "
        "найти потому, что соседка перед захоронением в братской могиле "
        "положила ей в карман записку с ФИО. Also sourced from внучка "
        "(granddaughter, direct, not independently capturable here).",
    ),
    (
        "https://t.me/mariupolRIP/30852",
        "mariupolRIP -- Паскаль Мария + Галушко Андрей, married couple, Металлургов 47",
        "Паскаль Мария и Галушко Андрей, супружеская пара, погибли 24.03.2022 "
        "при обстреле, готовили во дворе. Металлургов 47 -- место гибели и "
        "захоронения совпадают. Single post cited for both names. Also "
        "sourced from соседи (neighbours, direct, not independently "
        "capturable here).",
    ),
    (
        "https://t.me/mariupolRIP/44164",
        "mariupolRIP -- Горлачова Раиса Дмитриевна, пр. Металлургов 47",
        "Горлачова Раиса Дмитриевна (07.02.1942-17.03.2022). Пр. Металлургов 47.",
    ),
    (
        "https://t.me/mariupolRIP/44185",
        "mariupolRIP -- Иванов Максим Владимирович (2 of 2 posts), died пр. Металлургов 47",
        "Second of two mariupolRIP posts cited for Иванов Максим Владимирович "
        "(see /19075 above).",
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

    # 1. mariupoldestruction.com victims spreadsheet (TSV export)
    sheet_url = (
        "https://docs.google.com/spreadsheets/d/e/"
        "2PACX-1vRClYf-zQAtTququ0nEPfQBMO6EHaTSltS-d5caPXVbjc0fElqGuDKyr9P1gBCByw/"
        "pub?output=tsv"
    )
    content, ctype, status = fetch(sheet_url)
    sha_sheet = forensics.capture_source(
        content, url=sheet_url, source_type="mariupoldestruction_victims_tsv",
        title="mariupoldestruction.com -- «Поименный список жертв» "
              "(List of victims by name), Google Sheets TSV export",
        description=(
            "Citywide victims spreadsheet published by mariupoldestruction.com "
            "(\"Mariupol Destruction and Victims Map\", "
            "https://www.mariupoldestruction.com), linked from the site's "
            "\"Victims\" section. 4,515 rows as captured. Confirmed on "
            "capture (grep) to include all 8 rows for prosp. Metallurgov, 47 "
            "quoted by the user 2026-07-03 from an XLSX copy of the same "
            "underlying data: Фёдорова Надежда, Харакоз Наталья Георгиевна, "
            "Тёрин Александр Евгеньевич, Тёрина Елена Александровна, "
            "Иванов Максим Владимирович, Паскаль Мария, Галушко Андрей, "
            "Горлачова Раиса Дмитриевна. This is the attributing source for "
            "the whole casualty record."
        ),
        content_type=ctype, http_status=status, con=con,
    )
    log.info("captured mariupoldestruction.com victims TSV -> sha=%s status=%s", sha_sheet[:12], status)
    time.sleep(REQUEST_PAUSE_S)

    # 2. memorial.ua -- Фёдорова Надежда
    memorial_url = "https://memorial.ua/obituaries/civilians/kfedorova-nadiia-12510"
    content, ctype, status = fetch(memorial_url)
    sha_memorial = forensics.capture_source(
        content, url=memorial_url, source_type="memorial_ua_obituary",
        title="memorial.ua -- Фёдорова Надежда (b. 04.10.1938, killed 01-03.03.2022, пр. Металлургов 47)",
        description=(
            "Individual obituary page. Killed by shelling: windows blown "
            "out, injured by glass shards, heart stopped. Buried next to "
            "the building, wrapped in a carpet/rug -- «похоронили "
            "возле дома, в ковре. Перезахоронение неизвестно» "
            "(reburial status unknown), per the same row in the "
            "mariupoldestruction.com spreadsheet above."
        ),
        content_type=ctype, http_status=status, con=con,
    )
    log.info("captured memorial.ua obituary -> sha=%s status=%s", sha_memorial[:12], status)
    time.sleep(REQUEST_PAUSE_S)

    # 3. Telegram posts
    shas = {}
    for url, title, description in TELEGRAM_POSTS:
        content, ctype, status = fetch(f"{url}?embed=1")
        sha = forensics.capture_source(
            content, url=url, source_type="telegram_post",
            title=title, description=description,
            content_type=ctype, http_status=status, con=con,
        )
        shas[url] = sha
        log.info("captured %s -> sha=%s status=%s", url, sha[:12], status)
        time.sleep(REQUEST_PAUSE_S)

    con.close()

    log.info("=== SHA-256 SUMMARY (paste into scripts/240_load_metallurgov47_casualty_record.py) ===")
    log.info("SHA_MARIUPOLDESTRUCTION_TSV = %r", sha_sheet)
    log.info("SHA_MEMORIAL_UA = %r", sha_memorial)
    for url, sha in shas.items():
        log.info("%s -> %r", url, sha)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
