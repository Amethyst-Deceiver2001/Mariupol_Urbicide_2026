#!/usr/bin/env python3
"""Scan @ssaniaworld — text messages only, no media downloads.

Sania Denisova's personal channel. She is a Russian-loyalist but occupation-
critical activist, originally from Penza, now based in Mariupol — already
surfaced once this project's own mining of @mariupol_nash (msg 91318,
2024-08-06, https://t.me/mariupol_nash/91318): she reported organizing
residents whose apartments were demolished or transferred to "bezkhoz" into
filing collective letters with the DNR prosecutor's office. Her own channel is
therefore a plausible primary/first-person source on the ownerless-designation
pipeline's effect on residents, from someone politically aligned with the
occupation but willing to publicly push back on this specific mechanism —
a distinct reliability profile from both purely oppositional and purely
propaganda channels; profile/affiliation not otherwise verified, treat every
claim as a lead until independently corroborated (same standing rule as
scripts/211/212).

Same text-only methodology as scripts/211 (building chats) and scripts/212
(@mariupol_nash): skips client.download_media() entirely so a full-history run
stays small (JSON message objects are ~1-5 KB each). Use scripts/225-style
flag-then-targeted-pull tooling afterward to recover media for any high-value
leads this surfaces, rather than downloading everything up front.

Source-type: "telegram_ssaniaworld_msg" (own namespace, independent
resumability bookkeeping from every other channel this project has crawled).

Claude must never run this (CLAUDE.md) — it hits Telegram, a geoblocked
foreign-state-adjacent service. Run from your own Russia-routed terminal:

    .venv312/bin/python scripts/227_crawl_ssaniaworld_text_only.py
    .venv312/bin/python scripts/227_crawl_ssaniaworld_text_only.py --backfill

Re-runs are incremental (highest captured id used as min_id on next run).
--backfill fetches history older than the lowest captured id.
"""
from __future__ import annotations

import base64
import datetime as _dt
import json
import logging
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

CHANNEL = "ssaniaworld"
SOURCE_TYPE = "telegram_ssaniaworld_msg"
NOTE = ("Sania Denisova's personal channel. Russian-loyalist but "
        "occupation-critical activist (from Penza, based in Mariupol) — "
        "already surfaced organizing collective prosecutor complaints for "
        "bezkhoz/demolished-property owners (see mariupol_nash msg 91318). "
        "Affiliation/reliability not independently profiled beyond that one "
        "cross-reference — treat as first-person commentary/leads, not "
        "primary source, until verified. No spine property_id mapping. "
        "Text-only capture.")


# ---------------------------------------------------------------------------
# serialization helpers (same as telegram_building_chats.py / scripts/212)
# ---------------------------------------------------------------------------

def _json_default(o: Any):
    if isinstance(o, (_dt.datetime, _dt.date)):
        return o.isoformat()
    if isinstance(o, (bytes, bytearray)):
        return base64.b64encode(bytes(o)).decode("ascii")
    if isinstance(o, set):
        return sorted(o)
    return str(o)


def _serialize(message) -> bytes:
    d = message.to_dict()
    return json.dumps(d, ensure_ascii=False, default=_json_default,
                      sort_keys=True, indent=2).encode("utf-8")


# ---------------------------------------------------------------------------
# resumability — keyed off SOURCE_TYPE so fully independent of every other
# channel crawler in this project
# ---------------------------------------------------------------------------

def _max_captured_id(con) -> int:
    prefix = f"https://t.me/{CHANNEL}/"
    rows = con.execute(
        "SELECT url FROM source_document WHERE source_type=? AND url LIKE ?",
        (SOURCE_TYPE, prefix + "%"),
    ).fetchall()
    best = 0
    for (url,) in rows:
        tail = url[len(prefix):].split("/", 1)[0]
        if tail.isdigit():
            best = max(best, int(tail))
    return best


def _min_captured_id(con) -> int:
    prefix = f"https://t.me/{CHANNEL}/"
    rows = con.execute(
        "SELECT url FROM source_document WHERE source_type=? AND url LIKE ?",
        (SOURCE_TYPE, prefix + "%"),
    ).fetchall()
    best = 0
    for (url,) in rows:
        tail = url[len(prefix):].split("/", 1)[0]
        if tail.isdigit():
            v = int(tail)
            best = v if best == 0 else min(best, v)
    return best


# ---------------------------------------------------------------------------
# capture (text only — no media download)
# ---------------------------------------------------------------------------

def _capture_message(con, message) -> None:
    url = f"https://t.me/{CHANNEL}/{message.id}"
    text = (message.message or "").strip()
    has_media = getattr(message, "media", None) is not None
    forensics.capture_source(
        _serialize(message), url=url,
        source_type=SOURCE_TYPE,
        title=f"@{CHANNEL}/{message.id}",
        description=(
            f"@{CHANNEL} post {message.id} "
            f"({message.date.isoformat() if message.date else '?'}, "
            f"{'has_media=True' if has_media else 'text_only'}). "
            f"{NOTE} text_len={len(text)}."
        ),
        content_type="application/json",
        http_status=200, con=con,
    )


# ---------------------------------------------------------------------------
# scan helpers
# ---------------------------------------------------------------------------

def _connect_client():
    from telethon.sync import TelegramClient
    client = TelegramClient(
        config.TELEGRAM_SESSION, config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH)
    client.start(phone=config.TELEGRAM_PHONE_NUMBER)
    return client


def _run_forward(con) -> int:
    """Fetch messages newer than the highest already-captured id."""
    from telethon import errors

    min_id = _max_captured_id(con)
    incremental = min_id > 0
    log.info("@%s forward scan: min_id=%d (%s)", CHANNEL, min_id,
             "incremental" if incremental else "first run — full history")

    client = _connect_client()
    n = 0
    try:
        try:
            entity = client.get_entity(CHANNEL)
        except (errors.UsernameInvalidError, ValueError) as e:
            log.error("channel %r not resolvable: %s", CHANNEL, e)
            return 0

        kwargs: dict[str, Any] = {"min_id": min_id} if incremental else {}
        for message in client.iter_messages(entity, **kwargs):
            _capture_message(con, message)
            n += 1
            if n % 500 == 0:
                log.info("@%s … %d messages captured so far", CHANNEL, n)
    finally:
        client.disconnect()

    log.info("@%s forward scan done — %d messages captured this run", CHANNEL, n)
    return n


def _run_backfill(con) -> int:
    """Fetch history older than the lowest already-captured id."""
    from telethon import errors

    min_id = _min_captured_id(con)
    if min_id == 0:
        log.info("@%s: no prior captures — running full history scan", CHANNEL)
        kwargs: dict[str, Any] = {}
    else:
        log.info("@%s: backfilling below message id %d", CHANNEL, min_id)
        kwargs = {"max_id": min_id}

    client = _connect_client()
    n = 0
    try:
        try:
            entity = client.get_entity(CHANNEL)
        except (errors.UsernameInvalidError, ValueError) as e:
            log.error("channel %r not resolvable: %s", CHANNEL, e)
            return 0

        for message in client.iter_messages(entity, **kwargs):
            _capture_message(con, message)
            n += 1
            if n % 500 == 0:
                log.info("@%s backfill … %d messages so far", CHANNEL, n)
    finally:
        client.disconnect()

    log.info("@%s backfill done — %d messages captured this run", CHANNEL, n)
    return n


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    ap = argparse.ArgumentParser()
    ap.add_argument("--backfill", action="store_true",
                    help="Fetch history OLDER than the lowest already-captured id")
    args = ap.parse_args()

    if not (config.TELEGRAM_API_ID and config.TELEGRAM_API_HASH):
        log.error("TELEGRAM_API_ID / TELEGRAM_API_HASH not set in .env — aborting")
        sys.exit(1)

    try:
        import telethon  # noqa: F401
    except ImportError:
        log.error("telethon not installed — run: pip install -e '.[telegram]'")
        sys.exit(1)

    con = forensics.open_state()

    if args.backfill:
        _run_backfill(con)
    else:
        _run_forward(con)

    total_stored = con.execute(
        "SELECT COUNT(*) FROM source_document WHERE source_type=?", (SOURCE_TYPE,)
    ).fetchone()[0]
    log.info("total %s artifacts in store: %d", SOURCE_TYPE, total_stored)
