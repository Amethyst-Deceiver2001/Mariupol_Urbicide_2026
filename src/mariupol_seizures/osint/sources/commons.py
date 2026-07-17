"""Source 8 — Wikimedia Commons geosearch (photos near the address).

Commons keeps EXIF/extmetadata (DateTimeOriginal, GPS, author, license) —
one of the two sources in the matrix that preserves camera geotags.
Free API, no key. Original files capped at 25MB; larger files captured as
a 2048px thumb instead.
"""
from __future__ import annotations

import logging
import time

import requests

from ... import forensics
from .base import SourceResult, http_headers

log = logging.getLogger(__name__)

NAME = "commons"
RUN = "C"
NETWORK = True
DESCRIPTION = "Wikimedia Commons geosearch + image capture (EXIF preserved)"

API = "https://commons.wikimedia.org/w/api.php"
MAX_FILES = 20
MAX_ORIGINAL_BYTES = 25 * 1024 * 1024


def plan(bundle) -> str:
    return f"geosearch ns=6 radius≤300m, imageinfo+extmetadata, capture ≤{MAX_FILES} files"


def fetch(bundle, con, radius_m: float = 300.0) -> SourceResult:
    captured: list[str] = []
    try:
        r = requests.get(API, params={
            "action": "query", "list": "geosearch",
            "gscoord": f"{bundle.lat}|{bundle.lon}",
            "gsradius": str(int(min(radius_m, 10000))),
            "gslimit": "50", "gsnamespace": "6", "format": "json",
        }, headers=http_headers(), timeout=45)
        r.raise_for_status()
        gs = r.json().get("query", {}).get("geosearch", [])
    except requests.RequestException as e:
        return SourceResult(NAME, False, f"geosearch failed: {e}")

    captured.append(forensics.capture_source(
        r.content, url=r.url,
        source_type="osint_commons_geosearch",
        title=f"commons geosearch {bundle.slug}",
        description=(f"Wikimedia Commons geosearch at ({bundle.lat:.6f},"
                     f"{bundle.lon:.6f}) r={radius_m:.0f}m, pid={bundle.pid}."),
        content_type="application/json", http_status=r.status_code, con=con,
    ))

    findings: list[dict] = []
    for i, hit in enumerate(gs[:MAX_FILES]):
        title = hit.get("title", "")
        try:
            ir = requests.get(API, params={
                "action": "query", "titles": title, "prop": "imageinfo",
                "iiprop": "url|size|extmetadata", "iiurlwidth": "2048",
                "format": "json",
            }, headers=http_headers(), timeout=45)
            ir.raise_for_status()
            pages = ir.json().get("query", {}).get("pages", {})
            info = next(iter(pages.values())).get("imageinfo", [{}])[0]
        except Exception:  # noqa: BLE001
            log.warning("imageinfo failed for %s", title, exc_info=True)
            continue
        ext = info.get("extmetadata", {}) or {}

        def meta(k):
            v = ext.get(k) or {}
            return str(v.get("value", ""))[:200]

        rec = {
            "kind": "commons_photo",
            "title": title,
            "page_url": info.get("descriptionurl", ""),
            "date_original": meta("DateTimeOriginal"),
            "author": meta("Artist"),
            "license": meta("LicenseShortName"),
            "gps": f'{meta("GPSLatitude")},{meta("GPSLongitude")}'.strip(","),
            "distance_m": hit.get("dist"),
        }
        dl = (info.get("url") if (info.get("size") or 0) <= MAX_ORIGINAL_BYTES
              else info.get("thumburl"))
        if dl:
            try:
                fr = requests.get(dl, headers=http_headers(), timeout=90)
                if fr.status_code == 200 and fr.content:
                    sha = forensics.capture_source(
                        fr.content, url=dl,
                        source_type="osint_commons_photo",
                        title=title[:120],
                        description=(f"Commons file near pid={bundle.pid} "
                                     f"({rec['distance_m']}m). "
                                     f"date={rec['date_original']} "
                                     f"license={rec['license']} "
                                     f"page={rec['page_url']}"),
                        content_type=fr.headers.get("Content-Type", "image/jpeg"),
                        http_status=fr.status_code, con=con,
                    )
                    rec["sha256"] = sha
                    rec["image_url"] = dl  # stable upload.wikimedia.org URL for reverse-image pivot
                    captured.append(sha)
                    time.sleep(0.4)
            except requests.RequestException:
                log.warning("commons file fetch failed: %s", dl, exc_info=True)
        findings.append(rec)

    return SourceResult(NAME, True,
                        f"{len(gs)} geosearch hits, {len(findings)} files processed",
                        findings, captured)
