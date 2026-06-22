#!/usr/bin/env python3
"""Fetch Sentinel-2 L2A scenes (visual/TCI) for each AOI x date-window in the
wave-1 satellite worklist (data/parsed/satellite_worklist.json, built by
script 54).

Source: Sentinel-2 L2A Cloud-Optimized GeoTIFFs via the AWS earth-search STAC
API (https://earth-search.aws.element84.com/v1/search), collection
"sentinel-2-l2a". This is a free, public, non-geoblocked Western data
service -- no VPS/proxy required, unlike the occupation court crawlers.

Selection rule (per AOI/window):
  - search the window's date range, sorted by datetime (desc for T0/T3 --
    "closest to invasion" / "most current"; asc for T1/T2 -- "closest to
    demolition from either side")
  - walk the sorted results and take the FIRST item whose eo:cloud_cover is
    below a progressively widened threshold (20 / 40 / 60 / 100%); record
    which threshold was actually needed (`achieved_cloud_threshold`) for
    "resolution/clarity honesty" in the review step (script 56)
  - if eo:cloud_cover is missing entirely, fall back to the first item in
    sort order and flag achieved_cloud_threshold=null

Forensic chain of custody (documented deviation from "capture full raw body"):
  - the STAC item itself (search-result JSON) is captured verbatim to
    data/raw/satellite/stac_items/<item_id>.json with a SHA-256 + .meta.json
    sidecar (source_url = the STAC search endpoint).
  - the imagery is NOT mirrored in full (each COG band is 100s of MB); instead
    we take a small windowed read of the public "visual" (TCI, true-colour
    uint8) asset for the AOI bbox, write that clip as its own GeoTIFF to
    data/raw/satellite/clips/, and record its SHA-256 + the exact replay
    parameters (asset href, AOI bbox in EPSG:4326, COG CRS, pixel window) in
    the .meta.json sidecar. Anyone can re-derive byte-identical pixels by
    reading that href with those parameters against Element84's immutable,
    versioned COG -- the STAC item id + asset href + window IS the chain of
    custody for the clip.

Output: data/parsed/satellite_manifest.json (one entry per AOI/window,
resumable -- re-running skips entries already present).
"""
import argparse
import hashlib
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import rasterio
import requests
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402

log = logging.getLogger("fetch_satellite_pairs")

STAC_URL = "https://earth-search.aws.element84.com/v1/search"
COLLECTION = "sentinel-2-l2a"
CLOUD_THRESHOLDS = [20, 40, 60, 100]
SEARCH_LIMIT = 100
REQUEST_PAUSE_S = 0.5

WORKLIST_PATH = config.DATA_DIR / "parsed" / "satellite_worklist.json"
MANIFEST_PATH = config.DATA_DIR / "parsed" / "satellite_manifest.json"
SAT_RAW_DIR = config.RAW_DIR / "satellite"
STAC_DIR = SAT_RAW_DIR / "stac_items"
CLIP_DIR = SAT_RAW_DIR / "clips"

# "closer to the boundary event" direction for sort order
SORT_DESC = {"T0": True, "T1": False, "T2": False, "T3": True}


def stac_search(bbox: list[float], date_from: str, date_to: str, desc: bool) -> list[dict]:
    payload = {
        "collections": [COLLECTION],
        "bbox": bbox,
        "datetime": f"{date_from}T00:00:00Z/{date_to}T23:59:59Z",
        "limit": SEARCH_LIMIT,
        "sortby": [{"field": "properties.datetime", "direction": "desc" if desc else "asc"}],
    }
    resp = requests.post(STAC_URL, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["features"]


def pick_item(features: list[dict]) -> tuple[dict | None, int | None]:
    """Walk `features` (already sorted) and return the first item meeting a
    progressively widened cloud-cover threshold, plus that threshold."""
    for max_cloud in CLOUD_THRESHOLDS:
        for feat in features:
            cc = feat["properties"].get("eo:cloud_cover")
            if cc is not None and cc < max_cloud:
                return feat, max_cloud
    if features:
        return features[0], None  # cloud_cover unknown for all candidates
    return None, None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_meta(path: Path, source_url: str, extra: dict | None = None) -> str:
    meta = {
        "source_url": source_url,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "sha256": sha256_file(path),
    }
    if extra:
        meta.update(extra)
    with open(f"{path}.meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return meta["sha256"]


def save_stac_item(item: dict) -> tuple[Path, str]:
    item_id = item["id"]
    path = STAC_DIR / f"{item_id}.json"
    if not path.exists():
        with open(path, "w", encoding="utf-8") as f:
            json.dump(item, f, ensure_ascii=False, indent=2)
        sha = write_meta(path, STAC_URL, extra={"item_id": item_id, "kind": "stac_item"})
    else:
        sha = sha256_file(path)
    return path, sha


def fetch_clip(item: dict, bbox_4326: list[float], out_path: Path) -> dict:
    """Windowed read of the item's `visual` (TCI) asset over `bbox_4326`,
    written to `out_path` as a small standalone GeoTIFF. Returns replay
    metadata for the .meta.json sidecar."""
    href = item["assets"]["visual"]["href"]
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
        with rasterio.open(href) as src:
            bounds_cog = transform_bounds("EPSG:4326", src.crs, *bbox_4326)
            window = from_bounds(*bounds_cog, transform=src.transform).round_offsets().round_lengths()
            data = src.read(window=window)
            win_transform = src.window_transform(window)
            profile = {
                "driver": "GTiff",
                "dtype": data.dtype,
                "count": data.shape[0],
                "height": data.shape[1],
                "width": data.shape[2],
                "crs": src.crs,
                "transform": win_transform,
            }
            with rasterio.open(out_path, "w", **profile) as dst:
                dst.write(data)
            return {
                "asset_href": href,
                "asset_crs": str(src.crs),
                "bbox_4326": bbox_4326,
                "bbox_asset_crs": list(bounds_cog),
                "pixel_window": {
                    "col_off": window.col_off,
                    "row_off": window.row_off,
                    "width": window.width,
                    "height": window.height,
                },
                "clip_shape": list(data.shape),
                "kind": "image_clip",
            }


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"generated_at": None, "entries": []}


def save_manifest(manifest: dict) -> None:
    manifest["generated_at"] = datetime.now(timezone.utc).isoformat()
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--aoi", help="only process this aoi_id")
    ap.add_argument("--window", help="only process this window label (T0/T1/T2/T3)")
    args = ap.parse_args()

    STAC_DIR.mkdir(parents=True, exist_ok=True)
    CLIP_DIR.mkdir(parents=True, exist_ok=True)

    with open(WORKLIST_PATH, encoding="utf-8") as f:
        worklist = json.load(f)

    manifest = load_manifest()
    done = {(e["aoi_id"], e["window_label"]) for e in manifest["entries"]}

    for aoi in worklist["aois"]:
        if args.aoi and aoi["aoi_id"] != args.aoi:
            continue
        bbox = [
            aoi["bbox"]["min_lon"],
            aoi["bbox"]["min_lat"],
            aoi["bbox"]["max_lon"],
            aoi["bbox"]["max_lat"],
        ]
        for window in aoi["windows"]:
            if args.window and window["label"] != args.window:
                continue
            key = (aoi["aoi_id"], window["label"])
            if key in done:
                log.info("skip %s/%s (already in manifest)", *key)
                continue

            desc = SORT_DESC[window["label"]]
            log.info(
                "%s/%s: searching %s..%s (sort %s)",
                aoi["aoi_id"], window["label"],
                window["date_from"], window["date_to"],
                "desc" if desc else "asc",
            )
            features = stac_search(bbox, window["date_from"], window["date_to"], desc)
            item, achieved_cloud = pick_item(features)
            time.sleep(REQUEST_PAUSE_S)

            entry = {
                "aoi_id": aoi["aoi_id"],
                "tier": aoi["tier"],
                "window_label": window["label"],
                "expected_state": window["expected_state"],
                "requested_date_from": window["date_from"],
                "requested_date_to": window["date_to"],
                "n_candidates": len(features),
            }

            if item is None:
                log.warning("%s/%s: NO SCENE FOUND (0 candidates)", *key)
                entry["status"] = "no_scene_found"
                manifest["entries"].append(entry)
                save_manifest(manifest)
                continue

            stac_path, stac_sha = save_stac_item(item)
            clip_name = f"{aoi['aoi_id']}__{window['label']}__{item['id']}.tif"
            clip_path = CLIP_DIR / clip_name
            try:
                replay = fetch_clip(item, bbox, clip_path)
            except Exception:
                log.exception("%s/%s: clip fetch failed for item %s", *key, item["id"])
                entry["status"] = "clip_fetch_failed"
                entry["item_id"] = item["id"]
                manifest["entries"].append(entry)
                save_manifest(manifest)
                continue
            clip_sha = write_meta(clip_path, replay["asset_href"], extra=replay)

            entry.update(
                {
                    "status": "ok",
                    "item_id": item["id"],
                    "item_datetime": item["properties"]["datetime"],
                    "eo_cloud_cover": item["properties"].get("eo:cloud_cover"),
                    "achieved_cloud_threshold": achieved_cloud,
                    "stac_item_path": str(stac_path.relative_to(config.PROJECT_ROOT)),
                    "stac_item_sha256": stac_sha,
                    "clip_path": str(clip_path.relative_to(config.PROJECT_ROOT)),
                    "clip_sha256": clip_sha,
                    "clip_shape": replay["clip_shape"],
                }
            )
            log.info(
                "%s/%s: %s (%s, cloud=%.1f%%, threshold<%s) -> %s",
                aoi["aoi_id"], window["label"], item["id"], item["properties"]["datetime"],
                item["properties"].get("eo:cloud_cover", -1), achieved_cloud, clip_name,
            )
            manifest["entries"].append(entry)
            save_manifest(manifest)
            time.sleep(REQUEST_PAUSE_S)

    n_ok = sum(1 for e in manifest["entries"] if e["status"] == "ok")
    n_missing = sum(1 for e in manifest["entries"] if e["status"] != "ok")
    log.info("Done. %d entries (%d ok, %d missing/failed) -> %s", len(manifest["entries"]), n_ok, n_missing, MANIFEST_PATH)


if __name__ == "__main__":
    main()
