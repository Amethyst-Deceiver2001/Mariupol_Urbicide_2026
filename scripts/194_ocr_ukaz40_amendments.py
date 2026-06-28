#!/usr/bin/env python3
"""OCR the two amendments to Указ врио Главы ДНР №40 (02.12.2022, "О порядке
выявления и сноса объектов, поврежденных в результате боевых действий") —
the DNR-wide post-annexation demolition-procedure decree. Both amendments
were already captured by script 39's archives-only crawl + indexed by
script 43 (data/parsed/denis_pushilin_archive_index.jsonl), but never OCR'd
(same ocrmypdf pattern as script 44 for the appointment chronology).
progress_report_2026-06.md §5 item 5.

  - Ukaz_N657_03122024.pdf  №657 03.12.2024  "О внесении изменений в Указ ... №40"
  - Ukaz_N513_24062025.pdf  №513 24.06.2025  "О внесении изменений в Указ ... №40"

(Not to be confused with the unrelated Ukaz_N513_31102023.pdf, a different
decree that happens to share the number 513 — liquidation of the DNR coal/
energy ministry. Distinguished by sha256/filename, not number alone.)

FORENSIC RULE: OCR is lossy -- raw scans are never modified. Each OCR output
is written as a DERIVED artifact (forensics.capture_derived), source_type
`denis_pushilin_doc_ocr_pdf`, recording derived_from + transform. Idempotent.

Output: data/parsed/ukaz40_amendments_202606.jsonl

Local-only, no network. Run:
  PYTHONPATH=src .venv312/bin/python scripts/194_ocr_ukaz40_amendments.py
"""
from __future__ import annotations

import json
import logging
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import pdfplumber  # noqa: E402

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

PARSED_DIR = config.PROJECT_ROOT / "data" / "parsed"

OCR_ARGS = ["--language", "rus", "--skip-text", "--rotate-pages", "--deskew"]
TRANSFORM = f"ocrmypdf {' '.join(OCR_ARGS)}"
_OCR_EXECUTABLE = str(Path(sys.executable).parent / "ocrmypdf")

TARGETS: dict[str, tuple[str, str]] = {
    "Ukaz_N657_03122024.pdf": (
        "9d9f8ea04ca16ba53dc518ae161ad77c067fb869ebbfc6575105c34c636e4ea8",
        "О внесении изменений в Указ №40 (02.12.2022) — 1st amendment",
    ),
    "Ukaz_N513_24062025.pdf": (
        "d33496fa9080309a061027739965e3d3702139c4aadd0b2505ed79e5822f43fc",
        "О внесении изменений в Указ №40 (02.12.2022) — 2nd amendment",
    ),
}


def _already_ocrd(con, parent_sha: str):
    return con.execute(
        "SELECT sha256, raw_path FROM source_document "
        "WHERE derived_from = ? AND transform = ? LIMIT 1",
        (parent_sha, TRANSFORM),
    ).fetchone()


def _run_ocr(src: Path) -> bytes | None:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "ocr.pdf"
        cmd = [_OCR_EXECUTABLE, *OCR_ARGS, str(src), str(out)]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if res.returncode != 0:
            log.error("ocrmypdf failed (exit %d) on %s:\n%s",
                      res.returncode, src.name, res.stderr.strip()[:500])
            return None
        return out.read_bytes()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")

    con = forensics.open_state()
    out_rows = []

    for filename, (sha, label) in TARGETS.items():
        row = con.execute(
            "SELECT raw_path FROM source_document WHERE sha256=?", (sha,)
        ).fetchone()
        if not row:
            log.error("%s: sha256 %s not in source_document", filename, sha)
            continue
        src_path = Path(row[0])

        existing = _already_ocrd(con, sha)
        if existing:
            ocr_sha, ocr_path = existing
            log.info("%s: already OCR'd -> %s", filename, ocr_sha[:16])
        else:
            log.info("%s: running ocrmypdf...", filename)
            ocr_bytes = _run_ocr(src_path)
            if ocr_bytes is None:
                continue
            ocr_sha = forensics.capture_derived(
                ocr_bytes,
                derived_from=sha,
                transform=TRANSFORM,
                source_type="denis_pushilin_doc_ocr_pdf",
                title=f"{filename} [OCR] -- {label}",
                description=(
                    f"OCR-derived searchable PDF of {filename} (parent "
                    f"sha256={sha}). Transform: {TRANSFORM}. Amendment to "
                    "Указ №40/02.12.2022 (demolition-designation procedure), "
                    "docs/legal_mechanisms_review.md. Derived artifact -- "
                    f"raw scan ({sha[:16]}..) remains the immutable original."
                ),
                content_type="application/pdf",
                con=con,
            )
            ocr_path = str(config.RAW_DIR / f"{ocr_sha}.pdf")
            log.info("%s: OCR done -> %s", filename, ocr_sha[:16])

        text = ""
        try:
            with pdfplumber.open(ocr_path) as pdf:
                text = "\n".join(p.extract_text() or "" for p in pdf.pages)
        except Exception as e:
            log.error("%s: text extraction failed: %s", filename, e)

        out_rows.append({
            "filename": filename,
            "label": label,
            "source_sha256": sha,
            "ocr_sha256": ocr_sha,
            "text": text.strip(),
        })
        log.info("%s: extracted %d chars", filename, len(text))

    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PARSED_DIR / "ukaz40_amendments_202606.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for r in out_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    log.info("wrote %s (%d rows)", out_path, len(out_rows))


if __name__ == "__main__":
    main()
