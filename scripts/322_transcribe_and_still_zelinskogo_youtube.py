#!/usr/bin/env python3
"""Second half of the wO7FXXmKV7Y / lQ_Xyu2WWjg pipeline (scripts/321
downloaded + captured both videos into the raw store and extracted audio).

For each video:
  1. Whisper-transcribe the audio (Russian, "medium" model -- same choice
     as scripts/284, for better accuracy on place names/numbers than
     "small"), writing both a plain transcript and a timestamped-segment
     file (data/parsed/<id>_transcript.txt / _segments.txt).
  2. Regex-scan every segment for a mention of Зелинского / Бахчиванджи /
     Нахимовск(ий) (+ nearby house numbers), writing
     data/parsed/<id>_address_timecodes.csv -- a timecode index of every
     address mention, for cross-reference against the crosswalk in
     scripts/164_export_map_layers.py.
  3. Extract a still frame (ffmpeg) at every KNOWN_TIMECODES entry (the
     specific moments already identified -- 1:58 for wO7FXXmKV7Y's green
     fence, and the user's 0:28-0:42 annotated pan for lQ_Xyu2WWjg) AND at
     every additional address-mention timecode step 2 found, deduped to
     one still per ~3-second window. Stills land in
     data/parsed/stills/<video_id>/<mmss>.jpg and are registered as
     DERIVED artifacts (forensics.capture_derived, derived_from the
     video's own sha) -- consistent with this project's forensic rule that
     a transformation must log its lineage, not just the source video.

This is CPU-bound (whisper "medium" transcription of two videos) --
per project convention, generated for you to run in your own terminal,
not launched by Claude as a background task.

Run:
    .venv312/bin/python scripts/322_transcribe_and_still_zelinskogo_youtube.py

Requires scripts/321 to have already downloaded + captured both videos.
Idempotent -- skips a video's transcript/stills if already present.
"""
from __future__ import annotations

import csv
import json
import logging
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import forensics  # noqa: E402

log = logging.getLogger(__name__)

SCRATCH = Path(
    "/private/tmp/claude-501/-Users-ak-Downloads-mariupol-property-seizures/"
    "342b195a-6008-4b21-a81f-9d63615da8f5/scratchpad"
)
PARSED_DIR = ROOT / "data" / "parsed"
STILLS_DIR = PARSED_DIR / "stills"
PARSED_DIR.mkdir(parents=True, exist_ok=True)

SOURCE_TYPE_VIDEO = "youtube_video"
WHISPER_MODEL = "medium"

# fixed timecodes already identified by direct review -- always extracted
# regardless of what the transcript turns up (seconds).
KNOWN_TIMECODES = {
    "wO7FXXmKV7Y": [
        (118, "narrator points at green fence around L-shaped demolished 17А"),
    ],
    "lQ_Xyu2WWjg": [
        (28, "left side of L-shaped courtyard of Зелинского 15"),
        (30, "destroyed facade of 17Б"),
        (32, "corner of 17А"),
        (34, "brick chimney of boiler house (котельная №5), "
             "47°05'43.27\"N 37°31'05.96\"E, #25 visible in background"),
        (38, "collapsed corner of 19Б, 47°05'41.77\"N 37°31'06.54\"E"),
        (42, "camera turns back to 15's courtyard"),
    ],
}

VIDEO_IDS = ["wO7FXXmKV7Y", "lQ_Xyu2WWjg"]

ADDRESS_RX = re.compile(
    r"(Зелинск\w*|Бахчиванджи\w*|Нахимовск\w*)[^.\n]{0,40}?"
    r"(\d{1,3}\s*[АБВабв]?)?", re.I,
)


def _video_path_and_sha(vid_id: str, con):
    row = con.execute(
        "SELECT sha256, raw_path FROM source_document "
        "WHERE source_type=? AND url LIKE ?",
        (SOURCE_TYPE_VIDEO, f"%{vid_id}%"),
    ).fetchone()
    return row  # (sha256, raw_path) or None


def _fmt_ts(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}m{s:02d}s"


def transcribe(vid_id: str, wav_path: Path, model) -> list[dict]:
    transcript_path = PARSED_DIR / f"{vid_id}_transcript.txt"
    segments_path = PARSED_DIR / f"{vid_id}_segments.txt"
    segments_json = PARSED_DIR / f"{vid_id}_segments.json"

    if segments_json.exists():
        log.info("%s: transcript already exists, loading cached segments", vid_id)
        return json.loads(segments_json.read_text(encoding="utf-8"))

    if not wav_path.exists():
        log.error("%s: missing audio %s -- run scripts/321 first", vid_id, wav_path)
        return []

    log.info("%s: transcribing (whisper %s, this can take several minutes)...",
             vid_id, WHISPER_MODEL)
    result = model.transcribe(str(wav_path), language="ru", verbose=False)
    transcript_path.write_text(result["text"], encoding="utf-8")

    segments = result["segments"]
    with segments_path.open("w", encoding="utf-8") as fh:
        for seg in segments:
            fh.write(f"[{seg['start']:8.1f} -> {seg['end']:8.1f}] {seg['text'].strip()}\n")
    segments_json.write_text(
        json.dumps([{"start": s["start"], "end": s["end"], "text": s["text"]}
                   for s in segments], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log.info("%s: wrote transcript (%d chars, %d segments)",
             vid_id, len(result["text"]), len(segments))
    return [{"start": s["start"], "end": s["end"], "text": s["text"]} for s in segments]


def find_address_timecodes(vid_id: str, segments: list[dict]) -> list[dict]:
    hits = []
    for seg in segments:
        text = seg["text"]
        for m in ADDRESS_RX.finditer(text):
            street = m.group(1)
            house = (m.group(2) or "").strip()
            hits.append({
                "start": seg["start"], "end": seg["end"],
                "timecode": _fmt_ts(seg["start"]),
                "street": street, "house": house,
                "text": text.strip(),
            })
    out_csv = PARSED_DIR / f"{vid_id}_address_timecodes.csv"
    with out_csv.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["timecode", "start", "end", "street", "house", "text"])
        w.writeheader()
        for h in hits:
            w.writerow(h)
    log.info("%s: %d address-mention segments -> %s", vid_id, len(hits), out_csv)
    return hits


def extract_stills(vid_id: str, video_path: Path, sha: str, known: list[tuple],
                    address_hits: list[dict], con) -> None:
    out_dir = STILLS_DIR / vid_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # merge known timecodes + address-hit timecodes, dedup within 3s windows
    points: list[tuple[float, str]] = [(float(t), note) for t, note in known]
    for h in address_hits:
        points.append((h["start"], f"transcript mention: {h['street']} {h['house']} "
                                    f"— \"{h['text'][:80]}\""))
    points.sort(key=lambda p: p[0])
    deduped: list[tuple[float, str]] = []
    for t, note in points:
        if deduped and abs(t - deduped[-1][0]) < 3.0:
            continue
        deduped.append((t, note))

    for t, note in deduped:
        ts = _fmt_ts(t)
        still_path = out_dir / f"{ts}.jpg"
        if still_path.exists():
            continue
        cmd = ["ffmpeg", "-y", "-ss", str(t), "-i", str(video_path),
               "-frames:v", "1", "-q:v", "2", str(still_path)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0 or not still_path.exists():
            log.warning("%s: still extraction failed at %s:\n%s", vid_id, ts, r.stderr[-800:])
            continue
        blob = still_path.read_bytes()
        forensics.capture_derived(
            blob,
            derived_from=sha,
            transform=f"ffmpeg -ss {t} -frames:v 1 (frame extraction)",
            source_type="youtube_video_still",
            title=f"{vid_id} still @ {ts}",
            description=f"{note} ({vid_id}, {ts})",
            content_type="image/jpeg",
            con=con,
        )
        log.info("%s: still @ %s -> %s (%s)", vid_id, ts, still_path.name, note[:60])


def main() -> None:
    con = forensics.open_state()

    import whisper  # deferred import -- slow to load
    log.info("loading whisper model: %s", WHISPER_MODEL)
    model = whisper.load_model(WHISPER_MODEL)

    for vid_id in VIDEO_IDS:
        row = _video_path_and_sha(vid_id, con)
        if not row:
            log.error("%s: not found in source_document -- run scripts/321 first", vid_id)
            continue
        sha, raw_path = row
        video_path = Path(raw_path)
        wav_path = None
        for cand in SCRATCH.glob(f"{vid_id}.*"):
            if cand.suffix == ".wav":
                wav_path = cand
        if wav_path is None:
            log.error("%s: no extracted audio found in scratchpad -- run scripts/321 first", vid_id)
            continue

        segments = transcribe(vid_id, wav_path, model)
        address_hits = find_address_timecodes(vid_id, segments)
        extract_stills(vid_id, video_path, sha, KNOWN_TIMECODES.get(vid_id, []),
                       address_hits, con)

    con.close()
    log.info("done. Review data/parsed/*_transcript.txt, *_address_timecodes.csv, "
             "and data/parsed/stills/<video_id>/ -- then tell Claude so findings "
             "can be folded into docs/case_studies/death_sites_new_construction.md.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
