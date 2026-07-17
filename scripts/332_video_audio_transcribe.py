#!/usr/bin/env python3
"""Video/audio transcription — Whisper-transcribe an already-captured video's
speech into the forensic store, with lineage to the source.

The audio complement to scripts/331 (which OCRs the VISUAL channel of a
video): this transcribes the SPOKEN channel. Built for videos where the
evidence is what people SAY — e.g. the Зелинского-cluster protest video
(osint_vk_flagged_post_video), where residents both hold address signs
(→ 331) and speak their grievance/addresses aloud (→ this).

Does NOT capture new video — reads a video ALREADY in the raw store (by sha
or source_type), extracts its audio with ffmpeg, transcribes with OpenAI
Whisper (offline, local — chain-of-custody-safe, nothing leaves the machine,
unlike a cloud STT), and captures the transcript (plain text + timestamped
segments JSON) as derived artifacts with `derived_from` = the source video
sha. Address-shaped mentions in the transcript are flagged for review (same
cue regex as 326/331); nothing is written to the DB or a case study
automatically.

This is a LONGER LOCAL COMPUTE job (Whisper `medium` on CPU is several
minutes for a few-minute clip) — run it yourself; Claude won't execute it.
`medium` is a good Russian-accuracy/speed balance; `large-v3` is more
accurate but much slower; `small` is faster/rougher.

Setup: ffmpeg + openai-whisper (already in .venv312: `pip install openai-whisper`).

Usage:
    PYTHONPATH=src .venv312/bin/python scripts/332_video_audio_transcribe.py \
        --source-type osint_vk_flagged_post_video --model medium --language ru

    # or a specific video by sha
    PYTHONPATH=src .venv312/bin/python scripts/332_video_audio_transcribe.py \
        --sha 188ddb5f2ac83f2ba6a517e63d71f9e9b026d726ea9f6e6e7d9a2c9a5f92e90f
"""
from __future__ import annotations

import argparse
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

# same address cue as scripts/326/331 (kept in sync by hand)
_ADDR_CUE = re.compile(
    r"(ул\.?|вул\.?|улиц|проспект|пр-?кт|пр\.|бульвар|б-р|переул|дом\s|д\.\s*\d)",
    re.IGNORECASE)


def _outdir() -> Path:
    d = config.DATA_DIR / "reports" / "video_transcripts"
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
            "WHERE source_type=? AND (content_type LIKE 'video/%' OR "
            "content_type LIKE 'audio/%' OR raw_path LIKE '%.mp4') "
            "ORDER BY captured_at DESC LIMIT 1", (args.source_type,)).fetchone()
    if not row:
        return None
    return {"sha256": row[0], "raw_path": row[1], "content_type": row[2]}


def _extract_audio(video_path: Path, out_wav: Path) -> None:
    """16kHz mono WAV — Whisper's native input, robust to the source's
    container/extension (our raw store uses .bin regardless of real type)."""
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-i", str(video_path), "-vn", "-ac", "1", "-ar", "16000",
         "-f", "wav", str(out_wav)], check=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sha", help="sha256 of the captured video/audio to transcribe")
    ap.add_argument("--source-type", help="transcribe the newest video of this source_type")
    ap.add_argument("--model", default="medium",
                    help="Whisper model (tiny/base/small/medium/large-v3; default medium)")
    ap.add_argument("--language", default="ru", help="source language (default ru)")
    args = ap.parse_args()

    if not args.sha and not args.source_type:
        log.error("need --sha or --source-type")
        sys.exit(1)

    con = forensics.open_state()
    video = _resolve_video(args, con)
    if not video:
        log.error("no video/audio found for %s", args.sha or args.source_type)
        sys.exit(1)

    raw_path = Path(video["raw_path"])
    if not raw_path.is_absolute():
        raw_path = config.PROJECT_ROOT / raw_path
    if not raw_path.exists():
        log.error("raw file missing on disk: %s", raw_path)
        sys.exit(1)

    try:
        import whisper
    except ImportError:
        log.error("whisper not installed — pip install openai-whisper")
        sys.exit(1)

    log.info("transcribing %s (%s) with Whisper '%s' [lang=%s] — this takes a few minutes",
             video["sha256"][:16], video["content_type"], args.model, args.language)

    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "audio.wav"
        try:
            _extract_audio(raw_path, wav)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            log.error("ffmpeg audio extraction failed (is ffmpeg installed?): %s", e)
            con.close()
            sys.exit(1)

        model = whisper.load_model(args.model)
        result = model.transcribe(str(wav), language=args.language, verbose=False)

    text = (result.get("text") or "").strip()
    segments = [{"start": round(s["start"], 2), "end": round(s["end"], 2),
                 "text": s["text"].strip()} for s in result.get("segments", [])]

    # capture transcript (plain text) + timestamped segments, lineage to video
    forensics.capture_derived(
        text.encode("utf-8"), derived_from=video["sha256"],
        transform=f"whisper_{args.model}_transcribe_{args.language}",
        source_type="osint_video_transcript",
        title=f"transcript {video['sha256'][:12]}",
        description=(f"Whisper '{args.model}' transcript of video "
                     f"{video['sha256'][:16]} ({args.language})."),
        content_type="text/plain", con=con,
    )
    forensics.capture_derived(
        json.dumps({"video_sha256": video["sha256"], "language": args.language,
                    "model": args.model, "segments": segments},
                   ensure_ascii=False).encode("utf-8"),
        derived_from=video["sha256"],
        transform=f"whisper_{args.model}_segments_{args.language}",
        source_type="osint_video_transcript_segments",
        title=f"transcript segments {video['sha256'][:12]}",
        description=(f"Timestamped Whisper segments for video "
                     f"{video['sha256'][:16]}."),
        content_type="application/json", con=con,
    )

    # write a human-readable copy + flag address mentions
    addr_segs = [s for s in segments if _ADDR_CUE.search(s["text"])]
    slug = args.sha[:12] if args.sha else args.source_type
    out_txt = _outdir() / f"{slug}.txt"
    out_txt.write_text(text + "\n", encoding="utf-8")

    print(f"\n{'='*72}\nTRANSCRIPT — video {video['sha256'][:16]} "
          f"(Whisper {args.model}, {args.language})\n{'='*72}")
    print(text)
    print(f"{'='*72}")
    if addr_segs:
        print(f"\n{len(addr_segs)} segment(s) with an address cue (review):")
        for s in addr_segs:
            print(f"  [{s['start']:>6.0f}s] {s['text']}")
    print(f"\ntranscript captured (osint_video_transcript, lineage -> "
          f"{video['sha256'][:12]}); text copy: {out_txt}")
    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
