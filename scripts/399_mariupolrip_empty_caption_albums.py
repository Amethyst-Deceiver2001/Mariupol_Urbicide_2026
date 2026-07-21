#!/usr/bin/env python3
"""Detect @mariupolRIP grouped photo albums whose caption is EMPTY -- a
structural blind spot in the whole scripts/309/311/312 flagging pipeline,
which keys entirely off message TEXT. Telegram sometimes carries an album's
caption/name-plaque content only in the photo pixels (a close-up of a grave
marker, e.g.) with every grouped message's `.message` field blank, as found
2026-07-21 reviewing the Грушевского 10/12 courtyard site: the companion
4-photo album at t.me/mariupolRIP/16611-16614 (grouped_id 13208641807002994)
named a 4th victim (Головина Марина) invisible to every text classifier
because none of the 4 grouped messages carried any caption text at all.

This script finds every OTHER grouped album in the full mariupolRIP scan
with the same shape (grouped_id set, message text empty on every member) so
they can be queued for the same photo-download-and-visual-read treatment as
scripts/397 applied by hand to 16611-16614 -- rather than staying invisible
until a user happens to notice one by chance.

Read-only, local, no network.

    PYTHONPATH=src python scripts/399_mariupolrip_empty_caption_albums.py
"""
from __future__ import annotations

import json
import logging
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402

log = logging.getLogger(__name__)

SOURCE_TYPE = "telegram_mariupolrip_msg"
OUT = ROOT / "data" / "parsed" / "mariupolrip_empty_caption_albums.jsonl"


def main() -> None:
    con = sqlite3.connect(config.STATE_DB)
    rows = con.execute(
        "SELECT url, raw_path FROM source_document WHERE source_type=? ORDER BY url",
        (SOURCE_TYPE,),
    ).fetchall()
    log.info("scanning %d %s messages for empty-caption grouped albums", len(rows), SOURCE_TYPE)

    albums: dict[int, list[dict]] = defaultdict(list)
    n_msg = 0
    for url, raw_path in rows:
        if not raw_path:
            continue
        p = ROOT / raw_path
        if not p.exists():
            continue
        try:
            obj = json.loads(p.read_bytes())
        except Exception:
            continue
        if obj.get("_") != "Message":
            continue
        n_msg += 1
        gid = obj.get("grouped_id")
        if gid is None:
            continue
        msg_id = url.rstrip("/").rsplit("/", 1)[-1]
        albums[gid].append({
            "msg_id": msg_id, "url": url,
            "date": (obj.get("date") or "")[:10],
            "message": (obj.get("message") or "").strip(),
            "has_media": bool(obj.get("media")),
        })

    log.info("%d messages scanned, %d distinct grouped_id albums found", n_msg, len(albums))

    empty_albums = []
    for gid, members in albums.items():
        if not all(m["has_media"] for m in members):
            continue  # only interested in all-photo albums
        if any(m["message"] for m in members):
            continue  # at least one member has caption text -- already flaggable
        members.sort(key=lambda m: int(m["msg_id"]))
        empty_albums.append({
            "grouped_id": gid,
            "n_photos": len(members),
            "first_url": members[0]["url"],
            "date": members[0]["date"],
            "msg_ids": [m["msg_id"] for m in members],
        })

    empty_albums.sort(key=lambda a: a["date"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for a in empty_albums:
            f.write(json.dumps(a, ensure_ascii=False) + "\n")

    print(f"\n{len(empty_albums)} empty-caption grouped albums found "
          f"(invisible to scripts/309/311/312's text classifiers)")
    print(f"total photos across them: {sum(a['n_photos'] for a in empty_albums)}")
    print(f"written -> {OUT}")
    print("\nfirst 20, oldest first (each needs the scripts/397-style manual "
          "photo-fetch + visual read to recover any names/addresses):")
    for a in empty_albums[:20]:
        print(f"  {a['date']}  {a['first_url']}  ({a['n_photos']} photos)")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
