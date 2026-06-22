#!/usr/bin/env python3
"""Stage 4e (geocoding fallback): Tier B -- apply user-verified manual
geocode overrides to data/parsed/geocoded_buildings.jsonl.

Some addresses use informal Soviet-era microdistrict numbering (e.g. "27
квартал, д.4А") that free/global geocoders (Nominatim, Overpass/OSM tags,
Google) only resolve to the neighbourhood/quarter level, not the building.
Yandex Maps has denser coverage for these in DNR-administered Mariupol; the
user looks up the building manually and reports back lat/lon, which is
recorded in data/parsed/manual_geocode_overrides.jsonl (one JSON object per
line: building_key, lat, lon, geocode_confidence, geocode_source, note,
verified_at).

A row is only overwritten if the override's confidence is STRICTLY HIGHER
than its current value (never downgrades); previous_geocode is preserved on
any row this script upgrades.

geocode_source="yandex_maps_manual" tags these rows so they can be filtered,
reviewed, or independently re-verified separately before any public RD4U/
court submission -- there is no API response to capture/hash here, only the
user's verified lat/lon and the date of verification.

Run locally, no network: python3 scripts/25_apply_manual_geocode_overrides.py
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402

log = logging.getLogger(__name__)

PARSED_DIR = config.PROJECT_ROOT / "data" / "parsed"


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")

    geo_path = PARSED_DIR / "geocoded_buildings.jsonl"
    overrides_path = PARSED_DIR / "manual_geocode_overrides.jsonl"
    if not geo_path.exists() or not overrides_path.exists():
        log.error("missing inputs -- run scripts/21-24 first")
        sys.exit(1)

    geocoded = _read_jsonl(geo_path)
    overrides = {o["building_key"]: o for o in _read_jsonl(overrides_path)}

    n_upgraded = 0
    n_unknown_key = 0
    seen_keys: set[str] = set()
    results: list[dict] = []
    for row in geocoded:
        override = overrides.get(row["building_key"])
        if not override:
            results.append(row)
            continue
        seen_keys.add(row["building_key"])
        if override["geocode_confidence"] <= row["geocode_confidence"]:
            results.append(row)
            continue
        new_row = dict(row)
        new_row["previous_geocode"] = {
            "lat": row.get("lat"), "lon": row.get("lon"),
            "geocode_confidence": row["geocode_confidence"],
            "geocode_source": row.get("geocode_source"),
        }
        new_row["lat"] = override["lat"]
        new_row["lon"] = override["lon"]
        new_row["geocode_confidence"] = override["geocode_confidence"]
        new_row["geocode_source"] = override["geocode_source"]
        new_row["manual_override_note"] = override.get("note")
        new_row["manual_override_verified_at"] = override.get("verified_at")
        results.append(new_row)
        n_upgraded += 1

    for key in overrides:
        if key not in seen_keys:
            n_unknown_key += 1
            log.warning("override building_key not found in geocoded_buildings.jsonl: %s", key)

    with geo_path.open("w", encoding="utf-8") as fh:
        for r in results:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    log.info("Applied %d/%d manual overrides (%d unknown building_key)",
             n_upgraded, len(overrides), n_unknown_key)
    by_conf: dict[float, int] = {}
    for r in results:
        by_conf[r["geocode_confidence"]] = by_conf.get(r["geocode_confidence"], 0) + 1
    for conf, n in sorted(by_conf.items(), reverse=True):
        log.info("  confidence %.1f: %d", conf, n)


if __name__ == "__main__":
    main()
