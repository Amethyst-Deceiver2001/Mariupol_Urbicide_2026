#!/usr/bin/env python3
"""Scan OCR'd bezkhoz/avariinoe derivatives for genuine rotation-garble
(scripts/355's problem: ocrmypdf's --rotate-pages picks the wrong angle on a
landscape table page, producing text with reversed/incoherent character
order — e.g. "2 еинежолирП" instead of "Приложение 2").

FIRST VERSION OF THIS SCRIPT (short-Cyrillic-token-ratio heuristic across
every page) was too noisy to use: normal bezkhoz registry tables are
naturally dense with short tokens (apartment numbers, "кв.", "лит.",
cadastral fragments) even when correctly oriented, so it flagged ~340 pages
that scripts/06_parse_ownerless_decrees.py had already successfully parsed
into hundreds of claim-grade rows -- proof those pages were NOT garbled.

REAL signal used here instead: a document is a genuine parse-failure
candidate only if (a) its OCR text is substantial (not just OCR failure/
missing derivative) AND (b) it produced ZERO rows in the actual parse
output (data/parsed/ownerless_decrees.jsonl / avariinoe_decrees.jsonl),
while being a decree_kind that's EXPECTED to yield rows (designation/
registration/removal_*/avariinoe designation) -- NOT a metadata-only kind
(procedure/amendment) where 0 rows is correct by design.

Only within those flagged documents do we then apply the short-token-ratio
heuristic per-page, as a secondary aid to pinpoint WHICH page is worth a
scripts/355-style rotation-aware retry -- not as the primary signal.

Run:
    PYTHONPATH=src python scripts/356_scan_ocr_derivatives_for_rotation_garble.py
"""
from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import pdfplumber  # noqa: E402

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

_CYRILLIC_TOKEN = re.compile(r"[а-яёА-ЯЁ]+")
SHORT_RATIO_THRESHOLD = 0.55
MIN_TOKENS = 15
MIN_TEXT_LEN_FOR_SUSPECT = 500  # substantial OCR text, not a near-empty/failed OCR

# decree_kind values that are metadata-only by design -- 0 rows there is
# expected and NOT a sign of rotation garble.
METADATA_ONLY_KINDS = {"procedure", "amendment"}


def _load_parsed_shas(jsonl_path: Path) -> dict[str, int]:
    """source_sha256 -> row count, from an already-written parsed jsonl."""
    counts: dict[str, int] = {}
    if not jsonl_path.exists():
        return counts
    with jsonl_path.open(encoding="utf-8") as fh:
        for line in fh:
            d = json.loads(line)
            sha = d.get("source_sha256")
            if sha:
                counts[sha] = counts.get(sha, 0) + 1
    return counts


def _page_short_ratio(text: str) -> tuple[float, int]:
    tokens = _CYRILLIC_TOKEN.findall(text)
    if not tokens:
        return 0.0, 0
    short_ratio = sum(1 for t in tokens if len(t) <= 3) / len(tokens)
    return short_ratio, len(tokens)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parsed_dir = config.PROJECT_ROOT / "data" / "parsed"
    row_counts = {}
    row_counts.update(_load_parsed_shas(parsed_dir / "ownerless_decrees.jsonl"))
    row_counts.update(_load_parsed_shas(parsed_dir / "avariinoe_decrees.jsonl"))
    log.info("%d distinct source docs have >=1 parsed row on file", len(row_counts))

    con = forensics.open_state()
    ocr_docs = con.execute(
        """SELECT ocr.sha256, ocr.raw_path, ocr.title, parent.source_type
           FROM source_document ocr
           JOIN source_document parent ON parent.sha256 = ocr.derived_from
           WHERE (parent.source_type LIKE 'ownerless_decree_%_pdf'
                  OR parent.source_type LIKE 'avariinoe_%_pdf')"""
    ).fetchall()
    log.info("%d OCR'd bezkhoz/avariinoe derivatives to check", len(ocr_docs))

    def _kind_of(source_type: str) -> str:
        for k in ("designation", "registration", "removal", "procedure",
                  "amendment", "resettlement_program"):
            if k in source_type:
                return k
        return "unknown"

    flagged_docs = []
    for sha, raw_path, title, source_type in ocr_docs:
        kind = _kind_of(source_type)
        if kind in METADATA_ONLY_KINDS:
            continue  # 0 rows expected here, not a garble signal
        if row_counts.get(sha, 0) > 0:
            continue  # already parsed successfully -- proven not garbled
        p = Path(raw_path)
        if not p.exists():
            continue
        try:
            with pdfplumber.open(p) as pdf:
                full_text = "\n".join(pg.extract_text() or "" for pg in pdf.pages)
        except Exception:
            log.exception("failed to open %s", raw_path)
            continue
        if len(full_text) < MIN_TEXT_LEN_FOR_SUSPECT:
            continue  # OCR itself likely failed/near-empty -- a 06a problem, not rotation
        flagged_docs.append((sha, raw_path, title, kind))

    log.info("%d documents are genuine parse-failure candidates (substantial OCR "
             "text, expected-to-yield-rows kind, but 0 parsed rows)", len(flagged_docs))

    for sha, raw_path, title, kind in flagged_docs:
        log.info("--- %s (kind=%s) %s", sha[:16], kind, (title or "")[:70])
        with pdfplumber.open(raw_path) as pdf:
            page_scores = []
            for i, pg in enumerate(pdf.pages):
                text = pg.extract_text() or ""
                ratio, n_tokens = _page_short_ratio(text)
                if n_tokens > MIN_TOKENS:
                    page_scores.append((i + 1, ratio, n_tokens))
        page_scores.sort(key=lambda x: -x[1])
        for page_no, ratio, n_tokens in page_scores[:5]:
            log.info("    page %d: short_ratio=%.2f tokens=%d (candidate for rotation retry)",
                     page_no, ratio, n_tokens)

    if flagged_docs:
        log.info("Next: for each flagged doc above, add {source_sha256, raw_path, "
                 "pages:[...]} to TARGETS in scripts/355_rotate_ocr_resettlement_annex.py "
                 "(generalize it to take a list) and re-run the rotation-aware pass on "
                 "just those pages.")
    else:
        log.info("No genuine rotation-garble candidates found beyond the resettlement "
                 "annex already handled.")


if __name__ == "__main__":
    main()
