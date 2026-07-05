#!/usr/bin/env python3
"""Crawl the highest-value channels surfaced by the second-order
forward-source graph (scripts/259/260) plus the 3 remaining Mariupol
district channels the user found and joined manually (2026-07-06):
@ilichevskiy, @mariupol_primorskiy, @zhovtnevyy -- these complete the set of
4 city districts alongside @ordjonikidzadmin (Орджоникидзевский, already
crawled via scripts/257).

Also includes the strongest official-channel candidates from the
second-order resolution (scripts/260's output), ranked by how directly they
bear on the property-seizure pipeline:

  TIER 1 (default): the 3 new district channels; @KoltsovAnton (Anton
  Koltsov, the CURRENT head of Mariupol -- already in the stakeholder
  network, personal channel not yet crawled); @rosreestr80 (official DNR
  Rosreestr channel -- direct primary-source registry announcements);
  @minstroydnr (official DNR Ministry of Construction -- runs the
  demolition/ownerless-registry framework); @news_oktyabrskiy (a second,
  possibly-official Жовтневый district channel, distinct from @zhovtnevyy --
  crawl both, reconcile once read).

  TIER 2 (--tier 2 or --all): top-level DNR executive channels (@AG_DPR,
  @prav_dnr) and two named stakeholder-network figures/entities
  (@rks_nr -- ООО "РКС-НР", already a known demolition-contractor chain link;
  @mkhusnullin -- Marat Khusnullin, federal deputy PM overseeing
  reconstruction, already named in the stakeholder network but this is his
  personal channel).

  TIER 3 (--all only): other official DNR ministry channels found in the
  same batch (@mtspdnr Минтруд, @mzdnr_official Минздрав, @minobrnauki_dnr,
  @merdnr Минэкономразвития) -- lower direct relevance to property seizure
  but still official primary-source channels, included for completeness.

Same text-only capture methodology as scripts/211/212/227/234/257; each
channel gets its own source_type namespace and independent resumability.

Claude must never run this (CLAUDE.md) — it hits Telegram, a geoblocked
foreign-state-adjacent service. Run from your own Russia-routed terminal:

    .venv312/bin/python scripts/262_crawl_second_order_channels.py
    .venv312/bin/python scripts/262_crawl_second_order_channels.py --tier 2
    .venv312/bin/python scripts/262_crawl_second_order_channels.py --all
    .venv312/bin/python scripts/262_crawl_second_order_channels.py --channel KoltsovAnton
"""
from __future__ import annotations

import argparse
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

# username -> (title, note, tier)
CHANNELS: dict[str, tuple[str, str, int]] = {
    # ---- Tier 1: district channels + strongest official finds ----
    "ilichevskiy":        ("Ильичёвский район", "One of the 3 remaining district channels, found/joined by user 2026-07-06", 1),
    "mariupol_primorskiy": ("Приморский район", "One of the 3 remaining district channels, found/joined by user 2026-07-06", 1),
    "zhovtnevyy":         ("Жовтневый район", "One of the 3 remaining district channels, found/joined by user 2026-07-06", 1),
    "news_oktyabrskiy":   ("Управа Жовтневого внутригородского района", "Possibly a SECOND, official Жовтневый channel distinct from @zhovtnevyy -- crawl both, reconcile once read", 1),
    "KoltsovAnton":       ("Антон Кольцов, глава Мариуполя", "Current head of Mariupol (already in stakeholder network) -- personal channel", 1),
    "rosreestr80":        ("Управление Росреестра по ДНР", "Official DNR Rosreestr channel -- direct primary-source registry announcements", 1),
    "minstroydnr":        ("МИНСТРОЙ ДНР", "Official DNR Ministry of Construction -- runs the demolition/ownerless-registry framework", 1),

    # ---- Tier 2: top-level DNR executive + named stakeholder figures ----
    "AG_DPR":             ("Администрация Главы ДНР", "Top-level DNR executive channel", 2),
    "prav_dnr":           ("Правительство ДНР", "DNR government channel", 2),
    "rks_nr":             ("ООО \"РКС-НР\"", "Already a known demolition-contractor chain link (Roskapstroy) in the stakeholder network", 2),
    "mkhusnullin":        ("Марат Хуснуллин", "Federal deputy PM overseeing reconstruction, already named in stakeholder network -- personal channel", 2),

    # ---- Tier 3: other official DNR ministry channels ----
    "mtspdnr":            ("МИНТРУД ДНР", "DNR Ministry of Labor -- lower direct relevance, included for completeness", 3),
    "mzdnr_official":     ("Минздрав ДНР", "DNR Ministry of Health -- lower direct relevance", 3),
    "minobrnauki_dnr":    ("Министерство образования и науки ДНР", "DNR Ministry of Education -- lower direct relevance", 3),
    "merdnr":             ("Минэкономразвития ДНР", "DNR Ministry of Economic Development -- lower direct relevance", 3),
}


# ---------------------------------------------------------------------------
# serialization helpers (same as scripts/211/212/227/234/257)
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


def _source_type(channel: str) -> str:
    return f"telegram_2ndorder_{channel.lower()}_msg"


def _max_captured_id(con, channel: str) -> int:
    source_type = _source_type(channel)
    prefix = f"https://t.me/{channel}/"
    rows = con.execute(
        "SELECT url FROM source_document WHERE source_type=? AND url LIKE ?",
        (source_type, prefix + "%"),
    ).fetchall()
    best = 0
    for (url,) in rows:
        tail = url[len(prefix):].split("/", 1)[0]
        if tail.isdigit():
            best = max(best, int(tail))
    return best


def _min_captured_id(con, channel: str) -> int:
    source_type = _source_type(channel)
    prefix = f"https://t.me/{channel}/"
    rows = con.execute(
        "SELECT url FROM source_document WHERE source_type=? AND url LIKE ?",
        (source_type, prefix + "%"),
    ).fetchall()
    best = 0
    for (url,) in rows:
        tail = url[len(prefix):].split("/", 1)[0]
        if tail.isdigit():
            v = int(tail)
            best = v if best == 0 else min(best, v)
    return best


def _capture_message(con, channel: str, note: str, message) -> None:
    url = f"https://t.me/{channel}/{message.id}"
    text = (message.message or "").strip()
    has_media = getattr(message, "media", None) is not None
    forensics.capture_source(
        _serialize(message), url=url,
        source_type=_source_type(channel),
        title=f"@{channel}/{message.id}",
        description=(
            f"@{channel} post {message.id} "
            f"({message.date.isoformat() if message.date else '?'}, "
            f"{'has_media=True' if has_media else 'text_only'}). "
            f"Found via @mariupol_nash forward-network second-order graph "
            f"(scripts/259/260) or direct user discovery. {note} text_len={len(text)}."
        ),
        content_type="application/json",
        http_status=200, con=con,
    )


def _connect_client():
    from telethon.sync import TelegramClient
    client = TelegramClient(
        config.TELEGRAM_SESSION, config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH)
    client.start(phone=config.TELEGRAM_PHONE_NUMBER)
    return client


def _scan_channel(channel: str, note: str, backfill: bool) -> int:
    from telethon import errors

    con = forensics.open_state()
    client = _connect_client()
    n = 0
    try:
        try:
            entity = client.get_entity(channel)
        except (errors.UsernameInvalidError, errors.ChannelPrivateError, ValueError) as e:
            log.error("@%s not resolvable: %s -- skipping", channel, e)
            return 0

        if backfill:
            min_id = _min_captured_id(con, channel)
            kwargs: dict[str, Any] = {} if min_id == 0 else {"max_id": min_id}
            log.info("@%s backfill: %s", channel,
                      "first run — full history" if min_id == 0 else f"below id {min_id}")
        else:
            min_id = _max_captured_id(con, channel)
            kwargs = {"min_id": min_id} if min_id > 0 else {}
            log.info("@%s forward scan: min_id=%d (%s)", channel, min_id,
                      "incremental" if min_id > 0 else "first run — full history")

        for message in client.iter_messages(entity, **kwargs):
            _capture_message(con, channel, note, message)
            n += 1
            if n % 500 == 0:
                log.info("  @%s … %d messages captured so far", channel, n)
    finally:
        client.disconnect()

    log.info("@%s done — %d messages captured this run", channel, n)
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", type=int, choices=[1, 2, 3], default=None,
                     help="crawl only this tier (default: tier 1)")
    ap.add_argument("--all", action="store_true", help="crawl all tiers including tier 3")
    ap.add_argument("--channel", default=None, help="crawl just this one channel (username, no @)")
    ap.add_argument("--backfill", action="store_true",
                     help="fetch history OLDER than the lowest already-captured id, per channel")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if not (config.TELEGRAM_API_ID and config.TELEGRAM_API_HASH):
        log.error("TELEGRAM_API_ID / TELEGRAM_API_HASH not set in .env — aborting")
        sys.exit(1)
    try:
        import telethon  # noqa: F401
    except ImportError:
        log.error("telethon not installed — run: pip install -e '.[telegram]'")
        sys.exit(1)

    if args.channel:
        if args.channel not in CHANNELS:
            log.error("unknown channel %r -- not in this run's candidate list", args.channel)
            sys.exit(1)
        targets = [args.channel]
    elif args.all:
        targets = list(CHANNELS)
    elif args.tier:
        targets = [c for c, (_, _, t) in CHANNELS.items() if t == args.tier]
    else:
        targets = [c for c, (_, _, t) in CHANNELS.items() if t == 1]

    log.info("crawling %d channel(s): %s", len(targets), ", ".join(targets))

    total_this_run = 0
    for channel in targets:
        title, note, tier = CHANNELS[channel]
        full_note = f"Tier {tier}. {title} -- {note}."
        total_this_run += _scan_channel(channel, full_note, args.backfill)

    print(f"\n{'='*72}")
    print(f"crawl_second_order_channels: {total_this_run} messages captured this run "
          f"across {len(targets)} channel(s)")
    print(f"{'='*72}")


if __name__ == "__main__":
    main()
