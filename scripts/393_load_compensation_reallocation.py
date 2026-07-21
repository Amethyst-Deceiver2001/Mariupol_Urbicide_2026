#!/usr/bin/env python3
"""Load the crowd-sourced compensation-reallocation ledger (scripts/391 output)
into `corroboration` -- resident-testimony evidence that a SPECIFIC apartment
was handed out as "compensation housing," the reallocation endpoint of the
seizure pipeline. See memory/monitored_scan_findings_2026-07-21.md.

kind='compensation_reallocation', verdict='confirms'. These are TIER-3
testimony (a resident post, primary-source but unaudited -- docs/
tier3_corroboration_design.md), NOT an authoritative seizure_event: the
official record is the AGO distribution list captured by scripts/392, which
loads separately as seizure_event(stage='reallocation') once parsed. Keeping
the two apart preserves the evidentiary distinction (what residents report vs.
what the administration published).

Attaches to the building-level property, creating a minimal property row if
the building isn't yet on the spine (a reallocated flat IS a seized property,
so it belongs on the spine -- unlike a bare reclaim, cf. load_ownerless_
removals). Apartment-level granularity is carried in detail.apt_raw and, where
the building already has a `unit` row for that apartment, unit_id.

PRIVACY (CLAUDE.md): the parser already stripped names/phones; this loader
stores only building/apt/date/provenance. Confidence scales with the number
of independent posts naming the same unit (single post 0.6, 2+ posts 0.75).

Per project convention this writes to the canonical Postgres spine and is NOT
run by Claude -- run it yourself:

    PYTHONPATH=src .venv312/bin/python scripts/393_load_compensation_reallocation.py --dry-run
    PYTHONPATH=src .venv312/bin/python scripts/393_load_compensation_reallocation.py
"""
from __future__ import annotations

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
    _upsert_source_doc_by_sha,
)

log = logging.getLogger(__name__)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", default="data/parsed/compensation_reallocation.jsonl")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    path = Path(config.PROJECT_ROOT / args.jsonl)
    if not path.exists():
        raise SystemExit(f"{path} not found — run scripts/391 first.")

    import psycopg2
    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()

    loaded = new_props = 0
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            building_id = d["building_id"]
            apt = d.get("apt_raw")

            cur.execute("SELECT id FROM property WHERE building_id = %s", (building_id,))
            row = cur.fetchone()
            if row:
                property_id = row[0]
            else:
                new_props += 1
                if args.dry_run:
                    property_id = None
                else:
                    occ = f"{d.get('street_raw')}, {d.get('house_raw')}"
                    property_id = _find_or_create_property(cur, building_id, occupation_address=occ)

            unit_id = None
            if apt and not args.dry_run and property_id:
                # only attach to an EXISTING unit row; don't fabricate units on the
                # strength of a single resident post (registry units are decree-backed)
                cur.execute("SELECT id FROM unit WHERE property_id=%s AND apt_no=%s",
                            (property_id, apt))
                u = cur.fetchone()
                unit_id = u[0] if u else None

            confidence = 0.75 if d.get("n_posts", 1) >= 2 else 0.6
            source_doc_id = None if args.dry_run else _upsert_source_doc_by_sha(cur, d.get("source_sha256"))
            dedup_key = f"compensation_reallocation:{building_id}:{apt}"
            detail = {
                "source": "resident_report",
                "apt_raw": apt,
                "street_raw": d.get("street_raw"),
                "house_raw": d.get("house_raw"),
                "first_report_date": d.get("first_report_date"),
                "n_independent_posts": d.get("n_posts", 1),
                "source_channel": d.get("source_channel"),
                "source_url": d.get("source_url"),
                "note": "New occupant/agent publicly sought the dispossessed owner of "
                        "this flat after it was assigned as compensation housing. "
                        "Owner and occupant are living private individuals — minimized.",
            }

            if not args.dry_run:
                cur.execute(
                    """INSERT INTO corroboration
                           (property_id, kind, reference, detail, dedup_key, captured_at,
                            source_doc_id, confidence, verdict, observed_start)
                       VALUES (%s, 'compensation_reallocation', %s, %s, %s, now(),
                               %s, %s, 'confirms', %s)
                       ON CONFLICT (dedup_key) DO UPDATE
                           SET detail = EXCLUDED.detail,
                               confidence = EXCLUDED.confidence,
                               source_doc_id = EXCLUDED.source_doc_id""",
                    (property_id,
                     f"resident compensation-reallocation report ({d.get('source_channel')})",
                     json.dumps(detail, ensure_ascii=False), dedup_key,
                     source_doc_id, confidence, d.get("first_report_date") or None),
                )
            loaded += 1
            log.info("%s %s apt=%s (pid=%s, unit=%s, posts=%d)",
                     "[DRY]" if args.dry_run else "load", building_id, apt,
                     property_id, unit_id, d.get("n_posts", 1))

    if not args.dry_run:
        con.commit()
    con.close()
    log.info("%s: %d reallocation reports (%d on buildings new to the spine)",
             "[DRY RUN]" if args.dry_run else "done", loaded, new_props)
    print(f"{'[DRY RUN] would load' if args.dry_run else 'loaded'} {loaded} "
          f"compensation_reallocation corroboration rows ({new_props} new properties)")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
