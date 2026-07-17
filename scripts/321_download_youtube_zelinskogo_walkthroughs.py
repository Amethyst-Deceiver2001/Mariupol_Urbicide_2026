#!/usr/bin/env python3
"""Download 2 YouTube walkthrough/flyover videos of the Зелинского 17А/17Б/
19Б + Бахчиванджи 25/27 demolition cluster (ЖК «Нахимовский», decree №178
-- see docs/case_studies/death_sites_new_construction.md Case 2), flagged
by the user 2026-07-15:

1. wO7FXXmKV7Y (2023-09-20) -- Зелинского walkthrough. At 1:58 the narrator
   points at the green fence around the L-shaped demolished 17А. Other
   addresses appear elsewhere in the video -- next step (scripts/322)
   transcribes the full audio and matches address mentions to timecodes.

2. lQ_Xyu2WWjg (2022-05, contemporary/siege-era) -- camera pan across this
   same cluster. User has already manually annotated the pan at 0:28-0:42:
     0:28 -- left side of L-shaped courtyard of Зелинского 15
     ~0:30 -- destroyed facade of 17Б
     0:32  -- corner of 17А
     0:34  -- brick chimney of боiler house (котельная №5),
              47°05'43.27"N 37°31'05.96"E, #25 visible in background
     ~0:38 -- collapsed corner of 19Б, 47°05'41.77"N 37°31'06.54"E
     0:42  -- camera turns back to 15's courtyard
   This annotation is corroborated by a satellite-image screenshot the user
   attached in chat (not machine-readable here) -- see the case study for
   the full writeup once scripts/322 has extracted stills for side-by-side
   comparison.

Uses yt-dlp (already installed, `pyproject.toml` `media` extra) -- not
geoblocked, but per project convention (memory: user runs long/network
jobs themselves) this is generated for you to run, not auto-executed.

Run:
    .venv312/bin/python scripts/321_download_youtube_zelinskogo_walkthroughs.py

Downloads to the scratchpad, then hashes + captures both into the forensic
raw store (source_type "youtube_video", chain-of-custody sidecar), and
extracts the audio track to .wav for scripts/322's whisper transcription
pass. Idempotent -- skips any video already captured (checked by URL).

Next step once this has run:
    .venv312/bin/python scripts/322_transcribe_and_still_zelinskogo_youtube.py
"""
from __future__ import annotations

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

SCRATCH = Path(
    "/private/tmp/claude-501/-Users-ak-Downloads-mariupol-property-seizures/"
    "342b195a-6008-4b21-a81f-9d63615da8f5/scratchpad"
)
SCRATCH.mkdir(parents=True, exist_ok=True)

SOURCE_TYPE = "youtube_video"

VIDEOS = [
    {
        "id": "wO7FXXmKV7Y",
        "url": "https://www.youtube.com/watch?v=wO7FXXmKV7Y",
        "note": ("Зелинского walkthrough, 2023-09-20. 1:58 -- narrator points "
                 "at green fence around L-shaped demolished 17А. Other "
                 "addresses appear elsewhere in the video; timecoded by "
                 "scripts/322 against a whisper transcript. Cluster: ЖК "
                 "«Нахимовский», decree №178 (see "
                 "docs/case_studies/death_sites_new_construction.md Case 2)."),
    },
    {
        "id": "lQ_Xyu2WWjg",
        "url": "https://www.youtube.com/watch?v=lQ_Xyu2WWjg",
        "note": ("Contemporary/siege-era pan across the same cluster, "
                 "2022-05. User-annotated 0:28-0:42 pan: 15's courtyard -> "
                 "17Б facade -> 17А corner -> boiler house (котельная №5) "
                 "chimney 47°05'43.27\"N 37°31'05.96\"E with #25 visible "
                 "behind -> collapsed 19Б corner 47°05'41.77\"N "
                 "37°31'06.54\"E -> back to 15's courtyard. Corroborated by "
                 "a user-supplied satellite screenshot."),
    },
]


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _ytdlp_download(vid: dict) -> Path | None:
    out_tmpl = str(SCRATCH / f"{vid['id']}.%(ext)s")
    existing = list(SCRATCH.glob(f"{vid['id']}.*"))
    existing = [p for p in existing if p.suffix in (".mp4", ".webm", ".mkv")]
    if existing:
        log.info("already downloaded: %s", existing[0].name)
        return existing[0]
    cmd = [
        "yt-dlp",
        "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "--merge-output-format", "mp4",
        "--write-info-json",
        "-o", out_tmpl,
        vid["url"],
    ]
    log.info("downloading %s ...", vid["url"])
    r = subprocess.run(cmd, cwd=SCRATCH, capture_output=True, text=True)
    if r.returncode != 0:
        log.error("yt-dlp failed for %s:\n%s", vid["url"], r.stderr[-2000:])
        return None
    hits = [p for p in SCRATCH.glob(f"{vid['id']}.*") if p.suffix in (".mp4", ".webm", ".mkv")]
    return hits[0] if hits else None


def _extract_audio(video_path: Path) -> Path:
    wav_path = video_path.with_suffix(".wav")
    if wav_path.exists():
        return wav_path
    cmd = ["ffmpeg", "-y", "-i", str(video_path), "-ac", "1", "-ar", "16000", str(wav_path)]
    log.info("extracting audio -> %s", wav_path.name)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        log.error("ffmpeg audio extraction failed:\n%s", r.stderr[-2000:])
    return wav_path


def _capture(vid: dict, video_path: Path, con) -> None:
    url = vid["url"]
    existing = con.execute(
        "SELECT sha256 FROM source_document WHERE url=? AND source_type=?",
        (url, SOURCE_TYPE),
    ).fetchone()
    if existing:
        log.info("already captured: %s (sha=%s)", url, existing[0][:12])
        return

    info = {}
    info_path = video_path.with_suffix(".info.json")
    if info_path.exists():
        try:
            info = json.loads(info_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    sha = _sha256_file(video_path)
    ext = video_path.suffix or ".mp4"
    raw_path = config.RAW_DIR / f"{sha}{ext}"
    if not raw_path.exists():
        raw_path.write_bytes(video_path.read_bytes())
    else:
        log.info("sha=%s already in raw store, not re-writing bytes", sha[:12])

    captured = forensics.now_iso()
    title = info.get("title") or video_path.name
    meta = {
        "url": url,
        "source_type": SOURCE_TYPE,
        "title": title,
        "description": vid["note"],
        "channel": info.get("channel") or info.get("uploader"),
        "channel_url": info.get("channel_url") or info.get("uploader_url"),
        "upload_date": info.get("upload_date"),
        "duration_seconds": info.get("duration"),
        "sha256": sha,
        "content_type": "video/mp4",
        "http_status": 200,
        "captured_at": captured,
    }
    Path(str(raw_path) + ".meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    con.execute(
        """INSERT OR REPLACE INTO source_document
           (sha256, url, source_type, title, description,
            raw_path, content_type, http_status, captured_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (sha, url, SOURCE_TYPE, title, vid["note"],
         str(raw_path), "video/mp4", 200, captured),
    )
    con.commit()
    log.info("captured %s -> sha=%s", video_path.name, sha[:12])


def main() -> None:
    con = forensics.open_state()
    for vid in VIDEOS:
        video_path = _ytdlp_download(vid)
        if not video_path:
            log.error("skipping %s -- download failed", vid["id"])
            continue
        _capture(vid, video_path, con)
        _extract_audio(video_path)
    con.close()
    log.info("done. Next: .venv312/bin/python scripts/322_transcribe_and_still_zelinskogo_youtube.py")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
