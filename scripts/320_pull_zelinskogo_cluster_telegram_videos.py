#!/usr/bin/env python3
"""Download 2 specific videos flagged 2026-07-15 during review of the
Зелинского 17А/17Б/19Б + Бахчиванджи 25/27 demolition cluster (ЖК
«Нахимовский», decree №178 -- see docs/case_studies/
death_sites_new_construction.md Case 2). Too large / not exposed via the
unauthenticated t.me/<chan>/<id>?embed=1 widget, so pulled via an
authenticated telethon session (same reason as scripts/283):

1. @kadryVoynyMariypol2022/854 -- walkthrough video, 2:44-4:25 relevant:
   narrator points at the green fence around the L-shaped demolished 17А.
   Other addresses appear elsewhere in the same video (not yet timecoded).

2. @mariupolnow/8354 -- another video of 17Б.

(A third artifact the user flagged, @mariupolnow/25517 -- 17А demolition in
progress -- was a photo/short clip already reviewable via the ?embed=1
widget and does not need this authenticated path; skip unless review shows
otherwise.)

Claude must never run this (CLAUDE.md) -- it hits Telegram, a geoblocked
foreign-state-adjacent service. Run from your own Russia-routed terminal:

    .venv312/bin/python scripts/320_pull_zelinskogo_cluster_telegram_videos.py

Downloads both videos into the forensic raw store directly (SHA-256 +
.meta.json sidecar via forensics.capture_source), source_type
"telegram_video_zelinskogo_cluster". Idempotent -- re-running skips
messages whose media is already captured (checked by URL before download).
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

SOURCE_TYPE = "telegram_video_zelinskogo_cluster"

TARGETS = [
    {
        "channel": "kadryVoynyMariypol2022",
        "msg_id": 854,
        "note": ("Walkthrough video. 2:44-4:25: narrator identifies "
                 "Зелинского 17А by its green fence. Other addresses appear "
                 "elsewhere in the video, not yet timecoded/reviewed -- "
                 "review full runtime once downloaded."),
    },
    {
        "channel": "mariupolnow",
        "msg_id": 8354,
        "note": "Video of Зелинского 17Б.",
    },
]


def _media_content_type(message) -> str:
    f = getattr(message, "file", None)
    mime = getattr(f, "mime_type", None) if f is not None else None
    if mime:
        return mime
    if getattr(message, "photo", None) is not None:
        return "image/jpeg"
    return "application/octet-stream"


def main() -> None:
    if not (config.TELEGRAM_API_ID and config.TELEGRAM_API_HASH):
        log.error("TELEGRAM_API_ID / TELEGRAM_API_HASH not set in .env — aborting")
        sys.exit(1)
    try:
        import telethon  # noqa: F401
    except ImportError:
        log.error("telethon not installed — run: pip install -e '.[telegram]'")
        sys.exit(1)

    from telethon.sync import TelegramClient
    from telethon import errors

    con = forensics.open_state()
    client = TelegramClient(
        config.TELEGRAM_SESSION, config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH)
    client.start(phone=config.TELEGRAM_PHONE_NUMBER)

    n_pulled = n_skipped = n_err = 0
    try:
        for t in TARGETS:
            channel, msg_id = t["channel"], t["msg_id"]
            url = f"https://t.me/{channel}/{msg_id}"
            existing = con.execute(
                "SELECT sha256 FROM source_document WHERE url=? AND source_type=?",
                (url + "/media", SOURCE_TYPE),
            ).fetchone()
            if existing:
                log.info("already captured, skipping: %s (sha=%s)", url, existing[0][:12])
                n_skipped += 1
                continue

            try:
                entity = client.get_entity(channel)
            except (errors.UsernameInvalidError, ValueError) as e:
                log.error("channel %r not resolvable: %s", channel, e)
                n_err += 1
                continue

            msg = client.get_messages(entity, ids=msg_id)
            if msg is None or getattr(msg, "media", None) is None:
                log.error("no media on %s", url)
                n_err += 1
                continue

            log.info("downloading %s ...", url)
            try:
                blob = client.download_media(msg, file=bytes)
            except Exception:  # noqa: BLE001
                log.exception("download failed for %s", url)
                n_err += 1
                continue
            if not blob:
                log.error("empty download for %s", url)
                n_err += 1
                continue

            ct = _media_content_type(msg)
            caption = (msg.message or "").strip()
            forensics.capture_source(
                blob, url=url + "/media",
                source_type=SOURCE_TYPE,
                title=f"@{channel}/{msg_id} media",
                description=(
                    f"Зелинского cluster artifact. {t['note']} "
                    f"{url} ({msg.date.date() if msg.date else '?'}, {ct}). "
                    f"caption: {caption[:200]!r}"),
                content_type=ct, http_status=200, con=con,
            )
            n_pulled += 1
            log.info("captured %s (%s, %d bytes)", url, ct, len(blob))
    finally:
        client.disconnect()

    log.info("done — %d pulled, %d skipped (already captured), %d errors",
             n_pulled, n_skipped, n_err)
    log.info("Next step: tell Claude once done -- review + fold findings into "
              "docs/case_studies/death_sites_new_construction.md Case 2.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
