"""Source — Microsoft Planetary Computer: Sentinel-2 AOI-cropped imagery.

Free, keyless STAC catalog (planetarycomputer.microsoft.com/api/stac/v1) —
no account/quota needed, unlike Planet's trial. Solves exactly the problem
that killed planet_imagery.py's visual usefulness: Planet's thumbnail
endpoint only renders the WHOLE scene footprint (confirmed empirically
2026-07-16, ~24x8km at 256px — useless below city scale), and its
Orders/clip/tile endpoints all require paid entitlements this account
doesn't have. Planetary Computer's Data API instead exposes a genuine
crop endpoint (POST an unwrapped GeoJSON Feature geometry to
`/item/crop/{width}x{height}.{format}`, collection/item/assets as query
params — confirmed by reading the deployed openapi.json directly, since
the docs site is a JS SPA and plausible-looking summaries of it suggested
a `/item/crop/{minx},{miny},{maxx},{maxy}.png` path-bbox form that 404s)
that server-side crops+renders true-color imagery to an arbitrary AOI,
publicly, with no signing/auth — real address-level visual evidence.

Verified live against pid 4837 (улица Зелинского, 17а), which already has
a documented demolition (seizure_event 2022-09-29) and rebuild crosswalk
(ЕИСЖС object 66986, ЖК «Нахимовский», СМУ-5) on the spine: the 4-window
crop sequence is visually consistent with that timeline — scattered
built structure in the 2022-07-07 (pre-demolition) crop, a distinct bright
bare-ground/rubble patch appearing by 2023-08-06 (post the Wayback
"cleared" tag) and persisting through 2024-09-29, then additional built
structure by 2026-05-22 consistent with the rebuild. At 10m/pixel this is
a corroborating visual signal, not proof — same evidentiary weight class
as the existing Wayback-tile/UNOSAT layers, not a replacement for them.

Searches the same explicit yearly windows as planet_imagery.py (quick
STAC search returns matches unordered/paginated; narrow windows are simpler
than paging), picks each window's lowest-cloud scene, and captures both the
STAC item metadata and a crop.png clipped to the AOI buffer.

Follow-up not built here: Microsoft Building Footprints (ms-buildings
collection) is organized as quadkey-partitioned GeoParquet, not per-building
STAC items — querying it needs pyarrow/geopandas, not currently a project
dependency. Worth adding later as a separate footprint-diff source if the
demolish-rebuild modality needs footprint-level (not just visual) proof.
"""
from __future__ import annotations

import logging
import math
import time

import requests

from ... import forensics
from .base import SourceResult, http_headers

log = logging.getLogger(__name__)

NAME = "planetary_computer"
RUN = "C"
NETWORK = True
DESCRIPTION = "Microsoft Planetary Computer Sentinel-2 — free, keyless, real AOI-cropped imagery"

STAC_SEARCH = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
# Real contract confirmed empirically 2026-07-16 by reading the deployed
# openapi.json (NOT the docs site, which is a JS SPA WebFetch can't read,
# and NOT to be confused with the /item/crop/{minx},{miny},{maxx},{maxy}.png
# path-bbox form that plausible-looking docs summaries suggested — that
# 404s on this deployment). Actual: POST an UNWRAPPED GeoJSON Feature as
# the JSON body (not {"geojson": feature} despite the OpenAPI schema name
# suggesting a wrapper — FastAPI embeds single-body-param GeoJSON models
# unwrapped here), collection/item/assets as query params.
CROP_URL = "https://planetarycomputer.microsoft.com/api/data/v1/item/crop/512x512.png"
COLLECTION = "sentinel-2-l2a"
MAX_CLOUD_COVER = 20  # percent, PC's eo:cloud_cover is 0-100 not 0-1
WINDOWS = [
    ("2022-04-01", "2022-12-31"),
    ("2023-01-01", "2023-12-31"),
    ("2024-01-01", "2024-12-31"),
    ("2025-01-01", "2026-07-16"),
]
PAUSE = 0.5


def plan(bundle) -> str:
    return (f"Planetary Computer STAC search ({COLLECTION}) across {len(WINDOWS)} "
            f"date windows, capture metadata + AOI-cropped visual PNG per window's "
            f"lowest-cloud scene — free, no key")


def _bbox(lat: float, lon: float, radius_m: float) -> tuple[float, float, float, float]:
    lat_pad = radius_m / 111_320.0
    lon_pad = radius_m / (111_320.0 * math.cos(math.radians(lat)))
    return (lon - lon_pad, lat - lat_pad, lon + lon_pad, lat + lat_pad)


def fetch(bundle, con, radius_m: float = 150.0) -> SourceResult:
    findings: list[dict] = []
    captured: list[str] = []
    bbox = _bbox(bundle.lat, bundle.lon, radius_m)
    bbox_str = ",".join(f"{v:.6f}" for v in bbox)

    total_scenes = 0
    n_errors = 0
    picks: list[dict] = []
    for start, end in WINDOWS:
        body = {
            "collections": [COLLECTION],
            "bbox": list(bbox),
            "datetime": f"{start}T00:00:00Z/{end}T23:59:59Z",
            "query": {"eo:cloud_cover": {"lt": MAX_CLOUD_COVER}},
            "limit": 100,
        }
        r = None
        last_err: Exception | None = None
        # a 504 from this endpoint has been observed to be a transient
        # overload, not a real empty-AOI result — worth one retry before
        # giving up, so a bad summary line doesn't get mistaken for a
        # genuine "no imagery" finding.
        for attempt in range(2):
            try:
                r = requests.post(STAC_SEARCH, json=body, headers=http_headers(), timeout=40)
                r.raise_for_status()
                last_err = None
                break
            except requests.RequestException as e:
                last_err = e
                r = None
                if attempt == 0:
                    time.sleep(3)
        if last_err is not None or r is None:
            n_errors += 1
            findings.append({"kind": "error", "window": f"{start}..{end}", "error": str(last_err)})
            continue

        captured.append(forensics.capture_source(
            r.content, url=f"{STAC_SEARCH}?window={start}..{end}",
            source_type="osint_planetary_computer_search",
            title=f"Planetary Computer STAC search {bundle.slug} {start}..{end}",
            description=(f"Planetary Computer STAC search, {COLLECTION}, window "
                         f"{start}..{end}, cloud<{MAX_CLOUD_COVER}%, pid={bundle.pid}, "
                         f"bbox={bbox_str}."),
            content_type="application/json", http_status=r.status_code, con=con,
        ))

        feats = r.json().get("features", [])
        total_scenes += len(feats)
        if not feats:
            continue
        best = min(feats, key=lambda f: f.get("properties", {}).get("eo:cloud_cover", 100))
        picks.append(best)

    findings.append({"kind": "pc_search_summary", "n_scenes": total_scenes,
                     "n_windows": len(WINDOWS), "n_errors": n_errors})
    if not picks:
        if n_errors == len(WINDOWS):
            return SourceResult(NAME, False,
                                f"all {len(WINDOWS)} window searches failed "
                                f"(transient API error, e.g. 504) — not a real "
                                f"empty-AOI result, re-run to retry",
                                findings, captured)
        return SourceResult(NAME, True,
                            f"0 scenes found across {len(WINDOWS) - n_errors}/"
                            f"{len(WINDOWS)} windows searched successfully"
                            + (f" ({n_errors} window(s) also failed with a "
                               f"transient error)" if n_errors else ""),
                            findings, captured)

    for item in picks:
        item_id = item["id"]
        props = item.get("properties", {})
        acquired = (props.get("datetime") or "")[:10]
        cloud = props.get("eo:cloud_cover")
        geojson_feature = {
            "type": "Feature", "properties": {},
            "geometry": {"type": "Polygon", "coordinates": [[
                [bbox[0], bbox[1]], [bbox[2], bbox[1]],
                [bbox[2], bbox[3]], [bbox[0], bbox[3]], [bbox[0], bbox[1]],
            ]]},
        }
        crop_url = (f"{CROP_URL}?collection={COLLECTION}&item={item_id}"
                   f"&assets=visual&bbox={bbox_str}")  # bbox in URL for capture provenance only
        rec = {
            "kind": "pc_scene", "item_id": item_id, "acquired": acquired,
            "cloud_cover": cloud,
            "url": f"https://planetarycomputer.microsoft.com/explore?"
                   f"c={bundle.lon:.6f}%2C{bundle.lat:.6f}&z=16&"
                   f"d={COLLECTION}&s={item_id}",
        }
        try:
            ir = requests.post(CROP_URL,
                               params={"collection": COLLECTION, "item": item_id,
                                      "assets": "visual"},
                               json=geojson_feature, headers=http_headers(), timeout=60)
            if ir.status_code == 200 and ir.content and ir.headers.get(
                    "Content-Type", "").startswith("image"):
                sha = forensics.capture_source(
                    ir.content, url=crop_url,
                    source_type="osint_planetary_computer_crop",
                    title=f"Planetary Computer Sentinel-2 crop {item_id} {acquired}",
                    description=(f"Sentinel-2 L2A true-color, AOI-cropped to "
                                 f"bbox={bbox_str} (~{radius_m:.0f}m radius) around "
                                 f"pid={bundle.pid}. Scene {item_id}, acquired "
                                 f"{acquired}, cloud_cover={cloud}%. 10m/pixel — "
                                 f"real address-level crop, not a whole-scene "
                                 f"thumbnail. {rec['url']}"),
                    content_type=ir.headers.get("Content-Type", "image/png"),
                    http_status=ir.status_code, con=con,
                )
                rec["sha256"] = sha
                captured.append(sha)
            else:
                rec["crop_error"] = f"HTTP {ir.status_code} or non-image response"
        except requests.RequestException as e:
            rec["crop_error"] = str(e)
        findings.append(rec)
        time.sleep(PAUSE)

    n_crops = sum(1 for f in findings if f["kind"] == "pc_scene" and "sha256" in f)
    dates = sorted(p.get("properties", {}).get("datetime", "")[:10] for p in picks)
    return SourceResult(NAME, True,
                        f"{total_scenes} scenes found across {len(WINDOWS)} windows, "
                        f"{n_crops} AOI-cropped images captured ({dates[0]} to {dates[-1]})",
                        findings, captured)
