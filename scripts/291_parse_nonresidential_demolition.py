#!/usr/bin/env python3
"""Stage 2: parse the citywide NON-RESIDENTIAL demolition list («Снос.pdf»).

WHY THIS EXISTS
---------------
The MinStroy 525-building demolition register already loaded is overwhelmingly
multi-apartment residential buildings. A separate, citywide list of
*non-residential* objects slated for demolition — shops, shopping centres, a
bakery, hotels, warehouses, a telecoms building, an entertainment complex, a
DOSAAF building — was posted by the occupation-news channel @nmrpl as
«Снос.pdf» (ПЕРЕЧЕНЬ объектов, подлежащих сносу на территории города
Мариуполя). 42 numbered items. It is largely non-overlapping with the loaded
residential demolition register and has never been loaded onto the spine.

Source: @nmrpl/11325 — «Снос.pdf» (text PDF, no OCR needed).

Each item follows the shape:
  N. {object_type}, расположенн{ый/ое/ая} по адресу: город Мариуполь,
     {district} район, {street}, {house}

OUTPUT
------
  data/parsed/nonresidential_demolition.jsonl — one record per object:
    source_sha256, source_url,
    seq_no, object_type, district, address_raw, address_street,
    address_building, building_id

Re-running is safe — output is overwritten. Reads only the immutable raw store.
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mariupol_seizures import config  # noqa: E402
from mariupol_seizures.normalize.address import (  # noqa: E402
    address_to_building_key,
    norm_commas,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("parse_nonres_demolition")

OUT = config.PROJECT_ROOT / "data" / "parsed" / "nonresidential_demolition.jsonl"
SRC_URL = "https://t.me/nmrpl/11325"

# "{type}, расположен{...} по адресу: город Мариуполь, {district} район, {rest}"
_ITEM_RE = re.compile(
    r"^(?P<type>.+?),\s*располож[а-яё]+\s+по адресу:\s*"
    r"город\s+Мариуполь,\s*(?P<district>[А-Яа-яёЁ\-]+)\s+район,\s*(?P<rest>.+)$",
    re.I,
)


def _lookup(con: sqlite3.Connection, url: str) -> tuple[str, str] | None:
    row = con.execute(
        "SELECT sha256, raw_path FROM source_document "
        "WHERE url = ? AND (title LIKE '%Снос%' OR title LIKE '%.pdf%') "
        "ORDER BY captured_at DESC LIMIT 1",
        (url,),
    ).fetchone()
    if row is None:
        # fall back: any capture under that URL that is a pdf on disk
        for (sha,) in con.execute(
            "SELECT sha256 FROM source_document WHERE url = ?", (url,)
        ):
            if (config.RAW_DIR / f"{sha}.pdf").exists():
                return sha, str(config.RAW_DIR / f"{sha}.pdf")
    return row


def _pdf_text(pdf_path: Path) -> str:
    out = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"],
        capture_output=True, text=True, check=True,
    )
    return out.stdout.replace("\f", " ")


def _split_addr(rest: str) -> tuple[str, str | None, str | None]:
    """'ул. Краснофлотская, 194.' -> (raw, street, house)."""
    rest = rest.strip().rstrip(".").strip()
    addr = norm_commas(rest)
    parts = [p.strip() for p in addr.split(",")]
    street = parts[0] or None if parts else None
    house = parts[1] if len(parts) > 1 else None
    return rest, street, house


def main() -> None:
    con = sqlite3.connect(config.STATE_DB)
    found = _lookup(con, SRC_URL)
    con.close()
    if not found:
        log.error("source %s (Снос.pdf) not captured — nothing to parse", SRC_URL)
        sys.exit(1)
    sha = found[0]
    pdf_path = config.RAW_DIR / f"{sha}.pdf"

    text = _pdf_text(pdf_path)
    # Normalise whitespace, then split into numbered items 1..N.
    flat = " ".join(l.strip() for l in text.splitlines() if l.strip())
    chunks = re.split(r"(?<!\d)(\d{1,2})\.\s*", flat)
    # chunks[0] = preamble; then (num, body) pairs
    records: list[dict] = []
    for i in range(1, len(chunks), 2):
        seq = chunks[i]
        body = chunks[i + 1].strip() if i + 1 < len(chunks) else ""
        m = _ITEM_RE.match(body)
        if not m:
            log.warning("item %s did not match the address shape: %r", seq, body[:80])
            continue
        object_type = m.group("type").strip()
        district = m.group("district").strip()
        addr_raw, street, house = _split_addr(m.group("rest"))
        building_id = address_to_building_key(street, house)
        records.append(
            {
                "source_sha256": sha,
                "source_url": SRC_URL,
                "seq_no": int(seq),
                "object_type": object_type,
                "district": district,
                "address_raw": addr_raw,
                "address_street": street,
                "address_building": house,
                "building_id": building_id,
                "list_kind": "nonresidential_demolition_list",
            }
        )

    with_bid = sum(1 for r in records if r["building_id"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    log.info("wrote %s: %d objects (%d resolved to a building_id)",
             OUT, len(records), with_bid)
    print(f"nonresidential_demolition: {len(records)} objects "
          f"({len(records) - with_bid} unparseable address)")


if __name__ == "__main__":
    main()
