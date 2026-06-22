#!/usr/bin/env python3
"""Stage 2: extract structured fields from developer-site PDF captures.

Eleven developer marketing sites were crawled (scripts 120, 121, 124, 126-133)
but never parsed. Their *_pdf source_documents are a mix of:
  - ФЗ-214 "Проектная декларация" (RPD) filings — same regulated format as
    eisghs_rpd_pdf (script 19), often the developer's own copy of a filing
    the project may not otherwise have, or independent confirmation of one
    it does.
  - Generic legal/marketing boilerplate (privacy policy, agency-cooperation
    regulations) with no project-specific data.

This script:
  1. Extracts text via pdftotext -layout (matches script 19's choice — it
     handles the tightly-kerned Cyrillic in these PDF generators correctly,
     unlike pdfplumber which inserts spurious intra-word spaces).
  2. Falls back to OCR (pytesseract + pdf2image, already set up per project
     memory) for PDFs with no extractable text layer -- several of the
     mars_group declarations are scanned/flattened with no text layer at all.
  3. Classifies each PDF as a declaration (header matches "ПРОЕКТНАЯ
     ДЕКЛАРАЦИЯ") or boilerplate, and only runs full field extraction on
     declarations. Boilerplate PDFs are recorded with just a text sample.
  4. Reuses script 19's exact regex patterns for cadastral/INN/OGRN/RPD-num/
     project-title extraction, so output is structurally comparable to
     eisghs_rpd_cadastrals.jsonl.
  5. OCR output is persisted as a derived artifact via
     forensics.capture_derived() (transform="pytesseract:ocr"), never
     overwriting the immutable raw PDF.

OUTPUT
------
data/parsed/developer_site_pdfs.jsonl — one record per PDF, all 11 sites.

Re-running is safe: output is overwritten; OCR derived artifacts are
content-addressed and idempotent (capture_derived no-ops if already present).

Run (offline, no network — safe to run repeatedly):
    .venv312/bin/python scripts/160_parse_developer_site_pdfs.py
"""
from __future__ import annotations

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

# All developer-site crawlers use a "<prefix>_pdf" source_type convention.
SITE_PREFIXES = [
    "proektinvest", "evoinfo", "mars_group", "rskdnr", "sadovoe_kolco",
    "sz_antares", "vertikal_ug", "su2007", "rks_development",
    "lazurnieberega", "mirapolis",
]

_DECLARATION_HEADER = re.compile(r"ПРОЕКТНАЯ\s+ДЕКЛАРАЦИЯ", re.I)

# ---- regex patterns, ported verbatim from scripts/19_ocr_rpd_pdf.py -------
_CADASTRAL = re.compile(r"93:\d+:\d+:\d+")
_RPD_NUM = re.compile(r"\b(93-0{4,5}\d{1,3})\b")
_INN_DNR = re.compile(r"\b(93\d{8})\b")
# NOTE: deliberately NOT using a "ОГРН:"-labelled regex here. These RPD forms
# use the spelled-out label "Основной государственный регистрационный номер"
# (no abbreviation) for the developer's own OGRN immediately after the §2.1.1
# INN, and only use the literal "ОГРН:" abbreviation later, in the escrow
# bank's section (§19) -- a labelled regex silently returns the BANK's OGRN.
# Confirmed by inspection: developer OGRN sits 2-3 lines after the INN match;
# the bank's appears ~1,600 lines later. We instead take the first bare
# 13-15-digit run within ~400 chars AFTER the INN match.
_OGRN_BARE = re.compile(r"\b(\d{13,15})\b")
_PROJECT_QUOT = re.compile(r'["«"]([^"»"]{3,80})[»""]')
_PROJECT_TITLE = re.compile(
    r"№\s*\d{2}-\d{4,6}\s+от\s+\d{2}\.\d{2}\.\d{4}\s*\n+(.+?)\n+\s*Дата первичного размещения",
    re.S,
)
_AREA_GENERIC = re.compile(
    r"([\d][\d\s]{0,10}[\.,]\d{2})\s*м\s*[²2]|([\d][\d\s]{0,10})\s*м\s*[²2]", re.I,
)
_SOFT_HYPHEN = "­"


def _clean(text: str) -> str:
    return text.replace(_SOFT_HYPHEN, "")


def extract_text_pdftotext(path: Path) -> str | None:
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", "-enc", "UTF-8", str(path), "-"],
            capture_output=True, timeout=60,
        )
        if result.returncode == 0:
            return result.stdout.decode("utf-8", errors="replace")
        log.warning("pdftotext exited %d for %s", result.returncode, path.name)
        return None
    except FileNotFoundError:
        log.error("pdftotext not found — install poppler")
        return None
    except subprocess.TimeoutExpired:
        log.warning("pdftotext timed out on %s", path.name)
        return None


def extract_text_ocr(path: Path, con, sha256: str) -> str | None:
    """OCR fallback for PDFs with no text layer. Persists OCR text as a
    derived artifact (Berkeley Protocol: never silently discard the
    transformation)."""
    try:
        import pytesseract
        from pdf2image import convert_from_path
    except ImportError:
        log.warning("pytesseract/pdf2image not installed — cannot OCR %s", path.name)
        return None
    try:
        pages = convert_from_path(str(path), dpi=200)
        texts = [pytesseract.image_to_string(p, lang="rus") for p in pages]
        text = "\n\n".join(texts)
    except Exception as exc:
        log.warning("OCR failed on %s: %s", path.name, exc)
        return None
    if not text.strip():
        return None
    forensics.capture_derived(
        text.encode("utf-8"),
        derived_from=sha256,
        transform="pytesseract:ocr:lang=rus,dpi=200",
        source_type="developer_site_pdf_ocr_text",
        title=f"OCR text for {path.name}",
        description="pytesseract OCR fallback for a developer-site PDF with no extractable text layer.",
        content_type="text/plain",
        con=con,
    )
    return text


def extract_text(path: Path, con, sha256: str) -> tuple[str | None, str]:
    text = extract_text_pdftotext(path)
    if text and text.strip():
        return _clean(text), "pdftotext"
    text = extract_text_ocr(path, con, sha256)
    if text:
        return _clean(text), "ocr"
    return None, "none"


def _clean_area(raw: str) -> float | None:
    s = re.sub(r"\s+", "", raw).replace(",", ".").split("+")[0].split("-")[0]
    try:
        return float(s)
    except ValueError:
        return None


def parse_declaration(text: str) -> dict:
    flags: list[str] = []

    cadastrals = list(dict.fromkeys(_CADASTRAL.findall(text)))
    if not cadastrals:
        flags.append("cadastral_missing")

    areas: list[float] = []
    for m in _AREA_GENERIC.finditer(text):
        raw = (m.group(1) or m.group(2) or "").strip()
        v = _clean_area(raw)
        if v and 100 < v < 50_000:
            areas.append(v)
    parcel_candidates = [v for v in areas if 200 <= v <= 10_000]
    area_sqm = min(parcel_candidates) if parcel_candidates else None
    if area_sqm is None:
        flags.append("area_missing")

    rpd_matches = _RPD_NUM.findall(text)
    rpd_num_in_pdf = rpd_matches[0] if rpd_matches else None

    inn_match = _INN_DNR.search(text)
    inn_in_pdf = inn_match.group(1) if inn_match else None

    ogrn_in_pdf = None
    if inn_match:
        window = text[inn_match.end():inn_match.end() + 400]
        m_ogrn = _OGRN_BARE.search(window)
        if m_ogrn:
            ogrn_in_pdf = m_ogrn.group(1)

    project_names = _PROJECT_QUOT.findall(text)
    project_name_in_pdf = project_names[0].strip() if project_names else None

    m_title = _PROJECT_TITLE.search(text)
    project_title_in_pdf = re.sub(r"\s+", " ", m_title.group(1)).strip() if m_title else None
    if not project_title_in_pdf:
        flags.append("project_title_missing")

    return {
        "rpd_num_in_pdf": rpd_num_in_pdf,
        "project_name_in_pdf": project_name_in_pdf,
        "project_title_in_pdf": project_title_in_pdf,
        "developer_inn_in_pdf": inn_in_pdf,
        "developer_ogrn_in_pdf": ogrn_in_pdf,
        "cadastral_numbers": cadastrals,
        "area_sqm": area_sqm,
        "flags": flags,
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    con = forensics.open_state()

    where = " OR ".join(f"source_type = '{p}_pdf'" for p in SITE_PREFIXES)
    sources = con.execute(
        f"SELECT sha256, url, source_type, raw_path, title FROM source_document WHERE {where} ORDER BY source_type"
    ).fetchall()

    if not sources:
        log.error("No developer-site PDF records found — run the crawl scripts first.")
        return

    log.info("Found %d developer-site PDFs across %d sites", len(sources), len(SITE_PREFIXES))

    out_dir = config.PROJECT_ROOT / "data" / "parsed"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "developer_site_pdfs.jsonl"

    n_decl = n_boilerplate = n_no_text = 0
    with out_path.open("w", encoding="utf-8") as fh:
        for sha256, url, source_type, raw_path, title in sources:
            path = Path(raw_path)
            if not path.exists():
                log.warning("raw file missing for %s: %s", sha256[:12], raw_path)
                continue

            text, method = extract_text(path, con, sha256)
            site = source_type.rsplit("_pdf", 1)[0]

            if text is None:
                n_no_text += 1
                record = {
                    "site": site, "source_sha256": sha256, "url": url, "title": title,
                    "kind": "no_text_extracted", "extract_method": method,
                }
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                log.info("[no-text] %s %s", site, url)
                continue

            is_declaration = bool(_DECLARATION_HEADER.search(text[:200]))
            if is_declaration:
                n_decl += 1
                fields = parse_declaration(text)
                record = {
                    "site": site, "source_sha256": sha256, "url": url, "title": title,
                    "kind": "declaration", "extract_method": method, **fields,
                }
                log.info("[declaration] %s RPD=%s cadastral=%s",
                         site, fields["rpd_num_in_pdf"], fields["cadastral_numbers"])
            else:
                n_boilerplate += 1
                sample = re.sub(r"\s+", " ", text)[:300].strip()
                record = {
                    "site": site, "source_sha256": sha256, "url": url, "title": title,
                    "kind": "boilerplate_or_marketing", "extract_method": method,
                    "text_sample": sample,
                }
                log.info("[other] %s %s", site, sample[:80])

            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"\n{'='*60}")
    print(f"developer-site PDF parse complete: {len(sources)} PDFs")
    print(f"  Declarations (RPD)       : {n_decl}")
    print(f"  Boilerplate / marketing  : {n_boilerplate}")
    print(f"  No text extracted        : {n_no_text}")
    print(f"  Output: {out_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
