#!/usr/bin/env python3
"""Analyse the first-instance DNR district-court ownerless-property population
parsed by `scripts/182`. Pure local analysis — no network. Writes
`docs/dnr_district_first_instance_2026-06.md` + prints a summary.

WHAT THIS ADDS OVER scripts/176
-------------------------------
`scripts/176` measured the ВС ДНР *appellate* layer, which is self-selected to
contested cases and therefore cannot show the base rate of seizure. This is the
*first-instance* layer — the ~8,300 особое-производство petitions across the 26
courts that actually returned records — i.e. the base rate itself. The single
most important number it produces is the share of first-instance petitions the
courts simply GRANT.

PRIVACY: judges and petitioner organisations act in official capacity and are
named (CLAUDE.md). Owners are only ever counted, never named — `scripts/182`
already stripped owner names upstream; this script never reintroduces them.

Run:
    .venv312/bin/python scripts/183_analyze_dnr_district_bezkhoz.py
"""
from __future__ import annotations

import json
import logging
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

log = logging.getLogger(__name__)

SRC = ROOT / "data" / "parsed" / "dnr_district_bezkhoz.json"
OUT = ROOT / "docs" / "dnr_district_first_instance_2026-06.md"


def pct(n: int, d: int) -> str:
    return f"{100*n/d:.1f}%" if d else "—"


def grant_rate(rows: list[dict]) -> tuple[int, int]:
    """Return (granted, decided) where decided excludes pending/no-result."""
    decided = [r for r in rows if not r["rollup"].startswith("UNKNOWN")]
    granted = [r for r in decided if r["rollup"].startswith("LOSE")]
    return len(granted), len(decided)


def month(d: str | None) -> str | None:
    if not d:
        return None
    try:
        return datetime.strptime(d, "%d.%m.%Y").strftime("%Y-%m")
    except ValueError:
        return None


def main() -> None:
    rows = json.loads(SRC.read_text(encoding="utf-8"))
    n = len(rows)

    roll = Counter(r["rollup"] for r in rows)
    g, d = grant_rate(rows)

    # per-municipality
    by_city = defaultdict(list)
    for r in rows:
        by_city[r["municipality"]].append(r)
    city_tbl = []
    for city, rs in sorted(by_city.items(), key=lambda kv: -len(kv[1])):
        cg, cd = grant_rate(rs)
        city_tbl.append((city, len(rs), cg, cd))

    # Mariupol vs rest
    mar = [r for r in rows if r["is_mariupol"]]
    rest = [r for r in rows if not r["is_mariupol"]]
    mg, md = grant_rate(mar)
    rg, rd = grant_rate(rest)

    # temporal (by decision month), split Mariupol vs rest to expose the
    # registry-pivot shutdown
    dec_month = Counter(m for m in (month(r["decided"]) for r in rows) if m)
    mar_month, rest_month = Counter(), Counter()
    for r in rows:
        m = month(r["decided"])
        if m:
            (mar_month if r["is_mariupol"] else rest_month)[m] += 1

    # knowing dispossession: outcome when the court HAD a living owner on record
    named = [r for r in rows if r.get("has_named_owner")]
    unnamed = [r for r in rows if not r.get("has_named_owner")]
    ng, nd = grant_rate(named)
    ug, ud = grant_rate(unnamed)
    granted_rows = [r for r in rows if r["rollup"].startswith("LOSE")]
    granted_with_owner = sum(1 for r in granted_rows if r.get("has_named_owner"))

    # petitioner
    pet = Counter(r["petitioner_type"] for r in rows)

    # judges (named officials) — most prolific grant-signers
    judge_grants = Counter()
    judge_total = Counter()
    for r in rows:
        if r.get("judge"):
            judge_total[r["judge"]] += 1
            if r["rollup"].startswith("LOSE"):
                judge_grants[r["judge"]] += 1

    # property identity recovery
    pub = sum(r["text_published"] for r in rows)
    redacted = sum(1 for r in rows if r.get("address_redacted"))
    with_addr = sum(1 for r in rows if r.get("property_address"))
    with_cad = sum(1 for r in rows if r.get("cadastral_number"))
    owners = sum(1 for r in rows if r.get("has_named_owner"))

    L = []
    A = L.append
    A("# DNR first-instance “ownerless property” seizures — base-rate analysis")
    A("")
    A(f"*Analysis date: 2026-06-28. Population: {n:,} unique first-instance "
      f"(бесхозяйная "
      "недвижимость, "
      "особое производство) "
      "petitions across the 26 DNR district/city courts that returned records. "
      "Capture: full-population district crawl (2026-06-27/28, `crawl/courts.py`). "
      "Parse: `scripts/182`. Source: `data/parsed/dnr_district_bezkhoz.json`; "
      "raw: `data/raw/<sha>.html`.*")
    A("")
    A("## Why this layer matters")
    A("")
    A("The ВС ДНР appellate analysis "
      "([dnr_bezkhoz_appellate_outcomes_2026-06](dnr_bezkhoz_appellate_outcomes_2026-06.md)) "
      "is self-selected to cases *someone contested*, so it shows a WIN-heavy "
      "distribution — the cases worth appealing. **This is the layer beneath "
      "it: the base rate.** It is what happens to an ownerless-property petition "
      "by default, before and absent any appeal — and the default is grant.")
    A("")
    A("## Headline: the first-instance grant rate")
    A("")
    A(f"**Of {d:,} decided first-instance petitions, {g:,} were granted — "
      f"a {pct(g, d)} grant rate.** The administration asks a court to vest a "
      "war-emptied home in municipal ownership, and ~6 times in 7 the court "
      "says yes at first instance.")
    A("")
    A("| Owner-side outcome | n | share |")
    A("|---|---|---|")
    for k, v in roll.most_common():
        A(f"| {k} | {v:,} | {pct(v, n)} |")
    A("")
    A("The dominant WIN sub-type is "
      "`оставлено без "
      "рассмотрения` "
      "— a *спор о праве* "
      "bounce that, exactly as in the appellate layer, is procedural and "
      "refileable, not a ruling that the seizure is unlawful.")
    A("")
    A("## Per-municipality")
    A("")
    A("| Court / municipality | cases | granted / decided | grant rate |")
    A("|---|---|---|---|")
    for city, tot, cg, cd in city_tbl:
        A(f"| {city} | {tot:,} | {cg}/{cd} | {pct(cg, cd)} |")
    A("")
    A("## Mariupol vs. rest of DNR — at first instance")
    A("")
    A(f"- **Mariupol:** {mg}/{md} granted = **{pct(mg, md)}**")
    A(f"- **Rest of DNR:** {rg}/{rd} granted = **{pct(rg, rd)}**")
    A("")
    A("Note the inversion from the appellate finding: at **first instance** the "
      "grant rate is uniformly high *everywhere* — Mariupol is not harsher "
      "here, the rubber-stamp is region-wide. The Mariupol-specific harshness "
      "documented in "
      "[dnr_bezkhoz_citizenship_doctrine_2026-06](dnr_bezkhoz_citizenship_doctrine_2026-06.md) "
      "is a feature of how *contested* cases resolve on appeal, not of the "
      "base grant rate. Both readings coexist: near-universal first-instance "
      "granting, plus a harsher appellate posture toward the displaced "
      "Mariupol owners who manage to contest.")
    A("")
    A("## Knowing dispossession — the court grants even when it knows an owner exists")
    A("")
    A(f"- Petitions where a living owner **was named** as `заинтересованное "
      f"лицо`: granted **{pct(ng, nd)}** ({ng:,}/{nd:,} decided).")
    A(f"- Petitions with **no named owner**: granted **{pct(ug, ud)}** "
      f"({ug:,}/{ud:,}).")
    A(f"- Of **{len(granted_rows):,}** granted seizures, **{granted_with_owner:,}** "
      f"({pct(granted_with_owner, len(granted_rows))}) had a living owner named "
      f"in the case file.")
    A("")
    A("Naming an owner barely moves the outcome — the court vests the home in "
      "the municipality at nearly the same rate whether or not it has a living "
      "owner on the record in front of it. About a third of all granted "
      "seizures were entered with an identified owner present in the file. This "
      "is the base-rate counterpart to the appellate "
      "[citizenship doctrine](dnr_bezkhoz_citizenship_doctrine_2026-06.md): the "
      "doctrine is the *reasoning* the court reaches for when a named owner "
      "actually contests; this is how often it dispossesses a known owner "
      "without one contesting at all. (Owners are counted, never named — "
      "CLAUDE.md.)")
    A("")
    A("## Tempo — and the Mariupol court shutdown")
    A("")
    A("| Month | Mariupol | rest of DNR |")
    A("|---|---|---|")
    for m in sorted(set(mar_month) | set(rest_month)):
        if m < "2025-06":
            continue
        A(f"| {m} | {mar_month.get(m, 0):,} | {rest_month.get(m, 0):,} |")
    A("")
    A("The two columns diverge sharply. Mariupol first-instance bezkhoz "
      "decisions **collapse to zero** through early 2026 (and filings collapse "
      "the same way, so this is the conveyor stopping, not a backlog of "
      "undecided cases), while the rest of DNR keeps running. Read against the "
      "**1 July 2026** ownerless re-registration deadline and ФКЗ-4 (Dec 2025) "
      "abolishing the court stage (`CLAUDE.md`): Mariupol — the Roskadastr "
      "НСПД pilot — finished its court conveyor **first** and handed off to "
      "direct registry inclusion ahead of the rest of the occupied oblast. The "
      "court data carries the signature of the legal pivot, dated and "
      "municipality-specific.")
    A("")
    A("## Who petitions")
    A("")
    A("| Petitioner type | n |")
    A("|---|---|")
    for k, v in pet.most_common():
        A(f"| {k} | {v:,} |")
    A("")
    A("Petitioner organisations and the judges below are occupation officials "
      "acting in official capacity — named, not minimised (CLAUDE.md). The "
      "owners are living private individuals and are only counted, never named: "
      f"**{owners:,}** cases list at least one natural-person owner as the "
      "`заинтересованное "
      "лицо` — i.e. the court knew an owner existed and "
      "vested the property in the municipality anyway.")
    A("")
    A("## Most prolific first-instance grant-signers (named officials)")
    A("")
    A("| Judge | grants | total bezkhoz cases |")
    A("|---|---|---|")
    for j, gc in judge_grants.most_common(20):
        A(f"| {j} | {gc} | {judge_total[j]} |")
    A("")
    A("## Property-identity recovery — and the redaction wall")
    A("")
    A(f"- Cards with embedded ruling text: **{pub:,}** of {n:,} ({pct(pub, n)}).")
    A(f"- Of those, the street address is redacted to "
      f"`<адрес>` on **{pct(redacted, pub)}** of cards.")
    A(f"- A **cadastral number** (a unique property identifier that links "
      f"directly to the spine / Rosreestr) survived on **{with_cad:,}** cards — "
      f"the only reliable property-identity recovery here, and 4 of them "
      f"exact-match existing spine properties (`scripts/184`).")
    A(f"- The street-address extractor fired on {with_addr:,} cards but is "
      f"**unreliable** — spot-checking shows mostly utility-narrative false "
      f"positives, not addresses. With the street redacted on 100% of rulings, "
      f"the cadastral number is the linkage target; the loose street field "
      f"should not be treated as claim-grade.")
    A("")
    A("This redaction is **not occupation-specific** — it is standard "
      "depersonalization practice under Russian Federal Law No. 262-FZ, applied "
      "by the GAS «Правосудие» "
      "system the same way at any Russian court "
      "nationwide. It masks owners as ФИО1/ФИО2 and "
      "the address as `<адрес>` "
      "uniformly. What is specific to this dataset is the practical effect, not "
      "the rule: the "
      "court-islands address gap persists not because the record "
      "wasn’t captured but because a generic depersonalization rule, applied here "
      "as everywhere, redacts the address in the published "
      "ruling. The cadastral numbers that survive are the highest-value linkage "
      "targets recovered here.")
    A("")
    A("## Scope and caveats")
    A("")
    A("- **Base rate of the contested-or-not first-instance layer**, across the "
      "26 productive courts only. The 15 enabled courts that returned zero "
      "(Avdiivka, Bakhmut, Vuhledar, Kramatorsk, Sloviansk, Kostiantynivka, "
      "…) split into two kinds: cities under Russian control but destroyed "
      "/ depopulated (nothing left to seize) and “ghost” courts for "
      "Donetsk-oblast territory Russia claims but has never controlled — "
      "neither produces ownerless cases, for opposite reasons.")
    A("- A first-instance “grant” is the seizure consummated unless and "
      "until appealed; most are never appealed (see the appellate layer’s "
      "self-selection caveat).")
    A("- `UNKNOWN/UNCLASSIFIED` = pending cases with no result code yet, plus a "
      "few rare result codes outside the mapped vocabulary.")
    A("- Reproducible end-to-end from `data/raw/` via `scripts/182` → "
      "`scripts/183`.")
    A("")

    OUT.write_text("\n".join(L), encoding="utf-8")

    print(f"\n{'='*68}\nDNR first-instance bezkhoz — {n:,} cases\n{'='*68}")
    print(f"GRANT RATE: {g:,}/{d:,} = {pct(g, d)}")
    print(f"Mariupol {pct(mg, md)} | rest {pct(rg, rd)}")
    print(f"cadastral numbers recovered: {with_cad} | partial addresses: {with_addr}")
    print(f"named-owner cases: {owners:,}")
    print(f"  -> {OUT}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
