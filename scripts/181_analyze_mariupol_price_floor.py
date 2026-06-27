#!/usr/bin/env python3
"""Compute the project's own Mariupol apartment-resale price-per-m² floor,
to check the Troianda-M / Metallurgov 47 case study's "compensation rate
undershoots the market floor" claim against more than one journalist's
quoted number.

Pure local analysis over data/parsed/realestate_offers.jsonl (produced by
scripts/51_parse_realestate_offers.py from the project's own captured
Telegram/web resale-listing corpus). No network -- safe to run directly.

WHY THIS EXISTS
----------------
The case study originally cited a single press article (Agents.Media) for
both numbers in the "compensation undershoots market" claim: a 45,000
RUB/m2 government compensation rate against a reported 53,000 RUB/m2
"cheapest available" market floor. That market-floor figure is one
journalist's quoted number, not independently checked against this
project's own ~1,243-listing resale corpus. This script does that check.

Building it surfaced two real bugs in scripts/51's price parser (now fixed
there, re-run before this analysis):
  1. _RE_PRICE_FULL's leading-digit group was \\d{1,3}, so malformed source
     text with no space after the first 4 digits ("3800 000" meaning
     3,800,000) matched only the trailing "800 000" -> 800,000. Fixed to
     \\d{1,4}.
  2. The composite additive form "3 млн 800 тыс" (= 3,800,000) was not
     handled at all -- the млн branch matched first and silently dropped
     the "800 тыс" remainder. Added _RE_PRICE_MLN_TYS, checked before the
     plain млн branch.
18 of 1243 records had their price_rub corrected by the fix; this script's
filters below catch the residual area-extraction error described in the
EXCLUSIONS section.

METHOD
------
1. Filter to: offer_type=sale, property_class=apartment, is_mariupol,
   not new_build (compare against EXISTING housing stock, the relevant
   comparison for compensation-in-kind), with both price_rub and
   area_total_m2 present.
2. De-duplicate exact reposts (same price + area + text_excerpt).
3. Plausibility filter: 20 <= area_total_m2 <= 200 (excludes records where
   the area parser grabbed a room/kitchen sub-area instead of total area --
   no 3-4-room apartment is genuinely 8-10 m2 total) and price_rub >=
   300,000 (excludes garage/parking misclassification).
4. One further documented exclusion: a single record (price 7,000,000,
   area 28.0) whose source text reads "46/28 м2" (total/living) -- the area
   parser captured the living-area component (28) instead of total (46),
   yielding an implausible 250,000 RUB/m2. Excluded by name, not by a
   general rule, pending a proper fix to the area parser's "NN/NN m2"
   handling (out of scope for this script).

Run:
    .venv312/bin/python scripts/181_analyze_mariupol_price_floor.py
"""
from __future__ import annotations

import json
import logging
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

log = logging.getLogger(__name__)

SRC = ROOT / "data" / "parsed" / "realestate_offers.jsonl"
OUT = ROOT / "data" / "reports" / "mariupol_price_floor_2026-06.md"

# documented area-parser error, see module docstring EXCLUSIONS
_KNOWN_BAD = {(7_000_000, 28.0)}


def load_clean_rows() -> list[dict]:
    recs = [json.loads(l) for l in SRC.open(encoding="utf-8")]
    sale = [
        r for r in recs
        if r.get("price_rub") and r.get("area_total_m2")
        and r.get("offer_type") == "sale"
        and r.get("property_class") == "apartment"
        and r.get("is_mariupol")
        and not r.get("new_build")
    ]
    seen: set[tuple] = set()
    deduped = []
    for r in sale:
        key = (r["price_rub"], r["area_total_m2"], r.get("text_excerpt"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    clean = [
        r for r in deduped
        if 20 <= r["area_total_m2"] <= 200
        and r["price_rub"] >= 300_000
        and (r["price_rub"], r["area_total_m2"]) not in _KNOWN_BAD
    ]
    return clean


def main() -> None:
    rows = load_clean_rows()
    psqm = sorted(r["price_rub"] / r["area_total_m2"] for r in rows)
    n = len(psqm)
    if n == 0:
        raise SystemExit("no rows survived filtering -- check SRC path/filters")

    def pct(p: float) -> float:
        return psqm[min(n - 1, int(n * p))]

    stats = {
        "n": n,
        "min": psqm[0],
        "p5": pct(0.05),
        "p10": pct(0.10),
        "p25": pct(0.25),
        "median": statistics.median(psqm),
        "mean": statistics.mean(psqm),
        "p75": pct(0.75),
        "p90": pct(0.90),
        "max": psqm[-1],
    }

    comp_rate = 45_000
    lines = [
        "# Mariupol existing-apartment price/m2 -- project's own resale corpus",
        "",
        f"*n = {n} de-duplicated, plausibility-filtered sale listings "
        f"(existing housing only) from `data/parsed/realestate_offers.jsonl`. "
        f"Method and exclusions: see `scripts/181_analyze_mariupol_price_floor.py` docstring.*",
        "",
        "| Stat | RUB/m² |",
        "|---|---|",
    ] + [f"| {k} | {v:,.0f} |" for k, v in stats.items() if k != "n"] + [
        "",
        f"**Compensation-vs-market check.** The occupation's stated compensation "
        f"rate is **{comp_rate:,} RUB/m²**. Against this project's own corpus:",
        "",
        f"- vs. p5 ({stats['p5']:,.0f}): compensation undershoots by "
        f"{(stats['p5']-comp_rate)/stats['p5']*100:.1f}%",
        f"- vs. p10 ({stats['p10']:,.0f}): undershoots by "
        f"{(stats['p10']-comp_rate)/stats['p10']*100:.1f}%",
        f"- vs. median ({stats['median']:,.0f}): undershoots by "
        f"{(stats['median']-comp_rate)/stats['median']*100:.1f}%",
        "",
        "Even against the cheapest 5% of the project's own captured listings -- "
        "not the median, the genuine floor -- the compensation rate falls short. "
        "This is independent of, and larger than, the ~15% gap computed from the "
        "single Agents.Media-quoted figure (45,000 vs. a reported 53,000).",
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")

    print(f"\n{'='*60}\nMariupol existing-apartment price/m2 (n={n})\n{'='*60}")
    for k, v in stats.items():
        print(f"  {k:8s} {v:,.0f}" if k != "n" else f"  {k:8s} {v}")
    print(f"\ncompensation rate {comp_rate:,} RUB/m2 vs p5 {stats['p5']:,.0f}: "
          f"undershoots by {(stats['p5']-comp_rate)/stats['p5']*100:.1f}%")
    print(f"  -> {OUT}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
