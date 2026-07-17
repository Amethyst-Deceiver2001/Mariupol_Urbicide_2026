#!/usr/bin/env python3
"""Rotation-aware OCR retry for the resettlement-program annex (Приложение 2 —
the per-building resettlement schedule inside decree №1084, "Переселение
граждан из аварийного жилищного фонда в 2026-2030 годах").

scripts/06a_ocr_decrees.py's ocrmypdf pass (--rotate-pages --deskew) gets most
pages right but garbles a handful into backwards-reading Cyrillic (e.g. line
"2 еинежолирП" instead of "Приложение 2" — confirmed 2026-07-17 on pages 20,
23, 24 of the OCR'd derivative at
data/raw/e5ae0eb80cd91d66b6f52daea90f3a834635b313009529eb88aa4b6fb12cd5c4.pdf).
That reversed-character pattern is the signature of ocrmypdf's auto-rotation
picking 180 degrees wrong on a landscape table page — the PDF page box stays
portrait (612x792) even though the scanned content itself is landscape, so
page-box aspect ratio can't be used to detect this; only re-OCR at each
candidate rotation and score the result can.

Approach: render each candidate page to a high-DPI image (pdf2image), try
OCR (pytesseract, rus) at 0/90/180/270 degrees, score each by the fraction of
extracted alphabetic characters that appear in a real Cyrillic dictionary
word context (crude heuristic: ratio of characters inside regex-matched
Cyrillic "words" of length >= 3 to total alphabetic characters — garbled/
reversed text produces far fewer coherent multi-char words). Keep whichever
rotation scores highest per page.

Requires pytesseract + pdf2image + poppler (see docs/ note in
ocr_tooling_setup memory) — installed in .venv312, NOT the project's default
.venv.

Run (from .venv312):
    .venv312/bin/python scripts/355_rotate_ocr_resettlement_annex.py
"""
from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

try:
    import pytesseract
    from pdf2image import convert_from_path
except ImportError:
    sys.exit(
        "pytesseract/pdf2image not installed in this interpreter.\n"
        "Run this script with .venv312, not .venv:\n"
        "  .venv312/bin/python scripts/355_rotate_ocr_resettlement_annex.py"
    )

from mariupol_seizures import forensics  # noqa: E402

log = logging.getLogger(__name__)

# The resettlement-program decree, and the specific pages found (2026-07-17,
# by inspecting the existing ocrmypdf pass) to contain the garbled/reversed
# annex table. Extend this list if a future resettlement-program decree is
# captured -- source_sha discovered via:
#   SELECT sha256 FROM source_document
#   WHERE source_type = 'avariinoe_resettlement_program_pdf'
TARGETS = [
    {
        "source_sha256": "c355d2480307af659d17f5cffd28d46540e555af2c9e16dd21ceaafedc8906b2",
        "raw_path": "data/raw/c355d2480307af659d17f5cffd28d46540e555af2c9e16dd21ceaafedc8906b2.pdf",
        "pages": [20, 21, 23, 24],  # 1-indexed; 21 included as a neighbor check
    },
]

CANDIDATE_ROTATIONS = (0, 90, 180, 270)
_CYRILLIC_WORD = re.compile(r"[а-яёА-ЯЁ]{3,}")
_CYRILLIC_CHAR = re.compile(r"[а-яёА-ЯЁ]")


def _score(text: str) -> float:
    """Higher = more likely correctly-oriented real Cyrillic text."""
    chars = _CYRILLIC_CHAR.findall(text)
    if not chars:
        return 0.0
    word_chars = sum(len(m) for m in _CYRILLIC_WORD.findall(text))
    return word_chars / len(chars)


def ocr_page_best_rotation(pdf_path: Path, page_no: int) -> tuple[int, str, dict]:
    """Return (best_angle, best_text, {angle: score}) for one page."""
    images = convert_from_path(
        str(pdf_path), dpi=300, first_page=page_no, last_page=page_no
    )
    if not images:
        return 0, "", {}
    base_image = images[0]

    scores: dict[int, float] = {}
    texts: dict[int, str] = {}
    for angle in CANDIDATE_ROTATIONS:
        rotated = base_image.rotate(-angle, expand=True)
        text = pytesseract.image_to_string(rotated, lang="rus")
        texts[angle] = text
        scores[angle] = _score(text)

    best_angle = max(scores, key=scores.get)
    return best_angle, texts[best_angle], scores


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    out_dir = ROOT / "data" / "reports" / "avariinoe_inspect"
    out_dir.mkdir(parents=True, exist_ok=True)

    for target in TARGETS:
        pdf_path = ROOT / target["raw_path"]
        if not pdf_path.exists():
            log.error("missing: %s", pdf_path)
            continue

        sha = target["source_sha256"]
        report_lines = [f"# Rotation-aware OCR — {sha[:16]} — decree resettlement annex\n"]

        for page_no in target["pages"]:
            log.info("page %d: trying rotations %s", page_no, CANDIDATE_ROTATIONS)
            best_angle, best_text, scores = ocr_page_best_rotation(pdf_path, page_no)
            log.info("  page %d: best angle=%d scores=%s", page_no, best_angle,
                     {a: round(s, 3) for a, s in scores.items()})
            report_lines.append(f"\n## Page {page_no} — best angle {best_angle} deg — scores {scores}\n")
            report_lines.append(best_text)
            report_lines.append("\n" + "=" * 80 + "\n")

        out_path = out_dir / f"{sha[:16]}_rotation_ocr.txt"
        out_path.write_text("\n".join(report_lines), encoding="utf-8")
        log.info("wrote %s", out_path)

    log.info("done. Read the .txt report(s) in data/reports/avariinoe_inspect/ "
             "to check whether the per-building resettlement table is now legible.")


if __name__ == "__main__":
    main()
