#!/usr/bin/env python3
"""Load the 225 on-spine Telegram apartment-resale offers
(data/parsed/realestate_offers.jsonl, on_seizure_spine=true) as
corroboration(kind='market_listing') rows.

These offers matched their building_id (66 distinct buildings, 100% of
on-spine offers) but carry NO apartment number -- they are building-level
matches only. A building having some units in registry_inclusion does not
mean every unit offered for sale in that building was seized; many are
plausibly ordinary apartments sold by their lawful owners. So these are
loaded as a separate, low-confidence corroboration kind (NOT
seizure_event(stage='resale')), verdict='indeterminate', confidence ~0.45 --
flagging "this building has post-seizure-era resale activity" without
claiming the specific listed unit was a seized one.

PRIVACY: contact info (phones/usernames, marked "sensitive": true in the
source JSONL) is excluded entirely. text_excerpt is scrubbed of any
phone-like digit runs before storage.

New corroboration kind per docs/tier3_corroboration_design.md discussion;
follows the dedup_key + ON CONFLICT pattern of scripts/61/63/65/66.

Idempotent via dedup_key.
"""
from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402
from mariupol_seizures.db.load import _upsert_source_doc_by_sha  # noqa: E402

log = logging.getLogger("load_resale_offers")

OFFERS_PATH = config.DATA_DIR / "parsed" / "realestate_offers.jsonl"

PHONE_RE = re.compile(r"(?:\+?\d[\d\-\s()]{6,}\d)")

UPSERT_CORRO_SQL = """
    INSERT INTO corroboration
        (property_id, kind, reference, detail, dedup_key, captured_at,
         source_doc_id, confidence, verdict, observed_start, observed_end)
    VALUES (%s, 'market_listing', %s, %s, %s, now(), %s, %s, 'indeterminate', %s, %s)
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


def scrub_phones(text: str | None) -> str | None:
    if not text:
        return text
    return PHONE_RE.sub("[redacted]", text)


def main() -> None:
    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()

    loaded = skipped_no_property = 0

    with OFFERS_PATH.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            if not d.get("on_seizure_spine"):
                continue

            building_id = d["building_key"]
            cur.execute("SELECT id FROM property WHERE building_id = %s", (building_id,))
            row = cur.fetchone()
            if row is None:
                skipped_no_property += 1
                continue
            property_id = row[0]

            sha = d["source_sha256"]
            source_doc_id = _upsert_source_doc_by_sha(cur, sha)

            posted_date = (d.get("posted_date") or "")[:10] or None

            detail = {
                "source": d.get("source"),
                "venue": d.get("venue"),
                "source_url": d.get("source_url"),
                "posted_date": d.get("posted_date"),
                "offer_type": d.get("offer_type"),
                "property_class": d.get("property_class"),
                "address_raw": d.get("address_raw"),
                "rooms": d.get("rooms"),
                "is_studio": d.get("is_studio"),
                "area_total_m2": d.get("area_total_m2"),
                "floor": d.get("floor"),
                "floors": d.get("floors"),
                "new_build": d.get("new_build"),
                "price_rub": d.get("price_rub"),
                "price_raw": d.get("price_raw"),
                "is_agency": (d.get("contact") or {}).get("is_agency"),
                "text_excerpt": scrub_phones(d.get("text_excerpt")),
                "source_sha256": sha,
                "caveat": "building-level match only -- no apartment number "
                          "in the listing; this offer is NOT confirmed to be "
                          "one of the building's seized/ownerless units",
            }
            reference = (
                f"Telegram listing ({d.get('venue')}, {posted_date or 'undated'}): "
                f"{d.get('offer_type')} offer for {d.get('address_raw')} -- "
                f"building-level match to this property, apartment not "
                f"identified"
            )
            dedup_key = f"market_listing:{sha}:{property_id}"

            cur.execute(UPSERT_CORRO_SQL, (
                property_id, reference, json.dumps(detail, ensure_ascii=False),
                dedup_key, source_doc_id, 0.45, posted_date, posted_date,
            ))
            loaded += 1

    con.commit()
    cur.close()
    con.close()
    log.info("load_resale_offers: %d market_listing corroboration rows "
             "(skipped %d with no matching property)",
             loaded, skipped_no_property)
    print(f"load_resale_offers: {loaded} market_listing corroboration rows "
          f"(skipped: {skipped_no_property} no matching property)")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    main()
