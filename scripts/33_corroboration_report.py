#!/usr/bin/env python3
"""Cross-source corroboration report (read-only analysis over the loaded DB).

Answers the Berkeley-Protocol question CLAUDE.md sets ("require >=2 independent
sources for legal-grade linkage"): for each Mariupol property on the spine, how
many INDEPENDENT occupation/federal documentary sources attest to its seizure /
destruction, and which properties clear the >=2-source legal-grade bar.

Independence here = distinct documentary source FAMILY. With one exception, all
families are occupation-internal or Russian-federal records; their value is as
self-incriminating admissions (CLAUDE.md), not neutral third-party verification.
The exception is independent_corroboration (Tier-3, UN/satellite/testimony --
see docs/tier3_corroboration_design.md), which IS neutral third-party
verification but speaks only to physical war damage, not to the seizure act
itself. The report says so explicitly. Source families:
  court_case          -- GAS Pravosudie court records (court_petition/transfer/appeal)
  ownerless_decree    -- occupation 'бесхозяйное' designation decrees
  ownerless_registry  -- post-ФКЗ-4 ownerless-property master registry (title transfer)
  demolition          -- MinStroy/ГКО demolition register + admin 'о сносе' decrees
  reallocation        -- ЕИСЖС new-build / DNR land-order beneficiary grants
  housing_distribution-- occupation displaced-persons distribution lists (corroboration)
  damage_assessment   -- Russian federal damage/reconstruction priority tracker (corroboration)
  independent_corroboration -- UN/satellite/testimony attestations, independent of
                        the occupation administration (corroboration kinds
                        unosat_damage/satellite_pair/testimony_ref/ua_registry_mirror;
                        counted only when verdict='confirms' AND confidence>=0.8)

OUTPUTS (data/reports/):
  corroboration_report.md        -- human-readable findings + methodology
  corroboration_legalgrade.csv   -- every property with >=2 independent families
  corroboration_candidates.csv   -- near-miss merge candidates (REVIEW ONLY, not applied)

This script does NOT mutate the database. The near-miss candidates are surfaced
for human review (CLAUDE.md: "rather miss than collide"; no regex-only address
merge as a final step). Run AFTER all loaders (03/27/28/30/31/32).
"""
from __future__ import annotations

import csv
import logging
import re
import sys
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

import psycopg2
from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402

log = logging.getLogger("corroboration_report")

# stage / corroboration-kind -> independent source family
SEIZURE_FAMILY = {
    "court_petition": "court_case",
    "court_transfer": "court_case",
    "appeal": "court_case",
    "entered_force": "court_case",
    "ownerless_designation": "ownerless_decree",
    "registry_inclusion": "ownerless_registry",
    "demolition": "demolition",
    "reallocation": "reallocation",
}
CORRO_FAMILY = {
    "displacement_claim": "housing_distribution",
    "mirror_source": "damage_assessment",
}
# Tier-3 independent-provenance kinds (docs/tier3_corroboration_design.md S4
# "Counting rule"): these are NOT occupation/federal records -- UN analyst /
# satellite / testimony attestations. They count toward n_sources only when
# the row is a confirmed, claim-grade physical finding (verdict='confirms'
# AND confidence >= 0.8); collectively treated as one additional family,
# since each adds "a second, independent provenance family" (design doc S1).
INDEPENDENT_CORRO_KINDS = {"unosat_damage", "satellite_pair", "testimony_ref", "ua_registry_mirror"}
INDEPENDENT_FAMILY = "independent_corroboration"
ALL_FAMILIES = ["court_case", "ownerless_decree", "ownerless_registry",
                "demolition", "reallocation", "housing_distribution",
                "damage_assessment", INDEPENDENT_FAMILY]
# Families that can actually co-occur on one property row (i.e. address-bearing).
# court_case rows are address-redacted islands and never share a property row.

NEARMISS_SCORE = 85  # WRatio threshold on the street stem (review-only)


def _connect():
    return psycopg2.connect(config.DATABASE_URL)


def gather(cur) -> dict:
    """Build per-property family sets + the metadata the report needs."""
    cur.execute("""
        SELECT id, building_id, occupation_address, prewar_address,
               rd4u_category, geom IS NOT NULL AS has_geom,
               ST_X(geom), ST_Y(geom)
        FROM property
    """)
    props = {}
    for pid, bid, occ, pre, rd4u, has_geom, lon, lat in cur.fetchall():
        props[pid] = {
            "building_id": bid, "occupation_address": occ,
            "prewar_address": pre, "rd4u_category": rd4u,
            "has_geom": has_geom, "lon": lon, "lat": lat,
            "families": set(), "stage_dates": {}, "destruction_pct": None,
        }

    # seizure_event families + earliest date per stage
    cur.execute("SELECT property_id, stage, event_date FROM seizure_event")
    for pid, stage, ev in cur.fetchall():
        p = props.get(pid)
        if not p:
            continue
        fam = SEIZURE_FAMILY.get(stage)
        if fam:
            p["families"].add(fam)
        if ev and (stage not in p["stage_dates"] or ev < p["stage_dates"][stage]):
            p["stage_dates"][stage] = ev

    # corroboration families (+ pull destruction_pct from damage rows)
    cur.execute("SELECT property_id, kind, detail, verdict, confidence FROM corroboration")
    for pid, kind, detail, verdict, confidence in cur.fetchall():
        p = props.get(pid)
        if not p:
            continue
        fam = CORRO_FAMILY.get(kind)
        if fam:
            p["families"].add(fam)
        # confidence is NUMERIC(3,2) -> Decimal; compare against Decimal, not the
        # float 0.8 (which is ~0.8000000000000000444 and would exclude exactly
        # Decimal('0.80') rows).
        elif kind in INDEPENDENT_CORRO_KINDS and verdict == "confirms" and (confidence or 0) >= Decimal("0.80"):
            p["families"].add(INDEPENDENT_FAMILY)
        if kind == "mirror_source" and detail:
            pct = detail.get("destruction_pct")
            if pct is not None:
                p["destruction_pct"] = max(p["destruction_pct"] or 0, pct)
    return props


def _numeric_tokens(s: str) -> set[str]:
    """Return all digit sequences found in a street stem."""
    return set(re.findall(r"\d+", s))


def _alpha_stem(s: str) -> str:
    """Strip digit sequences (and surrounding whitespace) from a street stem."""
    return re.sub(r"\s*\d+\s*", " ", s).strip()


# Geom distance below which coordinates override the numeric-token guard.
_GEOM_OVERRIDE_M = 50.0


def near_miss_candidates(props: dict) -> list[dict]:
    """Property rows that likely denote the SAME building but did not merge
    (different building_id) -- normalization noise (garbage prefixes, OCR
    typos, comma artefacts, STREET vs UNKNOWN class drift). Method: group by
    normalized house suffix, fuzzy-compare the street stem within each group.
    Pairs scoring >= NEARMISS_SCORE are surfaced for review. We flag whether a
    merge would actually UNITE distinct families (i.e. add corroboration)."""
    by_house: dict[str, list[int]] = defaultdict(list)
    for pid, p in props.items():
        bid = p["building_id"]
        if not bid or "|" not in bid:
            continue
        house = bid.split("|", 1)[1]
        by_house[house].append(pid)

    cands = []
    for house, pids in by_house.items():
        if len(pids) < 2:
            continue
        for i in range(len(pids)):
            for j in range(i + 1, len(pids)):
                a, b = props[pids[i]], props[pids[j]]
                stem_a = a["building_id"].split(":", 1)[-1].split("|", 1)[0]
                stem_b = b["building_id"].split(":", 1)[-1].split("|", 1)[0]
                if stem_a == stem_b:
                    continue  # identical stem, only class differs handled below
                score = fuzz.WRatio(stem_a, stem_b)
                if score < NEARMISS_SCORE:
                    continue

                # ── numeric-token guard ──────────────────────────────────────
                # Compute geom distance first so we can use it as an override.
                dist_m = None
                if a["has_geom"] and b["has_geom"]:
                    dist_m = round(_haversine(a["lat"], a["lon"],
                                              b["lat"], b["lon"]), 1)
                geom_confirms = dist_m is not None and dist_m < _GEOM_OVERRIDE_M

                if not geom_confirms:
                    nums_a = _numeric_tokens(stem_a)
                    nums_b = _numeric_tokens(stem_b)
                    if nums_a and nums_b:
                        if nums_a != nums_b:
                            # Different ordinals/квартал numbers are
                            # discriminating: "24 квартал" ≠ "25 квартал",
                            # "1 Кальчик" ≠ "2 Кальчик".
                            continue
                        else:
                            # Same ordinal but different alpha parts:
                            # "1 мая" vs "1 Кальчик" — the shared digit
                            # drove the WRatio up; check alpha similarity.
                            alpha_a = _alpha_stem(stem_a)
                            alpha_b = _alpha_stem(stem_b)
                            if (alpha_a and alpha_b
                                    and fuzz.WRatio(alpha_a, alpha_b) < NEARMISS_SCORE):
                                continue

                    # Suffix guard: one stem being a strict suffix of the
                    # other inflates WRatio ("строителей" ⊂ "машиностроителей")
                    # but they are different streets. Require geom if either
                    # stem is a proper suffix (>= 50% of the longer stem).
                    sa, sb = stem_a.replace(" ", ""), stem_b.replace(" ", "")
                    longer, shorter = (sa, sb) if len(sa) >= len(sb) else (sb, sa)
                    if (shorter and longer.endswith(shorter)
                            and len(shorter) / len(longer) >= 0.5):
                        continue  # suffix match without geom confirmation
                # ── end guard ────────────────────────────────────────────────

                fam_union = a["families"] | b["families"]
                adds_corro = len(fam_union) > max(len(a["families"]),
                                                  len(b["families"]))
                cands.append({
                    "score": round(score / 100, 3),
                    "house": house,
                    "building_id_a": a["building_id"],
                    "building_id_b": b["building_id"],
                    "address_a": a["occupation_address"],
                    "address_b": b["occupation_address"],
                    "families_a": "+".join(sorted(a["families"])) or "(none)",
                    "families_b": "+".join(sorted(b["families"])) or "(none)",
                    "merge_adds_corroboration": adds_corro,
                    "geom_dist_m": dist_m,
                })
    cands.sort(key=lambda c: (not c["merge_adds_corroboration"], -c["score"]))
    return cands


def _haversine(lat1, lon1, lat2, lon2) -> float:
    from math import asin, cos, radians, sin, sqrt
    r = 6371000.0
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    h = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * r * asin(sqrt(h))


def write_outputs(props: dict, cands: list[dict], outdir: Path) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)

    # ---- aggregate stats ----
    fam_property_count = Counter()
    for p in props.values():
        for f in p["families"]:
            fam_property_count[f] += 1

    strength = Counter(len(p["families"]) for p in props.values())
    legal = {pid: p for pid, p in props.items() if len(p["families"]) >= 2}
    court_islands = {pid: p for pid, p in props.items()
                     if p["families"] == {"court_case"}}
    zero = {pid: p for pid, p in props.items() if not p["families"]}

    # family-pair co-occurrence among legal-grade rows
    pair_counts = Counter()
    for p in legal.values():
        fams = sorted(p["families"])
        for i in range(len(fams)):
            for j in range(i + 1, len(fams)):
                pair_counts[(fams[i], fams[j])] += 1

    # ---- legal-grade CSV ----
    lg_csv = outdir / "corroboration_legalgrade.csv"
    with lg_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["property_id", "n_families", "families", "occupation_address",
                    "prewar_address", "rd4u_category", "destruction_pct",
                    "ownerless_designation_date", "registry_inclusion_date",
                    "demolition_date", "court_transfer_date", "has_geom"])
        for pid, p in sorted(legal.items(),
                             key=lambda kv: (-len(kv[1]["families"]),
                                             kv[1]["occupation_address"] or "")):
            sd = p["stage_dates"]
            w.writerow([
                pid, len(p["families"]), "+".join(sorted(p["families"])),
                p["occupation_address"], p["prewar_address"], p["rd4u_category"],
                p["destruction_pct"],
                sd.get("ownerless_designation"), sd.get("registry_inclusion"),
                sd.get("demolition"), sd.get("court_transfer"),
                "yes" if p["has_geom"] else "no",
            ])

    # ---- candidates CSV ----
    cand_csv = outdir / "corroboration_candidates.csv"
    with cand_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "score", "merge_adds_corroboration", "house", "geom_dist_m",
            "building_id_a", "families_a", "address_a",
            "building_id_b", "families_b", "address_b"])
        w.writeheader()
        for c in cands:
            w.writerow(c)

    # ---- markdown report ----
    md = outdir / "corroboration_report.md"
    total = len(props)
    lines = []
    A = lines.append
    A("# Cross-source corroboration report\n")
    A("_Generated by `scripts/33_corroboration_report.py` (read-only). "
      "No DB rows were modified._\n")
    A("## Method\n")
    A("Each property on the spine is tagged with the set of independent "
      "documentary **source families** that attest to it. A property clears the "
      "**legal-grade bar** (CLAUDE.md: ≥2 independent sources) when ≥2 "
      "distinct families co-occur on it. All families except one are "
      "occupation-internal or Russian-federal records — their evidentiary weight "
      "is as self-incriminating admissions, not neutral third-party "
      "verification. The exception, `independent_corroboration`, is a UN "
      "satellite-imagery damage assessment (Tier-3, "
      "docs/tier3_corroboration_design.md): genuinely neutral third-party "
      "verification, but it speaks only to physical war damage, not to the "
      "seizure act itself.\n")
    A(f"- Total properties on spine: **{total}**")
    A(f"- Properties meeting legal-grade (≥2 families): "
      f"**{len(legal)}**")
    A(f"- Court-record islands (court_case only, address-redacted, "
      f"**cannot** be address-corroborated): **{len(court_islands)}**")
    A(f"- Properties with no source family yet: **{len(zero)}**\n")

    A("## Source-family coverage (properties touched)\n")
    A("| family | properties |")
    A("|---|---|")
    for f in ALL_FAMILIES:
        A(f"| {f} | {fam_property_count.get(f, 0)} |")
    A("")

    A("## Corroboration strength (families per property)\n")
    A("| # independent families | properties |")
    A("|---|---|")
    for k in sorted(strength):
        A(f"| {k} | {strength[k]} |")
    A("")

    A("## Legal-grade family co-occurrence (which sources corroborate each other)\n")
    A("| family A | family B | properties |")
    A("|---|---|---|")
    for (fa, fb), n in pair_counts.most_common():
        A(f"| {fa} | {fb} | {n} |")
    A("")

    A("## The court-record island gap\n")
    A(f"{len(court_islands)} properties exist **only** as court cases. Their "
      "addresses are structurally redacted at source (`<адре"
      "с>` placeholder in every published ruling), and no non-court source "
      "references a court case number — so they cannot be matched to the "
      "address-bearing sources by address, cadastral, or geometry. They stand on "
      "the case record itself as primary evidence of the seizure act; "
      "cross-source corroboration is structurally unavailable for them via this "
      "portal. This is a hard limit of the source, not a coverage gap to close.\n")

    A("## Near-miss merge candidates (REVIEW ONLY — not applied)\n")
    adds = sum(1 for c in cands if c["merge_adds_corroboration"])
    A(f"{len(cands)} pairs of property rows share a house number and a "
      f"fuzzy-matching street stem (WRatio ≥ {NEARMISS_SCORE}) but did not "
      f"merge (normalization noise: garbage prefixes, OCR typos, comma "
      f"artefacts, STREET↔UNKNOWN class drift). Of these, **{adds}** would "
      f"unite distinct source families if merged (i.e. would create or "
      f"strengthen corroboration). Full list: `corroboration_candidates.csv`. "
      f"Per CLAUDE.md these are surfaced for human review, **not** auto-merged.\n")
    if cands:
        A("Top candidates that would add corroboration:\n")
        A("| score | dist (m) | A (families) | B (families) |")
        A("|---|---|---|---|")
        shown = 0
        for c in cands:
            if not c["merge_adds_corroboration"]:
                continue
            A(f"| {c['score']} | {c['geom_dist_m'] if c['geom_dist_m'] is not None else '—'} "
              f"| {c['building_id_a']} ({c['families_a']}) "
              f"| {c['building_id_b']} ({c['families_b']}) |")
            shown += 1
            if shown >= 25:
                break
        A("")

    md.write_text("\n".join(lines), encoding="utf-8")

    return {
        "total": total, "legal": len(legal), "islands": len(court_islands),
        "zero": len(zero), "candidates": len(cands), "cand_adds": adds,
        "md": md, "lg_csv": lg_csv, "cand_csv": cand_csv,
        "fam_property_count": fam_property_count, "strength": strength,
        "pair_counts": pair_counts,
    }


def main() -> None:
    con = _connect()
    cur = con.cursor()
    props = gather(cur)
    cur.close()
    con.close()

    cands = near_miss_candidates(props)
    outdir = config.PROJECT_ROOT / "data" / "reports"
    stats = write_outputs(props, cands, outdir)

    print(f"properties={stats['total']}  legal-grade(>=2 fam)={stats['legal']}  "
          f"court-islands={stats['islands']}  no-source={stats['zero']}")
    print(f"near-miss candidates={stats['candidates']} "
          f"({stats['cand_adds']} would add corroboration)")
    print("family coverage:", dict(stats["fam_property_count"]))
    print(f"wrote:\n  {stats['md']}\n  {stats['lg_csv']}\n  {stats['cand_csv']}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(message)s")
    main()
