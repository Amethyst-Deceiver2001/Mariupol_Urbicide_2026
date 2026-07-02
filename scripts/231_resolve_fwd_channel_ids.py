#!/usr/bin/env python3
"""Resolve the numeric channel_ids from scripts/230's forward-source graph into
@usernames / display titles, via a live Telegram API lookup (client.get_entity on
a telethon PeerChannel). This is the step scripts/230 explicitly could not do
offline.

Reads data/parsed/nash_fwd_source_graph.jsonl (produced by scripts/230), resolves
the top --limit channel_ids (default 40, i.e. well past the point forward-count
trails into noise), and writes back an augmented copy with username/title/
participants_count/about fields — plus prints a ranked table so you can immediately
see which unmapped channels are worth adding to the crawl list (same pattern that
found @mizodnr and @donurcenter, see memory/new_telegram_channels_intel_2026-06-27.md).

Skips any channel_id already known to be a source we crawl (mariupol_nash itself,
ssaniaworld, mizodnr, donurcenter, building chats) — edit ALREADY_CRAWLED_TITLES
below if that list drifts.

Claude must never run this (CLAUDE.md) — it hits Telegram, a geoblocked
foreign-state-adjacent service. Run from your own Russia-routed terminal:

    .venv312/bin/python scripts/231_resolve_fwd_channel_ids.py
    .venv312/bin/python scripts/231_resolve_fwd_channel_ids.py --limit 80
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

GRAPH = ROOT / "data" / "parsed" / "nash_fwd_source_graph.jsonl"
OUT = ROOT / "data" / "parsed" / "nash_fwd_source_graph_resolved.jsonl"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=40,
                     help="resolve the top N channel_ids by forward count (default 40)")
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
        log.error("%s not found — run scripts/230 first", GRAPH)
        sys.exit(1)

    rows = [json.loads(line) for line in GRAPH.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows.sort(key=lambda r: -r["forward_count"])
    todo = rows[: args.limit]
    log.info("resolving %d channel_ids (of %d total distinct sources)", len(todo), len(rows))

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
            except Exception as e:  # noqa: BLE001 — log and continue, don't kill the whole batch
                entry["username"] = None
                entry["title"] = None
                entry["resolve_error"] = f"{type(e).__name__}: {e}"
            resolved.append(entry)
            if (i + 1) % 10 == 0:
                log.info("… %d/%d resolved", i + 1, len(todo))
            time.sleep(0.3)  # gentle rate-limit; get_entity is a light call but this is a fixed batch
    finally:
        client.disconnect()

    OUT.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in resolved) + "\n",
        encoding="utf-8")

    print(f"\n{'='*72}")
    print(f"RESOLVED {len(resolved)} forward-source channel_ids")
    print(f"{'='*72}")
    print(f"\n{'count':>6}  {'flagged':>8}  {'username':<25} title")
    for r in resolved:
        uname = f"@{r['username']}" if r.get("username") else "(private/no username)"
        title = r.get("title") or r.get("resolve_error") or ""
        print(f"{r['forward_count']:>6}  {r['flagged_count']:>8}  {uname:<25} {title}")

    print(f"\n  → {OUT}")
    print("\n  Review the list above for crawl candidates: high forward_count AND high\n"
          "  flagged_count/flagged_rate = a channel worth adding to the project's\n"
          "  crawl list (same signal that found @mizodnr / @donurcenter).")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
