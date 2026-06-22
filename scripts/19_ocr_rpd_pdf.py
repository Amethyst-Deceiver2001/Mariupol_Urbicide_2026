#!/usr/bin/env python3
"""Stage 2g: extract text and cadastral data from captured ЕИСЖС RPD/PD PDFs.

Reads source_type='eisghs_rpd_pdf' raw PDF captures (stored as .bin files
with possibly wrong content-type, but valid %PDF- magic) and extracts:
  - Cadastral numbers of the land parcel(s)
  - Land area (m²)
  - Project name and RPD number (cross-check against JSON detail)
  - Developer INN / OGRN (independent confirmation)
  - Address / settlement name

Text is extracted with pdfplumber (text-layer PDFs — confirmed present).
Each extracted text body is persisted as a derived artifact via
forensics.capture_derived() with:
  derived_from = source sha256 of the RPD PDF
  transform    = "pdfplumber:text_extract"

OUTPUT FILES
------------
data/parsed/eisghs_rpd_cadastrals.jsonl
  One record per RPD PDF. Key fields:
    source_sha256, derived_sha256, eisghs_id, rpd_num, rpd_num_in_pdf,
    project_name_in_pdf, project_title_in_pdf, developer_inn_in_pdf,
    developer_ogrn_in_pdf, cadastral_numbers, area_sqm, address_in_pdf, flags

LEGAL-GRADE IMPACT
------------------
The RPD PDF is an independent source that contains cadastral numbers.
When the RPD cadastral matches the cadastral in dnr_land_orders.jsonl,
that creates a 2-source independent confirmation:
  source 1: dnr_land_order (INN exact join) → cadastral
  source 2: eisghs_rpd_pdf (text extraction) → same cadastral
Combined with the ЕИСЖС commissioned status (third source), this pushes
object 54271 (Дом с часами / RKS-Девелопмент) to legal_grade=True.

Run scripts/18_parse_eisghs_mariupol.py after this script to recompute
legal grades with the RPD cadastral data included.

Re-running is safe — output overwritten; derived artifacts are idempotent.
"""
from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
import tempfile
from pathlib import Path

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

try:
    import pdfplumber
    _PDFPLUMBER = True
except ImportError:
    _PDFPLUMBER = False
    log.warning("pdfplumber not available — falling back to pdftotext CLI")

# pdftotext location (homebrew poppler)
_PDFTOTEXT = "pdftotext"


# ── regex patterns ─────────────────────────────────────────────────────────────

# Cadastral numbers: 93:37:xxxxxxx:nn (Mariupol DNR registration zone 93)
_CADASTRAL = re.compile(r"93:\d+:\d+:\d+")

# Land parcel area: specifically from §12.3.2 "Площадь земельного участка"
# Matches "3 501,00 м²" or "3501.00 м2" etc., anchored near the label.
# Pattern: area label (with possible soft-hyphen artifacts) then a value on the same/next line.
_AREA_PARCEL_LABEL = re.compile(
    r"[Пп]ло\S*\s+зе\S*\s+[уу]час\S*"   # "Площадь земельного участка" with OCR variants
    r".{0,200}?"                          # table layout: label → section num → value (~150 chars)
    r"([\d][\d\s]{0,8}[\.,]\d{2})\s*м\s*[²2]",
    re.S | re.I,
)
# Fallback: generic area match for documents without the standard §12 label
_AREA_GENERIC = re.compile(
    r"([\d][\d\s]{0,10}[\.,]\d{2})\s*м\s*[²2]"
    r"|"
    r"([\d][\d\s]{0,10})\s*м\s*[²2]",
    re.I,
)

# RPD number: "93-000001" or "№ 93-000001" — section header or table value
_RPD_NUM = re.compile(r"\b(93-0{4,5}\d{1,3})\b")

# Developer INN: DNR-registered companies have INNs starting with 93 (10 digits).
# These appear at §2.1.1 without a keyword prefix; the escrow bank INN appears
# later at §19 with an explicit "ИНН:" label (and starts with 7x/other prefixes).
# Strategy: collect ALL 10-digit sequences starting with 93 and return the first
# (§2.1.1 precedes §12 and §19).
_INN_DNR = re.compile(r"\b(93\d{8})\b")

# OGRN: 13-15 digits
_OGRN = re.compile(r"(?:ОГРН|огрн)\s*:?\s*(\d{13,15})")

# Project name: after '"' (document header uses typewriter quotes or «»)
_PROJECT_QUOT = re.compile(r'["«"]([^"»"]{3,60})[»""]')

# Project title — the declaration's full project description, which sits
# between the "№ <rpd_num> от <date>" header line and the "Дата первичного
# размещения" line. This is the developer's own description of WHAT they are
# building and WHERE — often naming the pre-occupation street/address (e.g.
# "...по пр-ту Нахимова, 82 в г. Мариуполе") even when the ЕИСЖС object record
# carries the post-occupation address. Independent (federal RPD filing) source
# for address-laundering corroboration, distinct from the DNR land order.
_PROJECT_TITLE = re.compile(
    r"№\s*\d{2}-\d{4,6}\s+от\s+\d{2}\.\d{2}\.\d{4}\s*\n+(.+?)\n+\s*Дата первичного размещения",
    re.S,
)

# Date: DD.MM.YYYY
_DATE_DOT = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")


def _clean_area(raw: str) -> float | None:
    """Parse area string '3 501,00' or '3501.00' → 3501.0"""
    s = re.sub(r"\s+", "", raw).replace(",", ".").split("+")[0].split("-")[0]
    try:
        return float(s)
    except ValueError:
        return None


def extract_text_pdfplumber(path: Path) -> str | None:
    """Extract full text from PDF using pdfplumber."""
    try:
        with pdfplumber.open(str(path)) as pdf:
            parts = []
            for page in pdf.pages:
                text = page.extract_text(x_tolerance=2, y_tolerance=2)
                if text:
                    parts.append(text)
        return "\n".join(parts) if parts else None
    except Exception as exc:
        log.warning("pdfplumber failed on %s: %s", path.name, exc)
        return None


def extract_text_pdftotext(path: Path) -> str | None:
    """Extract full text from PDF using pdftotext CLI (poppler)."""
    try:
        result = subprocess.run(
            [_PDFTOTEXT, "-layout", "-enc", "UTF-8", str(path), "-"],
            capture_output=True, timeout=60,
        )
        if result.returncode == 0:
            return result.stdout.decode("utf-8", errors="replace")
        log.warning("pdftotext exited %d for %s: %s",
                    result.returncode, path.name, result.stderr[:200])
        return None
    except FileNotFoundError:
        log.error("pdftotext not found — install poppler")
        return None
    except subprocess.TimeoutExpired:
        log.warning("pdftotext timed out on %s", path.name)
        return None


def extract_text(path: Path) -> str | None:
    """Extract text, preferring pdftotext (handles kerned/spaced fonts correctly).

    pdfplumber inserts intra-word spaces for PDFs with tight kerning (common in
    Russian government document generators), breaking regex word-boundary matches.
    pdftotext -layout uses positional analysis and reconstructs words correctly.
    pdfplumber is used as fallback if pdftotext is unavailable.
    """
    text = extract_text_pdftotext(path)
    if not text and _PDFPLUMBER:
        text = extract_text_pdfplumber(path)
    return text


def parse_rpd_text(text: str, source_sha256: str, eisghs_id: int | None, rpd_num_expected: str | None) -> dict:
    """Extract structured fields from RPD PDF text."""
    flags: list[str] = []

    # Cadastral numbers — deduplicated, preserving first occurrence order
    cadastrals = list(dict.fromkeys(_CADASTRAL.findall(text)))
    if not cadastrals:
        flags.append("cadastral_missing")

    # Area — prefer the explicit §12.3.2 "Площадь земельного участка" value.
    area_sqm = None
    m_parcel = _AREA_PARCEL_LABEL.search(text)
    if m_parcel:
        area_sqm = _clean_area(m_parcel.group(1))
    if area_sqm is None:
        # Fallback: scan all area-like values and take the smallest plausible one
        # (land parcel is smaller than total building area).
        from collections import Counter
        areas: list[float] = []
        for m in _AREA_GENERIC.finditer(text):
            raw = (m.group(1) or m.group(2) or "").strip()
            v = _clean_area(raw)
            if v and 100 < v < 50_000:
                areas.append(v)
        if areas:
            # Take the smallest value in the realistic parcel range (200–10000 m²).
            parcel_candidates = [v for v in areas if 200 <= v <= 10_000]
            area_sqm = min(parcel_candidates) if parcel_candidates else None
    if area_sqm is None:
        flags.append("area_missing")

    # RPD number
    rpd_matches = _RPD_NUM.findall(text)
    rpd_num_in_pdf = rpd_matches[0] if rpd_matches else None
    if rpd_num_expected and rpd_num_in_pdf and rpd_num_in_pdf != rpd_num_expected:
        flags.append(f"rpd_num_mismatch:{rpd_num_in_pdf}!={rpd_num_expected}")

    # Developer INN — DNR INNs start with 93 and appear at §2.1.1 without a keyword prefix.
    # Bank/escrow INNs appear later (§19) with explicit "ИНН:" labels and start with 7x.
    # Return the first 93-prefix INN found (§2 precedes §19 in all DNR RPD forms).
    dnr_inns = _INN_DNR.findall(text)
    inn_in_pdf = dnr_inns[0] if dnr_inns else None

    # OGRN
    ogrn_matches = _OGRN.findall(text)
    ogrn_in_pdf = ogrn_matches[0] if ogrn_matches else None

    # Project name (appears in document header and section 1 area)
    project_names = _PROJECT_QUOT.findall(text)
    project_name_in_pdf = project_names[0].strip() if project_names else None

    # Project title — full description line(s) under the declaration header
    m_title = _PROJECT_TITLE.search(text)
    project_title_in_pdf = re.sub(r"\s+", " ", m_title.group(1)).strip() if m_title else None

    return {
        "source_sha256": source_sha256,
        "derived_sha256": None,   # filled after capture_derived()
        "eisghs_id": eisghs_id,
        "rpd_num_expected": rpd_num_expected,
        "rpd_num_in_pdf": rpd_num_in_pdf,
        "project_name_in_pdf": project_name_in_pdf,
        "project_title_in_pdf": project_title_in_pdf,
        "developer_inn_in_pdf": inn_in_pdf,
        "developer_ogrn_in_pdf": ogrn_in_pdf,
        "cadastral_numbers": cadastrals,
        "area_sqm": area_sqm,
        "flags": flags,
    }


def _eisghs_id_from_title(title: str) -> int | None:
    """Extract ЕИСЖС object ID from source_document title."""
    m = re.search(r"\bid=(\d+)", title)
    return int(m.group(1)) if m else None


def _rpd_num_from_title(title: str) -> str | None:
    """Try to extract RPD number from title (not always present there)."""
    m = _RPD_NUM.search(title)
    return m.group(1) if m else None


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
    )

    con = forensics.open_state()

    sources = con.execute(
        """SELECT sha256, raw_path, title
           FROM source_document
           WHERE source_type = 'eisghs_rpd_pdf'
           ORDER BY title"""
    ).fetchall()

    if not sources:
        log.error(
            "No eisghs_rpd_pdf records in state DB — "
            "run scripts/17_crawl_eisghs_mariupol.py first."
        )
        return

    log.info("Found %d RPD PDF records", len(sources))

    # Also load the ЕИСЖС object details to cross-reference RPD numbers and INNs
    obj_by_id: dict[int, dict] = {}
    obj_sources = con.execute(
        "SELECT sha256, raw_path FROM source_document WHERE source_type='eisghs_house_detail'"
    ).fetchall()
    for sha, path in obj_sources:
        try:
            d = json.loads(Path(path).read_bytes())
            data = d.get("data") or d
            eid = data.get("id")
            if eid:
                obj_by_id[eid] = {
                    "rpd_num": data.get("rpdNum"),
                    "dev_inn": (data.get("developer") or {}).get("devInn"),
                    "nameObj": data.get("nameObj"),
                }
        except Exception:
            pass

    # Build rpd_num → [eisghs_ids] index so that when a PDF is shared across
    # multiple objects (same construction permit covers several buildings), we
    # emit one record per object rather than only for the first one fetched.
    from collections import defaultdict as _dd
    rpd_num_to_ids: dict[str, list[int]] = _dd(list)
    for eid, meta in obj_by_id.items():
        rn = meta.get("rpd_num")
        if rn:
            rpd_num_to_ids[rn].append(eid)

    out_dir = config.PROJECT_ROOT / "data" / "parsed"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "eisghs_rpd_cadastrals.jsonl"

    records: list[dict] = []
    errors = 0
    total_cadastrals = 0

    with out_path.open("w", encoding="utf-8") as fh:
        for sha, raw_path, title in sources:
            p = Path(raw_path)
            if not p.exists():
                log.error("File missing: %s", raw_path)
                errors += 1
                continue

            # Verify it's actually a PDF
            raw_bytes = p.read_bytes()
            if not raw_bytes[:5] == b"%PDF-":
                log.warning("Not a PDF (bad magic): %s", raw_path)
                errors += 1
                continue

            eisghs_id = _eisghs_id_from_title(title)
            obj_meta = obj_by_id.get(eisghs_id, {}) if eisghs_id else {}
            rpd_num_expected = obj_meta.get("rpd_num") or _rpd_num_from_title(title)

            text = extract_text(p)
            if not text or len(text.strip()) < 100:
                log.warning("id=%-6s  no text extracted from %s", eisghs_id, p.name)
                errors += 1
                continue

            rec = parse_rpd_text(text, sha, eisghs_id, rpd_num_expected)

            # Persist extracted text as a derived artifact (chain of custody)
            text_bytes = text.encode("utf-8")
            derived_sha = forensics.capture_derived(
                text_bytes,
                derived_from=sha,
                transform="pdfplumber:text_extract" if _PDFPLUMBER else "pdftotext:text_extract",
                source_type="eisghs_rpd_text",
                title=f"ЕИСЖС RPD extracted text — id={eisghs_id} rpd={rpd_num_expected}",
                description=(
                    f"Full text extracted from RPD PDF (pdId for ЕИСЖС object {eisghs_id}). "
                    f"Cadastrals: {rec['cadastral_numbers']}. "
                    f"Area: {rec['area_sqm']} m²."
                ),
                content_type="text/plain",
                con=con,
            )
            rec["derived_sha256"] = derived_sha

            # INN cross-check: does the PDF-extracted INN match the API INN?
            api_inn = obj_meta.get("dev_inn")
            if api_inn and rec["developer_inn_in_pdf"] and rec["developer_inn_in_pdf"] != api_inn:
                rec["flags"].append(f"inn_mismatch:pdf={rec['developer_inn_in_pdf']}!={api_inn}")
            elif api_inn and rec["developer_inn_in_pdf"] == api_inn:
                rec["flags"].append("inn_confirmed")

            cadastral_count = len(rec["cadastral_numbers"])
            total_cadastrals += cadastral_count

            flag_str = ",".join(rec["flags"]) if rec["flags"] else "ok"
            log.info(
                "id=%-6s  rpd=%-12s  cadastrals=%s  area=%-10s  inn=%s  flags=%s",
                eisghs_id,
                rec.get("rpd_num_in_pdf") or "–",
                rec["cadastral_numbers"] or "[]",
                f"{rec['area_sqm']} m²" if rec["area_sqm"] else "–",
                rec.get("developer_inn_in_pdf") or "–",
                flag_str,
            )

            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            records.append(rec)

            # Emit sibling records for other objects sharing the same rpdNum.
            # These arise when a single construction permit covers multiple
            # buildings (same PDF, same sha256, different eisghs_id).
            sibling_ids = [
                sid for sid in rpd_num_to_ids.get(rpd_num_expected or "", [])
                if sid != eisghs_id
            ]
            for sid in sibling_ids:
                sib_meta = obj_by_id.get(sid, {})
                sib_rec = dict(rec)
                sib_rec["eisghs_id"] = sid
                sib_rec["flags"] = list(rec["flags"])
                sib_rec["flags"].append("rpd_sibling")
                # INN cross-check for sibling
                sib_api_inn = sib_meta.get("dev_inn")
                if sib_api_inn and rec["developer_inn_in_pdf"] and rec["developer_inn_in_pdf"] != sib_api_inn:
                    sib_rec["flags"].append(f"inn_mismatch:pdf={rec['developer_inn_in_pdf']}!={sib_api_inn}")
                elif sib_api_inn and rec.get("developer_inn_in_pdf") == sib_api_inn:
                    if "inn_confirmed" not in sib_rec["flags"]:
                        sib_rec["flags"].append("inn_confirmed")
                log.info(
                    "id=%-6s  rpd=%-12s  (sibling of id=%s)",
                    sid, rpd_num_expected, eisghs_id,
                )
                fh.write(json.dumps(sib_rec, ensure_ascii=False) + "\n")
                records.append(sib_rec)

    # ── Summary ─────────────────────────────────────────────────────────────
    clean = sum(1 for r in records if not [f for f in r["flags"] if not f.startswith("inn_")])
    with_cadastrals = sum(1 for r in records if r["cadastral_numbers"])

    log.info("── Summary ─────────────────────────────────────────────────────────────")
    log.info("  PDFs processed:    %d", len(sources))
    log.info("  Records extracted: %d (%d errors)", len(records), errors)
    log.info("  With cadastrals:   %d / %d", with_cadastrals, len(records))
    log.info("  Total cadastrals:  %d", total_cadastrals)
    log.info("  Clean (no flags):  %d", clean)
    log.info("  Output:            %s", out_path)

    # ── Троянда-М specific check ─────────────────────────────────────────────
    rks_records = [r for r in records if r.get("eisghs_id") == 54271]
    if rks_records:
        r = rks_records[0]
        log.info("── RPD PDF confirmation for Дом с часами (id=54271) ────────────────────")
        log.info("  RPD №%s", r.get("rpd_num_in_pdf"))
        log.info("  Project name: %r", r.get("project_name_in_pdf"))
        log.info("  Developer INN in PDF: %s", r.get("developer_inn_in_pdf"))
        log.info("  Cadastrals in PDF: %s", r.get("cadastral_numbers"))
        log.info("  Area: %s m²", r.get("area_sqm"))
        log.info("  Expected cadastrals (from land order №291): "
                 "['93:37:0010106:91', '93:37:0010106:92', '93:37:0010107:91']")
        pdf_cads = set(r.get("cadastral_numbers") or [])
        lo_cads  = {"93:37:0010106:91", "93:37:0010106:92", "93:37:0010107:91"}
        overlap  = pdf_cads & lo_cads
        log.info("  Overlap with land order: %s", sorted(overlap))
        if overlap:
            log.info("  ✓ CONFIRMED: RPD PDF independently confirms cadastral(s) in land order №291")
            log.info("    → legal_grade=True requires re-running scripts/18_parse_eisghs_mariupol.py")
        else:
            log.info("  ✗ No cadastral overlap with land order — check PDF extraction")

    log.info("Next step: re-run scripts/18_parse_eisghs_mariupol.py to update legal grades.")


if __name__ == "__main__":
    main()
