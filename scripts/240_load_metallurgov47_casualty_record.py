#!/usr/bin/env python3
"""Load the civilian-casualty record into the Postgres spine for the
пр. Металлургов, 47 (ТСЖ «Троянда-М») case study (user-supplied 2026-07-03).

Sources captured by scripts/239_capture_metallurgov47_casualty_record.py:
  - mariupoldestruction.com's published victims spreadsheet ("Поименный
    список жертв") -- the attributing source for the whole record, per the
    user's explicit request to credit "Mariupol Destruction and Victims
    Map" (https://www.mariupoldestruction.com).
  - memorial.ua obituary for Фёдорова Надежда.
  - t.me/mariupolRIP posts 19075, 19202, 25434, 30852, 44164, 44185.

8 named deceased, all at prosp. Metallurgov, 47 (property_id 4529, verified
via manual Google Earth geocode override, see
data/parsed/manual_geocode_overrides.jsonl). One record, all 8 names in the
detail payload -- mirrors the shared-record pattern used in
scripts/163_load_lenina_casualty_record.py.

kind='civilian_casualty' -- established precedent, see scripts/163.

PRIVACY: these are DECEASED individuals named in a public victims registry,
public Telegram posts, and a public obituary site -- not the project's
"living private owner" minimization rule (CLAUDE.md PRIVACY section), which
applies only to living owners. Naming deceased civilians is the documentary
point of this record.

Per project convention (CLAUDE.md "Generate scripts; do NOT auto-run
pandas/analysis. Let the user execute."), this writes to the canonical
Postgres spine and is NOT run by Claude -- run it yourself:

    PYTHONPATH=src python scripts/240_load_metallurgov47_casualty_record.py --dry-run
    PYTHONPATH=src python scripts/240_load_metallurgov47_casualty_record.py
"""
import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402
from mariupol_seizures.db.load import _upsert_source_doc_by_sha  # noqa: E402

log = logging.getLogger(__name__)

PROPERTY_ID = 4529  # prosp. Metallurgov, 47 -- see manual_geocode_overrides.jsonl

# SHA-256s -- from scripts/239's 2026-07-03 run (data/raw/ + state.sqlite
# source_document; re-verify if 239 is ever re-run and produces different
# hashes, e.g. if mariupoldestruction.com's spreadsheet content changes).
SHA_MARIUPOLDESTRUCTION_TSV = "3b10d33f56cd47496a6f9a095ff487c818418f3acc724e61901f9cd009149ff5"
SHA_MEMORIAL_UA = "4c533ad8d4dcbcae91e3730f9dc4dd67033f9a38e5db13dcd62b9bb13fdbcec1"
SHA_MARIUPOLRIP = {
    "https://t.me/mariupolRIP/19075": "6411cecc61dcb7fbb3a4db6f50683142b5f64276746c457103cb7e18227276d5",
    "https://t.me/mariupolRIP/19202": "3b5a330494626e52bfca5eb9ede6ab699dba62f1a6d890410ef5c5467ca0c4f6",
    "https://t.me/mariupolRIP/25434": "75273a2860d353939b07c1595d859c5054d3dafe8cf927fd99b99b3ed03fb883",
    "https://t.me/mariupolRIP/30852": "61bcb2d1186d91ec7ebd6df58e43e647de66a5ee5727bf84426ad6c9d794a323",
    "https://t.me/mariupolRIP/44164": "295fb7677aa7e6cb33506ef70f39ecb05904f8e4d845abb68a4ff9c9520d6ccd",
    "https://t.me/mariupolRIP/44185": "28c6f781abe262f7c1c1870e5462cee0a30a2f1ffbc35e8cd3e5e96042575939",
}

DETAIL = {
    "title": "Погибшие, пр. Металлургов 47",
    "attributed_to": "Mariupol Destruction and Victims Map "
                      "(https://www.mariupoldestruction.com)",
    "deceased": [
        {
            "name": "Фёдорова Надежда",
            "dates": "04.10.1938 - 01-03.03.2022",
            "circumstance": "Во время обстрела выбило окна, ранило "
                             "осколками стекла, остановилось сердце.",
            "burial": "Похоронили возле дома, в ковре. Перезахоронение "
                       "неизвестно.",
            "source_url": "https://memorial.ua/obituaries/civilians/"
                           "kfedorova-nadiia-12510",
        },
        {
            "name": "Харакоз Наталья Георгиевна",
            "dates": "13.07.1935 - 29.03.2022",
            "circumstance": "Известная в Мариуполе писательница и "
                             "журналистка. Умерла от стресса, условий, "
                             "нехватки медикаментов.",
            "burial": "Похоронили в общей могиле во дворе Металлургов, 47. "
                       "Позднее перезахоронена на Старокрымском кладбище "
                       "(сектор 17, квадрат 25, крайний ряд, могила 6) -- "
                       "могилу смогли найти потому, что соседка перед "
                       "захоронением в братской могиле положила ей в "
                       "карман записку с ФИО.",
            "source_url": "https://t.me/mariupolRIP/25434",
            "additional_source": "от внучки (granddaughter, direct)",
        },
        {
            "name": "Тёрин Александр Евгеньевич",
            "dates": None,
            "circumstance": "Тело нашли при разборе завалов.",
            "burial": None,
            "source_url": "https://t.me/mariupolRIP/19202",
        },
        {
            "name": "Тёрина Елена Александровна",
            "dates": None,
            "circumstance": "Тело нашли при разборе завалов.",
            "burial": None,
            "source_url": "https://t.me/mariupolRIP/19202",
        },
        {
            "name": "Иванов Максим Владимирович",
            "dates": None,
            "circumstance": "Погиб 17.03.2022 в результате авианалета "
                             "вместе с мамой Людмилой (Людмила не имеет "
                             "отдельной строки в источнике).",
            "burial": None,
            "source_url": "https://t.me/mariupolRIP/19075",
            "additional_source": "https://t.me/mariupolRIP/44185",
        },
        {
            "name": "Паскаль Мария",
            "dates": None,
            "circumstance": "Погибла 24.03.2022 при обстреле, готовила во "
                             "дворе. Супруг(а) -- Галушко Андрей (below), "
                             "то же место гибели и захоронения.",
            "burial": "Металлургов 47 (courtyard, per shared death/burial "
                       "address in source).",
            "source_url": "https://t.me/mariupolRIP/30852",
            "additional_source": "от соседей (neighbours, direct)",
        },
        {
            "name": "Галушко Андрей",
            "dates": None,
            "circumstance": "Погиб 24.03.2022 при обстреле, готовил во "
                             "дворе. Супруг(а) -- Паскаль Мария (above), "
                             "то же место гибели и захоронения.",
            "burial": "Металлургов 47 (courtyard, per shared death/burial "
                       "address in source).",
            "source_url": "https://t.me/mariupolRIP/30852",
            "additional_source": "от соседей (neighbours, direct)",
        },
        {
            "name": "Горлачова Раиса Дмитриевна",
            "dates": "07.02.1942 - 17.03.2022",
            "circumstance": None,
            "burial": None,
            "source_url": "https://t.me/mariupolRIP/44164",
        },
    ],
    "courtyard_burial_sites_documented": 2,
    "note": "Building demolished 10-25.12.2022 per KrashMash video evidence "
            "and court record (case 33-2575/2025); no exhumation record has "
            "been located for Фёдорова Надежда's grave as of this session.",
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    missing = [k for k, v in SHA_MARIUPOLRIP.items() if v is None]
    if SHA_MARIUPOLDESTRUCTION_TSV is None or SHA_MEMORIAL_UA is None or missing:
        log.error(
            "SHA-256 placeholders not filled in. Run "
            "scripts/239_capture_metallurgov47_casualty_record.py first, "
            "then paste its logged SHA-256 values into this script's "
            "SHA_MARIUPOLDESTRUCTION_TSV / SHA_MEMORIAL_UA / "
            "SHA_MARIUPOLRIP constants before running this loader."
        )
        sys.exit(1)

    import psycopg2
    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()

    dedup_key = f"civilian_casualty:metallurgov_47:{PROPERTY_ID}"
    if not args.dry_run:
        source_doc_id = _upsert_source_doc_by_sha(cur, SHA_MARIUPOLDESTRUCTION_TSV)
        cur.execute(
            """INSERT INTO corroboration
                   (property_id, kind, reference, detail, dedup_key,
                    captured_at, source_doc_id, confidence, verdict)
               VALUES (%s, 'civilian_casualty', %s, %s, %s, now(),
                       %s, %s, 'confirms')
               ON CONFLICT (dedup_key) DO UPDATE SET
                   detail = EXCLUDED.detail,
                   source_doc_id = EXCLUDED.source_doc_id""",
            (PROPERTY_ID, "Mariupol Destruction and Victims Map "
                          "(mariupoldestruction.com) / mariupolRIP / memorial.ua",
             json.dumps(DETAIL, ensure_ascii=False), dedup_key,
             source_doc_id, 0.8),
        )
        con.commit()
    log.info("%s property_id %s -> dedup_key=%s (8 named deceased)",
              "[DRY RUN] would load" if args.dry_run else "loaded",
              PROPERTY_ID, dedup_key)

    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
