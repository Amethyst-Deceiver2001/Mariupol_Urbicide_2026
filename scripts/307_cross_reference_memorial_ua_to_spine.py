#!/usr/bin/env python3
"""Cross-reference the 464 memorial.ua Mariupol victim records
(scripts/306) against the property spine, same methodology as
scripts/301/304: extract a street+house candidate from the full life-story
text, resolve it through the project's real address normalizer (recovering
the street-type class from the property table's own inventory when the
free text omits it, same as scripts/301), and flag whether that property
has a seizure_event on file. Also flags informal/courtyard-burial language
in the story text (same keyword set as scripts/300/304).

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

IN_FILE = ROOT / "data" / "parsed" / "memorial_ua_obituaries.jsonl"
OUT_FILE = ROOT / "data" / "reports" / "memorial_ua_property_overlap.csv"

MARIUPOL_RE = re.compile(r"маріупол", re.IGNORECASE)

INFORMAL_KEYWORDS = [
    "у дворі", "у дворику", "за будинком", "біля будинку", "коло будинку",
    "поруч з будинком", "в саду", "в городі", "город",
    "біля під'їзду", "коло під'їзду", "під'їзд",
    "у палісаднику", "палісадник",
    "на дитячому майданчик", "на клумбі", "клумб",
    "під вікн",
    "у гаражі", "гараж",
    "у підвалі", "підвал",
    "у сараї", "сарай",
    "прикопал", "закопал",
    "у вирві", "у воронці",
]

STREET_TYPE = (
    r"(?:вул\.?|вулиця|пр-?т\.?|просп\.?|проспект|б-р|бул\.?|бульвар|"
    r"пров\.?|провулок|пл\.?|площа|наб\.?|набережна|проїзд|шосе)"
)
TYPED_RE = re.compile(
    rf"{STREET_TYPE}\.?\s+([а-яіїєґА-ЯІЇЄҐа-яёА-ЯЁ][а-яіїєґА-ЯІЇЄҐа-яёА-ЯЁ\-\s]{{2,25}}?)[,\s]+(?:буд\.?\s*)?(\d+[а-яА-Я]?(?:/\d+)?)",
    re.IGNORECASE,
)


# memorial.ua is Ukrainian-language; the property spine's building_id keys
# are built from occupation-era Russian-language sources. These are plain
# language equivalents of the same street (not political toponym renames --
# those are already handled by classify_street's toponym lookup), so they
# don't belong in data/toponyms.csv. Kept small and hand-verified: sourced
# from this project's own already-published UA/RU dual-spelling pairs
# (STYLE_GUIDE.md's title="UA ... · RU ..." pattern across the exhibits)
# plus confirmed-present-in-spine checks (2026-07-12) for the rest. Every
# entry here was checked against `property.building_id` before being added
# -- do not add a translation without that check (silent mismatches would
# misattribute a death to the wrong building).
UA_TO_RU_STREET = {
    "будівельників": "строителей",
    "металургів": "металлургов",
    "миру": "ленина",  # toponym rename (pre-war UA name -> occupation RU name), confirmed in data/toponyms.csv too
    "перемоги": "победы",
    "кленовий": "кленовый",
    "кленова": "кленовая",
    "трамвайний": "трамвайный",
    "трамвайна": "трамвайная",
    "сєченова": "сеченова",
    "чорноморський": "черноморский",
    "нахімова": "нахимова",
}


def extract_candidate(text: str) -> tuple[str, str] | None:
    if not text:
        return None
    m = TYPED_RE.search(text)
    if m:
        house = m.group(2).split("/")[0]  # "32/42" -> "32"
        street = m.group(1).strip()
        translated = UA_TO_RU_STREET.get(street.lower())
        return (translated if translated else street), house
    return None


def main() -> None:
    records = [json.loads(line) for line in IN_FILE.open(encoding="utf-8")]
    leads = [r for r in records
             if MARIUPOL_RE.search(r.get("death_city", "") + r.get("birth_city", ""))]
    log.info("loaded %d Mariupol-matched records", len(leads))

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
    for rec in leads:
        story = rec.get("story_full", "") or ""
        matched_kw = next((kw for kw in INFORMAL_KEYWORDS if kw in story.lower()), None)

        candidate = extract_candidate(story)
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

        if not matched_kw and not prop:
            continue

        seizure_stages = ""
        if prop:
            cur.execute(
                "select distinct stage from seizure_event where property_id = %s",
                (prop["id"],),
            )
            seizure_stages = ";".join(sorted(r["stage"] for r in cur.fetchall()))

        results.append({
            "url": rec["url"],
            "name": rec.get("name", ""),
            "death_date": rec.get("death_date", ""),
            "age": rec.get("age", ""),
            "death_city": rec.get("death_city", ""),
            "matched_keyword": matched_kw or "",
            "matched_building_id": prop["building_id"] if prop else "",
            "property_id": prop["id"] if prop else "",
            "occupation_address": (prop["occupation_address"] or "") if prop else "",
            "prewar_address": (prop["prewar_address"] or "") if prop else "",
            "seizure_stages": seizure_stages,
            "story_excerpt": story[:400],
        })

    con.close()

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w", encoding="utf-8", newline="") as f:
        fieldnames = list(results[0].keys()) if results else [
            "url", "name", "death_date", "age", "death_city", "matched_keyword",
            "matched_building_id", "property_id", "occupation_address",
            "prewar_address", "seizure_stages", "story_excerpt",
        ]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(results)

    on_spine = sum(1 for r in results if r["property_id"])
    seized = sum(1 for r in results if r["seizure_stages"])
    kw_only = sum(1 for r in results if r["matched_keyword"] and not r["property_id"])

    log.info("=== SUMMARY ===")
    log.info("flagged (keyword and/or address match): %d", len(results))
    log.info("  matched to a property on the spine: %d", on_spine)
    log.info("    of which that property has a seizure_event: %d", seized)
    log.info("  keyword-only, no address extracted: %d", kw_only)
    log.info("written -> %s", OUT_FILE)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
