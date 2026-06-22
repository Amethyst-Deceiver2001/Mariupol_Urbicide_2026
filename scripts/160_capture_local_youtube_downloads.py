#!/usr/bin/env python3
"""Register already-downloaded YouTube videos into the raw store.

The user downloaded CHrEXXI8CK0 (resident testimony to camera) and fzN0pI8alEY
(104/106 courtyard siege-damage footage) to /tmp via yt-dlp directly, ahead of
this script, for manual frame review (see memory/lenina106_*). This script
does NOT re-download the video bytes (that already happened, no network
needed for them) -- it only hashes the local file into data/raw/ + a
.meta.json sidecar and registers it in source_document, then fetches just the
lightweight --skip-download metadata (title/description/channel/upload_date)
to fill out that record. Same capture-before-parse discipline as the rest of
the pipeline; the only difference from scripts/157 is the video bytes are
read from /tmp instead of downloaded fresh.

Usage:
    .venv312/bin/python scripts/160_capture_local_youtube_downloads.py
"""
import hashlib
import json
import logging
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

LOCAL_VIDEOS = [
    {"url": "https://www.youtube.com/watch?v=CHrEXXI8CK0",
     "local_path": "/tmp/CHrEXXI8CK0.mp4",
     "note": "user 2026-06-19: resident testimony to camera, "
             "пр. Ленина 104/106/108/110 -- see scripts/157 TARGETS for the "
             "full transcript summary."},
    {"url": "https://www.youtube.com/watch?v=fzN0pI8alEY",
     "local_path": "/tmp/fzN0pI8alEY.mp4",
     "note": "user 2026-06-19: contemporary courtyard siege-damage footage, "
             "104 (0:10-0:20, 0:43-1:02), makeshift brick kitchen (3:39), "
             "106 (4:02-4:21)."},
]


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def capture_one(url: str, local_path: str, note: str, con) -> None:
    src = Path(local_path)
    if not src.exists():
        log.error("local file not found: %s -- skipping %s", local_path, url)
        return

    sha = _sha256_file(src)
    raw_path = config.RAW_DIR / f"{sha}.mp4"
    if not raw_path.exists():
        raw_path.write_bytes(src.read_bytes())
    else:
        log.info("sha=%s already in raw store, not re-writing bytes", sha[:12])

    # Lightweight metadata-only fetch (no video re-download).
    info = {}
    result = subprocess.run(
        ["yt-dlp", "--no-playlist", "--skip-download", "--print-json", url],
        capture_output=True, text=True,
    )
    if result.returncode == 0 and result.stdout.strip():
        info = json.loads(result.stdout.strip().splitlines()[-1])
    else:
        log.warning("yt-dlp metadata fetch failed for %s:\n%s", url, result.stderr[-1000:])

    captured = forensics.now_iso()
    meta = {
        "url": url,
        "source_type": "youtube_video",
        "title": info.get("title"),
        "description": info.get("description"),
        "channel": info.get("channel") or info.get("uploader"),
        "channel_url": info.get("channel_url") or info.get("uploader_url"),
        "upload_date": info.get("upload_date"),
        "duration_seconds": info.get("duration"),
        "sha256": sha,
        "content_type": "video/mp4",
        "http_status": 200,
        "captured_at": captured,
        "user_note_at_handoff": note,
    }
    Path(str(raw_path) + ".meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    con.execute(
        """INSERT OR REPLACE INTO source_document
           (sha256, url, source_type, title, description,
            raw_path, content_type, http_status, captured_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (sha, url, "youtube_video", info.get("title"), info.get("description"),
         str(raw_path), "video/mp4", 200, captured),
    )
    con.commit()
    log.info("captured %s -> %s (sha=%s)", url, raw_path.name, sha[:12])


def main() -> None:
    con = forensics.open_state()
    for v in LOCAL_VIDEOS:
        capture_one(v["url"], v["local_path"], v["note"], con)
    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
