#!/usr/bin/env python3
"""OCR + keyword-triage the /doc/GKO/ subfolder of the denis-pushilin.ru
archive (scripts/39, scripts/247's survey) -- 130 image-only PDFs, the
highest-value-per-effort slice of the 2,391 image-only backlog: every
GKO decree previously read individually in this project (No. 162/205/245/
300/164/263/175/282/341/56) came from exactly this folder, and its filenames
encode the decree number directly (Post_GKO_<N>.pdf), so no OCR is needed
just to know WHICH decrees these are -- only to read their content.

Run from .venv312 (pytesseract/pdf2image live there, not the default .venv):
    .venv312/bin/python3 scripts/248_ocr_survey_gko_folder.py
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

STATE_DB = ROOT / "data" / "state.sqlite"
OUT_DIR = ROOT / "data" / "parsed" / "pushilin_gko_ocr"
OUT_DIR.mkdir(parents=True, exist_ok=True)
INDEX_PATH = ROOT / "data" / "parsed" / "pushilin_gko_survey.jsonl"

KEYWORDS = [
    "Мариуполь", "Мариуполя", "Мариуполю",
    "бесхозя", "изъят", "снос", "аварийны", "маневренн",
    "земельного участка", "инвестиционного проекта", "без проведения торгов",
    "муниципальной собственности", "государственной собственности",
    "ипотек", "многоквартирн", "жилищн", "выселен", "компенсаци",
    "ЕГРН", "кадастров", "инвентаризац",
]
KEYWORD_RE = re.compile("|".join(re.escape(k) for k in KEYWORDS))


def main() -> None:
    from pdf2image import convert_from_path
    import pytesseract

    con = sqlite3.connect(STATE_DB)
    cur = con.cursor()
    cur.execute("SELECT sha256, url, raw_path FROM source_document WHERE source_type = 'denis_pushilin_doc_pdf'")
    all_rows = cur.fetchall()
    gko = [(sha, url, path) for sha, url, path in all_rows if "/doc/GKO/" in url]
    print(f"{len(gko)} GKO PDFs to OCR", file=sys.stderr)

    with open(INDEX_PATH, "w", encoding="utf-8") as out:
        for i, (sha, url, raw_path) in enumerate(gko, 1):
            print(f"  [{i}/{len(gko)}] {url}", file=sys.stderr)
            txt_path = OUT_DIR / f"{sha}.txt"
            if not txt_path.exists():
                try:
                    pages = convert_from_path(raw_path, dpi=200)
                    text = "\n".join(pytesseract.image_to_string(p, lang="rus") for p in pages)
                    txt_path.write_text(text, encoding="utf-8")
                except Exception as e:
                    out.write(json.dumps({"sha256": sha, "url": url, "error": str(e)}, ensure_ascii=False) + "\n")
                    continue
            else:
                text = txt_path.read_text(encoding="utf-8", errors="replace")

            m = re.search(r"Post_GKO_(\d+)", url)
            decree_no = m.group(1) if m else None
            matched_kw = sorted(set(KEYWORD_RE.findall(text)))
            out.write(json.dumps({
                "sha256": sha, "url": url, "decree_no": decree_no,
                "text_len": len(text.strip()), "keywords": matched_kw,
                "first_300": text.strip()[:300],
            }, ensure_ascii=False) + "\n")
            out.flush()

    print(f"Done. Index: {INDEX_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
