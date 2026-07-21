#!/usr/bin/env python3
"""Capture t.me/nmrpl/6259 -- official Ilyichevsk district administration
post (АГО МАРИУПОЛЬ channel) dated 2023-03-30, confirming site clearance at
the Гонды 40А churchyard cemetery (temple of Sv. Vera, Nadezhda, Lyubov i
mat' ikh Sofia). Official text states over 50 people were buried near the
church during hostilities, were subsequently reburied elsewhere ("после
перезахоронения на территории остались ямы" -- pits remained after
reburial), and the site was landscaped by MUP AGM "Zelenstroy" + district
communal-services dept, assisted by contractor "Stroymonolit", ahead of
Easter. Named: Natalya Martynenko (secretary, KSN "Tsentralny-2"), father
Gennady (priest). 3 photos attached (msgs 6259-6261) show a backhoe grading
the burial field with the church cupola visible in frame.

This dates the clearance precisely between the two satellite reference
points already on file: church/graves visible 9 May 2022 (Google Earth,
user-supplied), site clear 8 Aug 2024 (Google Earth, user-supplied).

Public, unauthenticated t.me embed widget (?embed=1) -- same precedent as
scripts/239/397: non-geoblocked, Claude runs this directly, no VPN needed.
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
POST_URL = "https://t.me/nmrpl/6259"  # first msg of the grouped album

PHOTOS = [
    ("https://cdn4.telesco.pe/file/eVQUsvlPA659zB5-Vnqu-6aiYkGwfyVVUQW7CYakXpuKvn1H6yLHCelp3ETc_YwijgLOImx4eMYNMPqZcVFsW7JesLYarv2RLOlZS3mfnQlpcbm5Kt3HO8zKF0uOAX_-36n7pXasUArUzsKre4HsMTJsF-H1nGmeaq9lQAYUKi3963BO6GkpUCnyVNYE7NeDVxbsOkS262qf5t4kAIdymCI8TxECDmrC3hyQczhDGUbbPEN38rrsGv-YR6tiAWwsXLc_MAoqLJow_j9tWrJHexMdfPtnAlMOibMagTJdLALQpTyCn9JnbMETz1K34zRAMk90SiltEvlW0bevTsEH2w.jpg",
     "backhoe grading burial field, church cupola visible (msg 6259)"),
    ("https://cdn4.telesco.pe/file/GS1XCDUFt7kAZ-gvYBrnKvQRSbt03A52DieEBoQqaLmacwslW-LsmU6ew1mh-GYd0T8SrIZSeEnHH97yAaLSRNAD4_jYF_t3goO_Ek2AEePe_2Del1vyCRZ_8V-ymq_cSt_RLKGbqecT0xzTV3n2D2PWSe6EwpkmhhPkFgHqWexpTZyf5WPbNy42dPPZR4gyAF2j4xuxDkAfpSfkhjXqc_iSMoKt58ZlXpXfHncrJeKNUt_-Q2JvUayPv4o4xNascKA8FTMrqxS_ihKQID1r9hnCByv2yhsG14s76laZUvpMGm-0rtp-apmhAeGad9xrYGSHEPGm_uQoirqH42wLYg.jpg",
     "backhoe on site, apartment block on Металлургов side visible in background (msg 6260)"),
    ("https://cdn4.telesco.pe/file/CmhSGxDsKuNgsRKOl5w9DCJzaL6-0SjJLEJJy-96I8zIiilbKaFzgiKGpKnrCmBkJ44wIJv2kVc2dlBDai3weLr78ft8mn5ho987pFB8LJRkqbFpz6De6pe1QYfTadQWeY-KsuDHldhW8wUp2sLjKRY8fAmhxsPAb-fy50DytJvbBXCMUlI2JASoIUN7NRcQ8-dw8Kfjle9KfqSfvZsuS5eznMJnM3b_Se1ukQOAiF9HlIT7tspuD1SBXs9ydF_U0XtcDF1dWT1IfFB-mdHE2mQvA1_pGGkeXXKgLUtbfOysP5-kWOG9h9Qmb5czbCe1P3bZtzLxsorCjbZ4HylMKA.jpg",
     "backhoe + church full facade, wide shot (msg 6261)"),
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

    content, ctype, status = fetch(f"{POST_URL}?embed=1")
    sha_embed = forensics.capture_source(
        content, url=POST_URL, source_type="telegram_post",
        title="nmrpl/6259 -- official Ilyichevsk district admin post confirming Гонды 40А churchyard site clearance (2023-03-30)",
        description=(
            "t.me/nmrpl (АГО МАРИУПОЛЬ, official Ilyichevsk district "
            "administration channel), grouped post msgs 6259-6261, posted "
            "2023-03-30T11:13:00Z. Official text: 'Начато благоустройство "
            "территории возле храма Св. Веры, Надежды, Любови и матери их "
            "Софии' -- states over 50 people were buried near the church "
            "during hostilities ('пришлось захоронить свыше 50-и погибших'), "
            "were subsequently reinterred elsewhere ('после перезахоронения "
            "на территории остались ямы'), and the site was landscaped by "
            "MUP AGM Zelenstroy + Ilyichevsk district communal-services dept, "
            "assisted by contractor Stroymonolit, ahead of Easter. Named: "
            "Natalya Martynenko (secretary, KSN Tsentralny-2), father "
            "Gennady (priest). Corroborates and dates the clearance seen "
            "between user-supplied Google Earth references (graves visible "
            "9 May 2022, site clear 8 Aug 2024)."
        ),
        content_type=ctype, http_status=status, con=con,
    )
    log.info("captured embed page -> sha=%s status=%s", sha_embed[:12], status)
    time.sleep(REQUEST_PAUSE_S)

    shas = []
    for url, desc in PHOTOS:
        content, ctype, status = fetch(url)
        sha = forensics.capture_source(
            content, url=url, source_type="telegram_post_photo",
            title=f"nmrpl/6259 clearance-post photo -- {desc}",
            description=(f"Photo from official Ilyichevsk district admin "
                          f"post on Гонды 40А churchyard site clearance "
                          f"(t.me/{POST_URL.split('t.me/')[1]}, parent embed "
                          f"sha={sha_embed[:12]}). {desc}"),
            content_type=ctype, http_status=status, con=con,
        )
        shas.append(sha)
        log.info("captured photo -> sha=%s status=%s (%s)", sha[:12], status, desc[:50])
        time.sleep(REQUEST_PAUSE_S)

    con.close()
    log.info("=== SHA-256 SUMMARY ===")
    log.info("SHA_EMBED_PAGE = %r", sha_embed)
    for sha, (_, desc) in zip(shas, PHOTOS):
        log.info("%r  # %s", sha, desc)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
