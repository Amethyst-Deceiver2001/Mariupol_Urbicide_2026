#!/usr/bin/env python3
"""Export remaining 0.5-confidence geocodes for manual map review.

geocode_confidence == 0.5 means Nominatim/Google matched only the street
(matched_house_number=False) -- the lat/lon is a street- or district-level
fallback, not the actual building. This is the queue the user works through
by cross-checking each entry against Google/Yandex Maps, Street View,
Wikimapia and visicom.ua cadastral footprints, then adding a corrected entry
to data/parsed/manual_geocode_overrides.jsonl (applied via
scripts/69_apply_geocode_overrides.py).

Excludes any building_key already resolved in manual_geocode_overrides.jsonl.
Joins address_registry.jsonl for occupation_address / prewar_name /
district_key / n_sources (review priority signal -- more source references
means a stronger corroboration trail once the location is fixed).

Output: data/exports/low_confidence_review.csv (loadable in QGIS via
"Add Delimited Text Layer", X field=lon, Y field=lat).
"""
import csv
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mariupol_seizures import config  # noqa: E402

log = logging.getLogger("export_low_confidence_review")

PARSED_DIR = config.PROJECT_ROOT / "data" / "parsed"
OUT_PATH = config.PROJECT_ROOT / "data" / "exports" / "low_confidence_review.csv"


def main() -> None:
    overrides = set()
    overrides_path = PARSED_DIR / "manual_geocode_overrides.jsonl"
    with overrides_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            overrides.add(json.loads(line)["building_key"])

    registry = {}
    with (PARSED_DIR / "address_registry.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            registry[d["building_key"]] = d

    rows = []
    with (PARSED_DIR / "geocoded_buildings.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            if d.get("geocode_confidence") != 0.5:
                continue
            bk = d["building_key"]
            if bk in overrides:
                continue

            reg = registry.get(bk, {})
            n_sources = reg.get("n_sources", 0)
            source_refs = "+".join(sorted(reg.get("source_refs", {}).keys()))

            rows.append({
                "building_key": bk,
                "street_occupation": reg.get("street_occupation", ""),
                "house_no": reg.get("house_no", ""),
                "prewar_name": reg.get("prewar_name") or "",
                "district_key": reg.get("district_key") or "",
                "lat": d["lat"],
                "lon": d["lon"],
                "geocode_source": d.get("geocode_source", ""),
                "query_used": d.get("query_used", ""),
                "n_sources": n_sources,
                "source_refs": source_refs,
            })

    rows.sort(key=lambda r: (r["street_occupation"], r["house_no"]))

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        writer.writerows(rows)

    log.info("wrote %s (%d rows, %d resolved by manual_geocode_overrides.jsonl excluded)",
             OUT_PATH, len(rows), len(overrides))
    print(f"wrote {OUT_PATH} ({len(rows)} rows)")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    main()
