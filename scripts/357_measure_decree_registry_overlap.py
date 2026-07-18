#!/usr/bin/env python3
"""Measure how much the municipal-decree track (stage in
'ownerless_designation'/'ownerless_registration', sourced from individual
Постановления PDFs) actually overlaps with the live ownerless REGISTRY
(stage='registry_inclusion', 12,948 rows from the gosuslugi.ru registry
listing) -- i.e. whether every unit on the current bezkhoz registry has a
citable (quasi)legal decree basis, or whether the two tracks are largely
disjoint.

Two levels of granularity:
  1. BUILDING-level (property_id): straightforward, since decree-track
     events resolve to property_id but NOT unit_id (no apartment-level
     linkage was built for that loader -- see db/load.py's
     load_ownerless_decrees).
  2. APARTMENT-level (property_id, apt_no): decree rows carry the apartment
     number only as free text inside detail->>'address_raw' ("...кв.5"),
     never as a structured field -- extracted here via regex and matched
     against the `unit` table's apt_no for registry_inclusion events on the
     same building. Nonresidential decree rows (no "кв." at all) are
     correctly excluded from this level -- they have no apartment to match.

Read-only analytics against the already-loaded DB; run directly.

Run:
    set -a && source .env && set +a
    PYTHONPATH=src python scripts/357_measure_decree_registry_overlap.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import psycopg2  # noqa: E402

from mariupol_seizures import config  # noqa: E402

_APT_RE = re.compile(r"кв\.?\s*(\S+)", re.I)


def _norm_apt(raw: str) -> str:
    return raw.strip().rstrip(",.").lstrip("0") or "0"


def main() -> None:
    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()

    # ── Building-level overlap ──────────────────────────────────────────
    cur.execute("""
        SELECT
            (SELECT count(DISTINCT property_id) FROM seizure_event
             WHERE stage = 'registry_inclusion') AS registry_buildings,
            (SELECT count(DISTINCT property_id) FROM seizure_event
             WHERE stage IN ('ownerless_designation', 'ownerless_registration')) AS decree_buildings,
            (SELECT count(DISTINCT r.property_id) FROM seizure_event r
             WHERE r.stage = 'registry_inclusion'
               AND EXISTS (SELECT 1 FROM seizure_event d
                           WHERE d.property_id = r.property_id
                             AND d.stage IN ('ownerless_designation', 'ownerless_registration'))
            ) AS overlap_buildings
    """)
    reg_b, dec_b, overlap_b = cur.fetchone()
    print("=== Building-level overlap ===")
    print(f"Registry buildings (registry_inclusion):        {reg_b}")
    print(f"Decree-track buildings (designation+reg):        {dec_b}")
    print(f"Overlap (registry buildings WITH a decree hit):  {overlap_b}  "
          f"({overlap_b / reg_b * 100:.1f}% of registry buildings)")
    print(f"Registry buildings with NO decree basis found:   {reg_b - overlap_b}")
    print(f"Decree buildings NOT in current registry snapshot: "
          f"{dec_b - overlap_b}")
    print()

    # ── Apartment-level overlap ─────────────────────────────────────────
    cur.execute("""
        SELECT property_id, detail->>'address_raw'
        FROM seizure_event
        WHERE stage IN ('ownerless_designation', 'ownerless_registration')
          AND detail->>'address_raw' IS NOT NULL
    """)
    decree_units: set[tuple[int, str]] = set()
    decree_rows_total = 0
    decree_rows_with_apt = 0
    for property_id, address_raw in cur.fetchall():
        decree_rows_total += 1
        m = _APT_RE.search(address_raw or "")
        if not m:
            continue  # nonresidential row, or apt not captured -- correctly excluded
        decree_rows_with_apt += 1
        decree_units.add((property_id, _norm_apt(m.group(1))))

    cur.execute("""
        SELECT se.property_id, u.apt_no
        FROM seizure_event se
        JOIN unit u ON u.id = se.unit_id
        WHERE se.stage = 'registry_inclusion'
    """)
    registry_units: set[tuple[int, str]] = set()
    for property_id, apt_no in cur.fetchall():
        registry_units.add((property_id, _norm_apt(apt_no)))

    matched = decree_units & registry_units
    print("=== Apartment-level overlap ===")
    print(f"Decree-track rows total:                          {decree_rows_total}")
    print(f"  ...with a parseable apartment number:            {decree_rows_with_apt}")
    print(f"  ...distinct (building, apt) pairs:               {len(decree_units)}")
    print(f"Registry (building, apt) pairs:                    {len(registry_units)}")
    print(f"Matched (decree apt found in registry):            {len(matched)}  "
          f"({len(matched) / len(decree_units) * 100:.1f}% of decree apts)")
    print(f"Decree apartments with NO matching registry entry: {len(decree_units) - len(matched)}")
    print(f"Registry apartments with NO matching decree found: "
          f"{len(registry_units) - len(matched)}  "
          f"({(len(registry_units) - len(matched)) / len(registry_units) * 100:.1f}% of registry)")

    cur.close()
    con.close()


if __name__ == "__main__":
    main()
