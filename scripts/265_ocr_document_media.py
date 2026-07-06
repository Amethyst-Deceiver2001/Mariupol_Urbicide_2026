#!/usr/bin/env python3
"""Batch-OCR the document attachments scripts/264 flagged as needs_ocr (scanned/
image-only PDFs, 105 as of 2026-07-06) — decrees, lists, and letters pulled by
scripts/233 whose text layer was empty (photographed/scanned rather than
digitally authored).

Local, offline, no network. Converts each flagged PDF to page images
(pdf2image/poppler) then runs tesseract (rus) per page, matching the ad-hoc
OCR pattern already used throughout this project (see
memory/ocr_tooling_setup.md) but as a repeatable batch script instead of
one-off shell commands. Caps pages per document (most of this project's
decrees are under 20pp; the one 238pp outlier, the "ЕДИНЫЙ СВОД" PDF, is a
third-party re-aggregation already confirmed duplicate of loaded data — see
memory/document_media_content_survey_2026-07-06.md — and is skipped by
default to avoid burning time on it; use --include-large to force it).

Output: data/parsed/document_media_ocr/<sha256>.txt (plain concatenated text,
one file per document), plus a summary JSONL
data/parsed/document_media_ocr_manifest.jsonl recording char counts so a
follow-up keyword/content pass (like scripts/264) can run against the newly
OCR'd text.

Run:
    .venv312/bin/python3 scripts/265_ocr_document_media.py
    .venv312/bin/python3 scripts/265_ocr_document_media.py --limit 20   # smoke-test a subset first
    .venv312/bin/python3 scripts/265_ocr_document_media.py --include-large  # also OCR the 238pp outlier
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

SURVEY_PATH = ROOT / "data" / "parsed" / "document_media_survey.jsonl"
OUT_DIR = ROOT / "data" / "parsed" / "document_media_ocr"
MANIFEST_PATH = ROOT / "data" / "parsed" / "document_media_ocr_manifest.jsonl"
RAW_DIR = ROOT / "data" / "raw"

LARGE_PAGE_THRESHOLD = 40  # the 238pp ЕДИНЫЙ СВОД outlier; everything else in this batch is well under this


def ocr_pdf(path: Path, max_pages: int | None) -> str:
    from pdf2image import convert_from_path
    with tempfile.TemporaryDirectory() as tmp:
        images = convert_from_path(str(path), dpi=300)
        if max_pages:
            images = images[:max_pages]
        parts = []
        for i, img in enumerate(images):
            png_path = Path(tmp) / f"p{i}.png"
            img.save(png_path)
            result = subprocess.run(
                ["tesseract", str(png_path), "stdout", "-l", "rus", "--psm", "6"],
                capture_output=True, text=True, cwd=tmp,
            )
            parts.append(result.stdout)
        return "\n".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="only OCR the first N flagged docs (smoke test)")
    ap.add_argument("--include-large", action="store_true",
                     help=f"also OCR PDFs over {LARGE_PAGE_THRESHOLD} pages (default: skipped)")
    ap.add_argument("--force", action="store_true", help="re-OCR even documents already in the output dir")
    args = ap.parse_args()

    rows = []
    decoder = json.JSONDecoder()
    text = SURVEY_PATH.read_text(encoding="utf-8")
    pos = 0
    length = len(text)
    while pos < length:
        while pos < length and text[pos] in "\n\r\t ":
            pos += 1
        if pos >= length:
            break
        obj, end = decoder.raw_decode(text, pos)
        rows.append(obj)
        pos = end
    todo = [r for r in rows if r.get("needs_ocr")]
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(todo)} documents flagged needs_ocr", file=sys.stderr)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    n_done = 0
    n_skipped_large = 0
    n_skipped_stored = 0
    n_errors = 0
    with open(MANIFEST_PATH, "a", encoding="utf-8") as manifest:
        for i, r in enumerate(todo, 1):
            sha = r["sha256"]
            out_path = OUT_DIR / f"{sha}.txt"
            if out_path.exists() and not args.force:
                n_skipped_stored += 1
                continue

            mime = r.get("mime", "")
            ext = {"application/pdf": ".pdf"}.get(mime, "")
            if not ext:
                n_errors += 1
                continue
            pdf_path = RAW_DIR / f"{sha}{ext}"
            if not pdf_path.exists():
                print(f"  [{i}/{len(todo)}] MISSING raw file: {pdf_path}", file=sys.stderr)
                n_errors += 1
                continue

            max_pages = None if args.include_large else LARGE_PAGE_THRESHOLD
            try:
                from pypdf import PdfReader  # noqa: F401 -- optional page-count probe
                page_count = None
            except ImportError:
                page_count = None

            print(f"  [{i}/{len(todo)}] OCR'ing {r['url']} ({r.get('title', sha)})", file=sys.stderr)
            try:
                text = ocr_pdf(pdf_path, max_pages)
            except Exception as e:  # noqa: BLE001
                print(f"    error: {e}", file=sys.stderr)
                n_errors += 1
                continue

            out_path.write_text(text, encoding="utf-8")
            manifest.write(json.dumps({
                "sha256": sha, "url": r["url"], "channel": r.get("channel"),
                "title": r.get("title"), "text_len": len(text),
                "output": str(out_path),
            }, ensure_ascii=False) + "\n")
            n_done += 1

    print(f"\nDone. {n_done} OCR'd, {n_skipped_stored} already done, "
          f"{n_skipped_large} skipped as >{LARGE_PAGE_THRESHOLD}pp (use --include-large), "
          f"{n_errors} errors. Output dir: {OUT_DIR}", file=sys.stderr)


if __name__ == "__main__":
    main()
