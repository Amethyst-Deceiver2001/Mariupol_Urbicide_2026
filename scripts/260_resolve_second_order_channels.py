#!/usr/bin/env python3
"""Resolve the top candidate channel_ids from scripts/259's second-order
forward-source graph into @usernames/titles, via a live Telegram API lookup
(client.get_entity on a telethon PeerChannel) -- same technique as
scripts/231, applied one hop further out: scripts/230/231 mapped who
forwards INTO @mariupol_nash; scripts/259 mapped who forwards into all 26
channels scripts/257 crawled; this resolves THAT larger candidate list.

Automatically excludes channel_ids already resolved in
data/parsed/nash_fwd_source_graph_resolved.jsonl (the first-order graph) --
of 2,365 distinct channel_ids scripts/259 found, only 40 are already known,
leaving ~2,325 unresolved. This script resolves the top --limit of those
(default 40, well past the point forward-count trails into noise) and prints
a ranked table, same format as scripts/231.

Claude must never run this (CLAUDE.md) — it hits Telegram, a geoblocked
foreign-state-adjacent service. Run from your own Russia-routed terminal:

    .venv312/bin/python scripts/260_resolve_second_order_channels.py
    .venv312/bin/python scripts/260_resolve_second_order_channels.py --limit 80
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402

log = logging.getLogger(__name__)

GRAPH = ROOT / "data" / "parsed" / "fwdnet_second_order_graph.jsonl"
FIRST_ORDER_RESOLVED = ROOT / "data" / "parsed" / "nash_fwd_source_graph_resolved.jsonl"
OUT = ROOT / "data" / "parsed" / "fwdnet_second_order_graph_resolved.jsonl"


def _already_known_ids() -> set[str]:
    known = set()
    if FIRST_ORDER_RESOLVED.exists():
        for line in FIRST_ORDER_RESOLVED.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            known.add(str(row.get("channel_id")))
    return known


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=40,
                     help="resolve the top N unresolved channel_ids by forward count (default 40)")
    args = ap.parse_args()

    if not (config.TELEGRAM_API_ID and config.TELEGRAM_API_HASH):
        log.error("TELEGRAM_API_ID / TELEGRAM_API_HASH not set in .env — aborting")
        sys.exit(1)

    try:
        from telethon.sync import TelegramClient
        from telethon.tl.types import PeerChannel
        from telethon import errors
    except ImportError:
        log.error("telethon not installed — run: pip install -e '.[telegram]'")
        sys.exit(1)

    if not GRAPH.exists():
        log.error("%s not found — run scripts/259 first", GRAPH)
        sys.exit(1)

    known = _already_known_ids()
    rows = [json.loads(line) for line in GRAPH.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = [r for r in rows if r["channel_id"] not in known]
    rows.sort(key=lambda r: -r["forward_count"])
    todo = rows[: args.limit]
    log.info("resolving %d channel_ids (of %d unresolved, %d already known excluded)",
              len(todo), len(rows), len(known))

    client = TelegramClient(config.TELEGRAM_SESSION, config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH)
    client.start(phone=config.TELEGRAM_PHONE_NUMBER)

    resolved = []
    try:
        for i, row in enumerate(todo):
            channel_id = int(row["channel_id"])
            entry = dict(row)
            try:
                entity = client.get_entity(PeerChannel(channel_id))
                entry["username"] = getattr(entity, "username", None)
                entry["title"] = getattr(entity, "title", None)
                entry["participants_count"] = getattr(entity, "participants_count", None)
                entry["broadcast"] = getattr(entity, "broadcast", None)
                entry["megagroup"] = getattr(entity, "megagroup", None)
                entry["resolve_error"] = None
            except (errors.ChannelPrivateError, errors.ChannelInvalidError) as e:
                entry["username"] = None
                entry["title"] = None
                entry["resolve_error"] = f"{type(e).__name__}: {e}"
            except Exception as e:  # noqa: BLE001
                entry["username"] = None
                entry["title"] = None
                entry["resolve_error"] = f"{type(e).__name__}: {e}"
            resolved.append(entry)
            if (i + 1) % 10 == 0:
                log.info("… %d/%d resolved", i + 1, len(todo))
            time.sleep(0.3)
    finally:
        client.disconnect()

    OUT.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in resolved) + "\n",
        encoding="utf-8")

    print(f"\n{'='*72}")
    print(f"RESOLVED {len(resolved)} second-order forward-source channel_ids")
    print(f"{'='*72}")
    print(f"\n{'count':>6}  {'flagged/via':>6}  {'username':<25} title")
    for r in resolved:
        uname = f"@{r['username']}" if r.get("username") else "(private/no username)"
        title = r.get("title") or r.get("resolve_error") or ""
        print(f"{r['forward_count']:>6}  {len(r.get('seen_via_source_types', [])):>6}  {uname:<25} {title}")

    print(f"\n  → {OUT}")
    print("\n  Review for crawl candidates -- high forward_count AND seen via many\n"
          "  DIFFERENT source channels (not just one chatty repost bot) is the\n"
          "  strongest signal, same as scripts/231's original find.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
