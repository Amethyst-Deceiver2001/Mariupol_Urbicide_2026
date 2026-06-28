#!/usr/bin/env python3
"""Reconcile the first-instance district bezkhoz capture (`scripts/182`)
against the PostgreSQL spine BEFORE any load, and surface the hard
cadastral-number links it adds. Read-only against both stores — no network,
no writes.

WHY THIS GATES THE LOAD
-----------------------
The 4 Mariupol courts in the new district capture are the SAME four courts the
project already saturated via the original `court_crawler.py` pass (the ~2,666
cases CLAUDE.md calls saturated, already in `seizure_event`). Loading the new
8,271-case parse naively would double-count those Mariupol cases. This script
computes the exact overlap on the portal-internal `case_id` (a stable per-court
key present in both stores' source URLs), so the loader can take only the
net-new set.

WHAT IT ALSO FINDS
------------------
The cadastral numbers `scripts/182` recovered from the ~2% of ruling texts that
leak one past the `<адрес>` redaction are exact-matchable against
`property.cadastral_no`. Each match links a new court seizure case to an
existing spine property by a unique identifier — legal-grade linkage with no
fuzzy matching. (Most spine matches are cadastral-only entries that previously
had no address; the court case is their first human-readable identity.)

Run:
    .venv312/bin/python scripts/184_reconcile_district_to_spine.py
"""
from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import psycopg2  # noqa: E402

from mariupol_seizures import config  # noqa: E402

log = logging.getLogger(__name__)

SRC = ROOT / "data" / "parsed" / "dnr_district_bezkhoz.json"
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "parsed" / "district_spine_reconciliation.json"
MARIUPOL_COURTS = {"mar-zhovt--dnr", "mar-prim--dnr",
                   "mar-ordzh--dnr", "mar-ilich--dnr"}


def case_id(url: str) -> str | None:
    m = re.search(r"[?&]case_id=(\d+)", url)
    return m.group(1) if m else None


def court_sub(url: str) -> str | None:
    m = re.search(r"https?://([^/.]+)", url)
    return m.group(1) if m else None


def main() -> None:
    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()

    # --- spine court case_ids (from the original court_crawler harvest) ---
    cur.execute("SELECT url FROM source_document WHERE url LIKE '%name_op=case%'")
    spine_ids = {(court_sub(u), case_id(u)) for (u,) in cur.fetchall()
                 if case_id(u)}

    # --- new capture (court, case_id) from each card's raw meta sidecar ---
    recs = json.loads(SRC.read_text(encoding="utf-8"))
    new_ids = set()
    id_to_rec = {}
    for r in recs:
        mp = RAW / (r["raw_sha"] + ".html.meta.json")
        try:
            url = json.loads(mp.read_text()).get("url", "")
        except Exception:
            continue
        ci, cs = case_id(url), court_sub(url)
        if ci:
            new_ids.add((cs, ci))
            id_to_rec[(cs, ci)] = r

    overlap = spine_ids & new_ids
    new_only = new_ids - spine_ids
    new_mar = {x for x in new_ids if x[0] in MARIUPOL_COURTS}
    net_new = new_only
    net_new_mariupol = {x for x in new_only if x[0] in MARIUPOL_COURTS}

    # --- cadastral exact-match ---
    cur.execute("SELECT cadastral_no, id, occupation_address, prewar_address "
                "FROM property WHERE cadastral_no IS NOT NULL")
    spine_cad = {c.strip(): (pid, occ, pre)
                 for c, pid, occ, pre in cur.fetchall()}
    cad_recs = [r for r in recs if r.get("cadastral_number")]
    cad_matches = []
    for r in cad_recs:
        cad = r["cadastral_number"]
        if cad in spine_cad:
            pid, occ, pre = spine_cad[cad]
            cad_matches.append({
                "cadastral": cad, "case": r["case"],
                "court": r["court_code"], "spine_property_id": pid,
                "spine_address": occ or pre,
                "is_mariupol": r["is_mariupol"],
            })

    report = {
        "spine_court_case_ids": len(spine_ids),
        "new_capture_case_ids": len(new_ids),
        "overlap": len(overlap),
        "mariupol_new_total": len(new_mar),
        "net_new_total": len(net_new),
        "net_new_mariupol": len(net_new_mariupol),
        "net_new_rest_of_dnr": len(net_new) - len(net_new_mariupol),
        "cadastrals_recovered": len(cad_recs),
        "cadastral_spine_matches": len(cad_matches),
        "cadastral_match_detail": cad_matches,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1),
                   encoding="utf-8")

    print(f"\n{'='*66}\nDistrict capture ↔ spine reconciliation\n{'='*66}")
    print(f"spine court case_ids (original harvest): {len(spine_ids):,}")
    print(f"new capture case_ids:                    {len(new_ids):,}")
    print(f"overlap (already on spine):              {len(overlap):,}")
    print(f"\nNET-NEW to load (no double-count):       {len(net_new):,}")
    print(f"  · net-new Mariupol (filed since harvest): {len(net_new_mariupol)}")
    print(f"  · net-new rest-of-DNR (new coverage):     "
          f"{len(net_new) - len(net_new_mariupol):,}")
    print(f"\ncadastral numbers recovered:   {len(cad_recs)}")
    print(f"exact spine-property matches:  {len(cad_matches)}")
    for m in cad_matches:
        print(f"  {m['cadastral']}  case {m['case']}  -> spine pid "
              f"{m['spine_property_id']} ({m['spine_address'] or 'address-less entry'})")
    print(f"\n  -> {OUT}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
