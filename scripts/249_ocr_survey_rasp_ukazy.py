#!/usr/bin/env python3
"""OCR + keyword-triage the /doc/rasp/ (728) and /doc/ukazy/ (1,538) subfolders
of the denis-pushilin.ru archive -- the last two untouched chunks of the
2,833-PDF archive (scripts/247 covered zakony/akty by text-extraction;
scripts/248 covered the GKO folder by OCR and found a genuine new
expropriation-mechanism finding written up in docs/legal_mechanisms_review.md).

This is the big one: ~2,266 image-only scanned PDFs, but only decrees dated
on or after 24.02.2022 (invasion date) can possibly bear on occupation-era
property seizure, so this filters by the date embedded in each filename
(`..._DDMMYYYY.pdf`) BEFORE queuing any OCR work -- checked 2026-07-06:
2,227 of 2,266 are already >=24.02.2022; the ~39 excluded are either
genuinely pre-war (oldest found: 2018) or have a non-standard filename date
format that couldn't be parsed -- those unparseable ones are logged to
stderr and SKIPPED by default (rerun with --include-unparseable-dates to
force them through if you want the handful checked anyway).

At the GKO folder's observed rate this will still take HOURS, not minutes --
run it yourself in a terminal you can leave running, not something to
fire-and-forget from an agent session. Resumable: re-running skips any
sha256 whose .txt already exists in the output dir, so Ctrl-C and restart
is safe.

Setup (one-time, if not already done for this project):
    source .venv312/bin/activate   # or: .venv312/bin/python3 directly

Run (both folders, default):
    .venv312/bin/python3 scripts/249_ocr_survey_rasp_ukazy.py
Run one folder only:
    .venv312/bin/python3 scripts/249_ocr_survey_rasp_ukazy.py --folder rasp
    .venv312/bin/python3 scripts/249_ocr_survey_rasp_ukazy.py --folder ukazy
Limit for a test run:
    .venv312/bin/python3 scripts/249_ocr_survey_rasp_ukazy.py --limit 20
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

STATE_DB = ROOT / "data" / "state.sqlite"
OUT_DIR = ROOT / "data" / "parsed" / "pushilin_rasp_ukazy_ocr"
OUT_DIR.mkdir(parents=True, exist_ok=True)
INDEX_PATH = ROOT / "data" / "parsed" / "pushilin_rasp_ukazy_survey.jsonl"

KEYWORDS = [
    "Мариуполь", "Мариуполя", "Мариуполю",
    "бесхозя", "изъят", "снос", "аварийны", "маневренн",
    "земельного участка", "инвестиционного проекта", "без проведения торгов",
    "муниципальной собственности", "государственной собственности",
    "ипотек", "многоквартирн", "жилищн", "выселен", "компенсаци",
    "ЕГРН", "кадастров", "инвентаризац",
]
KEYWORD_RE = re.compile("|".join(re.escape(k) for k in KEYWORDS))

INVASION_DATE = (2022, 2, 24)  # (year, month, day) -- exclude anything strictly before this
_DATE_RE = re.compile(r"(\d{2})(\d{2})(\d{4})")  # first DDMMYYYY run found in the filename


def parse_filename_date(url: str) -> tuple[int, int, int] | None:
    """Best-effort DDMMYYYY extraction from denis-pushilin.ru filenames.
    Handles the standard `..._DDMMYYYY.pdf` shape and tolerates the small
    number of malformed variants (extra digit, missing underscore, etc.) by
    just taking the first 8-digit run; returns None if nothing parses to a
    plausible date."""
    name = url.rsplit("/", 1)[-1]
    for m in _DATE_RE.finditer(name):
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= d <= 31 and 1 <= mo <= 12 and 2015 <= y <= 2027:
            return (y, mo, d)
    return None


def is_in_scope(url: str, include_unparseable: bool) -> bool:
    parsed = parse_filename_date(url)
    if parsed is None:
        return include_unparseable
    y, mo, d = parsed
    return (y, mo, d) >= INVASION_DATE


def already_done_shas() -> set[str]:
    if not INDEX_PATH.exists():
        return set()
    done = set()
    with open(INDEX_PATH, encoding="utf-8") as f:
        for line in f:
            try:
                done.add(json.loads(line)["sha256"])
            except Exception:
                continue
    return done


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", choices=["rasp", "ukazy", "both"], default="both")
    ap.add_argument("--limit", type=int, default=None, help="cap number of PDFs (for a test run)")
    ap.add_argument("--include-unparseable-dates", action="store_true",
                     help="also OCR the handful of files whose filename date couldn't be parsed "
                          "(default: skip them, logged to stderr)")
    args = ap.parse_args()

    from pdf2image import convert_from_path
    import pytesseract

    con = sqlite3.connect(STATE_DB)
    cur = con.cursor()
    cur.execute("SELECT sha256, url, raw_path FROM source_document WHERE source_type = 'denis_pushilin_doc_pdf'")
    all_rows = cur.fetchall()

    def folder_of(u: str) -> str:
        m = re.match(r"https?://[^/]+/doc/([^/]+)/", u)
        return m.group(1) if m else "(other)"

    wanted = {"rasp", "ukazy"} if args.folder == "both" else {args.folder}
    in_folder = [(sha, url, path) for sha, url, path in all_rows if folder_of(url) in wanted]

    targets = []
    skipped_prewar = 0
    skipped_unparseable = 0
    for sha, url, path in in_folder:
        parsed = parse_filename_date(url)
        if parsed is None:
            if not args.include_unparseable_dates:
                skipped_unparseable += 1
                print(f"  SKIP (unparseable date): {url}", file=sys.stderr)
                continue
        elif parsed < INVASION_DATE:
            skipped_prewar += 1
            continue
        targets.append((sha, url, path))

    print(f"{len(in_folder)} in {wanted}, excluded {skipped_prewar} pre-24.02.2022 "
          f"+ {skipped_unparseable} unparseable-date -> {len(targets)} in scope", file=sys.stderr)

    if args.limit is not None:
        targets = targets[: args.limit]

    done = already_done_shas()
    remaining = [t for t in targets if t[0] not in done]
    print(f"{len(targets)} total in scope, {len(done)} already done, {len(remaining)} remaining", file=sys.stderr)

    with open(INDEX_PATH, "a", encoding="utf-8") as out:
        start = time.time()
        for i, (sha, url, raw_path) in enumerate(remaining, 1):
            if i % 20 == 0:
                elapsed = time.time() - start
                rate = elapsed / i
                eta_min = rate * (len(remaining) - i) / 60
                print(f"  [{i}/{len(remaining)}] elapsed={elapsed/60:.1f}min ETA={eta_min:.0f}min -- {url}", file=sys.stderr)

            txt_path = OUT_DIR / f"{sha}.txt"
            if not txt_path.exists():
                try:
                    pages = convert_from_path(raw_path, dpi=200)
                    text = "\n".join(pytesseract.image_to_string(p, lang="rus") for p in pages)
                    txt_path.write_text(text, encoding="utf-8")
                except Exception as e:
                    out.write(json.dumps({"sha256": sha, "url": url, "error": str(e)}, ensure_ascii=False) + "\n")
                    out.flush()
                    continue
            else:
                text = txt_path.read_text(encoding="utf-8", errors="replace")

            matched_kw = sorted(set(KEYWORD_RE.findall(text)))
            out.write(json.dumps({
                "sha256": sha, "url": url, "folder": folder_of(url),
                "text_len": len(text.strip()), "keywords": matched_kw,
                "first_300": text.strip()[:300],
            }, ensure_ascii=False) + "\n")
            out.flush()

    print(f"Done. Index: {INDEX_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
