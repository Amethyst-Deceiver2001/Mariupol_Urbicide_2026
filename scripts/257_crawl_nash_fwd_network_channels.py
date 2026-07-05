#!/usr/bin/env python3
"""Scan the highest-signal UNCRAWLED channels from @mariupol_nash's forward-source
graph (scripts/230 built the graph, scripts/231 resolved channel_ids -> usernames,
data/parsed/nash_fwd_source_graph_resolved.jsonl). This is the next step of the
same discovery method that originally found @mizodnr and @donurcenter
(memory/new_telegram_channels_intel_2026-06-27.md) — generalized here into a
one-shot crawl of everything the graph surfaced that this project hasn't touched
yet, instead of investigating candidates one at a time.

Cross-checked 2026-07-06 against every channel this project already crawls
(building chats, @mariupol_nash, @ssaniaworld, @mizodnr, @donurcenter,
@mrpl_besxozxata, @nmrpl, and named advocate/realtor channels) — the 26
channels below are genuinely new. Ranked by a mix of forward_count (volume)
and flagged_rate (scripts/225's property/seizure keyword hit rate among this
channel's messages, as forwarded into @mariupol_nash) into three tiers:

  TIER 1 (default set — run these first): named officials' personal channels
  (Иващенко, Моргун, Пушилин — all in the stakeholder network already), the
  official Орджоникидзевский district admin channel (@ordjonikidzadmin, same
  shape as the already-good @mizodnr/@nmrpl finds), and the two
  highest-flagged-rate general channels (@mariupol_po_faktu at 0.160,
  @solntsev_official at 0.087).

  TIER 2: secondary signal (flagged_rate 0.02-0.04) — district gossip/announce
  channels, @Nash_Mariupol (NOTE: distinct username from the already-crawled
  @mariupol_nash — word order swapped, verify not a rebrand/duplicate before
  reading results as "new" intel), @CHYORNYY_SPISOK, @infrMariupol.

  TIER 3 (--all only): everything else the graph surfaced (music/photo/humor/
  sports/university channels) — low flagged_rate, included for completeness,
  not expected to be high-value.

Also surfaced 8 channels with NO resolvable username (private, or
resolve_error) that forward heavily into @mariupol_nash, including PRIVATE
district channels for exactly the 4 districts already central to this
project's court-layer analysis (Жовтневый, Ильичёвский, Орджоникидзевский,
Приморский) plus "БЮРО — Подслушано в Мариуполе" (forward_count 3278,
flagged_rate 0.151 — second-highest flag rate in the whole graph). These
CANNOT be crawled without an invite link (Telethon's get_entity needs a
username or a resolved invite hash) — worth hunting for an invite link to
these specifically, given the flag rates involved. Printed as a reminder at
the end of every run; not crawled by this script.

Same text-only methodology as scripts/211/212/227/234: skips
client.download_media() so a full-history run stays small. Each channel gets
its own source_type namespace (telegram_fwdnet_<username>_msg) and
independent forward/backfill resumability, same pattern as every other
per-channel crawler in this project.

Claude must never run this (CLAUDE.md) — it hits Telegram, a geoblocked
foreign-state-adjacent service. Run from your own Russia-routed terminal:

    .venv312/bin/python scripts/257_crawl_nash_fwd_network_channels.py
    .venv312/bin/python scripts/257_crawl_nash_fwd_network_channels.py --tier 2
    .venv312/bin/python scripts/257_crawl_nash_fwd_network_channels.py --all
    .venv312/bin/python scripts/257_crawl_nash_fwd_network_channels.py --channel ordjonikidzadmin
    .venv312/bin/python scripts/257_crawl_nash_fwd_network_channels.py --backfill   # any of the above + backfill

Re-runs are incremental per channel (highest captured id used as min_id).
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

# username -> (title, forward_count, flagged_rate, tier)
CHANNELS: dict[str, tuple[str, int, float, int]] = {
    # ---- Tier 1: named officials + strongest signal ----
    "ivashchenko_kv":     ("Константин Иващенко (former врио Head, Mariupol admin)", 565, 0.039, 1),
    "morgun_ov":          ("Олег Моргун (Mariupol admin chain)", 144, 0.014, 1),
    "PushilinDenis":      ("Пушилин Д.В. (personal channel, distinct from denis-pushilin.ru site)", 433, 0.021, 1),
    "ordjonikidzadmin":   ("УПРАВА ОРДЖОНИКИДЗЕВСКОГО ВНУТРИГОРОДСКОГО РАЙОНА ГОРОДА МАРИУПОЛЬ (official district admin)", 220, 0.032, 1),
    "mariupol_po_faktu":  ("МАРИУПОЛЬ ПО ФАКТУ (highest flagged_rate in the graph)", 144, 0.160, 1),
    "solntsev_official":  ("Евгений Солнцев", 115, 0.087, 1),

    # ---- Tier 2: secondary signal ----
    "Nash_Mariupol":      ("Наш Мариуполь (NOTE: distinct from already-crawled @mariupol_nash -- verify not a duplicate/rebrand)", 5593, 0.014, 2),
    "CHYORNYY_SPISOK":    ("ЧЁРНЫЙ СПИСОК - МАРИУПОЛЬ", 584, 0.031, 2),
    "infrMariupol":       ("Инфраструктура Мариуполя", 438, 0.027, 2),
    "Mangush_Podslushano": ("Подслушано в Мангуше", 102, 0.039, 2),

    # ---- Tier 3: low signal, completeness only ----
    "Mariupol_Photograph": ("ФОТО. МАРИУПОЛЬ. ДОНЕЦК. ДНР", 2194, 0.002, 3),
    "Mariupol_Kultura":   ("КУЛЬТУРА. МАРИУПОЛЬ", 573, 0.010, 3),
    "black_pirat_news":   ("Black Pirate News", 521, 0.017, 3),
    "Mariupol_Media":     ("МУЗЫКА. МАРИУПОЛЬ. ДОНЕЦК. ДНР.", 495, 0.014, 3),
    "Svyatoy_Matros":     ("Святой Матрос", 373, 0.019, 3),
    "TLenamrpl":          ("Тётя Лена", 307, 0.003, 3),
    "Mariupol_Yumor":     ("ЮМОР", 290, 0.003, 3),
    "ZV_MRPL":            ("ZV езда Мариуполь", 231, 0.000, 3),
    "rusgorod":           ("Русский город", 213, 0.019, 3),
    "khartsyz":           ("ХАРЦЫЗ | Большой Харцызск для жителей Донбасса", 189, 0.005, 3),
    "marmgu":             ("Мариупольский государственный университет имени А.И. Куинджи", 120, 0.017, 3),
    "Papochki_ru":        ("ПАПОЧКИ", 115, 0.000, 3),
    "yagodkin_d":         ("ОБЪЕКТИВ ЯГОДКИНА", 114, 0.018, 3),
    "sport_dlya_vsekh_Mariupol": ("МБУ МГЦФЗН \"СПОРТ ДЛЯ ВСЕХ\" г.о.Мариуполь", 108, 0.009, 3),
    "molodoy_mrpl":       ("Мариуполь Молодой", 100, 0.000, 3),
    "gorizont_mariupol":  ("Образовательное пространство \"Горизонт успеха\"", 98, 0.000, 3),
}

# Heavily-forwarding sources with NO resolvable username -- cannot be crawled
# without an invite link. Printed as a reminder, not crawled.
PRIVATE_UNRESOLVED = [
    ("Донецкая Губерния", 5233, 0.025),
    ("БЮРО — Подслушано в Мариуполе", 3278, 0.151),
    ("(resolve_error, no title)", 1466, 0.005),
    ("МАМОЧКИ. МАРИУПОЛЬ", 655, 0.011),
    ("Мариуполь Наш", 455, 0.013),
    ("МАШИНА. МАРИУПОЛЬ. ДОНЕЦК. ДНР", 257, 0.031),
    ("(resolve_error, no title)", 219, 0.009),
    ("Орджоникидзевский район — Мариуполь", 142, 0.141),
    ("НЕДВИЖИМОСТЬ. МАРИУПОЛЬ", 138, 0.051),
    ("Приморский район — Мариуполь", 132, 0.114),
    ("ТОРГОВЛЯ. МАРИУПОЛЬ. ДОНЕЦК. ДНР.", 124, 0.000),
    ("Ильичёвский район — Мариуполь", 117, 0.128),
    ("РАБОТА. МАРИУПОЛЬ", 106, 0.000),
    ("Жовтневый район — Мариуполь", 96, 0.115),
]


# ---------------------------------------------------------------------------
# serialization helpers (same as scripts/211/212/227/234)
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
    return f"telegram_fwdnet_{channel.lower()}_msg"


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
            f"Found via @mariupol_nash forward-source graph (scripts/230/231). "
            f"{note} text_len={len(text)}."
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
                     help="crawl only this tier (default: tiers 1+2)")
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
        targets = [c for c, (_, _, _, t) in CHANNELS.items() if t == args.tier]
    else:
        targets = [c for c, (_, _, _, t) in CHANNELS.items() if t in (1, 2)]

    log.info("crawling %d channel(s): %s", len(targets), ", ".join(targets))

    total_this_run = 0
    for channel in targets:
        title, forward_count, flagged_rate, tier = CHANNELS[channel]
        note = f"Tier {tier}, forward_count={forward_count}, flagged_rate={flagged_rate}. {title}."
        total_this_run += _scan_channel(channel, note, args.backfill)

    print(f"\n{'='*72}")
    print(f"crawl_nash_fwd_network_channels: {total_this_run} messages captured this run "
          f"across {len(targets)} channel(s)")
    print(f"{'='*72}")

    if not args.channel:
        print("\nReminder: these forward-source channels have NO resolvable username and "
              "cannot be crawled without an invite link. Worth hunting for one, especially "
              "the two highest flag rates:")
        for title, fc, fr in sorted(PRIVATE_UNRESOLVED, key=lambda x: -x[2]):
            print(f"  flagged_rate={fr:.3f}  forward_count={fc:>5}  {title}")


if __name__ == "__main__":
    main()
