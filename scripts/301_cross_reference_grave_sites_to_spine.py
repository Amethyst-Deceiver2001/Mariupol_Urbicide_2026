#!/usr/bin/env python3
"""Cross-reference the 284 potential ad-hoc grave-site rows extracted in
scripts/300 against the property spine, to find addresses where an informal
burial happened AND the property was later seized/demolished/redeveloped --
the overlap that makes this belong in the property-seizure project rather
than reading as general war-crimes documentation.

For each grave-site row, extract a (street, house) candidate from the
burial-place / death-place / residence text (whichever yields one), run it
through the project's real address normalization pipeline
(normalize.address.address_to_building_key -- same code db/load.py and the
address registry use, so it already handles occupation renames/aliases),
and join against property.building_id. For matches, pull that property's
seizure_event stages.

Read-only: two local reads (CSV + Postgres SELECT), one CSV write. No DB
writes, no crawling.
"""
from __future__ import annotations

import csv
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

IN_FILE = ROOT / "data" / "reports" / "courtyard_grave_sites.csv"
OUT_FILE = ROOT / "data" / "reports" / "grave_sites_property_overlap.csv"

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
    rows = list(csv.DictReader(IN_FILE.open(encoding="utf-8")))
    log.info("loaded %d grave-site rows from %s", len(rows), IN_FILE.name)

    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("select id, building_id, prewar_address, occupation_address from property where building_id is not null")
    all_props = cur.fetchall()
    by_key = {r["building_id"]: r for r in all_props}
    log.info("loaded %d property building_id keys for matching", len(by_key))

    # Grave-site free text usually omits the street-type prefix ("Металлургов
    # 47" not "пр. Металлургов, 47"), so address_to_building_key can only
    # classify it as UNKNOWN -- the project's normalizer deliberately refuses
    # to guess a class (STREET vs AVENUE vs BOULEVARD), "miss rather than
    # collide". Recover it here from the property table's own inventory
    # instead of guessing blind: for a bare stem, look up which class(es)
    # that stem is actually known under. If exactly one of those classes has
    # a property at this house number, that's the match -- backed by real
    # data, not an assumption. If more than one does, it's a genuine
    # ambiguity (e.g. "металлургов" exists as both STREET and AVENUE in the
    # spine) and is left unmatched rather than resolved by guesswork.
    stem_to_classes: dict[str, set] = {}
    for r in all_props:
        cls, _, rest = r["building_id"].partition(":")
        stem, _, _house = rest.rpartition("|")
        stem_to_classes.setdefault(stem, set()).add(cls)

    ambiguous_hits = []
    results = []
    matched = 0
    for row in rows:
        candidate = None
        for field in (row["burial_place"], row["death_place"], row["residence"]):
            c = extract_candidate(field)
            if c:
                candidate = c
                break
        if not candidate:
            continue
        street_raw, house_raw = candidate
        raw_key = address_to_building_key(street_raw, house_raw)
        if not raw_key:
            continue
        cls, _, rest = raw_key.partition(":")
        stem, _, house_norm = rest.rpartition("|")

        prop = None
        if raw_key in by_key:
            prop = by_key[raw_key]
        else:
            candidate_classes = stem_to_classes.get(stem, set())
            hits = [by_key[f"{c}:{stem}|{house_norm}"] for c in candidate_classes
                    if f"{c}:{stem}|{house_norm}" in by_key]
            if len(hits) == 1:
                prop = hits[0]
            elif len(hits) > 1:
                ambiguous_hits.append((row["name"], street_raw, house_raw, [h["building_id"] for h in hits]))
                continue
        if prop is None:
            continue
        cur.execute(
            "select stage, event_date, confidence from seizure_event "
            "where property_id = %s order by stage, event_date nulls last",
            (prop["id"],),
        )
        events = cur.fetchall()
        stages = sorted({e["stage"] for e in events})
        seized = bool(stages)

        matched += 1
        results.append({
            "name": row["name"],
            "dod": row["dod"],
            "burial_place": row["burial_place"],
            "death_place": row["death_place"],
            "residence": row["residence"],
            "matched_building_id": prop["building_id"],
            "property_id": prop["id"],
            "prewar_address": prop["prewar_address"] or "",
            "occupation_address": prop["occupation_address"] or "",
            "on_spine": seized,
            "seizure_stages": ";".join(stages),
            "flags": row["flags"],
        })

    con.close()

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w", encoding="utf-8", newline="") as f:
        fieldnames = list(results[0].keys()) if results else [
            "name", "dod", "burial_place", "death_place", "residence",
            "matched_building_id", "property_id", "prewar_address",
            "occupation_address", "on_spine", "seizure_stages", "flags",
        ]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(results)

    on_spine = sum(1 for r in results if r["on_spine"])
    from collections import Counter
    stage_counts = Counter()
    for r in results:
        for s in r["seizure_stages"].split(";"):
            if s:
                stage_counts[s] += 1

    log.info("=== SUMMARY ===")
    log.info("grave-site rows with an extractable address candidate: %d",
              sum(1 for row in rows if any(extract_candidate(row[f]) for f in ("burial_place", "death_place", "residence"))))
    log.info("matched to a property on the spine: %d", matched)
    log.info("  of which the property HAS at least one seizure_event: %d", on_spine)
    for k, v in stage_counts.most_common():
        log.info("    %s: %d", k, v)
    log.info("ambiguous stem+house (matches >1 property, left unresolved): %d", len(ambiguous_hits))
    for name, street_raw, house_raw, keys in ambiguous_hits:
        log.info("    %s -- %r %r -> %s", name, street_raw, house_raw, keys)
    log.info("written -> %s", OUT_FILE)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
