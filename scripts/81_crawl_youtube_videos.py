#!/usr/bin/env python3
"""Forensic capture of YouTube videos relevant to Mariupol property seizures.

Uses yt-dlp to download video + metadata, then ingests into the forensics store
with full Berkeley Protocol chain of custody (SHA-256, ISO-8601 timestamps,
sidecar .meta.json, logged to source_document).

VIDEO LIST — add new entries to VIDEOS below.
Each entry: (youtube_id, property_ids, description_note)

Currently catalogued:
  2iMpIXJNAXo  — Пр.Строителей 74,76,78 April 2022
                  Channel: Мариуполь. Разное. (@Magdalina-_-M)
                  Siege-era footage of buildings in Case 7 (death_sites_new_construction.md)
                  before demolition; land granted to СЗ-1 ПОРФИР via decrees 390-394.

Run:
    python scripts/81_crawl_youtube_videos.py
    python scripts/81_crawl_youtube_videos.py --id 2iMpIXJNAXo   # single video

Output:
    data/raw/<sha256>.bin + <sha256>.meta.json   — raw video bytes
    data/raw/<sha256>.bin + <sha256>.meta.json   — metadata JSON
    Logged to source_document table (source_type=youtube_video / youtube_metadata)
"""
import argparse
import hashlib
import json
import logging
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import forensics  # noqa: E402

log = logging.getLogger(__name__)

SOURCE_TYPE_VIDEO = "youtube_video"
SOURCE_TYPE_META  = "youtube_metadata"

# ── Video catalogue ────────────────────────────────────────────────────────────
# (youtube_id, property_ids, evidence_note)
VIDEOS = [
    (
        "2iMpIXJNAXo",
        [6262, 6263, 6264],  # Строителей 74/76/78 — adjust pids if spine differs
        (
            "Siege-era footage of пр.Строителей 74, 76, 78, April 2022. "
            "Channel: 'Мариуполь. Разное.' (@Magdalina-_-M). "
            "Buildings still standing post-siege; all three subsequently demolished "
            "and land granted to developer СЗ-1 ПОРФИР via Пушилин decrees 390-394. "
            "Case 7 in docs/case_studies/death_sites_new_construction.md. "
            "RD4U: A3.1/A3.2. Rome Statute Art.8(2)(b)(viii) context."
        ),
    ),
]


def _oembed_meta(vid_id: str) -> dict:
    """Fetch oEmbed metadata (title, author, thumbnail) without authentication."""
    url = (
        f"https://www.youtube.com/oembed"
        f"?url=https://www.youtube.com/watch?v={vid_id}&format=json"
    )
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.loads(r.read())
    except Exception as e:
        log.warning("oEmbed fetch failed for %s: %s", vid_id, e)
        return {}


def _ytdlp_download(vid_id: str, out_dir: Path) -> Path | None:
    """Download best-quality mp4 (capped at 1080p) to out_dir. Returns file path."""
    url = f"https://www.youtube.com/watch?v={vid_id}"
    out_tmpl = str(out_dir / "%(id)s.%(ext)s")
    cmd = [
        "yt-dlp",
        "--format", "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--no-playlist",
        "--quiet",
        "--no-warnings",
        "-o", out_tmpl,
        url,
    ]
    log.info("downloading %s …", url)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log.error("yt-dlp failed for %s:\n%s", vid_id, result.stderr[:500])
        return None
    # Find the downloaded file
    candidates = sorted(out_dir.glob(f"{vid_id}.*"))
    if not candidates:
        log.error("yt-dlp ran but no file found for %s", vid_id)
        return None
    return candidates[0]


def _ytdlp_info_json(vid_id: str, out_dir: Path) -> dict:
    """Extract full yt-dlp info JSON without downloading the video."""
    url = f"https://www.youtube.com/watch?v={vid_id}"
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--no-playlist",
        "--quiet",
        "--no-warnings",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not result.stdout.strip():
        log.warning("info JSON failed for %s", vid_id)
        return {}
    try:
        return json.loads(result.stdout)
    except Exception:
        return {}


def capture_video(con, vid_id: str, property_ids: list[int], evidence_note: str) -> bool:
    """Full forensic capture of one YouTube video. Returns True on success."""
    yt_url = f"https://www.youtube.com/watch?v={vid_id}"

    # 1. oEmbed metadata (lightweight, no auth)
    oembed = _oembed_meta(vid_id)
    title  = oembed.get("title") or vid_id
    author = oembed.get("author_name") or ""
    log.info("video: %r  by %r", title, author)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # 2. Full info JSON via yt-dlp (rich metadata: upload_date, description, tags…)
        info = _ytdlp_info_json(vid_id, tmp)
        upload_date = info.get("upload_date") or ""  # YYYYMMDD
        description = info.get("description") or ""
        duration    = info.get("duration")           # seconds
        view_count  = info.get("view_count")
        uploader    = info.get("uploader") or author
        channel_url = info.get("channel_url") or oembed.get("author_url") or ""

        # Merge into a compact metadata record
        meta_obj = {
            "youtube_id":   vid_id,
            "youtube_url":  yt_url,
            "title":        title,
            "uploader":     uploader,
            "channel_url":  channel_url,
            "upload_date":  upload_date,
            "description":  description,
            "duration_s":   duration,
            "view_count":   view_count,
            "oembed":       oembed,
            "property_ids": property_ids,
            "evidence_note": evidence_note,
        }
        meta_bytes = json.dumps(meta_obj, ensure_ascii=False, indent=2).encode("utf-8")

        # Capture metadata record first
        meta_sha = forensics.capture_source(
            meta_bytes,
            url=yt_url + "#metadata",
            source_type=SOURCE_TYPE_META,
            title=f"YouTube metadata: {title}",
            description=(
                f"yt-dlp info JSON for {yt_url}. "
                f"Uploader: {uploader}. Upload date: {upload_date}. "
                f"property_ids={property_ids}. {evidence_note[:200]}"
            ),
            content_type="application/json",
            http_status=200,
            con=con,
        )
        log.info("metadata captured: sha=%s", meta_sha[:12])

        # 3. Download video
        vid_path = _ytdlp_download(vid_id, tmp)
        if not vid_path:
            log.error("video download failed — metadata only captured")
            return False

        video_bytes = vid_path.read_bytes()
        ext = vid_path.suffix.lstrip(".")
        ct  = "video/mp4" if ext == "mp4" else f"video/{ext}"

        video_sha = forensics.capture_source(
            video_bytes,
            url=yt_url,
            source_type=SOURCE_TYPE_VIDEO,
            title=f"YouTube video: {title}",
            description=(
                f"Video download of {yt_url}. "
                f"Title: {title!r}. Uploader: {uploader!r}. "
                f"Upload date: {upload_date}. Duration: {duration}s. "
                f"property_ids={property_ids}. "
                f"metadata_sha={meta_sha[:12]}. "
                f"{evidence_note[:300]}"
            ),
            content_type=ct,
            http_status=200,
            con=con,
        )
        log.info("video captured: sha=%s  size=%d bytes", video_sha[:12], len(video_bytes))

    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", metavar="YOUTUBE_ID",
                        help="Process only this video ID from the catalogue")
    args = parser.parse_args()

    con = forensics.open_state()

    targets = VIDEOS
    if args.id:
        targets = [v for v in VIDEOS if v[0] == args.id]
        if not targets:
            log.error("ID %r not in catalogue", args.id)
            sys.exit(1)

    ok = fail = skip = 0
    for vid_id, pids, note in targets:
        # Idempotency: skip if already captured
        existing = con.execute(
            "SELECT COUNT(*) FROM source_document WHERE source_type=? AND url=?",
            (SOURCE_TYPE_VIDEO, f"https://www.youtube.com/watch?v={vid_id}"),
        ).fetchone()[0]
        if existing:
            log.info("already captured: %s — skipping", vid_id)
            skip += 1
            continue

        log.info("─── capturing %s ───", vid_id)
        if capture_video(con, vid_id, pids, note):
            ok += 1
        else:
            fail += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"YouTube capture complete")
    print(f"  captured : {ok}")
    print(f"  failed   : {fail}")
    print(f"  skipped  : {skip} (already in store)")

    total_v = con.execute(
        "SELECT COUNT(*) FROM source_document WHERE source_type=?",
        (SOURCE_TYPE_VIDEO,),
    ).fetchone()[0]
    total_m = con.execute(
        "SELECT COUNT(*) FROM source_document WHERE source_type=?",
        (SOURCE_TYPE_META,),
    ).fetchone()[0]
    print(f"  store total youtube_video: {total_v}")
    print(f"  store total youtube_metadata: {total_m}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
