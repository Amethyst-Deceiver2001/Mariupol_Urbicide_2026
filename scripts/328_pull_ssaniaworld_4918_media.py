#!/usr/bin/env python3
"""Pull the actual media for @ssaniaworld/4918 (user-flagged 2026-07-16).

The unauthenticated t.me embed widget (both `?embed=1` and the `/s/`
channel preview list, both captured 2026-07-16, source_type
'telegram_ssaniaworld_msg_embed') marks this post `text_not_supported_wrap`
-- Telegram's OWN public widget refuses to render its content type. Turned
out why on inspection: this is a "rich message" (Instant-View/article-style)
post -- msg.media is None; the actual photos live in
msg.rich_message.photos[] (a Photo TL object per image, referenced from the
article body via PageBlockPhoto blocks), not as a classic message
attachment. telethon's download_media() accepts a raw Photo object
directly, so each gets downloaded that way once msg.media comes back empty.

Claude must never run this (CLAUDE.md) -- run from your own terminal:

    .venv312/bin/python scripts/328_pull_ssaniaworld_4918_media.py

Downloads into the forensic raw store (SHA-256 + .meta.json sidecar via
forensics.capture_source), source_type "telegram_ssaniaworld_msg_media".
Idempotent -- re-running skips photo ids already captured.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

SOURCE_TYPE = "telegram_ssaniaworld_msg_media"
CHANNEL = "ssaniaworld"
MSG_ID = 4918


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
    url = f"https://t.me/{CHANNEL}/{MSG_ID}"

    client = TelegramClient(
        config.TELEGRAM_SESSION, config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH)
    client.start(phone=config.TELEGRAM_PHONE_NUMBER)
    n_pulled = n_skipped = 0
    try:
        try:
            entity = client.get_entity(CHANNEL)
        except (errors.UsernameInvalidError, ValueError) as e:
            log.error("channel %r not resolvable: %s", CHANNEL, e)
            sys.exit(1)

        msg = client.get_messages(entity, ids=MSG_ID)
        if msg is None:
            log.error("message %s not found (deleted, or account not in channel)", url)
            sys.exit(1)

        rich = getattr(msg, "rich_message", None)
        rich_photos = getattr(rich, "photos", None) or []
        log.info("message type check — media=%s, poll=%s, rich_message_photos=%d, text=%r",
                 type(getattr(msg, "media", None)).__name__,
                 getattr(msg, "poll", None) is not None,
                 len(rich_photos), (msg.message or "")[:200])

        if getattr(msg, "media", None) is not None:
            log.info("downloading classic attachment on %s ...", url)
            blob = client.download_media(msg, file=bytes)
            if blob:
                ct = _media_content_type(msg)
                sha = forensics.capture_source(
                    blob, url=url + "/media", source_type=SOURCE_TYPE,
                    title=f"@{CHANNEL}/{MSG_ID} media",
                    description=f"User-flagged 2026-07-16. {url} ({ct}).",
                    content_type=ct, http_status=200, con=con,
                )
                log.info("captured %s (%s, %d bytes) -> sha=%s", url, ct, len(blob), sha[:16])
                n_pulled += 1

        if not rich_photos:
            if n_pulled == 0:
                log.warning("no downloadable media on %s at all — check the "
                           "message type check line above", url)
            return

        # rich-message (article/Instant-View) post: photos live in
        # rich_message.photos[], each a raw Photo TL object, referenced from
        # the article body via PageBlockPhoto blocks. download_media()
        # accepts a Photo object directly.
        for i, photo in enumerate(rich_photos):
            photo_url = f"{url}/rich_photo/{photo.id}"
            existing = con.execute(
                "SELECT sha256 FROM source_document WHERE url=? AND source_type=?",
                (photo_url, SOURCE_TYPE),
            ).fetchone()
            if existing:
                log.info("already captured, skipping: %s (sha=%s)",
                        photo_url, existing[0][:12])
                n_skipped += 1
                continue

            log.info("downloading rich-message photo %d/%d (id=%s) ...",
                     i + 1, len(rich_photos), photo.id)
            blob = client.download_media(photo, file=bytes)
            if not blob:
                log.error("empty download for rich photo %s", photo.id)
                continue

            sha = forensics.capture_source(
                blob, url=photo_url, source_type=SOURCE_TYPE,
                title=f"@{CHANNEL}/{MSG_ID} rich-message photo {i+1}/{len(rich_photos)}",
                description=(f"User-flagged 2026-07-16. Rich-message "
                             f"(Instant-View/article) post, photo {i+1} of "
                             f"{len(rich_photos)} embedded in the article "
                             f"body. Photo id={photo.id}, dated "
                             f"{photo.date.date() if photo.date else '?'}. "
                             f"{url}"),
                content_type="image/jpeg", http_status=200, con=con,
            )
            log.info("captured %s (%d bytes) -> sha=%s", photo_url, len(blob), sha[:16])
            n_pulled += 1
    finally:
        client.disconnect()

    log.info("done — %d pulled, %d skipped (already captured)", n_pulled, n_skipped)

    log.info("Next: PYTHONPATH=src .venv312/bin/python "
             "scripts/326_rekognition_photo_triage.py --source-type %s --limit 5",
             SOURCE_TYPE)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
