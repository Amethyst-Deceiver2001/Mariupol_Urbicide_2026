#!/usr/bin/env python3
"""Build a forward-source frequency graph over @mariupol_nash's 159,363 captured
messages — the "untried next step" flagged in docs/nash_channel_findings_2026-07.md
§7.3: 32,352 messages (20%) are forwards from other channels/users, an unmapped
source graph. This is how @mizodnr and @donurcenter were originally found
(memory/new_telegram_channels_intel_2026-06-27.md) — this script generalizes that
discovery method into a repeatable count instead of stumbling on sources by luck.

Telethon's serialized fwd_from carries only a numeric channel_id (PeerChannel) or a
free-text from_name (forwarded from a user/deleted account) — never a @username.
Resolving channel_id -> @username requires a live Telegram API lookup, which is a
network op this script deliberately does NOT do (CLAUDE.md: Claude never executes
the crawler). Instead it ranks channel_ids by frequency and hands the top N to
scripts/231 (network, user-run) to resolve.

Also cross-tabulates each forward-source against how many of ITS messages were
flagged by scripts/225 (data/parsed/nash_flagged_messages.jsonl) — a channel that's
both high-volume AND high-flag-rate is a stronger crawl candidate than one that's
just chatty.

Pure local analysis: reads data/raw/ via source_document rows only. No network, no
writes to data/raw or the DB.

Run:
    PYTHONPATH=src python scripts/230_nash_fwd_source_graph.py
"""
import json
import logging
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import forensics  # noqa: E402

log = logging.getLogger(__name__)

SOURCE_TYPE = "telegram_nash_msg"
FLAGGED = ROOT / "data" / "parsed" / "nash_flagged_messages.jsonl"
OUT_JSONL = ROOT / "data" / "parsed" / "nash_fwd_source_graph.jsonl"
OUT_SUMMARY = ROOT / "data" / "parsed" / "nash_fwd_source_graph_summary.json"


def _load_flagged_ids() -> set:
    ids = set()
    if FLAGGED.exists():
        for line in FLAGGED.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            mid = row.get("msg_id") or row.get("id")
            if mid is not None:
                ids.add(str(mid))
    return ids


def main() -> None:
    con = forensics.open_state()
    rows = con.execute(
        "SELECT url, raw_path FROM source_document WHERE source_type=?",
        (SOURCE_TYPE,),
    ).fetchall()
    log.info("scanning %d captured %s files for fwd_from", len(rows), SOURCE_TYPE)

    flagged_ids = _load_flagged_ids()
    log.info("cross-referencing against %d flagged msg_ids", len(flagged_ids))

    channel_counts: Counter = Counter()
    channel_flagged: Counter = Counter()
    channel_first_seen = {}
    channel_last_seen = {}
    channel_example_msgs = defaultdict(list)

    username_from_name_counts: Counter = Counter()  # forwards from users/deleted accts

    n_total = 0
    n_fwd = 0
    n_parse_err = 0

    for url, raw_path in rows:
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

        msg_id = str(d.get("id"))
        date = (d.get("date") or "")[:10]

        from_id = fwd.get("from_id") or {}
        channel_id = from_id.get("channel_id") if isinstance(from_id, dict) else None

        if channel_id is not None:
            key = str(channel_id)
            channel_counts[key] += 1
            if key not in channel_first_seen or date < channel_first_seen[key]:
                channel_first_seen[key] = date
            if key not in channel_last_seen or date > channel_last_seen[key]:
                channel_last_seen[key] = date
            if msg_id in flagged_ids:
                channel_flagged[key] += 1
            if len(channel_example_msgs[key]) < 3:
                channel_example_msgs[key].append(
                    {"msg_id": msg_id, "date": date,
                     "fwd_channel_post": fwd.get("channel_post")})
        else:
            from_name = fwd.get("from_name")
            if from_name:
                username_from_name_counts[from_name] += 1

    fh = OUT_JSONL.open("w", encoding="utf-8")
    ranked = channel_counts.most_common()
    for channel_id, count in ranked:
        fh.write(json.dumps({
            "channel_id": channel_id,
            "forward_count": count,
            "flagged_count": channel_flagged.get(channel_id, 0),
            "flagged_rate": round(channel_flagged.get(channel_id, 0) / count, 3),
            "first_seen": channel_first_seen.get(channel_id),
            "last_seen": channel_last_seen.get(channel_id),
            "example_msgs": channel_example_msgs.get(channel_id, []),
        }, ensure_ascii=False) + "\n")
    fh.close()

    summary = {
        "n_messages_scanned": n_total,
        "n_forwards": n_fwd,
        "n_parse_errors": n_parse_err,
        "n_distinct_channel_sources": len(channel_counts),
        "n_distinct_user_from_name_sources": len(username_from_name_counts),
        "top_20_channel_ids_by_forward_count": [
            {"channel_id": c, "forward_count": n, "flagged_count": channel_flagged.get(c, 0)}
            for c, n in ranked[:20]
        ],
        "top_20_from_name_user_forwards": username_from_name_counts.most_common(20),
    }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{'='*72}")
    print(f"@mariupol_nash FORWARD-SOURCE GRAPH — {n_fwd}/{n_total} messages are forwards "
          f"({round(100*n_fwd/max(n_total,1),1)}%)")
    print(f"{'='*72}")
    print(f"\n{len(channel_counts)} distinct forward-source channel_ids "
          f"(no @username resolvable offline — see scripts/231)")
    print(f"\n── top 25 channels by forward count (channel_id | count | flagged | flag-rate) ──")
    for channel_id, count in ranked[:25]:
        fc = channel_flagged.get(channel_id, 0)
        rate = round(100 * fc / count, 1)
        print(f"  {channel_id:>15}  {count:>5}  flagged={fc:>4}  ({rate}%)  "
              f"{channel_first_seen[channel_id]} .. {channel_last_seen[channel_id]}")

    if username_from_name_counts:
        print(f"\n── top 10 forwards from named users/deleted accounts (not channels) ──")
        for name, count in username_from_name_counts.most_common(10):
            print(f"  {count:>5}  {name}")

    print(f"\n  JSONL      → {OUT_JSONL}")
    print(f"  Summary    → {OUT_SUMMARY}")
    print(f"\n  Next: PYTHONPATH=src .venv312/bin/python scripts/231_resolve_fwd_channel_ids.py "
          f"— resolves the top channel_ids to @usernames (network, run yourself).")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
