#!/usr/bin/env python3
"""Stage 2k: two follow-on passes over the completed denis-pushilin.ru
archives-only crawl (script 39) + its index (script 43).

Part A -- lexicon review report. data/parsed/denis_pushilin_archive_index.jsonl
has 282 entries with lexicon_match=True and mariupol_match=False (NOTE: an
earlier memory note said "271" -- that was an arithmetic slip; the correct
per-archive breakdown 128+39+58+9+48 sums to 282). Writes a grouped markdown
report of all 282 (date/filename/title/description/sha) for manual scan --
no OCR, just re-reading the already-captured index text.

Part B -- "О предоставлении земельного участка" land-grant rasporyazheniya
(Распоряжения Главы ДНР). An earlier memory note said "770" such entries
existed in the rasporyazheniya_glavy archive vs. the network -- that figure
was also wrong. The actual count: the raw index page has only 11 substring
hits for "земельного участка", of which only 4 were captured (>=2022 date
filter): rasporiazhglavaN{192,203,204,205}_*2026.pdf, all dated 05-09 June
2026. All 4 are scanned images (pdfplumber returns 0 chars). This part OCRs
those 4 (same ocrmypdf pattern as script 44, forensics.capture_derived,
source_type denis_pushilin_doc_ocr_pdf), extracts text, and flags any
cadastral numbers (RRR:RR:NNNNNNN:NNNN) and "Мариупол" mentions for
cross-checking against data/parsed/dnr_land_orders.jsonl (51 rows).

Outputs:
  - data/reports/denis_pushilin_lexicon_review.md
  - data/parsed/denis_pushilin_land_grants_202606.jsonl

Local-only, no network. Run:
  PYTHONPATH=src .venv/bin/python scripts/45_review_lexicon_and_land_grants.py
"""
from __future__ import annotations

import json
import logging
import re
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
REPORTS_DIR = config.PROJECT_ROOT / "data" / "reports"

ARCHIVE_INDEX = PARSED_DIR / "denis_pushilin_archive_index.jsonl"

OCR_ARGS = ["--language", "rus", "--skip-text", "--rotate-pages", "--deskew"]
TRANSFORM = f"ocrmypdf {' '.join(OCR_ARGS)}"
_OCR_EXECUTABLE = str(Path(sys.executable).parent / "ocrmypdf")

_CADASTRAL_RE = re.compile(r"\d{2}:\d{2}:\d{6,7}:\d+")
_MARIUPOL_RE = re.compile(r"мариупол", re.IGNORECASE)

# filename -> (sha256, label)
LAND_GRANT_TARGETS: dict[str, tuple[str, str]] = {
    "rasporiazhglavaN205_09062026.pdf": (
        "9993dcc4879bd5c82d1360961f3c3de0da62ff58aaeb264941b27be9b707ab7d",
        "Распоряжение №205 от 09.06.2026 -- О предоставлении земельного участка",
    ),
    "rasporiazhglavaN204_09062026.pdf": (
        "9e9f17f292a23f60007efa4cf3f821139dde03c3160a7225bae9fcc68a6198d7",
        "Распоряжение №204 от 09.06.2026 -- О предоставлении земельного участка",
    ),
    "rasporiazhglavaN203_09062026.pdf": (
        "7875cff4286bbd9b30413fe327f1d738896f0d9e59da22fd9a36c2e265482fe3",
        "Распоряжение №203 от 09.06.2026 -- О предоставлении земельного участка",
    ),
    "rasporiazhglavaN192_05062026.pdf": (
        "9361aa6ac33dba010dd551aa7e40f35b06e4ecd660429b2639c04bc6a6121efd",
        "Распоряжение №192 от 05.06.2026 -- О предоставлении земельного участка",
    ),
}


def part_a_lexicon_review() -> None:
    rows = []
    with ARCHIVE_INDEX.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r.get("lexicon_match") and not r.get("mariupol_match"):
                rows.append(r)

    log.info("Part A: %d lexicon-matched, non-Мариуполь entries", len(rows))

    by_archive: dict[str, list[dict]] = {}
    for r in rows:
        by_archive.setdefault(r["archive"], []).append(r)

    lines = [
        "# denis-pushilin.ru lexicon-matched, non-Мариуполь entries -- "
        "review report",
        "",
        f"Total: {len(rows)} entries (script 43 index, "
        "lexicon_match=True, mariupol_match=False). Grouped by archive, "
        "sorted by date. Review for any Mariupol-relevant content not "
        "caught by the literal \"Мариуполь\" string match (e.g. property "
        "transferred to a Mariupol-based beneficiary, or a street address "
        "without the city name).",
        "",
    ]
    for archive, sub in by_archive.items():
        sub_sorted = sorted(sub, key=lambda r: r.get("filename_date") or "")
        lines.append(f"## {archive} ({len(sub_sorted)})")
        lines.append("")
        lines.append("| Date | Filename | Title | Description | SHA |")
        lines.append("|---|---|---|---|---|")
        for r in sub_sorted:
            lines.append(
                f"| {r.get('filename_date') or '?'} | `{r['filename']}` | "
                f"{r['title_text']} | {r['description_text']} | "
                f"`{r['sha256'][:12]}..` |"
            )
        lines.append("")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORTS_DIR / "denis_pushilin_lexicon_review.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    log.info("wrote %s", out_path)


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


def part_b_land_grants() -> None:
    con = forensics.open_state()
    out_rows = []

    for filename, (sha, label) in LAND_GRANT_TARGETS.items():
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
                    f"sha256={sha}). Transform: {TRANSFORM}. Land-grant "
                    "rasporyazheniye, screened for Mariupol relevance "
                    "(scripts/45). Derived artifact -- raw scan "
                    f"({sha[:16]}..) remains the immutable original."
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

        cadastral_numbers = sorted(set(_CADASTRAL_RE.findall(text)))
        mariupol_mention = bool(_MARIUPOL_RE.search(text))

        out_rows.append({
            "filename": filename,
            "label": label,
            "source_sha256": sha,
            "ocr_sha256": ocr_sha,
            "text": text.strip(),
            "cadastral_numbers": cadastral_numbers,
            "mariupol_mention": mariupol_mention,
        })
        log.info(
            "%s: extracted %d chars, cadastral=%s, mariupol_mention=%s",
            filename, len(text), cadastral_numbers, mariupol_mention,
        )

    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PARSED_DIR / "denis_pushilin_land_grants_202606.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for r in out_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    log.info("wrote %s (%d rows)", out_path, len(out_rows))

    mariupol_93_37 = [
        r for r in out_rows
        if r["mariupol_mention"]
        or any(c.startswith("93:37") for c in r["cadastral_numbers"])
    ]
    if mariupol_93_37:
        log.warning(
            "%d/4 land-grant decrees mention Мариуполь or cadastral "
            "prefix 93:37 -- cross-check against dnr_land_orders.jsonl "
            "(51 rows) for a possible Tier 4 addition",
            len(mariupol_93_37),
        )
    else:
        log.info(
            "0/4 land-grant decrees mention Мариуполь or cadastral prefix "
            "93:37 -- likely out of scope"
        )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    part_a_lexicon_review()
    part_b_land_grants()


if __name__ == "__main__":
    main()
