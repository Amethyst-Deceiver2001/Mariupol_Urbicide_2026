#!/usr/bin/env python3
"""Load the AGO Mariupol compensation-programme LOST-DWELLING list (scripts/394
output) into `corroboration`, one row per building, and cross-reference the
673 officially-lost buildings against the seizure spine.

WHAT THIS IS. scripts/394 parsed the administration's own apartment-level list
of dwellings recorded as "утраченное" (lost) whose owners are being rehoused
under Пост. ГКО №175 / Решение №61-1 / Закон №141-РЗ. Each such building is the
occupation's self-authored admission that the dwelling was lost -- RD4U A3.1
(damage/loss) evidence, dated and address-specific. We load it building-level
(kind='compensation_program_lost_dwelling', verdict='confirms'), attaching to
the spine property and creating a minimal property if the building isn't yet on
the spine (a destroyed dwelling IS a property in scope for A3.1, same logic as
scripts/393's reallocated flats).

THE CROSS-REFERENCE. The interesting question is overlap: a building that is
BOTH on this lost-dwelling list AND carries an ownerless-seizure event on the
spine (registry_inclusion / court_petition / ownerless_designation / reclaim)
is a double-dispossession signal -- the same address whose residents were
displaced/compensated is also having its stock taken as "ownerless." The
--dry-run (default) prints that overlap and the on/off-spine split without
writing anything.

PRIVACY (CLAUDE.md): the recipient is a living private individual, pseudonymised
to a hex ID at source; we store building/apt/district/date only, never a name.

    PYTHONPATH=src .venv312/bin/python scripts/395_load_ago_lost_dwellings.py --dry-run
    PYTHONPATH=src .venv312/bin/python scripts/395_load_ago_lost_dwellings.py --apply
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402
from mariupol_seizures.db.load import (  # noqa: E402
    _find_or_create_property,
    _upsert_source_doc_by_sha,
)

log = logging.getLogger(__name__)

# spine stages that mean "this building's stock was taken/contested as ownerless"
OWNERLESS_STAGES = (
    "ownerless_designation", "ownerless_registration", "court_petition",
    "court_transfer", "entered_force", "registry_inclusion", "reclaim",
    "expropriation", "temporary_use",
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", default="data/parsed/ago_lost_dwellings.jsonl")
    ap.add_argument("--apply", action="store_true",
                    help="write to the DB (default is a read-only dry-run/cross-reference)")
    ap.add_argument("--dry-run", action="store_true",
                    help="explicit no-op: dry-run is already the default without --apply")
    args = ap.parse_args()
    dry = not args.apply

    path = Path(config.PROJECT_ROOT / args.jsonl)
    if not path.exists():
        raise SystemExit(f"{path} not found — run scripts/394 first.")

    # group rows by building
    buildings: dict[str, dict] = defaultdict(
        lambda: {"apts": set(), "districts": set(), "dates": set(),
                 "street_raw": None, "house_raw": None, "sha": None})
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            b = buildings[d["building_id"]]
            if d.get("apt_raw"):
                b["apts"].add(d["apt_raw"])
            if d.get("district"):
                b["districts"].add(d["district"])
            if d.get("list_date"):
                b["dates"].add(d["list_date"])
            b["street_raw"] = b["street_raw"] or d.get("street_raw")
            b["house_raw"] = b["house_raw"] or d.get("house_raw")
            b["sha"] = b["sha"] or d.get("source_sha256")

    log.info("%d distinct lost-dwelling buildings to reconcile", len(buildings))

    import psycopg2
    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()

    on_spine = off_spine = overlap = 0
    overlap_rows: list[tuple] = []
    loaded = new_props = 0

    for building_id, b in sorted(buildings.items()):
        cur.execute("SELECT id FROM property WHERE building_id = %s", (building_id,))
        row = cur.fetchone()
        property_id = row[0] if row else None

        if property_id:
            on_spine += 1
            cur.execute(
                "SELECT array_agg(DISTINCT stage::text) FROM seizure_event "
                "WHERE property_id = %s", (property_id,))
            stages = (cur.fetchone()[0] or [])
            hit = sorted(s for s in stages if s in OWNERLESS_STAGES)
            if hit:
                overlap += 1
                overlap_rows.append((building_id, len(b["apts"]), ",".join(hit)))
        else:
            off_spine += 1

        if not dry:
            if property_id is None:
                new_props += 1
                occ = f"{b['street_raw']}, {b['house_raw']}"
                property_id = _find_or_create_property(cur, building_id, occupation_address=occ)
            source_doc_id = _upsert_source_doc_by_sha(cur, b["sha"])
            detail = {
                "source": "ago_compensation_distribution_list",
                "n_lost_apartments": len(b["apts"]),
                "apartments": sorted(b["apts"], key=lambda x: (len(x), x))[:200],
                "districts": sorted(b["districts"]),
                "list_dates": sorted(b["dates"]),
                "note": "Building recorded by the occupation administration on its own "
                        "compensation-housing distribution list as the LOST ('утраченное') "
                        "dwelling of one or more rehoused recipients (Пост. №175 / Решение "
                        "№61-1 / Закон №141-РЗ). Recipients are living private individuals — "
                        "pseudonymised at source; no names stored.",
            }
            dedup_key = f"compensation_program_lost_dwelling:{building_id}"
            cur.execute(
                """INSERT INTO corroboration
                       (property_id, kind, reference, detail, dedup_key, captured_at,
                        source_doc_id, confidence, verdict, observed_start)
                   VALUES (%s, 'compensation_program_lost_dwelling', %s, %s, %s, now(),
                           %s, %s, 'confirms', %s)
                   ON CONFLICT (dedup_key) DO UPDATE
                       SET detail = EXCLUDED.detail,
                           confidence = EXCLUDED.confidence,
                           source_doc_id = EXCLUDED.source_doc_id""",
                (property_id, "AGO compensation-distribution lost-dwelling list",
                 json.dumps(detail, ensure_ascii=False), dedup_key,
                 source_doc_id, 0.9, min(b["dates"]) if b["dates"] else None),
            )
            loaded += 1

    if not dry:
        con.commit()

    print(f"\n{'[DRY RUN] ' if dry else ''}lost-dwelling buildings: {len(buildings)} total, "
          f"{on_spine} already on spine, {off_spine} off-spine")
    print(f"OVERLAP with an ownerless-seizure event on the spine: {overlap} buildings "
          f"(double-dispossession signal)")
    for bid, n_apts, stages in sorted(overlap_rows, key=lambda r: -r[1])[:40]:
        print(f"  {n_apts:3} lost-apts  {bid:34}  ownerless-stage: {stages}")
    if not dry:
        print(f"\nloaded {loaded} corroboration rows ({new_props} new minimal properties)")
    else:
        print("\n(dry run — nothing written; re-run with --apply to load)")
    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
