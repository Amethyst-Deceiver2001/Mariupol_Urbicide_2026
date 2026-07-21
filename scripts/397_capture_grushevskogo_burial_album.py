#!/usr/bin/env python3
"""Capture the 4-photo grave-marker album at t.me/mariupolRIP/16611-16614
(grouped_id=13208641807002994) -- companion photos to the video already
captured at t.me/mariupolRIP/17883 (sha fa96a0e8..., see
memory/grave_sites_case_study_upgrade_2026-07-12.md and the 2026-07-21
courtyard-burial review). These photos give clean, full-resolution reads of
4 named grave markers at the Грушевского 10/12 courtyard site (property_id
4690/4691) that the compressed video frames could only partially confirm:
  - Шмат Борис Петрович, 1939-2022 (video misread as "Ищат")
  - Василенко В.Я./В.А. (cursive initial ambiguous even at this resolution),
    died 27.03.2022
  - Выходцев Александр Петрович, 27.02.1954-21.03.2022
  - Головина Марина, died ~15.03.2022 (carved directly into the cross wood;
    not confidently matched to a specific cross in the video pan)

Public, unauthenticated t.me embed widget (?embed=1) -- same precedent as
scripts/239: non-geoblocked, Claude runs this directly, no VPN needed.
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
ALBUM_MSG_URL = "https://t.me/mariupolRIP/16611"  # first msg of the grouped album

PHOTOS = [
    ("https://cdn4.telesco.pe/file/s3wu9gdY600EMsR03EbycioIeDx7ZLu5015-jfmzc_UMFUHre1N0nWeLLTZV0q0fc_ZYiloG0ptQxZW9Ck7s9qrdAdeRpoJUgvYpv1itovzDVTIR77UE6t-OXDdnLQWvsDjmDHR6MTSx2PqvKRaz9PP8tzeEOsRFbQNgJRcG9Z2dYXXY0bTvpYvpvwLJsortxidkdZSeuSAF7Xlc-lDjsedWUZ-CXskhcVQj-u_GcsqtcDOpckKRYZmMeP5Jb5iR15ieRs4KvKwOAjWQNuIL0CwRUhadWcXz3h8i7jfpMC4pxuEsk7KNgXITKQApSIZXZ1cvbak_jVq-QR4QpsJEFA.jpg",
     "Выходцев Александр Петрович, 27.02.1954-21.03.2022 (grave marker, close-up)"),
    ("https://cdn4.telesco.pe/file/VJFNr4SpvBV6xhHAd8W5DgP-SF_aBknGwuiyp6OPXNmeETo3o-e2L4lUnaw9OReOOUmlDUpLS5VRraYdDWsb9oMhKXTYnQrb3Fjd94OblD0kadtoES-viKvKORE-Rc4vPfBuXepEqwRRWUDsHWMxQYYmhR4YbyG_tuncv95Z3HT_y7JII08gynzV1ZOU4a8DSs3grN6sfSkemi_Ms-tzZ6MJoGZCChDy3QF2lY1pq5CMUSl4bCW5sPywPYw_4-lxm21bl_wLpgHq7KGdXS45rxWvSMeqt0pN4SAT2IkeCOPkEt79cm4bYkY2W5gzZerisLAM6inUTOg_vz-e_6ojhA.jpg",
     "Головина Марина, died ~15.03.2022 (name carved directly into cross wood)"),
    ("https://cdn4.telesco.pe/file/jJZlnAOtaIR8oI-_cn_sMrWbBzf0Xbo0aLk0PVN3zrV-T7dui5wvV6mCqKncO5a29JstVMqQf5gt722LNy1VwgEWt4g8zTb1PajCbZ-XVpbydJGOYSVnjzpBYbAiXdHpA3ZrBGBM1Q-hIto3-Xy-nZjM4ypFd8lDsUUOWtgIR7OoP1QFNVfmV7hDE6LBBqlh37aZmleQqqe2oAI2X9tN9tgerDNT8aCdMwZIna4elsYt8kodTxpgSRGyXofIqBzydZswRiWRVz8WU2lx06t1IIUkHcoVtmfw49p5id1fzbQY6yu73lv-KuOTlDKVpEqjeglSprLpRXvykhqLLZz6Mg.jpg",
     "Василенко В.Я./В.А. (cursive initial ambiguous), died 27.03.2022 (grave marker, close-up)"),
    ("https://cdn4.telesco.pe/file/sOALSA7QeVER7R-YWdiU3LCIXuQk9mfVcPXOb4dFwXtrJog-YSf1bw1v4jTCoD8n-YVbyJ3INb5rTFn9RQw6a0oMOzieAuM7i2lzt4uOboa2F5IVpprvRkG8509Nxp19oj9E_97NcF7DRphUmGSr009WGnSgJcPm_-hvYklyswm9cd7dOqlALTmIPF1XQ-3Ig4Nhfe5mNTOAM-PriC0WwVni18gmbP_ftihFBQr9qpq3KJHJR5-bIkBWMgSBFfKZ66OwkEarwlLyKJ1apOuZbLVe6wS-IySFUMb_KYg0p71cvICrTEOWMJYxkDldHG2zNN9G8xwBEhboKqmceIPM0g.jpg",
     "Шмат Борис Петрович, 1939-2022 (grave marker, close-up -- video-frame catalog misread this as \"Ищат\")"),
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

    # the embed page itself (album context, all 4 photo URLs embedded)
    content, ctype, status = fetch(f"{ALBUM_MSG_URL}?embed=1")
    sha_embed = forensics.capture_source(
        content, url=ALBUM_MSG_URL, source_type="telegram_post",
        title="mariupolRIP/16611 -- Грушевского 10/12 courtyard grave-marker album (4 photos)",
        description=(
            "t.me/mariupolRIP grouped photo album (grouped_id=13208641807002994, "
            "msgs 16611-16614, posted 2026-04-27), embed widget HTML. Companion "
            "primary source to the courtyard-burial video at mariupolRIP/17883 "
            "(sha fa96a0e8...) for the same Грушевского 10/12 site "
            "(property_id 4690/4691). 4 named grave markers photographed."
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
            title=f"mariupolRIP/16611 album photo -- {desc}",
            description=(f"Full-resolution grave-marker photo from the "
                          f"Грушевского 10/12 courtyard burial album "
                          f"(t.me/{ALBUM_MSG_URL.split('t.me/')[1]}, parent embed "
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
