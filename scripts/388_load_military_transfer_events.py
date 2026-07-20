#!/usr/bin/env python3
"""Load the 4 confirmed municipal-to-military real-estate transfers as
seizure_event(stage='military_transfer') rows -- MUP-CS-011, see
docs/case_studies/chernomorskaya18_fsb_transfer.md for the full write-up
and docs/legal_mechanisms_review.md rung [F2] for the mechanism.

Source: 3 Мариупольский городской совет "Решение" PDFs (scripts/383 crawl,
scripts/06a OCR, scripts/387 classification -- category federal_transfer).
Hand-curated, not a general parser, because only 3 of the 339 decisions in
this corpus carry a NAMED, cadastral-numbered REAL-ESTATE transfer to a
military/security unit; the remaining federal_transfer hits move
construction MATERIALS (no property_id, no address -- deliberately not
loaded here, see db/schema.sql's 'military_transfer' comment and the case
study's §5).

Records:
  1. ул. Черноморская, 18, кв. 24 -> в/ч 1297 (Решение №I/5-5, 12.03.2026)
  2. пр. Ленина, 101, кв. 21      -> в/ч 1297 (Решение №I/1-2, 22.01.2026)
  3. ул. Чкалова, 23/25 (нежилое) -> в/ч 1297 (Решение №I/1-2, 22.01.2026)
  4. пер. Киевский, 10А (нежилое) -> в/ч 76835 (Решение №I/11-2, 14.05.2026)

в/ч 1297 loaded as actor role='beneficiary' with FSB-ownership attribution
(OpenSanctions/EGRUL, see case study §4) recorded in notes; в/ч 76835 the
same but without a confirmed parent-agency attribution. Commanders/signing
officials named in the decisions are loaded as role='signing_official' /
'beneficiary'-adjacent actors per CLAUDE.md (named officials/beneficiaries
acting in official capacity are in scope for accountability -- this is not
the living-owner privacy rule).

Per project convention (CLAUDE.md "Generate scripts; do NOT auto-run
pandas/analysis. Let the user execute."), this writes to the canonical
Postgres spine and is NOT run by Claude -- run it yourself, after applying
the schema migration:

    psql "$DATABASE_URL" -f db/schema.sql
    PYTHONPATH=src .venv312/bin/python scripts/388_load_military_transfer_events.py --dry-run
    PYTHONPATH=src .venv312/bin/python scripts/388_load_military_transfer_events.py
"""
import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402
from mariupol_seizures.db.load import (  # noqa: E402
    _find_or_create_property,
    _find_or_create_unit,
    _upsert_actor,
    _upsert_beneficiary,
    _upsert_source_doc_by_sha,
)

log = logging.getLogger(__name__)

# SHA-256s from data/state.sqlite's source_document table (scripts/383
# crawl), source_type='mariupol_gorsovet_reshenie_pdf' -- re-verify if 383
# is ever re-run against a changed source.
SHA_I_5_5 = "f3c23e88ebb32bf45cb2ba7c269a02e0b162410eed9d26eef25e7b3123713217"    # 12.03.2026
SHA_I_1_2 = "1dc26b50f60ef4486e6e51f81f30d4550e16268fbfd390e28cbf402d4191a2e3"    # 22.01.2026
SHA_I_11_2 = "17697d1702fffa7d2ee670618e7ea1314de7c6b8cf9f238149db389734c7d9f4"  # 14.05.2026

VCH_1297_NOTES = (
    "ИНН 9310007740 | ОГРН 1239300004866 | registered 22.05.2023 | "
    "legal address ДНР, Старобешевский р-н, с. Победа, ул. Ленина, 35 | "
    "ОКВЭД 84.22 (обеспечение военной безопасности) | acting commander of "
    "record 25.08.2025: Ладнов Сергей Сергеевич | FSB ownership per "
    "OpenSanctions/EGRUL (https://www.opensanctions.org/entities/"
    "ru-inn-9310007740/) -- NOT independently re-verified beyond "
    "OpenSanctions/EGRUL, see case study §4"
)
VCH_76835_NOTES = (
    "Recipient of пер. Киевский, 10А non-residential space (Решение "
    "№I/11-2, 14.05.2026) -- registration particulars and any parent-agency "
    "affiliation not yet independently researched beyond this decision"
)

RECORDS = [
    {
        "key": "chernomorskaya_18_kv24",
        "building_id": "STREET:черноморская|18",
        "occupation_address": "улица Черноморская, 18",
        "apt_no": "24",
        "cadastral_no": "93:37:0010410:1856",
        "area_sqm": 54.59,
        "property_type": "жилое помещение (квартира)",
        "decree_number": "I/5-5",
        "decree_date": "2026-03-12",
        "sha256": SHA_I_5_5,
        "recipient_unit": "ФГКУ «Войсковая часть 1297»",
        "recipient_inn": "9310007740",
        "recipient_ogrn": "1239300004866",
        "recipient_notes": VCH_1297_NOTES,
        "requesting_officer": "врио командира в/ч 1297, №23/1РЦ/б-2440, 29.11.2025",
        "signing_officials": ["Кольцов А.В.", "Сенин Ю.А."],
    },
    {
        "key": "lenina_101_kv21",
        "building_id": "AVENUE:ленина|101",
        "occupation_address": "проспект Ленина, 101",
        "apt_no": "21",
        "cadastral_no": "93:37:0010106:504",
        "area_sqm": 101.6,
        "property_type": "жилое помещение (квартира)",
        "decree_number": "I/1-2",
        "decree_date": "2026-01-22",
        "sha256": SHA_I_1_2,
        "recipient_unit": "ФГКУ «Войсковая часть 1297»",
        "recipient_inn": "9310007740",
        "recipient_ogrn": "1239300004866",
        "recipient_notes": VCH_1297_NOTES,
        "requesting_officer": (
            "в/ч 1297 запрос №174-дсп, 16.07.2025; также Территориальное "
            "управление Федерального агентства по управлению государственным "
            "имуществом в ДНР (Росимущество), 15.12.2025"
        ),
        "signing_officials": ["Кольцов А.В.", "Сенин Ю.А."],
    },
    {
        "key": "chkalova_23_25",
        "building_id": "STREET:чкалова|23/25",
        "occupation_address": "улица Чкалова, 23/25",
        "apt_no": None,
        "cadastral_no": "93:37:0010313:354",
        "area_sqm": 2.72,
        "property_type": "нежилое помещение (гараж/хоз. постройка)",
        "decree_number": "I/1-2",
        "decree_date": "2026-01-22",
        "sha256": SHA_I_1_2,
        "recipient_unit": "ФГКУ «Войсковая часть 1297»",
        "recipient_inn": "9310007740",
        "recipient_ogrn": "1239300004866",
        "recipient_notes": VCH_1297_NOTES,
        "requesting_officer": (
            "в/ч 1297 запрос №174-дсп, 16.07.2025; также Территориальное "
            "управление Федерального агентства по управлению государственным "
            "имуществом в ДНР (Росимущество), 15.12.2025"
        ),
        "signing_officials": ["Кольцов А.В.", "Сенин Ю.А."],
    },
    {
        "key": "kievskiy_10a",
        "building_id": "LANE:киевский|10а",
        "occupation_address": "переулок Киевский, 10А",
        "apt_no": None,
        "cadastral_no": "93:37:0010313:1069",
        "area_sqm": 430.0,
        "property_type": "нежилое помещение (1-й/2-й этаж)",
        "decree_number": "I/11-2",
        "decree_date": "2026-05-14",
        "sha256": SHA_I_11_2,
        "recipient_unit": "ФГКУ «Войсковая часть 76835»",
        "recipient_inn": None,
        "recipient_ogrn": None,
        "recipient_notes": VCH_76835_NOTES,
        "requesting_officer": None,
        "signing_officials": ["Кольцов А.В.", "Сенин Ю.А."],
    },
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    import psycopg2
    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()

    loaded = 0
    for rec in RECORDS:
        property_id = _find_or_create_property(
            cur, rec["building_id"], occupation_address=rec["occupation_address"],
            cadastral_no=rec["cadastral_no"],
        )
        unit_id = None
        if rec["apt_no"]:
            unit_id = _find_or_create_unit(cur, property_id, rec["apt_no"])

        source_doc_id = _upsert_source_doc_by_sha(cur, rec["sha256"])
        recipient_actor_id = _upsert_beneficiary(
            cur, rec["recipient_unit"], inn=rec["recipient_inn"],
            ogrn=rec["recipient_ogrn"], extra=rec["recipient_notes"],
        )
        signing_actor_ids = [
            _upsert_actor(cur, name, "signing_official", None)
            for name in rec["signing_officials"]
        ]

        dedup_key = f"military_transfer:{rec['sha256']}:{rec['key']}"
        detail = {
            "source": "gorsovet_reshenie",
            "decree_number": rec["decree_number"],
            "decree_kind": "military_transfer",
            "recipient_unit": rec["recipient_unit"],
            "requesting_officer": rec["requesting_officer"],
            "cadastral_number": rec["cadastral_no"],
            "property_type": rec["property_type"],
            "area_sqm": rec["area_sqm"],
            "address_raw": rec["occupation_address"]
                            + (f", кв. {rec['apt_no']}" if rec["apt_no"] else ""),
            "apt_raw": rec["apt_no"],
            "case_study": "MUP-CS-011",
        }

        if not args.dry_run:
            cur.execute(
                """INSERT INTO seizure_event
                       (property_id, unit_id, stage, event_date, source_doc_id,
                        confidence, detail, dedup_key)
                   VALUES (%s, %s, 'military_transfer'::seizure_stage, %s, %s, %s, %s, %s)
                   ON CONFLICT (dedup_key) DO UPDATE
                       SET property_id   = EXCLUDED.property_id,
                           unit_id       = EXCLUDED.unit_id,
                           stage         = EXCLUDED.stage,
                           event_date    = EXCLUDED.event_date,
                           source_doc_id = EXCLUDED.source_doc_id,
                           confidence    = EXCLUDED.confidence,
                           detail        = EXCLUDED.detail
                   RETURNING id""",
                (property_id, unit_id, rec["decree_date"], source_doc_id, 0.95,
                 json.dumps(detail, ensure_ascii=False), dedup_key),
            )
            event_id = cur.fetchone()[0]
            for actor_id in [recipient_actor_id, *signing_actor_ids]:
                if actor_id:
                    cur.execute(
                        """INSERT INTO event_actor (seizure_event_id, actor_id)
                           VALUES (%s, %s) ON CONFLICT DO NOTHING""",
                        (event_id, actor_id),
                    )

        loaded += 1
        log.info("%s property_id=%s unit_id=%s -> %s (%s)",
                  "[DRY RUN] would load" if args.dry_run else "loaded",
                  property_id, unit_id, rec["recipient_unit"], dedup_key)

    if not args.dry_run:
        con.commit()
    con.close()
    log.info("%s: %d military_transfer events", "[DRY RUN]" if args.dry_run else "done", loaded)
    print(f"{'[DRY RUN] would load' if args.dry_run else 'loaded'} {loaded} military_transfer events")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
