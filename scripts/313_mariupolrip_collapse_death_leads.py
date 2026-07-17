#!/usr/bin/env python3
"""Extract collapse-entombment leads from the full @mariupolRIP channel scan
(scripts/302 capture, scripts/303 parse) and cross-reference against the
property spine -- same method as scripts/304, but for a distinct death
modality Case 8 (2026-07-12 sweep, see docs/case_studies/
death_sites_new_construction.md) explicitly tracked separately and did not
count as a "grave": victims whose bodies were never recovered from beneath
their own collapsed building (завалило/обвалилось/под завалами/etc.),
rather than informally buried in a yard.

Evidentiary rationale (see docs/case_studies/death_sites_new_construction.md,
"Case 9"): a body entombed in rubble and a body buried in the courtyard are
the same category of harm for this project's purpose -- unexhumed human
remains at a specific address, at risk of being built over without proper
exhumation/reinterment if that address is later demolished and redeveloped.
This script finds the collapse-entombment addresses and checks each one
against every seizure_event stage on the spine, exactly as scripts/304 does
for courtyard burials.

A message is EXCLUDED if it also contains explicit later-exhumation/
reburial language (перезахорон*) -- those are closed cases, remains already
recovered, not at risk from future redevelopment.

Read-only: local JSONL + Postgres SELECT, one CSV write.

    PYTHONPATH=src python scripts/313_mariupolrip_collapse_death_leads.py
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
OUT_FILE = ROOT / "data" / "reports" / "mariupolrip_collapse_death_leads.csv"

COLLAPSE_RE = re.compile(
    r"завалил\w*|обвалил\w*|обрушил\w*|придавил\w*|плитой|плитами|под завалами|"
    r"не откопал\w*|не смогли откопать|не удалось откопать|погреб\w*н\w*|засыпал\w*|"
    r"разрушил\w*ся|рухнул\w*|сложил\w*ся дом|обломками|под обломками|раздавил\w*",
    re.IGNORECASE,
)
EXHUMED_RE = re.compile(r"перезахорон\w*", re.IGNORECASE)

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


def main() -> None:
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
    n_exhumed_excluded = 0
    for m in messages:
        text = m["text"]
        if not text or m["text_len"] < 15:
            continue
        if not COLLAPSE_RE.search(text):
            continue
        if EXHUMED_RE.search(text):
            n_exhumed_excluded += 1
            continue

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
            "matched_building_id": prop["building_id"] if prop else "",
            "property_id": prop["id"] if prop else "",
            "occupation_address": (prop["occupation_address"] or "") if prop else "",
            "prewar_address": (prop["prewar_address"] or "") if prop else "",
            "seizure_stages": seizure_stages,
            "text": text.replace("\n", " ⏎ "),
        })

    con.close()

    results.sort(key=lambda r: (not r["property_id"], not r["seizure_stages"], r["msg_id"]))

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w", encoding="utf-8", newline="") as f:
        fieldnames = list(results[0].keys()) if results else [
            "msg_id", "url", "date", "matched_building_id", "property_id",
            "occupation_address", "prewar_address", "seizure_stages", "text",
        ]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(results)

    on_spine = sum(1 for r in results if r["property_id"])
    seized = sum(1 for r in results if r["seizure_stages"])

    log.info("=== SUMMARY ===")
    log.info("collapse-entombment messages: %d (excluded %d already-reburied)", len(results), n_exhumed_excluded)
    log.info("  matched to a property on the spine: %d", on_spine)
    log.info("  of which that property has a seizure_event: %d", seized)
    log.info("written -> %s", OUT_FILE)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
