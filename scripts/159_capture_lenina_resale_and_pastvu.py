#!/usr/bin/env python3
"""Capture demand-side resale evidence + a prewar baseline photo for the
пр. Ленина 104/106/108/110 case study (user-supplied 2026-06-19).

Public/unauthenticated, non-geoblocked sources (t.me embed widget, pastvu.com)
-- same precedent as scripts/59/60, Claude runs this directly, no VPS needed.

Sources:
  1. t.me/Mariupol_house/84850/402040 -- 2-room resale listing, пр. Ленина 106
     (with "переход"/extra room), channel "Мир мариупольской недвижимости"
     forwarded into Mariupol_house's discussion group, 2024-01-24. The
     ?embed=1 widget returns "Service message / media not supported" for
     this post (it's a multi-photo album) -- SAME limitation already hit and
     documented for 676643 below; only channel/date/post-link are
     independently verifiable this way. The actual listing text/photo the
     user pasted directly into chat (2k apt, 4/9 floor, 47.8/26.3/6.3 m²,
     5 млн руб, contact +7(949)70-69-167 "Сергей") is recorded here as
     user-supplied content, NOT independently re-derived from this capture.
  2. t.me/Mariupol_house/676643/1040061 -- SAME canonical post as the
     already-captured sha bf0b3fdc... (url .../676643/919942, captured
     2026-06-19). The trailing id is the discussion-group's internal
     redirect pointer, which shifts over time -- not a new post, so no
     re-capture here. CORRECTION (2026-06-19): the case study's earlier
     memory note guessed this listing was for 108 (the partially-demolished
     building) purely by inference, never having seen the actual content.
     The user has now supplied the screenshot directly: it is a 3-room,
     63.4 m², 7/9-floor "под ремонт" listing for пр. Ленина 110 (not 108),
     3 млн руб (reduced), "поставлена в Росреестр, один собственник",
     contact +79495584140. Recorded here as user-supplied content -- the
     ?embed=1 widget still only yields "Service message / media not
     supported" for this post, so the listing text/photos are not
     independently re-derivable from the capture itself.
  3. pastvu.com/p/1167758 -- 1979 photo titled "Проспект Ленина", geotagged
     47.09889/37.518342 -- ~25m from property_id 4423 (пр. Ленина 110,
     47.0984355/37.5180284). CONFIRMED by the user (2026-06-19) as пр.
     Ленина 110 -- the package's first prewar-baseline imagery for any of
     the four buildings.

Capture-before-parse: raw bytes -> data/raw/<sha256>.<ext> + .meta.json,
registered in source_document. No field extraction, no DB writes beyond that.
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

    # 1) Mariupol_house/84850 comment -- partial capture (widget can't
    # render the album; channel/date/link only)
    url = "https://t.me/Mariupol_house/84850/402040?embed=1"
    content, ctype, status = fetch(url)
    sha = forensics.capture_source(
        content, url="https://t.me/Mariupol_house/84850", source_type="telegram_post",
        title="Mariupol_house discussion comment, forwarded from 'Мир "
              "мариупольской недвижимости' (Сергей) -- 2k resale listing, "
              "пр. Ленина 106, 2024-01-24",
        description=(
            "?embed=1 widget returns 'Service message / media not supported' "
            "(multi-photo album) -- only channel name, post date "
            "(2024-01-24T05:19:56Z) and canonical link independently "
            "verifiable from this capture. Listing content as supplied "
            "directly by the user (screenshot, 2026-06-19): '2к квартира в "
            "САМОМ ЦЕНТРЕ ГОРОДА, С БОЛЬШИМ ПЕРЕХОДОМ (дополнительная "
            "комната), 4 этаж 9-этажного дома, 47.8/26.3/6.3 м², вид на "
            "проспект, пр. Ленина 106, квартира с полным ремонтом от "
            "подрядчика, внесена в Росреестр, 5 млн ₽ торг, "
            "+7(949)70-69-167 Сергей'. First direct demand-side resale "
            "evidence for 106 specifically (108 already had 2 leads, see "
            "memory; 110 below)."
        ),
        content_type=ctype, http_status=status, con=con,
    )
    log.info("captured 84850 comment -> sha=%s status=%s", sha[:12], status)
    time.sleep(REQUEST_PAUSE_S)

    # 2) Pastvu 1979 photo -- full capture, fetchable directly
    page_content, page_ctype, page_status = fetch("https://pastvu.com/p/1167758")
    forensics.capture_source(
        page_content, url="https://pastvu.com/p/1167758", source_type="pastvu_page",
        title="Pastvu p/1167758 -- 'Проспект Ленина', 1979",
        description="Page metadata for the photo below: title 'Проспект "
                     "Ленина', year 1979, geo 47.09889/37.518342, uploaded "
                     "by user 'nb92'.",
        content_type=page_ctype, http_status=page_status, con=con,
    )
    time.sleep(REQUEST_PAUSE_S)

    photo_content, photo_ctype, photo_status = fetch(
        "https://pastvu.com/_p/a/2/n/i/2nikkyp6s4rmxtd7o8.jpg"
    )
    photo_sha = forensics.capture_source(
        photo_content, url="https://pastvu.com/_p/a/2/n/i/2nikkyp6s4rmxtd7o8.jpg",
        source_type="pastvu_photo",
        title="Pastvu p/1167758 photo -- 9-storey Soviet apartment block, "
              "пр. Ленина, 1979",
        description=(
            "1979 photo, geotagged 47.09889/37.518342 -- ~25m from "
            "property_id 4423 (пр. Ленина 110, 47.0984355/37.5180284). "
            "CONFIRMED by the user (2026-06-19) as пр. Ленина 110 -- prewar "
            "baseline photo for this building, ~43 years before the siege."
        ),
        content_type=photo_ctype, http_status=photo_status, con=con,
    )
    log.info("captured pastvu photo -> sha=%s status=%s", photo_sha[:12], photo_status)
    time.sleep(REQUEST_PAUSE_S)

    # 3) Re-fetch 676643 purely to correct its metadata description -- raw
    # bytes are unchanged/idempotent (capture_source never rewrites bytes
    # for an existing sha), this call only fixes the building attribution.
    # Originally guessed as 108 by inference; the user has now confirmed via
    # direct screenshot that this listing is for 110, not 108.
    content2, ctype2, status2 = fetch("https://t.me/Mariupol_house/676643/1040061?embed=1")
    sha2 = forensics.capture_source(
        content2, url="https://t.me/Mariupol_house/676643/919942",
        source_type="telegram_post",
        title="Недвижимость - Мариуполь (channel), 2025-12-29 -- resale "
              "listing, пр. Ленина 110",
        description=(
            "?embed=1 widget returns 'Service message / media not "
            "supported' (multi-photo album) -- only channel name, post "
            "date (2025-12-29) and canonical link independently verifiable "
            "from this capture. CORRECTED (2026-06-19): listing content "
            "as supplied directly by the user (screenshot): 3-room "
            "apartment, 63.4 m², floor 7/9, 'под ремонт', new wiring/water/"
            "gas/floor screed installed, 'поставлена в Росреестр, один "
            "собственник', price reduced to 3 млн руб, contact "
            "+79495584140. Address is пр. Ленина 110 -- NOT 108 as "
            "originally guessed by inference before the content was seen."
        ),
        content_type=ctype2, http_status=status2, con=con,
    )
    log.info("re-captured 676643 (corrected to 110) -> sha=%s status=%s", sha2[:12], status2)

    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
