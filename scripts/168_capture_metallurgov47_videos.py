#!/usr/bin/env python3
"""Register the Metallurgov-47 video evidence (already downloaded this
session via yt-dlp into the scratchpad, plus the user-supplied Telegram
video) into the forensic raw store, following the same capture-before-parse
discipline as scripts/157.

Inputs are local files already on disk -- this script only hashes and
copies them into data/raw/ with .meta.json sidecars and a source_document
row. No network calls. Safe to run directly.

Usage:
    .venv312/bin/python scripts/168_capture_metallurgov47_videos.py
"""
import hashlib
import json
import logging
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

TARGETS = [
    {
        "path": SCRATCH / "r52lcv5MhPw.webm",
        "info_json": SCRATCH / "r52lcv5MhPw_info.info.json",
        "url": "https://www.youtube.com/watch?v=r52lcv5MhPw",
        "source_type": "youtube_video",
        "note": "Silent/music-only demolition footage, ~2m13s. Visually consistent "
                "with Dec 2022 demolition window. Uploader title credits contractor "
                "'ГК «КрашМаш»' -- this is an UNVERIFIED uploader label, not "
                "on-screen text (checked via frame extraction, no captions visible "
                "in footage). Conflicts with court-testimony contractor name "
                "'Северный ветер' from E6SNZt0RjpQ -- unresolved discrepancy, "
                "possibly subcontractor vs. paper-contract holder, or one source "
                "is simply wrong.",
        "content_type": "video/webm",
    },
    {
        "path": SCRATCH / "E6SNZt0RjpQ.mp4",
        "info_json": SCRATCH / "E6SNZt0RjpQ.info.json",
        "url": "https://www.youtube.com/watch?v=E6SNZt0RjpQ",
        "source_type": "youtube_video",
        "note": "Resident (apparently the building's case representative) "
                "addressing camera, 15.06.2025, ~16.5 min. Auto-caption transcript "
                "(RU) extracted and reviewed in full -- see "
                "docs/case_studies/troianda_m_demolition_challenge.md for the "
                "summarized claims (Sept 2023 'address annulled' notice; "
                "demolition contractor 'Северный ветер' physically demolished "
                "10-25.12.2022 per resident video evidence; PPK «Единый заказчик» "
                "/ RKS-NR demolition CONTRACT dated 27.12.2024 -- two years after "
                "physical demolition, ~103 million RUB; internally inconsistent "
                "dates in Severny Veter's own project documentation; competing "
                "unsigned technical reports from 'Профессиональные экспертные "
                "технологии' and 'СтройТех-21'; named official Олег Валерьевич "
                "Баргун never answered resettlement queries; 55 families/127 "
                "people affected, only 10 households resident at demolition "
                "time). Self-disclosed as an open judicial proceeding under "
                "Russian law -- speaker states she is permitted to disclose case "
                "documents.",
        "content_type": "video/mp4",
    },
    {
        "path": Path("/Users/ak/Downloads/video_2025-03-03_13-52-43.mp4"),
        "info_json": None,
        "url": None,
        "source_type": "telegram_video_user_supplied",
        "note": "User-supplied video (provenance: downloaded from Telegram by the "
                "user, exact channel/post not given). Whisper (small model, ru) "
                "transcript: multiple residents address camera identifying as "
                "пр. Металлургов 47 residents -- named speaker Блуховцова Мария "
                "Александровна (two children, ages 6 and 9); one unnamed speaker, "
                "apt. 116, disability group 2. Explicit appeal 'к русской общине "
                "и Следственному комитету России' -- almost certainly the source "
                "footage behind the @allmarinews/21995 Telegram post captured in "
                "scripts/167. Quote: 'Полное беззаконие идёт. Нарушение прав "
                "человека в угоду бизнесу.' Full transcript in "
                "docs/case_studies/troianda_m_demolition_challenge.md.",
        "content_type": "video/mp4",
    },
]


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def capture_one(t: dict, con) -> None:
    path = t["path"]
    if not path.exists():
        log.warning("missing file, skip: %s", path)
        return
    info = {}
    if t["info_json"] and t["info_json"].exists():
        info = json.loads(t["info_json"].read_text(encoding="utf-8"))

    sha = _sha256_file(path)
    ext = path.suffix or ".mp4"
    raw_path = config.RAW_DIR / f"{sha}{ext}"
    if not raw_path.exists():
        raw_path.write_bytes(path.read_bytes())
    else:
        log.info("sha=%s already in raw store, not re-writing bytes", sha[:12])

    captured = forensics.now_iso()
    title = info.get("title") or path.name
    description = t["note"]
    meta = {
        "url": t["url"] or f"local:{path}",
        "source_type": t["source_type"],
        "title": title,
        "description": description,
        "channel": info.get("channel") or info.get("uploader"),
        "channel_url": info.get("channel_url") or info.get("uploader_url"),
        "upload_date": info.get("upload_date"),
        "duration_seconds": info.get("duration"),
        "sha256": sha,
        "content_type": t["content_type"],
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
        (sha, meta["url"], t["source_type"], title, description,
         str(raw_path), t["content_type"], 200, captured),
    )
    con.commit()
    log.info("captured %s -> %s (sha=%s)", path.name, raw_path.name, sha[:12])


def main() -> None:
    con = forensics.open_state()
    for t in TARGETS:
        capture_one(t, con)
    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
