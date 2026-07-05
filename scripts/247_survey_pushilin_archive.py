#!/usr/bin/env python3
"""One-time survey of the denis-pushilin.ru archive crawl (scripts/39):
2,833 PDFs captured, but only ~29 have ever been individually read/OCR'd --
everything cited by name in docs/legal_mechanisms_review.md so far came from
targeted pulls, not a systematic pass over the whole archive.

This is a local, offline text-extraction + keyword-triage job over already-
captured raw bytes -- no network access, no geoblocking concern, safe to run
directly (unlike the crawl scripts, which the user runs themselves).

Extracts plain text for every captured PDF (pdftotext; falls back to marking
image-only scans for a later OCR pass) and greps the result against a
curated keyword list of Mariupol-property/seizure terms, to surface
candidate documents worth an individual read -- without pretending to
"analyze" 2,800 files by just running a keyword grep.

Run:
    python3 scripts/247_survey_pushilin_archive.py
"""
from __future__ import annotations

import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

STATE_DB = ROOT / "data" / "state.sqlite"
OUT_DIR = ROOT / "data" / "parsed" / "pushilin_archive_text"
OUT_DIR.mkdir(parents=True, exist_ok=True)
INDEX_PATH = ROOT / "data" / "parsed" / "pushilin_archive_survey.jsonl"

# Mariupol-property/seizure-relevant keywords -- deliberately broad; this is
# a triage pass, not a claim-grade extraction. Case-sensitive Cyrillic only.
KEYWORDS = [
    "Мариуполь", "Мариуполя", "Мариуполю",
    "бесхозя", "изъят", "снос", "аварийны", "маневренн",
    "земельного участка", "инвестиционного проекта", "без проведения торгов",
    "муниципальной собственности", "государственной собственности",
    "ипотек", "многоквартирн", "жилищн", "выселен", "компенсаци",
    "ЕГРН", "кадастров",
]
KEYWORD_RE = re.compile("|".join(re.escape(k) for k in KEYWORDS))


def already_read_shas() -> set[str]:
    """sha256 of the ~29 already-OCR'd/read denis_pushilin_doc_ocr_pdf rows,
    so the survey doesn't re-flag documents already worked through."""
    con = sqlite3.connect(STATE_DB)
    cur = con.cursor()
    cur.execute("SELECT sha256 FROM source_document WHERE source_type = 'denis_pushilin_doc_ocr_pdf'")
    return {r[0] for r in cur.fetchall()}


def main() -> None:
    con = sqlite3.connect(STATE_DB)
    cur = con.cursor()
    cur.execute("SELECT sha256, url, raw_path FROM source_document WHERE source_type = 'denis_pushilin_doc_pdf'")
    rows = cur.fetchall()
    print(f"{len(rows)} PDFs to survey", file=sys.stderr)

    already_read = already_read_shas()

    hits = 0
    empty = 0
    with open(INDEX_PATH, "w", encoding="utf-8") as out:
        for i, (sha, url, raw_path) in enumerate(rows, 1):
            if i % 200 == 0:
                print(f"  {i}/{len(rows)}...", file=sys.stderr)
            txt_path = OUT_DIR / f"{sha}.txt"
            if not txt_path.exists():
                try:
                    result = subprocess.run(
                        ["pdftotext", raw_path, str(txt_path)],
                        capture_output=True, timeout=30,
                    )
                except Exception as e:
                    out.write(json.dumps({"sha256": sha, "url": url, "error": str(e)}, ensure_ascii=False) + "\n")
                    continue
                if result.returncode != 0:
                    out.write(json.dumps({"sha256": sha, "url": url, "error": result.stderr.decode(errors="replace")[:200]}, ensure_ascii=False) + "\n")
                    continue

            text = txt_path.read_text(encoding="utf-8", errors="replace") if txt_path.exists() else ""
            text_len = len(text.strip())
            if text_len < 20:
                empty += 1
                out.write(json.dumps({"sha256": sha, "url": url, "text_len": text_len, "image_only": True}, ensure_ascii=False) + "\n")
                continue

            matched_kw = sorted(set(KEYWORD_RE.findall(text)))
            record = {
                "sha256": sha,
                "url": url,
                "text_len": text_len,
                "keywords": matched_kw,
                "already_read": sha in already_read,
            }
            if matched_kw:
                hits += 1
            out.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Done. {hits} keyword hits, {empty} image-only/empty (need OCR to survey), "
          f"index written to {INDEX_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
