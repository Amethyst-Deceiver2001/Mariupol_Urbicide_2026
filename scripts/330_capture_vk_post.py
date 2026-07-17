#!/usr/bin/env python3
"""Capture + transcribe a specific, manually-identified VK post.

User-flagged 2026-07-16: https://vk.ru/wall-211186281_167139 — found by
hand while reviewing the automated `vk` OSINT source's noisy results for
pid 4837 (улица Зелинского, 17а); this is the one genuinely relevant post
(a resident's address) buried among generic Mariupol/other-city photos the
automated photos.search geo-radius query returned. See vk.py's docstring
fix for why the automated search is noisy.

Fetches the post via wall.getById, captures the full JSON + every attached
photo at best resolution, and prints the post text (and any OCR-relevant
photo notes) for transcription review. Needs config.VK_ACCESS_TOKEN.
VK is Russian infrastructure -> RUN=V: user-terminal/VPS only, Claude
never executes this.

Usage:
    PYTHONPATH=src .venv312/bin/python scripts/330_capture_vk_post.py \\
        --owner -211186281 --post 167139
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

API = "https://api.vk.com/method/{method}"
API_VERSION = "5.199"
SOURCE_TYPE = "osint_vk_flagged_post"
PAUSE = 0.35
PAGE_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
          "(KHTML, like Gecko) Version/17.4.1 Safari/605.1.15")


def _scrape_progressive_urls(video_url: str) -> dict[int, str]:
    """Scrape the video page's embedded player config for direct, whole-file
    progressive mp4 URLs keyed by resolution (240/360/480/720/1080).

    This is what actually works, confirmed 2026-07-16 after video.get's
    'files'/'direct_url' both failed (direct_url resolved to an HTML page,
    not media — needs a logged-in browser session per VK, not a plain
    server-side GET). The video *page* itself embeds a <script type=module>
    containing 'al_video.php' with a JSON blob carrying "url240"/"url360"/
    etc. keys pointing at real, directly-downloadable per-resolution files
    — no DASH segment reconstruction needed. Technique credit: reverse-
    engineered independently by github.com/o-mikhailovskii/vkVideoDownloader;
    reimplemented here (not vendored) to stay inside this project's own
    forensics.capture_source() chain-of-custody pipeline.
    """
    r = requests.get(video_url, headers={"User-Agent": PAGE_UA}, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, "html.parser")
    scripts = [s for s in soup.find_all("script", {"type": "module"})
              if s.text and "al_video.php" in s.text]
    if not scripts:
        return {}
    text = scripts[0].text
    matches = re.findall(r'"url(\d+)":\s*"([^"]+)"', text)
    # VK JSON-escapes the URLs (\/ for /, & for &) — unescape before use
    out = {}
    for res, url in matches:
        clean = url.replace("\\/", "/").encode().decode("unicode_escape")
        out[int(res)] = clean
    return out


def _call(method: str, **params) -> dict | None:
    if not config.VK_ACCESS_TOKEN:
        log.error("VK_ACCESS_TOKEN not set in .env — aborting")
        sys.exit(1)
    params.update({"access_token": config.VK_ACCESS_TOKEN, "v": API_VERSION})
    r = requests.get(API.format(method=method), params=params, timeout=40)
    r.raise_for_status()
    j = r.json()
    if "error" in j:
        log.error("VK %s error: %s", method, j["error"].get("error_msg"))
        sys.exit(1)
    return j.get("response")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--owner", type=int, required=True,
                    help="owner_id from the wall URL, e.g. -211186281 (negative = group/community)")
    ap.add_argument("--post", type=int, required=True, help="post id from the wall URL")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    url = f"https://vk.com/wall{args.owner}_{args.post}"
    log.info("fetching %s", url)

    resp = _call("wall.getById", posts=f"{args.owner}_{args.post}", extended=1)
    items = resp.get("items", []) if resp else []
    if not items:
        log.error("post not found (deleted, private, or requires membership) — %s", url)
        sys.exit(1)
    post = items[0]

    con = forensics.open_state()

    import json
    raw_json = json.dumps(post, ensure_ascii=False, indent=2).encode("utf-8")
    sha = forensics.capture_source(
        raw_json, url=url, source_type=SOURCE_TYPE,
        title=f"VK post {args.owner}_{args.post}",
        description=(f"User-flagged 2026-07-16 while reviewing pid=4837 (улица "
                     f"Зелинского, 17а) OSINT sweep — the one relevant hit "
                     f"among the automated vk source's noisy results. {url}"),
        content_type="application/json", http_status=200, con=con,
    )
    log.info("captured post JSON -> sha=%s", sha[:16])

    text = post.get("text", "")
    print("\n" + "=" * 72)
    print("POST TEXT (verbatim, for manual transcription review):")
    print("=" * 72)
    print(text or "(no text body — check attachments)")
    print("=" * 72 + "\n")

    date_str = ""
    if post.get("date"):
        import datetime as _dt
        date_str = _dt.datetime.fromtimestamp(post["date"], _dt.timezone.utc).strftime("%Y-%m-%d")
    log.info("post date: %s", date_str or "unknown")

    n_photos = 0
    for att in post.get("attachments", []):
        if att.get("type") != "photo":
            continue
        photo = att["photo"]
        sizes = photo.get("sizes", [])
        best = max(sizes, key=lambda s: s.get("width", 0), default={})
        if not best.get("url"):
            continue
        try:
            ir = requests.get(best["url"], timeout=60)
            if ir.status_code == 200 and ir.content:
                photo_id = f"{photo.get('owner_id')}_{photo.get('id')}"
                psha = forensics.capture_source(
                    ir.content, url=best["url"],
                    source_type="osint_vk_flagged_post_photo",
                    title=f"VK post {args.owner}_{args.post} photo {photo_id}",
                    description=(f"Attached photo from user-flagged VK post {url}, "
                                 f"date {date_str}. photo_id={photo_id}. If this "
                                 f"photo contains address/document text, run "
                                 f"scripts/326_rekognition_photo_triage.py "
                                 f"--source-type osint_vk_flagged_post_photo"),
                    content_type=ir.headers.get("Content-Type", "image/jpeg"),
                    http_status=ir.status_code, con=con,
                )
                n_photos += 1
                log.info("captured photo %s -> sha=%s", photo_id, psha[:16])
                time.sleep(PAUSE)
        except requests.RequestException as e:
            log.warning("photo fetch failed: %s", e)

    n_videos = 0
    for att in post.get("attachments", []):
        if att.get("type") != "video":
            continue
        v = att["video"]
        v_owner, v_id, v_key = v.get("owner_id"), v.get("id"), v.get("access_key")
        video_url = f"https://vkvideo.ru/video{v_owner}_{v_id}"
        # vk.com's legacy video page template is what actually embeds the
        # al_video.php script the page-scrape method looks for;
        # vkvideo.ru (VK's newer rebranded product) uses a different,
        # JS-rendered SPA template with no such embedded script — confirmed
        # empirically 2026-07-16 (scrape found nothing on vkvideo.ru).
        scrape_url = f"https://vk.com/video{v_owner}_{v_id}"
        log.info("found video attachment: %s (%r, %ds)", video_url,
                 v.get("title", ""), v.get("duration", 0))

        # Method 1 (primary): scrape the video page itself for embedded
        # progressive mp4 URLs — confirmed working 2026-07-16 after the
        # API-based methods below both failed.
        file_url, best_key = None, None
        try:
            scraped = _scrape_progressive_urls(scrape_url)
        except requests.RequestException as e:
            log.warning("page scrape request failed: %s", e)
            scraped = {}
        if scraped:
            best_res = max(scraped)
            file_url, best_key = scraped[best_res], f"page-scrape_{best_res}p"
            log.info("page scrape found resolutions: %s — using %dp",
                     sorted(scraped, reverse=True), best_res)
        else:
            log.warning("page scrape found no al_video.php config for %s "
                       "— falling back to video.get API", scrape_url)
            # Method 2 (fallback): video.get API — wall.getById's embedded
            # video object never carries direct file URLs (only preview
            # images), so this separate call is needed. Confirmed this
            # account's video.get returns no 'files' dict for at least one
            # real video, and its 'direct_url' resolved to an HTML page
            # requiring a logged-in browser session, not a plain GET — kept
            # only as a last-resort attempt, not relied on.
            videos_param = f"{v_owner}_{v_id}"
            if v_key:
                videos_param += f"_{v_key}"
            vresp = _call("video.get", videos=videos_param)
            vitems = vresp.get("items", []) if vresp else []
            if vitems:
                vitem = vitems[0]
                files = vitem.get("files", {})
                mp4_keys = sorted([k for k in files if k.startswith("mp4_")],
                                  key=lambda k: int(k.split("_")[1]), reverse=True)
                if mp4_keys:
                    best_key = mp4_keys[0]
                    file_url = files[best_key]
                elif vitem.get("direct_url"):
                    best_key = "direct_url"
                    file_url = vitem["direct_url"]
            if not file_url:
                log.error("both page-scrape and video.get API failed for %s "
                         "— manual capture needed (see prior 'Save Video As' "
                         "instructions)", video_url)
                continue
        log.info("downloading %s (%s) ...", video_url, best_key)
        try:
            vr = requests.get(file_url, timeout=180, allow_redirects=True)
            ctype = vr.headers.get("Content-Type", "")
            # direct_url can resolve to an HTML login/view page instead of
            # raw media (confirmed: happened here) — never trust status 200
            # alone, verify the response is actually binary video content.
            looks_like_video = (
                vr.status_code == 200 and vr.content
                and not ctype.startswith("text/")
                and not vr.content[:15].lstrip().startswith(b"<")
            )
            if looks_like_video:
                vsha = forensics.capture_source(
                    vr.content, url=video_url,
                    source_type="osint_vk_flagged_post_video",
                    title=f"VK post {args.owner}_{args.post} video {v_owner}_{v_id}",
                    description=(f"Video attachment from user-flagged VK post {url}, "
                                 f"date {date_str}. Title: {v.get('title','')!r}, "
                                 f"duration {v.get('duration',0)}s, quality {best_key}. "
                                 f"{video_url}"),
                    content_type=ctype or "video/mp4", http_status=vr.status_code, con=con,
                )
                n_videos += 1
                log.info("captured video -> sha=%s (%d bytes, %s, content-type=%s)",
                         vsha[:16], len(vr.content), best_key, ctype)
            elif vr.status_code == 200:
                log.error("'%s' resolved to HTML/text (%s), not video content "
                         "— not captured. VK's direct_url for this video "
                         "appears to require a logged-in browser session, not "
                         "a plain HTTP GET. Try: open %s in a browser where "
                         "you're logged into VK, right-click the video, "
                         "'copy video address', and paste that URL back for "
                         "a manual capture.", file_url[:80], ctype, video_url)
            else:
                log.error("video download failed: HTTP %s", vr.status_code)
        except requests.RequestException as e:
            log.error("video download failed: %s", e)

    log.info("done — post captured, %d photo(s), %d video(s) captured",
             n_photos, n_videos)
    if n_photos:
        log.info("Next (if photos may contain address/document text): "
                "PYTHONPATH=src .venv312/bin/python "
                "scripts/326_rekognition_photo_triage.py "
                "--source-type osint_vk_flagged_post_photo --limit 10")


if __name__ == "__main__":
    main()
