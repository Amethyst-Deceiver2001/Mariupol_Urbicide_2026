#!/usr/bin/env python3
"""Stage 2c: parse OCR'd demolition-decree PDFs into structured building records.

Reads OCR derivatives produced by scripts/06a_ocr_decrees.py
(source_type LIKE 'demolition_decree_%_ocr_pdf') and extracts:

  decree_number | decree_date | decree_kind | address_raw
  | district_hint | signing_official | officials | legal_basis | flags

Unlike the ownerless decree parser (06_parse_ownerless_decrees.py), demolition
decrees have NO registry table — addresses are embedded in paragraph 1 prose.
Extraction is regex-based address splitting after stripping the recurrent
boilerplate prefix "Российская Федерация, Донецкая Народная Республика,
городской округ Мариуполь, город Мариуполь".

Decree number and date come from source_document.title (the HTML capture —
reliable) rather than the OCR'd text, which garbles date digits.

Output: data/parsed/demolition_decrees.jsonl — one record per building.
Re-running is safe (output overwritten).

FOOTPRINT CROSSWALK
-------------------
Each output row is one condemned address — the OLD-address side of the
demolish→rebuild identity break. To close the crosswalk:

  demolition_decrees.jsonl   (this file — OLD address)
  ↕  rapidfuzz address match (≥ 0.8) or cadastral join
  ownerless_decrees.jsonl    (same address → confirms pre-demolition status)
  damage_assessment.jsonl    (same address → building condition data)
  ЕИСЖС / наш.дом.рф        (NEW address under which replacement is sold)

Two matching sources + this decree = claim-grade linkage under CLAUDE.md rules.
"""
from __future__ import annotations

import json
import logging
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

try:
    import pdfplumber
except ImportError:
    sys.exit("pdfplumber not installed — run: .venv/bin/pip install pdfplumber")


# ── regex patterns ────────────────────────────────────────────────────────────

# Paragraph 1: from "Признать [objects] расположенные по адрес*:" to
# "подлежащими сносу".  DOTALL because the address list spans multiple lines.
_P1 = re.compile(
    r"Признать\s+(?:объекты|здания?|многоквартирн\w+\s+дом\w*)[^,]*,?\s*"
    r"расположенн\w+\s+по\s+адрес\w+\s*:\s*(.*?)"
    r"(?:,\s*)?подлежащими\s+сносу",
    re.DOTALL | re.I,
)

# MKD form: "Признать аварийными и подлежащими сносу МКД, расположенные по
# адресу: <list>".  Operative words come BEFORE the target, opposite of _P1.
# Terminates at the next numbered paragraph ("\n2." etc.) or end of text.
_P1_MKD = re.compile(
    r"Признать\s+аварийными\s+и\s+подлежащими\s+сносу\s+"
    r"многоквартирн\w+\s+дом\w*,?\s*"
    r"расположенн\w+\s+по\s+адресу?\s*:\s*"
    r"(.*?)"
    r"(?=\n\s*\d+\.\s|Признать\s+непригодными|\Z)",
    re.DOTALL | re.I,
)

# Boilerplate location prefix repeated before every address in a multi-item list.
# "Российская Федерация" is present in building/OKS decrees but absent in MKD form.
_BOILERPLATE = re.compile(
    r"(?:Российская\s+Федерация,?\s+)?"
    r"Донецкая?\s+Народная?\s+Республика,?\s+"
    r"(?:городской\s+округ\s+Мариуполь,?\s+)?"
    r"(?:город(?:ской)?\s+Мариуполь\s*,?\s*)?",
    re.I,
)

# Officials in parentheses: "(Фамилия И.О.)" — the most common form
_OFFICIAL_PARENS = re.compile(
    r"\(([А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.\s*[А-ЯЁ]\.)\)"
)
# Signing official at end of document: "А.В. Кольцов" or "О.В. Моргун"
_SIGNER = re.compile(
    r"([А-ЯЁ]\.\s*[А-ЯЁ]\.\s+[А-ЯЁ][а-яё]{2,})\s*$",
    re.M,
)

# District in "Управа X внутригородского района"
_DISTRICT = re.compile(
    r"Управ\w+\s+(Орджоникидзевского|Приморского|Жовтневого|Ильичевского)"
    r"\s+внутригородского\s+района",
    re.I,
)

# Amendment: "в постановление ... № NNN"
_AMENDS = re.compile(r"в\s+постановление[^№]*№\s*(\d+)", re.I)

# Legal-basis references (for accountability track: ФКЗ 5-ФКЗ is the annexation law)
_LEGAL_REF = re.compile(
    r"(?:Федеральн\w+\s+(?:конституционн\w+\s+)?закон\w*"
    r"|постановлени\w+\s+Правительства)"
    r"\s+от\s+\d{2}\.\d{2}\.\d{4}\s+№\s+[\w-]+",
    re.I,
)

# Title parsing: decree number and date from the HTML-captured title string
_TITLE_NO = re.compile(r"№\s*(\d+)")
_TITLE_DATE_VERBAL = re.compile(
    r"от\s+(\d{1,2})\s+(\w+)\s+(\d{4})\s+года?", re.I
)
_TITLE_DATE_NUMERIC = re.compile(r"от\s+(\d{2})\.(\d{2})\.(\d{4})")

_MONTH_RU = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4,
    "мая": 5, "июня": 6, "июля": 7, "августа": 8,
    "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}

_HAS_DIGIT = re.compile(r"\d")
_LATIN = re.compile(r"[A-Za-z]")


# ── metadata from title ───────────────────────────────────────────────────────

def _parse_title(title: str) -> tuple[str | None, str | None]:
    """Return (decree_number, ISO-date) parsed from a source_document title."""
    no = None
    m = _TITLE_NO.search(title)
    if m:
        no = m.group(1)

    dt = None
    mv = _TITLE_DATE_VERBAL.search(title)
    if mv:
        month = _MONTH_RU.get(mv.group(2).lower())
        if month:
            try:
                dt = date(int(mv.group(3)), month, int(mv.group(1))).isoformat()
            except ValueError:
                pass
    if dt is None:
        mn = _TITLE_DATE_NUMERIC.search(title)
        if mn:
            try:
                dt = date(int(mn.group(3)), int(mn.group(2)), int(mn.group(1))).isoformat()
            except ValueError:
                pass
    return no, dt


# ── address extraction ────────────────────────────────────────────────────────

def _split_addresses(raw_block: str) -> list[str]:
    """Split a multi-address prose block into individual address strings.

    Strategy:
    1. Split on every occurrence of the boilerplate prefix — each recurrence
       marks the start of a new address (МКД-style lists).
    2. Within each fragment, also split on bare semicolons.
    3. Discard fragments with no digit (they're not addresses).
    """
    block = re.sub(r"\s+", " ", raw_block).strip()
    fragments = _BOILERPLATE.split(block)
    addresses: list[str] = []
    for frag in fragments:
        frag = frag.strip().rstrip(",;. ")
        if not frag:
            continue
        for sf in re.split(r";\s*", frag):
            sf = sf.strip().rstrip(",;.: ")
            # Strip trailing conjunction «и» left when two addresses are joined
            # "addr1 и [Российская Федерация...] addr2" without a repeated prefix.
            sf = re.sub(r"\s+и\s*$", "", sf).strip().rstrip(",;.: ")
            # Strip OCR-garbled paragraph number: period + lowercase Cyrillic at end.
            # e.g. "дом № 46. д" (where "д" is "2." misread) → "дом № 46".
            # Uppercase Cyrillic (section designator like "лит. А") is kept.
            sf = re.sub(r"\.\s+[а-яё]\s*$", "", sf).strip().rstrip(",;.: ")
            if sf and _HAS_DIGIT.search(sf):
                addresses.append(sf)
    return addresses


def _extract_addresses(full_text: str) -> list[str]:
    m = _P1.search(full_text) or _P1_MKD.search(full_text)
    if not m:
        return []
    return _split_addresses(m.group(1))


# ── officials extraction ──────────────────────────────────────────────────────

def _extract_officials(full_text: str) -> list[dict]:
    """Return [{role, name}] for all named officials in the decree.

    Named officials are accountability-track subjects (not minimized per
    CLAUDE.md): they receive lawful instructions to execute demolitions.
    """
    officials: list[dict] = []
    seen: set[str] = set()

    for m in _OFFICIAL_PARENS.finditer(full_text):
        name = m.group(1).strip()
        if name in seen:
            continue
        seen.add(name)
        # Role = last clause before the parenthesis (≤200 chars back)
        prefix = full_text[max(0, m.start() - 200) : m.start()]
        role_raw = re.split(r"[\n.]", prefix)[-1].strip().rstrip("( ")
        officials.append({
            "role": re.sub(r"\s+", " ", role_raw)[:120],
            "name": name,
        })

    sm = _SIGNER.search(full_text)
    if sm:
        name = sm.group(1).strip()
        if name not in seen:
            officials.append({"role": "signing_official", "name": name})

    return officials


# ── flags ─────────────────────────────────────────────────────────────────────

def _flag_address(addr: str) -> list[str]:
    flags: list[str] = []
    if not _HAS_DIGIT.search(addr):
        flags.append("address_no_number")
    if _LATIN.search(addr):
        flags.append("address_latin_chars")
    if len(addr) < 5:
        flags.append("address_too_short")
    if addr == "[NOT EXTRACTED]":
        flags.append("address_extraction_failed")
    return flags


# ── PDF parsing ───────────────────────────────────────────────────────────────

def parse_demolition_pdf(
    pdf_path: Path,
    source_sha256: str,
    decree_number: str | None,
    decree_date: str | None,
    decree_kind: str,
) -> list[dict]:
    """Extract all building records from a single OCR'd demolition decree PDF."""
    full_text_parts: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            full_text_parts.append(page.extract_text() or "")
    full_text = "\n".join(full_text_parts)

    if not full_text.strip():
        log.warning("%s: no text after OCR — re-run 06a_ocr_decrees.py",
                    pdf_path.name)
        return []

    addresses = _extract_addresses(full_text)
    if not addresses:
        log.warning("decree №%s: paragraph-1 extraction found nothing; "
                    "emitting a sentinel row for manual review", decree_number)
        addresses = ["[NOT EXTRACTED]"]

    officials = _extract_officials(full_text)
    signing = next(
        (o["name"] for o in officials if o["role"] == "signing_official"), None
    )

    districts = list(dict.fromkeys(
        m.group(1) for m in _DISTRICT.finditer(full_text)
    ))

    legal_basis = list(dict.fromkeys(
        re.sub(r"\s+", " ", m.group(0)).strip()
        for m in _LEGAL_REF.finditer(full_text)
    ))

    amends = None
    if decree_kind == "amendment":
        am = _AMENDS.search(full_text)
        if am:
            amends = am.group(1)

    rows: list[dict] = []
    for addr in addresses:
        flags = _flag_address(addr)
        rows.append({
            "source_sha256": source_sha256,
            # decree_number and decree_date come from the gosuslugi HTML title
            # (machine-generated portal metadata), NOT from the OCR'd PDF text.
            # The PDF header fields are handwritten cursive — Tesseract misreads
            # them consistently. The raw scan (raw_scan_sha256) remains the
            # physical-document anchor; the HTML capture is the metadata source.
            "decree_metadata_source": "html_title",
            "decree_number": decree_number,
            "decree_date": decree_date,
            "decree_kind": decree_kind,
            "amends_decree": amends,
            "address_raw": addr,
            "district_hint": districts[0] if len(districts) == 1 else (districts or None),
            "signing_official": signing,
            "officials": officials,
            "legal_basis": legal_basis,
            "flags": flags,
        })

    clean = sum(1 for r in rows if not r["flags"])
    preview = "; ".join(addresses[:3]) + ("…" if len(addresses) > 3 else "")
    log.info("decree №%s (%s): %d buildings (%d clean) — %s",
             decree_number or "?", decree_kind, len(rows), clean, preview)
    return rows


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    con = forensics.open_state()
    ocr_sources = con.execute(
        """SELECT sha256, raw_path, title, source_type, derived_from
           FROM source_document
           WHERE source_type LIKE 'demolition_decree_%_ocr_pdf'
           ORDER BY
             CASE WHEN source_type LIKE '%mkd%'      THEN 0
                  WHEN source_type LIKE '%building%'  THEN 1
                  WHEN source_type LIKE '%oks%'       THEN 2
                  ELSE 3 END,
             captured_at"""
    ).fetchall()

    if not ocr_sources:
        n_raw = con.execute(
            """SELECT COUNT(*) FROM source_document
               WHERE source_type LIKE 'demolition_decree_%_pdf'
                 AND derived_from IS NULL"""
        ).fetchone()[0]
        if n_raw:
            log.warning(
                "No OCR derivatives yet, but %d demolition PDFs are captured.\n"
                "Run:  PYTHONPATH=src python scripts/06a_ocr_decrees.py",
                n_raw,
            )
        else:
            log.warning(
                "No demolition PDFs in store — run 08_crawl_demolition_decrees.py first."
            )
        return

    out_dir = config.PROJECT_ROOT / "data" / "parsed"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "demolition_decrees.jsonl"

    total = clean_total = 0
    flag_tally: Counter = Counter()

    with out_path.open("w", encoding="utf-8") as fh:
        for ocr_sha, raw_path, title, source_type, parent_sha in ocr_sources:
            p = Path(raw_path)
            if not p.exists():
                log.error("OCR file missing on disk: %s", raw_path)
                continue

            kind = (source_type
                    .replace("demolition_decree_", "")
                    .replace("_ocr_pdf", ""))
            decree_no, decree_date = _parse_title(title)

            try:
                rows = parse_demolition_pdf(p, ocr_sha, decree_no, decree_date, kind)
            except Exception:
                log.exception("failed to parse %s", raw_path)
                continue

            for row in rows:
                row["raw_scan_sha256"] = parent_sha
                if not row["flags"]:
                    clean_total += 1
                for f in row["flags"]:
                    flag_tally[f] += 1
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            total += len(rows)

    log.info("done — %d building records written to %s", total, out_path)
    log.info("  clean (no flags): %d / %d", clean_total, total)
    if flag_tally:
        log.info("  flags: %s", dict(flag_tally.most_common()))
    if total == 0:
        log.warning(
            "Zero records extracted. Check OCR quality: run 06a again, "
            "then inspect /tmp/dem_*_ocr.pdf text layers manually."
        )


if __name__ == "__main__":
    main()
