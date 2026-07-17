"""Source 21 — reverse-image pivot sheet (manual-assist, no network).

Takes the images already captured for this property by earlier sweep
sources (pastvu / commons / mapillary / flickr — read out of their result
JSONs in the sweep dir) and emits reverse-search links so the user can hunt
for more copies / originals / context by hand. Yandex Images in particular
is the strongest reverse-image engine for Russian/Ukrainian material. Pure
local — constructs URLs / file paths, fetches nothing. Runs LAST (after the
image sources) so it has something to pivot from.

Two pivot modes, chosen per image:
  * `image_url` present  → the source captured the image AND recorded a
    STABLE public direct-image URL (pastvu _p/a CDN, upload.wikimedia.org,
    staticflickr) — emit by-URL reverse-search links that engines can fetch
    directly.
  * only `sha256` present → the image was captured but its source URL is
    expiring/unstable (e.g. Mapillary's signed graph CDN thumbs) or absent
    — point at the LOCAL raw-store file for manual upload (Yandex/Lens both
    accept file upload) instead of a by-URL link that would 404 later.

A finding with NEITHER (metadata-only, e.g. Mapillary images whose thumbs
came back empty behind the token's app-review gate — no bytes ever
captured) is skipped: there is no actual image to reverse-search, so
emitting a link for it would be a false affordance. This was a real bug
fixed 2026-07-16 — the source used to feed source *page* URLs
(mapillary.com/app/?pKey=…, the Commons File: page) to the reverse engines,
which cannot reverse-search an HTML page, and counted metadata-only
Mapillary hits as pivotable images.
"""
from __future__ import annotations

import glob
import json
import logging
import urllib.parse
from pathlib import Path

from ... import config
from .base import SourceResult

log = logging.getLogger(__name__)

NAME = "reverse_image"
RUN = "C"
NETWORK = False
DESCRIPTION = "reverse-image pivot sheet (Yandex Images / Google Lens links) — manual assist"

# result-file -> finding kind that carries a captured image (image_url and/or sha256)
IMAGE_SOURCES = {
    "pastvu.json": "historical_photo",
    "commons.json": "commons_photo",
    "mapillary.json": "mapillary_image",
    "flickr.json": "flickr_photo",
}


def plan(bundle) -> str:
    return "read prior image-source results, emit Yandex/Lens reverse-search links or local-upload paths"


def _pivot_links(public_url: str) -> dict:
    enc = urllib.parse.quote(public_url, safe="")
    return {
        "mode": "by_url",
        "image_url": public_url,
        "yandex_images": f"https://yandex.com/images/search?rpt=imageview&url={enc}",
        "google_lens": f"https://lens.google.com/uploadbyurl?url={enc}",
        "tineye": f"https://tineye.com/search?url={enc}",
    }


def _local_path(sha: str) -> str:
    """Best-effort raw-store path for a captured sha (extension varies)."""
    matches = glob.glob(str(config.DATA_DIR / "raw" / f"{sha}.*"))
    real = [m for m in matches if not m.endswith(".meta.json")]
    return real[0] if real else str(config.DATA_DIR / "raw" / f"{sha}.*")


def fetch(bundle, con, radius_m: float = 0.0) -> SourceResult:
    sweep_dir = config.DATA_DIR / "reports" / "osint" / bundle.slug
    findings: list[dict] = []
    n_by_url = n_local = n_skipped_no_image = 0
    for fname, kind in IMAGE_SOURCES.items():
        fp = sweep_dir / fname
        if not fp.exists():
            continue
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        for f in data.get("findings", []):
            if f.get("kind") != kind:
                continue
            image_url = f.get("image_url") or ""
            sha = f.get("sha256") or ""
            base = {
                "kind": "reverse_image_pivot",
                "from_source": fname.replace(".json", ""),
                "title": f.get("title", ""),
                "sha256": sha,
            }
            if image_url:
                findings.append({**base, **_pivot_links(image_url)})
                n_by_url += 1
            elif sha:
                findings.append({
                    **base, "mode": "local_upload",
                    "local_file": _local_path(sha),
                    "note": ("no stable public image URL (expiring/absent) — "
                             "open this local file and upload it manually at "
                             "yandex.com/images or lens.google.com"),
                })
                n_local += 1
            else:
                # metadata-only finding: no bytes were ever captured, nothing
                # to reverse-search — skip rather than emit a false link.
                n_skipped_no_image += 1

    if not findings:
        note = ("no captured images to pivot from yet — run pastvu/commons/"
                "mapillary/flickr first, or those sources found no imagery "
                f"for this address ({n_skipped_no_image} metadata-only hits skipped)")
    else:
        note = (f"{len(findings)} images with reverse-search links "
                f"({n_by_url} by-URL, {n_local} local-upload; "
                f"{n_skipped_no_image} metadata-only hits skipped)")
    return SourceResult(NAME, True, note, findings)
