#!/usr/bin/env python3
"""Re-parse all memorial.ua obituary pages already captured by scripts/305
(source_type "memorial_ua_obituary_page" in the sqlite state DB) with a
corrected field extractor -- scripts/305's original parser had two bugs:

  1. "Вік" (age) had no stop-boundary at "Дата народження" (date of birth,
     not in FIELD_LABELS), so it swallowed that whole next field too, e.g.
     age="23 Дата народження 16 жовтня 1998" instead of age="23".
  2. "Дата загибелі" (date of death) is always the LAST field in the
     personal-data block, with no other FIELD_LABEL following it within the
     bounded {2,80}? capture window -- and the true end-of-text `$` is
     thousands of characters away (the life-story narrative follows) -- so
     the regex could never match at all and the field was silently dropped
     for every single row.

Fixed here by adding "Дата народження" / "Платформа пам'яті Меморіал" /
"Історія життя" as universal stop-boundaries (present on every page,
reliably close after the last personal-data field).

Pure local reprocessing of already-captured raw HTML -- no network request,
so unlike scripts/305 this is safe for Claude to run directly.

Output: data/parsed/memorial_ua_obituaries.jsonl (all captured pages,
Mariupol-matched or not) + a corrected
data/reports/memorial_ua_mariupol_leads.csv (replaces scripts/305's
original, which had the age/death_date bugs above).
"""
from __future__ import annotations

import csv
import json
import logging
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402

log = logging.getLogger(__name__)

SOURCE_TYPE = "memorial_ua_obituary_page"
OUT_JSONL = ROOT / "data" / "parsed" / "memorial_ua_obituaries.jsonl"
OUT_LEADS = ROOT / "data" / "reports" / "memorial_ua_mariupol_leads.csv"

MARIUPOL_RE = re.compile(r"маріупол|mariupol", re.IGNORECASE)

FIELD_LABELS = {
    "Місто загибелі": "death_city",
    "Місто народження": "birth_city",
    "Область загибелі": "death_oblast",
    "Дата загибелі": "death_date",
    "Вік": "age",
    "Професія": "profession",
}
# Present on every page, immediately after the personal-data block --
# universal stop-boundaries so the LAST personal-data field (Дата загибелі)
# has something to terminate on within the bounded capture window.
EXTRA_STOPS = ["Дата народження", "Платформа пам'яті Меморіал", "Історія життя"]
ALL_STOPS = list(FIELD_LABELS.keys()) + EXTRA_STOPS


def parse_fields(html: bytes) -> dict:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    name = ""
    h1 = soup.find("h1")
    if h1:
        name = h1.get_text(" ", strip=True)

    fields = {}
    for label, key in FIELD_LABELS.items():
        stops = [s for s in ALL_STOPS if s != label]
        pat = (re.escape(label) + r"\s*(.{1,80}?)\s*(?:" +
               "|".join(re.escape(s) for s in stops) + r")")
        m = re.search(pat, text)
        if m:
            fields[key] = m.group(1).strip(" .,")

    # The story block is followed by related-victims lists and then site
    # chrome/footer (nav menu, org contact info incl. memorial.ua's own Kyiv
    # office address -- a real bug caught in review: an early version of
    # this parser let the story run unbounded into that footer text, which
    # then looked like a Mariupol street address in downstream matching).
    # Cut at whichever of these appears first.
    story = ""
    m = re.search(r"Історія життя\s*(.*?)(?:Загиблі рідні|Загиблі однієї професії|"
                  r"Розкажіть про героя|$)", text)
    if m:
        story = m.group(1).strip()

    return {"name": name, **fields, "story_full": story, "story_excerpt": story[:600],
            "raw_text_len": len(text)}


def main() -> None:
    con = sqlite3.connect(config.STATE_DB)
    rows = con.execute(
        "SELECT url, raw_path FROM source_document WHERE source_type=?", (SOURCE_TYPE,)
    ).fetchall()
    log.info("found %d captured memorial.ua pages", len(rows))

    parsed = []
    leads = []
    missing = 0
    for url, raw_path in rows:
        p = Path(raw_path)
        if not p.exists():
            missing += 1
            continue
        html = p.read_bytes()
        fields = parse_fields(html)
        rec = {"url": url, **fields}
        parsed.append(rec)

        # Match on the structured city fields only, not the free-text story --
        # the story often mentions Mariupol in passing (fled from, visited,
        # etc.) for people who neither died nor were born there, which would
        # loosen this from "Mariupol victim" to "anyone whose story mentions
        # Mariupol". death_city/birth_city are the precise signal.
        haystack = " ".join(str(fields.get(k, "")) for k in ("death_city", "birth_city"))
        if MARIUPOL_RE.search(haystack):
            leads.append(rec)

    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSONL.open("w", encoding="utf-8") as f:
        for r in parsed:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    OUT_LEADS.parent.mkdir(parents=True, exist_ok=True)
    with OUT_LEADS.open("w", encoding="utf-8", newline="") as f:
        fieldnames = ["url", "name", "death_city", "birth_city", "death_oblast",
                      "death_date", "age", "profession", "story_excerpt", "raw_text_len"]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in leads:
            w.writerow({k: r.get(k, "") for k in fieldnames})

    death_date_filled = sum(1 for r in parsed if r.get("death_date"))
    age_clean = sum(1 for r in parsed if r.get("age") and len(r["age"]) <= 3)

    log.info("=== SUMMARY ===")
    log.info("missing raw files: %d", missing)
    log.info("parsed: %d", len(parsed))
    log.info("death_date now populated: %d (was 0 in scripts/305's original run)", death_date_filled)
    log.info("age field clean (<=3 chars): %d", age_clean)
    log.info("Mariupol matches: %d", len(leads))
    log.info("written -> %s", OUT_JSONL)
    log.info("written -> %s (replaces scripts/305's buggy leads file)", OUT_LEADS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
