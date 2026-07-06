#!/usr/bin/env python3
"""Keyword-triage survey of the ~205,000 messages captured by scripts/262 —
the 15 second-order channels (4 district управы, official DNR ministries
@minstroydnr/@rosreestr80/@prav_dnr/etc, named officials @KoltsovAnton/
@mkhusnullin). Same methodology as scripts/247-249/258: local, offline, no
network -- reads
each message's raw JSON via source_document, extracts the `message` text
field, and greps it against the project's property/seizure keyword list.

This is a TRIAGE pass, not analysis: most of this volume will be non-property
chatter (weather, ads, local news) exactly like the archive sweep found for
administrative decrees. Flags candidates worth an individual read.

Run:
    python3 scripts/263_survey_2ndorder_channels.py
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

STATE_DB = ROOT / "data" / "state.sqlite"
OUT_PATH = ROOT / "data" / "parsed" / "2ndorder_survey.jsonl"

KEYWORDS = [
    "Мариуполь", "Мариуполя", "Мариуполю",
    "бесхозя", "изъят", "снос", "аварийны", "маневренн",
    "земельного участка", "инвестиционного проекта", "без проведения торгов",
    "муниципальной собственности", "государственной собственности",
    "ипотек", "многоквартирн", "жилищн", "выселен", "компенсаци",
    "ЕГРН", "кадастров", "инвентаризац", "незавершенного строительства",
    "квартир", "дом снес", "переселен", "расселен",
]
KEYWORD_RE = re.compile("|".join(re.escape(k) for k in KEYWORDS))


def main() -> None:
    con = sqlite3.connect(STATE_DB)
    cur = con.cursor()
    cur.execute("""
        SELECT sha256, url, raw_path, source_type FROM source_document
        WHERE source_type LIKE 'telegram_2ndorder_%'
    """)
    rows = cur.fetchall()
    print(f"{len(rows)} messages to survey", file=sys.stderr)

    hits = 0
    empty = 0
    by_channel_hits: dict[str, int] = {}
    with open(OUT_PATH, "w", encoding="utf-8") as out:
        for i, (sha, url, raw_path, source_type) in enumerate(rows, 1):
            if i % 10000 == 0:
                print(f"  {i}/{len(rows)}...", file=sys.stderr)
            try:
                d = json.loads(Path(raw_path).read_text(encoding="utf-8"))
            except Exception as e:
                out.write(json.dumps({"sha256": sha, "url": url, "error": str(e)}, ensure_ascii=False) + "\n")
                continue
            text = (d.get("message") or "").strip()
            if len(text) < 5:
                empty += 1
                continue
            matched_kw = sorted(set(KEYWORD_RE.findall(text)))
            if matched_kw:
                hits += 1
                by_channel_hits[source_type] = by_channel_hits.get(source_type, 0) + 1
                out.write(json.dumps({
                    "sha256": sha, "url": url, "source_type": source_type,
                    "date": d.get("date"), "text_len": len(text),
                    "keywords": matched_kw,
                    "has_media": d.get("media") is not None,
                    "fwd_from": bool(d.get("fwd_from")),
                    "first_300": text[:300],
                }, ensure_ascii=False) + "\n")

    print(f"\nDone. {hits} keyword hits, {empty} empty/too-short, "
          f"index written to {OUT_PATH}", file=sys.stderr)
    print("Hits by channel:", file=sys.stderr)
    for st, n in sorted(by_channel_hits.items(), key=lambda x: -x[1]):
        print(f"  {st}: {n}", file=sys.stderr)


if __name__ == "__main__":
    main()
