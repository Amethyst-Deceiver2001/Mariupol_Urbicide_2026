#!/usr/bin/env python3
"""Second-order expansion of the @mariupol_nash forward-source network.

scripts/230 built a forward-source graph over @mariupol_nash alone and found
26 new channels (crawled by scripts/257). This script generalizes that same
technique across ALL 26 of those newly-crawled channels (plus the older
@ssaniaworld/@nmrpl/@mizodnr/@donurcenter/@mrpl_besxozxata channels this
project already mines) to see who THEY forward from — a channel that never
forwards into @mariupol_nash directly could still be one hop further out,
reachable only through e.g. @ordjonikidzadmin or @morgun_ov's own forwards.

Pure local analysis: reads already-captured JSON via source_document rows
only. No network, no writes to data/raw or the DB. Excludes channel_ids
already known to belong to a channel this project crawls (best-effort, by
title keyword match against KNOWN_TITLES below -- Telethon's fwd_from only
carries a numeric channel_id, never a @username, so exact identity can't be
confirmed offline; scripts/231's resolve step, run by the user, is still the
final word on any candidate this script surfaces).

Run:
    python3 scripts/259_fwdnet_second_order_graph.py
"""
from __future__ import annotations

import json
import logging
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import forensics  # noqa: E402

log = logging.getLogger(__name__)

OUT_JSONL = ROOT / "data" / "parsed" / "fwdnet_second_order_graph.jsonl"

SOURCE_TYPE_PREFIXES = (
    "telegram_fwdnet_",   # the 26 channels from scripts/257
    "telegram_nash_msg",  # @mariupol_nash itself
    "telegram_ssaniaworld_msg", "telegram_nmrpl_msg",
)

# Best-effort title-based de-dup against channels this project already crawls
# (see scripts/231's ALREADY_CRAWLED_TITLES docstring note -- same idea,
# applied here since we now have many more known titles to check against).
KNOWN_TITLES = {
    "мариупольский вестник", "мизо днр", "донурцентр", "безхозхата",
    "наш мариуполь", "ssaniaworld", "нмрпл", "мариуполь по факту",
    "чёрный список", "иващенко", "моргун", "пушилин", "солнцев",
    "инфраструктура мариуполя", "подслушано в мангуше", "управа орджоникидзевского",
}


def _title_known(title: str | None) -> bool:
    if not title:
        return False
    t = title.lower()
    return any(k in t for k in KNOWN_TITLES)


def main() -> None:
    con = forensics.open_state()
    where = " OR ".join("source_type LIKE ?" for _ in SOURCE_TYPE_PREFIXES)
    params = [f"{p}%" if p.endswith("_") else p for p in SOURCE_TYPE_PREFIXES]
    rows = con.execute(
        f"SELECT source_type, raw_path FROM source_document WHERE {where}", params
    ).fetchall()
    log.info("scanning %d captured messages across %d source_type prefixes",
              len(rows), len(SOURCE_TYPE_PREFIXES))

    channel_counts: Counter = Counter()
    channel_first_seen: dict[str, str] = {}
    channel_last_seen: dict[str, str] = {}
    channel_seen_via: dict[str, set[str]] = defaultdict(set)
    channel_example: dict[str, dict] = {}

    n_total = n_fwd = n_parse_err = 0
    for source_type, raw_path in rows:
        n_total += 1
        p = Path(raw_path)
        if not p.exists():
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            n_parse_err += 1
            continue

        fwd = d.get("fwd_from")
        if not fwd:
            continue
        n_fwd += 1

        from_id = fwd.get("from_id") or {}
        channel_id = from_id.get("channel_id") if isinstance(from_id, dict) else None
        if channel_id is None:
            continue

        key = str(channel_id)
        date = (d.get("date") or "")[:10]
        channel_counts[key] += 1
        channel_seen_via[key].add(source_type)
        if key not in channel_first_seen or date < channel_first_seen[key]:
            channel_first_seen[key] = date
        if key not in channel_last_seen or date > channel_last_seen[key]:
            channel_last_seen[key] = date
        if key not in channel_example:
            channel_example[key] = {"msg_id": str(d.get("id")), "date": date,
                                     "fwd_channel_post": fwd.get("channel_post")}

    log.info("%d/%d messages are forwards; %d distinct source channel_ids; %d parse errors",
              n_fwd, n_total, len(channel_counts), n_parse_err)

    ranked = channel_counts.most_common()
    with OUT_JSONL.open("w", encoding="utf-8") as out:
        for channel_id, count in ranked:
            out.write(json.dumps({
                "channel_id": channel_id,
                "forward_count": count,
                "seen_via_source_types": sorted(channel_seen_via[channel_id]),
                "first_seen": channel_first_seen[channel_id],
                "last_seen": channel_last_seen[channel_id],
                "example_msg": channel_example[channel_id],
            }, ensure_ascii=False) + "\n")

    print(f"\n{len(ranked)} distinct forward-source channel_ids found across "
          f"{len(SOURCE_TYPE_PREFIXES)} channel groups")
    print(f"Top 30 by forward_count (resolve with scripts/231-style get_entity, user-run):\n")
    print(f"{'count':>6}  {'seen via (N groups)':<22} channel_id")
    for channel_id, count in ranked[:30]:
        n_groups = len(channel_seen_via[channel_id])
        print(f"{count:>6}  {n_groups:<22} {channel_id}")
    print(f"\n  → {OUT_JSONL}")
    print("\n  NOTE: channel_id here has NOT been cross-checked against the 26 channels\n"
          "  scripts/257 already crawls (that would need a username, which this offline\n"
          "  pass can't get) -- some top entries are probably re-discoveries of channels\n"
          "  already in this project's crawl list. Resolve the top N with a get_entity\n"
          "  call (same pattern as scripts/231) before treating any of these as new.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
