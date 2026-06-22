#!/usr/bin/env python3
"""Crawl the private Telegram chat "Морской 38, 36, 30" — 2022-01-01 to 2023-12-31.

Private group (invite link https://t.me/+SnEb70BmuGg4NzNi, internal id 1671356804).
Account is already a member — no join action needed.

Covers three buildings:
  - бульвар Морской (Комсомольский), д.30 — not yet in spine
  - бульвар Морской (Комсомольский), д.36 — not yet in spine
  - бульвар Морской (Комсомольский), д.38 — pid=10724, rd4u=A3.3/A3.6, no seizure events

~3,498 total messages; post-2023 is predominantly spam; this script caps at 2023-12-31.

Claude must never run this (CLAUDE.md). Run from project root with:

    .venv312/bin/python scripts/75_crawl_morskoy_chat.py

Re-runs are incremental (skips already-stored message ids).

Output:
  data/raw/<sha256>.bin + <sha256>.meta.json  — raw message JSON blobs
  data/raw/<sha256>.bin + <sha256>.meta.json  — media blobs
  Logged to data/raw_index.db source_document table
  (source_type = telegram_building_chat_msg / telegram_building_chat_media)
"""
import base64
import datetime as dt
import json
import logging
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

# Private group — access via invite hash (account already member)
INVITE_HASH  = "SnEb70BmuGg4NzNi"
CHANNEL_SLUG = "morskoy_38_36_30"   # used only for URL keys and log labels
BUILDING_NOTE = (
    "Residents' chat 'Морской 38, 36, 30', Mariupol. "
    "бульвар Морской (occupation: Комсомольский), д.30/36/38. "
    "pid=10724 (д.38, rd4u=A3.3,A3.6); д.30 and д.36 not yet in spine."
)

DATE_FROM = dt.datetime(2022, 1, 1, tzinfo=dt.timezone.utc)
DATE_TO   = dt.datetime(2023, 12, 31, 23, 59, 59, tzinfo=dt.timezone.utc)

SOURCE_TYPE_MSG   = "telegram_building_chat_msg"
SOURCE_TYPE_MEDIA = "telegram_building_chat_media"


def _json_default(o: Any):
    if isinstance(o, (dt.datetime, dt.date)):
        return o.isoformat()
    if isinstance(o, (bytes, bytearray)):
        return base64.b64encode(bytes(o)).decode("ascii")
    if isinstance(o, set):
        return sorted(o)
    return str(o)


def _serialize(message) -> bytes:
    return json.dumps(
        message.to_dict(), ensure_ascii=False, default=_json_default,
        sort_keys=True, indent=2,
    ).encode("utf-8")


def _max_captured_id(con, slug: str) -> int:
    """Highest message id already captured for this channel slug (0 if none)."""
    prefix = f"https://t.me/{slug}/"
    rows = con.execute(
        "SELECT url FROM source_document WHERE source_type=? AND url LIKE ?",
        (SOURCE_TYPE_MSG, prefix + "%"),
    ).fetchall()
    best = 0
    for (url,) in rows:
        tail = url[len(prefix):].split("/", 1)[0]
        if tail.isdigit():
            best = max(best, int(tail))
    return best


def _capture_message(client, con, slug: str, message) -> bool:
    """Capture one message + its media. Returns True if media was present."""
    url  = f"https://t.me/{slug}/{message.id}"
    text = (message.message or "").strip()
    has_media = getattr(message, "media", None) is not None

    sha = forensics.capture_source(
        _serialize(message), url=url,
        source_type=SOURCE_TYPE_MSG,
        title=f"morskoy/{message.id}",
        description=(
            f"Resident chat post morskoy/{message.id} "
            f"({message.date.isoformat() if message.date else '?'}, "
            f"{'media' if has_media else 'text'}). {BUILDING_NOTE} "
            f"text_len={len(text)}."
        ),
        content_type="application/json",
        http_status=200, con=con,
    )

    if not has_media:
        return False

    try:
        blob = client.download_media(message, file=bytes)
    except Exception:
        log.exception("media download failed for msg id=%d", message.id)
        return False
    if not blob:
        return False

    f    = getattr(message, "file", None)
    mime = getattr(f, "mime_type", None) if f else None
    ct   = mime or ("image/jpeg" if getattr(message, "photo", None) else "application/octet-stream")
    caption_note = f" caption: {text[:200]!r}" if text else ""

    forensics.capture_source(
        blob, url=url + "/media",
        source_type=SOURCE_TYPE_MEDIA,
        title=f"morskoy/{message.id} media",
        description=(
            f"Media attached to morskoy/{message.id} "
            f"({message.date.date() if message.date else '?'}). "
            f"{BUILDING_NOTE} parent_sha={sha[:12]}.{caption_note}"
        ),
        content_type=ct, http_status=200, con=con,
    )
    return True


def run() -> None:
    try:
        from telethon.sync import TelegramClient
        from telethon.tl.functions.messages import CheckChatInviteRequest
        from telethon.tl.types import ChatInviteAlready
    except ImportError:
        log.error("telethon not installed — run: pip install -e '.[telegram]'")
        return

    if not (config.TELEGRAM_API_ID and config.TELEGRAM_API_HASH):
        log.error("TELEGRAM_API_ID / TELEGRAM_API_HASH not set in .env — aborting")
        return

    con = forensics.open_state()
    client = TelegramClient(
        config.TELEGRAM_SESSION, config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH)
    client.start(phone=config.TELEGRAM_PHONE_NUMBER)
    log.info("telegram session started")

    try:
        # Resolve the private group via invite hash
        invite_info = client(CheckChatInviteRequest(hash=INVITE_HASH))
        if not isinstance(invite_info, ChatInviteAlready):
            log.error(
                "Account is no longer a member of this group (got %s). "
                "Join the group manually first, then re-run.",
                type(invite_info).__name__,
            )
            return

        entity = invite_info.chat
        log.info("resolved group: id=%d title=%r", entity.id, entity.title)

        min_id = _max_captured_id(con, CHANNEL_SLUG)
        log.info(
            "scanning '%s' | window %s → %s | min_id=%d (%s)",
            entity.title, DATE_FROM.date(), DATE_TO.date(), min_id,
            "incremental" if min_id else "first run",
        )

        n = n_media = n_skip_future = 0

        for message in client.iter_messages(
            entity,
            offset_date=DATE_TO + dt.timedelta(seconds=1),
            min_id=min_id,
        ):
            msg_date = message.date
            if msg_date and msg_date.tzinfo is None:
                msg_date = msg_date.replace(tzinfo=dt.timezone.utc)

            if msg_date and msg_date < DATE_FROM:
                log.info(
                    "reached DATE_FROM (%s) at msg id=%d — stopping",
                    DATE_FROM.date(), message.id,
                )
                break

            if msg_date and msg_date > DATE_TO:
                n_skip_future += 1
                continue

            if _capture_message(client, con, CHANNEL_SLUG, message):
                n_media += 1
            n += 1

            if n % 200 == 0:
                log.info(
                    "'%s' … %d messages (%d with media); current date %s",
                    entity.title, n, n_media,
                    msg_date.date() if msg_date else "?",
                )

        log.info(
            "'%s' done — %d messages captured (%d with media); "
            "%d skipped (post-%s)",
            entity.title, n, n_media, n_skip_future, DATE_TO.date(),
        )

    finally:
        client.disconnect()

    stored = con.execute(
        "SELECT COUNT(*) FROM source_document WHERE source_type=?",
        (SOURCE_TYPE_MSG,),
    ).fetchone()[0]
    stored_media = con.execute(
        "SELECT COUNT(*) FROM source_document WHERE source_type=?",
        (SOURCE_TYPE_MEDIA,),
    ).fetchone()[0]
    log.info(
        "store totals: %d %s / %d %s",
        stored, SOURCE_TYPE_MSG, stored_media, SOURCE_TYPE_MEDIA,
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    run()
