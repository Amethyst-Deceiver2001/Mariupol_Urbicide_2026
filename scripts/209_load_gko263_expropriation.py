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
have loose near-matches by street + rounded house number but unconfirmed
building identity (different suffix letters in the existing spine entries)
-- per the project's no-false-precision rule, these are logged and SKIPPED,
not force-merged into an existing property_id. A future manual/geocoded
review could confirm or reject the match.

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
     "near_match_property_id": 5816, "near_match_address": "проспект Лунина, 9а"},
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
     "name": "Общежитие", "near_match_property_id": 5672, "near_match_address": "улица Карпинского, 84"},
    {"seq": 4, "occupation_address": "город Мариуполь, Ильичевский район, улица Сеченова, дом 81",
     "name": "Общежитие", "near_match_property_id": 5759, "near_match_address": "улица Сеченова, 81"},
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
        cur.execute(INSERT_PROPERTY_SQL, (item["occupation_address"], notes))
        property_id = cur.fetchone()[0]
        dedup_key = f"gko263_expropriation:annex1:{item['seq']}"
        detail = json.dumps({
            "annex": 1, "name": item["name"], "compensation": False,
            "transfer_type": "state_to_municipal",
            "note": "Former Ukrainian-state-owned property; transferred to municipal "
                    "ownership outright, no compensation owed (not private property).",
        }, ensure_ascii=False)
        cur.execute(UPSERT_EVENT_SQL, (property_id, EVENT_DATE, source_doc_id, 0.9, detail, dedup_key))
        n_loaded += 1
        log.info("  LOADED annex1.%d -> new property %d: %s", item["seq"], property_id, item["occupation_address"])

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
        cur.execute(INSERT_PROPERTY_SQL, (item["occupation_address"], notes))
        property_id = cur.fetchone()[0]
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
        log.info("  LOADED annex2.%d -> new property %d: %s", item["seq"], property_id, item["occupation_address"])

    pg.commit()
    log.info("done: %d new properties + expropriation events loaded, %d skipped (unconfirmed near-match)",
              n_loaded, n_skipped)
    print(f"load_gko263_expropriation: {n_loaded} loaded, {n_skipped} skipped of 13 total addresses")


if __name__ == "__main__":
    main()
