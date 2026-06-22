#!/usr/bin/env python3
"""Crawl the private Telegram chat at invite https://t.me/+SWCkzbFpPJBkODBi.

Building identity unknown at script-authoring time — this invite hash has not
been resolved yet. Likely covers the бул. Шевченко / ул. Котляревского
intersection area, per user context. ул. Котляревского has 6 entries on the
spine (pid=4920/4921/4922/4923/4924/6110); бул. Шевченко has many entries
incl. pid=4399 (д.74, scripts 116) and pid=4401/4402 (д.77/79, scripts
89/91). Do not assume a specific pid — after capture, check msg id=1 (or
the earliest MessageService with action._=="MessageActionChannelMigrateFrom")
for the group's original title, the same way "Б-р Шевченко 77, 79" and
"Группа БАХЧИВАНДЖИ 13-17" were resolved for other invite-hash chats.

If the account is not yet a member of this chat, CheckChatInviteRequest will
return a (non-"already joined") invite preview and this script will log the
title from that preview without capturing messages — join manually first via
the Telegram app, then re-run.

No date cap given — pull full history. If later triage shows a spam-only
tail, narrow DATE_TO in a follow-up run.

Claude must never run this. Run from project root:
    .venv312/bin/python scripts/117_crawl_invite_SWCkzbFpPJBkODBi.py

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

INVITE_HASH  = "SWCkzbFpPJBkODBi"
CHANNEL_SLUG = "invite_SWCkzbFpPJBkODBi"  # placeholder — rename once building is identified
BUILDING_NOTE = (
    "Residents' chat resolved from invite https://t.me/+SWCkzbFpPJBkODBi. "
    "Likely бул. Шевченко / ул. Котляревского intersection area. "
    "Building/pid mapping NOT YET IDENTIFIED — review earliest messages and "
    "the channel-migration service message (msg id=1, action.title) after "
    "first capture to determine the subject building(s)."
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


def _capture_message(client, con, slug: str, message) -> bool:
    url       = f"https://t.me/{slug}/{message.id}"
    text      = (message.message or "").strip()
    has_media = getattr(message, "media", None) is not None

    sha = forensics.capture_source(
        _serialize(message), url=url,
        source_type=SOURCE_TYPE_MSG,
        title=f"{slug}/{message.id}",
        description=(
            f"Resident chat post {slug}/{message.id} "
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
        title=f"{slug}/{message.id} media",
        description=(
            f"Media attached to {slug}/{message.id} "
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
        from telethon.tl.functions.messages import CheckChatInviteRequest
        from telethon.tl.types import ChatInviteAlready
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
        info = client(CheckChatInviteRequest(hash=INVITE_HASH))
        if not isinstance(info, ChatInviteAlready):
            title = getattr(info, "title", None)
            log.error(
                "not a member yet (got %s, title=%r) — join manually in the "
                "Telegram app first, then re-run this script",
                type(info).__name__, title,
            )
            return

        entity = info.chat
        log.info("resolved: id=%d title=%r — UPDATE CHANNEL_SLUG/BUILDING_NOTE "
                  "in this script once the subject building is identified",
                  entity.id, entity.title)

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
            if _capture_message(client, con, CHANNEL_SLUG, message):
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
                if _capture_message(client, con, CHANNEL_SLUG, message):
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
