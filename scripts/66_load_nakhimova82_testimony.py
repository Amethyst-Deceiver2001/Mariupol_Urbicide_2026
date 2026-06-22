#!/usr/bin/env python3
"""Load two corroboration(kind='testimony_ref') rows for property 5865
(просп. Нахимова, 82 / Черноморский 1Б) from the addendum captured by
scripts/59_fetch_nakhimova82_testimony.py
(docs/exhibits/nakhimova82_testimony_addendum.md).

Leg 0 (27 Dec 2023, t.me/olegtsarov/9754): a resident's first-person
complaint naming "Нахимова, 82" directly -- demolished, rebuilt as a
mortgage development, no former owner retained a unit -- posted two days
before the replacement building's 29 Dec 2023 ЕИСЖС commissioning date.
Corroborates the demolish->mortgage-sale chain (legs 3-5 of
docs/case_studies/nakhimova_82_chernomorsky_1b.md) from the resident side.
verdict='confirms'.

Leg 6 (3 Oct 2025, t.me/mariupol24tv/104461): AGO Mariupol's own press names
the replacement building "Нахимова, 82" again and quotes Наталья Клочкова
(head of city-planning/architecture) on "transforming Mariupol into a modern
comfortable Russian city" -- a named official's own framing, directly usable
for the Rome Statute art. 8(2)(b)(viii) population-transfer argument.
verdict='confirms' (an official admission/identification, not a contested
claim).

New S5 (testimony_ref) entries per docs/tier3_corroboration_design.md,
following the dedup_key convention and ON CONFLICT pattern of scripts/61/63/65.

Idempotent via dedup_key.
"""
import json
import logging
import sys
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402
from mariupol_seizures.db.load import _upsert_source_doc_by_sha  # noqa: E402

log = logging.getLogger("load_nakhimova82_testimony")

BUILDING_ID = "AVENUE:нахимова|82"

UPSERT_CORRO_SQL = """
    INSERT INTO corroboration
        (property_id, kind, reference, detail, dedup_key, captured_at,
         source_doc_id, confidence, verdict, observed_start, observed_end)
    VALUES (%s, 'testimony_ref', %s, %s, %s, now(), %s, %s, 'confirms', %s, %s)
    ON CONFLICT (dedup_key) DO UPDATE
        SET reference      = EXCLUDED.reference,
            detail         = EXCLUDED.detail,
            captured_at    = now(),
            source_doc_id  = EXCLUDED.source_doc_id,
            confidence     = EXCLUDED.confidence,
            observed_start = EXCLUDED.observed_start,
            observed_end   = EXCLUDED.observed_end
    RETURNING id
"""


def main() -> None:
    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()

    cur.execute("SELECT id FROM property WHERE building_id = %s", (BUILDING_ID,))
    row = cur.fetchone()
    if row is None:
        raise SystemExit(f"property with building_id={BUILDING_ID!r} not found")
    property_id = row[0]
    log.info("property_id=%s (building_id=%s)", property_id, BUILDING_ID)

    # Leg 0: resident complaint, 27 Dec 2023
    sha_leg0 = "9a2264f73d632741ee7c39a844ff069304e2e317afa62f391994f8d651891691"
    source_doc_leg0 = _upsert_source_doc_by_sha(cur, sha_leg0)
    detail_leg0 = {
        "source": "telegram_post",
        "channel": "olegtsarov",
        "post_id": 9754,
        "post_url": "https://t.me/olegtsarov/9754",
        "post_date": "2023-12-27",
        "views": "180K",
        "quote": "...имел квартиру на Нахимова, 82. Дом был в ОСМД. Его "
                 "снесли, построили ипотечный и распродали. Ни одного "
                 "бывшего владельца там теперь нет. Так происходит со всеми "
                 "лакомыми кусочками в городе. Бывших владельцев тупо "
                 "выкидывают на улицу. Обращались и в СК и в прокуратуру и "
                 "в Администрацию Президента РФ и у депутата от Единой "
                 "России были с более сотней обращений. Бестолку. Всё "
                 "пересылают в ДНР для решения вопроса.",
        "summary": "First-person resident complaint naming Нахимова 82 "
                   "directly: building demolished, rebuilt as a mortgage "
                   "development, sold off with no former owners retained -- "
                   "posted two days before the 29 Dec 2023 ЕИСЖС "
                   "commissioning of the replacement building. Corroborates "
                   "the demolish->mortgage-sale chain (legs 3-5 of "
                   "nakhimova_82_chernomorsky_1b.md) from the resident side.",
        "post_sha256": sha_leg0,
    }
    reference_leg0 = (
        "Telegram, Олег Царёв channel, post t.me/olegtsarov/9754 "
        "(27 Dec 2023, 180K views): resident complaint naming Нахимова 82 -- "
        "demolished, rebuilt as mortgage housing, no former owner retained "
        "a unit -- corroborates the demolish->mortgage-sale chain (legs "
        "3-5 of nakhimova_82_chernomorsky_1b.md)"
    )
    dedup_key_leg0 = f"testimony_ref:{sha_leg0}:{property_id}:leg0"
    cur.execute(UPSERT_CORRO_SQL, (
        property_id, reference_leg0, json.dumps(detail_leg0, ensure_ascii=False),
        dedup_key_leg0, source_doc_leg0, 0.85, "2023-12-27", "2023-12-27",
    ))
    corro_id_leg0 = cur.fetchone()[0]
    log.info("upserted corroboration id=%s (leg 0, resident complaint)", corro_id_leg0)

    # Leg 6: AGO Mariupol press / Klochkova quote, 3 Oct 2025
    sha_leg6 = "8b8b6834467f11384dd733ece286e23da30bc9e3529b937771b67415b686fbb2"
    source_doc_leg6 = _upsert_source_doc_by_sha(cur, sha_leg6)
    detail_leg6 = {
        "source": "telegram_post",
        "channel": "mariupol24tv",
        "post_id": 104461,
        "post_url": "https://t.me/mariupol24tv/104461",
        "post_date": "2025-10-03",
        "views": "1.52K",
        "quote": "Две мариупольские постройки завоевали призовые места в "
                 "престижном смотре-конкурсе «АРХИТАВР»... По итогам "
                 "смотра-конкурса бронзовым дипломом в номинации "
                 "«Многоквартирные жилые здания» отмечен проект решения "
                 "многоквартирного жилого дома со встроенными помещениями "
                 "по проспекту Нахимова, 82... Как отметила начальник "
                 "управления градостроительства и архитектуры АГО "
                 "Мариуполь Наталья Клочкова, две высокие награды из более "
                 "160 представленных на конкурс проектов – достойное "
                 "признание заслуг архитекторов, которые работают над "
                 "преображением Мариуполя в современный комфортный "
                 "российский город.",
        "named_official": "Наталья Клочкова, начальник управления "
                           "градостроительства и архитектуры АГО Мариуполь",
        "summary": "AGO Mariupol's own press names the replacement building "
                   "'Нахимова, 82' (4th independent admission the address "
                   "refers to the same site as Черноморский 1Б, alongside "
                   "the DNR land order, federal RPD declaration, and "
                   "developer render filenames). A named official "
                   "(Klochkova) is quoted using explicit Russification "
                   "language -- 'transforming Mariupol into a modern "
                   "comfortable Russian city' -- about this building's "
                   "design award, 22 months after the leg-0 resident "
                   "complaint about the same address.",
        "rome_statute_relevance": "8(2)(b)(viii) -- named occupation "
                                   "official's own words framing "
                                   "redevelopment of a dispossessed "
                                   "residential site as part of making "
                                   "Mariupol a 'Russian city'",
        "post_sha256": sha_leg6,
    }
    reference_leg6 = (
        "Telegram, МАРИУПОЛЬ 24 channel, post t.me/mariupol24tv/104461 "
        "(3 Oct 2025): AGO Mariupol press naming the replacement building "
        "'Нахимова, 82' and quoting Наталья Клочкова (head of city-planning/"
        "architecture) on 'transforming Mariupol into a modern comfortable "
        "Russian city' -- 4th independent admission of address identity, "
        "official population-transfer framing"
    )
    dedup_key_leg6 = f"testimony_ref:{sha_leg6}:{property_id}:leg6"
    cur.execute(UPSERT_CORRO_SQL, (
        property_id, reference_leg6, json.dumps(detail_leg6, ensure_ascii=False),
        dedup_key_leg6, source_doc_leg6, 0.85, "2025-10-03", "2025-10-03",
    ))
    corro_id_leg6 = cur.fetchone()[0]
    log.info("upserted corroboration id=%s (leg 6, AGO press/Klochkova)", corro_id_leg6)

    con.commit()
    cur.close()
    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    main()
