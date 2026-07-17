#!/usr/bin/env python3
"""Stage 2b: parse OCR'd ownerless-decree annexes into structured rows.

Reads the OCR DERIVATIVES produced by scripts/06a_ocr_decrees.py
(source_type LIKE 'ownerless_decree_%_ocr_pdf') and extracts the registry table:

  seq_no | property_type | address_raw | area_sqm
       | rosreestr_order_ref | rosreestr_order_date | rosreestr_reg_date
       | cadastral_number

Plus decree-level metadata (number, date, signing official) from the text.
Output: data/parsed/ownerless_decrees.jsonl — one record per property row,
carrying the OCR artifact sha256 AND its parent raw-scan sha256 (chain of
custody). Re-running is safe (output overwritten).

The originals are SCANNED IMAGES — this parser deliberately reads the OCR
derivatives, never the raw scans. If no OCR derivatives exist yet, it tells
you to run 06a first rather than silently producing nothing.

OCR NOISE → CONFIDENCE FLAGS (per the project rule: never silently drop)
------------------------------------------------------------------------
OCR misreads cadastral numbers (the join key) and addresses. Every row gets a
`flags` list (data quality only) and `row_confidence`:
  - cadastral_malformed : value present but fails the strict ЕГРН format
  - cadastral_missing   : no cadastral number found in the row
  - address_suspect     : address has Latin chars (OCR confusion) or no digit
  - area_missing        : area didn't parse to a number
Extraction method (lines / text_cells / text_fallback) is in `extract_strategy`,
NOT in flags. Rows with an empty flags list are claim-grade; flagged rows are
kept for human review. text_fallback rows have row_confidence capped at 0.8.

TABLE EXTRACTION ON OCR'd SCANS
-------------------------------
After OCR the table BORDERS are still raster pixels (no PDF vector lines), so
pdfplumber's default line-based table detection often finds nothing. This
parser tries, in order: (1) line-based tables, (2) text-position tables,
(3) a line-by-line text fallback anchored on the seq-no + cadastral pattern.
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path

log = logging.getLogger(__name__)

# ── project root on sys.path ────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

try:
    import pdfplumber
except ImportError:
    sys.exit("pdfplumber not installed — run: pip install pdfplumber")

# ── regex patterns ───────────────────────────────────────────────────────────

# Decree header in OCR text: handwritten date/number — GARBLED, not reliable.
# Use HTML title instead (see _parse_title_meta).  Only _SIGNER is read from OCR.
_DECREE_DATE_NO = re.compile(
    r"от\s+(\d{1,2})\s+(\w+)\s+(\d{4})\s+года?\s*№\s*(\d+)", re.I
)
# Signing official: "А.В. Кольцов" — last occurrence in text
_SIGNER = re.compile(r"([А-ЯЁ]\.\s*[А-ЯЁ]\.\s+[А-ЯЁ][а-яё]+)\s*$", re.M)

# Title metadata: decree number and date from the gosuslugi HTML title string.
# The PDF header date/number are handwritten — OCR garbles them consistently.
_TITLE_NO = re.compile(r"№\s*(\d+)")
_TITLE_DATE_VERBAL = re.compile(
    r"от\s+(\d{1,2})\s+(\w+)\s+(\d{4})\s+года?", re.I
)
_TITLE_DATE_NUMERIC = re.compile(r"от\s+(\d{2})\.(\d{2})\.(\d{4})")

# Rosreestr basis cell: "№ 1781 от 21.11.2025"
_BASIS = re.compile(r"№\s*(\d+)\s+от\s+(\d{2}\.\d{2}\.\d{4})")

# Date cell: DD.MM.YYYY
_DATE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")

# Cadastral number: permissive capture (OCR may insert spaces), then a STRICT
# validator the value must satisfy to be claim-grade.
_CADASTRAL = re.compile(r"93:\s?\d+:\s?\d+:\s?\d+")
# Strict ЕГРН form for Mariupol: 93:NN:NNNNNN(N):NN(NNN). Anything else = flag.
_CADASTRAL_STRICT = re.compile(r"^93:\d{2}:\d{6,7}:\d{1,5}$")
# Latin letters are a common OCR confusion in otherwise-Cyrillic cells.
_LATIN = re.compile(r"[A-Za-z]")
# A plausible street address should carry a house number somewhere.
_HAS_DIGIT = re.compile(r"\d")

_MONTH_RU = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4,
    "мая": 5, "июня": 6, "июля": 7, "августа": 8,
    "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}


def _parse_ru_date(day: str, month_word: str, year: str) -> str | None:
    m = _MONTH_RU.get(month_word.lower())
    if not m:
        return None
    try:
        return date(int(year), m, int(day)).isoformat()
    except ValueError:
        return None


def _parse_dot_date(s: str) -> str | None:
    m = _DATE.search(s)
    if not m:
        return None
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
    except ValueError:
        return None


def _parse_title_meta(title: str) -> dict:
    """Return {decree_number, decree_date, decree_metadata_source} from the
    gosuslugi HTML title string.  More reliable than OCR text: the PDF header
    date and number are handwritten and Tesseract misreads them consistently."""
    meta: dict = {"decree_metadata_source": "html_title"}
    m = _TITLE_NO.search(title)
    if m:
        meta["decree_number"] = m.group(1)
    mv = _TITLE_DATE_VERBAL.search(title)
    if mv:
        dt = _parse_ru_date(mv.group(1), mv.group(2), mv.group(3))
        if dt:
            meta["decree_date"] = dt
    if "decree_date" not in meta:
        mn = _TITLE_DATE_NUMERIC.search(title)
        if mn:
            try:
                meta["decree_date"] = date(
                    int(mn.group(3)), int(mn.group(2)), int(mn.group(1))
                ).isoformat()
            except ValueError:
                pass
    return meta


def _extract_decree_meta(text: str) -> dict:
    """Pull signing official from full PDF text (decree number/date come from title)."""
    meta: dict = {}
    sm = _SIGNER.search(text)
    if sm:
        meta["signing_official"] = sm.group(1).strip()
    return meta


# ── table parsing ─────────────────────────────────────────────────────────────

# Expected column count in the annex table.
_EXPECTED_COLS = 7

# Rows whose first cell looks like a header (not a row number).
_HEADER_CELL = re.compile(r"[№Нн]|Место|Харак|Основ|Свед|Кадас", re.I)


def _is_header_row(row: list) -> bool:
    first = (row[0] or "").strip()
    return bool(_HEADER_CELL.match(first)) or not first.isdigit()


def _coerce_area(s: str) -> float | None:
    cleaned = s.replace(",", ".").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_basis(cell: str) -> tuple[str | None, str | None]:
    """Return (rosreestr_order_ref, rosreestr_order_date) from basis cell."""
    m = _BASIS.search(cell)
    if not m:
        return None, None
    return m.group(1), _parse_dot_date(m.group(2))


def _clean_cadastral(raw: str | None) -> str | None:
    """Strip OCR-inserted spaces from a captured cadastral number."""
    if not raw:
        return None
    return re.sub(r"\s+", "", raw)


def _row_flags(address: str, cadastral: str | None, area) -> tuple[list[str], float]:
    """Validate a parsed row; return (flags, confidence in 0..1).

    Never raises and never drops — flags let a human triage OCR noise. A clean
    row (strict-valid cadastral, plausible address, area present) scores 1.0.
    """
    flags: list[str] = []
    if cadastral is None:
        flags.append("cadastral_missing")
    elif not _CADASTRAL_STRICT.match(cadastral):
        flags.append("cadastral_malformed")
    if not address or _LATIN.search(address) or not _HAS_DIGIT.search(address):
        flags.append("address_suspect")
    if area is None:
        flags.append("area_missing")
    # Confidence: start at 1.0, dock per flag, cadastral issues weigh most.
    penalty = sum(
        0.5 if f.startswith("cadastral") else 0.2 for f in flags
    )
    return flags, round(max(0.0, 1.0 - penalty), 2)


def _row_from_cells(cells: list[str], source_sha256: str) -> dict | None:
    """Build a record from a 7-wide cell list, or None if it's not a data row."""
    while len(cells) < _EXPECTED_COLS:
        cells.append("")
    if _is_header_row(cells):
        return None
    seq_raw = cells[0].strip()
    if not seq_raw.isdigit():
        return None  # continuation / merged cell
    basis_ref, basis_date = _parse_basis(cells[4])
    cad = _clean_cadastral(
        (_CADASTRAL.search(cells[6]).group(0) if _CADASTRAL.search(cells[6]) else None)
    )
    address = cells[2].strip()
    area = _coerce_area(cells[3])
    flags, conf = _row_flags(address, cad, area)
    return {
        "source_sha256": source_sha256,
        "seq_no": int(seq_raw),
        "property_type": cells[1].strip(),
        "address_raw": address,
        "area_sqm": area,
        "rosreestr_order_ref": basis_ref,
        "rosreestr_order_date": basis_date,
        "rosreestr_reg_date": _parse_dot_date(cells[5]),
        "cadastral_number": cad,
        "flags": flags,
        "row_confidence": conf,
    }


# Two-line OCR structure for scanned РЕЕСТР annexes:
#   Line 1: {seq}. {type} {city_noise}.Мариуполь, {area} №{basis_ref} {reg_date} {cadastral}
#   Line 2: {street_address} от {basis_date}
# Table borders are raster pixels — no vector lines for pdfplumber to detect,
# so this 2-line pair parser is the primary extraction path.
_L1_TWO = re.compile(
    r"^[-\s]*(\d{1,4})[.\s]+\s*"   # seq_no at line start
    r"(.+?)\s+"                     # property_type (lazy, stops at city)
    r"\S*Мариуполь,?\s*"            # city field (OCR noise: "Г.", "г.", "Гг.", "|.", etc.)
    r"([\d,\.]+)\s+"                # area_sqm (decimal comma)
    r"№\s*(\d+)\s+"                 # rosreestr basis ref number
    r"(\d{2}\.\d{2}\.\d{4})\s+"    # rosreestr reg date
    r"(93:\s?\d+:\s?\d+:\s?\d+)",   # cadastral number
    re.I,
)
_L2_OT = re.compile(
    r"^(.+?)\s+от\s+(\d{2}\.\d{2}\.\d{4})\s*$",
    re.I,
)


def _rows_from_text(text: str, source_sha256: str) -> list[dict]:
    """Parse the 2-line-per-entry OCR text from scanned РЕЕСТР annexes.

    Extraction method is recorded in extract_strategy='text_fallback'; it is NOT
    put in the flags list. Flags are reserved for data-quality problems only
    (cadastral_missing/malformed, address_suspect, area_missing). Rows with a
    well-formed cadastral and clean address score up to 0.8 confidence (the 0.2
    penalty reflects text-layer uncertainty vs. a structured table extraction).
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out: list[dict] = []
    i = 0
    while i < len(lines):
        m1 = _L1_TWO.match(lines[i])
        if m1:
            seq = int(m1.group(1))
            prop_type = m1.group(2).strip()
            area = _coerce_area(m1.group(3))
            basis_ref = m1.group(4)
            reg_date = _parse_dot_date(m1.group(5))
            cad = _clean_cadastral(m1.group(6))

            # Line 2: street address + order date
            address: str | None = None
            basis_date: str | None = None
            if i + 1 < len(lines):
                m2 = _L2_OT.match(lines[i + 1])
                if m2:
                    address = m2.group(1).strip()
                    basis_date = _parse_dot_date(m2.group(2))
                    i += 1  # consume line 2

            flags, conf = _row_flags(address or "", cad, area)
            # text_fallback goes in extract_strategy, not flags — extraction
            # method is not a data-quality defect.
            out.append({
                "source_sha256": source_sha256,
                "seq_no": seq,
                "property_type": prop_type,
                "address_raw": address or "",
                "area_sqm": area,
                "rosreestr_order_ref": basis_ref,
                "rosreestr_order_date": basis_date,
                "rosreestr_reg_date": reg_date,
                "cadastral_number": cad,
                "flags": flags,
                "row_confidence": round(max(0.0, conf - 0.2), 2),
            })
        i += 1
    return out


# ── registration-decree ("постановка на учет") table parsing ─────────────────
# Registration decrees ("О постановке на учет недвижимой вещи в качестве
# бесхозяйной") are the EARLIER pipeline stage, before Rosreestr assigns a
# cadastral number — so these tables never carry a rosreestr_order_ref or
# cadastral column at all (the 7th column literally reads "информация
# отсутствует" for every row). Neither existing extraction path fits: the
# cell-based _row_from_cells (via pdfplumber's text-position table detection)
# silently misaligns columns on this shape's wrapped multi-line address cell
# (confirmed 2026-07-17: address truncated to "г. Мар", a wrapped
# continuation line like "Квартира" leaking into address_raw on its own
# spurious "row" — while still returning non-empty rows, which blocked the
# text_fallback parser below from ever running); _rows_from_text's _L1_TWO
# regex expects a rosreestr_order_ref/cadastral on line 1, which this shape
# never has, so it matches nothing.
#
# Real 3-line-per-record structure (pdfplumber extract_text(), not -layout):
#   L1: {seq} | Квартира г. Мариуполь, {area} требует ремонтно- | {date} | информация отсутствует
#   L2: [stray "|"/"/" noise] {street}, д.{house}, кв.{apt} восстановительных
#   L3: работ   (wrapped tail of "восстановительных работ" — content-free, skipped)
_REG_L1 = re.compile(
    r"^(\d{1,4})\s*\|?\s*Квартира\s+г\.\s*Мариуполь,\s*"
    r"([\d,\.]+)\s+требует\s+ремонтно-\s*\|?\s*"
    r"(\d{2}\.\d{2}\.\d{4})\s*\|?\s*информация\s+отсутствует",
    re.I,
)
_REG_L2 = re.compile(
    r"^[|/‚\s]*(.+?,\s*д\.\S+?,\s*кв\.\d+)\s+восстановительных\s*$",
    re.I,
)


def _rows_from_registration_table_text(text: str, source_sha256: str) -> list[dict]:
    """Parse the 3-line-per-entry OCR text from registration-decree
    ("постановка на учет") annexes. cadastral_number and rosreestr_order_ref
    are always None here — genuinely absent at this pipeline stage, not a
    parse failure — so cadastral_missing will still flag every row (an
    accurate reflection of the decree stage, not a defect); the actual gain
    over the generic cell/text-fallback paths is a correctly extracted
    address_raw and area_sqm instead of truncated/empty garbage."""
    lines = [ln.rstrip() for ln in text.splitlines()]
    out: list[dict] = []
    i = 0
    while i < len(lines):
        m1 = _REG_L1.match(lines[i].strip())
        if m1:
            seq = int(m1.group(1))
            area = _coerce_area(m1.group(2))
            reg_date = _parse_dot_date(m1.group(3))
            address: str | None = None
            if i + 1 < len(lines):
                m2 = _REG_L2.match(lines[i + 1].strip())
                if m2:
                    address = m2.group(1).strip()
                    i += 1  # consume line 2
            flags, conf = _row_flags(address or "", None, area)
            out.append({
                "source_sha256": source_sha256,
                "seq_no": seq,
                "property_type": "Квартира",
                "address_raw": address or "",
                "area_sqm": area,
                "rosreestr_order_ref": None,
                "rosreestr_order_date": None,
                "rosreestr_reg_date": reg_date,
                "cadastral_number": None,
                "flags": flags,
                "row_confidence": round(max(0.0, conf - 0.2), 2),
            })
        i += 1
    return out


# ── removal-decree ("исключение из Реестра") table parsing ────────────────────
# Removal-decree annexes use a DIFFERENT column layout than designation
# annexes (no rosreestr_order_ref "basis" column; instead: designation date +
# cadastral + a "дата снятия с кадастрового учета" placeholder column that's
# usually unfilled boilerplate, not a real date). Forcing these through
# _row_from_cells (tuned for the 7-col designation layout) silently
# misaligned columns and produced ~98% address_raw=="г." garbage (found
# 2026-07-02 while cross-checking a bezkhoz-list differential — see
# docs/legal_mechanisms_review.md). pdfplumber's extract_text() renders each
# annex row as 3 physical lines:
#   L1: "{seq} {type} г. Мариуполь, {area} {designation_date} {cadastral} дата снятия"
#   L2: "{street}, д.{house}[, кв.{apt}] с кадастрового"
#   L3: "учета"
# seq_no is frequently OCR-misread as "|" (vertical bar) or other junk on
# handwritten/scanned tables -- it is NOT used as the record's seq_no (would
# collide); rows are numbered by parse order within the decree instead.
_REMOVAL_L1 = re.compile(
    r"^\S+\s+(\S+)\s+"              # seq_no (ignored) + property_type
    r"г\.\s*Мариуполь,?\s*"         # city field
    r"([\d,\.]+)\s+"                # area_sqm
    r"(\d{2}\.\d{2}\.\d{4})\s+"    # designation date ("дата постановки на учет")
    r"(93:\s?\d+:\s?\d+:\s?\d+)"    # cadastral number
    r"\s+дата",                     # start of the "дата снятия..." placeholder
    re.I,
)
# Found 2026-07-03 auditing the residual removal-decree gap: the address
# line does NOT reliably sit immediately after L1 -- some decrees wrap the
# whole "дата снятия с кадастрового учета" placeholder onto its own line
# BEFORE the address line arrives (originally assumed address always comes
# first), and the "с кадастрового"/"учета" split point itself varies by
# decree. Also found: "N квартал"/"кв-л N" rows (same numbered-block
# addressing fixed in toponym.py) use the number-then-word TRAILING form,
# not the leading form the original street-word alternation assumed. Rather
# than keep special-casing line order, this scans a window of up to 3 lines
# after L1 for the first line that looks like an address (street/house core
# only -- no longer requires "кадастрового" to co-occur on the same line,
# since we're already scoped inside a confirmed L1's window) and, separately,
# backfills the apartment number from a lone "кв. N" line if it wasn't
# captured inline.
_STREET_PREFIX = (
    r"(?:(?:ул|пр|просп|пр-кт|б-р|бул|пер|мкр)\S*\.?\s+[^,]+?"
    r"|\d+\s*(?:квартал|кв-л))"
)
_REMOVAL_ADDR_CORE = re.compile(
    rf"^\|?\s*({_STREET_PREFIX}),\s*"
    r"д(?:ом)?[.,]?\s*([^\s,]+),?"
    r"(?:\s*кв\.?\s*([^\s,._]+))?",
    re.I,
)
_REMOVAL_L3_APT = re.compile(r"^кв\.?\s*(\S+)\s*$", re.I)


def _rows_from_removal_text(text: str, source_sha256: str) -> list[dict]:
    """Parse the multi-line-per-entry OCR text from removal-decree
    ("исключение из Реестра") annexes -- see _REMOVAL_L1/_REMOVAL_ADDR_CORE
    above. Each entry starts with an L1 line (seq/type/area/date/cadastral),
    followed within the next 1-3 physical lines by the address; exact line
    order/wrapping is inconsistent across decrees, so this scans forward
    rather than assuming a fixed position."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out: list[dict] = []
    seen_cad: set[str] = set()
    seq = 0
    i = 0
    while i < len(lines):
        m1 = _REMOVAL_L1.match(lines[i])
        if m1:
            m2 = None
            addr_idx = None
            for j in range(i + 1, min(i + 4, len(lines))):
                m2 = _REMOVAL_ADDR_CORE.match(lines[j])
                if m2:
                    addr_idx = j
                    break
            # Found 2026-07-03: a genuine clerical duplicate in a source
            # decree's own annex (decree №300/03.03.2025, cadastral
            # 93:37:0010309:1633 listed twice at two different seq_no) --
            # dedup by cadastral within a single decree's rows, same guard
            # as _rows_from_nonres_annex_text uses.
            if m2 and _clean_cadastral(m1.group(4)) in seen_cad:
                i += 1
                continue
            if m2:
                seq += 1
                prop_type = m1.group(1).strip()
                area = _coerce_area(m1.group(2))
                designation_date = _parse_dot_date(m1.group(3))
                cad = _clean_cadastral(m1.group(4))
                if cad:
                    seen_cad.add(cad)
                street = m2.group(1).strip().rstrip(",")
                house = m2.group(2).strip()
                apt = m2.group(3).strip() if m2.group(3) else None
                last_idx = addr_idx
                if apt is None and last_idx + 1 < len(lines):
                    m3 = _REMOVAL_L3_APT.match(lines[last_idx + 1])
                    if m3:
                        apt = m3.group(1).strip()
                        last_idx += 1
                address = f"{street}, д.{house}" + (f", кв.{apt}" if apt else "")
                i = last_idx  # advance past the consumed address (+ apt) lines

                flags, conf = _row_flags(address, cad, area)
                out.append({
                    "source_sha256": source_sha256,
                    "seq_no": seq,
                    "property_type": prop_type,
                    "address_raw": address,
                    "area_sqm": area,
                    "rosreestr_order_ref": None,
                    "rosreestr_order_date": None,
                    "rosreestr_reg_date": designation_date,
                    "cadastral_number": cad,
                    "flags": flags,
                    "row_confidence": round(max(0.0, conf - 0.2), 2),
                })
        i += 1
    return out


# Removal reason: classified from the decree's own preamble ("На основании
# ..."), NOT assumed. Found 2026-07-02 that removal decrees are near-
# universally OWNER/HEIR RECLAIM events (title documents surfaced, an
# inheritance case opened, or a court/enforcement order in the owner's favor)
# -- i.e. the bezkhoz procedure was HALTED, not completed. This corrects an
# earlier working assumption ("removal = transfer consummated") that turned
# out backwards; see docs/legal_mechanisms_review.md for the correction and
# the sampled decree evidence.
_REMOVAL_REASON_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"наследственн\w+\s+дел", re.I), "heir_inheritance_case"),
    (re.compile(r"документ\w*,?\s*подтвержда\w+\s+право\s+собственности", re.I),
     "owner_title_documents"),
    (re.compile(r"исполнительн\w+\s+лист", re.I), "court_enforcement_writ"),
    (re.compile(r"возбужден\w+\s+исполнительн\w+\s+производств", re.I),
     "enforcement_proceeding"),
    (re.compile(r"справки\s+нотариальной\s+палаты", re.I), "notary_chamber_certificate"),
    # Nonresidential removal decrees cite an EGRN extract showing existing
    # registered rights, rather than documents an owner personally submitted
    # -- same underlying logic as owner_title_documents (a registered right
    # already exists) but a distinct legal basis, worth its own label rather
    # than folding into that category or leaving 100 rows "unclassified".
    # Found 2026-07-03.
    (re.compile(r"выпис\w*\s+из\s+Единого\s+государственного\s+реестра\s+недвижимости", re.I),
     "egrn_extract_registered_rights"),
]


# Single-property removal decrees (heir/notary/enforcement-writ reasons) have
# NO annex table at all -- the one property is named inline in the decree
# body, e.g. "недвижимое имущество, расположенное по адресу: ... улица
# Карпинского, дом 37А, квартира 9" and/or "кадастровый номер 93:37:...,
# расположенное по адресу: ...". Found 2026-07-02 alongside the multi-row
# annex fix above -- _rows_from_removal_text returns [] for these by design
# (no annex to parse), so this is a separate single-record extractor used as
# a fallback. Originally hardcoded "улица" -- found 2026-07-03 this silently
# dropped every decree naming a проспект/переулок/бульвар address (e.g.
# "проспект Строителей, дом 41, квартира 80", decree №998) since the whole
# regex simply failed to match. Generalized to the full street-type word set.
_STREET_TYPE_WORD = (
    r"(?:улица|проспект|переулок|бульвар|шоссе|проезд|набережная)"
)
_REMOVAL_SINGLE_ADDR = re.compile(
    rf"по\s+адресу:.{{0,120}}?({_STREET_TYPE_WORD})\s+([А-ЯЁа-яё0-9№\-\s]+?),\s*дом\s+(\S+?),"
    r"(?:\s*квартира\s+(\S+))?",
    re.S | re.I,
)
_REMOVAL_SINGLE_TYPE = re.compile(r"жилое помещение|квартир\w+|дом\w*", re.I)


def _single_property_from_removal_text(text: str, source_sha256: str) -> list[dict]:
    m = _REMOVAL_SINGLE_ADDR.search(text)
    if not m:
        return []
    street = f"{m.group(1).strip()} {m.group(2).strip()}"
    house = m.group(3).strip().rstrip(",")
    apt = m.group(4).strip().rstrip(",") if m.group(4) else None
    address = f"{street}, д.{house}" + (f", кв.{apt}" if apt else "")
    cad = None
    cm = _CADASTRAL.search(text)
    if cm:
        cad = _clean_cadastral(cm.group(0))
    tm = _REMOVAL_SINGLE_TYPE.search(text)
    prop_type = tm.group(0) if tm else None
    flags, conf = _row_flags(address, cad, 0)  # area never given inline -> always flagged
    flags = [f for f in flags if f != "area_missing"] or flags  # keep area_missing; it's genuinely absent
    return [{
        "source_sha256": source_sha256,
        "seq_no": 1,
        "property_type": prop_type,
        "address_raw": address,
        "area_sqm": None,
        "rosreestr_order_ref": None,
        "rosreestr_order_date": None,
        "rosreestr_reg_date": None,
        "cadastral_number": cad,
        "flags": flags,
        "row_confidence": round(max(0.0, conf - 0.1), 2),  # single-record body extraction, slightly lower than annex
    }]


# A third single-property shape, found 2026-07-03: NONRESIDENTIAL removal
# decrees (e.g. №746/06.12.2024, №519/21.10.2024) phrase the operative
# paragraph differently -- no "дом"/"квартира" words at all, just "{street},
# {house}" directly, plus the area and cadastral inline: "нежилого
# помещения, площадью 70,0 кв.м, расположенного по адресу: г. Мариуполь,
# проспект Строителей, 19/16, принятого на учет в качестве бесхозяйного
# объекта недвижимости 23.07.2024 с кадастровым номером: 93:37:0010410:1458."
# _REMOVAL_SINGLE_ADDR doesn't match (no "дом" literal), so this is a
# separate extractor, tried after both other single-property/annex attempts
# fail.
_REMOVAL_NONRES_SINGLE_RE = re.compile(
    rf"нежилого помещения,\s*площадью\s*([\d,\.]+)\s*кв\.?\s*м,?\s*"
    rf"расположенного по адресу:\s*г\.?\s*Мариуполь,\s*"
    rf"({_STREET_TYPE_WORD})\s+([А-ЯЁа-яё0-9№\-\s]+?),\s*(\S+?),\s*принятого на учет.*?"
    rf"(\d{{2}}\.\d{{2}}\.\d{{4}})\s*с кадастровым номером:\s*(93:\s?\d+:\s?\d+:\s?\d+)",
    re.S | re.I,
)


def _nonres_single_property_from_removal_text(text: str, source_sha256: str) -> list[dict]:
    m = _REMOVAL_NONRES_SINGLE_RE.search(text)
    if not m:
        return []
    area = _coerce_area(m.group(1))
    street = f"{m.group(2).strip()} {m.group(3).strip()}"
    house = m.group(4).strip().rstrip(",")
    address = f"{street}, {house}"
    designation_date = _parse_dot_date(m.group(5))
    cad = _clean_cadastral(m.group(6))
    flags, conf = _row_flags(address, cad, area)
    return [{
        "source_sha256": source_sha256,
        "seq_no": 1,
        "property_type": "нежилое помещение",
        "address_raw": address,
        "area_sqm": area,
        "rosreestr_order_ref": None,
        "rosreestr_order_date": None,
        "rosreestr_reg_date": designation_date,
        "cadastral_number": cad,
        "flags": flags,
        "row_confidence": round(max(0.0, conf - 0.1), 2),
    }]


# A fourth shape, found 2026-07-03: NONRESIDENTIAL removal decrees with a
# multi-property "Перечень"/table annex, e.g. №746/06.12.2024's 3-4 row
# lists. Unlike the residential _REMOVAL_L1/_REMOVAL_ADDR_CORE annex, this
# layout has NO "г. Мариуполь" city marker and NO "дата снятия..."
# placeholder -- just "{street прefix, sometimes badly OCR-garbled}
# {ProperNoun}, {house} {area}? {date} {cadastral}" per row, seq/type on a
# separate/adjacent line that's frequently unreadable ("ПЕЗИТОЕ"/"НЕЯЗАОЕ"
# for "нежилое"). OCR quality on these specific annexes is markedly worse
# than the residential ones (even the street-type prefix itself is often
# corrupted, e.g. "просискг"/"просиект"/"просиекг" for "проспект") --
# _NONRES_ANNEX_ROW_RE tries the real street-type alternation first, and
# falls back to accepting ANY short token immediately before a Capitalized
# proper noun as a (possibly garbled) street prefix, rather than dropping
# the row outright; toponym.classify_street() will correctly flag a truly
# unrecognisable prefix as UNKNOWN downstream rather than misclassifying it.
# Scoped to the text AFTER "Перечень"/"РЕЕСТР" (the annex heading) to avoid
# spurious matches against addresses that might appear in the preamble.
_NONRES_STREET_STRICT = r"(?i:ул|пр|просп|пр-кт|пр-т|пер|бул|б-р|мкр)\S*\.?"
_NONRES_STREET_LOOSE = r"\S{3,12}"
_NONRES_ANNEX_ROW_RE = re.compile(
    rf"(?:({_NONRES_STREET_STRICT})|({_NONRES_STREET_LOOSE}))\s+"
    r"([А-ЯЁ][а-яёА-ЯЁ]+(?:\s[А-ЯЁ][а-яёА-ЯЁ]+)?),?\s*"
    r"([^\s,|]+),?\s*\|?\s*"
    r"([\d,\.]+)?\s*\|?\s*"
    r"(\d{2}\.\d{2}\.?\d{4})\s*\|?\s*"
    r"(93:\s?\d+:\s?\d+:\s?\d+)"
)
_ANNEX_HEADING_RE = re.compile(r"(?:Перечень|РЕЕСТР)\s", re.I)


def _rows_from_nonres_annex_text(text: str, source_sha256: str) -> list[dict]:
    heading = _ANNEX_HEADING_RE.search(text)
    scope = text[heading.start():] if heading else text
    seen_cad: set[str] = set()
    out: list[dict] = []
    seq = 0
    for m in _NONRES_ANNEX_ROW_RE.finditer(scope):
        cad = _clean_cadastral(m.group(7))
        if cad in seen_cad:
            continue  # multi-line rows can be matched more than once by .finditer scanning
        seen_cad.add(cad)
        seq += 1
        street_word = (m.group(1) or m.group(2) or "").strip()
        proper_noun = m.group(3).strip()
        house = m.group(4).strip().rstrip(",")
        area = _coerce_area(m.group(5)) if m.group(5) else None
        date = _parse_dot_date(m.group(6))
        address = f"{street_word} {proper_noun}, {house}".strip()
        flags, conf = _row_flags(address, cad, area)
        if m.group(2):  # matched via the loose/garbled fallback, not a recognised prefix
            flags = flags + ["address_suspect"] if "address_suspect" not in flags else flags
            conf = round(max(0.0, conf - 0.2), 2)
        out.append({
            "source_sha256": source_sha256,
            "seq_no": seq,
            "property_type": "нежилое помещение",
            "address_raw": address,
            "area_sqm": area,
            "rosreestr_order_ref": None,
            "rosreestr_order_date": None,
            "rosreestr_reg_date": date,
            "cadastral_number": cad,
            "flags": flags,
            "row_confidence": round(max(0.0, conf - 0.3), 2),  # noisiest extraction path -- capped lower
        })
    return out


def _classify_removal_reason(text: str) -> str:
    # Case-insensitive on "[Нн]а основании" -- found 2026-07-03 the original
    # capital-only "На" match silently missed every decree where the phrase
    # sits mid-sentence lowercase (all 13 nonresidential-annex decrees),
    # falling back to text[:300] (the letterhead, not the actual reason) and
    # miscounting them "unclassified".
    m = re.search(r"[Нн]а основании.{0,300}", text, re.S)
    basis = m.group(0) if m else text[:300]
    for pattern, label in _REMOVAL_REASON_PATTERNS:
        if pattern.search(basis):
            return label
    return "unclassified"


# Text-position table settings — infer columns from text alignment, not lines.
_TEXT_TABLE_SETTINGS = {
    "vertical_strategy": "text",
    "horizontal_strategy": "text",
    "snap_tolerance": 4,
}

# Off-topic-decree gate. `ownerless_lists.py`'s "procedure" classifier matches
# any "О внесении изменений..." title (a generic amendment pattern, needed to
# catch genuine amendments to the bezkhoz procedure/commission acts) and the
# curated cur_cc=7767 section crawl also sweeps in "unknown"-kind pages whose
# title matched none of the strict bezkhoz patterns. Both of those buckets can
# and do contain decrees that are NOT about the ownerless-property registry at
# all — e.g. decree found 2026-07-02 titled "О внесении изменений в
# постановление... «Об утверждении перечня мероприятий... капитального
# ремонта общего имущества в многоквартирных домах...»" (a capital-repair
# program amendment) got matched by the generic procedure pattern and its
# repair-cost-estimate table (Общая площадь / Стоимость капитального ремонта /
# Плановая дата — a different schema entirely) was force-mapped into the
# bezkhoz row schema (type/address/area/cadastral), producing nonsense rows
# ("сатоола", "обадевт", no address, no cadastral).
#
# designation/removal decree_kinds are exempt from this gate — their titles
# are already strictly matched against "признани...бесхозяйн" /
# "включени/исключени...реестр" by ownerless_lists.py, so by construction they
# ARE about the bezkhoz registry. For procedure/unknown/demolition_declaration
# kinds (looser or unrelated-by-design title matches), only attempt table
# extraction if "бесхозя" actually appears in the decree's own title or OCR
# text — a cheap, high-precision confirmation the annex is even plausibly a
# property list, applied before spending effort on table-shape heuristics.
_BEZKHOZ_ROOT = re.compile(r"бесхозя", re.I)
_EXEMPT_KINDS = {"designation", "removal"}


def _looks_bezkhoz(title: str, text: str) -> bool:
    return bool(_BEZKHOZ_ROOT.search(title) or _BEZKHOZ_ROOT.search(text))


def parse_decree_pdf(pdf_path: Path, source_sha256: str, title: str = "",
                      decree_kind: str = "") -> list[dict]:
    """Extract all property rows from an OCR'd decree-annex PDF.

    Tries line-based tables, then text-position tables, then a text fallback.
    Returns [] if the PDF genuinely has no recoverable text (OCR failed), or
    if decree_kind isn't designation/removal and neither the title nor the
    OCR text mentions бесхозя — see _looks_bezkhoz above.
    """
    rows: list[dict] = []
    full_text_parts: list[str] = []
    strategy_used = "none"

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            full_text_parts.append(page.extract_text() or "")

    full_text_probe = "\n".join(full_text_parts)
    if decree_kind not in _EXEMPT_KINDS and not _looks_bezkhoz(title, full_text_probe):
        log.info("%s: skipped — decree_kind=%s and no 'бесхозя' in title/text "
                  "(off-topic decree swept in by a loose title match, not a "
                  "bezkhoz registry annex): %s",
                  pdf_path.name, decree_kind or "?", (title or "")[:100])
        return []

    if decree_kind == "removal":
        # Removal annexes never match the designation-tuned cell layout --
        # go straight to the dedicated 3-line text parser (see
        # _rows_from_removal_text above).
        rows = _rows_from_removal_text(full_text_probe, source_sha256)
        strategy_used = "removal_text" if rows else "none"
        if not rows:
            rows = _single_property_from_removal_text(full_text_probe, source_sha256)
            strategy_used = "removal_single_property" if rows else "none"
        if not rows:
            rows = _nonres_single_property_from_removal_text(full_text_probe, source_sha256)
            strategy_used = "removal_nonres_single_property" if rows else "none"
        if not rows:
            rows = _rows_from_nonres_annex_text(full_text_probe, source_sha256)
            strategy_used = "removal_nonres_annex" if rows else "none"
        full_text = full_text_probe
        decree_meta = _parse_title_meta(title) if title else {}
        decree_meta.update(_extract_decree_meta(full_text))
        decree_meta["removal_reason"] = _classify_removal_reason(full_text)
        for row in rows:
            row.update(decree_meta)
            row["extract_strategy"] = strategy_used
        clean = sum(1 for r in rows if not r["flags"])
        log.info("%s: %d rows (%d claim-grade) via %s — decree №%s, %s, reason=%s",
                  pdf_path.name, len(rows), clean, strategy_used,
                  decree_meta.get("decree_number", "?"),
                  decree_meta.get("decree_date", "?"),
                  decree_meta.get("removal_reason"))
        return rows

    if decree_kind == "registration":
        # Registration annexes have their own 3-line table shape (no
        # rosreestr_order_ref/cadastral columns at all — see
        # _rows_from_registration_table_text above); the generic cell/
        # text-fallback paths below don't fit it and silently misalign.
        rows = _rows_from_registration_table_text(full_text_probe, source_sha256)
        strategy_used = "registration_text" if rows else "none"
        full_text = full_text_probe
        decree_meta = _parse_title_meta(title) if title else {}
        decree_meta.update(_extract_decree_meta(full_text))
        for row in rows:
            row.update(decree_meta)
            row["extract_strategy"] = strategy_used
        clean = sum(1 for r in rows if not r["flags"])
        log.info("%s: %d rows (%d claim-grade) via %s — decree №%s, %s",
                  pdf_path.name, len(rows), clean, strategy_used,
                  decree_meta.get("decree_number", "?"),
                  decree_meta.get("decree_date", "?"))
        return rows

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_rows: list[dict] = []
            # (1) line-based tables
            for table in page.extract_tables() or []:
                for raw in table:
                    rec = _row_from_cells([(c or "") for c in raw], source_sha256)
                    if rec:
                        page_rows.append(rec)
            if page_rows:
                strategy_used = "lines"
            else:
                # (2) text-position tables
                for table in page.extract_tables(_TEXT_TABLE_SETTINGS) or []:
                    for raw in table:
                        rec = _row_from_cells([(c or "") for c in raw], source_sha256)
                        if rec:
                            page_rows.append(rec)
                if page_rows:
                    strategy_used = "text_cells"
            rows.extend(page_rows)

    full_text = "\n".join(full_text_parts)
    if not full_text.strip():
        log.warning("%s: still no text after OCR — OCR likely failed; re-run 06a",
                    pdf_path.name)
        return []

    # (3) text fallback if structured extraction found nothing, OR if it found
    # rows but NONE are claim-grade — a real failure mode confirmed 2026-07-17:
    # pdfplumber's text-position table detection can find a spurious/misaligned
    # table (registration-decree pages have a different column layout than the
    # designation-decree schema _row_from_cells expects: state-text and
    # "информация отсутствует" columns instead of a basis-ref/cadastral pair),
    # producing NON-EMPTY but garbage rows (truncated addresses like "г. Мар",
    # every row flagged cadastral_missing+address_suspect+area_missing) that
    # silently blocked this fallback from ever running. The 2-line text parser
    # below handles this exact table shape correctly (confirmed: adjacent
    # registration decrees parsed via text_fallback hit 90%+ claim-grade), so
    # prefer it whenever the cell-based pass came back with zero clean rows.
    if not rows or not any(not r["flags"] for r in rows):
        fallback_rows = _rows_from_text(full_text, source_sha256)
        if fallback_rows and (
            not rows or sum(1 for r in fallback_rows if not r["flags"]) > 0
        ):
            rows = fallback_rows
            strategy_used = "text_fallback"

    # Decree number/date: prefer HTML title (handwritten OCR is unreliable);
    # signing official still comes from OCR text.
    decree_meta = _parse_title_meta(title) if title else {}
    decree_meta.update(_extract_decree_meta(full_text))
    for row in rows:
        row.update(decree_meta)
        row["extract_strategy"] = strategy_used

    clean = sum(1 for r in rows if not r["flags"])
    log.info("%s: %d rows (%d claim-grade) via %s — decree №%s, %s",
             pdf_path.name, len(rows), clean, strategy_used,
             decree_meta.get("decree_number", "?"),
             decree_meta.get("decree_date", "?"))
    return rows


# ── known OCR corrections ────────────────────────────────────────────────────
# Source-cited, narrowly-scoped corrections for specific Cyrillic-to-Cyrillic
# OCR misreads that _row_flags doesn't catch (no Latin chars, has a digit).
# Keyed by source_sha256 (the OCR'd PDF) so a correction can never silently
# apply to a different document. The verbatim OCR text is preserved in
# address_raw_ocr; address_raw becomes the corrected value.
#
# Decree №1731 (2025-11-13), пр-кт Ленина apartment cluster: Tesseract
# consistently inserts a spurious "З" before the "А" building-letter suffix --
# 11 rows read "д.123ЗА" and one (seq_no 120, кв.98, cadastral
# 93:37:0010102:4587) reads "д.12ЗА" (spurious "З" AND a dropped "3"). Evidence
# this is OCR noise, not a real address "123ЗА"/"12ЗА":
#  - geocoded_buildings.jsonl: "просп. Миру 123А" (building_key
#    AVENUE:ленина|123а) is a Nominatim ROOFTOP match (confidence 0.9), ~150m
#    from "просп. Миру 123" (AVENUE:ленина|123, also 0.9) -- a real, adjacent
#    building.
#  - "просп. Миру 123ЗА" / "проспект Ленина 123за" returns no house-level
#    match at all (confidence 0.5, road-level only, in a different
#    microdistrict ~1.3km away) -- "123за" is not a real OSM address.
#  - The 12 corrected rows form one numerically coherent apartment range
#    (кв. 8, 14, 51, 52, 56, 61, 85, 86, 90, 93, 98, 102, 108, 113), consistent
#    with a single large apartment block.
# Confirmed against this OCR'd PDF's text 2026-06-10.
_LENINA_123A_OCR_FIX_SHA = "01c1e3bbae234bfbc24839ca33d409efc74fc96b7792be60d64f76b24c20ec3e"
_LENINA_123A_OCR_FIX_RE = re.compile(r"^(пр-кт Ленина, д\.)(123ЗА|12ЗА)(, кв\.\d+)$")

# Tesseract sometimes drops the leading "у" from "ул." (likely clipped at the
# top edge of a cropped table cell, since "у" has a descender), leaving "л.",
# "л ", or "л." with NO following space before the street name. Found 22 rows
# across 2 OCR'd decree PDFs (sha 49951b02153d..., 01c1e3bbae23...), covering
# 9 different streets that all have many more rows correctly read as
# "ул. <name>" elsewhere in the same/other documents (Артёма, Олимпийская,
# Киевская, Февральская, Горловская, Кронштадтская, Гаганрогская, Зелинского,
# 50 лет СССР) -- e.g. seq_no 237/242 "л. Артёма, д.96, кв.X" vs. seq_no
# 214-240 "ул. Артёма, д.96, кв.Y" (same building, cadastral block
# 93:37:0010110, prewar "вул. Архипа Куїнджі"). "л"/"л." is not a real
# Russian street-type abbreviation (toponym._CLASS_MAP), so this is a
# structural fix, not a street-name correction -- it does NOT touch
# "Гаганрогская" vs "Таганрогская" (a separate, pre-existing question; both
# already have their own STREET-classified clusters). Not source_sha256-scoped
# since the same dropped-"у" failure mode recurs across documents.
#
# The captured street-name group allows a leading digit (e.g. "л. 50 лет
# СССР, д.32, кв.X" -> "ул. 50 лет СССР, ...") and zero whitespace after
# "л"/"л." (e.g. "л.Зелинского, д.13, кв.X" -> "ул. Зелинского, ..."), in
# addition to the original "л. <Name>"/"л <Name>" forms. A repo-wide check
# confirms address_raw never starts with bare lowercase "л" except for these
# 22 truncation rows -- no false-positive risk. Confirmed 2026-06-10.
_TRUNCATED_UL_RE = re.compile(r"^л\.?\s*([А-ЯЁ0-9].*?,\s*д\.\d.*)$")


def _apply_known_ocr_corrections(row: dict) -> None:
    """Apply documented OCR corrections in place: the source-scoped
    _LENINA_123A_OCR_FIX_RE and the general _TRUNCATED_UL_RE (see above).
    No-op for rows matching neither."""
    addr = row.get("address_raw") or ""

    if row.get("source_sha256") == _LENINA_123A_OCR_FIX_SHA:
        m = _LENINA_123A_OCR_FIX_RE.match(addr)
        if m:
            row["address_raw_ocr"] = addr
            addr = row["address_raw"] = f"{m.group(1)}123А{m.group(3)}"
            row["correction_note"] = (
                f"OCR misread house number as '{m.group(2)}'; corrected to '123А' "
                "-- decree №1731 пр-кт Ленина apartment cluster, see "
                "_LENINA_123A_OCR_FIX_RE in this script for evidence. "
                "Confirmed 2026-06-10."
            )

    m = _TRUNCATED_UL_RE.match(addr)
    if m:
        if "address_raw_ocr" not in row:
            row["address_raw_ocr"] = addr
        row["address_raw"] = f"ул. {m.group(1)}"
        note = ("OCR dropped leading 'у' from 'ул.' (read as 'л.'/'л'); "
                "restored to 'ул.' -- see _TRUNCATED_UL_RE in this script. "
                "Confirmed 2026-06-10.")
        existing = row.get("correction_note")
        row["correction_note"] = f"{existing} {note}" if existing else note


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    con = forensics.open_state()
    # Read OCR DERIVATIVES, and carry each one's parent raw-scan sha for the
    # chain of custody (derived_from). Designations first — they hold the
    # property registries that join to the court docket and damage data.
    ocr_sources = con.execute(
        """SELECT sha256, raw_path, title, source_type, derived_from
           FROM source_document
           WHERE source_type LIKE 'ownerless_decree_%_ocr_pdf'
           ORDER BY
             CASE WHEN source_type LIKE '%designation%' THEN 0 ELSE 1 END,
             captured_at"""
    ).fetchall()

    if not ocr_sources:
        # Are there un-OCR'd scans waiting?
        n_raw = con.execute(
            """SELECT COUNT(*) FROM source_document
               WHERE source_type LIKE 'ownerless_decree_%_pdf'
                 AND derived_from IS NULL"""
        ).fetchone()[0]
        if n_raw:
            log.warning(
                "No OCR derivatives yet, but %d scanned annexes are captured.\n"
                "Run OCR first:  PYTHONPATH=src python scripts/06a_ocr_decrees.py",
                n_raw,
            )
        else:
            log.warning("No decree annexes in the store — run 05_crawl first.")
        return

    out_dir = config.PROJECT_ROOT / "data" / "parsed"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "ownerless_decrees.jsonl"

    total = claim_grade = 0
    from collections import Counter
    flag_tally: Counter = Counter()
    with out_path.open("w", encoding="utf-8") as fh:
        for ocr_sha, raw_path, title, source_type, parent_sha in ocr_sources:
            p = Path(raw_path)
            if not p.exists():
                log.error("OCR file missing: %s", raw_path)
                continue
            decree_kind = (
                source_type.replace("ownerless_decree_", "")
                           .replace("_ocr_pdf", "")
            )
            try:
                rows = parse_decree_pdf(p, ocr_sha, title=title, decree_kind=decree_kind)
            except Exception:
                log.exception("failed to parse %s", raw_path)
                continue
            for row in rows:
                # Chain of custody: OCR artifact + its parent raw scan + kind.
                row["source_sha256"] = ocr_sha
                row["raw_scan_sha256"] = parent_sha
                row["decree_kind"] = decree_kind
                _apply_known_ocr_corrections(row)
                if not row["flags"]:
                    claim_grade += 1
                for f in row["flags"]:
                    flag_tally[f] += 1
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            total += len(rows)

    log.info("done — %d rows written to %s", total, out_path)
    log.info("  claim-grade (no flags): %d / %d", claim_grade, total)
    if flag_tally:
        log.info("  flags: %s", dict(flag_tally.most_common()))
    if total == 0:
        log.warning(
            "Zero rows extracted from OCR derivatives. Inspect one OCR'd PDF's "
            "text layer manually — OCR may have produced garbage (low-DPI scan, "
            "rotated pages). Consider re-running 06a after tuning ocrmypdf args."
        )


if __name__ == "__main__":
    main()
