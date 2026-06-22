#!/usr/bin/env python3
"""Fetch UNOSAT building-damage assessment datasets for Mariupol from HDX.

Tier-3 corroboration layer, sub-layer S1 (docs/tier3_corroboration_design.md
section 3). Downloads the three UNOSAT/HDX releases covering Mariupol --
shapefile + geodatabase zips, all CC-BY-(SA|IGO), hosted at
unosat-maps.web.cern.ch (CERN, non-geoblocked, no VPS needed). Every zip is
captured verbatim via forensics.capture_source() (SHA-256 + .meta.json into
data/raw/, logged to data/state.sqlite's source_document table).

Resource URLs + sizes verified live against the HDX CKAN API
(https://data.humdata.org/api/3/action/package_show?id=<dataset>) on
2026-06-13:

  - mariupol-updated-building-damage-assessment-overview-map-livoberezhnyi-and-zhovtnevyi-dist
    (12 May 2022 imagery -- the headline citywide building-level dataset,
    5,647 damaged structures: 315 destroyed / 2,132 severe / 3,002 moderate /
    194 possible)
  - unosat-damage-assessment-overview-map-livoberezhnyi-district-mariupol-city-ukraine
    (14 March 2022 imagery -- 773/17,594 structures damaged, incl. 8 schools
    / 4 health facilities)
  - mariupol-rapid-damage-assessment-overview-map
    (26 March 2022 imagery -- 500m x 500m Rapid Damage Building Assessment
    grid over the Mariupolska Hromada, 556/3,456 cells damaged)

Output:
  - data/raw/<sha256>.zip + .meta.json for each resource (forensic store)
  - data/parsed/unosat_manifest.json -- maps each resource to its sha256/
    raw_path + the dataset-level HDX/UNOSAT provenance (license, UNOSAT code,
    imagery dates, summary). Consumed by scripts/53_load_unosat_damage.py.

Idempotent / resumable: re-running skips any resource already present (by
URL) in the manifest with a raw file that still exists on disk.
"""
import json
import logging
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger("fetch_unosat_damage")

MANIFEST_PATH = config.DATA_DIR / "parsed" / "unosat_manifest.json"
REQUEST_PAUSE_S = 1.0

DATASETS = [
    {
        "hdx_dataset": "mariupol-updated-building-damage-assessment-overview-map-livoberezhnyi-and-zhovtnevyi-dist",
        "hdx_url": "https://data.humdata.org/dataset/mariupol-updated-building-damage-assessment-overview-map-livoberezhnyi-and-zhovtnevyi-dist",
        "unosat_code": "CE20220223UKR",
        "title": "Mariupol Updated Building Damage Assessment Overview Map - "
                  "Livoberezhnyi and Zhovtnevyi Districts",
        "license": "cc-by-sa (Creative Commons Attribution Share-Alike)",
        "imagery_dates": ["2021-06-21", "2022-03-14", "2022-05-07", "2022-05-08", "2022-05-12"],
        "summary": "Headline citywide building-level damage assessment. "
                    "5,647 structures (~32% of the AOI) sustained visible "
                    "damage as of 7/8/12 May 2022: 315 destroyed, 2,132 "
                    "severely damaged, 3,002 moderately damaged, 194 "
                    "possibly damaged.",
        "resources": [
            {
                "name": "UNOSAT_LivoberezhnyiDistrict_DamageAssessment_12May2022_shp.zip",
                "format": "SHP", "role": "primary",
                "url": "https://unosat-maps.web.cern.ch/UA/CE20220223UKR/"
                       "UNOSAT_LivoberezhnyiDistrict_DamageAssessment_12May2022_shp.zip",
                "size": 253287,
            },
            {
                "name": "UNOSAT_LivoberezhnyiDistrict_DamageAssessment_12May2022.gdb.zip",
                "format": "Geodatabase", "role": "reference",
                "url": "https://unosat-maps.web.cern.ch/UA/CE20220223UKR/"
                       "UNOSAT_LivoberezhnyiDistrict_DamageAssessment_12May2022.gdb.zip",
                "size": 419252,
            },
        ],
    },
    {
        "hdx_dataset": "unosat-damage-assessment-overview-map-livoberezhnyi-district-mariupol-city-ukraine",
        "hdx_url": "https://data.humdata.org/dataset/unosat-damage-assessment-overview-map-livoberezhnyi-district-mariupol-city-ukraine",
        "unosat_code": "CE20220223UKR",
        "title": "UNOSAT Damage Assessment Overview Map - Livoberezhnyi and "
                 "Zhovtnevyi Districts, Mariupol City, Ukraine",
        "license": "cc-by-igo (Creative Commons Attribution for Intergovernmental Organisations)",
        "imagery_dates": ["2021-06-21", "2022-03-14"],
        "summary": "Earlier (pre-May) building-level damage assessment. "
                    "773/17,594 structures (~4%) sustained visible damage as "
                    "of 14 March 2022: 62 destroyed, 315 severely damaged, "
                    "321 moderately damaged, 75 possibly damaged. Includes 8 "
                    "schools and 4 health facilities.",
        "resources": [
            {
                "name": "CE20220223UKR_UNOSAT_Damage_shp.zip",
                "format": "SHP", "role": "primary",
                "url": "https://unosat-maps.web.cern.ch/UA/CE20220223UKR/"
                       "CE20220223UKR_UNOSAT_Damage_shp.zip",
                "size": 172171,
            },
            {
                "name": "CE20220223UKR_UNOSAT_Damage_gdb.zip",
                "format": "Geodatabase", "role": "reference",
                "url": "https://unosat-maps.web.cern.ch/UA/CE20220223UKR/"
                       "CE20220223UKR_UNOSAT_Damage_gdb.zip",
                "size": 1910130,
            },
        ],
    },
    {
        "hdx_dataset": "mariupol-rapid-damage-assessment-overview-map",
        "hdx_url": "https://data.humdata.org/dataset/mariupol-rapid-damage-assessment-overview-map",
        "unosat_code": "CE20220223UKR",
        "title": "Mariupol Rapid Damage Assessment Overview Map",
        "license": "cc-by-sa (Creative Commons Attribution Share-Alike)",
        "imagery_dates": ["2022-03-26"],
        "summary": "Citywide Rapid Damage Building Assessment (RDBA): 500m x "
                    "500m grid over the Mariupolska Hromada. 556/3,456 cells "
                    "(~16%) sustained visible damage as of 26 March 2022. "
                    "Coarse triage grid, not building-level -- lower "
                    "priority for the property-level spatial join than the "
                    "12 May 2022 dataset above.",
        "resources": [
            {
                "name": "UNOSAT_Mariupol_26March2022_RDA_shp.zip",
                "format": "SHP", "role": "primary",
                "url": "https://unosat-maps.web.cern.ch/UA/CE20220223UKR/"
                       "UNOSAT_Mariupol_26March2022_RDA_shp.zip",
                "size": 93692,
            },
            {
                "name": "CE20220223UKR_UNOSAT_Damage_gdb.zip",
                "format": "Geodatabase", "role": "reference",
                "url": "https://unosat-maps.web.cern.ch/UA/CE20220223UKR/"
                       "CE20220223UKR_UNOSAT_Damage_gdb.zip",
                "size": 1910130,
            },
        ],
    },
]


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"generated_at": None, "datasets": []}


def save_manifest(manifest: dict) -> None:
    from datetime import datetime, timezone

    manifest["generated_at"] = datetime.now(timezone.utc).isoformat()
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def already_fetched(manifest: dict, url: str) -> dict | None:
    for ds in manifest["datasets"]:
        for res in ds["resources"]:
            if res["url"] == url and res.get("raw_path") and Path(res["raw_path"]).exists():
                return res
    return None


def fetch_resource(url: str, expected_size: int) -> tuple[bytes, str, int]:
    """Return (content, content_type, http_status). Retries transient errors."""
    for attempt in range(config.MAX_RETRIES):
        try:
            resp = requests.get(
                url,
                headers={"User-Agent": config.USER_AGENT},
                timeout=config.TIMEOUT,
                allow_redirects=True,
            )
            resp.raise_for_status()
            content = resp.content
            if expected_size and len(content) != expected_size:
                log.warning(
                    "size mismatch for %s: expected %d, got %d (HDX resource may have "
                    "been updated -- continuing with the bytes actually received)",
                    url, expected_size, len(content),
                )
            return content, resp.headers.get("Content-Type", "application/zip"), resp.status_code
        except requests.exceptions.RequestException as exc:
            if attempt == config.MAX_RETRIES - 1:
                raise
            log.warning("transient error fetching %s (attempt %d/%d): %s -- retrying",
                         url, attempt + 1, config.MAX_RETRIES, exc)
            time.sleep(2.0 * (attempt + 1))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")

    state = forensics.open_state()
    manifest = load_manifest()

    for ds in DATASETS:
        log.info("Dataset: %s (%s)", ds["title"], ds["unosat_code"])
        for res in ds["resources"]:
            cached = already_fetched(manifest, res["url"])
            if cached:
                log.info("  skip %s (already captured -> %s)", res["name"], cached["raw_path"])
                res.update(cached)
                continue

            log.info("  fetching %s (%s, ~%d bytes) <- %s", res["name"], res["format"],
                     res["size"], res["url"])
            content, content_type, http_status = fetch_resource(res["url"], res["size"])

            description = (
                f"{ds['title']} -- {res['name']} ({res['format']}, "
                f"{len(content)} bytes). UNOSAT code {ds['unosat_code']}. "
                f"License: {ds['license']}. HDX dataset: {ds['hdx_url']}. "
                f"{ds['summary']}"
            )
            sha = forensics.capture_source(
                content,
                url=res["url"],
                source_type=f"unosat_damage_{res['format'].lower()}",
                title=f"{ds['title']} -- {res['name']}",
                description=description,
                content_type=content_type,
                http_status=http_status,
                con=state,
            )
            raw_path = str((config.RAW_DIR / f"{sha}.zip").relative_to(config.PROJECT_ROOT))
            res["sha256"] = sha
            res["raw_path"] = raw_path
            res["captured_size"] = len(content)
            log.info("  captured -> %s (sha256=%s)", raw_path, sha)
            time.sleep(REQUEST_PAUSE_S)

        # Rebuild the dataset entry in the manifest (idempotent on dataset id).
        manifest["datasets"] = [d for d in manifest["datasets"] if d["hdx_dataset"] != ds["hdx_dataset"]]
        manifest["datasets"].append(ds)
        save_manifest(manifest)

    state.close()
    log.info("Done -> %s", MANIFEST_PATH)


if __name__ == "__main__":
    main()
