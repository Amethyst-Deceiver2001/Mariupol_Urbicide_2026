#!/usr/bin/env python3
"""Extract grave-site leads from the full @mariupolRIP channel scan
(scripts/302 capture, scripts/303 parse) -- the same informal-burial /
address-echo signal as scripts/300, applied to 4,710 free-text channel
messages instead of the curated mariupoldestruction.com spreadsheet, then
cross-referenced against the property spine (scripts/301-style) and split
into:

  - NEW leads: message id is not among the ~1,468 t.me/mariupolRIP/NNNN
    links already cited as a source in the spreadsheet (scripts/299's
    capture) -- i.e. genuinely new to this project, not just a richer quote
    for a row we already have.
  - Corroboration: message id IS already cited in the spreadsheet -- the
    full original post text for a row scripts/300 already flagged,
    useful for exhibit quotes (STYLE_GUIDE rule 10: verbatim RU quotes only)
    but not a new data point.

Read-only: local JSONL + Postgres SELECT, one CSV write.
"""
from __future__ import annotations

import csv
import json
import logging
import re
import sys
from pathlib import Path

import psycopg2
import psycopg2.extras

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402
from mariupol_seizures.normalize.address import address_to_building_key  # noqa: E402

log = logging.getLogger(__name__)

MESSAGES_FILE = ROOT / "data" / "parsed" / "mariupolrip_messages.jsonl"
SHEET_FILE = ROOT / "data" / "raw" / "17e0dd2c821dfecd01d1f11a499eb4f72cdf585cf9eb1e4520eb4efeaa9dc7a8.csv"
OUT_FILE = ROOT / "data" / "reports" / "mariupolrip_channel_grave_leads.csv"

# Keyword lists mirror scripts/300_extract_courtyard_grave_sites.py --
# kept in sync manually (same convention as the repeated _serialize/
# _json_default helpers across the telegram crawler scripts).
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
    "на месте гибели", "на месте смерти", "там же, где",
    "закопали", "закопан",
]
UNBURIED_KEYWORDS = [
    "не захоронен", "не захоронены", "не захоронена",
    "не погребен", "без захоронения", "тело лежит", "тела лежат",
    "не смогли похоронить", "не удалось похоронить",
]
CEMETERY_KEYWORDS = ["кладбищ"]

STREET_TYPE = (
    r"(?:ул\.?|улица|пр-?кт\.?|просп\.?|проспект|б-р|бул\.?|бульвар|"
    r"пер\.?|переулок|пл\.?|площадь|наб\.?|набережная|проезд|шоссе)"
)
TYPED_RE = re.compile(
    rf"{STREET_TYPE}\.?\s+([а-яёА-ЯЁ][а-яёА-ЯЁ\-\s]{{2,25}}?)[,\s]+(?:д\.?\s*)?(\d+[а-яА-Я]?)",
    re.IGNORECASE,
)
BARE_RE = re.compile(r"([А-ЯЁ][а-яё]{2,20}(?:ая|ой|ий|ый|ого)?)[,\s]+(?:д\.?\s*)?(\d+[а-яА-Я]?)\b")


def extract_candidate(text: str) -> tuple[str, str] | None:
    if not text:
        return None
    m = TYPED_RE.search(text)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    m = BARE_RE.search(text)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return None


def load_known_ids() -> set[int]:
    rows = list(csv.reader(SHEET_FILE.open(encoding="utf-8")))
    src_col = 8  # "Источник информации/ контакт для связи"
    ids = set()
    for r in rows[1:]:
        if len(r) <= src_col:
            continue
        for m in re.finditer(r"t\.me/mariupolRIP/(\d+)", r[src_col]):
            ids.add(int(m.group(1)))
    return ids


def main() -> None:
    known_ids = load_known_ids()
    log.info("known (already-cited-in-sheet) mariupolRIP message ids: %d", len(known_ids))

    messages = [json.loads(line) for line in MESSAGES_FILE.open(encoding="utf-8")]
    log.info("loaded %d parsed messages", len(messages))

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

    results = []
    counts = {"new_informal": 0, "new_address_echo": 0, "known_cited": 0}
    for m in messages:
        text = m["text"]
        if not text or m["text_len"] < 15:
            continue
        low = text.lower()

        matched_kw = next((kw for kw in INFORMAL_KEYWORDS if kw in low), None)
        is_unburied = any(kw in low for kw in UNBURIED_KEYWORDS)
        is_cemetery_only = any(kw in low for kw in CEMETERY_KEYWORDS) and not matched_kw

        candidate = extract_candidate(text)
        prop = None
        if candidate:
            street_raw, house_raw = candidate
            raw_key = address_to_building_key(street_raw, house_raw)
            if raw_key:
                cls, _, rest = raw_key.partition(":")
                stem, _, house_norm = rest.rpartition("|")
                if raw_key in by_key:
                    prop = by_key[raw_key]
                else:
                    hits = [by_key[f"{c}:{stem}|{house_norm}"] for c in stem_to_classes.get(stem, set())
                            if f"{c}:{stem}|{house_norm}" in by_key]
                    if len(hits) == 1:
                        prop = hits[0]

        if not matched_kw and not prop:
            continue
        if is_cemetery_only:
            continue

        is_known = m["id"] in known_ids
        category = "known_cited" if is_known else ("new_informal" if matched_kw else "new_address_echo")
        counts[category] += 1

        seizure_stages = ""
        if prop:
            cur.execute(
                "select distinct stage from seizure_event where property_id = %s",
                (prop["id"],),
            )
            seizure_stages = ";".join(sorted(r["stage"] for r in cur.fetchall()))

        results.append({
            "msg_id": m["id"],
            "url": m["url"],
            "date": m["date"],
            "category": category,
            "matched_keyword": matched_kw or "",
            "unburied": is_unburied,
            "matched_building_id": prop["building_id"] if prop else "",
            "property_id": prop["id"] if prop else "",
            "occupation_address": (prop["occupation_address"] or "") if prop else "",
            "prewar_address": (prop["prewar_address"] or "") if prop else "",
            "seizure_stages": seizure_stages,
            "text": text.replace("\n", " ⏎ "),
        })

    con.close()

    results.sort(key=lambda r: (r["category"] != "new_informal", r["category"] != "new_address_echo", r["msg_id"]))

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w", encoding="utf-8", newline="") as f:
        fieldnames = list(results[0].keys()) if results else [
            "msg_id", "url", "date", "category", "matched_keyword", "unburied",
            "matched_building_id", "property_id", "occupation_address",
            "prewar_address", "seizure_stages", "text",
        ]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(results)

    new_total = counts["new_informal"] + counts["new_address_echo"]
    new_on_spine = sum(1 for r in results if r["category"] != "known_cited" and r["property_id"])
    new_seized = sum(1 for r in results if r["category"] != "known_cited" and r["seizure_stages"])

    log.info("=== SUMMARY ===")
    log.info("flagged messages total: %d", len(results))
    log.info("  new_informal (keyword, not previously cited): %d", counts["new_informal"])
    log.info("  new_address_echo (address match, not previously cited): %d", counts["new_address_echo"])
    log.info("  known_cited (already in spreadsheet as a source): %d", counts["known_cited"])
    log.info("NEW leads total: %d", new_total)
    log.info("  of which matched to a property on the spine: %d", new_on_spine)
    log.info("  of which that property has a seizure_event (demolition/registry/etc): %d", new_seized)
    log.info("written -> %s", OUT_FILE)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
