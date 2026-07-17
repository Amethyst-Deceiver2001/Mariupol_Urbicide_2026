"""Source 3 — Telegram global post search (budgeted: 10/day via ledger).

Top Telegram tier (design §budget): discovers UNKNOWN channels mentioning
the address. Premium global post search is capped at ~10 queries/day, so
this spends the ledger (osint.ledger) on only the 1-3 top-ranked variants,
and only after the local + in-channel tiers have run.

The exact TL primitive for Premium *public* global post search is
layer-dependent and not guaranteed available on every account; this module
tries telethon's SearchGlobalRequest (messages across dialogs) +
contacts.SearchRequest (public channel/username discovery) as a best
effort, records each spend in the ledger, and — crucially — documents the
zero-API FALLBACK the design specifies: the user runs the N searches in the
Telegram app by hand and forwards hits to a private intake channel, which a
standard 317-pattern crawler ingests with full provenance. No API guesswork
needed for that path.

RUN=U, budgeted. Refuses past the daily cap (ledger.spend_or_raise).
"""
from __future__ import annotations

import base64
import datetime as _dt
import json
import logging

import os

from ... import config, forensics
from ..ledger import DAILY_BUDGETS, record, remaining_today
from .base import SourceResult

log = logging.getLogger(__name__)

NAME = "telegram_global"
RUN = "U"
NETWORK = True
DESCRIPTION = f"global post search — DISCOVERS unknown channels (budget {DAILY_BUDGETS['telegram_global']}/day)"

LEDGER_SOURCE = "telegram_global"
# Was a hardcoded 3 — fine for ONE isolated address, but a multi-address
# cluster sweep (nearby addresses share ~150m radius, so their variant
# queries are near-duplicates likely to surface the same channels anyway)
# drains the shared 10/day budget after only ~3 properties, leaving the
# rest of the cluster with zero telegram_global coverage that day
# (observed 2026-07-17 running the 5-address ЖК Нахимовский cluster: budget
# went 10->7->4->1 across just 3 properties). Default down to 1/run;
# override via env for a genuine single-address deep dive.
MAX_QUERIES_PER_RUN = int(os.environ.get("TELEGRAM_GLOBAL_MAX_QUERIES", "1"))


def plan(bundle) -> str:
    return (f"top {MAX_QUERIES_PER_RUN} variant(s) via SearchGlobal + contacts.Search, "
            f"ledger-gated (override: TELEGRAM_GLOBAL_MAX_QUERIES env var); "
            f"else intake-channel fallback")


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
        from telethon import functions, errors, types
    except ImportError:
        return SourceResult(NAME, True, "skipped — telethon not installed")

    rem = remaining_today(con, LEDGER_SOURCE)
    if rem is not None and rem <= 0:
        return SourceResult(NAME, True,
                            f"budget exhausted for today (0/{DAILY_BUDGETS[LEDGER_SOURCE]}) "
                            "— queue persists, re-run tomorrow; or use the "
                            "intake-channel fallback (see module docstring)")

    queries: list[str] = []
    for v in bundle.variants:
        if v.kind == "typed" and v.text not in queries:
            queries.append(v.text)
        if len(queries) >= min(MAX_QUERIES_PER_RUN, rem or MAX_QUERIES_PER_RUN):
            break

    findings: list[dict] = []
    captured: list[str] = []
    client = TelegramClient(config.TELEGRAM_SESSION, config.TELEGRAM_API_ID,
                            config.TELEGRAM_API_HASH)
    client.start(phone=config.TELEGRAM_PHONE_NUMBER)
    try:
        for q in queries:
            record(con, LEDGER_SOURCE, q, {"pid": bundle.pid})
            # (A) discover public channels by name/username
            try:
                res = client(functions.contacts.SearchRequest(q=q, limit=15))
                for chat in getattr(res, "chats", []):
                    uname = getattr(chat, "username", None)
                    findings.append({
                        "kind": "telegram_discovered_channel", "query": q,
                        "title": getattr(chat, "title", ""),
                        "username": uname,
                        "url": f"https://t.me/{uname}" if uname else "",
                    })
            except errors.RPCError as e:
                log.debug("contacts.Search failed %r: %s", q, e)
            # (B) global message search across the account's reachable dialogs
            try:
                res = client(functions.messages.SearchGlobalRequest(
                    q=q, filter=types.InputMessagesFilterEmpty(),
                    min_date=None, max_date=None,
                    offset_rate=0, offset_peer=types.InputPeerEmpty(),
                    offset_id=0, limit=20))
                id_to_username = {}
                for chat in getattr(res, "chats", []):
                    id_to_username[chat.id] = getattr(chat, "username", None)
                for msg in getattr(res, "messages", []):
                    peer = getattr(msg, "peer_id", None)
                    cid = getattr(peer, "channel_id", None)
                    uname = id_to_username.get(cid)
                    url = (f"https://t.me/{uname}/{msg.id}" if uname
                           else f"tg://msg?id={msg.id}")
                    sha = forensics.capture_source(
                        _serialize(msg), url=url,
                        source_type="osint_telegram_global_hit",
                        title=f"global-search hit {q!r}",
                        description=(f"Telegram global post-search hit for {q!r} "
                                     f"(pid={bundle.pid})."),
                        content_type="application/json", http_status=200, con=con,
                    )
                    captured.append(sha)
                    findings.append({
                        "kind": "telegram_global_hit", "query": q,
                        "channel": uname or "", "url": url,
                        "excerpt": (getattr(msg, "message", "") or "")[:200].replace("\n", " | "),
                    })
            except (errors.RPCError, TypeError, ValueError) as e:
                log.warning("SearchGlobal failed %r: %s — use intake-channel "
                            "fallback for this query", q, e)
                findings.append({"kind": "global_search_unavailable", "query": q,
                                 "error": str(e),
                                 "fallback": "run this search in the Telegram app, "
                                             "forward hits to your intake channel, "
                                             "then crawl it (317-pattern)"})
    finally:
        client.disconnect()

    rem_after = remaining_today(con, LEDGER_SOURCE)
    n_disc = sum(1 for f in findings if f["kind"] == "telegram_discovered_channel")
    n_hit = sum(1 for f in findings if f["kind"] == "telegram_global_hit")
    return SourceResult(NAME, True,
                        f"{len(queries)} queries spent ({rem_after}/"
                        f"{DAILY_BUDGETS[LEDGER_SOURCE]} left today); "
                        f"{n_disc} channels discovered, {n_hit} message hits",
                        findings, captured)
