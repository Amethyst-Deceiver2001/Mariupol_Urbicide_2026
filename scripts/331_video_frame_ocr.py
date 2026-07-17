#!/usr/bin/env python3
"""Video frame-OCR triage — sample frames from an already-captured video,
Rekognition-OCR each, and surface every address/text sign across the clip.

Built for the case where evidence is spoken/shown IN a video rather than in
a still: e.g. the Зелинского-cluster "Обращение к Президенту" protest video
(captured 2026-07-16, source_type osint_vk_flagged_post_video) where
residents hold up hand-written signs with their building addresses — one
still frame already showed ~8 addresses; sampling the whole clip catches the
rest as different people's signs come into view.

Does NOT capture new video — it reads a video ALREADY in the raw store (by
sha or source_type), samples frames with ffmpeg, runs AWS Rekognition
DetectText on each, dedups detected lines across frames, and writes a review
CSV. To keep the raw store lean (project resource envelope), only frames that
yielded an address/паспорт/text-of-interest hit are captured back as derived
artifacts (with lineage to the source video sha); plain non-hit samples are
discarded — they're reproducible from the video sha, which IS in the store.
The aggregate per-frame OCR result JSON is always captured (lineage to video).

Nothing here writes to the DB or a case study automatically — same rule as
scripts/326: OCR text is a lead for a human to verify, not claim-grade
evidence on its own.

Setup: needs ffmpeg (brew install ffmpeg) + boto3/.env AWS keys (see
scripts/326 / docs/address_osint_assistant_design.md). Rekognition DetectText
free tier = 5,000 images/month for the account's first 12 months; each
sampled frame = 1 unit, so --max-frames is the cost guardrail.

Usage:
    # OCR every ~3s across a specific captured video
    PYTHONPATH=src .venv312/bin/python scripts/331_video_frame_ocr.py \
        --sha 188ddb5f2ac83f2ba6a517e63d71f9e9b026d726ea9f6e6e7d9a2c9a5f92e90f

    # or target the newest video of a source_type
    PYTHONPATH=src .venv312/bin/python scripts/331_video_frame_ocr.py \
        --source-type osint_vk_flagged_post_video

    # scope/cost check only, no ffmpeg, no API calls
    PYTHONPATH=src .venv312/bin/python scripts/331_video_frame_ocr.py \
        --source-type osint_vk_flagged_post_video --dry-run
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

# reuse the same address/паспорт cues as scripts/326 (kept in sync by hand)
_ADDR_CUE = re.compile(
    r"(ул\.?|вул\.?|улиц|проспект|пр-?кт|пр\.|бульвар|б-р|переул)", re.IGNORECASE)
_HOUSE_NO = re.compile(r"\b\d{1,4}[а-яА-Яa-zA-Z]?\b")
_PASPORT_CUE = re.compile(r"паспорт\s*об[ъь]?ект", re.IGNORECASE)


def _outdir() -> Path:
    d = config.DATA_DIR / "reports" / "video_frame_ocr"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _resolve_video(args, con) -> dict | None:
    if args.sha:
        row = con.execute(
            "SELECT sha256, raw_path, content_type FROM source_document WHERE sha256=?",
            (args.sha,)).fetchone()
    else:
        row = con.execute(
            "SELECT sha256, raw_path, content_type FROM source_document "
            "WHERE source_type=? AND (content_type LIKE 'video/%' OR raw_path LIKE '%.mp4') "
            "ORDER BY captured_at DESC LIMIT 1", (args.source_type,)).fetchone()
    if not row:
        return None
    return {"sha256": row[0], "raw_path": row[1], "content_type": row[2]}


def _extract_frames(video_path: Path, interval_s: float, max_frames: int,
                    out_dir: Path) -> list[tuple[Path, float]]:
    """Sample 1 frame per interval_s seconds via ffmpeg (single pass). Returns
    [(frame_path, approx_timestamp_s), ...] capped at max_frames."""
    pattern = str(out_dir / "frame_%04d.jpg")
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(video_path),
           "-vf", f"fps=1/{interval_s}", "-frames:v", str(max_frames),
           "-q:v", "3", pattern]
    subprocess.run(cmd, check=True)
    frames = sorted(out_dir.glob("frame_*.jpg"))
    return [(f, i * interval_s) for i, f in enumerate(frames)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sha", help="sha256 of the captured video to OCR")
    ap.add_argument("--source-type", help="OCR the newest video of this raw source_type")
    ap.add_argument("--interval-s", type=float, default=3.0,
                    help="sample one frame per N seconds (default 3)")
    ap.add_argument("--max-frames", type=int, default=60,
                    help="cost guardrail: max frames sent to Rekognition (default 60)")
    ap.add_argument("--min-confidence", type=float, default=60.0,
                    help="Rekognition text confidence threshold (default 60)")
    ap.add_argument("--dry-run", action="store_true",
                    help="show scope + estimated cost, no ffmpeg/API calls")
    ap.add_argument("--region", default=None, help="override AWS_DEFAULT_REGION")
    args = ap.parse_args()

    if not args.sha and not args.source_type:
        log.error("need --sha or --source-type")
        sys.exit(1)

    con = forensics.open_state()
    video = _resolve_video(args, con)
    if not video:
        log.error("no video found for %s", args.sha or args.source_type)
        sys.exit(1)

    raw_path = Path(video["raw_path"])
    if not raw_path.is_absolute():
        raw_path = config.PROJECT_ROOT / raw_path

    n_est = args.max_frames
    print(f"\n{'='*72}\nVideo frame-OCR triage")
    print(f"  video sha: {video['sha256'][:16]}  ({video['content_type']})")
    print(f"  raw file : {raw_path}")
    print(f"  sampling : 1 frame / {args.interval_s}s, up to {args.max_frames} frames")
    print(f"  API calls: up to {n_est} (DetectText per frame)")
    print(f"  free tier: 5,000/month for account's first 12 months\n{'='*72}")

    if args.dry_run:
        print("\n-- dry run, no ffmpeg/API calls made --")
        con.close()
        return
    if not raw_path.exists():
        log.error("raw file missing on disk: %s", raw_path)
        sys.exit(1)

    try:
        import boto3
    except ImportError:
        log.error("boto3 not installed — pip install -e '.[aws]'")
        sys.exit(1)
    kwargs = {"region_name": args.region} if args.region else {}
    rekognition = boto3.client("rekognition", **kwargs)

    # all detected lines across all frames, deduped by normalized text
    line_index: dict[str, dict] = {}
    all_frame_results: list[dict] = []
    n_frames_ocrd = n_hit_frames = 0

    with tempfile.TemporaryDirectory(dir=config.SCRATCH_DIR if hasattr(config, "SCRATCH_DIR")
                                     else None) as tmp:
        tmp_dir = Path(tmp)
        try:
            frames = _extract_frames(raw_path, args.interval_s, args.max_frames, tmp_dir)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            log.error("ffmpeg frame extraction failed (is ffmpeg installed?): %s", e)
            con.close()
            sys.exit(1)
        print(f"extracted {len(frames)} frames\n")

        for frame_path, ts in frames:
            img_bytes = frame_path.read_bytes()
            try:
                resp = rekognition.detect_text(Image={"Bytes": img_bytes})
            except Exception as e:  # noqa: BLE001
                log.warning("rekognition failed at t=%.0fs: %s", ts, e)
                continue
            n_frames_ocrd += 1
            lines = [d for d in resp.get("TextDetections", [])
                     if d.get("Type") == "LINE"
                     and d.get("Confidence", 0) >= args.min_confidence]
            frame_hit = False
            for d in lines:
                txt = d["DetectedText"].strip()
                if not txt:
                    continue
                is_addr = bool(_ADDR_CUE.search(txt) or
                               (_HOUSE_NO.search(txt) and len(txt) < 40))
                is_pasp = bool(_PASPORT_CUE.search(txt))
                key = re.sub(r"\s+", " ", txt.lower())
                rec = line_index.setdefault(key, {
                    "text": txt, "is_address": is_addr, "is_pasport": is_pasp,
                    "first_ts": ts, "frames": 0, "max_confidence": 0.0})
                rec["frames"] += 1
                rec["max_confidence"] = max(rec["max_confidence"], d.get("Confidence", 0))
                if is_addr or is_pasp:
                    frame_hit = True
            all_frame_results.append({"t": ts, "n_lines": len(lines)})

            if frame_hit:
                n_hit_frames += 1
                # capture ONLY evidence-bearing frames (lineage to video sha)
                forensics.capture_derived(
                    img_bytes, derived_from=video["sha256"],
                    transform=f"ffmpeg_frame@{ts:.0f}s",
                    source_type="osint_video_evidence_frame",
                    title=f"video frame t={ts:.0f}s {video['sha256'][:12]}",
                    description=(f"Frame at t={ts:.0f}s of video "
                                 f"{video['sha256'][:16]} — contained address/"
                                 f"паспорт text (see video_frame_ocr CSV)."),
                    content_type="image/jpeg", con=con,
                )
            print(f"  t={ts:6.0f}s  {len(lines):2d} lines"
                  f"{'  <-- address/паспорт hit' if frame_hit else ''}")

    # aggregate OCR result JSON (lineage to video), always captured
    forensics.capture_derived(
        json.dumps({"video_sha256": video["sha256"],
                    "frames": all_frame_results,
                    "lines": list(line_index.values())},
                   ensure_ascii=False, default=str).encode("utf-8"),
        derived_from=video["sha256"], transform="video_frame_ocr_aggregate",
        source_type="osint_video_ocr_result",
        title=f"video frame-OCR {video['sha256'][:12]}",
        description=(f"Aggregate Rekognition DetectText over {n_frames_ocrd} "
                     f"sampled frames of video {video['sha256'][:16]}."),
        content_type="application/json", con=con,
    )

    rows = sorted(line_index.values(),
                  key=lambda r: (not (r["is_address"] or r["is_pasport"]),
                                 -r["max_confidence"]))
    slug = args.sha[:12] if args.sha else args.source_type
    out_csv = _outdir() / f"{slug}.csv"
    with out_csv.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["text", "is_address", "is_pasport",
                                           "first_ts", "frames", "max_confidence"])
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in
                        ["text", "is_address", "is_pasport", "first_ts",
                         "frames", "max_confidence"]})

    n_addr = sum(1 for r in rows if r["is_address"])
    n_pasp = sum(1 for r in rows if r["is_pasport"])
    print(f"\ndone — {n_frames_ocrd} frames OCR'd, {n_hit_frames} evidence frames captured")
    print(f"       {len(rows)} unique text lines ({n_addr} address-shaped, "
          f"{n_pasp} паспорт-объекта)")
    print(f"review CSV: {out_csv}")
    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
