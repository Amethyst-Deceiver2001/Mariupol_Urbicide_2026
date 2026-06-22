#!/usr/bin/env python3
"""Capture sources for a mass-casualty record tied to the пр. Ленина(Мира)
104/106/108/110 case study (user-supplied 2026-06-19).

Per the user's choice (asked directly given how many building-attribution
mistakes this case study has already caught and fixed): record this as a
SHARED finding across all four buildings, not pinned to one -- the 6 named
deceased are documented under "Мира, 110" (the document title and most
individual entries), the makeshift grave the user found is in 106's
courtyard, and a separate not-yet-verified video shows bodies wrapped in
blankets in 108's courtyard.

Sources:
  1. t.me/mariupolRIP/36979 -- Глушко Анатолий Петрович (1937-2022), died in
     a basement from a blast head injury, body could not be buried due to
     shelling, пр-т Мира 110.
  2. t.me/mariupolRIP/37382 -- Хильдунин Евгений Александрович (b.1985),
     died in the building, body moved to a shoe shop, collected by
     emergency services before Easter, пр-т Мира 110.
  3. Google My Maps (mariupoldestruction.com's "Погибшие" / deceased layer,
     mid=1n0elDNzvK4vQYmWxCn2792ljSXNJK4x3) -- independently corroborates
     multiple "Мира, 110" casualty entries; this is the attributing source
     for the whole record per the user.
  Other names in the user's list (Малюха Анатолий, Коваленко Инга's sister,
  Афонин Пётр/Афонина Клавдия at Ленина 110 кв.127) are recorded in the
  description from the user's text directly -- no independent source link
  was given for those beyond the same Google My Maps layer.
  NOT captured here (per the user's explicit instruction): a YouTube video
  (https://www.youtube.com/watch?v=AmPu1gRLh-M) showing bodies wrapped in
  blankets in 108's courtyard -- user confirmed this is NOT the original
  source video, just a lead to keep on record until the original is found.
  Do not treat this URL as evidence pending that.

Public/unauthenticated, non-geoblocked sources (t.me embed widget, Google My
Maps) -- same precedent as scripts/59/60/159/160/161, Claude runs this
directly, no VPS needed.
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

YOUTUBE_LEAD_NOT_CAPTURED = "https://www.youtube.com/watch?v=AmPu1gRLh-M"


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

    content1, ctype1, status1 = fetch("https://t.me/mariupolRIP/36979?embed=1")
    sha1 = forensics.capture_source(
        content1, url="https://t.me/mariupolRIP/36979", source_type="telegram_post",
        title="mariupolRIP -- Глушко Анатолий Петрович, died пр-т Мира 110",
        description=(
            "Глушко Анатолий Петрович, 01.07.1937-17.03.2022. 'Умер в "
            "подвале от получения травмы головы взрывной волны. Тело "
            "подняли в квартиру. Захоронить не получилось из-за обстрелов, "
            "пр-т Мира 110.' (Died in a basement from a blast head injury; "
            "body moved to the apartment; burial impossible due to ongoing "
            "shelling.) Part of a 6-person casualty record for пр. Мира/"
            "Ленина 110 supplied by the user 2026-06-19, attributed to "
            "mariupoldestruction.com."
        ),
        content_type=ctype1, http_status=status1, con=con,
    )
    log.info("captured mariupolRIP/36979 -> sha=%s status=%s", sha1[:12], status1)
    time.sleep(REQUEST_PAUSE_S)

    content2, ctype2, status2 = fetch("https://t.me/mariupolRIP/37382?embed=1")
    sha2 = forensics.capture_source(
        content2, url="https://t.me/mariupolRIP/37382", source_type="telegram_post",
        title="mariupolRIP -- Хильдунин Евгений Александрович, died пр-т Мира 110",
        description=(
            "Хильдунин Евгений Александрович, b. 17.05.1985. 'умер в доме "
            "проспект Мира 110, вынесен был в обувной магазин, забрали "
            "перед паской МЧС.' (Died in the building; body moved to a "
            "shoe shop; collected by emergency services before Easter.) "
            "Part of the same 6-person casualty record as 36979 above."
        ),
        content_type=ctype2, http_status=status2, con=con,
    )
    log.info("captured mariupolRIP/37382 -> sha=%s status=%s", sha2[:12], status2)
    time.sleep(REQUEST_PAUSE_S)

    maps_url = ("https://www.google.com/maps/d/u/0/viewer?mid="
                "1n0elDNzvK4vQYmWxCn2792ljSXNJK4x3&"
                "ll=47.098102420177995,37.51938978751018&z=18")
    content3, ctype3, status3 = fetch(maps_url)
    sha3 = forensics.capture_source(
        content3, url=maps_url, source_type="google_my_maps_page",
        title="mariupoldestruction.com 'Погибшие' (deceased) layer -- "
              "Google My Maps, mid=1n0elDNzvK4vQYmWxCn2792ljSXNJK4x3",
        description=(
            "Citywide Google My Maps document, attributed to "
            "mariupoldestruction.com, with a per-building 'Погибшие в этом "
            "доме' (deceased in this building) layer. Independently "
            "confirmed (grep on the captured page) multiple casualty "
            "entries referencing 'Мира, 110', corroborating the two "
            "mariupolRIP posts above. Full per-pin extraction not done here "
            "-- this capture is the page-level corroborating source; the "
            "user's full 6-name list (Глушко, Хильдунин, Малюха Анатолий, "
            "Коваленко Инга's sister, Афонин Пётр, Афонина Клавдия -- the "
            "last two at Ленина 110 кв.127) plus a makeshift grave noted in "
            "106's courtyard is recorded as user-supplied text pending a "
            "structured per-pin re-extraction if needed."
        ),
        content_type="text/html", http_status=status3, con=con,
    )
    log.info("captured Google My Maps page -> sha=%s status=%s", sha3[:12], status3)

    log.info("NOT captured (user-flagged as not-yet-verified lead): %s",
             YOUTUBE_LEAD_NOT_CAPTURED)

    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
