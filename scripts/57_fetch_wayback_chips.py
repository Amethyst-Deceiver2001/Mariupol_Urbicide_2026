#!/usr/bin/env python3
"""Fetch high-resolution before/after imagery from Esri's "World Imagery
Wayback" archive for two small AOIs, as a sharper companion to the 10m
Sentinel-2 chips from scripts 54-56.

Source: https://www.arcgis.com/home/item.html?id=10df2279f9684e4a9f6a7f08febac2a9
("World Imagery Wayback") -- a free, public archive of ~194 dated releases
(2014-present) of Esri's World Imagery basemap, served as standard
{z}/{y}/{x} JPEG tiles from wayback.maptiles.arcgis.com. No API key, no VPS
(non-geoblocked AWS/Esri infrastructure). Each release's tile set only
contains tiles that changed vs. the previous release at a given zoom, so a
404 for an old release at high zoom typically means "no high-res tasking yet
for this area at that date" -- this script walks zoom levels (18 then 17)
and, for each target date, walks releases by date-proximity until it finds
one where ALL tiles covering the AOI return 200.

Two AOIs (siege ended ~2022-05-20; no kinetic damage to structures after
that date, so any 2022-06->2023+ change is administrative):
  - nakhimova_82_wayback: the documented demolish->rebuild flagship
    (see scripts/54-56, data/parsed/satellite_worklist.json), re-imaged here
    at ~0.8m/px for a direct sharper-vs-Sentinel comparison.
  - volgodonska_azovstalska_block: NEW -- a ~480x550m block of ~13 mid-rise
    apartment buildings on ul. Волгодонская / просп. Перемоги / бул. Меотиды
    (Орджоникидзевский / Left Bank district, near Azovstal), several with
    80-100% destruction in the federal damage tracker + displacement claims
    for dozens of households (corroboration table), but NO seizure_event
    (court) records yet. A single Wayback tile here showed a dramatic
    intact (2022-02) -> war-damaged (2022-06) -> cleared (2023-06) ->
    partially rebuilt (2026-05) sequence -- this is the AOI matching the
    project owner's "visually striking ... intact / heavily damaged /
    cleared lot" Google Earth example.

Date labels (4 per AOI, snapped to the nearest Wayback release with full
tile coverage at the chosen zoom):
  - prewar:     target 2022-02-15 (before the invasion)
  - post_siege: target 2022-06-01 (just after siege end, no new kinetic
                damage after this point -- any later change is
                administrative)
  - cleared:    target 2023-06-15
  - current:    target = latest available release

Forensic chain of custody: every tile is saved verbatim to
data/raw/wayback/tiles/<release_item_id>/<z>/<y>/<x>.jpg with a SHA-256 +
.meta.json sidecar (source_url = the tile URL, release date/itemID/
layerIdentifier/title + the World Imagery copyright/attribution string for
that release). Each mosaic is saved to data/raw/wayback/mosaics/ with its own
SHA-256 + .meta.json recording the release used, achieved zoom, tile grid
(x/y range), and per-tile SHA-256 list -- the release item URL template +
tile grid + this script IS the chain of custody (anyone can re-derive
byte-identical tiles from Esri's immutable per-release tile store).

Output: data/parsed/wayback_manifest.json (resumable -- re-running skips
AOI/date combos already present).
"""
import hashlib
import json
import logging
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
import requests
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402

log = logging.getLogger("fetch_wayback_chips")

WAYBACK_CONFIG_URL = "https://s3-us-west-2.amazonaws.com/config.maptiles.arcgis.com/waybackconfig.json"
TILE_SIZE = 256
ZOOM_CANDIDATES = [18, 17]  # try sharper (~0.4m/px) first, fall back to ~0.8m/px
REQUEST_PAUSE_S = 0.25

WAYBACK_RAW_DIR = config.RAW_DIR / "wayback"
TILES_DIR = WAYBACK_RAW_DIR / "tiles"
MOSAIC_DIR = WAYBACK_RAW_DIR / "mosaics"
MANIFEST_PATH = config.DATA_DIR / "parsed" / "wayback_manifest.json"

TARGET_DATES = [
    # (label, target_date, max_offset_days) -- max_offset_days bounds how far
    # a release's date may drift from the target before we give up on a zoom
    # level and fall back. Without this, a higher zoom that lacks 2022
    # coverage can "succeed" by matching prewar/post_siege to a much-later
    # (already-cleared) release, silently collapsing the before/after
    # narrative. None = unbounded (used only for "current").
    ("prewar", "2022-02-15", 45),
    ("post_siege", "2022-06-01", 45),
    ("cleared", "2023-06-15", 90),
    ("current", "2026-06-12", None),
]

AOI_DEFS = [
    {
        "aoi_id": "nakhimova_82_wayback",
        "title": "проспект Нахимова, 82 -> переулок Черноморский, 1Б "
                 "(re-imaged at ~0.8m/px for comparison with the Sentinel-2 chips)",
        "bbox": (37.5106, 47.0747, 37.5145, 47.0774),
        "member_property_ids": [5865, 6333],
    },
    {
        "aoi_id": "volgodonska_azovstalska_block",
        "title": "ул. Волгодонская / просп. Перемоги / бул. Меотиды block "
                 "(Левобережный/Орджоникидзевский, near Azovstal)",
        "bbox": (37.6305, 47.1028, 37.6368, 47.1078),
        "member_property_ids": [
            5456, 5457, 5459, 5460, 5461, 5462, 6172,
            5443, 5444, 5446, 5447, 5448, 5449,
        ],
    },
]


def fetch_property_info(cur, property_id: int) -> dict:
    cur.execute(
        """
        SELECT id, prewar_address, occupation_address, rd4u_category
        FROM property WHERE id = %s
        """,
        (property_id,),
    )
    row = cur.fetchone()
    if row is None:
        return {"property_id": property_id, "occupation_address": "?", "rd4u_category": None,
                "destruction_pct": None, "households_displaced": None, "n_seizure_events": 0}
    info = {
        "property_id": row[0],
        "prewar_address": row[1],
        "occupation_address": row[2],
        "rd4u_category": row[3],
    }
    cur.execute(
        """
        SELECT detail->>'destruction_pct', detail->>'households_displaced'
        FROM corroboration WHERE property_id = %s AND kind IN ('mirror_source', 'displacement_claim')
        """,
        (property_id,),
    )
    destruction_pct = None
    households_displaced = 0
    for pct, hh in cur.fetchall():
        if pct is not None:
            destruction_pct = float(pct)
        if hh is not None:
            households_displaced += int(hh)
    info["destruction_pct"] = destruction_pct
    info["households_displaced"] = households_displaced or None

    cur.execute("SELECT count(*) FROM seizure_event WHERE property_id = %s", (property_id,))
    info["n_seizure_events"] = cur.fetchone()[0]
    return info


def load_wayback_releases() -> list[dict]:
    resp = requests.get(WAYBACK_CONFIG_URL, timeout=60)
    resp.raise_for_status()
    cfg = resp.json()
    releases = []
    for v in cfg.values():
        date_str = v["itemTitle"].split("(Wayback ")[1].rstrip(")")
        releases.append(
            {
                "date": date_str,
                "item_url_template": v["itemURL"],
                "item_id": v["itemID"],
                "layer_identifier": v["layerIdentifier"],
                "title": v["itemTitle"],
                "metadata_layer_url": v["metadataLayerUrl"],
            }
        )
    releases.sort(key=lambda r: r["date"])
    return releases


def deg2tilef(lat: float, lon: float, zoom: int) -> tuple[float, float]:
    lat_r = math.radians(lat)
    n = 2 ** zoom
    x = (lon + 180.0) / 360.0 * n
    y = (1.0 - math.log(math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi) / 2.0 * n
    return x, y


def tile_range(bbox: tuple[float, float, float, float], zoom: int) -> tuple[int, int, int, int]:
    min_lon, min_lat, max_lon, max_lat = bbox
    x0, y0 = deg2tilef(max_lat, min_lon, zoom)  # top-left
    x1, y1 = deg2tilef(min_lat, max_lon, zoom)  # bottom-right
    return int(math.floor(x0)), int(math.floor(x1)), int(math.floor(y0)), int(math.floor(y1))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tile_path(release: dict, z: int, x: int, y: int) -> Path:
    return TILES_DIR / release["item_id"] / str(z) / str(y) / f"{x}.jpg"


def fetch_tile(release: dict, z: int, x: int, y: int) -> bytes | None:
    """Return tile bytes (cached on disk with .meta.json), or None on 404."""
    path = tile_path(release, z, x, y)
    if path.exists():
        return path.read_bytes()
    url = release["item_url_template"].format(level=z, row=y, col=x)
    for attempt in range(3):
        try:
            resp = requests.get(url, allow_redirects=True, timeout=30)
            break
        except requests.exceptions.RequestException:
            if attempt == 2:
                raise
            log.warning("transient error fetching %s (attempt %d/3), retrying", url, attempt + 1)
            time.sleep(2.0)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    data = resp.content
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    meta = {
        "source_url": url,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "sha256": sha256_bytes(data),
        "release_date": release["date"],
        "release_item_id": release["item_id"],
        "release_title": release["title"],
        "layer_identifier": release["layer_identifier"],
        "kind": "wayback_tile",
        "z": z, "x": x, "y": y,
    }
    with open(f"{path}.meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return data


def releases_by_proximity(releases: list[dict], target_date: str) -> list[dict]:
    from datetime import date as ddate

    t = ddate.fromisoformat(target_date)
    return sorted(releases, key=lambda r: abs((ddate.fromisoformat(r["date"]) - t).days))


def try_fetch_all_tiles(release: dict, zoom: int, x_range: tuple[int, int], y_range: tuple[int, int]) -> dict | None:
    """Attempt to fetch every tile in the grid for `release`/`zoom`. Return
    {(x,y): bytes} on full success, or None if any tile 404s (after caching
    whatever succeeded -- harmless, reused on retry)."""
    x_min, x_max = x_range
    y_min, y_max = y_range
    tiles = {}
    for x in range(x_min, x_max + 1):
        for y in range(y_min, y_max + 1):
            data = fetch_tile(release, zoom, x, y)
            time.sleep(REQUEST_PAUSE_S)
            if data is None:
                return None
            tiles[(x, y)] = data
    return tiles


def resolve_aoi(aoi: dict, releases: list[dict]) -> tuple[int, dict] | tuple[None, None]:
    """Find a single zoom level for which ALL 4 target dates have a release
    with full tile coverage; return (zoom, {label: (release, x_range, y_range, tiles)})."""
    for zoom in ZOOM_CANDIDATES:
        x_min, x_max, y_min, y_max = tile_range(aoi["bbox"], zoom)
        n_tiles = (x_max - x_min + 1) * (y_max - y_min + 1)
        log.info("%s: zoom=%d -> %d tile(s) (x %d..%d, y %d..%d)", aoi["aoi_id"], zoom, n_tiles, x_min, x_max, y_min, y_max)
        resolved = {}
        ok = True
        for label, target_date, max_offset_days in TARGET_DATES:
            found = None
            for release in releases_by_proximity(releases, target_date):
                offset_days = abs((datetime.fromisoformat(release["date"]) - datetime.fromisoformat(target_date)).days)
                if max_offset_days is not None and offset_days > max_offset_days:
                    break  # sorted by proximity -- nothing closer remains
                tiles = try_fetch_all_tiles(release, zoom, (x_min, x_max), (y_min, y_max))
                if tiles is not None:
                    found = (release, tiles)
                    break
            if found is None:
                log.info("%s: zoom=%d FAILED for date label '%s' (no release within tolerance has full coverage)", aoi["aoi_id"], zoom, label)
                ok = False
                break
            release, tiles = found
            resolved[label] = {
                "release": release,
                "x_range": (x_min, x_max),
                "y_range": (y_min, y_max),
                "tiles": tiles,
            }
            log.info(
                "%s/%s: zoom=%d -> release %s (target %s, offset %dd)",
                aoi["aoi_id"], label, zoom, release["date"], target_date,
                abs((datetime.fromisoformat(release["date"]) - datetime.fromisoformat(target_date)).days),
            )
        if ok:
            return zoom, resolved
    return None, None


def build_mosaic(tiles: dict[tuple[int, int], bytes], x_range: tuple[int, int], y_range: tuple[int, int]) -> Image.Image:
    x_min, x_max = x_range
    y_min, y_max = y_range
    width = (x_max - x_min + 1) * TILE_SIZE
    height = (y_max - y_min + 1) * TILE_SIZE
    canvas = Image.new("RGB", (width, height))
    for (x, y), data in tiles.items():
        from io import BytesIO

        tile_img = Image.open(BytesIO(data)).convert("RGB")
        canvas.paste(tile_img, ((x - x_min) * TILE_SIZE, (y - y_min) * TILE_SIZE))
    return canvas


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"generated_at": None, "aois": []}


def save_manifest(manifest: dict) -> None:
    manifest["generated_at"] = datetime.now(timezone.utc).isoformat()
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    TILES_DIR.mkdir(parents=True, exist_ok=True)
    MOSAIC_DIR.mkdir(parents=True, exist_ok=True)

    conn = psycopg2.connect(config.DATABASE_URL)
    cur = conn.cursor()

    log.info("Loading World Imagery Wayback release config...")
    releases = load_wayback_releases()
    log.info("Loaded %d releases (%s .. %s)", len(releases), releases[0]["date"], releases[-1]["date"])

    manifest = load_manifest()
    done_aois = {a["aoi_id"] for a in manifest["aois"]}

    for aoi in AOI_DEFS:
        if aoi["aoi_id"] in done_aois:
            log.info("skip %s (already in manifest)", aoi["aoi_id"])
            continue

        members = [fetch_property_info(cur, pid) for pid in aoi["member_property_ids"]]

        zoom, resolved = resolve_aoi(aoi, releases)
        if zoom is None:
            log.warning("%s: no zoom level had full coverage for all 4 target dates -- skipping", aoi["aoi_id"])
            continue

        entries = []
        for label, target_date, _max_offset_days in TARGET_DATES:
            r = resolved[label]
            release = r["release"]
            mosaic = build_mosaic(r["tiles"], r["x_range"], r["y_range"])
            mosaic_name = f"{aoi['aoi_id']}__{label}__{release['item_id']}.png"
            mosaic_path = MOSAIC_DIR / mosaic_name
            mosaic.save(mosaic_path)
            mosaic_bytes = mosaic_path.read_bytes()
            mosaic_sha = sha256_bytes(mosaic_bytes)

            meta = {
                "kind": "wayback_mosaic",
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "sha256": mosaic_sha,
                "aoi_id": aoi["aoi_id"],
                "label": label,
                "target_date": target_date,
                "zoom": zoom,
                "tile_size": TILE_SIZE,
                "x_range": list(r["x_range"]),
                "y_range": list(r["y_range"]),
                "bbox_4326": list(aoi["bbox"]),
                "release_date": release["date"],
                "release_item_id": release["item_id"],
                "release_title": release["title"],
                "layer_identifier": release["layer_identifier"],
                "item_url_template": release["item_url_template"],
                "attribution": "Source: Esri, Maxar, Earthstar Geographics and the GIS User "
                                "Community (per-release World Imagery Wayback metadata at "
                                f"{release['metadata_layer_url']})",
                "tile_sha256": {
                    f"{x},{y}": sha256_bytes(data) for (x, y), data in r["tiles"].items()
                },
            }
            with open(f"{mosaic_path}.meta.json", "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)

            entries.append(
                {
                    "label": label,
                    "target_date": target_date,
                    "release_date": release["date"],
                    "release_item_id": release["item_id"],
                    "release_title": release["title"],
                    "zoom": zoom,
                    "mosaic_path": str(mosaic_path.relative_to(config.PROJECT_ROOT)),
                    "mosaic_sha256": mosaic_sha,
                    "mosaic_size": list(mosaic.size),
                    "n_tiles": len(r["tiles"]),
                }
            )
            log.info(
                "%s/%s: mosaic %s (%dx%d, %d tiles, release %s)",
                aoi["aoi_id"], label, mosaic_name, *mosaic.size, len(r["tiles"]), release["date"],
            )

        manifest["aois"].append(
            {
                "aoi_id": aoi["aoi_id"],
                "title": aoi["title"],
                "bbox": list(aoi["bbox"]),
                "zoom": zoom,
                "members": members,
                "entries": entries,
            }
        )
        save_manifest(manifest)

    cur.close()
    conn.close()
    log.info("Done -> %s", MANIFEST_PATH)


if __name__ == "__main__":
    main()
