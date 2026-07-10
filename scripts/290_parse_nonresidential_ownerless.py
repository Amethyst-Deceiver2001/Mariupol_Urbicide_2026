#!/usr/bin/env python3
"""Stage 2: parse the MinStroy DNR commercial/industrial "ownerless-signs" lists.

WHY THIS EXISTS
---------------
The 12,948-row residential ownerless registry is only half the picture. In
June 2023 the Mariupol city administration's trade-and-services department ran
a parallel inspection of *non-residential* real estate and flagged objects
"имеющие признаки бесхозности" (bearing signs of ownerlessness) — the exact same
euphemism that opens the residential seizure pipeline, applied to shops, cafes,
salons, warehouses, and whole industrial parcels. This is a structurally
distinct designation track, run by MinStroy rather than the standard municipal
ownerless-registry process, and it has never been loaded onto the spine.

Three captured primary sources (from @minstroydnr, June 2023):

  1. @minstroydnr/3063 — Мариуполь_НЕ_ФУНКЦИОНИРУЮЩИЕ_ОБЪЕКТЫ_.xlsx
     1,234 commercial premises. Columns: №, Район, Адрес, Собственник(blank),
     Контактные данные(blank), Объект(type), Площадь(blank), Дополнительно,
     Расположение (объект в жилом доме | стационарный объект).

  2. @minstroydnr/3227 — Перечень промышленных площадок и коммерческих
     объектов ... .docx (two tables: 5 industrial parcels w/ cadastral + area,
     10 commercial objects). Dated supplement.

  3. @minstroydnr/3235 — 30_06_2023 Перечень ... .docx (6 industrial parcels
     w/ cadastral + area, 22 commercial objects). Dated supplement.

Together: 1,277 non-residential objects, of which 11 industrial parcels carry a
cadastral number and parcel area — claim-grade without further matching.

OUTPUT
------
  data/parsed/nonresidential_ownerless.jsonl — one record per object:
    source_sha256, source_url, source_msg_date,
    seq_no, district, address_raw, address_street, address_building,
    object_type, premises_class ('commercial'|'industrial'),
    location_class ('embedded_in_residential'|'standalone'|None),
    cadastral_no, parcel_area_ha, building_id

Re-running is safe — output is overwritten. No network access; reads only the
immutable raw store keyed by the URLs above.
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mariupol_seizures import config  # noqa: E402
from mariupol_seizures.normalize.address import (  # noqa: E402
    address_to_building_key,
    norm_commas,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("parse_nonres_ownerless")

OUT = config.PROJECT_ROOT / "data" / "parsed" / "nonresidential_ownerless.jsonl"

# The three captured primary sources, by URL in the forensics store.
XLSX_URL = "https://t.me/minstroydnr/3063"
DOCX_URLS = ["https://t.me/minstroydnr/3227", "https://t.me/minstroydnr/3235"]


def _lookup(con: sqlite3.Connection, url: str) -> tuple[str, str, str] | None:
    """Return (sha256, raw_path, captured_at) for a captured document URL."""
    row = con.execute(
        "SELECT sha256, raw_path, captured_at FROM source_document "
        "WHERE url = ? ORDER BY captured_at DESC LIMIT 1",
        (url,),
    ).fetchone()
    return row  # None if not captured


def _split_addr(addr_raw: str) -> tuple[str | None, str | None]:
    """Split a 'ул. X, 12А' address into (street, house) on the FIRST comma —
    matching the project's standing address-normalization rule."""
    if not addr_raw:
        return None, None
    addr = norm_commas(addr_raw)
    parts = [p.strip() for p in addr.split(",")]
    street = parts[0] or None if parts else None
    house = parts[1] if len(parts) > 1 else None
    return street, house


def _emit(rec: dict, records: list[dict]) -> None:
    """Compute building_id and append."""
    rec["building_id"] = address_to_building_key(
        rec.get("address_street"), rec.get("address_building")
    )
    records.append(rec)


def parse_xlsx(sha: str, url: str, captured_at: str, records: list[dict]) -> int:
    import openpyxl

    path = config.RAW_DIR / f"{sha}.xlsx"
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    # rows[0] merged title, rows[1] header, data from rows[2:]
    n0 = len(records)
    for r in rows[2:]:
        if r is None:
            continue
        seq = r[0]
        district = (r[1] or "").strip() or None
        address = (r[2] or "").strip() if r[2] else None
        object_type = (r[5] or "").strip() if r[5] else None
        location = (r[8] or "").strip() if len(r) > 8 and r[8] else None
        if not address:
            continue
        if location and "жил" in location.lower():
            loc_class = "embedded_in_residential"
        elif location:
            loc_class = "standalone"
        else:
            loc_class = None
        street, house = _split_addr(address)
        _emit(
            {
                "source_sha256": sha,
                "source_url": url,
                "source_msg_date": captured_at,
                "seq_no": seq,
                "district": district,
                "address_raw": address,
                "address_street": street,
                "address_building": house,
                "object_type": object_type,
                "premises_class": "commercial",
                "location_class": loc_class,
                "cadastral_no": None,
                "parcel_area_ha": None,
                "list_kind": "minstroy_nonfunctioning_objects",
            },
            records,
        )
    return len(records) - n0


_AREA_RE = re.compile(r"([\d.,]+)\s*га", re.I)


def _parse_area_ha(raw: str | None) -> float | None:
    if not raw:
        return None
    m = _AREA_RE.search(raw)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except ValueError:
        return None


def parse_docx(sha: str, url: str, captured_at: str, records: list[dict]) -> int:
    import docx

    path = config.RAW_DIR / f"{sha}.docx"
    d = docx.Document(path)
    n0 = len(records)
    for t in d.tables:
        # Header row (row index 1) tells us which table this is.
        header = [c.text.strip().lower() for c in t.rows[1].cells] if len(t.rows) > 1 else []
        is_industrial = any("кадастр" in h for h in header)
        for row in t.rows[2:]:
            cells = [c.text.strip().replace("\n", " ") for c in row.cells]
            if not cells or not any(cells):
                continue
            seq = cells[0] or None
            address = cells[1] if len(cells) > 1 else None
            if not address:
                continue
            street, house = _split_addr(address)
            if is_industrial:
                # cols: №, Адрес, Описание, Кадастровый номер, Площадь участка
                object_type = cells[2] if len(cells) > 2 else None
                cadastral = cells[3] if len(cells) > 3 else None
                area = _parse_area_ha(cells[4] if len(cells) > 4 else None)
                premises = "industrial"
            else:
                # cols: №, Адрес, Наименование
                object_type = cells[2] if len(cells) > 2 else None
                cadastral = None
                area = None
                premises = "commercial"
            _emit(
                {
                    "source_sha256": sha,
                    "source_url": url,
                    "source_msg_date": captured_at,
                    "seq_no": seq,
                    "district": None,
                    "address_raw": address,
                    "address_street": street,
                    "address_building": house,
                    "object_type": object_type or None,
                    "premises_class": premises,
                    "location_class": "standalone" if is_industrial else None,
                    "cadastral_no": cadastral or None,
                    "parcel_area_ha": area,
                    "list_kind": "minstroy_industrial_commercial_supplement",
                },
                records,
            )
    return len(records) - n0


def main() -> None:
    con = sqlite3.connect(config.STATE_DB)
    records: list[dict] = []

    x = _lookup(con, XLSX_URL)
    if x is None:
        log.error("xlsx source %s not captured — nothing to parse", XLSX_URL)
        sys.exit(1)
    sha, _raw_path, captured_at = x
    n = parse_xlsx(sha, XLSX_URL, captured_at, records)
    log.info("parsed %d commercial objects from %s", n, XLSX_URL)

    for url in DOCX_URLS:
        d = _lookup(con, url)
        if d is None:
            log.warning("docx source %s not captured — skipping", url)
            continue
        sha, _raw_path, captured_at = d
        n = parse_docx(sha, url, captured_at, records)
        log.info("parsed %d objects from %s", n, url)

    con.close()

    # Stats
    total = len(records)
    industrial = sum(1 for r in records if r["premises_class"] == "industrial")
    with_cad = sum(1 for r in records if r["cadastral_no"])
    with_bid = sum(1 for r in records if r["building_id"])
    embedded = sum(1 for r in records if r["location_class"] == "embedded_in_residential")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    log.info("wrote %s", OUT)
    log.info(
        "  %d objects total | %d industrial (%d with cadastral) | "
        "%d embedded-in-residential | %d resolved to a building_id",
        total, industrial, with_cad, embedded, with_bid,
    )
    print(
        f"nonresidential_ownerless: {total} objects "
        f"({industrial} industrial, {with_cad} with cadastral, "
        f"{total - with_bid} unparseable address)"
    )


if __name__ == "__main__":
    main()
