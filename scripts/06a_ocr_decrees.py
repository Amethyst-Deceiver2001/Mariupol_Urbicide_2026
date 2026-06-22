#!/usr/bin/env python3
"""Stage 2b-pre: OCR the scanned ownerless-decree annex PDFs.

The decree РЕЕСТР annexes captured by 05_crawl_ownerless_lists.py are SCANNED
IMAGES — they have no text layer, so pdfplumber extracts 0 chars / 0 tables.
This script runs OCR (ocrmypdf, Russian language model) over each raw scan and
stores the result as a DERIVED artifact, then scripts/06_parse_ownerless_decrees.py
reads those derivatives.

FORENSIC RULE (Berkeley Protocol)
---------------------------------
OCR is a lossy transformation. The immutable raw scan is NEVER overwritten.
Each OCR output is written under its own SHA-256 via forensics.capture_derived(),
which records:
  - derived_from : the parent scan's SHA-256
  - transform    : the exact tool + args used
  - captured_at  : ISO-8601 UTC timestamp
so the chain raw → OCR → parsed is fully reproducible and auditable.

Idempotent: a scan whose OCR derivative already exists (looked up by
derived_from + transform) is skipped, so re-running only fills gaps.

Why ocrmypdf (not raw tesseract)
--------------------------------
ocrmypdf adds a text layer while preserving the original page image, producing
a PDF that is visually identical to the scan but searchable. That keeps the
derived artifact a faithful representation of the source (important for court
admissibility) and lets the parser work on a normal PDF.

PREREQUISITES (install on the machine that runs this — may be the VPS or local;
OCR is offline so it can run anywhere the raw store is present):
    # macOS
    brew install ocrmypdf            # pulls tesseract + ghostscript
    # the Russian model must be present:
    brew install tesseract-lang      # or ensure 'rus' is in tesseract --list-langs
    # Debian/Ubuntu
    sudo apt-get install ocrmypdf tesseract-ocr-rus

Run:
    PYTHONPATH=src python scripts/06a_ocr_decrees.py
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import forensics  # noqa: E402

# Which captured source types are scanned annexes that need OCR.
# Ownerless-decree annexes (designation/removal/procedure) and demolition-decree
# annexes (mkd/oks/building/amendment) share the same scanned-image PDF format
# and can all be OCR'd with identical settings.
OCR_SOURCE_TYPES = (
    "ownerless_decree_designation_pdf",
    "ownerless_decree_removal_pdf",
    "ownerless_decree_procedure_pdf",
    "demolition_decree_mkd_pdf",
    "demolition_decree_oks_pdf",
    "demolition_decree_building_pdf",
    "demolition_decree_amendment_pdf",
    "demolition_decree_unknown_pdf",
)

# Canonical tool name — used in the TRANSFORM string recorded in the custody
# chain (never changes, even if the binary path changes).
OCR_TOOL = "ocrmypdf"
OCR_ARGS = ["--language", "rus", "--skip-text", "--rotate-pages", "--deskew"]
TRANSFORM = f"{OCR_TOOL} {' '.join(OCR_ARGS)}"

# Prefer the venv's ocrmypdf binary (Python 3.11+) over any system install
# (brew's ocrmypdf links against Python 3.14 which has a broken expat binding).
_VENV_BIN = Path(sys.executable).parent / "ocrmypdf"
_OCR_EXECUTABLE = str(_VENV_BIN) if _VENV_BIN.exists() else OCR_TOOL


def _ocrmypdf_available() -> bool:
    return _VENV_BIN.exists() or shutil.which(OCR_TOOL) is not None


def _already_ocrd(con, parent_sha: str) -> bool:
    row = con.execute(
        """SELECT 1 FROM source_document
           WHERE derived_from = ? AND transform = ? LIMIT 1""",
        (parent_sha, TRANSFORM),
    ).fetchone()
    return row is not None


def _run_ocr(src: Path) -> bytes | None:
    """OCR a single PDF; return the OCR'd bytes, or None on failure."""
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "ocr.pdf"
        cmd = [_OCR_EXECUTABLE, *OCR_ARGS, str(src), str(out)]
        try:
            res = subprocess.run(
                cmd, capture_output=True, text=True, timeout=900
            )
        except subprocess.TimeoutExpired:
            log.error("OCR timed out (>15min): %s", src.name)
            return None
        if res.returncode != 0:
            # ocrmypdf exit 6 = "already has text" (shouldn't happen with
            # --skip-text, but treat as non-fatal pass-through).
            log.error("ocrmypdf failed (exit %d) on %s:\n%s",
                      res.returncode, src.name, res.stderr.strip()[:500])
            return None
        return out.read_bytes()


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    if not _ocrmypdf_available():
        sys.exit(
            "ocrmypdf not found.\n"
            "  Install into the project venv (recommended — avoids Python 3.14 brew bug):\n"
            "    .venv/bin/pip install ocrmypdf\n"
            "  Also ensure the Russian tesseract model is present:\n"
            "    brew install tesseract-lang   # macOS\n"
            "    sudo apt-get install tesseract-ocr-rus  # Debian\n"
            "    tesseract --list-langs | grep rus"
        )

    con = forensics.open_state()
    placeholders = ",".join("?" * len(OCR_SOURCE_TYPES))
    scans = con.execute(
        f"""SELECT sha256, raw_path, title, source_type
            FROM source_document
            WHERE source_type IN ({placeholders})
              AND derived_from IS NULL       -- only originals, not derivatives
            ORDER BY captured_at""",
        OCR_SOURCE_TYPES,
    ).fetchall()

    if not scans:
        log.warning("No scanned decree annexes found — run 05_crawl first.")
        return

    done = skipped = failed = 0
    for parent_sha, raw_path, title, source_type in scans:
        if _already_ocrd(con, parent_sha):
            skipped += 1
            continue
        p = Path(raw_path)
        if not p.exists():
            log.error("raw scan missing on disk: %s", raw_path)
            failed += 1
            continue

        log.info("OCR: %s", title[:80])
        ocr_bytes = _run_ocr(p)
        if ocr_bytes is None:
            failed += 1
            continue

        # source_type of the derivative: parent type + '_ocr'
        derived_type = source_type.replace("_pdf", "_ocr_pdf")
        sha = forensics.capture_derived(
            ocr_bytes,
            derived_from=parent_sha,
            transform=TRANSFORM,
            source_type=derived_type,
            title=f"{title} [OCR]",
            description=(
                f"OCR-derived searchable PDF of scanned decree annex "
                f"(parent sha256={parent_sha}). Transform: {TRANSFORM}. "
                "Text layer added for parsing; page images preserved. "
                "Derived artifact — NOT the authoritative source; the raw scan "
                f"({parent_sha[:16]}…) remains the immutable original."
            ),
            content_type="application/pdf",
            con=con,
        )
        log.info("  -> derived %s", sha[:16])
        done += 1

    log.info("done — OCR'd %d, skipped %d (already done), failed %d",
             done, skipped, failed)
    if done:
        log.info("Next: PYTHONPATH=src python scripts/06_parse_ownerless_decrees.py")


if __name__ == "__main__":
    main()
