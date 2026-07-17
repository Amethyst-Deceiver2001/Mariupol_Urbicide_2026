"""Source — Planet Labs PlanetScope/SkySat scene-date metadata (search-only trial).

Planet's Data API quick-search is free and returns near-daily PlanetScope
(~3m) + occasional SkySat (sub-meter) scene metadata for any AOI, going back
to well before the invasion. A search-only trial (no Orders API / asset
entitlements / tile access — confirmed empirically 2026-07-16:
quick-search works; every asset/order path returns empty/403;
`my/subscriptions` is `[]`; the per-item XYZ tile endpoint
(tiles.planet.com/.../{z}/{x}/{y}.png) returns "No Permission") means the
per-scene "thumbnail" (tiles.planet.com/.../items/{id}/thumb) is the only
imagery byte this account can pull — and it renders the ENTIRE scene
footprint (PlanetScope scenes are ~24x8km+) at a fixed 256px, not a crop
around the AOI. At that scale a single building is far below one pixel;
verified visually against pid 4837 that the "thumbnail" shows farmland
outside the city, not the address. Treat the thumbnail purely as a
provenance/curiosity artifact, NOT as visual before/after evidence.

What this source is actually good for: confirming a scene EXISTS on a given
date with a given cloud-cover value near the address (i.e. imagery of the
area was captured on date X) — a date-corroboration signal, not a visual
one. If/when the account is upgraded to a paying tier with Orders/clip/tile
access, the thumbnail capture code here should be swapped for ordered,
AOI-clipped assets to get genuine visual before/after confirmation.

Builds a small buffer AOI (radius_m) around the pid's point, searches
several explicit yearly windows (quick-search returns newest-first, capped
at one page — narrow windows beat paging through hundreds of recent
scenes to reach 2022) and captures each window's earliest/latest low-cloud
scene's metadata + whole-scene thumbnail. Uses config.PLANET_API_KEY.
Skips with a note if no key.
"""
from __future__ import annotations

import logging
import math
import time

import requests

from ... import config, forensics
from .base import SourceResult, http_headers

log = logging.getLogger(__name__)

NAME = "planet_imagery"
RUN = "U"
NETWORK = True
DESCRIPTION = ("Planet Labs PlanetScope/SkySat scene-date metadata — $ key, search-only trial ok. "
              "Thumbnail = whole-scene 256px, NOT address-cropped; date-corroboration signal only.")

QUICK_SEARCH = "https://api.planet.com/data/v1/quick-search"
THUMB_TMPL = "https://tiles.planet.com/data/v1/item-types/{item_type}/items/{item_id}/thumb"
ITEM_TYPES = ["PSScene", "SkySatCollect"]
MAX_CLOUD_COVER = 0.2
DATE_START = "2022-04-01T00:00:00Z"  # Mariupol fell mid-May 2022
# quick-search returns newest-first, capped at one 250-item page per call
# (no pagination here — free, so multiple narrow-window calls beat paging
# through hundreds of recent results to reach 2022). Each window contributes
# its own earliest/latest low-cloud pick, giving a real before/mid/after
# spread instead of everything clustering in the most recent months.
WINDOWS = [
    ("2022-04-01T00:00:00Z", "2022-12-31T23:59:59Z"),  # siege-era baseline
    ("2023-01-01T00:00:00Z", "2023-12-31T23:59:59Z"),  # clearance/rebuild check
    ("2024-01-01T00:00:00Z", "2024-12-31T23:59:59Z"),
    ("2025-01-01T00:00:00Z", None),                     # current (None = now)
]
MAX_THUMBS_PER_WINDOW = 2
PAUSE = 0.5


def plan(bundle) -> str:
    if not config.PLANET_API_KEY:
        return "SKIP — no PLANET_API_KEY in .env"
    return (f"quick-search {ITEM_TYPES} over radius_m buffer AOI across "
            f"{len(WINDOWS)} date windows ({WINDOWS[0][0][:10]}..today), "
            f"capture search JSON + up to {MAX_THUMBS_PER_WINDOW} thumbnails "
            f"per window (earliest/latest low-cloud picks)")


def _aoi(lat: float, lon: float, radius_m: float) -> dict:
    lat_pad = radius_m / 111_320.0
    lon_pad = radius_m / (111_320.0 * math.cos(math.radians(lat)))
    coords = [
        [lon - lon_pad, lat - lat_pad], [lon + lon_pad, lat - lat_pad],
        [lon + lon_pad, lat + lat_pad], [lon - lon_pad, lat + lat_pad],
        [lon - lon_pad, lat - lat_pad],
    ]
    return {"type": "Polygon", "coordinates": [coords]}


def fetch(bundle, con, radius_m: float = 150.0) -> SourceResult:
    if not config.PLANET_API_KEY:
        return SourceResult(NAME, True, "skipped — no PLANET_API_KEY set "
                                        "(trial: planet.com/account)")
    findings: list[dict] = []
    captured: list[str] = []
    auth = (config.PLANET_API_KEY, "")
    aoi = _aoi(bundle.lat, bundle.lon, radius_m)

    all_picks: list[dict] = []
    total_scenes = 0
    for gte, lte in WINDOWS:
        date_cfg = {"gte": gte}
        if lte:
            date_cfg["lte"] = lte
        body = {
            "item_types": ITEM_TYPES,
            "filter": {
                "type": "AndFilter",
                "config": [
                    {"type": "DateRangeFilter", "field_name": "acquired", "config": date_cfg},
                    {"type": "GeometryFilter", "field_name": "geometry",
                     "relation": "intersects", "config": aoi},
                    {"type": "RangeFilter", "field_name": "cloud_cover",
                     "config": {"lte": MAX_CLOUD_COVER}},
                ],
            },
        }
        try:
            r = requests.post(QUICK_SEARCH, json=body, auth=auth,
                               headers=http_headers(), timeout=40)
            r.raise_for_status()
        except requests.RequestException as e:
            findings.append({"kind": "error", "window": f"{gte[:10]}..{(lte or 'now')[:10]}",
                             "error": str(e)})
            continue

        captured.append(forensics.capture_source(
            r.content, url=f"{QUICK_SEARCH}?window={gte[:10]}..{(lte or 'now')[:10]}",
            source_type="osint_planet_search",
            title=f"Planet quick-search {bundle.slug} {gte[:10]}..{(lte or 'now')[:10]}",
            description=(f"Planet Data API quick-search, {ITEM_TYPES}, window "
                         f"{gte[:10]}..{(lte or 'now')[:10]}, cloud<={MAX_CLOUD_COVER}, "
                         f"pid={bundle.pid}, radius={radius_m}m."),
            content_type="application/json", http_status=r.status_code, con=con,
        ))

        feats = sorted(r.json().get("features", []),
                        key=lambda f: f.get("properties", {}).get("acquired", ""))
        total_scenes += len(feats)
        if not feats:
            continue
        window_picks = [feats[0]]
        if len(feats) > 1 and feats[-1]["id"] != feats[0]["id"]:
            window_picks.append(feats[-1])
        all_picks.extend(window_picks[:MAX_THUMBS_PER_WINDOW])

    findings.append({"kind": "planet_search_summary", "n_scenes": total_scenes,
                     "n_windows": len(WINDOWS)})
    if not all_picks:
        return SourceResult(NAME, True, "0 scenes found across all windows (this trial is "
                                        "search-only; no asset/order access — see module docstring)",
                            findings, captured)

    for f in all_picks:
        item_id = f["id"]
        item_type = f.get("properties", {}).get("item_type", "PSScene")
        acquired = f.get("properties", {}).get("acquired", "")[:10]
        cloud = f.get("properties", {}).get("cloud_cover")
        thumb_url = THUMB_TMPL.format(item_type=item_type, item_id=item_id)
        rec = {
            "kind": "planet_scene", "item_id": item_id, "item_type": item_type,
            "acquired": acquired, "cloud_cover": cloud,
            "url": f"https://www.planet.com/explorer/?item={item_id}",
        }
        try:
            ir = requests.get(thumb_url, auth=auth, headers=http_headers(), timeout=60)
            if ir.status_code == 200 and ir.content:
                sha = forensics.capture_source(
                    ir.content, url=thumb_url,
                    source_type="osint_planet_thumbnail",
                    title=f"Planet {item_type} {item_id} {acquired}",
                    description=(f"Planet {item_type} scene {item_id} EXISTS, acquired "
                                 f"{acquired}, cloud_cover={cloud}, covering the area "
                                 f"near pid={bundle.pid} — a date-corroboration signal "
                                 f"only. The attached thumbnail is a 256px render of "
                                 f"the ENTIRE scene footprint (~24x8km+), NOT cropped "
                                 f"to the address; this trial account has no "
                                 f"Orders/clip/tile access (all confirmed 403/'No "
                                 f"Permission' 2026-07-16), so no address-level visual "
                                 f"is obtainable from Planet on this account. "
                                 f"{rec['url']}"),
                    content_type=ir.headers.get("Content-Type", "image/png"),
                    http_status=ir.status_code, con=con,
                )
                rec["sha256"] = sha
                captured.append(sha)
            else:
                rec["thumb_error"] = f"HTTP {ir.status_code}"
        except requests.RequestException as e:
            rec["thumb_error"] = str(e)
        findings.append(rec)
        time.sleep(PAUSE)

    n_thumbs = sum(1 for f in findings if f["kind"] == "planet_scene" and "sha256" in f)
    dates = sorted(f["properties"]["acquired"][:10] for f in all_picks)
    return SourceResult(NAME, True,
                        f"{total_scenes} scenes found across {len(WINDOWS)} windows, "
                        f"{n_thumbs} thumbnails captured ({dates[0]} to {dates[-1]})",
                        findings, captured)
