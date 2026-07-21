#!/usr/bin/env python3
"""Capture t.me/Z2022sw/558 -- the 3-photo grave-marker album at the Гонды
40А churchyard cemetery («у Храма Веры, Надежды, Любови и матери их Софии»,
47°07'36.59"N 37°34'02.12"E). Source that opened this investigation
(2026-07-21 session). Photos show markers for:
  - Цыганкова Светлана Яковлевна, 06.1938 - 04.04.2022
  - Бабич Анатолий Леонтьевич, 1941 - 09.04.2022
  - Еременко Антонина (patronymic illegible on marker)

A 4th name, Науменко С.И. (full name/sex unclear), also appears on one of
these markers per user review but could not be independently re-read from
the CDN copy at capture resolution -- kept as a name-only lead, same as the
loader's treatment of Гонды 40А #398's Vasilenko ambiguity.

A 5th individual, Моторин Николай Владимирович, was documented via a
separate cross photo supplied directly by the user (not from this t.me
post) -- no capturable URL exists for that image; it is cited in the
loader's detail JSONB as "user-supplied photo, chain of custody outside
the raw store" rather than forensically captured here.

Public, unauthenticated t.me embed widget (?embed=1) -- same precedent as
scripts/239/397/400.
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
POST_URL = "https://t.me/Z2022sw/558"

PHOTOS = [
    ("https://cdn4.telesco.pe/file/vSShnkU6AKEY6bT2juxfk0-1KPWd56AvipF1YVNnhEVdhSs2Xfvc7_BhLn4Itx4gHzb1YVy0HtrhS_M95I52hUhWJOx8iIFsm_-kJ48oMa09KKIYG4ZwG_DFo6zvUgnP2j_gHk1jhAfiGsuq9MUWYMZKsOKE0m-HZTfJ2HyDH-TjkfcC_wg5asteT4_NkIIMXWg3PyzLfuSxSGlYMg_s05tf8su_5_dD9rPaKHnPAdOtxzrxEqRHs9fB5rRGusP3B696tRDFbZ5lkSSDD40ENfm8IiGO0XHmPVnigSX56LtTPIcc_Z4EeHE9jYr3YfJaPdrv4SB_YByMTcO5XPiy5g.jpg",
     "Цыганкова Светлана Яковлевна (06.1938-04.04.2022) + Бабич Анатолий Леонтьевич (1941-09.04.2022) markers, plus Науменко С.И. name-fragment"),
    ("https://cdn4.telesco.pe/file/LNQhtf7HExcU0eIxI-k5JjK23mX9PlGDy4aTmHtFLl6ec0JWYmEYGr2Ff5vz20b7dL_b39qgbku280owLwQAU6JQCHCSRiYV_AWSmI4vPdtXRRFJBFjM4pWj8OWGRlfimQMGD_mSQJG9p28_aSM0dndp15p7s-mge2ddYoRu4KmgxLTWryZZ-AnDsQ4Gdevp3YYfxDv0miu7mZK2gtiqjTAAH6PBEAudeGGgeLlgUsfq04tVbHMT6j7LvfVcR7Rrl1ZN1xh1DnRZiPQwffHExJ1pJQc0rUgXq0IVn03x9NYREadG3s8CdcO41jSS3EeH0uXwBw7AlHLRt-IuS3K3SQ.jpg",
     "wider grave-plot view, second angle"),
    ("https://cdn4.telesco.pe/file/ewNAMVEE5sXgR_us6rQ-EceuvNs8Vbq4YuxGVsj3GiWAgFHCKWIwv0hyE8EP4rZLIH1ZIgetGJ4IYKQP-XRPfOUbJe0NNCvgu1d09C8CT4JAcbtIk88srL-HrR8hseSGTA9Dqq0w5PQag4u9uhkIjWUdjaobiQ7gj2UuV7eQuFfrzDPF7haPOQu8tvHU3juHSKP3Cs9Bxob2gKJE_scZTS_Aw-sk-buiEac2wkQxoE5mjSkqDVxAeL89J05AqqKXQg-RPZ8Q2vtzOya2VA3ztJZdVF4a2m5EWEbssBCel7rHBF1kLcG9MOFo9ZNCNurzD0RYR9iRBhyQhfGCaM-sIQ.jpg",
     "Еременко Антонина marker (patronymic illegible), third angle"),
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
        title="Z2022sw/558 -- Гонды 40А churchyard grave-marker album (3 photos)",
        description=(
            "t.me/Z2022sw grouped photo post, msg 558. Source that opened "
            "the Гонды 40А churchyard cemetery investigation (2026-07-21 "
            "session; location 47°07'36.59\"N 37°34'02.12\"E, backyard of "
            "the temple of Sv. Vera, Nadezhda, Lyubov i mat' ikh Sofia, "
            "ul. Gondy 40А). Grave markers for Цыганкова Светлана "
            "Яковлевна, Бабич Анатолий Леонтьевич, Еременко Антонина "
            "(patronymic illegible), and a partial Науменко С.И. fragment."
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
            title=f"Z2022sw/558 album photo -- {desc}",
            description=(f"Full-resolution grave-marker photo from the "
                          f"Гонды 40А churchyard cemetery album "
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
