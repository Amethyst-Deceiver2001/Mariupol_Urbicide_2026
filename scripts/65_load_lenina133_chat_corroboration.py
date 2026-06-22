#!/usr/bin/env python3
"""Load two corroboration(kind='testimony_ref') rows for property 4442
(просп. Ленина (Мира), 133) from the @Lenina133 resident-chat scrape
(scripts/62_crawl_lenina133_chat.py, 1311 msgs / 487 media, captured
2026-06-13/14).

1. Apt 2/33 sealing (msg 1145, 23 Oct 2025): residents report "ОПЕЧАТАНО"
   notices on apartments 2 AND 33 (alongside 19, already loaded as
   corroboration id 5417), corroborating the existing registry_inclusion
   seizure_event for apt 2 (id 37358). verdict='confirms'.

2. Systemic fake-meetings fraud + funds-diversion allegation (msgs 1024,
   1025, 1026, 1142, 1363; topic "Документация по дому", 21 Jun 2025 -
   25 Mar 2026): residents allege the building's official "паспорт объекта"
   (СТРОИТЕЛЬСТВО / full rebuild -- the same passport behind corroboration
   id 1412/5418) was used to draw federal reconstruction funds while only a
   minimal "тепловой контур" repair was delivered, then the building was
   "сдан на баланс администрации Моргуна и УКС" in 2023 via fraudulent
   resident-meeting certifications -- a pattern residents say was repeated
   "city-wide" (cf. Строителей 101). This is an unverified allegation, not an
   independently confirmed fact, so verdict='indeterminate' and a lower
   confidence (0.5).

Both rows are new S5 (testimony_ref) entries per
docs/tier3_corroboration_design.md, following the dedup_key convention and
ON CONFLICT pattern of scripts/61 and 63.

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

log = logging.getLogger("load_lenina133_chat_corroboration")

BUILDING_ID = "AVENUE:ленина|133"

UPSERT_CORRO_SQL = """
    INSERT INTO corroboration
        (property_id, kind, reference, detail, dedup_key, captured_at,
         source_doc_id, confidence, verdict, observed_start, observed_end)
    VALUES (%s, 'testimony_ref', %s, %s, %s, now(), %s, %s, %s, %s, %s)
    ON CONFLICT (dedup_key) DO UPDATE
        SET reference      = EXCLUDED.reference,
            detail         = EXCLUDED.detail,
            captured_at    = now(),
            source_doc_id  = EXCLUDED.source_doc_id,
            confidence     = EXCLUDED.confidence,
            verdict        = EXCLUDED.verdict,
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

    # 1. Apt 2/33 sealing, msg 1145 (23 Oct 2025)
    sha_1145 = "6a1052edab64a54948efcf86807de463826ed15fcc08d437c5f936a964ee6fee"
    source_doc_1145 = _upsert_source_doc_by_sha(cur, sha_1145)
    detail_1145 = {
        "source": "telegram_building_chat_msg",
        "channel": "Lenina133",
        "topic": "🚨О жизни дома🏠",
        "msg_id": 1145,
        "msg_url": "https://t.me/Lenina133/1145",
        "msg_date": "2025-10-23",
        "summary": "Residents report 'ОПЕЧАТАНО' (sealed) notices appeared "
                   "on apartments 2 AND 33 (alongside apt 19, corroboration "
                   "id 5417), citing the same 2024 court rulings on "
                   "бесхозяйность named in t.me/ssaniaworld/3348. Both flats "
                   "reportedly vacant; notices removed after one day. "
                   "Contact phone matched the отдел земельных отношений "
                   "number posted at the city admin board (Громовая 63), "
                   "since disconnected.",
        "related_apartments": ["2", "33"],
        "related_seizure_event_id": 37358,
        "note": "Apt 33 is not (yet) a registry_inclusion row for this "
                "property; apt 2 is (id 37358).",
        "msg_sha256": sha_1145,
    }
    reference_1145 = (
        "Telegram, @Lenina133 resident chat, msg 1145 (23 Oct 2025): "
        "apartments 2 and 33 also sealed («ОПЕЧАТАНО») same week as apt 19 "
        "(corroboration id 5417), citing the same 2024 бесхозяйность court "
        "rulings -- corroborates seizure_event id 37358 (registry_inclusion, "
        "apt 2)"
    )
    dedup_key_1145 = f"testimony_ref:{sha_1145}:{property_id}:apt2_33_sealing"
    cur.execute(UPSERT_CORRO_SQL, (
        property_id, reference_1145, json.dumps(detail_1145, ensure_ascii=False),
        dedup_key_1145, source_doc_1145, 0.85, "confirms", "2025-10-23", "2025-10-23",
    ))
    corro_id_1145 = cur.fetchone()[0]
    log.info("upserted corroboration id=%s (apt2/33 sealing)", corro_id_1145)

    # 2. Systemic fake-meetings fraud / funds-diversion allegation
    sha_1024 = "7d653c4570cc9099361290c23194b080717e4932da9dc174431ec60b9c676d34"
    source_doc_1024 = _upsert_source_doc_by_sha(cur, sha_1024)
    detail_fraud = {
        "source": "telegram_building_chat_msg",
        "channel": "Lenina133",
        "topic": "Документация по дому",
        "msg_ids": [1024, 1025, 1026, 1142, 1363],
        "msg_urls": [f"https://t.me/Lenina133/{i}" for i in (1024, 1025, 1026, 1142, 1363)],
        "msg_date_range": ["2025-06-21", "2026-03-25"],
        "primary_msg_sha256": sha_1024,
        "summary": "Residents allege the building's official "
                   "'паспорт объекта' (СТРОИТЕЛЬСТВО / full rebuild -- the "
                   "same passport behind corroboration id 1412/5418, ФКРМО "
                   "project lead Татаренко Владислав Вячеславович) was used "
                   "to draw federal reconstruction funds while project work "
                   "delivered only a minimal 'тепловой контур' repair "
                   "(msg 1024, named: Бакушин, Полозенко, Татаренко, "
                   "Моргун). The 2022 demolition-list аварийность was left "
                   "unaddressed, then the building was 'сдан на баланс "
                   "администрации Моргуна и УКС' in 2023, shortly before "
                   "Моргун was replaced. Msg 1026 generalizes the scheme "
                   "city-wide: fraudulent 'якобы всех жильцов' general "
                   "meetings used to certify acceptance of substandard "
                   "repairs and to install illegitimate 'старшие по дому' "
                   "(cf. Строителей 101 cross-building pattern). Msg 1142 "
                   "(23 Oct 2025): Полозенко -- without standing as старшая "
                   "по дому -- signed a waiver against contractor claims "
                   "despite the prosecutor's office reportedly holding "
                   "documentation of unsound floor slabs. Msg 1363 "
                   "(25 Mar 2026) independently confirms Татаренко's first "
                   "name as Владислав, corroborating the npa.dnronline.su "
                   "decree identification (ФКРМО ЦУП project lead).",
        "named_individuals": ["Татаренко Владислав Вячеславович", "Бакушин",
                               "Полозенко", "Моргун О.В."],
        "status": "unverified resident allegation, not independently "
                  "confirmed by an official document in this project's "
                  "holdings",
    }
    reference_fraud = (
        "Telegram, @Lenina133 resident chat, msgs 1024/1025/1026/1142/1363 "
        "(21 Jun 2025 - 25 Mar 2026): resident allegations of fraudulent "
        "fake-meeting certifications, minimal repair vs. full-rebuild "
        "funding, and a 2023 municipal-balance transfer for property 4442 "
        "-- an unverified allegation of funds diversion / fraudulent "
        "acceptance, generalized city-wide by residents"
    )
    dedup_key_fraud = f"testimony_ref:{sha_1024}:{property_id}:funds_diversion_allegation"
    cur.execute(UPSERT_CORRO_SQL, (
        property_id, reference_fraud, json.dumps(detail_fraud, ensure_ascii=False),
        dedup_key_fraud, source_doc_1024, 0.50, "indeterminate", "2025-06-21", "2026-03-25",
    ))
    corro_id_fraud = cur.fetchone()[0]
    log.info("upserted corroboration id=%s (funds-diversion allegation)", corro_id_fraud)

    con.commit()
    cur.close()
    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    main()
