#!/usr/bin/env python3
"""Load the residential municipal->FEDERAL bulk real-estate transfers as
seizure_event(stage='federal_property_transfer') rows -- the broader
municipal->federal housing conveyor of which the named-military-unit
transfers (scripts/388, stage='military_transfer') are the security-service
subset. See docs/case_studies/chernomorskaya18_fsb_transfer.md (MUP-CS-011,
the "wider conveyor" section) and docs/legal_mechanisms_review.md rung [F2].

Source: 2 Мариупольский городской совет "Решение" PDFs (scripts/383 crawl,
scripts/06a OCR, surfaced by a full read-through of the scripts/387
classification corpus, 2026-07-20):
  - Решение №I/13-7 (10.06.2026): 11 apartments, ул. Куприна 25б (4) +
    ул. Куприна 27а (7), transferred to федеральную собственность on
    Распоряжение Росимущества ТУ ДНР 21.05.2026 №93-79-р/дсп.
  - Решение №I/14-4 (23.10.2025): 11 apartments, пр. Нахимова 25 (9) +
    ул. Якова Гугеля 29 (2), transferred to федеральную собственность on
    Обращение Росимущества ТУ ДНР 29.09.2025 №93-03/3976-дсп.

Hand-curated (not a general parser): only these two decisions in the
339-decision corpus carry a NAMED, cadastral-numbered RESIDENTIAL transfer
to the general federal treasury. The parallel municipal->DNR-republican-state
transfers of already-municipal NON-residential/land assets (I/7-6, I/6-6,
I/27-1, I/28-7, I/14-7, I/1-4) are deliberately NOT loaded -- see the
'federal_property_transfer' comment in db/schema.sql and MUP-CS-011 for why
(governmental reorganization of public assets, private-ownership provenance
unestablished -- a category error to record as a per-owner seizure).

The CADASTRAL NUMBER is the reliable per-unit key here (OCR-clean on every
row); the apartment number is used for the `unit` row only where the OCR of
the appendix table is legible. Two Куприна rows whose apartment number is
OCR-garbled ("РА", "п") are loaded as property-level events with the
cadastral number in detail and unit_id NULL rather than inventing an
apartment number -- flagged via detail.apt_ocr_garbled=true.

Per project convention this writes to the canonical Postgres spine and is NOT
run by Claude -- run it yourself after applying the schema migration:

    psql "$DATABASE_URL" -f db/schema.sql
    PYTHONPATH=src .venv312/bin/python scripts/389_load_federal_property_transfers.py --dry-run
    PYTHONPATH=src .venv312/bin/python scripts/389_load_federal_property_transfers.py
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
    _upsert_source_doc_by_sha,
)

log = logging.getLogger(__name__)

SHA_I_13_7 = "0117a745eeecef278f0c1a3a15da0c26d590c254deef61d12cb3fc05946fe9ea"  # 10.06.2026
SHA_I_14_4 = "269a7ea7c4ab646c072df17a2c29153a2870a7be638475ba0d5a8d814b3e6290"  # 23.10.2025

# Each decree: (decree_number, decree_date, sha, rosreestr_ref, signing_officials, units[])
# unit tuple: (building_id, occupation_address, apt_no_or_None, area_sqm, cadastral, apt_ocr_garbled)
DECREES = [
    {
        "decree_number": "I/13-7",
        "decree_date": "2026-06-10",
        "sha256": SHA_I_13_7,
        "rosreestr_ref": "Распоряжение Росимущества ТУ ДНР 21.05.2026 №93-79-р/дсп",
        "signing_officials": ["Кольцов А.В.", "Сенин Ю.А."],
        "control_officer": "Яремчук И.И.",
        "units": [
            ("STREET:куприна|25б", "улица Куприна, 25б", None, 78.4, "93:37:0010102:7945", True),
            ("STREET:куприна|25б", "улица Куприна, 25б", "44", 54.8, "93:37:0010102:7964", False),
            ("STREET:куприна|25б", "улица Куприна, 25б", "45", 54.2, "93:37:0010102:7965", False),
            ("STREET:куприна|25б", "улица Куприна, 25б", "60", 57.6, "93:37:0010102:7982", False),
            ("STREET:куприна|27а", "улица Куприна, 27а", None, 56.4, "93:37:0010102:7836", True),
            ("STREET:куприна|27а", "улица Куприна, 27а", "30", 56.6, "93:37:0010102:7857", False),
            ("STREET:куприна|27а", "улица Куприна, 27а", "44", 54.0, "93:37:0010102:7872", False),
            ("STREET:куприна|27а", "улица Куприна, 27а", "46", 70.8, "93:37:0010102:7874", False),
            ("STREET:куприна|27а", "улица Куприна, 27а", "50", 53.8, "93:37:0010102:7879", False),
            ("STREET:куприна|27а", "улица Куприна, 27а", "64", 56.5, "93:37:0010102:7894", False),
            ("STREET:куприна|27а", "улица Куприна, 27а", "79", 56.6, "93:37:0010102:7911", False),
        ],
    },
    {
        "decree_number": "I/14-4",
        "decree_date": "2025-10-23",
        "sha256": SHA_I_14_4,
        "rosreestr_ref": "Обращение Росимущества ТУ ДНР 29.09.2025 №93-03/3976-дсп",
        "signing_officials": ["Кольцов А.В.", "Сенин Ю.А."],
        "control_officer": "Яремчук И.И.",
        "units": [
            ("AVENUE:нахимова|25", "проспект Нахимова, 25", "21", 60.3, "93:37:0010409:1322", False),
            ("AVENUE:нахимова|25", "проспект Нахимова, 25", "22", 96.6, "93:37:0010409:1323", False),
            ("AVENUE:нахимова|25", "проспект Нахимова, 25", "34", 60.1, "93:37:0010409:1336", False),
            ("AVENUE:нахимова|25", "проспект Нахимова, 25", "47", 70.4, "93:37:0010409:1350", False),
            ("AVENUE:нахимова|25", "проспект Нахимова, 25", "75", 61.8, "93:37:0010409:1381", False),
            ("AVENUE:нахимова|25", "проспект Нахимова, 25", "88", 104.4, "93:37:0010409:1395", False),
            ("AVENUE:нахимова|25", "проспект Нахимова, 25", "104", 48.0, "93:37:0010409:1291", False),
            ("AVENUE:нахимова|25", "проспект Нахимова, 25", "108", 104.9, "93:37:0010409:1295", False),
            ("AVENUE:нахимова|25", "проспект Нахимова, 25", "113", 70.0, "93:37:0010409:1301", False),
            ("STREET:гугеля|29", "улица Якова Гугеля, 29", "8", 97.2, "93:37:0010307:702", False),
            ("STREET:гугеля|29", "улица Якова Гугеля, 29", "32", 98.6, "93:37:0010307:685", False),
        ],
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
    for dec in DECREES:
        source_doc_id = _upsert_source_doc_by_sha(cur, dec["sha256"])
        signing_actor_ids = [
            _upsert_actor(cur, name, "signing_official", None)
            for name in dec["signing_officials"]
        ]
        for i, (bid, occ, apt, area, cad, garbled) in enumerate(dec["units"], 1):
            property_id = _find_or_create_property(cur, bid, occupation_address=occ, cadastral_no=cad)
            unit_id = None
            if apt and not garbled:
                unit_id = _find_or_create_unit(cur, property_id, apt)

            dedup_key = f"federal_property_transfer:{dec['sha256']}:{cad}"
            detail = {
                "source": "gorsovet_reshenie",
                "decree_number": dec["decree_number"],
                "decree_kind": "federal_property_transfer",
                "recipient": "федеральная собственность (Росимущество ТУ ДНР)",
                "rosreestr_ref": dec["rosreestr_ref"],
                "control_officer": dec["control_officer"],
                "cadastral_number": cad,
                "property_type": "жилое помещение (квартира)",
                "area_sqm": area,
                "address_raw": occ + (f", кв. {apt}" if apt else ""),
                "apt_raw": apt,
                "apt_ocr_garbled": garbled,
                "case_study": "MUP-CS-011",
            }
            if not args.dry_run:
                cur.execute(
                    """INSERT INTO seizure_event
                           (property_id, unit_id, stage, event_date, source_doc_id,
                            confidence, detail, dedup_key)
                       VALUES (%s, %s, 'federal_property_transfer'::seizure_stage, %s, %s, %s, %s, %s)
                       ON CONFLICT (dedup_key) DO UPDATE
                           SET property_id   = EXCLUDED.property_id,
                               unit_id       = EXCLUDED.unit_id,
                               stage         = EXCLUDED.stage,
                               event_date    = EXCLUDED.event_date,
                               source_doc_id = EXCLUDED.source_doc_id,
                               confidence    = EXCLUDED.confidence,
                               detail        = EXCLUDED.detail
                       RETURNING id""",
                    (property_id, unit_id, dec["decree_date"], source_doc_id,
                     0.9 if not garbled else 0.75,
                     json.dumps(detail, ensure_ascii=False), dedup_key),
                )
                event_id = cur.fetchone()[0]
                for actor_id in signing_actor_ids:
                    if actor_id:
                        cur.execute(
                            """INSERT INTO event_actor (seizure_event_id, actor_id)
                               VALUES (%s, %s) ON CONFLICT DO NOTHING""",
                            (event_id, actor_id),
                        )
            loaded += 1
            log.info("%s %s pid=%s unit=%s apt=%s cad=%s",
                      "[DRY]" if args.dry_run else "load",
                      dec["decree_number"], property_id, unit_id, apt or "(garbled)", cad)

    if not args.dry_run:
        con.commit()
    con.close()
    log.info("%s: %d federal_property_transfer events", "[DRY RUN]" if args.dry_run else "done", loaded)
    print(f"{'[DRY RUN] would load' if args.dry_run else 'loaded'} {loaded} "
          f"federal_property_transfer events (2 decrees, 4 buildings)")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
