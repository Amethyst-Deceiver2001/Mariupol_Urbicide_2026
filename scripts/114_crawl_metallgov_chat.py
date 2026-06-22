#!/usr/bin/env python3
"""Crawl the public Telegram chat "@metallgov" — full history.

Public channel: https://t.me/metallgov

Building/scope NOT assumed — "metallgov" likely abbreviates пр. Металлургов
(cf. script 108/@metalurgov89_91, pid=4550/4551, both demolished), but unlike
that chat this slug has no house numbers, so it may be a wider-scope area
channel covering the whole пр. Металлургов corridor rather than one or two
buildings. пр. Металлургов has dozens of entries on the spine across a wide
range of house numbers and rd4u categories — do not assume a specific pid.

After capture, check the channel-migration service message (msg id=1,
action._=="MessageActionChannelMigrateFrom", action.title) if present, and
profile message content (street/building mentions) to determine scope.

No date cap given — pull full history. If later triage shows a spam-only
tail, narrow DATE_TO in a follow-up run.

Claude must never run this. Run from project root:
    .venv312/bin/python scripts/114_crawl_metallgov_chat.py

Re-runs are incremental.
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

CHANNEL      = "metallgov"
CHANNEL_SLUG = "metallgov"
BUILDING_NOTE = (
    "Channel '@metallgov', Mariupol. Scope NOT YET CONFIRMED — likely "
    "relates to пр. Металлургов but no house numbers in the slug, unlike "
    "the narrower @metalurgov89_91 (pid=4550/4551). May be a wider-scope "
    "area channel. Resolve scope from message content after capture."
)

DATE_FROM = dt.datetime(2018, 1, 1, tzinfo=dt.timezone.utc)
DATE_TO   = dt.datetime.now(dt.timezone.utc)

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


def _captured_id_range(con, slug: str) -> tuple[int, int]:
    """Return (min_id, max_id) of captured messages; (0, 0) if none."""
    prefix = f"https://t.me/{slug}/"
    rows = con.execute(
        "SELECT url FROM source_document WHERE source_type=? AND url LIKE ?",
        (SOURCE_TYPE_MSG, prefix + "%"),
    ).fetchall()
    ids = []
    for (url,) in rows:
        tail = url[len(prefix):].split("/", 1)[0]
        if tail.isdigit():
            ids.append(int(tail))
    if not ids:
        return (0, 0)
    return (min(ids), max(ids))


def _capture_message(client, con, message) -> bool:
    url       = f"https://t.me/{CHANNEL_SLUG}/{message.id}"
    text      = (message.message or "").strip()
    has_media = getattr(message, "media", None) is not None

    sha = forensics.capture_source(
        _serialize(message), url=url,
        source_type=SOURCE_TYPE_MSG,
        title=f"metallgov/{message.id}",
        description=(
            f"Chat post metallgov/{message.id} "
            f"({message.date.isoformat() if message.date else '?'}, "
            f"{'media' if has_media else 'text'}). {BUILDING_NOTE} "
            f"text_len={len(text)}."
        ),
        content_type="application/json", http_status=200, con=con,
    )

    if not has_media:
        return False
    try:
        blob = client.download_media(message, file=bytes)
    except Exception:
        log.exception("media download failed msg id=%d", message.id)
        return False
    if not blob:
        return False

    f    = getattr(message, "file", None)
    mime = getattr(f, "mime_type", None) if f else None
    ct   = mime or ("image/jpeg" if getattr(message, "photo", None) else "application/octet-stream")
    forensics.capture_source(
        blob, url=url + "/media",
        source_type=SOURCE_TYPE_MEDIA,
        title=f"metallgov/{message.id} media",
        description=(
            f"Media attached to metallgov/{message.id} "
            f"({message.date.date() if message.date else '?'}). "
            f"{BUILDING_NOTE} parent_sha={sha[:12]}."
            + (f" caption: {text[:200]!r}" if text else "")
        ),
        content_type=ct, http_status=200, con=con,
    )
    return True


def run() -> None:
    try:
        from telethon.sync import TelegramClient
    except ImportError:
        log.error("telethon not installed")
        return

    if not (config.TELEGRAM_API_ID and config.TELEGRAM_API_HASH):
        log.error("TELEGRAM_API_ID / TELEGRAM_API_HASH not set")
        return

    con    = forensics.open_state()
    client = TelegramClient(
        config.TELEGRAM_SESSION, config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH)
    client.start(phone=config.TELEGRAM_PHONE_NUMBER)
    log.info("session started")

    try:
        entity = client.get_entity(CHANNEL)
        log.info("resolved: id=%d title=%r", entity.id, entity.title)

        captured_min, captured_max = _captured_id_range(con, CHANNEL_SLUG)
        n = n_media = n_skip_future = 0

        # ── Pass 1: forward scan — new messages since last run ────────────────
        log.info("Pass 1 (forward): %s → %s | stop at min_id=%d",
                 DATE_FROM.date(), DATE_TO.date(), captured_max)

        for message in client.iter_messages(
            entity,
            offset_date=DATE_TO + dt.timedelta(seconds=1),
            min_id=captured_max,
        ):
            msg_date = message.date
            if msg_date and msg_date.tzinfo is None:
                msg_date = msg_date.replace(tzinfo=dt.timezone.utc)
            if msg_date and msg_date < DATE_FROM:
                break
            if msg_date and msg_date > DATE_TO:
                n_skip_future += 1
                continue
            if _capture_message(client, con, message):
                n_media += 1
            n += 1
            if n % 500 == 0:
                log.info("pass1 %d msgs (%d media) | %s", n, n_media,
                         msg_date.date() if msg_date else "?")

        log.info("pass1 done — %d messages (%d media)", n, n_media)

        # ── Pass 2: gap-fill — old messages below crash point ─────────────────
        if captured_min > 1:
            log.info("Pass 2 (gap-fill): fetching id < %d", captured_min)
            n2 = n2_media = 0
            for message in client.iter_messages(entity, max_id=captured_min):
                msg_date = message.date
                if msg_date and msg_date.tzinfo is None:
                    msg_date = msg_date.replace(tzinfo=dt.timezone.utc)
                if msg_date and msg_date < DATE_FROM:
                    log.info("gap-fill reached DATE_FROM at id=%d — done", message.id)
                    break
                if _capture_message(client, con, message):
                    n2_media += 1
                n2 += 1
                if n2 % 500 == 0:
                    log.info("gap-fill %d msgs (%d media) | %s", n2, n2_media,
                             msg_date.date() if msg_date else "?")
            log.info("gap-fill done — %d messages (%d media)", n2, n2_media)
            n += n2; n_media += n2_media

        log.info("total this run — %d messages (%d media); %d skipped post-%s",
                 n, n_media, n_skip_future, DATE_TO.date())
    finally:
        client.disconnect()

    for st, label in [(SOURCE_TYPE_MSG, "msg"), (SOURCE_TYPE_MEDIA, "media")]:
        cnt = con.execute(
            "SELECT COUNT(*) FROM source_document WHERE source_type=?", (st,)
        ).fetchone()[0]
        log.info("store total %s: %d", label, cnt)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
