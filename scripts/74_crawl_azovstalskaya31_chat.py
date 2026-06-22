#!/usr/bin/env python3
"""Crawl the @Azovstalskaya31 Telegram resident chat — 2022-01-01 to 2023-12-31 only.

Property: ул. Азовстальская, 31 — pid=6259 in the spine.
Seizure stage on record: demolition (minstroy_demolition_register).
The Азовстальская corridor has the highest ownerless-registry concentration in the
dataset (536 apartments). д.31 was demolished rather than title-stripped — resident
posts from the siege and immediate occupation period are the primary evidence target.
Content after 2023 is predominantly spam; this script caps at 2023-12-31.

Claude must never run this (CLAUDE.md). Run from project root with:

    .venv312/bin/python scripts/74_crawl_azovstalskaya31_chat.py

First run is non-interactive if data/telegram_session already exists (scripts/50
created it). Re-runs are incremental (skips already-stored message ids).

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

CHANNEL = "Azovstalskaya31"
BUILDING_NOTE = (
    "property_id=6259, ул. Азовстальская, 31, Mariupol. "
    "Seizure stage: demolition (minstroy_demolition_register). "
    "Азовстальская corridor: 536 ownerless-registry events across street."
)

# Date window: siege + first occupation year only; post-2023 is spam
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


def _max_captured_id(con, channel: str) -> int:
    """Highest message id already captured for this channel (0 if none)."""
    prefix = f"https://t.me/{channel}/"
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


def _capture_message(client, con, channel: str, message) -> bool:
    """Capture one message + its media. Returns True if media was present."""
    url  = f"https://t.me/{channel}/{message.id}"
    text = (message.message or "").strip()
    has_media = getattr(message, "media", None) is not None

    sha = forensics.capture_source(
        _serialize(message), url=url,
        source_type=SOURCE_TYPE_MSG,
        title=f"@{channel}/{message.id}",
        description=(
            f"Resident chat post @{channel}/{message.id} "
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
        log.exception("media download failed for %s", url)
        return False
    if not blob:
        return False

    f = getattr(message, "file", None)
    mime = getattr(f, "mime_type", None) if f else None
    ct = mime or ("image/jpeg" if getattr(message, "photo", None) else "application/octet-stream")
    caption_note = f" caption: {text[:200]!r}" if text else ""

    forensics.capture_source(
        blob, url=url + "/media",
        source_type=SOURCE_TYPE_MEDIA,
        title=f"@{channel}/{message.id} media",
        description=(
            f"Media attached to {url} ({message.date.date() if message.date else '?'}). "
            f"{BUILDING_NOTE} parent_sha={sha[:12]}.{caption_note}"
        ),
        content_type=ct, http_status=200, con=con,
    )
    return True


def run() -> None:
    try:
        from telethon.sync import TelegramClient
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
    log.info("telegram session started (%s)", config.TELEGRAM_SESSION)

    try:
        from telethon import errors
        try:
            entity = client.get_entity(CHANNEL)
        except (errors.UsernameInvalidError, ValueError) as e:
            log.error("channel %r not resolvable: %s", CHANNEL, e)
            return

        min_id = _max_captured_id(con, CHANNEL)
        log.info(
            "scanning @%s | window %s → %s | min_id=%d (%s)",
            CHANNEL, DATE_FROM.date(), DATE_TO.date(), min_id,
            "incremental" if min_id else "first run",
        )

        n = n_media = n_skip_old = n_skip_future = 0

        # offset_date tells Telethon to start fetching from just before DATE_TO
        # (default direction is newest-first), so we iterate backwards through
        # the date window and break as soon as we pass DATE_FROM.
        for message in client.iter_messages(
            entity,
            offset_date=DATE_TO + dt.timedelta(seconds=1),
            min_id=min_id,
        ):
            msg_date = message.date
            if msg_date and msg_date.tzinfo is None:
                msg_date = msg_date.replace(tzinfo=dt.timezone.utc)

            # Messages arrive newest-first; once we pass DATE_FROM we're done
            if msg_date and msg_date < DATE_FROM:
                log.info("reached DATE_FROM (%s) at msg id=%d — stopping", DATE_FROM.date(), message.id)
                break

            # Sanity guard: skip anything newer than DATE_TO (shouldn't occur
            # given offset_date, but defend against Telethon edge cases)
            if msg_date and msg_date > DATE_TO:
                n_skip_future += 1
                continue

            if _capture_message(client, con, CHANNEL, message):
                n_media += 1
            n += 1

            if n % 200 == 0:
                log.info(
                    "@%s … %d messages (%d with media) captured; "
                    "current date %s",
                    CHANNEL, n, n_media,
                    msg_date.date() if msg_date else "?",
                )

        log.info(
            "@%s done — %d messages captured (%d with media); "
            "%d skipped (pre-%s); %d skipped (post-%s)",
            CHANNEL, n, n_media,
            n_skip_old, DATE_FROM.date(),
            n_skip_future, DATE_TO.date(),
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
