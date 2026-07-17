"""Source 10 — Yandex Maps photo-layer hotspots near the address.

Yandex has pre-war and post-war street-level photos tagged to points on the
map ("photo layer", `l=pht`). Earlier design assumed this needed a headless
browser (playwright) driving the interactive map UI, capturing whatever XHR
fired — but a passive page load never fires the photo-data request; Yandex
only requests it once a photo pin is CLICKED, so headless automation
reliably caught nothing but generic noise (`/layers/info`,
`/discoveryFeed/getHomeFeed`). Confirmed by diagnostic 2026-07-16
(scripts/333_yandex_maps_pin_xhr.py, an interactive session with full
request logging).

That diagnostic also found a REAL FIX: the photo layer is backed by a
keyless, session-less tile-server endpoint —
    core-pht-renderer.maps.yandex.net/3.x/tiles
        ?l=phj&x=<tx>&y=<ty>&z=<z>&scale=1&v=<cache-version>
        &lang=en_US&format=json&client_id=yandex-web-maps
— a public `client_id` constant (not a personal API key), no cookies/CSRF
needed. Response is a `HotspotSearchResponse` GeoJSON FeatureCollection;
each feature's `HotspotMetaData.id` (`img_<a>:<b>`) is a real photo id and
`geometry.coordinates` is `[lat, lon]` (confirmed non-standard order) of the
photo point. This is genuinely queryable with plain `requests`, no browser.

Tile addressing quirk (calibrated empirically, cause unconfirmed): standard
Web Mercator X matches exactly, but Y is offset by a CONSTANT
+`_Y_OFFSET_Z18` from the standard slippy-map formula at z=18. Verified at
3 geographically distant points (pid 4837 Мариуполь, pid ~5865 Нахимова 82,
and central Kyiv — all far enough apart that a Mercator/projection bug
would show a different offset at each, but the offset held constant), so
treated as a fixed indexing quirk of Yandex's tile scheme rather than
anything address-specific. A small local grid search (`_SEARCH_RADIUS_TILES`
in each direction) around the offset-corrected estimate absorbs any residual
rounding, so this doesn't depend on the constant being exact.

Known limitation: this gets photo EXISTENCE + id + approximate point, not
the full photo (image URL, upload date, uploader) — for that,
`yandex.com/maps/api/photos/getById?id=<id>` needs `csrfToken` AND two more
params neither appear in static HTML: `sessionId` (minted per page load) and
`s` (a per-request signature). Root-caused 2026-07-17 via
scripts/347_yandex_photo_detail_token_hunt.py (an interactive session
logging real outgoing request URLs after an actual click-through, not just
responses): a hand-built request missing `s`/`sessionId` gets silently
echoed a fresh `{"csrfToken": "<token>"}` stub instead of erroring (the trap
fixed 2026-07-16 — detecting/discarding that stub shape, without yet
understanding why it fired). The static `csrfToken` grepped from page HTML
turned out to be valid all along; `s`/`sessionId` are computed by Yandex's
own front-end JS and only exist once a photo marker is genuinely clicked —
they cannot be constructed from a passive `page.goto()`. So the fix is to
let the page's JS build and fire the request: navigate the map centered on
each hotspot's own coordinates, click it, and capture whatever real
`getById` response the page's own JS emits (`page.on("response")`), rather
than crafting the URL ourselves. The hotspot search above is unaffected and
is this source's validated, real deliverable on its own — existence + id +
approximate point for every photo pin near an address, zero session/auth
needed.

RUN=U: Yandex is Russian infrastructure (ToS-gray) even though the hotspot
endpoint itself isn't technically geoblocked from outside Russia (confirmed
during calibration) — the user runs it, per this project's standing rule
for Russian-infra sources.
"""
from __future__ import annotations

import logging
import math
import time

import requests

from ... import config, forensics
from .base import SourceResult, http_headers

log = logging.getLogger(__name__)

NAME = "yandex_maps"
RUN = "U"
NETWORK = True
DESCRIPTION = "Yandex Maps photo-layer hotspot search (keyless tile API) + optional photo-detail pass"

TILE_API = "https://core-pht-renderer.maps.yandex.net/3.x/tiles"
TILE_ZOOM = 18
# cache-buster the tile API rejects requests without; observed live
# 2026-07-16 — if this endpoint starts 400ing broadly, Yandex has rotated
# it and it needs re-pinning via scripts/333.
TILE_VERSION = "2026.07.07.16.25.52.new"
CLIENT_ID = "yandex-web-maps"
# empirically calibrated 2026-07-16 (see module docstring) — constant
# across 3 distant test points at TILE_ZOOM=18.
_Y_OFFSET_Z18 = 204
_SEARCH_RADIUS_TILES = 2  # ±2 tiles in x and y = 25 requests per address

PHOTOS_API = "https://yandex.com/maps/api/photos/getById"
MAX_DETAIL_PULLS = 10  # cap the optional playwright detail pass


def plan(bundle) -> str:
    return (f"keyless tile-hotspot search (±{_SEARCH_RADIUS_TILES} tiles @ z{TILE_ZOOM}) "
            f"for photo-layer pins near the point; optional playwright detail pass "
            f"on up to {MAX_DETAIL_PULLS} ids if chromium is available")


def _std_tile(lat: float, lon: float, z: int) -> tuple[int, int]:
    n = 2 ** z
    lat_rad = math.radians(lat)
    xtile = int((lon + 180) / 360 * n)
    ytile = int((1 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2 * n)
    return xtile, ytile


def _hotspot_search(lat: float, lon: float, con) -> tuple[list[dict], list[str]]:
    """Grid search around the offset-corrected tile estimate. Returns
    (photo hotspot records, captured shas)."""
    xtile, ytile_std = _std_tile(lat, lon, TILE_ZOOM)
    ytile = ytile_std + _Y_OFFSET_Z18
    seen_ids: set[str] = set()
    records: list[dict] = []
    captured: list[str] = []
    r = _SEARCH_RADIUS_TILES

    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            tx, ty = xtile + dx, ytile + dy
            try:
                resp = requests.get(TILE_API, params={
                    "l": "phj", "x": tx, "y": ty, "z": TILE_ZOOM, "scale": 1,
                    "v": TILE_VERSION, "lang": "en_US", "format": "json",
                    "client_id": CLIENT_ID,
                }, headers=http_headers(), timeout=20)
            except requests.RequestException:
                continue
            if resp.status_code != 200:
                continue
            try:
                data = resp.json()
            except ValueError:
                continue
            feats = data.get("data", {}).get("features", [])
            if not feats:
                continue

            sha = forensics.capture_source(
                resp.content, url=resp.url,
                source_type="osint_yandex_photo_hotspot_tile",
                title=f"yandex photo hotspot tile ({tx},{ty},{TILE_ZOOM})",
                description=(f"Yandex photo-layer hotspot tile ({tx},{ty},z={TILE_ZOOM}) "
                             f"near ({lat:.6f},{lon:.6f})."),
                content_type="application/json", http_status=resp.status_code, con=con,
            )
            captured.append(sha)

            for f in feats:
                meta = f.get("properties", {}).get("HotspotMetaData", {})
                oid = meta.get("id", "")
                if not oid or oid in seen_ids:
                    continue
                seen_ids.add(oid)
                geom = f.get("geometry", {}).get("coordinates", [None, None])
                # confirmed non-standard order: [lat, lon]
                records.append({
                    "kind": "yandex_photo_hotspot", "id": oid,
                    "provider": meta.get("provider", ""),
                    "lat": geom[0], "lon": geom[1],
                    "tile": [tx, ty, TILE_ZOOM],
                })
            time.sleep(0.15)
    return records, captured


_DETAIL_CLICK_ZOOM = TILE_ZOOM + 2  # zoom in tight so the target pin is
# isolated near viewport center — makes a blind center-click far more
# likely to actually land on it than at the wider search zoom.
_DETAIL_VIEWPORT = {"width": 1280, "height": 900}
_DETAIL_WAIT_MS = 1200  # time to let a real getById fire after each click
# 0/8 across two runs at raw-viewport-center clicks turned out NOT to be a
# targeting-precision problem — a headless-vs-headed screenshot diagnostic
# (scripts/348, 2026-07-17) proved the pin renders correctly in headless
# (SwiftShader software WebGL is fine here, no blank-canvas issue) but sits
# nowhere near the raw viewport midpoint: the left "categories" search panel
# (~420px wide at this viewport) eats into the layout, so the map CANVAS's
# own center is offset well to the right of viewport-width/2. Empirically
# measured from that screenshot: canvas center ~= (viewport_center_x + 210,
# viewport_center_y + 10). Offsets below are relative to THAT corrected
# center, not raw viewport center.
_MAP_CANVAS_CENTER_OFFSET = (210, 10)
_DETAIL_CLICK_OFFSETS = [
    (0, 0), (0, -20), (0, -35), (0, -50),
    (15, -20), (-15, -20), (15, -35), (-15, -35),
    (15, 0), (-15, 0), (0, 15),
]


def _photo_detail_pass(hotspots: list[dict], lat: float, lon: float,
                       con) -> tuple[list[dict], list[str]]:
    """Optional: for up to MAX_DETAIL_PULLS hotspots, drive a real click on
    the map so Yandex's OWN front-end JS builds and fires the getById
    request (with the `s`/`sessionId` params only real client-side code can
    compute — see module docstring), then capture whatever real response
    comes back. Best-effort — skips cleanly if playwright/chromium isn't
    available, or per-hotspot if the click misses; the hotspot search above
    already succeeded independent of this."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return [], []

    details: list[dict] = []
    captured: list[str] = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(user_agent=config.USER_AGENT,
                                           viewport=_DETAIL_VIEWPORT)

            for hs in hotspots[:MAX_DETAIL_PULLS]:
                oid = hs["id"]
                h_lat, h_lon = hs.get("lat", lat), hs.get("lon", lon)
                page = context.new_page()
                caught: dict = {}

                def _on_response(resp, _oid=oid, _caught=caught):
                    try:
                        u = resp.url
                        if "api/photos/getbyid" not in u.lower():
                            return
                        if _oid not in u and _oid.split(":")[0] not in u:
                            return
                        if resp.status != 200:
                            return
                        body = resp.body()
                        # a token/session-stub response ({"csrfToken":"..."})
                        # means the click didn't mint a real session for this
                        # request — skip rather than capture it as real data.
                        if body.strip().startswith(b'{"csrfToken"'):
                            return
                        _caught["body"] = body
                        _caught["url"] = u
                        _caught["status"] = resp.status
                    except Exception:  # noqa: BLE001
                        pass

                page.on("response", _on_response)
                try:
                    url = (f"https://yandex.com/maps/?l=pht&ll="
                          f"{h_lon:.6f},{h_lat:.6f}&z={_DETAIL_CLICK_ZOOM}")
                    page.goto(url, wait_until="networkidle", timeout=45000)
                    cx = _DETAIL_VIEWPORT["width"] // 2 + _MAP_CANVAS_CENTER_OFFSET[0]
                    cy = _DETAIL_VIEWPORT["height"] // 2 + _MAP_CANVAS_CENTER_OFFSET[1]
                    for ox, oy in _DETAIL_CLICK_OFFSETS:
                        page.mouse.click(cx + ox, cy + oy)
                        page.wait_for_timeout(_DETAIL_WAIT_MS)
                        if caught.get("body"):
                            break
                except Exception:  # noqa: BLE001
                    pass
                finally:
                    page.close()

                if not caught.get("body"):
                    log.info("yandex_maps: no getById response captured for "
                            "hotspot %s (click likely missed the pin)", oid)
                    continue

                sha = forensics.capture_source(
                    caught["body"], url=caught["url"],
                    source_type="osint_yandex_photo_detail",
                    title=f"yandex photo detail {oid}",
                    description=(f"Yandex photo detail for hotspot {oid}, captured via "
                                 "real click-through (page's own JS fired the request)."),
                    content_type="application/json", http_status=caught["status"], con=con,
                )
                captured.append(sha)
                details.append({"kind": "yandex_photo_detail", "id": oid, "sha256": sha})

            browser.close()
    except Exception:  # noqa: BLE001
        log.warning("yandex_maps photo-detail pass failed (hotspot search still valid)",
                    exc_info=True)
    return details, captured


def fetch(bundle, con, radius_m: float = 150.0) -> SourceResult:
    hotspots, tile_shas = _hotspot_search(bundle.lat, bundle.lon, con)

    findings: list[dict] = list(hotspots)
    captured: list[str] = list(tile_shas)

    details, detail_shas = _photo_detail_pass(hotspots, bundle.lat, bundle.lon, con)
    findings.extend(details)
    captured.extend(detail_shas)

    note = (f"{len(hotspots)} photo hotspots found (keyless tile search); "
            f"{len(details)}/{min(len(hotspots), MAX_DETAIL_PULLS)} full-detail "
            f"pulls {'succeeded' if details else '(playwright unavailable or all failed)'}")
    return SourceResult(NAME, True, note, findings, captured)
