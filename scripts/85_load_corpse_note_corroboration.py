#!/usr/bin/env python3
"""Load corpse-note corroboration rows from the Russian federal damage assessment.

Three buildings in data/parsed/damage_assessment.jsonl have free-text notes in
col 49 (C_NOTES) that document unburied human bodies found during the occupation's
own contractor survey (ГК Трансстройинвест). Two are Group 4 (designated for
demolition at time of survey).

These records are admitted evidence of:
  1. Buildings occupied/not abandoned at time of siege (bodies = residents who died)
  2. Bodies present when the same buildings were being processed for «бесхозяйность»
  3. The occupation's own contractor acknowledging the need for burial — probative
     against any "orderly vacated" framing.

Source SHA-256: 0bd1edf794b562f65f7e0a57a8b9e5e88bd20aed1e01cfe3c00286d3e64e0bf9
  (Russian_damage_assessment.xlsx, captured from occupation GIS portal)

Hardcoded because there are exactly 3 records and they never change.

Run:
    python scripts/85_load_corpse_note_corroboration.py [--dry-run]
"""
import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402
from mariupol_seizures.db.load import _upsert_source_doc_by_sha  # noqa: E402

log = logging.getLogger(__name__)

SOURCE_SHA = "0bd1edf794b562f6fa419cf564c0b424b411b6161723f8491c66c5e444d9d7c7"
KIND       = "damage_assessment_corpse_note"

# Hardcoded from data/parsed/damage_assessment.jsonl — stable, 3 records.
RECORDS = [
    {
        "property_id":    4326,
        "address_raw":    "бульвар Богдана Хмельницкого, 20",
        "seq_no":         6,
        "district":       "Октябрьский",
        "group":          4,
        "destruction_pct": 100.0,
        "contractor":     "ГК Трансстройинвест",
        "notes":          (
            "70% дома сгорело.\n"
            "На въезде во двор лежит труп.\n"
            "Требуется уборка территории."
        ),
        "match_score":    0.95,
    },
    {
        "property_id":    4570,
        "address_raw":    "проспект Нахимова, 190",
        "seq_no":         250,
        "district":       "Октябрьский",
        "group":          2,
        "destruction_pct": 30.0,
        "contractor":     "ГК Трансстройинвест",
        "notes":          (
            "Сгорел 1 подъезд и частично 2.\n"
            "Множественные повреждения стен и кровли.\n"
            "Требуется обследование территорий. (трупы)"
        ),
        "match_score":    0.93,
    },
    {
        "property_id":    4884,
        "address_raw":    "улица Итальянская, 143",
        "seq_no":         565,
        "district":       "Октябрьский",
        "group":          4,
        "destruction_pct": 100.0,
        "contractor":     "ГК Трансстройинвест",
        "notes":          (
            "Дом сгорел полностью.\n"
            "Множественные повреждения стен.\n"
            "В доме есть трупы, которые необходимо захоронить."
        ),
        "match_score":    0.93,
    },
]


def main(dry_run: bool = False) -> None:
    print(f"\n{'='*65}")
    print("Corpse-note corroboration loader")
    print(f"{'='*65}")
    print(f"  Source : Russian federal damage assessment (ГК Трансстройинвест)")
    print(f"  SHA    : {SOURCE_SHA[:16]}…")
    print(f"  Records: {len(RECORDS)}")
    print()

    for r in RECORDS:
        print(f"  pid={r['property_id']}  {r['address_raw']}")
        print(f"    group={r['group']}  destruction={r['destruction_pct']}%  "
              f"match_score={r['match_score']:.2f}")
        print(f"    notes: {r['notes'][:120].replace(chr(10), ' / ')}")
        print()

    if dry_run:
        log.info("dry-run — skipping DB load")
        return

    import psycopg2
    conn = psycopg2.connect(config.DATABASE_URL)
    cur  = conn.cursor()

    source_doc_id = _upsert_source_doc_by_sha(cur, SOURCE_SHA)
    log.info("source_doc_id for damage assessment: %s", source_doc_id)

    loaded = skipped = 0
    for r in RECORDS:
        dedup_key = f"{KIND}_{r['seq_no']}"
        detail = json.dumps({
            "seq_no":          r["seq_no"],
            "address_raw":     r["address_raw"],
            "district":        r["district"],
            "group":           r["group"],
            "destruction_pct": r["destruction_pct"],
            "contractor":      r["contractor"],
            "notes_verbatim":  r["notes"],
            "source_sha256":   SOURCE_SHA,
            "evidentiary_note": (
                "Occupation contractor survey (ГК Трансстройинвест) documented "
                "unburied human remains at this address during the federal "
                "reconstruction damage-assessment process. Probative against "
                "abandonment framing; documents continued presence of residents "
                "through the siege period. Source: Russian federal reconstruction "
                "tracker (Russian_damage_assessment.xlsx)."
            ),
        }, ensure_ascii=False)

        cur.execute("""
            INSERT INTO corroboration
              (property_id, kind, reference, source_doc_id, confidence,
               detail, dedup_key, captured_at, verdict)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), 'confirms')
            ON CONFLICT (dedup_key) DO UPDATE
                SET detail      = EXCLUDED.detail,
                    captured_at = NOW()
            RETURNING id, (xmax = 0) AS inserted
        """, (
            r["property_id"], KIND,
            "Russian_damage_assessment.xlsx",
            source_doc_id, r["match_score"],
            detail, dedup_key,
        ))
        row = cur.fetchone()
        if row and row[1]:
            loaded += 1
            log.info("inserted  pid=%d  %s  corroboration.id=%d",
                     r["property_id"], r["address_raw"], row[0])
        else:
            skipped += 1
            log.info("updated   pid=%d  %s  corroboration.id=%d",
                     r["property_id"], r["address_raw"], row[0])

    conn.commit()
    conn.close()

    print(f"{'='*65}")
    print(f"  Inserted : {loaded}")
    print(f"  Updated  : {skipped}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
