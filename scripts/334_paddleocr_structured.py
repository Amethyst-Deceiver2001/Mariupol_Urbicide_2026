#!/usr/bin/env python3
"""PaddleOCR PP-StructureV3 — Cyrillic structured-table OCR of captured documents.

The occupation decrees, ownerless-property notices, and land orders this
project has captured (denis_pushilin_*_pdf, ownerless_decree_*_pdf,
dnr_land_order_pdf, mariupol_gosuslugi_nonres_attachment, eisghs_rnv_pdf,
...) are scanned Russian documents, many with STRUCTURED TABLES (address
lists, apartment schedules, expropriation registers). The project's existing
OCR (tesseract via scripts/06a/19/265/...) reads running text but flattens
tables into an unstructured blob — losing which value belongs to which
column/row. PaddleOCR's PP-StructureV3 pipeline is the only free, offline,
chain-of-custody-safe engine that does true table-structure recognition:
per-cell coordinates exported to Markdown tables + JSON, with a Cyrillic
recognition model (lang='ru').

Runs under a DEDICATED venv (.venv-ocr), NOT .venv312 — paddleocr pulls a
heavy, fast-moving stack (paddlepaddle, paddlex, numpy 2.3.x, pandas 3.x,
opencv-contrib) that would risk the main pipeline's numpy/rasterio ABI.
.venv-ocr only needs paddleocr + python-dotenv + pdf2image; forensics/config
are stdlib+dotenv only, so PYTHONPATH=src is enough to reach them.

Reads docs ALREADY in the raw store (by --source-type / --sha), converts
PDFs to page images (poppler/pdf2image), runs PP-StructureV3 per page, and
captures TWO derived artifacts per document (lineage to the source PDF sha):
  * osint_paddle_structured_md   — Markdown: running text + tables as
                                    Markdown tables (structure preserved)
  * osint_paddle_structured_json — full result incl. per-cell coordinates
Plus a human-review .md under data/reports/paddle_ocr/. Address-shaped lines
are flagged. Nothing is written to the DB / a case study automatically —
same rule as scripts/326/331: OCR output is a lead for a human to verify.

This is a HEAVY LOCAL COMPUTE job — measured empirically 2026-07-17 on
Apple Silicon (arm64 macOS, CPU-only): **15-30 MINUTES PER PAGE**, not
seconds. PaddlePaddle has no Metal/Apple-Silicon-GPU backend, only CUDA, so
there is no faster path on this hardware — a 25-page document is a
6-12+ HOUR run. This rules out PaddleOCR as a bulk/sweep tool entirely
(the project has thousands of decree PDFs). Use it ONLY as a narrow,
hand-picked, single-page tool for a specific document where table
structure is genuinely worth the wait — never point --source-type at a
whole category expecting it to churn through it. `--max-pages` defaults
to 1 and refuses more without an explicit, deliberate override; there is
no scenario where sweeping this across a source_type at default settings
is the right call on this hardware.

First run also downloads models over the network — benign infra setup,
like whisper/chromium.

Setup:
    /opt/homebrew/bin/python3.12 -m venv .venv-ocr
    .venv-ocr/bin/pip install paddleocr paddlepaddle python-dotenv pdf2image
    # + brew install poppler (already required by the project's `ocr` extra)

Usage (note the .venv-ocr interpreter) — always pin to ONE document, ONE page:
    PYTHONPATH=src .venv-ocr/bin/python scripts/334_paddleocr_structured.py \
        --sha <doc_sha>   # first page only by default

    PYTHONPATH=src .venv-ocr/bin/python scripts/334_paddleocr_structured.py \
        --sha <doc_sha> --max-pages 3 --seals   # explicit override, still small

    PYTHONPATH=src .venv-ocr/bin/python scripts/334_paddleocr_structured.py \
        --source-type dnr_land_order_pdf --dry-run   # scope check only, no OCR

BACKGROUND-FRIENDLY BY DEFAULT (2026-07-17): a real run was observed to
saturate the whole 8-core (4P+4E) machine for 15-30 min/page, making the
Mac unusable for anything else while it ran. Two independent throttles are
now on by default so this can run alongside interactive work:
  1. CPU thread pool capped to 3 (OMP/OpenBLAS/VECLIB/NUMEXPR env vars,
     set here BEFORE numpy/paddle import so they take effect — must be set
     this early, not inside main()) — override with --threads N.
  2. The process lowers its own OS scheduling priority (os.nice) so the
     kernel preempts it in favor of foreground apps — override with
     --full-priority to opt back into unthrottled (faster) execution.
Both cost wall-clock time (fewer threads + lower priority = slower per
page) in exchange for the machine staying usable — the right trade for a
tool whose whole point is "let it grind in the background."
"""
from __future__ import annotations

import os
import sys as _sys

# MUST run before numpy/paddle import — these libraries size their thread
# pools once at import time, so setting the env var after import has no
# effect. Parsed directly from sys.argv here (not via argparse, which runs
# later in main()) specifically so this can happen early enough.
_threads = "3"
if "--threads" in _sys.argv:
    _i = _sys.argv.index("--threads")
    if _i + 1 < len(_sys.argv):
        _threads = _sys.argv[_i + 1]
if "--full-priority" not in _sys.argv:
    for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                 "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ.setdefault(_var, _threads)

import argparse
import glob
import logging
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

_ADDR_CUE = re.compile(
    r"(ул\.?|вул\.?|улиц|проспект|пр-?кт|пр\.|бульвар|б-р|переул|кв\.?\s*\d|д\.\s*\d)",
    re.IGNORECASE)
# 15-30 MIN/PAGE measured on Apple Silicon CPU (2026-07-17, no GPU path
# exists for paddlepaddle here) — this is a hard ceiling, not a tunable
# default. --max-pages requires an explicit, deliberate override past 1.
_MAX_PAGES_PER_DOC = 1
_MAX_PAGES_HARD_CAP = 30  # even an explicit override can't exceed this (~15-22h
# at 30-45min/page with background throttling on); raised 2026-07-17 for a
# deliberate whole-document run, still a real ceiling against accidents


def _outdir() -> Path:
    d = config.DATA_DIR / "reports" / "paddle_ocr"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _docs(args, con) -> list[dict]:
    if args.sha:
        rows = con.execute(
            "SELECT sha256, raw_path, content_type FROM source_document WHERE sha256=?",
            (args.sha,)).fetchall()
    else:
        rows = con.execute(
            "SELECT sha256, raw_path, content_type FROM source_document "
            "WHERE source_type=? AND (content_type LIKE '%pdf%' OR content_type LIKE 'image/%') "
            "ORDER BY captured_at LIMIT ?", (args.source_type, args.limit)).fetchall()
    return [{"sha256": r[0], "raw_path": r[1], "content_type": r[2]} for r in rows]


def _page_count(raw: Path) -> int:
    from pdf2image import pdfinfo_from_path
    return int(pdfinfo_from_path(str(raw)).get("Pages", 0))


def _page_images(doc: dict, tmp_dir: Path, max_pages: int, start_page: int = 1):
    """PDF -> per-page JPGs (poppler), ONE PAGE AT A TIME (generator) — a
    25-page doc rasterized all-at-once via convert_from_path(first_page=1,
    last_page=N) was observed to OOM-kill the process on top of the already
    heavy multi-model pipeline; converting page-by-page bounds peak memory
    to ~1 rasterized page regardless of document length. A single image
    passes through as-is (one-element generator).

    start_page lets a specific page (e.g. the one with the actual table) be
    targeted directly, instead of burning 15-30 min/page walking pages 1..N-1
    just to reach it."""
    raw = Path(doc["raw_path"])
    if not raw.is_absolute():
        raw = config.PROJECT_ROOT / raw
    if not raw.exists():
        return
    if "pdf" in (doc["content_type"] or "").lower():
        from pdf2image import convert_from_path
        total = _page_count(raw)
        last = min(total, start_page + max_pages - 1)
        if start_page > total:
            log.error("%s has only %d pages, --start-page %d is out of range",
                     doc["sha256"][:12], total, start_page)
            return
        if last < start_page + max_pages - 1:
            log.info("%s has %d pages — clamped to page %d", doc["sha256"][:12], total, last)
        for i in range(start_page, last + 1):
            pages = convert_from_path(str(raw), dpi=200, first_page=i, last_page=i)
            if not pages:
                continue
            p = tmp_dir / f"{doc['sha256'][:12]}_p{i-1:03d}.jpg"
            pages[0].save(p, "JPEG", quality=85)
            del pages
            yield p
    else:
        yield raw


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sha", help="OCR a single captured document by sha256")
    ap.add_argument("--source-type", help="OCR documents of this raw source_type")
    ap.add_argument("--limit", type=int, default=1,
                    help="max documents (compute guardrail, default 1 — "
                         "this tool is for one hand-picked document at a "
                         "time, not a sweep)")
    ap.add_argument("--max-pages", type=int, default=_MAX_PAGES_PER_DOC,
                    help=f"max pages per document (default {_MAX_PAGES_PER_DOC}). "
                         f"~15-30 min/page on Apple Silicon CPU, no GPU path "
                         f"exists — raise only deliberately, hard-capped at "
                         f"{_MAX_PAGES_HARD_CAP}")
    ap.add_argument("--start-page", type=int, default=1,
                    help="1-indexed page to start from — target a specific "
                         "page (e.g. the one with the real table) directly "
                         "instead of walking from page 1")
    ap.add_argument("--seals", action="store_true",
                    help="also OCR official stamps/seals (slower; names issuing body)")
    ap.add_argument("--dry-run", action="store_true",
                    help="show scope, no model load / OCR")
    ap.add_argument("--threads", type=int, default=3,
                    help="CPU thread cap for numpy/paddle's math libraries "
                         "(default 3 of 8 cores) — parsed from sys.argv "
                         "BEFORE this argparse call so the env vars land "
                         "before numpy/paddle import; changing the default "
                         "here alone does nothing, see the top of the file")
    ap.add_argument("--full-priority", action="store_true",
                    help="skip both throttles (thread cap + os.nice) for "
                         "unthrottled, faster, but machine-hogging execution")
    args = ap.parse_args()

    if not args.sha and not args.source_type:
        log.error("need --sha or --source-type")
        sys.exit(1)
    if args.max_pages > _MAX_PAGES_HARD_CAP:
        log.error("--max-pages %d exceeds the hard cap of %d (~%.1f-%.1fh at "
                 "15-30 min/page) — this tool is for hand-picked single "
                 "documents, not bulk processing", args.max_pages,
                 _MAX_PAGES_HARD_CAP, _MAX_PAGES_HARD_CAP * 15 / 60,
                 _MAX_PAGES_HARD_CAP * 30 / 60)
        sys.exit(1)

    if not args.full_priority:
        try:
            os.nice(15)  # lower OS scheduling priority — let foreground apps preempt
            log.info("lowered process priority (os.nice +15) so this runs in the "
                     "background without hogging the machine; --full-priority to skip")
        except (AttributeError, PermissionError, OSError):
            log.warning("could not lower process priority (os.nice unsupported/denied) "
                       "— this may still saturate the machine while it runs")

    con = forensics.open_state()
    docs = _docs(args, con)
    print(f"\n{'='*72}\nPaddleOCR PP-StructureV3 (Cyrillic structured tables)")
    print(f"  scope: {'sha='+args.sha[:12] if args.sha else args.source_type}")
    print(f"  documents: {len(docs)} (limit {args.limit})")
    print(f"  max pages/doc: {args.max_pages} (~15-30 min/page on this hardware)")
    print(f"  seals: {'on' if args.seals else 'off'}")
    print(f"  background mode: {'off (--full-priority)' if args.full_priority else f'on (threads capped, nice +15)'}"
         f"\n{'='*72}")
    if not docs:
        con.close()
        return
    if args.dry_run:
        for d in docs:
            print(f"  {d['sha256'][:12]}  {d['content_type']}")
        con.close()
        return

    try:
        from paddleocr import PPStructureV3
    except ImportError:
        log.error("paddleocr not installed in THIS interpreter. Run under the "
                 "dedicated venv: PYTHONPATH=src .venv-ocr/bin/python %s ...", sys.argv[0])
        sys.exit(1)

    log.info("loading PP-StructureV3 (lang=ru) — first run downloads models ...")
    pipeline = PPStructureV3(
        lang="ru",
        use_table_recognition=True,
        use_seal_recognition=args.seals,
        use_formula_recognition=False,
        use_chart_recognition=False,
        use_doc_orientation_classify=True,   # scanned decrees are sometimes rotated
        use_doc_unwarping=False,             # flat scans, not curled photos
        use_textline_orientation=False,
    )

    outdir = _outdir()
    n_docs = n_tables = 0
    for doc in docs:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            md_parts: list[str] = []
            json_parts: list[dict] = []
            n_pages = 0
            # pages are rasterized ONE AT A TIME by _page_images (generator)
            # and freed as soon as each is OCR'd — holding an entire
            # multi-page document's bitmaps in memory alongside the heavy
            # PP-StructureV3 pipeline was observed to OOM-kill the process
            # on a 25-page document.
            for pi, page in enumerate(_page_images(doc, tmp_dir, args.max_pages, args.start_page)):
                n_pages += 1
                page_no = args.start_page + pi  # true 1-indexed PDF page, not offset-from-zero
                log.info("OCR %s — page %d", doc["sha256"][:12], page_no)
                results = pipeline.predict(input=str(page))
                for res in results:
                    res.save_to_markdown(save_path=str(tmp_dir))
                    res.save_to_json(save_path=str(tmp_dir))
                # read back what save_to_* wrote for this page
                for mf in sorted(tmp_dir.glob(f"{page.stem}*.md")):
                    md_parts.append(f"\n\n<!-- page {page_no} -->\n" + mf.read_text(encoding="utf-8"))
                    mf.unlink()
                for jf in sorted(tmp_dir.glob(f"{page.stem}*.json")):
                    import json as _json
                    json_parts.append({"page": page_no,
                                       "result": _json.loads(jf.read_text(encoding="utf-8"))})
                page.unlink(missing_ok=True)  # free the rasterized page immediately
            if n_pages == 0:
                log.warning("no pages for %s (missing file?)", doc["sha256"][:12])
                continue

            full_md = "".join(md_parts).strip()
            # PP-StructureV3 emits tables as EITHER markdown pipe-syntax OR
            # raw embedded HTML <table> — observed 2026-07-17 (a real 9-row
            # apartment schedule rendered as <table><tr><td>, not "|",
            # which the original "|" in full_md check silently missed and
            # misreported as "no table"). Check for both.
            has_table = ("|" in full_md) or ("<table" in full_md.lower())
            n_tables += 1 if has_table else 0

            # capture both artifacts with lineage to the source document
            forensics.capture_derived(
                full_md.encode("utf-8"), derived_from=doc["sha256"],
                transform="paddleocr_ppstructurev3_ru_markdown",
                source_type="osint_paddle_structured_md",
                title=f"paddle structured md {doc['sha256'][:12]}",
                description=(f"PP-StructureV3 (ru) Markdown of document "
                             f"{doc['sha256'][:16]} — text + tables as Markdown "
                             f"tables, {n_pages} page(s)."),
                content_type="text/markdown", con=con,
            )
            import json as _json
            forensics.capture_derived(
                _json.dumps(json_parts, ensure_ascii=False, default=str).encode("utf-8"),
                derived_from=doc["sha256"],
                transform="paddleocr_ppstructurev3_ru_json",
                source_type="osint_paddle_structured_json",
                title=f"paddle structured json {doc['sha256'][:12]}",
                description=(f"PP-StructureV3 (ru) full result (per-cell coords) "
                             f"for document {doc['sha256'][:16]}."),
                content_type="application/json", con=con,
            )

            # human-review copy
            addr_lines = [ln for ln in full_md.splitlines() if _ADDR_CUE.search(ln)]
            review = outdir / f"{doc['sha256'][:12]}.md"
            review.write_text(full_md + "\n", encoding="utf-8")
            n_docs += 1
            print(f"  [{n_docs}/{len(docs)}] {doc['sha256'][:12]}: "
                  f"{'table(s) found' if has_table else 'no table'}, "
                  f"{len(addr_lines)} address-shaped line(s) -> {review.name}")

    print(f"\ndone — {n_docs} documents OCR'd, {n_tables} contained tables")
    print(f"review markdown: {outdir}/")
    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
