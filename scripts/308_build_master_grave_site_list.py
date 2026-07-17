#!/usr/bin/env python3
"""Reconcile the three grave-site/property overlap reports built this
session into one master list:

  - scripts/301 -- data/reports/grave_sites_property_overlap.csv
    (mariupoldestruction.com spreadsheet, scripts/300's extraction)
  - scripts/304 -- data/reports/mariupolrip_channel_grave_leads.csv
    (@mariupolRIP full channel scan)
  - scripts/307 -- data/reports/memorial_ua_property_overlap.csv
    (memorial.ua obituaries)

Dedup logic: the mariupolRIP channel scan's "known_cited" rows are, BY
DEFINITION, messages already used as the citation source for a spreadsheet
row -- including them here would double-count the same underlying event
against scripts/301's output. Only "new_informal"/"new_address_echo" channel
rows are included. This does not catch every possible duplicate (two
independent posts describing the same person would still both appear), but
it removes the one guaranteed, structural double-count.

Output:
  - data/reports/grave_sites_master_evidence.csv -- one row per evidence
    item (victim/message/obituary), tagged by source, property-joined.
  - data/reports/grave_sites_master_properties.csv -- one row per property,
    aggregated: evidence count, source count, seizure stages, victim names.

Read-only: three local CSV reads, two CSV writes. No network, no DB write.
"""
import csv
import logging
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
log = logging.getLogger(__name__)

REPORTS = ROOT / "data" / "reports"
SHEET_FILE = REPORTS / "grave_sites_property_overlap.csv"
CHANNEL_FILE = REPORTS / "mariupolrip_channel_grave_leads.csv"
MEMORIAL_FILE = REPORTS / "memorial_ua_property_overlap.csv"

OUT_EVIDENCE = REPORTS / "grave_sites_master_evidence.csv"
OUT_PROPERTIES = REPORTS / "grave_sites_master_properties.csv"

EVIDENCE_FIELDS = [
    "source", "property_id", "matched_building_id", "prewar_address",
    "occupation_address", "seizure_stages", "victim_name", "event_date",
    "evidence_url", "quote", "flags",
]


def load_sheet() -> list[dict]:
    rows = list(csv.DictReader(SHEET_FILE.open(encoding="utf-8")))
    out = []
    for r in rows:
        if not r["seizure_stages"]:
            continue
        out.append({
            "source": "mariupoldestruction_sheet",
            "property_id": r["property_id"],
            "matched_building_id": r["matched_building_id"],
            "prewar_address": r["prewar_address"],
            "occupation_address": r["occupation_address"],
            "seizure_stages": r["seizure_stages"],
            "victim_name": r["name"],
            "event_date": r["dod"],
            "evidence_url": "",
            "quote": r["burial_place"],
            "flags": r["flags"],
        })
    return out


def load_channel() -> list[dict]:
    rows = list(csv.DictReader(CHANNEL_FILE.open(encoding="utf-8")))
    out = []
    for r in rows:
        if not r["seizure_stages"]:
            continue
        if r["category"] == "known_cited":
            continue  # already represented by a mariupoldestruction_sheet row
        out.append({
            "source": "mariupolrip_channel",
            "property_id": r["property_id"],
            "matched_building_id": r["matched_building_id"],
            "prewar_address": r["prewar_address"],
            "occupation_address": r["occupation_address"],
            "seizure_stages": r["seizure_stages"],
            "victim_name": "",  # channel posts are free text, no parsed name
            "event_date": r["date"][:10] if r["date"] else "",
            "evidence_url": r["url"],
            "quote": r["text"][:200],
            "flags": r["category"] + (";unburied" if r["unburied"] == "True" else ""),
        })
    return out


def load_memorial() -> list[dict]:
    rows = list(csv.DictReader(MEMORIAL_FILE.open(encoding="utf-8")))
    out = []
    for r in rows:
        if not r["seizure_stages"]:
            continue
        out.append({
            "source": "memorial_ua",
            "property_id": r["property_id"],
            "matched_building_id": r["matched_building_id"],
            "prewar_address": r["prewar_address"],
            "occupation_address": r["occupation_address"],
            "seizure_stages": r["seizure_stages"],
            "victim_name": r["name"],
            "event_date": r["death_date"],
            "evidence_url": r["url"],
            "quote": r["story_excerpt"][:200],
            "flags": r["matched_keyword"],
        })
    return out


def main() -> None:
    evidence = load_sheet() + load_channel() + load_memorial()
    log.info("evidence rows: sheet=%d channel(new-only)=%d memorial=%d total=%d",
              len(load_sheet()), len(load_channel()), len(load_memorial()), len(evidence))

    OUT_EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    with OUT_EVIDENCE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=EVIDENCE_FIELDS)
        w.writeheader()
        w.writerows(evidence)

    by_prop = defaultdict(list)
    for e in evidence:
        by_prop[e["property_id"]].append(e)

    prop_rows = []
    for pid, items in by_prop.items():
        addr = items[0]["occupation_address"] or items[0]["prewar_address"]
        stages = sorted({s for it in items for s in it["seizure_stages"].split(";") if s})
        sources = sorted({it["source"] for it in items})
        names = sorted({it["victim_name"] for it in items if it["victim_name"]})
        prop_rows.append({
            "property_id": pid,
            "matched_building_id": items[0]["matched_building_id"],
            "address": addr,
            "seizure_stages": ";".join(stages),
            "evidence_count": len(items),
            "source_count": len(sources),
            "sources": ";".join(sources),
            "named_victims": "; ".join(names),
        })

    prop_rows.sort(key=lambda r: (-r["source_count"], -r["evidence_count"]))

    with OUT_PROPERTIES.open("w", encoding="utf-8", newline="") as f:
        fieldnames = ["property_id", "matched_building_id", "address", "seizure_stages",
                      "evidence_count", "source_count", "sources", "named_victims"]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(prop_rows)

    multi_source = sum(1 for r in prop_rows if r["source_count"] > 1)
    stage_totals = defaultdict(int)
    for r in prop_rows:
        for s in r["seizure_stages"].split(";"):
            if s:
                stage_totals[s] += 1

    log.info("=== SUMMARY ===")
    log.info("distinct properties (informal burial + seizure event): %d", len(prop_rows))
    log.info("properties corroborated by >1 independent source: %d", multi_source)
    for k, v in sorted(stage_totals.items(), key=lambda x: -x[1]):
        log.info("  %s: %d", k, v)
    log.info("written -> %s (%d rows)", OUT_EVIDENCE, len(evidence))
    log.info("written -> %s (%d rows)", OUT_PROPERTIES, len(prop_rows))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
