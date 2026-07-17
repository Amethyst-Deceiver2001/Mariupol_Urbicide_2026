#!/usr/bin/env python3
"""Flag @mariupolRIP obituary-shaped messages and build a targeted media-pull
manifest -- the scripts/225/226 pattern, applied to the full mariupolRIP scan
(scripts/302 capture, scripts/303 parse) instead of @mariupol_nash.

@mariupolRIP ("Погибшие и Пропавшие, Мариуполь") is a dedicated memorial
channel: the overwhelming majority of its ~5,961 messages are individual
victim records -- a name, then the circumstances and/or place of death or
burial, frequently with an attached photo of the victim or of the grave
itself (see the samples surfaced during this session, e.g. msg 191, 268,
645). scripts/304 already narrowed the channel to messages that mention an
INFORMAL BURIAL specifically (courtyard/basement/etc. language) -- a strict
subset. This script instead flags the channel's general obituary shape (a
named individual + death/burial language, or a bare name-only record typical
of this channel), so media attached to any victim record can be recovered,
not only the informal-burial subset.

Read-only, local, no network -- reads the already-captured
"telegram_mariupolrip_msg" raw store + Postgres (for address matching),
writes two files:

  1. data/parsed/mariupolrip_flagged_messages.jsonl -- one row per message
     that looks like an obituary record, with media kind/size, an address
     match against the property spine (same stem/class recovery as
     scripts/304), and pull priority.
  2. data/parsed/mariupolrip_media_pull_manifest.jsonl -- the subset that
     actually carries media, ready for scripts/310 to fetch by message id.

Run (safe, read-only):
    PYTHONPATH=src python scripts/309_mariupolrip_flag_and_media_manifest.py
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

import psycopg2
import psycopg2.extras

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402
from mariupol_seizures.normalize.address import address_to_building_key  # noqa: E402

log = logging.getLogger(__name__)

SOURCE_TYPE = "telegram_mariupolrip_msg"
OUT_FLAGGED = ROOT / "data" / "parsed" / "mariupolrip_flagged_messages.jsonl"
OUT_MANIFEST = ROOT / "data" / "parsed" / "mariupolrip_media_pull_manifest.jsonl"

# A named-victim record on this channel almost always opens with a capitalized
# Cyrillic name run (surname [given name [patronymic]]) -- see scripts/304's
# BARE_RE for the same shape used for address stems. Kept deliberately loose
# (this channel's whole purpose is naming the dead) but anchored to the start
# of the message so it doesn't fire on mid-sentence proper nouns.
NAME_START_RE = re.compile(
    r"^[А-ЯЁ][а-яё]{2,20}(?:\s+[А-ЯЁ][а-яё]{2,20}){0,2}\b"
)

DEATH_RE = re.compile(
    r"погиб\w*|умер\w*|скончал\w*|убит\w*|не стало|ушел из жизни|ушёл из жизни|"
    r"пропал\w*|похорон\w*|захорон\w*",
    re.IGNORECASE,
)

# same informal-burial keyword set as scripts/300/304, kept in sync manually
INFORMAL_KEYWORDS = [
    "во дворе", "во дворике", "в дворе", "дворике", "дворик",
    "за домом", "возле дома", "около дома", "у дома", "рядом с домом",
    "в саду", "в огороде", "огород",
    "у подъезда", "около подъезда", "подъезд",
    "в палисаднике", "палисадник",
    "на детской площад", "на клумбе", "клумб",
    "под окн",
    "в гараже", "гараж",
    "в подвале", "подвал",
    "в сарае", "сарай",
    "закопали", "закопан",
]

STREET_TYPE = (
    r"(?:ул\.?|улица|пр-?кт\.?|просп\.?|проспект|б-р|бул\.?|бульвар|"
    r"пер\.?|переулок|пл\.?|площадь|наб\.?|набережная|проезд|шоссе)"
)
TYPED_RE = re.compile(
    rf"{STREET_TYPE}\.?\s+([а-яёА-ЯЁ][а-яёА-ЯЁ\-\s]{{2,25}}?)[,\s]+(?:д\.?\s*)?(\d+[а-яА-Я]?)",
    re.IGNORECASE,
)
BARE_RE = re.compile(r"([А-ЯЁ][а-яё]{2,20}(?:ая|ой|ий|ый|ого)?)[,\s]+(?:д\.?\s*)?(\d+[а-яА-Я]?)\b")


def _extract_candidate(text: str) -> tuple[str, str] | None:
    m = TYPED_RE.search(text)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    m = BARE_RE.search(text)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return None


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
    if t == "MessageMediaWebPage":
        return "webpage", None
    return t.replace("MessageMedia", "").lower() if t else "none", None


def main() -> None:
    con_state = sqlite3.connect(config.STATE_DB)
    rows = con_state.execute(
        "SELECT url, raw_path FROM source_document WHERE source_type=? ORDER BY url",
        (SOURCE_TYPE,),
    ).fetchall()
    log.info("scanning %d %s messages", len(rows), SOURCE_TYPE)

    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("select id, building_id, prewar_address, occupation_address from property where building_id is not null")
    all_props = cur.fetchall()
    by_key = {r["building_id"]: r for r in all_props}
    stem_to_classes: dict[str, set] = {}
    for r in all_props:
        cls, _, rest = r["building_id"].partition(":")
        stem, _, _house = rest.rpartition("|")
        stem_to_classes.setdefault(stem, set()).add(cls)
    log.info("loaded %d property building_id keys for matching", len(by_key))

    OUT_FLAGGED.parent.mkdir(parents=True, exist_ok=True)
    fh = OUT_FLAGGED.open("w", encoding="utf-8")
    mh = OUT_MANIFEST.open("w", encoding="utf-8")

    media_counts: Counter = Counter()
    priority_counts: Counter = Counter()
    n_msg = n_flagged = n_media_flagged = n_matched_property = 0

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

        msg_id = url.rstrip("/").rsplit("/", 1)[-1]
        text = (obj.get("message") or "").strip()
        date = (obj.get("date") or "")[:10]
        if not text:
            continue

        name_hit = bool(NAME_START_RE.match(text))
        death_hit = bool(DEATH_RE.search(text))
        informal_hit = next((kw for kw in INFORMAL_KEYWORDS if kw in text.lower()), None)

        # obituary shape: named-record opener, OR any death/burial language at all
        # (short "Саша погиб..." records use a bare first name, no surname).
        if not (name_hit or death_hit or informal_hit):
            continue

        candidate = _extract_candidate(text)
        prop = None
        if candidate:
            street_raw, house_raw = candidate
            raw_key = address_to_building_key(street_raw, house_raw)
            if raw_key:
                if raw_key in by_key:
                    prop = by_key[raw_key]
                else:
                    cls, _, rest = raw_key.partition(":")
                    stem, _, house_norm = rest.rpartition("|")
                    hits = [by_key[f"{c}:{stem}|{house_norm}"] for c in stem_to_classes.get(stem, set())
                            if f"{c}:{stem}|{house_norm}" in by_key]
                    if len(hits) == 1:
                        prop = hits[0]

        n_flagged += 1
        media_kind, media_size = _media_info(obj)
        media_counts[media_kind] += 1

        if prop:
            n_matched_property += 1
            priority = 1
        elif name_hit and (death_hit or informal_hit):
            priority = 2
        else:
            priority = 3

        rec = {
            "msg_id": msg_id, "url": url, "date": date,
            "name_shaped": name_hit, "death_language": death_hit,
            "informal_burial_kw": informal_hit,
            "matched_building_id": prop["building_id"] if prop else "",
            "property_id": prop["id"] if prop else "",
            "media_kind": media_kind, "media_size_bytes": media_size,
            "pull_priority": priority,
            "text": text[:400],
        }
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

        if media_kind != "none":
            n_media_flagged += 1
            priority_counts[priority] += 1
            mh.write(json.dumps({
                "msg_id": msg_id, "url": url, "date": date,
                "media_kind": media_kind, "media_size_bytes": media_size,
                "pull_priority": priority,
                "matched_building_id": rec["matched_building_id"],
                "property_id": rec["property_id"],
                "note": f"name_shaped={name_hit} death_language={death_hit} "
                        f"informal_kw={informal_hit or ''}",
            }, ensure_ascii=False) + "\n")

    fh.close()
    mh.close()
    con.close()

    print(f"\n{'='*72}")
    print(f"@mariupolRIP OBITUARY FLAGGING — {n_msg} messages scanned, {n_flagged} obituary-shaped")
    print(f"{'='*72}")
    print("\n── media on flagged messages ──")
    for k, c in media_counts.most_common():
        print(f"  {k:12s} {c}")
    print(f"\n  {n_media_flagged} flagged messages carry media")
    print(f"  {n_matched_property} matched to a property on the spine")
    print("\n── media-pull manifest by priority ──")
    print(f"  P1 (matched to a property)      = {priority_counts[1]}")
    print(f"  P2 (named + death/burial lang.) = {priority_counts[2]}")
    print(f"  P3 (weaker obituary signal)     = {priority_counts[3]}")
    print(f"\n  Flagged  → {OUT_FLAGGED}")
    print(f"  Manifest → {OUT_MANIFEST}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
