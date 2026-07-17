#!/usr/bin/env python3
"""Parse OCR'd "аварийное" (emergency/dilapidated building status) decrees
(scripts/351) into data/parsed/avariinoe_decrees.jsonl.

Document family and structure, established by reading real full-text OCR
dumps 2026-07-17 (data/reports/avariinoe_inspect/):

  - DESIGNATION ("О признании ... аварийным(и) и подлежащим(и) сносу/
    реконструкции", source_type='avariinoe_designation_pdf'): the core
    per-building act. TWO forms:
      (a) multi-building list: "1. Признать аварийными и подлежащими сносу
          многоквартирные дома, расположенные по адресу: {addr};\n{addr};
          ...\n2. Признать непригодными..." — a flat list, one address per
          entry, terminated by the next numbered clause.
      (b) single-building prose: "1. Признать многоквартирный дом,
          расположенный по адресу: {addr} аварийным и подлежащим
          {сносу|реконструкции} на основании..." — one address embedded in
          a sentence.
    Outcome ("сносу"=demolition / "реконструкции"=reconstruction) is a
    legally meaningful distinction (see db/schema.sql's seizure_stage enum
    comment) captured in each row's 'outcome' field.
  - AMENDMENT/PROCEDURE (source_type='avariinoe_amendment_pdf'/
    'avariinoe_procedure_pdf'): administrative machinery (commission
    composition, publication-clause wording, program amendments) — no
    per-building data to extract. Metadata-only rows (decree_number/date/
    kind), mirroring ownerless_decree_procedure_pdf's handling in
    scripts/06_parse_ownerless_decrees.py.
  - RESETTLEMENT PROGRAM ("Переселение граждан из аварийного жилищного
    фонда", source_type='avariinoe_resettlement_program_pdf'): a rich
    ПАСПОРТ (passport/summary) section with funding/resident/building counts
    is reliably extractable. The actual per-building schedule (Приложение 2)
    is a LANDSCAPE-ORIENTED page that page-upright OCR garbles completely
    (readable Cyrillic words spelled backward — confirmed 2026-07-17,
    data/reports/avariinoe_inspect/c355d24803_full.txt lines ~1000+) — NOT
    parsed here. This is a deliberate, flagged gap (parsed_program_annex=
    False on every row of this kind), not a silent drop; closing it needs a
    rotation-aware OCR pass (e.g. try both 90-degree rotations, keep
    whichever yields recognizable Cyrillic) before a table parser can be
    written.

Decree number/date: same rule as scripts/06_parse_ownerless_decrees.py —
the PDF's own "от ... №..." header line is HANDWRITTEN and OCR-garbled
(confirmed on every sample read 2026-07-17), so decree_number/date come from
the HTML title captured at crawl time (scripts/06_parse_ownerless_decrees.py's
_parse_title_meta, reused here via import), never from OCR text.

Run:
    PYTHONPATH=src python scripts/354_parse_avariinoe_decrees.py
"""
from __future__ import annotations

import importlib.util
import json
import logging
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

try:
    import pdfplumber
except ImportError:
    sys.exit("pdfplumber not installed — run: pip install pdfplumber")

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

_spec = importlib.util.spec_from_file_location(
    "m06", str(ROOT / "scripts" / "06_parse_ownerless_decrees.py"))
m06 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m06)  # noqa: E402
_parse_title_meta = m06._parse_title_meta
_extract_decree_meta = m06._extract_decree_meta

SOURCE_TYPES = {
    "avariinoe_designation_pdf": "designation",
    "avariinoe_amendment_pdf": "amendment",
    "avariinoe_procedure_pdf": "procedure",
    "avariinoe_resettlement_program_pdf": "resettlement_program",
}

# multi-building list entries: "{street type} {street name}, дом № {N}[ лит. {L}]"
_ADDR_LIST_ITEM = re.compile(
    r"(город\s+Мариуполь,\s*(?:улица|переулок|проспект|бульвар)\s+"
    r"[А-ЯЁа-яё\-\s]+?,\s*дом\s*№?\s*\d+(?:\s*лит\.?\s*[А-ЯЁ])?)",
    re.I,
)
_LIST_START = re.compile(r"Признать\s+аварийн\w*\s+и\s+подлежащ\w*\s+сносу.{0,80}по\s+адресу", re.I | re.S)
_LIST_END = re.compile(r"^\s*2\.\s+Признать", re.M)

# single-building prose form: "...расположенный по адресу: {addr} аварийным
# и подлежащим {outcome}"
_SINGLE_ADDR = re.compile(
    r"расположенн\w+\s+по\s+адресу:\s*(.+?)\s+аварийн\w*\s+и\s+подлежащ\w*\s+"
    r"(сносу|реконструкции)",
    re.I | re.S,
)
_OUTCOME_WORD = {"сносу": "demolition", "реконструкции": "reconstruction"}

# resettlement-program ПАСПОРТ summary fields
_RESULT_BLOCK = re.compile(
    r"Обеспечение\s+благоустроенным\s+жильем\s+(\d+)\s+граждан\s+из\s+(\d+)\s+"
    r"многоквартирных\s+домов.{0,80}?площадью\s+расселяемых\s+жилых\s+помещений\s+"
    r"([\d,\.]+)\s*кв\.?\s*м",
    re.I | re.S,
)
_FUNDING = re.compile(
    r"Всего\s+по\s+программе\s+на\s+\d{4}\s+год.{0,20}этап\)\s+([\d\s]+,\d+)\s*рубл",
    re.I,
)


def _rows_from_designation(text: str, source_sha256: str) -> list[dict]:
    rows: list[dict] = []
    m_start = _LIST_START.search(text)
    if m_start:
        m_end = _LIST_END.search(text, m_start.end())
        segment = text[m_start.end():m_end.start() if m_end else None]
        outcome = "demolition"  # _LIST_START only matches the "сносу" form
        for i, m in enumerate(_ADDR_LIST_ITEM.finditer(segment), 1):
            addr = re.sub(r"\s+", " ", m.group(1)).strip()
            rows.append({
                "source_sha256": source_sha256, "seq_no": i,
                "address_raw": addr, "outcome": outcome,
                "form": "list",
            })
        if rows:
            return rows
    m_single = _SINGLE_ADDR.search(text)
    if m_single:
        addr = re.sub(r"\s+", " ", m_single.group(1)).strip().rstrip(",")
        outcome = _OUTCOME_WORD.get(m_single.group(2).lower(), "unknown")
        rows.append({
            "source_sha256": source_sha256, "seq_no": 1,
            "address_raw": addr, "outcome": outcome,
            "form": "single",
        })
    return rows


def _resettlement_program_summary(text: str, source_sha256: str) -> list[dict]:
    row = {
        "source_sha256": source_sha256, "seq_no": 1,
        "parsed_program_annex": False,
        "note": ("Приложение 2 (per-building resettlement schedule) is a "
                "landscape-oriented page OCR garbles when read upright — "
                "NOT parsed. See module docstring."),
    }
    m = _RESULT_BLOCK.search(text)
    if m:
        row["residents_count"] = int(m.group(1))
        row["buildings_count"] = int(m.group(2))
        row["resettled_area_sqm"] = float(m.group(3).replace(",", "."))
    mf = _FUNDING.search(text)
    if mf:
        row["stage1_funding_rub"] = float(mf.group(1).replace(" ", "").replace(",", "."))
    return [row]


def parse_pdf(pdf_path: Path, source_sha256: str, title: str, kind: str) -> list[dict]:
    with pdfplumber.open(pdf_path) as pdf:
        full_text = "\n".join(p.extract_text() or "" for p in pdf.pages)

    if not full_text.strip():
        log.warning("%s: no text after OCR — OCR likely failed; re-run 06a", pdf_path.name)
        return []

    if kind == "designation":
        rows = _rows_from_designation(full_text, source_sha256)
    elif kind == "resettlement_program":
        rows = _resettlement_program_summary(full_text, source_sha256)
    else:  # amendment / procedure — metadata-only, no per-building data
        rows = [{"source_sha256": source_sha256, "seq_no": 1}]

    decree_meta = _parse_title_meta(title) if title else {}
    decree_meta.update(_extract_decree_meta(full_text))
    decree_meta["decree_kind"] = kind
    for row in rows:
        row.update(decree_meta)
    return rows


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    con = forensics.open_state()
    # Match on the PARENT's current source_type, not the derivative's own
    # source_type: a scan OCR'd before this session's avariinoe reclassification
    # (e.g. originally scooped up by the demolition-decree crawl) carries a
    # stale derivative source_type (e.g. 'demolition_decree_mkd_ocr_pdf') even
    # though its parent is now correctly tagged 'avariinoe_designation_pdf'.
    ocr_sources = con.execute(
        """SELECT ocr.sha256, ocr.raw_path, ocr.title, parent.source_type
           FROM source_document ocr
           JOIN source_document parent ON parent.sha256 = ocr.derived_from
           WHERE parent.source_type LIKE 'avariinoe_%_pdf'
             AND ocr.derived_from IS NOT NULL"""
    ).fetchall()

    out_dir = config.PROJECT_ROOT / "data" / "parsed"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "avariinoe_decrees.jsonl"

    total = 0
    with out_path.open("w", encoding="utf-8") as fh:
        for sha, raw_path, title, source_type in ocr_sources:
            p = Path(raw_path)
            if not p.exists():
                log.error("file missing: %s", raw_path)
                continue
            orig_type = source_type.replace("_ocr_pdf", "_pdf")
            kind = SOURCE_TYPES.get(orig_type)
            if kind is None:
                log.error("unrecognized derived source_type: %s", source_type)
                continue
            try:
                rows = parse_pdf(p, sha, title or "", kind)
            except Exception:
                log.exception("failed to parse %s", raw_path)
                continue
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            total += len(rows)
            log.info("%s: %d rows via kind=%s — decree №%s, %s",
                     p.name, len(rows), kind,
                     rows[0].get("decree_number", "?") if rows else "?",
                     rows[0].get("decree_date", "?") if rows else "?")

    log.info("done — %d rows written to %s", total, out_path)
    log.info("Next: build a DB loader (load_avariinoe_designation) for "
             "kind='designation' rows -> seizure_event(stage="
             "'avariinoe_designation'). resettlement_program/amendment/"
             "procedure rows are metadata-only, not yet loaded to the spine.")


if __name__ == "__main__":
    main()
