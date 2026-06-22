"""Stage 1j: scan Telegram channels for Mariupol apartment-SALE offers (MTProto).

Claude must never run this — see CLAUDE.md. The user runs it; it uses the user's
Telegram credentials (config.TELEGRAM_*, from .env) and a persisted login session.

WHY THIS EXISTS
---------------
Telegram classified channels are the most liquid resale market for occupied
Mariupol flats — more current than the web marketplaces, and the venue where
seized/rebuilt stock is openly traded ([F] resale; Rome 8(2)(b)(viii) — disposal
of appropriated property to the occupier's population). The channels are
mixed-content (sale / rent / buy / commercial / houses all interleaved); the
SALE-of-residential-apartment filter runs in the parser (scripts/51) — this scanner
captures every message verbatim (capture before parse).

FORENSICS (CLAUDE.md, non-negotiable)
-------------------------------------
- Capture before parse. Each message is serialized verbatim (Telethon
  `message.to_dict()` → canonical JSON) and written to data/raw/ SHA-256-keyed with
  a .meta.json custody sidecar BEFORE any filtering. url = https://t.me/<channel>/<id>.
- These are public market posts, evidence of an open market in occupied-territory
  property — never valid title. A poster may be an agency, a beneficiary reselling
  seized stock, or an innocent departing resident: the parser isolates poster
  contact PII (phone/@username) so shared outputs can minimize private individuals.

RESUMABILITY
------------
Per channel we record the highest message id already captured (derived from the
source_document URLs — no new schema) and fetch only id > that on the next run, so
the scan is incremental. First run walks history newest→oldest, bounded by
TELEGRAM_HISTORY_LIMIT and the config.DATE_FROM date floor.

AUTH
----
First run is interactive: Telethon prompts for the SMS/app login code (and 2FA
password if set) for config.TELEGRAM_PHONE_NUMBER, then writes the session file
(config.TELEGRAM_SESSION, under data/ — gitignored, holds an auth token = secret).
Subsequent runs are non-interactive.

    pip install -e '.[telegram]'        # telethon
    python3 scripts/50_crawl_telegram_channels.py            # all configured channels
    python3 scripts/50_crawl_telegram_channels.py nemariupol # subset
"""
from __future__ import annotations

import base64
import datetime as _dt
import json
import logging
from typing import Any

from .. import config, forensics

log = logging.getLogger(__name__)

# First-run history bound (per channel). Re-runs are incremental and ignore this.
HISTORY_LIMIT = int(__import__("os").environ.get("TELEGRAM_HISTORY_LIMIT", "8000"))


def _date_floor() -> _dt.datetime:
    """Lower date bound for the first-run history walk (config.DATE_FROM, dd.mm.yyyy)."""
    try:
        d = _dt.datetime.strptime(config.DATE_FROM, "%d.%m.%Y")
    except ValueError:
        d = _dt.datetime(2024, 1, 1)
    return d.replace(tzinfo=_dt.timezone.utc)


def _json_default(o: Any):
    """Make Telethon's to_dict() JSON-serializable, losslessly where it matters."""
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
        "SELECT url FROM source_document WHERE source_type='telegram_channel_msg' "
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


def _scan_channel(client, con, channel: str) -> int:
    from telethon import errors  # local import: optional dep

    try:
        entity = client.get_entity(channel)
    except (errors.UsernameInvalidError, ValueError) as e:
        log.error("channel %r not resolvable: %s — skipping", channel, e)
        return 0

    min_id = _max_captured_id(con, channel)
    incremental = min_id > 0
    floor = _date_floor()
    log.info("scanning @%s (min_id=%d, %s)", channel, min_id,
             "incremental" if incremental else f"first run, floor {floor.date()}")

    n = 0
    kwargs: dict[str, Any] = {"min_id": min_id} if incremental else {"limit": HISTORY_LIMIT}
    for message in client.iter_messages(entity, **kwargs):
        # First-run date floor (incremental runs are already bounded by min_id).
        if not incremental and message.date and message.date < floor:
            log.info("@%s reached date floor at id %d (%s) — stopping",
                     channel, message.id, message.date.date())
            break

        url = f"https://t.me/{channel}/{message.id}"
        text = (message.message or "").strip()
        media_flag = "media" if _has_media(message) else "text"
        sha = forensics.capture_source(
            _serialize(message), url=url,
            source_type="telegram_channel_msg",
            title=f"@{channel}/{message.id}",
            description=(f"Telegram post @{channel}/{message.id} "
                        f"({message.date.isoformat() if message.date else '?'}, {media_flag}). "
                        f"Mixed-content classifieds; filter to apartment-sale in scripts/51. "
                        f"text_len={len(text)}."),
            content_type="application/json",
            http_status=200, con=con,
        )
        n += 1

        # Optional media download — bounded by a cheap text prefilter so we only
        # pull photos for likely apartment-sale posts. Full classification is the
        # parser's job; this is just a download gate.
        if (config.TELEGRAM_FETCH_MEDIA and _has_media(message)
                and _looks_like_apartment_sale(text)):
            try:
                blob = client.download_media(message, file=bytes)
                if blob:
                    forensics.capture_source(
                        blob, url=url + "/media",
                        source_type="telegram_channel_media",
                        title=f"@{channel}/{message.id} media",
                        description=f"Photo attached to {url}; parent msg sha={sha[:12]}.",
                        content_type="image/jpeg", http_status=200, con=con,
                    )
            except Exception:  # noqa: BLE001
                log.exception("media download failed for %s", url)

        if n % 200 == 0:
            log.info("@%s … %d messages captured", channel, n)

    log.info("@%s done — %d new messages captured", channel, n)
    return n


# Cheap pre-filter ONLY to gate optional media downloads. Authoritative
# classification (sell vs rent vs buy, apartment vs other) is in scripts/51.
import re as _re  # noqa: E402

_SALE_HINT = _re.compile(
    r"продам|продаж|прода[её]тся|продаю|к\s*продаж", _re.IGNORECASE)
_APT_HINT = _re.compile(
    r"\bквартир|\bкв\.?\b|студи|[1-4]\s*-?\s*к\b|комнатн", _re.IGNORECASE)


def _looks_like_apartment_sale(text: str) -> bool:
    return bool(text) and bool(_SALE_HINT.search(text)) and bool(_APT_HINT.search(text))


def run(only: list[str] | None = None) -> None:
    try:
        from telethon.sync import TelegramClient  # noqa: F401
    except ImportError:
        log.error("telethon not installed — run: pip install -e '.[telegram]'")
        return

    if not (config.TELEGRAM_API_ID and config.TELEGRAM_API_HASH):
        log.error("TELEGRAM_API_ID / TELEGRAM_API_HASH not set in .env — aborting")
        return

    channels = [c for c in config.TELEGRAM_CHANNELS
                if only is None or c in only]
    if not channels:
        log.error("no matching channels (only=%s)", only)
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
                total += _scan_channel(client, con, ch)
            except Exception:  # noqa: BLE001 — one bad channel must not kill the run
                log.exception("channel @%s failed — continuing", ch)
    finally:
        client.disconnect()

    stored = con.execute(
        "SELECT COUNT(*) FROM source_document WHERE source_type='telegram_channel_msg'"
    ).fetchone()[0]
    log.info("done — %d new this run; %d telegram_channel_msg artifacts in store",
             total, stored)
