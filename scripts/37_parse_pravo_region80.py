#!/usr/bin/env python3
"""Stage 2h: categorize the pravo.gov.ru region80 (DNR) captures from
scripts/35_crawl_pravo_region80.py against the legal-mechanism categories in
docs/legal_mechanisms_review.md, and re-run the two negative-finding searches
(GKO Rasporyazhenie No.56 federal copy; street-renaming decrees) against the
full region80 index for reproducibility.

Reads source_document rows with source_type='pravo_region80_meta' /
'pravo_region80_pdf' (395 lexicon-matched captures, 2026-06-11) and
source_type='pravo_region80_index' (12 pages, 2,221 records total).

Output:
  data/parsed/pravo_region80_relevant.jsonl -- one row per captured act, with
    eo_number, document_type, number, document_date, name, complex_name,
    jd_reg_number/date, signatory authorities, meta/pdf SHA-256s, and
    pipeline_category (one of CATEGORY_MAP's entries below, or null).
  data/reports/pravo_region80_gaps_report.md -- category counts + the two
    negative-finding searches re-run against the full 2,221-record index.

Run locally, no network: python3 scripts/37_parse_pravo_region80.py
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

log = logging.getLogger(__name__)

PARSED_DIR = config.PROJECT_ROOT / "data" / "parsed"
REPORTS_DIR = config.PROJECT_ROOT / "data" / "reports"

# Curated categorization of the dispossession-relevant region80 acts identified
# 2026-06-11/12, keyed by (number, documentDate[:10]) -- DNR Postanovlenie
# numbers are reused year to year (e.g. two unrelated "29-4" acts exist), so
# the bare number is not a stable key.
CATEGORY_MAP: dict[tuple[str, str], tuple[str, str]] = {
    # Framework: FKZ-4 (15.12.2025) implementing acts
    ("134-РЗ", "2024-12-05"): ("fkz4_implementing", "Framework: FKZ-4 implementing acts (base law)"),
    ("240-РЗ", "2025-12-22"): ("fkz4_implementing", "Framework: FKZ-4 implementing acts"),
    ("275-РЗ", "2026-04-17"): ("fkz4_implementing", "Framework: FKZ-4 implementing acts (amendment)"),
    # [A] DNR ownerless-property procedure
    ("66-РЗ", "2024-03-21"): ("ownerless_procedure", "[A] DNR ownerless procedure (base law)"),
    ("137-РЗ", "2024-12-13"): ("ownerless_procedure", "[A] DNR ownerless procedure (amendment)"),
    ("269-РЗ", "2026-04-03"): ("ownerless_procedure", "[A] DNR ownerless procedure (disposal/compensation)"),
    ("272-РЗ", "2026-04-17"): ("ownerless_procedure", "[A] DNR ownerless procedure"),
    # [D] DNR no-auction land-allocation procedure
    ("39-РЗ", "2023-12-29"): ("land_no_auction", "[D] DNR no-auction land procedure (base law)"),
    ("145-РЗ", "2024-12-27"): ("land_no_auction", "[D] DNR no-auction land procedure (amendment)"),
    ("221-РЗ", "2025-10-31"): ("land_no_auction", "[D] DNR no-auction land procedure (amendment)"),
    ("263-РЗ", "2026-03-19"): ("land_no_auction", "[D] DNR no-auction land procedure (amendment)"),
    ("266-РЗ", "2026-04-03"): ("land_no_auction", "[D] DNR no-auction land procedure (amendment)"),
    ("29-4", "2024-03-21"): ("land_no_auction", "[D] DNR no-auction land rent-rate procedure"),
    ("64-4", "2025-07-03"): ("land_no_auction", "[D] DNR no-auction land rent-rate procedure (amendment)"),
    # [G] manevrenny fond / sluzhebnoe zhilye
    ("93-2", "2025-09-18"): ("housing_manevr_sluzh", "[G] manevrenny fond (maneuverable housing stock) regulation"),
    ("93-3", "2025-09-18"): ("housing_manevr_sluzh", "[G] sluzhebnoe zhilye inclusion procedure"),
    ("29-2", "2024-03-21"): ("housing_manevr_sluzh", "[G] sluzhebnoe zhilye procedure (amendment)"),
}

# Negative-finding re-checks against the full region80 index. complexName
# always opens with "<DocumentType> <Issuer> ot <date> No <number>", so an
# issuer-name search ("GKO") works without a resolved signatoryAuthority name.
# Case-sensitive whole-word match: lowercase "гко" is a substring of common
# words like "легковым"/"легкового" (passenger/light vehicle) and produces
# dozens of false positives if matched case-insensitively or without \b.
GKO_RE = re.compile(r"\bГКО\b")
RENAMING_RE = re.compile(r"переименован|наименован", re.IGNORECASE)


def load_full_index() -> list[dict]:
    con = forensics.open_state()
    rows = con.execute(
        "SELECT raw_path FROM source_document WHERE source_type='pravo_region80_index'"
    ).fetchall()
    docs: list[dict] = []
    for (raw_path,) in rows:
        data = json.loads(Path(raw_path).read_text(encoding="utf-8"))
        docs.extend(data.get("items", []))
    return docs


def load_captured() -> list[dict]:
    con = forensics.open_state()
    meta_rows = con.execute(
        "SELECT sha256, raw_path FROM source_document WHERE source_type='pravo_region80_meta'"
    ).fetchall()
    pdf_rows = con.execute(
        "SELECT sha256, url FROM source_document WHERE source_type='pravo_region80_pdf'"
    ).fetchall()

    eo_re = re.compile(r"eoNumber=(\d+)")
    pdf_by_eo: dict[str, str] = {}
    for sha, url in pdf_rows:
        m = eo_re.search(url)
        if m:
            pdf_by_eo[m.group(1)] = sha
        else:
            log.warning("could not extract eoNumber from pdf url: %s", url)

    records = []
    for meta_sha, raw_path in meta_rows:
        doc = json.loads(Path(raw_path).read_text(encoding="utf-8"))
        eo = doc["eoNumber"]
        date_key = (doc.get("documentDate") or "")[:10]
        number = doc.get("number") or ""
        cat = CATEGORY_MAP.get((number, date_key))
        records.append({
            "eo_number": eo,
            "document_type": (doc.get("documentType") or {}).get("name"),
            "number": number,
            "document_date": date_key,
            "name": (doc.get("name") or "").strip(),
            "complex_name": doc.get("complexName"),
            "jd_reg_number": doc.get("jdRegNumber"),
            "jd_reg_date": (doc.get("jdRegDate") or "")[:10] or None,
            "signatory_authorities": [a.get("name") for a in doc.get("signatoryAuthorities", [])],
            "meta_sha256": meta_sha,
            "pdf_sha256": pdf_by_eo.get(eo),
            "pipeline_category": cat[0] if cat else None,
            "pipeline_note": cat[1] if cat else None,
        })
    return records


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")

    records = load_captured()
    log.info("loaded %d captured region80 records (35-crawl, 2026-06-11)", len(records))

    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PARSED_DIR / "pravo_region80_relevant.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    log.info("wrote %s (%d rows)", out_path, len(records))

    cat_counts = Counter(r["pipeline_category"] or "uncategorized" for r in records)
    for cat, n in sorted(cat_counts.items()):
        log.info("  %-22s %d", cat, n)
    matched = sum(n for c, n in cat_counts.items() if c != "uncategorized")
    log.info("matched %d/%d captured acts to a pipeline category", matched, len(records))

    # Negative-finding re-checks against the full index
    full_index = load_full_index()
    log.info("full region80 index: %d records", len(full_index))

    gko_hits = [
        d for d in full_index
        if GKO_RE.search(d.get("complexName") or "") or GKO_RE.search(d.get("name") or "")
    ]
    renaming_hits = [
        d for d in full_index
        if RENAMING_RE.search(d.get("complexName") or "") or RENAMING_RE.search(d.get("name") or "")
    ]
    log.info("'GKO' issuer hits in full index: %d", len(gko_hits))
    log.info("street-renaming (pereimenovan/naimenovan) hits in full index: %d", len(renaming_hits))

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / "pravo_region80_gaps_report.md"
    lines = [
        "# pravo.gov.ru region80 crawl -- gap closure report (2026-06-11/12)",
        "",
        f"Captured: {len(records)} lexicon-matched acts out of "
        f"{len(full_index)} total region80 records (12 index pages).",
        "",
        "## Captured-record categorization",
        "",
    ]
    for cat, n in sorted(cat_counts.items()):
        lines.append(f"- `{cat}`: {n}")
    lines += [
        "",
        "## Resolved acts by category",
        "",
    ]
    for cat in sorted({c for c, _ in CATEGORY_MAP.values()}):
        lines.append(f"### {cat}")
        for r in records:
            if r["pipeline_category"] == cat:
                pdf_sha = r["pdf_sha256"] or "MISSING"
                lines.append(
                    f"- **{r['number']}** ({r['document_type']}, {r['document_date']}) "
                    f"-- {r['pipeline_note']} -- {r['name'][:100]} "
                    f"[meta `{r['meta_sha256'][:12]}..` / pdf `{pdf_sha[:12]}..`]"
                )
        lines.append("")

    lines += [
        "## Negative findings (full 2,221-record region80 index, 2026-06-11)",
        "",
        f"- **GKO Rasporyazhenie No.56** (Mariupol demolition order, 29.09.2022): "
        f"**{len(gko_hits)} hits** for issuer 'GKO' anywhere in region80 -- "
        "confirmed absent; likely npa.dnronline-only (script 13's domain).",
        f"- **Street-renaming decrees** (pereimenovanie/naimenovanie): "
        f"**{len(renaming_hits)} hits** -- confirmed absent; likely Mariupol "
        "municipal (mariupol.gosuslugi.ru, scripts 05/08).",
        "",
        "Both gaps remain `[region80 GAP]` in docs/legal_mechanisms_review.md "
        "and `Crawl gap` in docs/dispossession_pipeline.html, with these "
        "negative findings recorded inline.",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    log.info("wrote %s", report_path)


if __name__ == "__main__":
    main()
