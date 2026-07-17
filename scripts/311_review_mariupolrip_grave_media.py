#!/usr/bin/env python3
"""Rank the mariupolRIP media just pulled (scripts/310) by likelihood that the
attached photo/video shows the GRAVE ITSELF, not a portrait of the victim.

The obituary-flagging pass (scripts/309) could tell us a message names a dead
person and has media attached -- it could not tell us whether that media is a
photo of the deceased (the common case) or a photo of the burial site (what
we actually want to review here). Text alone cannot fully resolve that either,
but it can rank candidates: a message whose text explicitly references a
photographed grave marker/mound/cross, or that carries an informal-burial
keyword (courtyard/basement/etc. -- scripts/300's list) describing WHERE
someone was buried, is far more likely to have attached a grave photo than a
message that is purely "Name, DOB, killed by shelling."

Read-only: joins the source_document media rows (source_type
"telegram_mariupolrip_media", captured by scripts/310) against the parsed
obituary text (scripts/309's flagged-messages JSONL) by message id, scores
each for grave-photo likelihood, and writes a ranked CSV + prints the top N
with local file paths so they can be opened directly for visual review.

    PYTHONPATH=src python scripts/311_review_mariupolrip_grave_media.py
    PYTHONPATH=src python scripts/311_review_mariupolrip_grave_media.py --top 40
"""
from __future__ import annotations

import argparse
import csv
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

FLAGGED_FILE = ROOT / "data" / "parsed" / "mariupolrip_flagged_messages.jsonl"
OUT_FILE = ROOT / "data" / "reports" / "mariupolrip_grave_media_ranked.csv"

# strongest signal: the poster is explicitly describing a photographed grave
GRAVE_EXPLICIT_RE = re.compile(
    r"фото\s+(?:и\s+видео\s+)?могил|видео\s+могил|фото\s+захоронени|"
    r"могил[ауы]?\b|надгроби|табличк\w*\s+с\s+имен|холмик\w*|"
    r"крест\w*\s+(?:на|у|стоит)|венок\w*\s+на\s+могил",
    re.IGNORECASE,
)
# where-buried language (scripts/300/304/309's informal-burial keyword set) --
# means the message describes a burial LOCATION, so any attached photo is
# more likely to be of that location than a portrait
BURIAL_LOCATION_RE = re.compile(
    r"во дворе|во дворике|в дворе|дворике|дворик|"
    r"за домом|возле дома|около дома|у дома|рядом с домом|"
    r"в саду|в огороде|огород|"
    r"у подъезда|около подъезда|"
    r"в палисаднике|палисадник|"
    r"на детской площад|на клумбе|клумб|"
    r"под окн|в гараже|в подвале|в сарае|"
    r"в вирве|в воронке|прикопал|закопал",
    re.IGNORECASE,
)
# weak negative signal: explicit portrait/ID-photo language
PORTRAIT_HINT_RE = re.compile(r"на фото|на снимке|фото из архива|последнее фото", re.IGNORECASE)


def _score(text: str) -> tuple[int, list[str]]:
    hits = []
    score = 0
    if GRAVE_EXPLICIT_RE.search(text):
        score += 5
        hits.append("explicit_grave_ref")
    if BURIAL_LOCATION_RE.search(text):
        score += 3
        hits.append("burial_location")
    if PORTRAIT_HINT_RE.search(text):
        score -= 1
        hits.append("portrait_hint")
    return score, hits


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=30)
    args = ap.parse_args()

    flagged_by_id = {}
    for line in FLAGGED_FILE.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        flagged_by_id[r["msg_id"]] = r

    con = sqlite3.connect(config.STATE_DB)
    rows = con.execute(
        "SELECT sha256, url, raw_path, content_type, description "
        "FROM source_document WHERE source_type='telegram_mariupolrip_media' ORDER BY url"
    ).fetchall()
    log.info("reviewing %d captured media rows", len(rows))

    out = []
    for sha, url, raw_path, content_type, description in rows:
        msg_id = url.rstrip("/").rsplit("/", 2)[-2]  # .../<id>/media
        flagged = flagged_by_id.get(msg_id, {})
        text = flagged.get("text", "")
        score, hits = _score(text)
        out.append({
            "msg_id": msg_id,
            "url": f"https://t.me/mariupolRIP/{msg_id}",
            "score": score,
            "hits": ";".join(hits),
            "property_id": flagged.get("property_id", ""),
            "matched_building_id": flagged.get("matched_building_id", ""),
            "content_type": content_type,
            "raw_path": raw_path,
            "sha256": sha,
            "text": text.replace("\n", " ⏎ "),
        })

    out.sort(key=lambda r: (-r["score"], r["msg_id"]))

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)

    n_positive = sum(1 for r in out if r["score"] > 0)
    n_explicit = sum(1 for r in out if "explicit_grave_ref" in r["hits"])
    n_burial_loc = sum(1 for r in out if "burial_location" in r["hits"])
    n_property = sum(1 for r in out if r["property_id"])

    print(f"\n{'='*72}")
    print(f"GRAVE-MEDIA RANKING — {len(out)} captured media items scored")
    print(f"{'='*72}")
    print(f"  score > 0 (some grave signal): {n_positive}")
    print(f"    explicit grave/marker reference: {n_explicit}")
    print(f"    burial-location language only:   {n_burial_loc - n_explicit if n_burial_loc >= n_explicit else n_burial_loc}")
    print(f"  also matched to a property on the spine: {n_property}")
    print(f"\n  written -> {OUT_FILE}")
    print(f"\n── top {args.top} candidates ──")
    for r in out[:args.top]:
        print(f"  [{r['score']:+d}] {r['url']:<38} {r['hits']:<28} {r['raw_path'].rsplit('/',1)[-1]}")
        print(f"        {r['text'][:140]}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
