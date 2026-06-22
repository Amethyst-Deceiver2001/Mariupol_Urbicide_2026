#!/usr/bin/env python3
"""Capture YouTube videos as forensic evidence for the пр. Ленина
104/106/108/110 restoration-without-restitution case study (and general use).

Same capture-before-parse discipline as the rest of the pipeline (CLAUDE.md
NON-NEGOTIABLE rules): downloads the video with yt-dlp, hashes the actual
downloaded bytes (streamed, not loaded fully into memory -- videos can be
large), writes it to data/raw/<sha256>.<ext> with a .meta.json sidecar, and
registers it in source_document (forensics.open_state()) exactly like every
other captured artifact in this project.

This is a network-heavy, long-running job (video downloads) -- per project
convention the user runs it themselves, not Claude. See
memory/feedback_user_runs_long_scripts.md if using Claude Code.

Requires the system yt-dlp binary (already on this machine via Homebrew).

Usage:
    .venv312/bin/python scripts/157_capture_youtube_evidence.py
"""
import hashlib
import json
import logging
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

# URLs supplied by the user 2026-06-19 as candidate visual evidence for the
# Ленина 104/106/108/110 case study. "note" is the user's own characterization
# at hand-off -- NOT verified by Claude; verify by watching the captured file
# before citing in the case study (same caution as the Telegram media review).
TARGETS = [
    {"url": "https://www.youtube.com/watch?v=0ryoGHihIaY", "note": None},
    {"url": "https://youtube.com/shorts/Bzq5QnarNAo", "note":
        "user: shows demolition works at пр. Ленина 108 (property_id 4421) -- "
        "decree №56 (29.09.2022) is on record for this building but our case "
        "study documents it as restored, not razed; if this video genuinely "
        "shows demolition it may revise that finding, needs careful review"},
    {"url": "https://www.youtube.com/watch?v=oPTXL9Gluq0", "note": None},
    {"url": "https://www.youtube.com/watch?v=QBS9qOT-_RM", "note": None},
    {"url": "https://www.youtube.com/shorts/S0HfD_lkeEk", "note": None},
    {"url": "https://www.youtube.com/shorts/5fuqt-M5S6I", "note": None},
    {"url": "https://www.youtube.com/watch?v=pmb7BIl-Atw", "note": None},
    {"url": "https://www.youtube.com/watch?v=JHN1KrWgliE", "note":
        "user 2026-06-19: shows the whole пр. Ленина 104/106/108/110 stretch "
        "mid-reconstruction"},
    {"url": "https://www.youtube.com/watch?v=iDKIvw-2q_c", "note":
        "user 2026-06-19: 'more contemporary destruction footage'"},
    {"url": "https://www.youtube.com/watch?v=CHrEXXI8CK0", "note":
        "user 2026-06-19: 'reference/corroboration of residents' complaints'. "
        "Transcript (auto-captions, Russian): residents of пр. Ленина "
        "104/106/108/110 address camera directly, naming the same contractor "
        "chain already in stakeholder_network/the case study -- ППК «Единый "
        "заказчик», ФКР Московской области (ФКРМО), РКС-НР, департамент "
        "капстроительства г. Мариуполя, администрация МО ГО Мариуполь. Claims: "
        "facade work done but interiors in 'complete ruin', work HALTED with no "
        "explanation, new subcontractors brought in repeatedly but do nothing, "
        "ground-floor commercial units ALREADY occupied by a bank/flower shop/"
        "pelmennaya while residents can't access their own apartments, "
        "'квадратура изменилась' (apartment square footage/wall layout altered "
        "during works), residents in 4th year without housing, signatures "
        "collected and formal complaints sent to Следственный комитет РФ, "
        "Администрация президента РФ, Прокуратура РФ, прокуратура Мариуполя, "
        "администрация ГО Мариуполь, департамент строительного управления. "
        "Verify by watching before citing -- same caution as all other "
        "user-supplied videos in this project."},
    {"url": "https://www.youtube.com/watch?v=fzN0pI8alEY", "note":
        "user 2026-06-19: 'contemporary footage of destruction and damage, "
        "specifically 104 and 106 from inside the courtyard'. Would be the "
        "second confirmed wartime-destruction source for 104/106 (after "
        "iDKIvw-2q_c) and the first from the courtyard/rear side rather than "
        "the street facade -- verify by watching before citing."},
]


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def capture_one(url: str, note: str | None, con) -> None:
    log.info("downloading %s", url)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        out_tmpl = str(tmp_path / "%(id)s.%(ext)s")
        result = subprocess.run(
            ["yt-dlp", "--no-playlist", "--write-info-json",
             "-f", "bv*+ba/b", "--merge-output-format", "mp4",
             "-o", out_tmpl, url],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            log.error("yt-dlp failed for %s:\n%s", url, result.stderr[-2000:])
            return

        video_files = [p for p in tmp_path.iterdir()
                        if p.suffix not in (".json", ".part")]
        info_files = list(tmp_path.glob("*.info.json"))
        if not video_files or not info_files:
            log.error("missing video or info.json for %s after download", url)
            return
        video_path = video_files[0]
        info = json.loads(info_files[0].read_text(encoding="utf-8"))

        sha = _sha256_file(video_path)
        ext = video_path.suffix or ".mp4"
        raw_path = config.RAW_DIR / f"{sha}{ext}"
        if not raw_path.exists():
            raw_path.write_bytes(video_path.read_bytes())
        else:
            log.info("sha=%s already in raw store, not re-writing bytes", sha[:12])

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
    for t in TARGETS:
        capture_one(t["url"], t["note"], con)
    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
