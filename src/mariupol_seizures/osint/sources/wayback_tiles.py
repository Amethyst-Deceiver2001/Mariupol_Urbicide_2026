"""Source 13 — Esri World Imagery Wayback satellite-tile timeline for the
address footprint: intact -> damaged -> cleared -> rebuilt.

Generalizes scripts/57 (fixed AOIs) to any bundle point: same release
config, same tile math, same walk-releases-by-date-proximity with a
max-offset bound so an early date can't silently match a much-later
(already-cleared) release, same on-disk tile cache + .meta.json sidecars.
Mosaics are stitched per target date and registered in source_document.
"""
from __future__ import annotations

import datetime as _dt
import io
import json
import logging
import math
import time
from datetime import date as _date

import requests

from ... import config, forensics
from .base import SourceResult, http_headers

log = logging.getLogger(__name__)

NAME = "wayback_tiles"
RUN = "C"
NETWORK = True
DESCRIPTION = "Esri Wayback dated tile mosaics (prewar/post-siege/cleared/current)"

WAYBACK_CONFIG_URL = ("https://s3-us-west-2.amazonaws.com/"
                      "config.maptiles.arcgis.com/waybackconfig.json")
TILES_DIR = config.RAW_DIR / "wayback" / "tiles"
ZOOMS = [18, 17]
PAUSE = 0.25
PAD_DEG = 0.0006   # ≈ 55m half-width around the point

TARGET_DATES = [
    ("prewar", "2022-02-15", 45),
    ("post_siege", "2022-06-01", 45),
    ("cleared", "2023-06-15", 90),
    ("current", None, None),       # None -> today
]


def plan(bundle) -> str:
    return (f"tile grid ±{PAD_DEG*111000:.0f}m at z18→17, 4 target dates, "
            "mosaics into raw store")


def _releases() -> list[dict]:
    r = requests.get(WAYBACK_CONFIG_URL, headers=http_headers(), timeout=60)
    r.raise_for_status()
    rel = []
    for v in r.json().values():
        try:
            date_str = v["itemTitle"].split("(Wayback ")[1].rstrip(")")
        except (KeyError, IndexError):
            continue
        rel.append({"date": date_str, "tpl": v["itemURL"],
                    "item_id": v["itemID"], "title": v["itemTitle"]})
    rel.sort(key=lambda x: x["date"])
    return rel


def _deg2tile(lat: float, lon: float, z: int) -> tuple[float, float]:
    lr = math.radians(lat)
    n = 2 ** z
    return ((lon + 180.0) / 360.0 * n,
            (1.0 - math.log(math.tan(lr) + 1.0 / math.cos(lr)) / math.pi) / 2.0 * n)


def _grid(bundle, z: int) -> tuple[range, range]:
    x0, y0 = _deg2tile(bundle.lat + PAD_DEG, bundle.lon - PAD_DEG, z)
    x1, y1 = _deg2tile(bundle.lat - PAD_DEG, bundle.lon + PAD_DEG, z)
    return (range(int(x0), int(x1) + 1), range(int(y0), int(y1) + 1))


def _fetch_tile(rel: dict, z: int, x: int, y: int) -> bytes | None:
    path = TILES_DIR / rel["item_id"] / str(z) / str(y) / f"{x}.jpg"
    if path.exists():
        return path.read_bytes()
    url = rel["tpl"].format(level=z, row=y, col=x)
    try:
        r = requests.get(url, headers=http_headers(), timeout=30)
    except requests.RequestException:
        log.warning("tile fetch error %s", url, exc_info=True)
        return None
    if r.status_code == 404:
        return None
    r.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(r.content)
    meta = {"source_url": url, "sha256": forensics.sha256_bytes(r.content)
            if hasattr(forensics, "sha256_bytes") else "",
            "captured_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "release_date": rel["date"], "release_item_id": rel["item_id"],
            "kind": "wayback_tile", "z": z, "x": x, "y": y}
    (path.parent / f"{path.name}.meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    time.sleep(PAUSE)
    return r.content


def fetch(bundle, con, radius_m: float = 60.0) -> SourceResult:
    try:
        from PIL import Image
    except ImportError:
        return SourceResult(NAME, False,
                            "pillow not installed — pip install -e '.[imagery]'")
    try:
        releases = _releases()
    except requests.RequestException as e:
        return SourceResult(NAME, False, f"release config fetch failed: {e}")

    findings: list[dict] = []
    captured: list[str] = []
    today = _date.today().isoformat()

    for label, target, max_off in TARGET_DATES:
        target = target or today
        t = _date.fromisoformat(target)
        ordered = sorted(releases,
                         key=lambda r: abs((_date.fromisoformat(r["date"]) - t).days))
        done = False
        for z in ZOOMS:
            xs, ys = _grid(bundle, z)
            for rel in ordered:
                off = abs((_date.fromisoformat(rel["date"]) - t).days)
                if max_off is not None and off > max_off:
                    break   # ordered by proximity — everything after is worse
                tiles = {}
                ok = True
                for x in xs:
                    for y in ys:
                        data = _fetch_tile(rel, z, x, y)
                        if data is None:
                            ok = False
                            break
                        tiles[(x, y)] = data
                    if not ok:
                        break
                if not ok:
                    continue
                # stitch
                w, h = len(xs) * 256, len(ys) * 256
                mosaic = Image.new("RGB", (w, h))
                for (x, y), data in tiles.items():
                    mosaic.paste(Image.open(io.BytesIO(data)),
                                 ((x - xs[0]) * 256, (y - ys[0]) * 256))
                buf = io.BytesIO()
                mosaic.save(buf, "JPEG", quality=90)
                sha = forensics.capture_source(
                    buf.getvalue(),
                    url=f"wayback://mosaic/{bundle.slug}/{label}/{rel['item_id']}/z{z}",
                    source_type="osint_wayback_mosaic",
                    title=f"wayback {label} {rel['date']} {bundle.slug}",
                    description=(f"Esri Wayback mosaic, release {rel['title']} "
                                 f"({rel['date']}), z={z}, grid x{xs[0]}-{xs[-1]} "
                                 f"y{ys[0]}-{ys[-1]}, target={label}/{target}, "
                                 f"pid={bundle.pid}. Tiles cached under "
                                 f"data/raw/wayback/tiles/{rel['item_id']}/."),
                    content_type="image/jpeg", http_status=200, con=con,
                )
                captured.append(sha)
                findings.append({"kind": "wayback_mosaic", "label": label,
                                 "target_date": target, "release_date": rel["date"],
                                 "release_title": rel["title"], "zoom": z,
                                 "offset_days": off, "sha256": sha})
                done = True
                break
            if done:
                break
        if not done:
            findings.append({"kind": "wayback_gap", "label": label,
                             "target_date": target,
                             "note": f"no full-coverage release within ±{max_off}d "
                                     f"at z{ZOOMS}"})

    n_ok = sum(1 for f in findings if f["kind"] == "wayback_mosaic")
    return SourceResult(NAME, True,
                        f"{n_ok}/{len(TARGET_DATES)} target dates mosaicked",
                        findings, captured)
