#!/usr/bin/env python3
"""Load the 13 named addresses from Постановление ГКО ДНР №263 (29.09.2022)
"Об урегулировании имущественных вопросов пополнения маневренного фонда
города Мариуполя" -- read in full 2026-06-29 from the OCR'd primary text
(data/parsed/decree_gko263_ocr.txt, local-only; see legal_mechanisms_review.md's
corrected row), discovered to be a NAMED expropriation decree, not the
generic "маневренный фонд predicate framework" it was previously
characterized as.

Two annexes, two distinct legal effects -- loaded as the new
seizure_stage='expropriation' (db/schema.sql ALTER TYPE, 2026-06-29):

- Приложение №1 (5 addresses): former Ukrainian-state-owned dormitories/
  offices, transferred STATE -> MUNICIPAL ownership directly, NO
  compensation (Ukrainian state property, not private).
- Приложение №2 (8 addresses): PRIVATELY-OWNED hotels/dormitories/buildings,
  forcibly expropriated ("принудительное изъятие") with compensation
  CONTINGENT on owners submitting title documents within 30 days -- miss
  the deadline and lose the right to compensation entirely (§5-6). §8 also
  strips registered occupants' residency rights on the same 30-day clock.

Address-spine check (2026-06-29, exact street+house-number match): 10 of
13 addresses are confirmed NOT on the property spine -- these are loaded as
NEW properties. The remaining 3 (Карпинского 84, Сеченова 81, Лунина 9)
originally had loose near-matches by street + rounded house number but
unconfirmed building identity -- per the project's no-false-precision rule,
logged and SKIPPED, not force-merged.

Q8 follow-up (2026-06-29, outsourced research + map check, see
docs/research_outsourcing/OPEN_QUESTIONS_2026-06-29.md): all 3 resolved.
- Карпинского 84 (property_id 5672): exact house-number match AND map-confirmed
  as a dormitory (общежитие), matching the decree's own description of this
  entry -- CONFIRMED, now loaded as an event against the existing property_id
  (not a new property).
- Сеченова 81 (property_id 5759): exact house-number match AND map-confirmed
  as a converted dormitory (active apartment listing,
  https://mariupol.ayax.ru/flat/137105300/) -- CONFIRMED, same treatment as
  Карпинского 84, loaded against the existing property_id.
- Лунина 9: spine property_id 5816 is "Лунина 9а" -- map footprint check
  (domclick.ru + map screenshot, 2026-06-29) confirms №9 and №9а are SEPARATE
  building footprints several buildings apart along the same street (9, then
  11/11А/11Б/11В/13, then 9А), not a suffix variant of one plot -- CONFIRMED
  DISTINCT. Geocoded by user (2026-06-29): 47.070244, 37.514428 -- now loaded
  as its own new property with this geom, no longer skipped.

Idempotent: dedup_key = 'gko263_expropriation:<annex>:<seq_no>'.

Run:
    PYTHONPATH=src python scripts/209_load_gko263_expropriation.py
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
from mariupol_seizures.db.load import _upsert_source_doc_by_sha  # noqa: E402

log = logging.getLogger("load_gko263_expropriation")

SOURCE_SHA_PREFIX = "f3a676688bc3"
EVENT_DATE = "2022-09-29"

# Приложение №1 -- former Ukrainian-state property, transferred state->municipal, no compensation.
ANNEX_1 = [
    {"seq": 1, "occupation_address": "город Мариуполь, Жовтневый район, улица Апатова (Итальянская), дом 138",
     "name": "Общежитие (ранее за Верховной Радой Украины / Приазовский государственный технический университет)"},
    {"seq": 2, "occupation_address": "город Мариуполь, Приморский район, проспект Строителей, дом 13",
     "name": "Общежитие (ранее за Министерством образования и науки Украины / Одесская национальная морская академия)"},
    {"seq": 3, "occupation_address": "город Мариуполь, Приморский район, проспект Строителей, дом 52",
     "name": "Общежитие (ранее за Кабинетом Министров Украины / Мариупольский государственный гуманитарный университет)"},
    {"seq": 4, "occupation_address": "город Мариуполь, Приморский район, проспект Лунина, дом 9",
     "name": "Общежитие (ранее за Министерством транспорта и связи Украины / ГП «Мариупольский морской торговый порт»)",
     # Confirmed distinct from property_id 5816 (Лунина 9а) -- see Q8 in
     # docs/research_outsourcing/OPEN_QUESTIONS_2026-06-29.md. Geocoded by
     # user 2026-06-29; lonlat order matches ST_MakePoint(lon, lat).
     "lonlat": (37.514428, 47.070244)},
    {"seq": 5, "occupation_address": "город Мариуполь, Приморский район, улица Красномаякская, дом 17",
     "name": "Строение (ранее за Кабинетом Министров Украины / Региональное отделение Фонда государственного имущества Украины)"},
]

# Приложение №2 -- private property, forced expropriation, compensation contingent on 30-day deadline.
ANNEX_2 = [
    {"seq": 1, "occupation_address": "город Мариуполь, Ильичевский район, улица Карпинского, дом 80",
     "name": "Гостиница «Колумб»"},
    {"seq": 2, "occupation_address": "город Мариуполь, Ильичевский район, проспект Металлургов, дом 211",
     "name": "Гостиница «Дружба»"},
    {"seq": 3, "occupation_address": "город Мариуполь, Ильичевский район, улица Карпинского, дом 84",
     "name": "Общежитие", "confirmed_property_id": 5672},
    {"seq": 4, "occupation_address": "город Мариуполь, Ильичевский район, улица Сеченова, дом 81",
     "name": "Общежитие", "confirmed_property_id": 5759},
    {"seq": 5, "occupation_address": "город Мариуполь, Жовтневый район, проспект Ленина, дом 68",
     "name": "Здание"},
    {"seq": 6, "occupation_address": "город Мариуполь, Приморский район, проспект Строителей, дом 56",
     "name": "Общежитие"},
    {"seq": 7, "occupation_address": "город Мариуполь, Приморский район, проспект Нахимова, дом 7",
     "name": "Здание"},
    {"seq": 8, "occupation_address": "город Мариуполь, Приморский район, улица Большая Морская, дом 42",
     "name": "Гостиница «Бригантина»"},
]

INSERT_PROPERTY_SQL = """
    INSERT INTO property (occupation_address, notes)
    VALUES (%s, %s)
    RETURNING id
"""

INSERT_PROPERTY_WITH_GEOM_SQL = """
    INSERT INTO property (occupation_address, notes, geom)
    VALUES (%s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
    RETURNING id
"""

SELECT_PROPERTY_BY_ADDRESS_SQL = """
    SELECT id FROM property WHERE occupation_address = %s LIMIT 1
"""


def _find_or_insert_property(cur, occupation_address: str, notes: str,
                              lonlat: tuple[float, float] | None = None) -> tuple[int, bool]:
    """Idempotent property creation by exact occupation_address match -- a 2026-06-29
    re-run of this script (to load the Q8-confirmed Карпинского 84 merge) discovered
    INSERT_PROPERTY_SQL had no such guard, silently duplicating all 10 already-loaded
    addresses (properties 26299-26308, since cleaned up). Returns (property_id, created).
    `lonlat`, if given, is (lon, lat) -- same x/y convention as scripts/69 and
    `_find_or_create_property` in db/load.py -- and only applies on the insert path.
    """
    cur.execute(SELECT_PROPERTY_BY_ADDRESS_SQL, (occupation_address,))
    row = cur.fetchone()
    if row:
        return row[0], False
    if lonlat is not None:
        cur.execute(INSERT_PROPERTY_WITH_GEOM_SQL, (occupation_address, notes, lonlat[0], lonlat[1]))
    else:
        cur.execute(INSERT_PROPERTY_SQL, (occupation_address, notes))
    return cur.fetchone()[0], True

UPSERT_EVENT_SQL = """
    INSERT INTO seizure_event
        (property_id, stage, event_date, source_doc_id, confidence, detail, dedup_key)
    VALUES (%s, 'expropriation', %s, %s, %s, %s, %s)
    ON CONFLICT (dedup_key) DO UPDATE
        SET event_date    = EXCLUDED.event_date,
            source_doc_id = EXCLUDED.source_doc_id,
            confidence    = EXCLUDED.confidence,
            detail        = EXCLUDED.detail
"""


def latest_source_doc_id(cur, sqlite_con) -> int:
    sc = sqlite_con.cursor()
    sc.execute(
        "SELECT sha256 FROM source_document WHERE sha256 LIKE ? ORDER BY captured_at DESC LIMIT 1",
        (SOURCE_SHA_PREFIX + "%",),
    )
    row = sc.fetchone()
    if not row:
        raise SystemExit(f"no source_document found for sha prefix {SOURCE_SHA_PREFIX!r}")
    return _upsert_source_doc_by_sha(cur, row[0])


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    sqlite_con = forensics.open_state()

    pg = psycopg2.connect(config.DATABASE_URL)
    pg.autocommit = False
    cur = pg.cursor()

    source_doc_id = latest_source_doc_id(cur, sqlite_con)

    n_loaded, n_skipped = 0, 0

    for item in ANNEX_1:
        if "near_match_property_id" in item:
            n_skipped += 1
            log.info("  SKIP annex1.%d (%s) -- unconfirmed near-match to existing property %d (%s), "
                     "not force-merged", item["seq"], item["occupation_address"],
                     item["near_match_property_id"], item["near_match_address"])
            continue
        notes = (f"Постановление ГКО ДНР №263 (29.09.2022), Приложение №1 п.{item['seq']}: "
                 f"{item['name']}. Transferred Ukrainian-state -> municipal ownership directly, "
                 f"NO compensation (former Ukrainian state property, not private).")
        property_id, created = _find_or_insert_property(cur, item["occupation_address"], notes,
                                                          lonlat=item.get("lonlat"))
        dedup_key = f"gko263_expropriation:annex1:{item['seq']}"
        detail = json.dumps({
            "annex": 1, "name": item["name"], "compensation": False,
            "transfer_type": "state_to_municipal",
            "note": "Former Ukrainian-state-owned property; transferred to municipal "
                    "ownership outright, no compensation owed (not private property).",
        }, ensure_ascii=False)
        cur.execute(UPSERT_EVENT_SQL, (property_id, EVENT_DATE, source_doc_id, 0.9, detail, dedup_key))
        n_loaded += 1
        log.info("  annex1.%d %s property %d: %s", item["seq"],
                 "LOADED -> new" if created else "already exists, event re-upserted on existing",
                 property_id, item["occupation_address"])

    for item in ANNEX_2:
        if "near_match_property_id" in item:
            n_skipped += 1
            log.info("  SKIP annex2.%d (%s) -- unconfirmed near-match to existing property %d (%s), "
                     "not force-merged", item["seq"], item["occupation_address"],
                     item["near_match_property_id"], item["near_match_address"])
            continue
        notes = (f"Постановление ГКО ДНР №263 (29.09.2022), Приложение №2 п.{item['seq']}: "
                 f"{item['name']}. Privately-owned property, forced expropriation "
                 f"(\"принудительное изъятие\"); compensation contingent on owner submitting "
                 f"title documents within 30 days of the decree's effective date, or compensation "
                 f"right is forfeited entirely (§5-6).")
        if "confirmed_property_id" in item:
            property_id, created = item["confirmed_property_id"], False
            log.info("  MERGE annex2.%d (%s) -> confirmed existing property %d (Q8 resolved, "
                     "exact house-number match + map-confirmed dormitory)",
                     item["seq"], item["occupation_address"], property_id)
        else:
            property_id, created = _find_or_insert_property(cur, item["occupation_address"], notes)
        dedup_key = f"gko263_expropriation:annex2:{item['seq']}"
        detail = json.dumps({
            "annex": 2, "name": item["name"], "compensation": "contingent_30day_deadline",
            "transfer_type": "private_forced_expropriation",
            "note": "Privately-owned property forcibly expropriated; compensation owed only "
                    "if owner submitted title documents within 30 days, else forfeited (§5-6). "
                    "Registered occupants separately had 30 days to prove registration or lose "
                    "residency rights (§8).",
        }, ensure_ascii=False)
        cur.execute(UPSERT_EVENT_SQL, (property_id, EVENT_DATE, source_doc_id, 0.9, detail, dedup_key))
        n_loaded += 1
        if "confirmed_property_id" in item:
            verb = "MERGED into"
        else:
            verb = "LOADED -> new" if created else "already exists, event re-upserted on existing"
        log.info("  annex2.%d %s property %d: %s", item["seq"], verb, property_id, item["occupation_address"])

    pg.commit()
    log.info("done: %d new properties + expropriation events loaded, %d skipped (unconfirmed near-match)",
              n_loaded, n_skipped)
    print(f"load_gko263_expropriation: {n_loaded} loaded, {n_skipped} skipped of 13 total addresses")


if __name__ == "__main__":
    main()
