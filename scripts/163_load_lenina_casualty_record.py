#!/usr/bin/env python3
"""Load a civilian-casualty record into the Postgres spine for the
пр. Ленина(Мира) 104/106/108/110 case study (user-supplied 2026-06-19).

Sources captured by scripts/162_capture_lenina110_casualty_record.py:
  - t.me/mariupolRIP/36979, t.me/mariupolRIP/37382 (two of the six named
    deceased)
  - the mariupoldestruction.com "Погибшие" Google My Maps layer, which
    independently corroborates multiple "Мира, 110" entries

Per the user's explicit choice (asked directly, given several prior
building-attribution corrections in this case study): this is recorded as a
SHARED finding across all four buildings (104/106/108/110), not pinned to
one -- the document title and most named individuals point to building 110,
but the makeshift grave the user found is in 106's courtyard, so one
dedup_key/property_id pinning would misrepresent the other buildings'
involvement. This script writes one corroboration row per property_id
(4417/4419/4421/4423), each carrying the SAME full detail payload, so the
record is queryable from any of the four buildings.

NOT loaded: a YouTube video (AmPu1gRLh-M) showing bodies wrapped in
blankets in 108's courtyard -- user confirmed this is NOT the original
source video, just a lead pending verification. Add it in a follow-on load
once/if the original source is located; do not cite it as evidence before then.

kind='civilian_casualty' is a NEW corroboration kind (not previously used in
this project) -- there is no prior precedent table to match against, so this
is added straightforwardly per the existing kind column's free-text comment
in db/schema.sql.

Idempotent: dedup_key per property_id, INSERT ... ON CONFLICT DO NOTHING
against corroboration_dedup_uidx. Safe to re-run.

PRIVACY: these are DECEASED individuals named in public Telegram posts and a
public memorial map (mariupoldestruction.com) -- not the project's "living
private owner" minimization rule (CLAUDE.md PRIVACY section), which applies
only to living owners. Naming deceased civilians is the documentary point of
this record.

Per project convention (CLAUDE.md "Generate scripts; do NOT auto-run
pandas/analysis. Let the user execute."), this writes to the canonical
Postgres spine and is NOT run by Claude -- run it yourself:

    PYTHONPATH=src python scripts/163_load_lenina_casualty_record.py
    PYTHONPATH=src python scripts/163_load_lenina_casualty_record.py --dry-run
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

# property_id for пр. Ленина 104/106/108/110 (see memory/lenina106_*)
PROPERTY_IDS = {"104": 4417, "106": 4419, "108": 4421, "110": 4423}

# SHA-256s from scripts/162's run output -- update if that script is re-run
# and produces different hashes (it shouldn't, since these sources don't
# carry the t.me byte-instability issue documented for the resale-listing
# captures -- but re-verify against data/state.sqlite source_document if in doubt).
SHA_MARIUPOLRIP_36979 = "5c01848684e4c5156183f7253945cb6fce86b683c9cdf1c4885aad69b5c4f69d"
SHA_MARIUPOLRIP_37382 = "40fec819d368217051b140c61e6e776abb9015bdb962c233ae22fe4e3d4d54de"
SHA_GMYMAPS_PAGE = "c1f20d234cd22806c50bd03d1e6a41bcce9a0259652975114275790238aa17f6"

DETAIL = {
    "title": "Погибшие 6ч. Мира, 110",
    "attributed_to": "mariupoldestruction.com",
    "deceased": [
        {
            "name": "Глушко Анатолий Петрович",
            "dates": "01.07.1937-17.03.2022",
            "circumstance": "Умер в подвале от получения травмы головы "
                             "взрывной волны. Тело подняли в квартиру. "
                             "Захоронить не получилось из-за обстрелов, "
                             "пр-т Мира 110.",
            "source_url": "https://t.me/mariupolRIP/36979",
        },
        {
            "name": "Хильдунин Евгений Александрович",
            "dates": "b. 17.05.1985",
            "circumstance": "Умер в доме проспект Мира 110, вынесен был в "
                             "обувной магазин, забрали перед паской МЧС.",
            "source_url": "https://t.me/mariupolRIP/37382",
        },
        {
            "name": "Малюха Анатолий",
            "dates": "b. 1943, инвалид по ногам",
            "circumstance": "\"живьем сгорел мой сосед д.Толя инвалид на "
                             "ноги 1943г.р\" -- user-supplied quote, no "
                             "independent source link given.",
            "source_url": None,
        },
        {
            "name": "[сестра Коваленко Инги Евг.] (имя не указано)",
            "dates": None,
            "circumstance": "Коваленко Инга Евг. (1975 г.р.): \"24 марта "
                             "22г. у третьего подъезда снайпер убил мою "
                             "сестру, тело трое суток лежало по пр.Мира "
                             "110. Ее паспорт и телефон продали: 16 апреля "
                             "2022г. по нему была получена гум-помощь.\" "
                             "Sniper killing near the 3rd entrance; body "
                             "lay in place 3 days; identity documents/phone "
                             "later sold and used to fraudulently obtain "
                             "humanitarian aid.",
            "source_url": None,
        },
        {
            "name": "Афонин Пётр",
            "dates": None,
            "circumstance": "Проживал по адресу пр. Ленина 110, кв. 127, "
                             "с Афониной Клавдией (below).",
            "source_url": None,
        },
        {
            "name": "Афонина Клавдия",
            "dates": None,
            "circumstance": "Проживала по адресу пр. Ленина 110, кв. 127, "
                             "с Афониным Пётром (above).",
            "source_url": None,
        },
    ],
    "makeshift_grave": {
        "location": "courtyard of building 106",
        "source_url": "https://www.google.com/maps/d/u/0/viewer?mid="
                       "1n0elDNzvK4vQYmWxCn2792ljSXNJK4x3&"
                       "ll=47.098102420177995,37.51938978751018&z=18",
    },
    "unverified_lead_not_loaded": {
        "description": "Video reportedly showing bodies wrapped in "
                        "blankets in 108's courtyard -- NOT the original "
                        "source video per the user (2026-06-19); kept on "
                        "record as a lead only, not cited as evidence.",
        "url": "https://www.youtube.com/watch?v=AmPu1gRLh-M",
    },
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    import psycopg2
    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()

    n_loaded = 0
    for building, pid in PROPERTY_IDS.items():
        dedup_key = f"civilian_casualty:lenina_104_106_108_110:{pid}"
        if not args.dry_run:
            source_doc_id = _upsert_source_doc_by_sha(cur, SHA_GMYMAPS_PAGE)
            cur.execute(
                """INSERT INTO corroboration
                       (property_id, kind, reference, detail, dedup_key,
                        captured_at, source_doc_id, confidence, verdict)
                   VALUES (%s, 'civilian_casualty', %s, %s, %s, now(),
                           %s, %s, 'confirms')
                   ON CONFLICT (dedup_key) DO UPDATE SET
                       detail = EXCLUDED.detail,
                       source_doc_id = EXCLUDED.source_doc_id""",
                (pid, "mariupoldestruction.com / mariupolRIP",
                 json.dumps(DETAIL, ensure_ascii=False), dedup_key,
                 source_doc_id, 0.8),
            )
        n_loaded += 1
        log.info("%s building %s (property_id %s) -> dedup_key=%s",
                  "[DRY RUN] would load" if args.dry_run else "loaded",
                  building, pid, dedup_key)

    if not args.dry_run:
        con.commit()
    con.close()
    log.info("done: %d rows %s", n_loaded, "would be loaded" if args.dry_run else "loaded")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
