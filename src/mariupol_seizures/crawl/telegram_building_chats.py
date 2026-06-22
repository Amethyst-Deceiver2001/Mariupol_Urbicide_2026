"""Stage 1k: scan Telegram building-resident chats for siege/occupation evidence.

Claude must never run this — see CLAUDE.md. The user runs it; it uses the user's
Telegram credentials (config.TELEGRAM_*, from .env) and a persisted login session
(the same one created by scripts/50).

WHY THIS EXISTS
---------------
scripts/50 scans mixed-content resale classifieds and only downloads media that
passes an apartment-sale text filter. A building-specific resident chat (e.g.
@Lenina133, for property_id 4442 / просп. Ленина (Мира), 133) is a different
animal: every message and every photo is potential evidence for THAT property —
pre-war baseline, siege damage, post-siege state, occupation-era notices — so this
scanner captures messages AND media unconditionally, with no apartment-sale gate
and no date floor (full history by default).

FORENSICS (CLAUDE.md, non-negotiable)
-------------------------------------
- Capture before parse. Each message is serialized verbatim (Telethon
  `message.to_dict()` -> canonical JSON) and written to data/raw/ SHA-256-keyed
  with a .meta.json custody sidecar BEFORE any filtering.
  url = https://t.me/<channel>/<id>.
- source_type = "telegram_building_chat_msg" / "telegram_building_chat_media",
  distinct from scripts/50's "telegram_channel_msg" / "telegram_channel_media" so
  the two scan types never collide in resumability bookkeeping.
- These are resident first-person posts — primary-source, dated, but not
  independently audited. Treat per docs/tier3_corroboration_design.md (S5,
  testimony_ref) when loading into corroboration.

RESUMABILITY
------------
Per channel we record the highest message id already captured (derived from the
source_document URLs for that source_type+channel — no new schema) and fetch only
id > that on the next run.

USAGE
-----
    pip install -e '.[telegram]'        # first time, if not already done
    python3 scripts/62_crawl_lenina133_chat.py
    python3 scripts/62_crawl_lenina133_chat.py SomeOtherBuildingChat
"""
from __future__ import annotations

import base64
import datetime as _dt
import json
import logging
import os
from typing import Any

from .. import config, forensics

log = logging.getLogger(__name__)

# First-run history bound (per channel). Building chats are usually small enough
# that this is just a safety cap, not a real constraint. Re-runs are incremental.
HISTORY_LIMIT = int(os.environ.get("TELEGRAM_BUILDING_CHAT_HISTORY_LIMIT", "20000"))


def _json_default(o: Any):
    if isinstance(o, (_dt.datetime, _dt.date)):
        return o.isoformat()
    if isinstance(o, (bytes, bytearray)):
        return base64.b64encode(bytes(o)).decode("ascii")
    if isinstance(o, set):
        return sorted(o)
    return str(o)  # last resort: never let one odd field abort a capture


def _serialize(message) -> bytes:
    d = message.to_dict()
    return json.dumps(d, ensure_ascii=False, default=_json_default,
                       sort_keys=True, indent=2).encode("utf-8")


def _max_captured_id(con, channel: str) -> int:
    """Highest message id already captured for this channel (0 if none)."""
    prefix = f"https://t.me/{channel}/"
    rows = con.execute(
        "SELECT url FROM source_document WHERE source_type='telegram_building_chat_msg' "
        "AND url LIKE ?", (prefix + "%",),
    ).fetchall()
    best = 0
    for (url,) in rows:
        tail = url[len(prefix):].split("/", 1)[0]
        if tail.isdigit():
            best = max(best, int(tail))
    return best


def _has_media(message) -> bool:
    return getattr(message, "media", None) is not None


def _media_content_type(message) -> str:
    f = getattr(message, "file", None)
    mime = getattr(f, "mime_type", None) if f is not None else None
    if mime:
        return mime
    if getattr(message, "photo", None) is not None:
        return "image/jpeg"
    return "application/octet-stream"


def _list_topics(client, entity) -> list:
    """Enumerate forum topics (paginated). Includes the 'General' topic."""
    from telethon.tl.functions.messages import GetForumTopicsRequest

    topics: list = []
    offset_date = 0
    offset_id = 0
    offset_topic = 0
    while True:
        result = client(GetForumTopicsRequest(
            peer=entity, offset_date=offset_date, offset_id=offset_id,
            offset_topic=offset_topic, limit=100,
        ))
        if not result.topics:
            break
        topics.extend(result.topics)
        if len(result.topics) < 100:
            break
        msg_by_id = {m.id: m for m in result.messages}
        last = result.topics[-1]
        offset_topic = last.id
        offset_id = last.top_message
        last_msg = msg_by_id.get(last.top_message)
        offset_date = int(last_msg.date.timestamp()) if last_msg and last_msg.date else 0
    return topics


def _capture_message(client, con, channel: str, message, building_note: str,
                      topic_title: str | None = None) -> bool:
    """Capture one message (+ its media, if any). Returns True if it had media."""
    url = f"https://t.me/{channel}/{message.id}"
    text = (message.message or "").strip()
    has_media = _has_media(message)
    topic_note = f" topic={topic_title!r}." if topic_title else ""
    sha = forensics.capture_source(
        _serialize(message), url=url,
        source_type="telegram_building_chat_msg",
        title=f"@{channel}/{message.id}" + (f" [{topic_title}]" if topic_title else ""),
        description=(f"Resident chat post @{channel}/{message.id} "
                      f"({message.date.isoformat() if message.date else '?'}, "
                      f"{'media' if has_media else 'text'}).{topic_note} {building_note} "
                      f"text_len={len(text)}."),
        content_type="application/json",
        http_status=200, con=con,
    )

    if not has_media:
        return False

    try:
        blob = client.download_media(message, file=bytes)
    except Exception:  # noqa: BLE001
        log.exception("media download failed for %s", url)
        return False
    if not blob:
        return False

    ct = _media_content_type(message)
    caption_note = f" caption: {text[:200]!r}" if text else ""
    forensics.capture_source(
        blob, url=url + "/media",
        source_type="telegram_building_chat_media",
        title=f"@{channel}/{message.id} media" + (f" [{topic_title}]" if topic_title else ""),
        description=(f"Media attached to {url} ({message.date.date() if message.date else '?'})."
                      f"{topic_note} {building_note} parent msg sha={sha[:12]}.{caption_note}"),
        content_type=ct, http_status=200, con=con,
    )
    return True


def _scan_channel(client, con, channel: str, building_note: str) -> int:
    from telethon import errors  # local import: optional dep
    from telethon.tl.types import Channel as TLChannel

    try:
        entity = client.get_entity(channel)
    except (errors.UsernameInvalidError, ValueError) as e:
        log.error("chat %r not resolvable: %s — skipping", channel, e)
        return 0

    min_id = _max_captured_id(con, channel)
    incremental = min_id > 0
    log.info("scanning @%s (min_id=%d, %s)", channel, min_id,
             "incremental" if incremental else f"first run, up to {HISTORY_LIMIT} messages per topic")

    n = 0
    n_media = 0
    kwargs: dict[str, Any] = {"min_id": min_id} if incremental else {"limit": HISTORY_LIMIT}

    is_forum = isinstance(entity, TLChannel) and getattr(entity, "forum", False)
    if is_forum:
        # Per-topic message ids are not comparable to the global max-id from a
        # prior non-topic-aware scan (a topic can contain ids lower than the
        # highest id seen elsewhere). For a small chat it's cheap to just walk
        # every topic in full each run -- capture_source() is idempotent, so
        # re-seeing an already-stored message/media is a harmless no-op.
        topic_kwargs: dict[str, Any] = {"limit": HISTORY_LIMIT}
        topics = _list_topics(client, entity)
        log.info("@%s is a forum with %d topics", channel, len(topics))
        for topic in topics:
            t_n = 0
            for message in client.iter_messages(entity, reply_to=topic.id, **topic_kwargs):
                if _capture_message(client, con, channel, message, building_note,
                                     topic_title=topic.title):
                    n_media += 1
                n += 1
                t_n += 1
                if n % 200 == 0:
                    log.info("@%s … %d messages (%d media) captured so far", channel, n, n_media)
            log.info("@%s topic %r (id=%d): %d messages", channel, topic.title, topic.id, t_n)
    else:
        for message in client.iter_messages(entity, **kwargs):
            if _capture_message(client, con, channel, message, building_note):
                n_media += 1
            n += 1
            if n % 200 == 0:
                log.info("@%s … %d messages (%d media) captured", channel, n, n_media)

    log.info("@%s done — %d new messages, %d media captured", channel, n, n_media)
    return n


def run(channels: list[str], building_note: str = "") -> None:
    try:
        from telethon.sync import TelegramClient  # noqa: F401
    except ImportError:
        log.error("telethon not installed — run: pip install -e '.[telegram]'")
        return

    if not (config.TELEGRAM_API_ID and config.TELEGRAM_API_HASH):
        log.error("TELEGRAM_API_ID / TELEGRAM_API_HASH not set in .env — aborting")
        return

    con = forensics.open_state()
    from telethon.sync import TelegramClient
    client = TelegramClient(
        config.TELEGRAM_SESSION, config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH)
    client.start(phone=config.TELEGRAM_PHONE_NUMBER)
    log.info("telegram session started (%s)", config.TELEGRAM_SESSION)

    total = 0
    try:
        for ch in channels:
            try:
                total += _scan_channel(client, con, ch, building_note)
            except Exception:  # noqa: BLE001 — one bad chat must not kill the run
                log.exception("chat @%s failed — continuing", ch)
    finally:
        client.disconnect()

    stored = con.execute(
        "SELECT COUNT(*) FROM source_document WHERE source_type='telegram_building_chat_msg'"
    ).fetchone()[0]
    stored_media = con.execute(
        "SELECT COUNT(*) FROM source_document WHERE source_type='telegram_building_chat_media'"
    ).fetchone()[0]
    log.info("done — %d new messages this run; %d telegram_building_chat_msg / "
             "%d telegram_building_chat_media artifacts in store",
             total, stored, stored_media)
