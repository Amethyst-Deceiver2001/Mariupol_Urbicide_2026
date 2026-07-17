#!/usr/bin/env python3
"""AWS Rekognition photo triage — OCR (address plaques, паспорт объекта
signage) + damage-label detection over already-captured images.

Does NOT crawl or capture new images — it walks images this project has
ALREADY pulled (via an OSINT sweep's data/reports/osint/<slug>/*.json
findings, or any raw-store source_type with content_type image/*), runs
AWS Rekognition DetectText + DetectLabels on each, and writes a REVIEW CSV.

Nothing here writes to the DB or a case study automatically — per this
project's no-fuzzy-merge/confidence-score rule (CLAUDE.md), OCR text and
labels are leads for a human to verify, not claim-grade evidence on their
own. Promote a hit into a case study / corroboration row by hand once you've
looked at the source image and confirmed the reading.

Setup (see docs/address_osint_assistant_design.md):
    pip install -e '.[aws]'
    # .env: AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_DEFAULT_REGION
    # IAM policy needed: rekognition:DetectText, rekognition:DetectLabels only

Cost: Rekognition free tier is 5,000 images/month per API (DetectText and
DetectLabels billed separately) for the account's first 12 months; beyond
that ~$1/1000 images per API. This script calls BOTH per image, so 1 image
= 2 units against quota. Defaults to a conservative --limit; raise it
deliberately.

Usage:
    # triage every image already captured for one address's OSINT sweep
    PYTHONPATH=src .venv312/bin/python scripts/326_rekognition_photo_triage.py \
        --pid 4837 --limit 50

    # triage a specific raw source_type (e.g. all kadryVoyny media pulls)
    PYTHONPATH=src .venv312/bin/python scripts/326_rekognition_photo_triage.py \
        --source-type telegram_kadryvoyny_media --limit 100

    # cost/scope check only, no API calls, no spend
    PYTHONPATH=src .venv312/bin/python scripts/326_rekognition_photo_triage.py \
        --pid 4837 --dry-run
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

# labels worth surfacing for a demolition/damage/status triage pass — kept
# short and specific; Rekognition's generic label set is huge and mostly
# noise for this use case (it will happily label a ruin "Architecture").
LABELS_OF_INTEREST = {
    "Rubble", "Ruins", "Debris", "Demolition", "Construction Crane", "Crane",
    "Fire", "Explosion", "Smoke", "Damaged", "Bulldozer", "Wrecking Ball",
    "Scaffolding", "Building", "Housing", "Apartment Building", "Sign",
    "Signage", "Symbol", "Text", "Plaque", "Road Sign", "Street Sign",
}

# address-shaped OCR line: has a street-type cue word or a bare
# "word + digits(+letter)" house-number pattern. Deliberately loose — this
# is a human-review flag, not a parser (no auto-match to the spine here).
_ADDR_CUE = re.compile(
    r"(ул\.?|вул\.?|улиц|проспект|пр-?кт|пр\.|бульвар|переул)", re.IGNORECASE)
_HOUSE_NO = re.compile(r"\b\d{1,4}[а-яА-Я]?\b")
_PASPORT_CUE = re.compile(r"паспорт\s*об[ъь]?ект", re.IGNORECASE)


def _outdir() -> Path:
    d = config.DATA_DIR / "reports" / "rekognition_triage"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _images_for_pid(pid: int, con: sqlite3.Connection) -> list[dict]:
    """Every image sha256 already captured by an OSINT sweep for this pid,
    with enough context (source kind + url) to label the review row."""
    reports_dir = config.DATA_DIR / "reports" / "osint"
    matches = [d for d in reports_dir.glob(f"{pid}_*") if d.is_dir()]
    if not matches:
        log.error("no OSINT sweep found for pid=%s under %s — run scripts/324 first",
                  pid, reports_dir)
        return []
    out = []
    seen = set()
    for report_dir in matches:
        for jf in report_dir.glob("*.json"):
            if jf.name in ("bundle.json",):
                continue
            try:
                data = json.loads(jf.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                continue
            for f in data.get("findings", []):
                sha = f.get("sha256")
                if not sha or sha in seen:
                    continue
                row = con.execute(
                    "SELECT raw_path, content_type FROM source_document WHERE sha256=?",
                    (sha,)).fetchone()
                if not row or not (row[1] or "").startswith("image/"):
                    continue
                seen.add(sha)
                out.append({"sha256": sha, "raw_path": row[0], "content_type": row[1],
                            "context": f"{jf.stem}:{f.get('kind','')}",
                            "url": f.get("url", "")})
    return out


def _images_for_source_type(source_type: str, con: sqlite3.Connection,
                            limit: int) -> list[dict]:
    rows = con.execute(
        "SELECT sha256, raw_path, content_type, url FROM source_document "
        "WHERE source_type=? AND content_type LIKE 'image/%' LIMIT ?",
        (source_type, limit)).fetchall()
    return [{"sha256": r[0], "raw_path": r[1], "content_type": r[2],
             "context": source_type, "url": r[3]} for r in rows]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pid", type=int, help="triage images from this pid's OSINT sweep(s)")
    ap.add_argument("--source-type", help="triage images from this raw source_type instead")
    ap.add_argument("--limit", type=int, default=50,
                    help="max images to send to Rekognition (cost guardrail, default 50)")
    ap.add_argument("--min-confidence", type=float, default=70.0,
                    help="Rekognition label confidence threshold (default 70)")
    ap.add_argument("--dry-run", action="store_true",
                    help="show scope + estimated API-call cost, make no calls")
    ap.add_argument("--region", default=None, help="override AWS_DEFAULT_REGION")
    args = ap.parse_args()

    if not args.pid and not args.source_type:
        log.error("need --pid or --source-type")
        sys.exit(1)

    con = forensics.open_state()
    images = (_images_for_pid(args.pid, con) if args.pid
             else _images_for_source_type(args.source_type, con, args.limit * 3))
    images = images[:args.limit]

    print(f"\n{'='*72}\nRekognition photo triage")
    print(f"  scope: {'pid=' + str(args.pid) if args.pid else args.source_type}")
    print(f"  images found: {len(images)} (limit {args.limit})")
    print(f"  API calls: {len(images)*2} (DetectText + DetectLabels per image)")
    print(f"  free tier: 5,000/month per API for account's first 12 months, "
          f"~$1/1000 after\n{'='*72}")

    if not images:
        con.close()
        return
    if args.dry_run:
        print("\n-- dry run, no API calls made --")
        for im in images[:10]:
            print(f"  {im['sha256'][:12]}  {im['context']}  {im['url']}")
        if len(images) > 10:
            print(f"  ... and {len(images)-10} more")
        con.close()
        return

    try:
        import boto3
    except ImportError:
        log.error("boto3 not installed — pip install -e '.[aws]'")
        sys.exit(1)

    kwargs = {"region_name": args.region} if args.region else {}
    rekognition = boto3.client("rekognition", **kwargs)

    out_rows = []
    for i, im in enumerate(images, 1):
        raw_path = Path(im["raw_path"])
        if not raw_path.is_absolute():
            raw_path = config.PROJECT_ROOT / raw_path
        try:
            img_bytes = raw_path.read_bytes()
        except OSError as e:
            log.warning("can't read %s: %s", raw_path, e)
            continue

        print(f"[{i}/{len(images)}] {im['sha256'][:12]} {im['context']}")
        try:
            text_resp = rekognition.detect_text(Image={"Bytes": img_bytes})
            label_resp = rekognition.detect_labels(
                Image={"Bytes": img_bytes}, MaxLabels=25,
                MinConfidence=args.min_confidence)
        except Exception as e:  # noqa: BLE001
            log.warning("rekognition call failed for %s: %s", im["sha256"][:12], e)
            continue

        forensics.capture_derived(
            json.dumps({"text": text_resp, "labels": label_resp},
                      ensure_ascii=False, default=str).encode("utf-8"),
            derived_from=im["sha256"], transform="aws_rekognition_detect_text+labels",
            source_type="osint_rekognition_result",
            title=f"rekognition {im['sha256'][:12]}",
            description=f"AWS Rekognition DetectText+DetectLabels for {im['context']}.",
            content_type="application/json", con=con,
        )

        lines = [d["DetectedText"] for d in text_resp.get("TextDetections", [])
                if d.get("Type") == "LINE"]
        addr_hits = [ln for ln in lines if _ADDR_CUE.search(ln) or
                    (_HOUSE_NO.search(ln) and len(ln) < 40)]
        paspa_hits = [ln for ln in lines if _PASPORT_CUE.search(ln)]
        labels = [ld["Name"] for ld in label_resp.get("Labels", [])
                 if ld["Name"] in LABELS_OF_INTEREST]

        out_rows.append({
            "sha256": im["sha256"], "context": im["context"], "url": im["url"],
            "raw_path": str(raw_path),
            "ocr_lines": " | ".join(lines),
            "address_candidates": " | ".join(addr_hits),
            "pasport_obekta_plaque": " | ".join(paspa_hits),
            "labels_of_interest": ", ".join(labels),
            "flagged": bool(addr_hits or paspa_hits),
        })

    slug = f"pid{args.pid}" if args.pid else args.source_type
    out_csv = _outdir() / f"{slug}.csv"
    with out_csv.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()) if out_rows else
                           ["sha256", "context", "url", "raw_path", "ocr_lines",
                            "address_candidates", "pasport_obekta_plaque",
                            "labels_of_interest", "flagged"])
        w.writeheader()
        w.writerows(out_rows)

    n_flagged = sum(1 for r in out_rows if r["flagged"])
    print(f"\ndone — {len(out_rows)} images processed, {n_flagged} flagged "
          f"(address text or паспорт объекта plaque detected)")
    print(f"review CSV: {out_csv}")
    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
