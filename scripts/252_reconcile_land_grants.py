#!/usr/bin/env python3
"""Reconcile data/parsed/dnr_land_orders.jsonl into a clean, de-duplicated,
fully-dated authoritative land-grant set, closing the gaps found in the
2026-07-05 archive audit:

  1. scripts/250's content filter was case-sensitive ("земельн" missed the
     clause-initial "Земельного", "собственность" missed the genitive
     "собственности"), so it silently dropped genuine grants. Fixed in
     scripts/250; this script re-derives the FULL rasp-archive land-grant
     population with the corrected, case-insensitive filter.
  2. Cross-year number reuse was real and material: e.g. Распоряжение №392
     dated 2024-10-24 (СЗ «Строительное управление-2007») and №392 dated
     2025-11-06 (СЗ-1 «Порфир») are DIFFERENT decrees sharing a number; the
     old jsonl carried only one, undated. Keying on (number, filename-date)
     -- the filename date is ground truth, see scripts/250 -- keeps them
     distinct instead of conflating them.
  3. №122/2024-03-22 (Порфир, б-р Богдана Хмельницкого 6А) was entirely
     absent (a casualty of bug #1); the corrected scan recovers it.
  4. Two duplicate rows (№178/2026-05-25 captured from both нпа + pushilin;
     №289/2023-09-07 captured twice) collapse under (number, date) keying.
  5. 18 rows had decree_date=None; those whose decree appears in the rasp
     archive get their real date, resolving the conflation above. The few
     нпа-only grants absent from the archive (№170-174, 220) are preserved
     as-is (date stays None, flagged).

Method: the rasp archive (denis-pushilin.ru/doc/rasp/, reliable filename
dates) is the authoritative spine of the land-grant population. Every
archive land grant is re-parsed with scripts/250's parser. Existing jsonl
rows (нпа.днронлайн 27-parcel batch + original glavadnr batch) are then
folded in: a row matching an archive decree by (number, date) -- or, for a
date=None row, by number + beneficiary -- ENRICHES that archive record's
NULL fields (cadastral/area/address the OCR missed) rather than adding a
duplicate; a row whose decree is NOT in the archive at all is carried over
unchanged.

Output: rewrites data/parsed/dnr_land_orders.jsonl (backup written first).
Purely file-level parse-stage work; no DB writes. Spine loading is the
separate scripts/253 step (run by the user).

Run:
    PYTHONPATH=src python scripts/252_reconcile_land_grants.py           # dry-run, prints plan
    PYTHONPATH=src python scripts/252_reconcile_land_grants.py --apply   # writes the file
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

OCR_DIR = ROOT / "data" / "parsed" / "pushilin_rasp_ukazy_ocr"
SURVEY = ROOT / "data" / "parsed" / "pushilin_rasp_ukazy_survey.jsonl"
JSONL = ROOT / "data" / "parsed" / "dnr_land_orders.jsonl"
BACKUP = ROOT / "data" / "parsed" / "dnr_land_orders.jsonl.pre252.bak"

# Import scripts/250's parser (reuse, don't duplicate).
_spec = importlib.util.spec_from_file_location(
    "p250", ROOT / "scripts" / "250_parse_pushilin_land_grants.py")
p250 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(p250)


def _is_landgrant(text: str) -> bool:
    tl = text.lower()
    return ("без проведения торгов" in tl and "мариупол" in tl
            and "инвестиционного проекта" in tl and "земельн" in tl)


def _ben_tokens(name: str | None) -> set[str]:
    """Distinctive lowercase word tokens of a beneficiary name, for matching
    an undated нпа row to the right archive instance (drops the generic
    «Специализированный застройщик» wrapper words)."""
    if not name:
        return set()
    stop = {"специализированный", "застройщик", "специализированный-1", "ооо", "ук",
            "общество", "управляющая", "компания", "«", "»"}
    toks = re.findall(r"[а-яёa-z0-9]+", name.lower())
    return {t for t in toks if t not in stop and len(t) > 2}


def _archive_landgrants() -> dict[tuple[str, str], dict]:
    """Re-parse every rasp-archive land grant with the corrected filter.
    Keyed by (decree_number, decree_date)."""
    survey = [json.loads(l) for l in SURVEY.read_text(encoding="utf-8").splitlines() if l.strip()]
    out: dict[tuple[str, str], dict] = {}
    for r in survey:
        if r.get("folder") != "rasp" or "error" in r:
            continue
        txt = OCR_DIR / f"{r['sha256']}.txt"
        if not txt.exists():
            continue
        text = txt.read_text(encoding="utf-8", errors="replace")
        if not _is_landgrant(text):
            continue
        rec = p250.parse_ocr_text(text, r["sha256"], r["url"])
        key = (str(rec["decree_number"]), rec["decree_date"])
        if key in out:
            # Same (num,date) captured twice in the archive -- keep the
            # richer parse (more non-null fields).
            if _richness(rec) > _richness(out[key]):
                out[key] = rec
        else:
            out[key] = rec
    return out


_ENRICH_FIELDS = ["cadastral_numbers", "area_sqm", "address_raw", "address_normalized",
                  "beneficiary_ogrn", "beneficiary_inn", "beneficiary_inn_source",
                  "project_name", "signing_official"]


def _richness(rec: dict) -> int:
    return sum(1 for f in _ENRICH_FIELDS if rec.get(f))


def _enrich(target: dict, donor: dict) -> None:
    """Fill target's NULL/empty fields from donor (donor = an existing jsonl
    row). Never overwrites a value the authoritative archive parse already has."""
    for f in _ENRICH_FIELDS:
        tv = target.get(f)
        if (tv is None or tv == [] or tv == "") and donor.get(f):
            target[f] = donor[f]
    # drop now-resolved flags
    fixed = set()
    if target.get("cadastral_numbers"):
        fixed.add("cadastral_missing")
    if target.get("area_sqm") is not None:
        fixed.add("area_missing")
    if target.get("address_normalized") or target.get("address_raw"):
        fixed.add("address_missing")
    if target.get("beneficiary_name"):
        fixed.add("beneficiary_missing")
    target["flags"] = [fl for fl in target.get("flags", []) if fl not in fixed]
    target.setdefault("enriched_from", []).append(donor.get("source_sha256"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write the reconciled file (default: dry-run)")
    args = ap.parse_args()

    existing = [json.loads(l) for l in JSONL.read_text(encoding="utf-8").splitlines() if l.strip()]
    archive = _archive_landgrants()

    # index archive by number for date=None resolution
    by_num: dict[str, list[tuple[str, dict]]] = {}
    for (num, dt), rec in archive.items():
        by_num.setdefault(num, []).append((dt, rec))

    carried_over: list[dict] = []
    stats = {"archive": len(archive), "enriched": 0, "carried_over": 0,
             "dedup_merged": 0, "date_resolved": 0, "unresolved_date": 0}

    for row in existing:
        num = str(row.get("decree_number"))
        dt = row.get("decree_date")
        if dt and (num, dt) in archive:
            _enrich(archive[(num, dt)], row)
            stats["enriched"] += 1
            continue
        if dt is None:
            cands = by_num.get(num, [])
            chosen = None
            if len(cands) == 1:
                chosen = cands[0][1]
            elif len(cands) > 1:
                rt = _ben_tokens(row.get("beneficiary_name"))
                scored = [(len(rt & _ben_tokens(rec.get("beneficiary_name"))), rec) for _, rec in cands]
                scored.sort(key=lambda x: x[0], reverse=True)
                if scored and scored[0][0] > 0:
                    chosen = scored[0][1]
            if chosen is not None:
                _enrich(chosen, row)
                stats["enriched"] += 1
                stats["date_resolved"] += 1
                continue
            # no archive match -> carry over (нпа-only grant, e.g. №170-174/220)
            row.setdefault("flags", [])
            if "date_unresolved" not in row["flags"]:
                row["flags"].append("date_unresolved")
            carried_over.append(row)
            stats["carried_over"] += 1
            stats["unresolved_date"] += 1
            continue
        # dated row whose (num,date) is NOT in the archive -> non-archive grant
        # (original glavadnr batch); carry over unchanged.
        carried_over.append(row)
        stats["carried_over"] += 1

    # count dedup: existing rows that collapsed onto archive records
    stats["dedup_merged"] = len(existing) - stats["carried_over"] - (
        len(existing) - stats["enriched"] - stats["carried_over"])

    final = list(archive.values()) + carried_over
    final.sort(key=lambda r: (str(r.get("decree_date") or "0000"), str(r.get("decree_number"))))

    print(f"existing jsonl rows:        {len(existing)}")
    print(f"rasp-archive land grants:   {stats['archive']}")
    print(f"  enriched from existing:   {stats['enriched']}  (of which date-resolved: {stats['date_resolved']})")
    print(f"carried over (non-archive): {stats['carried_over']}  (unresolved date: {stats['unresolved_date']})")
    print(f"FINAL reconciled rows:      {len(final)}")
    # sanity: any residual duplicate (num,date)?
    seen = {}
    dups = 0
    for r in final:
        k = (str(r.get("decree_number")), r.get("decree_date"))
        if k in seen and k[1] is not None:
            dups += 1
            print(f"  !! residual duplicate {k}")
        seen[k] = True
    print(f"residual (num,date) duplicates: {dups}")

    # is №122 present?
    has122 = any(str(r.get("decree_number")) == "122" and r.get("decree_date") == "2024-03-22" for r in final)
    print(f"№122/2024-03-22 present:    {has122}")

    if not args.apply:
        print("\n(dry-run; re-run with --apply to write the file)")
        return

    shutil.copy2(JSONL, BACKUP)
    with JSONL.open("w", encoding="utf-8") as fh:
        for r in final:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nWROTE {len(final)} rows to {JSONL}")
    print(f"backup: {BACKUP}")


if __name__ == "__main__":
    main()
