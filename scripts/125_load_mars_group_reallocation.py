#!/usr/bin/env python3
"""Load missing reallocation events for mar-s.group projects.

Three "Проектная декларация" PDFs were captured from mar-s.group (script
124) confirming new-build reallocation for properties already on the
spine. One (RPD 93-000013, Нахимова 101Б -> pid=4560) was already loaded
via ЕИСЖС (script 72). Two are NOT yet loaded:

  RPD 93-000012 "Нахимов" (ул. Апатова, 121) -> pid=13980
    cadastral 93:37:0010105:886, developer СЗ ТЕМП (ИНН 9310011351,
    ОГРН 1239300017197). Declaration dated 25.11.2025. Sister parcel to
    93:37:0010105:887 (Нахимова 101Б, already loaded) -- same complex
    split across two adjoining cadastral parcels, registered 15 days apart.

  RPD 93-000017 "Горизонт" (б-р Богдана Хмельницкого, 33Б) -> pid=4333
    cadastral 93:37:0010103:2199, developer СЗ ТЕМП-80 (ИНН 9310011376,
    ОГРН 1239300017230). Declaration dated 10.11.2025. Companion
    declaration to RPD 93-000016 (Ленина 86А -> pid=4484, already loaded)
    under the same "Горизонт" project name.

Run:
    python scripts/125_load_mars_group_reallocation.py [--dry-run]
"""
import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402

log = logging.getLogger(__name__)

RECORDS = [
    {
        "property_id": 13980,
        "rpd_num": "93-000012",
        "rpd_date": "2025-11-25",
        "rpd_project_title": (
            "Жилой комплекс \"Нахимов\", расположенный по адресу: Российская "
            "Федерация, Донецкая Народная Республика, г. Мариуполь, ул. "
            "Апатова, д.121"
        ),
        "address_raw": "ул. Апатова, д.121",
        "cadastral": "93:37:0010105:886",
        "developer": "СЗ ТЕМП",
        "developer_inn": "9310011351",
        "developer_ogrn": "1239300017197",
        "sha256": "4c2a129cf34a38efa929e058efb561b289e99a2a820576ea71caf3b65d2d08cb",
        "source_url": "https://mar-s.group/upload/iblock/dec/gf7l30bk0wywd0c7bldns3ewf3a2q1c7.pdf",
        "sister_cadastral": "93:37:0010105:887 (Нахимова 101Б, pid=4560, already loaded RPD 93-000013)",
    },
    {
        "property_id": 4333,
        "rpd_num": "93-000017",
        "rpd_date": "2025-11-10",
        "rpd_project_title": (
            "Многоквартирный жилой дом по адресу Донецкая Народная "
            "Республика, городской округ Мариуполь, город Мариуполь, "
            "Жовтневый район, б-р Богдана Хмельницкого, д. 33 Б"
        ),
        "address_raw": "б-р Богдана Хмельницкого, д. 33 Б",
        "cadastral": "93:37:0010103:2199",
        "developer": "СЗ ТЕМП-80",
        "developer_inn": "9310011376",
        "developer_ogrn": "1239300017230",
        "sha256": "9d8d26a2e9ea54448c4a4a3f879409d3e797e35fa2c4e960bcf8f1b177e3bc7e",
        "source_url": "https://mar-s.group/upload/iblock/b7c/le8uy4jz8br72hbguf84fqkpedmv80ox.pdf",
        "sister_cadastral": None,
    },
]

# NOTE: sha256 values above are the PDF-content hashes already captured by
# script 124's forensics.capture_source(); _upsert_source_doc_by_sha looks
# them up by content hash, not URL, so source_url is informational only.


def main(dry_run: bool = False) -> None:
    if dry_run:
        for r in RECORDS:
            print(f"  pid={r['property_id']}  RPD {r['rpd_num']}  cadastral={r['cadastral']}")
        return

    import psycopg2
    from mariupol_seizures.db.load import _upsert_source_doc_by_sha  # noqa: E402

    conn = psycopg2.connect(config.DATABASE_URL)
    cur  = conn.cursor()

    loaded = 0
    for r in RECORDS:
        src_doc_id = _upsert_source_doc_by_sha(cur, r["sha256"])
        detail = json.dumps({
            "source": "mar_s_group_proektnaya_deklaratsiya",
            "rpd_num": r["rpd_num"],
            "rpd_date": r["rpd_date"],
            "rpd_project_title": r["rpd_project_title"],
            "address_raw": r["address_raw"],
            "cadastral": r["cadastral"],
            "developer": r["developer"],
            "developer_inn": r["developer_inn"],
            "developer_ogrn": r["developer_ogrn"],
            "sister_cadastral": r["sister_cadastral"],
            "evidentiary_note": (
                "Official ФЗ-214 project declaration captured from the "
                "developer's own marketing site (mar-s.group), confirming "
                "new-build reallocation on this demolished/seized parcel. "
                "Same RPD-number scheme as ЕИСЖС script-72 loads; this row "
                "fills a gap the original ЕИСЖС crawl had not yet captured."
            ),
        }, ensure_ascii=False)
        dedup_key = f"mars_group_rpd_{r['rpd_num']}"
        cur.execute("""
            INSERT INTO seizure_event
              (property_id, stage, event_date, detail, source_doc_id, dedup_key)
            VALUES (%s, 'reallocation', %s, %s, %s, %s)
            ON CONFLICT (dedup_key) DO UPDATE
                SET detail = EXCLUDED.detail, event_date = EXCLUDED.event_date
        """, (r["property_id"], r["rpd_date"], detail, src_doc_id, dedup_key))
        loaded += 1
        log.info("loaded pid=%d RPD %s", r["property_id"], r["rpd_num"])

    conn.commit()
    conn.close()
    print(f"\n{'='*60}")
    print(f"mar-s.group reallocation load complete: {loaded} rows")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
