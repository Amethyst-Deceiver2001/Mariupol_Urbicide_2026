"""Source 5 — PastVu historical photos near the address.

API: https://pastvu.com/api2?method=photo.giveNearestPhotos (free, no key);
image bytes at https://pastvu.com/_p/a/<file> (exact pattern confirmed by
the scripts/159 capture). Non-geoblocked, quick — Claude-runnable per the
scripts/159 precedent.
"""
from __future__ import annotations

import json
import logging
import time

import requests

from ... import forensics
from .base import SourceResult, haversine_m, http_headers

log = logging.getLogger(__name__)

NAME = "pastvu"
RUN = "C"
NETWORK = True
DESCRIPTION = "historical photos (pre-war baseline) via pastvu.com API + image capture"

API = "https://pastvu.com/api2"
IMG = "https://pastvu.com/_p/a/{file}"
PAGE = "https://pastvu.com/p/{cid}"
MAX_PHOTOS = 25


def plan(bundle) -> str:
    return f"giveNearestPhotos at point, keep ≤300m, capture listing + up to {MAX_PHOTOS} images"


def fetch(bundle, con, radius_m: float = 300.0) -> SourceResult:
    params = {
        "method": "photo.giveNearestPhotos",
        "params": json.dumps({"geo": [bundle.lat, bundle.lon], "limit": 40}),
    }
    try:
        resp = requests.get(API, params=params, headers=http_headers(), timeout=45)
        resp.raise_for_status()
    except requests.RequestException as e:
        return SourceResult(NAME, False, f"request failed: {e}")

    captured = [forensics.capture_source(
        resp.content, url=resp.url,
        source_type="osint_pastvu_listing",
        title=f"pastvu nearest-photos {bundle.slug}",
        description=(f"PastVu giveNearestPhotos at ({bundle.lat:.6f},"
                     f"{bundle.lon:.6f}), pid={bundle.pid}."),
        content_type="application/json", http_status=resp.status_code, con=con,
    )]

    findings: list[dict] = []
    try:
        photos = resp.json().get("result", {}).get("photos", [])
    except Exception:  # noqa: BLE001
        return SourceResult(NAME, False, "listing captured but parse failed",
                            [], captured)

    n_img = 0
    for p in photos:
        geo = p.get("geo") or [None, None]
        d = (haversine_m(bundle.lat, bundle.lon, geo[0], geo[1])
             if geo[0] is not None else None)
        if d is not None and d > radius_m:
            continue
        cid = p.get("cid")
        rec = {
            "kind": "historical_photo",
            "cid": cid,
            "title": p.get("title", ""),
            "year": p.get("year"),
            "year2": p.get("year2"),
            "dir": p.get("dir", ""),
            "distance_m": round(d, 1) if d is not None else None,
            "page_url": PAGE.format(cid=cid),
        }
        f = p.get("file")
        if f and n_img < MAX_PHOTOS:
            url = IMG.format(file=f)
            try:
                ir = requests.get(url, headers=http_headers(), timeout=60)
                if ir.status_code == 200 and ir.content:
                    sha = forensics.capture_source(
                        ir.content, url=url,
                        source_type="osint_pastvu_photo",
                        title=f"pastvu {cid}: {p.get('title','')[:80]}",
                        description=(f"PastVu photo cid={cid} "
                                     f"'{p.get('title','')}' year={p.get('year')}"
                                     f"-{p.get('year2')} geo={geo} "
                                     f"dist={rec['distance_m']}m from pid={bundle.pid}. "
                                     f"Page: {rec['page_url']}"),
                        content_type=ir.headers.get("Content-Type", "image/jpeg"),
                        http_status=ir.status_code, con=con,
                    )
                    rec["sha256"] = sha
                    rec["image_url"] = url  # stable direct-image URL for reverse-image pivot
                    captured.append(sha)
                    n_img += 1
                    time.sleep(0.4)
            except requests.RequestException:
                log.warning("pastvu image fetch failed cid=%s", cid, exc_info=True)
        findings.append(rec)

    return SourceResult(NAME, True,
                        f"{len(findings)} photos ≤{radius_m:.0f}m "
                        f"({n_img} images captured)",
                        findings, captured)
