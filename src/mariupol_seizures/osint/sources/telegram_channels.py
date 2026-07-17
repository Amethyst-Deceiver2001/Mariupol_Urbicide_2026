"""Source 2 — Telegram in-channel server-side search (all known channels).

Middle Telegram tier (design §budget): telethon's per-channel `search=`
does a FULL-history server-side search of each known channel — including
channels this project only text-crawled partially, and the fwd-graph
channels never crawled at all. NOT budget-limited (unlike global search),
so it runs every ranked variant against every known channel. Captures each
matching message via forensics.capture_source (source_type
'osint_telegram_channel_hit').

RUN=U: hits the live Telegram API — the user runs this from their own
terminal (standing rule), not Claude. Skips cleanly if telethon/creds
absent.
"""
from __future__ import annotations

import base64
import datetime as _dt
import json
import logging

from ... import config, forensics
from .base import SourceResult

log = logging.getLogger(__name__)

NAME = "telegram_channels"
RUN = "U"
NETWORK = True
DESCRIPTION = "in-channel server-side search across all known channels (free, unbudgeted)"

# Known channels: the resale/classified set from config + the primary
# property-seizure / memorial / official channels this project tracks.
# Extend freely — @username without the @.
KNOWN_CHANNELS = sorted(set(config.TELEGRAM_CHANNELS) | {
    "mariupolnow", "mariupolRIP", "kadryVoynyMariypol2022", "mariupol_nash",
    "ssaniaworld", "allmarinews", "mrpl_besxozxata", "mizodnr", "donurcenter",
    "russkiy_mariupol", "novosti_mariupol", "mariupol_helping",
    "morgun_ov", "nmrpl", "mariupolskiy_uezd",
    # discovered 2026-07-17 via telegram_global message-search hits across the
    # ЖК Нахимовский cluster sweep (5 addresses) — outside KNOWN_CHANNELS
    # until now despite novosti_mariupol1/mariupol24tv/mrpl_ctzn already
    # being cited as primary sources elsewhere in this project (the TASS
    # Моргун bezkhoz statements, the Овсиенко compensation-via-bezkhoz
    # quote — see docs/legal_mechanisms_review.md); mrplSprotyv surfaced a
    # named-victim hit with an exact spine-address match (Зелинского 17А)
    # and looks like an occupation-resistance/victim-tracking channel not
    # previously in this project's chat corpus at all.
    "mrplSprotyv", "novosti_mariupol1", "mariupol24tv", "mrpl_ctzn",
    "NickolayOsychenko",
})
MAX_VARIANTS = 6           # top-ranked variants only (in-channel search is cheap but not free)
MAX_HITS_PER_CHANNEL = 40


def plan(bundle) -> str:
    return (f"telethon search= over {len(KNOWN_CHANNELS)} channels × "
            f"top {MAX_VARIANTS} variants, capture matches")


def _serialize(message) -> bytes:
    def default(o):
        if isinstance(o, (_dt.datetime, _dt.date)):
            return o.isoformat()
        if isinstance(o, (bytes, bytearray)):
            return base64.b64encode(bytes(o)).decode("ascii")
        return str(o)
    return json.dumps(message.to_dict(), ensure_ascii=False, default=default,
                      sort_keys=True).encode("utf-8")


def fetch(bundle, con, radius_m: float = 0.0) -> SourceResult:
    if not (config.TELEGRAM_API_ID and config.TELEGRAM_API_HASH):
        return SourceResult(NAME, True, "skipped — TELEGRAM_API_ID/HASH not set")
    try:
        from telethon.sync import TelegramClient
        from telethon import errors
    except ImportError:
        return SourceResult(NAME, True, "skipped — telethon not installed")

    # most-specific typed variants first; dedup the raw query strings
    queries: list[str] = []
    for v in bundle.variants:
        if v.text not in queries:
            queries.append(v.text)
        if len(queries) >= MAX_VARIANTS:
            break

    findings: list[dict] = []
    captured: list[str] = []
    client = TelegramClient(config.TELEGRAM_SESSION, config.TELEGRAM_API_ID,
                            config.TELEGRAM_API_HASH)
    client.start(phone=config.TELEGRAM_PHONE_NUMBER)
    seen_ids: set[str] = set()
    try:
        for channel in KNOWN_CHANNELS:
            try:
                entity = client.get_entity(channel)
            except (errors.UsernameInvalidError, ValueError, errors.RPCError) as e:
                log.debug("channel %s not resolvable: %s", channel, e)
                continue
            hits_here = 0
            for q in queries:
                if hits_here >= MAX_HITS_PER_CHANNEL:
                    break
                try:
                    for msg in client.iter_messages(entity, search=q, limit=20):
                        key = f"{channel}/{msg.id}"
                        if key in seen_ids:
                            continue
                        seen_ids.add(key)
                        url = f"https://t.me/{channel}/{msg.id}"
                        sha = forensics.capture_source(
                            _serialize(msg), url=url,
                            source_type="osint_telegram_channel_hit",
                            title=f"@{channel}/{msg.id}",
                            description=(f"In-channel search hit for {q!r} "
                                         f"(pid={bundle.pid}); "
                                         f"{msg.date.isoformat() if msg.date else '?'}."),
                            content_type="application/json", http_status=200, con=con,
                        )
                        captured.append(sha)
                        findings.append({
                            "kind": "telegram_channel_hit", "channel": channel,
                            "query": q, "url": url,
                            "date": msg.date.strftime("%Y-%m-%d") if msg.date else "",
                            "excerpt": (msg.message or "")[:200].replace("\n", " | "),
                        })
                        hits_here += 1
                except errors.RPCError as e:
                    log.debug("search failed %s %r: %s", channel, q, e)
    finally:
        client.disconnect()

    channels_hit = len({f["channel"] for f in findings})
    return SourceResult(NAME, True,
                        f"{len(findings)} hits across {channels_hit} channels "
                        f"({len(queries)} variants × {len(KNOWN_CHANNELS)} channels)",
                        findings, captured)
