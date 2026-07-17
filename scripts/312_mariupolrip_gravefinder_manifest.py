#!/usr/bin/env python3
"""Targeted follow-up to scripts/309/310: flag the "found this grave, does
anyone recognize it" genre of @mariupolRIP post specifically.

Manual review of the first media pull (scripts/310, P1+P2, 1,266 items)
found that this genre has a much higher grave-photo hit rate than the
channel's general obituary posts (which are overwhelmingly portraits of the
deceased, not photos of the grave): 6 of 7 reviewed "found an unidentified
grave, does anyone know who this is" posts had an actual photo of the grave
marker attached, against roughly 4 of 15 for general obituary posts. But
scripts/309's classifier under-ranked this genre -- these posts usually open
with "Могила ..." / "Могилка ..." rather than a victim's own name, so
NAME_START_RE matched the word "Могила" itself as if it were a name, and
DEATH_RE (погиб/умер/похорон/захорон) often doesn't fire at all ("вдруг кто
ищет, проходила мимо, сфотографировала" names no death verb), so most of
this genre landed in scripts/309's weakest priority-3 tier and was not
pulled by a default (--max-priority 2) run of scripts/310.

This script re-scans the full "telegram_mariupolrip_msg" raw store (not just
scripts/309's already-flagged subset) for that specific genre and emits a
small, high-value manifest in the same shape scripts/310 already consumes.

Read-only, local, no network.

    PYTHONPATH=src python scripts/312_mariupolrip_gravefinder_manifest.py

Then pull with (Claude must NEVER run this step -- see scripts/310):
    .venv312/bin/python scripts/310_pull_mariupolrip_flagged_media.py \\
        --manifest data/parsed/mariupolrip_gravefinder_manifest.jsonl --max-priority 3
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402

log = logging.getLogger(__name__)

SOURCE_TYPE = "telegram_mariupolrip_msg"
OUT_FILE = ROOT / "data" / "parsed" / "mariupolrip_gravefinder_manifest.jsonl"

GRAVEFINDER_RE = re.compile(
    r"^могил\w*|^есть\s+могил|^найдена?\s+могил|сфотографировал\w*\s+могил|"
    r"сфотографировал\w*\s+(?:это\s+)?место\s+захоронени|"
    r"вдруг\s+кто[\- ]?(?:то\s+)?ищет|может\s+кто[\- ]?(?:то\s+)?ищет|кто[\- ]?то\s+ищет|"
    r"если\s+кто\s+ищет|кто\s+знает\s+отзов|прошу\s+отклик|"
    r"нужна\s+любая\s+информация\s+по\s+поводу\s+данной\s+могил",
    re.IGNORECASE,
)


def _media_info(obj) -> tuple[str, int | None]:
    m = obj.get("media")
    if not m:
        return "none", None
    t = m.get("_")
    if t == "MessageMediaPhoto":
        return "photo", None
    if t == "MessageMediaDocument":
        doc = m.get("document") or {}
        mime = doc.get("mime_type") or ""
        size = doc.get("size")
        if mime.startswith("video/"):
            return "video", size
        if mime.startswith("audio/"):
            return "audio", size
        return "document", size
    return t.replace("MessageMedia", "").lower() if t else "none", None


def main() -> None:
    con = sqlite3.connect(config.STATE_DB)
    rows = con.execute(
        "SELECT url, raw_path FROM source_document WHERE source_type=? ORDER BY url",
        (SOURCE_TYPE,),
    ).fetchall()
    log.info("scanning %d %s messages for the gravefinder genre", len(rows), SOURCE_TYPE)

    hits = []
    media_hits = 0
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
        text = (obj.get("message") or "").strip()
        if not text or not GRAVEFINDER_RE.search(text):
            continue
        msg_id = url.rstrip("/").rsplit("/", 1)[-1]
        date = (obj.get("date") or "")[:10]
        media_kind, media_size = _media_info(obj)
        hits.append({
            "msg_id": msg_id, "url": url, "date": date,
            "media_kind": media_kind, "media_size_bytes": media_size,
            "pull_priority": 1,  # this whole manifest IS the high-priority set
            "note": "gravefinder-genre post (scripts/312)",
            "text": text[:300],
        })
        if media_kind != "none":
            media_hits += 1

    hits.sort(key=lambda r: r["msg_id"])

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w", encoding="utf-8") as f:
        for r in hits:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\n{'='*72}")
    print(f"GRAVEFINDER-GENRE MANIFEST — {len(hits)} matching messages, {media_hits} carry media")
    print(f"{'='*72}")
    for r in hits:
        marker = "MEDIA" if r["media_kind"] != "none" else "    -"
        print(f"  [{marker}] {r['url']:<38} {r['text'][:90]}")
    print(f"\n  written -> {OUT_FILE}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
