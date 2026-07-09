#!/usr/bin/env python3
"""Hash both downloaded videos into the forensic raw store, then transcribe
each with whisper (Russian), following the same capture-before-parse
discipline as scripts/168.

Inputs (already downloaded to the scratchpad via scripts/283):
  1. morgun_9992.mp4       -- Олег Моргун Q&A livestream (@morgun_ov/9992,
                               45:47), inventory-procedure walkthrough.
  2. allmarinews_39282.mp4 -- Игнат Яремчук briefing (@allmarinews/39282,
                               37:29), chaptered legal-mechanism walkthrough.

Whisper's "medium" model is used for better Russian accuracy than "small"
(the model already used for the Металлургов-47 video, scripts/168) --
these are long-form, information-dense monologues/dialogues where
transcription errors on legal terms and numbers matter a lot. This is
CPU/GPU-bound and can take a while for the 45-minute file; run from your
own terminal, not inside a blocking assistant turn.

Usage:
    .venv312/bin/python scripts/284_transcribe_morgun_yaremchuk_videos.py

Writes transcripts to:
    data/parsed/morgun_9992_transcript.txt
    data/parsed/allmarinews_39282_transcript.txt
and registers both source videos (not the transcripts) in the raw store
with a sha256-keyed .meta.json sidecar, consistent with forensic
chain-of-custody rules (transcripts are a derived artifact, not the
evidence itself -- the video's own hash is what matters for provenance).
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

PARSED_DIR = ROOT / "data" / "parsed"
PARSED_DIR.mkdir(parents=True, exist_ok=True)

TARGETS = [
    {
        "path": SCRATCH / "morgun_9992.mp4",
        "url": "https://t.me/morgun_ov/9992",
        "title": "Олег Моргун Q&A livestream (@morgun_ov/9992, 45:47) -- "
                 "municipal housing fund, MKD/infrastructure restoration, "
                 "inventory procedure walkthrough",
        "description": "Моргун and department specialists answer resident "
                        "questions on forming the municipal housing fund, "
                        "MKD/infrastructure restoration, and the "
                        "inventory/bezkhoz-notice procedure.",
        "transcript_out": PARSED_DIR / "morgun_9992_transcript.txt",
    },
    {
        "path": SCRATCH / "allmarinews_39282.mp4",
        "url": "https://t.me/allmarinews/39282",
        "title": "Игнат Яремчук briefing (@allmarinews/39282, 37:29) -- "
                 "detailed inventory-mechanism walkthrough with chapters",
        "description": "Deputy head Игнат Яремчук explains the housing "
                        "inventory in detail: legislative changes, first "
                        "results, bezkhoz definition, registration-evasion "
                        "consequences, guidance for owners in Mariupol vs. "
                        "abroad, non-owner occupants, social/commercial "
                        "tenancy, inheritance cases, unprivatized-housing "
                        "replacement, and what to do upon finding a notice "
                        "on your door.",
        "transcript_out": PARSED_DIR / "allmarinews_39282_transcript.txt",
    },
]

WHISPER_MODEL = "medium"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def capture_video(t: dict, con) -> str:
    path = t["path"]
    if not path.exists():
        raise FileNotFoundError(f"missing file, run scripts/283 first: {path}")

    sha = _sha256_file(path)
    raw_path = config.RAW_DIR / f"{sha}.mp4"
    if not raw_path.exists():
        raw_path.write_bytes(path.read_bytes())
        log.info("copied into raw store: %s", raw_path.name)
    else:
        log.info("sha=%s already in raw store, not re-writing bytes", sha[:12])

    captured = forensics.now_iso()
    meta = {
        "url": t["url"],
        "source_type": "telegram_video_official_channel",
        "title": t["title"],
        "description": t["description"],
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
        (sha, t["url"], "telegram_video_official_channel", t["title"],
         t["description"], str(raw_path), "video/mp4", 200, captured),
    )
    con.commit()
    log.info("captured %s -> sha=%s", path.name, sha[:12])
    return sha


def transcribe(t: dict, model) -> None:
    out_path = t["transcript_out"]
    if out_path.exists():
        log.info("transcript already exists, skipping: %s", out_path)
        return
    log.info("transcribing %s (this can take several minutes)...", t["path"].name)
    result = model.transcribe(str(t["path"]), language="ru", verbose=False)
    out_path.write_text(result["text"], encoding="utf-8")

    # also write a segment-level version with timestamps -- useful for
    # citing specific chapter timestamps (esp. the Яремчук chaptered video)
    segments_path = out_path.with_name(out_path.stem + "_segments.txt")
    with segments_path.open("w", encoding="utf-8") as fh:
        for seg in result["segments"]:
            start = seg["start"]
            end = seg["end"]
            fh.write(f"[{start:8.1f} -> {end:8.1f}] {seg['text'].strip()}\n")

    log.info("wrote transcript -> %s (%d chars)", out_path, len(result["text"]))
    log.info("wrote timestamped segments -> %s", segments_path)


def main() -> None:
    con = forensics.open_state()
    for t in TARGETS:
        capture_video(t, con)
    con.close()

    import whisper  # deferred import -- slow to load
    log.info("loading whisper model: %s", WHISPER_MODEL)
    model = whisper.load_model(WHISPER_MODEL)

    for t in TARGETS:
        transcribe(t, model)

    log.info("done. Review the transcripts, then tell Claude so the "
              "findings can be logged into docs/legal_mechanisms_review.md.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
