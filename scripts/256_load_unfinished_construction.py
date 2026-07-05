#!/usr/bin/env python3
"""Load the 6 Mariupol sites designated "объекты незавершенного строительства"
(objects of unfinished construction) under Постановление ГКО ДНР №27
(21.04.2022), named in its implementing Распоряжение ГКО ДНР №28 (2022) --
found 2026-07-05 via an archive-wide OCR sweep of denis-pushilin.ru/
glavadnr.ru (see docs/legal_mechanisms_review.md, section [A2]).

This is a DESIGNATION event, not a confirmed completed transfer: №27 requires
the builder/developer to register within a window or have the object
declared to have "признаки бесхозяйного имущества" and pass to state
ownership by a FURTHER GKO decree -- the same claim-it-or-lose-it structure
as the housing 'ownerless_designation' track, applied one stage earlier (an
unfinished building, not yet occupied housing). New seizure_stage value
'unfinished_construction_designation' added in db/schema.sql for exactly this.

Of the 6 named sites, only 2 carry a house number resolvable to a building_id
via the project's normal street+house normalization pipeline:
  - просп. Нахимова, 2
  - ул. Амурская, 11
The other 4 are intersection/"between X and Y" descriptors with NO house
number ("проспект Строителей и ул. Крайняя" intersection; "между ул.
Пашковского и просп. Победы"; "ул. Иртышская, б/н"; the площадь Свободы site
between дом 101а по просп. Ленина и домом 125 по просп. Строителей) -- per
the project's no-false-precision rule, these are NOT force-geocoded to an
intersection centroid (that would represent "somewhere near here", not the
specific unfinished-construction lot the decree names) and are logged as
SKIPPED, matching the scripts/209 treatment of unconfirmed near-matches.

Idempotent: dedup_key = 'gko27_unfinished_construction:<seq>'; property
lookup by exact building_id (create-once, per _find_or_create_property).

Run:
    PYTHONPATH=src python scripts/256_load_unfinished_construction.py
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import psycopg2  # noqa: E402

from mariupol_seizures import config, forensics  # noqa: E402
from mariupol_seizures.normalize.address import classify_street, compute_building_key  # noqa: E402
from mariupol_seizures.db.load import _find_or_create_property, _upsert_source_doc_by_sha  # noqa: E402

log = logging.getLogger("load_unfinished_construction")

# Rasp_GKO_28's own decree number/date are OCR-garbled (scan artifacts); the
# filename convention (Rasp_GKO_28.pdf) is the only reliable identifier.
RASP_SHA_PREFIX = "694c700d4fac82"
POST27_SHA_PREFIX = "14b4587763ae26"
EVENT_DATE = None  # decree date not reliably OCR'd; see docstring

SITES = [
    {"seq": 1, "street": "проспект Нахимова", "house": "2",
     "occupation_address": "город Мариуполь, проспект Нахимова, 2",
     "descriptor": "между проспектом Нахимова и улицей Юнговской, на пересечении с улицей Санаторной"},
    {"seq": 2, "street": "проспект Строителей", "house": None,
     "occupation_address": "город Мариуполь, пересечение проспекта Строителей и улицы Крайней",
     "descriptor": "на пересечении проспекта Строителей и улицы Крайней"},
    {"seq": 3, "street": "улица Амурская", "house": "11",
     "occupation_address": "город Мариуполь, улица Амурская, 11",
     "descriptor": "улица Амурская, 11"},
    {"seq": 4, "street": None, "house": None,
     "occupation_address": None,
     "descriptor": "между улицей Пашковского и проспектом Победы"},
    {"seq": 5, "street": "улица Иртышская", "house": None,
     "occupation_address": None,
     "descriptor": "улица Иртышская, б/н"},
    {"seq": 6, "street": None, "house": None,
     "occupation_address": None,
     "descriptor": "Жовтневый район, район площади Свободы, между домом 101а по проспекту Ленина "
                    "и домом 125 по проспекту Строителей"},
]

UPSERT_EVENT_SQL = """
    INSERT INTO seizure_event
        (property_id, stage, event_date, source_doc_id, confidence, detail, dedup_key)
    VALUES (%s, 'unfinished_construction_designation', %s, %s, %s, %s, %s)
    ON CONFLICT (dedup_key) DO UPDATE
        SET event_date    = EXCLUDED.event_date,
            source_doc_id = EXCLUDED.source_doc_id,
            confidence    = EXCLUDED.confidence,
            detail        = EXCLUDED.detail
"""


def latest_source_doc_id(cur, sqlite_con, sha_prefix: str) -> int:
    sc = sqlite_con.cursor()
    sc.execute(
        "SELECT sha256 FROM source_document WHERE sha256 LIKE ? ORDER BY captured_at DESC LIMIT 1",
        (sha_prefix + "%",),
    )
    row = sc.fetchone()
    if not row:
        raise SystemExit(f"no source_document found for sha prefix {sha_prefix!r}")
    return _upsert_source_doc_by_sha(cur, row[0])


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    sqlite_con = forensics.open_state()

    pg = psycopg2.connect(config.DATABASE_URL)
    pg.autocommit = False
    cur = pg.cursor()

    rasp_source_doc_id = latest_source_doc_id(cur, sqlite_con, RASP_SHA_PREFIX)
    # Постановление №27 (the framework) is the enabling instrument for №28's named
    # list; registered here for chain-of-custody even though events below cite №28
    # (the named-list act) as their source_doc_id, not the framework itself.
    latest_source_doc_id(cur, sqlite_con, POST27_SHA_PREFIX)

    n_loaded = n_skipped = 0
    for item in SITES:
        classified = classify_street(item["street"]) if item["street"] else None
        building_id = None
        if classified is not None:
            building_id, _ = compute_building_key(classified.street_key, item["house"])

        if building_id is None:
            n_skipped += 1
            log.info("  SKIP site %d (%s) -- no house number, cannot resolve to a specific "
                     "building_id without false precision", item["seq"], item["descriptor"])
            continue

        notes = (f"Распоряжение ГКО ДНР №28 (2022, implementing Постановление ГКО ДНР №27, "
                 f"21.04.2022) п.{item['seq']}: designated \"объект незавершенного строительства\" "
                 f"({item['descriptor']}). Builder must register within the window set by №27 or "
                 f"the object is declared to have \"признаки бесхозяйного имущества\" and passes "
                 f"to state ownership by a further GKO decree.")
        property_id = _find_or_create_property(cur, building_id, occupation_address=item["occupation_address"])

        dedup_key = f"gko27_unfinished_construction:{item['seq']}"
        detail = json.dumps({
            "decree": "Распоряжение ГКО ДНР №28 (2022), implementing Постановление ГКО ДНР №27 (21.04.2022)",
            "descriptor": item["descriptor"],
            "mechanism": "unfinished_construction_designation",
            "note": "Designation event, not a confirmed completed transfer -- builder must "
                    "register within the window set by №27 or the object is declared to have "
                    "\"признаки бесхозяйного имущества\" and passes to state ownership by a "
                    "further GKO decree.",
        }, ensure_ascii=False)
        cur.execute(UPSERT_EVENT_SQL, (property_id, EVENT_DATE, rasp_source_doc_id, 0.75, detail, dedup_key))
        n_loaded += 1
        log.info("  site %d -> property %d: %s", item["seq"], property_id, item["occupation_address"])

    pg.commit()
    log.info("done: %d designated, %d skipped (no house number) of %d total sites",
              n_loaded, n_skipped, len(SITES))
    print(f"load_unfinished_construction: {n_loaded} loaded, {n_skipped} skipped of {len(SITES)} total sites")


if __name__ == "__main__":
    main()
