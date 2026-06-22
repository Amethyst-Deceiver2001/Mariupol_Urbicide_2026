#!/usr/bin/env python3
"""Ingest the ИЖС_бесхоз_Мариуполь PDF into the corroboration table.

Source: PDF shared in the Олімпійська Telegram chat (msg 25765, 2023-03-27),
already captured to data/raw/ with sha256=29efe8770976e77723f47f866ae13c2b788c6bd78e44e28bde8f940690c11a81.

The PDF is the occupation administration's list of private homes (ИЖС) declared
бесхозяйные in Приморський district, shared by a resident after the 30-day notice
was posted. Extracted with pdftotext: structured table, columns №/Район/Адрес/№дома.

This script:
  1. Re-extracts text from the raw PDF blob.
  2. Parses rows: district / street / house_no.
  3. Fuzzy-matches each entry against the property spine (property.occupation_address).
  4. Loads matches as corroboration rows (source_type='ijss_ownerless_list').
  5. Dumps full address list to data/parsed/ijss_ownerless_list.jsonl for review.

Run:
    python scripts/84_ingest_ijss_ownerless_pdf.py [--dry-run]
"""
import argparse
import json
import logging
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

PDF_SHA  = "29efe8770976e77723f47f866ae13c2b788c6bd78e44e28bde8f940690c11a81"
PDF_PATH = ROOT / "data" / "raw" / f"{PDF_SHA}.pdf"
OUT      = ROOT / "data" / "parsed" / "ijss_ownerless_list.jsonl"
SOURCE_TYPE = "ijss_ownerless_list"
CONFIDENCE  = 0.85

# Occupation street-type abbreviations → canonical
STREET_NORM = {
    "ул.": "улица", "пер.": "переулок", "пр.": "проспект",
    "б-р": "бульвар", "пл.": "площадь", "ш.": "шоссе",
}


def _extract_text(pdf_path: Path) -> str:
    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pdftotext failed: {result.stderr[:200]}")
    return result.stdout


_ROW_START = re.compile(r"^\s*(\d{1,4})\s")


def _parse_pdf(text: str) -> list[dict]:
    """Parse the 4-column layout-preserved table: №/Район/Адрес/№дома.

    With -layout, pdftotext preserves spatial alignment so each data row is a
    single line: <num>  <district>  <street>  <house_no> separated by 2+ spaces.
    Split on \\s{2,} to recover the four fields cleanly.
    """
    entries = []
    for line in text.split("\n"):
        if not _ROW_START.match(line):
            continue
        parts = re.split(r"\s{2,}", line.strip())
        if len(parts) < 4:
            continue
        try:
            num = int(parts[0])
        except ValueError:
            continue
        district = parts[1].strip()
        street   = parts[2].strip()
        house    = parts[3].strip()
        if not (district and street and house):
            continue
        entries.append({
            "num": num,
            "district": district,
            "street": street,
            "house": house,
            "address_raw": f"{street}, {house}",
        })
    return entries


def _fuzzy_match(addr: str, conn) -> tuple[int | None, float]:
    """Match address string against property.occupation_address using rapidfuzz."""
    try:
        from rapidfuzz import process, fuzz
    except ImportError:
        log.warning("rapidfuzz not installed — skipping fuzzy match")
        return None, 0.0

    cur = conn.cursor()
    cur.execute("SELECT id, occupation_address FROM property WHERE occupation_address IS NOT NULL")
    candidates = {row[0]: row[1] for row in cur.fetchall()}

    # extractOne with dict returns (matched_value, score, key) — key is the dict key (property id)
    _, best_score, best_id = process.extractOne(
        addr, candidates,
        scorer=fuzz.token_sort_ratio,
    )
    return best_id, best_score / 100.0


def main(dry_run: bool = False) -> None:
    if not PDF_PATH.exists():
        # Try to find it via forensics store
        con = forensics.open_state()
        row = con.execute(
            "SELECT raw_path FROM source_document WHERE sha256=?", (PDF_SHA,)
        ).fetchone()
        if row and row[0]:
            pdf_actual = ROOT / row[0]
        else:
            log.error("PDF not found at %s and not in forensics store", PDF_PATH)
            return
    else:
        pdf_actual = PDF_PATH

    log.info("extracting text from %s", pdf_actual)
    text = _extract_text(pdf_actual)

    entries = _parse_pdf(text)
    log.info("parsed %d address entries from PDF", len(entries))

    # Write parsed list
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        for e in entries:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    log.info("wrote %d entries to %s", len(entries), OUT)

    if dry_run:
        log.info("dry-run: skipping DB load")
        # Print sample
        for e in entries[:20]:
            print(f"  {e['num']:4d}  {e['district']:<20}  {e['address_raw']}")
        print(f"  ... ({len(entries)} total)")
        return

    import psycopg2
    from mariupol_seizures.db.load import _upsert_source_doc_by_sha  # noqa: E402
    conn = psycopg2.connect(config.DATABASE_URL)
    cur  = conn.cursor()

    # Upsert PDF into PG source_document and get its integer id
    src_doc_id = _upsert_source_doc_by_sha(cur, PDF_SHA)

    loaded = matched = 0

    for e in entries:
        pid, score = _fuzzy_match(e["address_raw"], conn)
        e["matched_property_id"] = pid
        e["match_score"] = round(score, 3)

        loaded += 1

        if pid and score >= CONFIDENCE:
            dedup_key = f"ijss_ownerless_{e['num']}"
            detail = json.dumps({
                "list_no":       e["num"],
                "district":      e["district"],
                "street":        e["street"],
                "house":         e["house"],
                "address_raw":   e["address_raw"],
                "source_pdf_sha": PDF_SHA,
                "chat_url":      "https://t.me/olimpiyskaya_71_79/25765",
                "list_date":     "2023-03-27",
                "note": (
                    "Occupation admin list of ИЖС with бесхозяйность signs, "
                    "shared by resident 2023-03-27 in Олімпійська resident chat. "
                    "30-day claim window before municipal transfer."
                ),
            }, ensure_ascii=False)
            cur.execute("""
                INSERT INTO corroboration
                  (property_id, kind, reference, source_doc_id, confidence,
                   detail, dedup_key, captured_at, verdict)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), 'confirms')
                ON CONFLICT (dedup_key) DO UPDATE
                    SET confidence   = EXCLUDED.confidence,
                        detail       = EXCLUDED.detail,
                        captured_at  = NOW()
            """, (
                pid, SOURCE_TYPE,
                "https://t.me/olimpiyskaya_71_79/25765",
                src_doc_id, score, detail, dedup_key,
            ))
            matched += 1

    conn.commit()
    conn.close()

    print(f"\n{'='*60}")
    print(f"ИЖС ownerless list ingest complete")
    print(f"  Entries parsed   : {len(entries)}")
    print(f"  Attempted match  : {loaded}")
    print(f"  Loaded to DB     : {matched}  (score ≥ {CONFIDENCE})")
    print(f"  Full list        : {OUT}")
    print(f"{'='*60}\n")

    # Print unmatched for review
    unmatched = [e for e in entries if e.get("match_score", 0) < CONFIDENCE]
    if unmatched:
        print(f"Unmatched ({len(unmatched)}) — address may need manual review:")
        for e in unmatched[:20]:
            print(f"  {e['address_raw']}  score={e.get('match_score', 0):.2f}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
