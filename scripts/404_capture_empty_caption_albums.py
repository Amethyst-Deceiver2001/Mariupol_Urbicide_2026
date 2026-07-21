#!/usr/bin/env python3
"""Capture all photos from the 66 empty-caption grouped albums identified by
scripts/399_mariupolrip_empty_caption_albums.py (159 photos total). These
were invisible to every prior text-keyword pass (scripts/303/304/309) since
they carry zero caption text on any message in the group -- the exact blind
spot that hid the Грушевского 10/12 courtyard album (grouped_id
13208641807002994) until a companion post supplied names. This closes that
gap systematically instead of relying on a lucky cross-post.

Fetches each album's first-message embed page (?embed=1), which Telegram
renders with every grouped photo's CDN URL inline (background-image:url(...)
in the grouped_media markup) -- one fetch per album covers the whole group,
same technique as scripts/397/400/401.

Public, unauthenticated t.me embed widget -- non-geoblocked, Claude runs
this directly, no VPN needed (same precedent as scripts/239 onward).
"""
import json
import logging
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

REQUEST_PAUSE_S = 1.0
ALBUMS_PATH = ROOT / "data" / "parsed" / "mariupolrip_empty_caption_albums.jsonl"
OUT_PATH = ROOT / "data" / "parsed" / "mariupolrip_empty_caption_captures.jsonl"

IMG_RE = re.compile(r"background-image:url\('([^']+\.jpg)'\)")


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
    albums = [json.loads(l) for l in open(ALBUMS_PATH, encoding="utf-8")]
    con = forensics.open_state()
    results = []

    for i, album in enumerate(albums, 1):
        url = album["first_url"]
        try:
            content, ctype, status = fetch(f"{url}?embed=1")
        except requests.exceptions.RequestException as exc:
            log.error("[%d/%d] FAILED %s: %s", i, len(albums), url, exc)
            results.append({**album, "embed_sha256": None, "photo_shas": [], "error": str(exc)})
            continue

        sha_embed = forensics.capture_source(
            content, url=url, source_type="telegram_post",
            title=f"mariupolRIP/{album['msg_ids'][0]} -- empty-caption album ({album['n_photos']} photos)",
            description=(
                f"t.me/mariupolRIP grouped photo album (grouped_id="
                f"{album['grouped_id']}, msgs {','.join(album['msg_ids'])}, "
                f"posted {album['date']}). Zero caption text on every "
                f"message in the group -- surfaced by "
                f"scripts/399_mariupolrip_empty_caption_albums.py's "
                f"blind-spot sweep, not by keyword match. Captured for "
                f"visual-only review (2026-07-21 systematic backlog)."
            ),
            content_type=ctype, http_status=status, con=con,
        )

        photo_urls = IMG_RE.findall(content.decode("utf-8", errors="replace"))
        photo_shas = []
        for photo_url in photo_urls:
            time.sleep(REQUEST_PAUSE_S)
            try:
                pcontent, pctype, pstatus = fetch(photo_url)
            except requests.exceptions.RequestException as exc:
                log.warning("  photo fetch failed %s: %s", photo_url, exc)
                continue
            psha = forensics.capture_source(
                pcontent, url=photo_url, source_type="telegram_post_photo",
                title=f"mariupolRIP/{album['msg_ids'][0]} empty-caption album photo",
                description=(f"Photo from empty-caption album "
                              f"(t.me/{url.split('t.me/')[1]}, parent embed "
                              f"sha={sha_embed[:12]})."),
                content_type=pctype, http_status=pstatus, con=con,
            )
            photo_shas.append(psha)

        results.append({**album, "embed_sha256": sha_embed, "photo_shas": photo_shas})
        log.info("[%d/%d] %s -> embed=%s, %d/%d photos captured",
                  i, len(albums), url, sha_embed[:12], len(photo_shas), album["n_photos"])
        time.sleep(REQUEST_PAUSE_S)

    con.close()

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    n_ok = sum(1 for r in results if r.get("embed_sha256"))
    n_photos = sum(len(r.get("photo_shas", [])) for r in results)
    log.info("=== done: %d/%d albums captured, %d photos total -> %s ===",
              n_ok, len(albums), n_photos, OUT_PATH)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
