#!/usr/bin/env python3
"""Parse the 5,961 @mariupolRIP messages captured by
scripts/302_crawl_mariupolrip_text_only.py (source_type
"telegram_mariupolrip_msg" in the sqlite state DB) into one clean JSONL for
downstream analysis.

Read-only: reads the sqlite state DB + raw JSON files, writes one JSONL.
No network, no Postgres write.
"""
import json
import logging
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402

log = logging.getLogger(__name__)

SOURCE_TYPE = "telegram_mariupolrip_msg"
OUT_FILE = ROOT / "data" / "parsed" / "mariupolrip_messages.jsonl"


def main() -> None:
    con = sqlite3.connect(config.STATE_DB)
    rows = con.execute(
        "SELECT sha256, url, raw_path FROM source_document WHERE source_type=?",
        (SOURCE_TYPE,),
    ).fetchall()
    log.info("found %d captured messages in state DB", len(rows))

    out = []
    missing = 0
    for sha, url, raw_path in rows:
        p = Path(raw_path)
        if not p.exists():
            missing += 1
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        msg_id = d.get("id")
        text = (d.get("message") or "").strip()
        out.append({
            "id": msg_id,
            "url": url,
            "sha256": sha,
            "date": d.get("date"),
            "text": text,
            "text_len": len(text),
            "has_media": d.get("media") is not None,
            "reply_to_id": (d.get("reply_to") or {}).get("reply_to_msg_id") if d.get("reply_to") else None,
            "fwd_from": bool(d.get("fwd_from")),
        })

    out.sort(key=lambda r: r["id"] or 0)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    non_empty = sum(1 for r in out if r["text_len"] > 0)
    log.info("missing raw files: %d", missing)
    log.info("parsed rows: %d (non-empty text: %d)", len(out), non_empty)
    log.info("written -> %s", OUT_FILE)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
