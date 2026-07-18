#!/usr/bin/env python3
"""Diagnose WHY the ownerless REGISTRY (12,948 apt-rows / 1,636 buildings,
recognition_marker='признаки бесхозяйности') and the municipal-DECREE track
(признание→постановка на учёт, 5,395 rows / 1,243 buildings) barely overlap
(only 287 buildings in common). scripts/357 measured the gap; this decides
its CAUSE, read-only, no crawl.

Three candidate causes, three targeted tests:

  (C) OUR MATCHING FAILURE — the decree for a "gap" registry building DOES
      exist in our data but under a slightly different normalized building_id
      (OCR noise, street-type disagreement AVENUE/STREET, house-suffix), so
      the exact building_id join in scripts/357 misses it.
      TEST 1: fuzzy-match each of the 1,349 no-decree registry buildings
      against ALL decree building_ids on the street|house key. High-scoring
      near-misses = recoverable matches we're currently losing.

  (A/B) THE GAP IS REAL — most registry buildings genuinely have no decree,
      because the registry ("signs of ownerlessness") is the WIDE upstream
      administrative funnel and the decree is a later, rarer formal act (and
      post-ФКЗ-4 registry inclusion is itself the operative title, so no
      individual decree is even required).
      TEST 2 (confound-free): restrict to the 287 buildings we have BOTH
      sources for — matching failure is impossible here, we found the decree.
      Compare, per building, how many apartments the registry lists vs how
      many the decrees name. If decrees systematically under-cover even here,
      the gap is real, not a lookup artifact.
      TEST 3: structural corroboration — cadastral/ЕГРН-registration rate on
      the decree track vs the registry (the registry is pre-cadastral by
      construction), and decree-track date span vs the (undated) registry.

Read-only analytics against the loaded DB; safe to run directly.

Run:
    set -a && source .env && set +a
    PYTHONPATH=src python scripts/360_diagnose_registry_decree_gap.py
"""
from __future__ import annotations

import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import psycopg2  # noqa: E402
from rapidfuzz import fuzz, process  # noqa: E402

from mariupol_seizures import config  # noqa: E402

_APT_RE = re.compile(r"кв\.?\s*(\S+)", re.I)


def _norm_apt(raw: str) -> str:
    return raw.strip().rstrip(",.").lstrip("0") or "0"


def _street_house(building_id: str) -> str:
    """Drop the TYPE: prefix so AVENUE:/STREET:/LANE: disagreements between
    the two sources don't hide a real street|house match."""
    return building_id.split(":", 1)[1] if ":" in building_id else building_id


def main() -> None:
    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()

    # building_id sets for each track ------------------------------------
    cur.execute("""
        SELECT DISTINCT p.id, p.building_id
        FROM property p JOIN seizure_event se ON se.property_id = p.id
        WHERE se.stage = 'registry_inclusion'
    """)
    reg = {pid: bid for pid, bid in cur.fetchall()}

    cur.execute("""
        SELECT DISTINCT p.id, p.building_id
        FROM property p JOIN seizure_event se ON se.property_id = p.id
        WHERE se.stage IN ('ownerless_designation', 'ownerless_registration')
    """)
    dec = {pid: bid for pid, bid in cur.fetchall()}

    dec_bids = set(dec.values())
    reg_gap = {pid: bid for pid, bid in reg.items() if bid not in dec_bids}
    overlap_pids = {pid for pid, bid in reg.items() if bid in dec_bids}

    print(f"Registry buildings:            {len(set(reg.values()))}")
    print(f"Decree buildings:              {len(dec_bids)}")
    print(f"Registry buildings w/o decree: {len(set(reg_gap.values()))}")
    print(f"Overlap buildings:             {len(overlap_pids)}\n")

    # ── TEST 1: fuzzy recovery of the "gap" via near-miss building_ids ───
    print("=== TEST 1: is the gap our matching failure? "
          "(fuzzy street|house match, gap-registry vs all-decree) ===")
    dec_keys = sorted({_street_house(b) for b in dec_bids})
    buckets = {"exact_streethouse": 0, ">=95": 0, "90-95": 0, "80-90": 0, "<80": 0}
    near_miss_examples = []
    dec_sh_set = set(dec_keys)
    for pid, bid in reg_gap.items():
        sh = _street_house(bid)
        if sh in dec_sh_set:
            # street|house identical but TYPE prefix differed -> real miss
            buckets["exact_streethouse"] += 1
            if len(near_miss_examples) < 25:
                near_miss_examples.append((100.0, bid, "TYPE-only diff", sh))
            continue
        m = process.extractOne(sh, dec_keys, scorer=fuzz.ratio)
        score = m[1] if m else 0.0
        if score >= 95:
            buckets[">=95"] += 1
        elif score >= 90:
            buckets["90-95"] += 1
        elif score >= 80:
            buckets["80-90"] += 1
        else:
            buckets["<80"] += 1
        if score >= 90 and len(near_miss_examples) < 25:
            near_miss_examples.append((score, bid, m[0], sh))

    total_gap = len(reg_gap)
    recoverable = buckets["exact_streethouse"] + buckets[">=95"] + buckets["90-95"]
    for k, v in buckets.items():
        print(f"  {k:20s}: {v:5d}  ({v / total_gap * 100:4.1f}%)")
    print(f"  -> plausibly recoverable (TYPE-only or >=90 fuzzy): {recoverable} "
          f"({recoverable / total_gap * 100:.1f}% of the gap)")
    print("  near-miss examples (score | registry bid | best decree | key):")
    for score, bid, best, sh in sorted(near_miss_examples, reverse=True)[:20]:
        print(f"    {score:5.1f} | {bid:34s} -> {best}")
    print()

    # ── TEST 2 (confound-free): apt coverage within the 287 overlap ─────
    print("=== TEST 2: within the 287 buildings we have BOTH sources for, "
          "do decrees cover the registry's apartments? ===")
    # registry apts per overlapping building
    cur.execute("""
        SELECT se.property_id, u.apt_no
        FROM seizure_event se JOIN unit u ON u.id = se.unit_id
        WHERE se.stage = 'registry_inclusion'
    """)
    reg_apts = defaultdict(set)
    for pid, apt in cur.fetchall():
        reg_apts[pid].add(_norm_apt(apt))

    cur.execute("""
        SELECT property_id, detail->>'address_raw'
        FROM seizure_event
        WHERE stage IN ('ownerless_designation', 'ownerless_registration')
          AND detail->>'address_raw' IS NOT NULL
    """)
    dec_apts = defaultdict(set)
    for pid, addr in cur.fetchall():
        m = _APT_RE.search(addr or "")
        if m:
            dec_apts[pid].add(_norm_apt(m.group(1)))

    ratios = []
    fully_covered = 0
    zero_covered = 0
    detail_rows = []
    for pid in overlap_pids:
        reg_n = len(reg_apts.get(pid, set()))
        if reg_n == 0:
            continue  # building-level registry entry (no apt) — not an apt test
        dec_hit = len(reg_apts[pid] & dec_apts.get(pid, set()))
        ratio = dec_hit / reg_n
        ratios.append(ratio)
        if ratio >= 0.999:
            fully_covered += 1
        if dec_hit == 0:
            zero_covered += 1
        detail_rows.append((ratio, reg_n, dec_hit, reg.get(pid, "?"), pid))

    if ratios:
        print(f"  overlap buildings with >=1 registry apartment: {len(ratios)}")
        print(f"  median decree-coverage of registry apts:        "
              f"{statistics.median(ratios) * 100:.1f}%")
        print(f"  mean decree-coverage of registry apts:          "
              f"{statistics.mean(ratios) * 100:.1f}%")
        print(f"  fully covered (decrees name ALL registry apts):  {fully_covered} "
              f"({fully_covered / len(ratios) * 100:.1f}%)")
        print(f"  ZERO covered (decree building, but 0 apt match): {zero_covered} "
              f"({zero_covered / len(ratios) * 100:.1f}%)")
        print("  worst-covered examples (coverage | reg_apts | matched | bid):")
        for ratio, reg_n, hit, bid, pid in sorted(detail_rows)[:12]:
            print(f"    {ratio * 100:5.1f}% | {reg_n:4d} | {hit:4d} | {bid}")
    print()

    # ── TEST 3: structural corroboration ────────────────────────────────
    print("=== TEST 3: structural signature (registry = upstream funnel?) ===")
    cur.execute("""
        SELECT
          count(*) FILTER (WHERE detail->>'cadastral_number' IS NOT NULL),
          count(*)
        FROM seizure_event WHERE stage IN ('ownerless_designation','ownerless_registration')
    """)
    cad, dec_total = cur.fetchone()
    print(f"  decree rows with a cadastral/ЕГРН number: {cad}/{dec_total} "
          f"({cad / dec_total * 100:.1f}%)")
    cur.execute("""
        SELECT count(*) FILTER (WHERE detail->>'cadastral_number' IS NOT NULL), count(*)
        FROM seizure_event WHERE stage = 'registry_inclusion'
    """)
    rcad, rtot = cur.fetchone()
    print(f"  registry rows with a cadastral/ЕГРН number: {rcad}/{rtot} "
          f"({rcad / rtot * 100:.1f}%)  <- registry is pre-cadastral by construction")
    cur.execute("""
        SELECT min(event_date), max(event_date)
        FROM seizure_event WHERE stage IN ('ownerless_designation','ownerless_registration')
          AND event_date IS NOT NULL
    """)
    dmin, dmax = cur.fetchone()
    print(f"  decree-track date span: {dmin} .. {dmax}")
    print(f"  registry-track dates:   none (0/{rtot} dated) — a single undated snapshot")

    cur.close()
    con.close()

    print("\n--- READING ---")
    print("TEST 1 tells you how much of the 1,349-building gap is recoverable "
          "on our side vs. genuinely absent.")
    print("TEST 2 is the clean one: if decrees under-cover even where we HAVE "
          "them, the gap is real, not a lookup miss.")


if __name__ == "__main__":
    main()
