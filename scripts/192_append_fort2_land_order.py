#!/usr/bin/env python3
"""Append the ВЕРТИКАЛЬ ФОРТ-2 land grant (Распоряжение №203/09.06.2026,
просп. Победы 127) as a new row of data/parsed/dnr_land_orders.jsonl.

scripts/11_parse_dnr_land_orders.py only ever rebuilds dnr_land_orders.jsonl
from source_type='dnr_land_order' HTML captures (script 10's crawl target).
This decree was captured separately by the Denis Pushilin site crawler
(script 39, source_type='denis_pushilin_doc_ocr_pdf') and OCR'd + flagged by
script 45 into data/parsed/denis_pushilin_land_grants_202606.jsonl — it sits
permanently outside script 11's scope, so it has to be appended by hand
rather than picked up by a re-run. progress_report_2026-06.md §5 item 1.

Idempotent: skips if a row with this source_sha256 already exists.

Local-only, no network. Run:
  PYTHONPATH=src .venv312/bin/python scripts/192_append_fort2_land_order.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

LAND_GRANTS = ROOT / "data/parsed/denis_pushilin_land_grants_202606.jsonl"
OUT = ROOT / "data/parsed/dnr_land_orders.jsonl"

_DATE_SIGNED = re.compile(r"(\d{1,2})\s+(\S+)\s+(\d{4})\s+года")
_MONTHS = {
    "января": "01", "февраля": "02", "марта": "03", "апреля": "04",
    "мая": "05", "июня": "06", "июля": "07", "августа": "08",
    "сентября": "09", "октября": "10", "ноября": "11", "декабря": "12",
}
_DECREE_NO = re.compile(r"№\s*(\d+)\s*$")
_SIGNER = re.compile(r"Глава\s+Донецкой\s+Народной\s+Республики\s+([А-ЯЁ]\.\s*[А-ЯЁ]\.\s+[А-ЯЁ][а-яё]+)")
_BENEFICIARY = re.compile(r"«Специализированный застройщик «([^»]+)»»?")
_CADASTRAL = re.compile(r"93:\d+:\d+:\d+")
_AREA = re.compile(r"площадью\s+(\d+)\s*\+/-\s*\d+\s*м")
_ADDRESS = re.compile(r"расположенный по адресу:\s*(.+?),\s*находящийся в государственной", re.S)
_PROJECT = re.compile(r"инвестиционного\s+проекта\s*«([^»]+)»", re.S)
_LEGAL_BASIS = re.compile(
    r"(?:подпункт\w*\s+\d+\s+пункт\w*\s+\d+\s+стать\w+\s+[\d.]+\s+Земельного\s+кодекса"
    r"|Закон\w*\s+Донецкой[^.]+?№\s+[\w-]+)",
    re.I | re.S,
)


def parse_record(rec: dict) -> dict:
    text = rec["text"]
    flags: list[str] = []

    dm = _DATE_SIGNED.search(text)
    decree_date = f"{dm.group(3)}-{_MONTHS.get(dm.group(2).lower(), '00')}-{int(dm.group(1)):02d}" if dm else None

    nm = _DECREE_NO.search(text.strip())
    decree_number = nm.group(1) if nm else None

    sm = _SIGNER.search(text)
    signing_official = sm.group(1).strip() if sm else None

    bm = _BENEFICIARY.search(text)
    beneficiary = f"Специализированный застройщик «{bm.group(1)}»" if bm else None
    if not beneficiary:
        flags.append("beneficiary_missing")

    cadastrals = list(dict.fromkeys(_CADASTRAL.findall(text)))
    if not cadastrals:
        flags.append("cadastral_missing")

    am = _AREA.search(text)
    area_sqm = float(am.group(1)) if am else None
    if area_sqm is None:
        flags.append("area_missing")

    adm = _ADDRESS.search(text)
    address_raw = re.sub(r"\s+", " ", adm.group(1)).strip() if adm else None
    if not address_raw:
        flags.append("address_missing")

    pm = _PROJECT.search(text)
    project_name = re.sub(r"\s+", " ", pm.group(1)).strip() if pm else None

    legal_basis = list(dict.fromkeys(
        re.sub(r"\s+", " ", m.group(0)).strip() for m in _LEGAL_BASIS.finditer(text)
    ))

    return {
        "source_sha256": rec["source_sha256"],
        "decree_number": decree_number,
        "decree_date": decree_date,
        "issuing_body": "Глава ДНР",
        "signing_official": signing_official,
        "beneficiary_name": beneficiary,
        "beneficiary_ogrn": None,
        "beneficiary_inn": None,
        "beneficiary_inn_source": None,
        "cadastral_numbers": cadastrals,
        "area_sqm": area_sqm,
        "address_raw": address_raw,
        "address_normalized": address_raw,
        "project_name": project_name,
        "legal_basis": legal_basis,
        "flags": flags + ["inn_missing", "ogrn_missing"],
    }


def main() -> None:
    target = None
    for line in LAND_GRANTS.read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        if rec.get("filename") == "rasporiazhglavaN203_09062026.pdf":
            target = rec
            break
    if target is None:
        sys.exit("ERROR: rasporiazhglavaN203_09062026.pdf record not found in "
                  f"{LAND_GRANTS}")

    existing_shas = set()
    rows: list[str] = []
    if OUT.exists():
        rows = OUT.read_text(encoding="utf-8").splitlines()
        for line in rows:
            existing_shas.add(json.loads(line)["source_sha256"])

    if target["source_sha256"] in existing_shas:
        print(f"already present (source_sha256={target['source_sha256'][:12]}...) — no-op")
        return

    new_row = parse_record(target)
    print(json.dumps(new_row, ensure_ascii=False, indent=2))

    with OUT.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(new_row, ensure_ascii=False) + "\n")

    print(f"\nappended row {len(rows) + 1} to {OUT}")


if __name__ == "__main__":
    main()
