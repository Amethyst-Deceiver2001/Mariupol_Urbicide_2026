#!/usr/bin/env python3
"""Load a corroboration(kind='testimony_ref') row for property 4442
(просп. Ленина (Мира), 133), apt 19, from the Telegram post + photo
captured by scripts/60_fetch_lenina133_sealing_notice.py.

Apt 19 is already a registry_inclusion seizure_event for property 4442
(id 37362, address_raw "...Ленина (Мира), 133, 19"). The captured post
(t.me/ssaniaworld/3348, 23 Oct 2025) and its attached photo show that
apartment's door physically sealed ("ОПЕЧАТАНО") by Управление имущественных
и земельных отношений, with handwritten vacate deadlines 22.10.2025 and
25.10.2025 and citations to RF Criminal Code arts. 139/168.

This is the project's first concrete S5 (testimony_ref) row -- a Tier-3
sub-layer that was pure design in docs/tier3_corroboration_design.md.
Unlike the (still-unloaded) Нахимова 82 testimony candidates, this artifact
names the exact apartment of an EXISTING registry_inclusion record and
includes a dated primary-source photo of the physical document, so it is
loaded here rather than left pending.

No schema change: corroboration.kind and .detail are free-form (kind is
TEXT, not an enum); source_doc_id/confidence/verdict/observed_* columns
already exist from scripts/53_load_unosat_damage.py's migration.

Idempotent: dedup_key = 'testimony_ref:<post_sha256>:4442:apt19'.
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

log = logging.getLogger("load_lenina133_apt19_corroboration")

MANIFEST_PATH = config.DATA_DIR / "parsed" / "lenina133_apt19_sealing_manifest.json"
BUILDING_ID = "AVENUE:ленина|133"

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
            verdict        = EXCLUDED.verdict,
            observed_start = EXCLUDED.observed_start,
            observed_end   = EXCLUDED.observed_end
    RETURNING id
"""


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    post, photo = manifest["artifacts"]
    post_sha = post["sha256"]
    photo_sha = photo["sha256"]

    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()

    cur.execute("SELECT id FROM property WHERE building_id = %s", (BUILDING_ID,))
    row = cur.fetchone()
    if row is None:
        raise SystemExit(f"property with building_id={BUILDING_ID!r} not found")
    property_id = row[0]
    log.info("property_id=%s (building_id=%s)", property_id, BUILDING_ID)

    source_doc_id = _upsert_source_doc_by_sha(cur, post_sha)
    log.info("source_document id for post (%s) -> %s", post_sha, source_doc_id)

    detail = {
        "source": "telegram_post",
        "channel": "ssaniaworld",
        "post_id": 3348,
        "post_url": post["url"],
        "post_date": "2025-10-23",
        "apt": "19",
        "issuing_authority": "Управление имущественных и земельных отношений "
                              "(АГО Мариуполь)",
        "notice_text": "ОПЕЧАТАНО. Объект является муниципальной "
                       "собственностью городского округа Мариуполь. "
                       "пр. Ленина д. 133 кв. 19. Без представителя "
                       "собственника не вскрывать.",
        "criminal_code_articles_cited": ["139", "168"],
        "contact_phone": "+7 (949) 814-63-64",
        "vacate_deadlines": ["2025-10-22", "2025-10-25"],
        "resident_described": "73-year-old registered (прописана) occupant, "
                               "power of attorney from owner (resident in "
                               "Belarus), utilities current; told to vacate "
                               "per 2024 court ruling on бесхозяйность",
        "related_apartments_named_in_post": ["2", "19", "20", "33"],
        "related_seizure_event_id": 37362,
        "photo_sha256": photo_sha,
        "photo_raw_path": photo["raw_path"],
        "post_sha256": post_sha,
        "post_raw_path": post["raw_path"],
    }
    reference = (
        "Telegram post + photo (t.me/ssaniaworld/3348, 23 Oct 2025): "
        "apt 19 physically sealed («ОПЕЧАТАНО») by Управление "
        "имущественных и земельных отношений, vacate deadline 22-25 Oct "
        "2025, citing RF Criminal Code arts. 139/168 -- corroborates "
        "seizure_event id 37362 (registry_inclusion, apt 19)"
    )
    dedup_key = f"testimony_ref:{post_sha}:{property_id}:apt19"

    cur.execute(UPSERT_CORRO_SQL, (
        property_id, reference, json.dumps(detail, ensure_ascii=False), dedup_key,
        source_doc_id, 0.90, "2025-10-23", "2025-10-23",
    ))
    corro_id = cur.fetchone()[0]
    con.commit()
    cur.close()
    con.close()
    log.info("upserted corroboration id=%s for property_id=%s (dedup_key=%s)",
             corro_id, property_id, dedup_key)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    main()
