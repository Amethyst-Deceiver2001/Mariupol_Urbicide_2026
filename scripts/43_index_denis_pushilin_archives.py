#!/usr/bin/env python3
"""Stage 2i: index the completed denis-pushilin.ru archives-only crawl (script 39).

The user ran `scripts/39_crawl_denis_pushilin.py --archives-only` to completion
(2026-06-12): 2,894 `denis_pushilin_doc_pdf` PDFs + 6 `denis_pushilin_doc_index`
archive-listing pages already in the raw store. This script is local-only (no
network) and re-runnable.

For each of the 6 archive-listing pages, re-parses the `<a href="...pdf">title</a>
description` entries (decree number/date + subject-line description), joins each
entry to its captured PDF by URL (source_document.url -> sha256), and flags:

  - lexicon_match: title+description matches DISPOSSESSION_LEXICON
    (same lexicon as scripts/35_crawl_pravo_region80.py / 37)
  - mariupol_match: title+description mentions "Мариуполь" (ё-folded,
    case-insensitive)

Output: data/parsed/denis_pushilin_archive_index.jsonl (one row per captured PDF
that has a matching index-page entry) + data/reports/denis_pushilin_index_report.md
(per-archive counts, lexicon/Мариуполь hit lists).

Entries with no index-page match (e.g. PDF captured but link text not parsed) are
logged but not dropped from the count -- they just lack title/description text.

Run locally, no network: python3 scripts/43_index_denis_pushilin_archives.py
"""
from __future__ import annotations

import json
import logging
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402
from mariupol_seizures.crawl.pravo_region80 import is_relevant  # noqa: E402

log = logging.getLogger(__name__)

PARSED_DIR = config.PROJECT_ROOT / "data" / "parsed"
REPORTS_DIR = config.PROJECT_ROOT / "data" / "reports"

# label -> archive-listing page URL (matches denis_pushilin.DATED_ARCHIVE_SLUGS +
# UNDATED_ARCHIVE_SLUGS)
ARCHIVES: dict[str, str] = {
    "ukazy_glavy": "https://denis-pushilin.ru/akty-glavy-dnr/ukazy/",
    "rasporyazheniya_glavy": "https://denis-pushilin.ru/akty-glavy-dnr/rasporyazheniya/",
    "zakony": "https://denis-pushilin.ru/zakony/",
    "akty_ees": "https://denis-pushilin.ru/akty-glavy-dnr/akty-edinogo-ekonomicheskogo-soveta/",
    "postanovleniya_gko": "https://denis-pushilin.ru/postanovleniya-gosudarstvennogo-komiteta-oborony/",
    "rasporyazheniya_gko": "https://denis-pushilin.ru/rasporyazheniya-gosudarstvennogo-komiteta-oborony/",
}

_PDF_LINK_RE = re.compile(
    r'<a href="(https://denis-pushilin\.ru/[^"]*?\.pdf)"[^>]*>([^<]*)</a>\s*([^<\n]{0,200})'
)
_PDF_DATE_RE = re.compile(r"_(\d{2})(\d{2})(\d{4})\.pdf$", re.I)
_MARIUPOL_RE = re.compile(r"мариупол", re.IGNORECASE)


def _parse_index_page(html: str) -> dict[str, dict]:
    """pdf_url -> {filename, title_text, description_text}."""
    out: dict[str, dict] = {}
    for url, title, desc in _PDF_LINK_RE.findall(html):
        out[url] = {
            "filename": url.rsplit("/", 1)[-1],
            "title_text": title.strip(),
            "description_text": desc.strip(),
        }
    return out


def _pdf_date(filename: str) -> str | None:
    m = _PDF_DATE_RE.search(filename)
    if not m:
        return None
    dd, mm, yyyy = m.groups()
    return f"{yyyy}-{mm}-{dd}"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")

    con = forensics.open_state()

    index_html: dict[str, str] = {}
    for sha, url, raw_path in con.execute(
        "SELECT sha256, url, raw_path FROM source_document "
        "WHERE source_type='denis_pushilin_doc_index'"
    ):
        index_html[url] = Path(raw_path).read_text(encoding="utf-8", errors="replace")

    pdf_sha: dict[str, str] = {}
    for sha, url in con.execute(
        "SELECT sha256, url FROM source_document WHERE source_type='denis_pushilin_doc_pdf'"
    ):
        pdf_sha[url] = sha

    log.info("loaded %d archive-index pages, %d captured PDFs", len(index_html), len(pdf_sha))

    rows: list[dict] = []
    unmatched_pdfs: list[str] = []
    archive_entry_counts: Counter[str] = Counter()

    matched_urls: set[str] = set()
    for label, index_url in ARCHIVES.items():
        html = index_html.get(index_url)
        if html is None:
            log.warning("missing index page for %s (%s)", label, index_url)
            continue
        entries = _parse_index_page(html)
        log.info("%s: %d <a>.pdf entries on index page", label, len(entries))
        for pdf_url, e in entries.items():
            sha = pdf_sha.get(pdf_url)
            if sha is None:
                continue  # not captured (date-filtered or HTTP error)
            matched_urls.add(pdf_url)
            blob = f"{e['title_text']} {e['description_text']}"
            rows.append({
                "archive": label,
                "pdf_url": pdf_url,
                "filename": e["filename"],
                "filename_date": _pdf_date(e["filename"]),
                "title_text": e["title_text"],
                "description_text": e["description_text"],
                "sha256": sha,
                "lexicon_match": is_relevant(blob),
                "mariupol_match": bool(_MARIUPOL_RE.search(blob)),
            })
            archive_entry_counts[label] += 1

    for pdf_url in pdf_sha:
        if pdf_url not in matched_urls:
            unmatched_pdfs.append(pdf_url)

    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PARSED_DIR / "denis_pushilin_archive_index.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    log.info("wrote %s (%d rows)", out_path, len(rows))

    if unmatched_pdfs:
        log.warning("%d captured PDFs had no index-page <a> match:", len(unmatched_pdfs))
        for u in unmatched_pdfs[:20]:
            log.warning("  %s", u)

    lex_hits = [r for r in rows if r["lexicon_match"]]
    mar_hits = [r for r in rows if r["mariupol_match"]]
    log.info("lexicon-matched (title/desc): %d / %d", len(lex_hits), len(rows))
    log.info("Мариуполь-matched (title/desc): %d / %d", len(mar_hits), len(rows))

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / "denis_pushilin_index_report.md"
    lines = [
        "# denis-pushilin.ru archive index (script 39 archives-only crawl) -- "
        "processing report, 2026-06-12",
        "",
        f"Total captured PDFs: {len(pdf_sha)}. Indexed (matched to an archive-page "
        f"`<a>` entry): {len(rows)}. Unmatched: {len(unmatched_pdfs)}.",
        "",
        "## Per-archive counts",
        "",
        "| Archive | Indexed PDFs | Lexicon-matched | Мариуполь-matched |",
        "|---|---|---|---|",
    ]
    for label in ARCHIVES:
        sub = [r for r in rows if r["archive"] == label]
        lines.append(
            f"| {label} | {len(sub)} | "
            f"{sum(1 for r in sub if r['lexicon_match'])} | "
            f"{sum(1 for r in sub if r['mariupol_match'])} |"
        )

    lines += [
        "",
        "## Мариуполь-matched entries (title/description mentions "
        f"\"Мариуполь\") -- {len(mar_hits)}",
        "",
    ]
    for r in sorted(mar_hits, key=lambda r: (r["archive"], r["filename_date"] or "")):
        lines.append(
            f"- `{r['filename']}` ({r['filename_date'] or 'no date'}, "
            f"{r['archive']}) -- {r['title_text']} {r['description_text']} "
            f"[`{r['sha256'][:12]}..`]"
        )

    lines += [
        "",
        "## Lexicon-matched, non-Мариуполь entries by archive -- counts only "
        "(see JSONL for full list)",
        "",
    ]
    for label in ARCHIVES:
        sub = [r for r in rows if r["archive"] == label and r["lexicon_match"]
               and not r["mariupol_match"]]
        if sub:
            lines.append(f"- {label}: {len(sub)}")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    log.info("wrote %s", report_path)


if __name__ == "__main__":
    main()
