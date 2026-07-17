#!/usr/bin/env python3
"""Capture a single ownerless-decree PDF flagged by the user for a PaddleOCR
table-recognition test (page 4 specifically) — not yet in the raw store
under this URL/domain pattern (mariupol.gosuslugi.ru/netcat_files/396/4721/
1468.pdf, distinct from the mariupol-r897.gosweb.gosuslugi.ru/.../p.XXXX.pdf
pattern already captured for other decrees).

Geoblocked from outside Russia (confirmed 2026-07-17: connection refused,
http_code=000). Run from your Russia-routed VPS (config.PROXY).

Usage:
    .venv312/bin/python scripts/345_capture_single_decree_1468.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import requests  # noqa: E402

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

URL = "https://mariupol.gosuslugi.ru/netcat_files/396/4721/1468.pdf"


def main() -> None:
    proxies = {"https": config.PROXY, "http": config.PROXY} if config.PROXY else None
    headers = {"User-Agent": config.USER_AGENT}
    r = requests.get(URL, headers=headers, proxies=proxies, timeout=60)
    r.raise_for_status()
    con = forensics.open_state()
    sha = forensics.capture_source(
        r.content, url=URL,
        source_type="ownerless_decree_designation_pdf",
        title="Постановление Администрации №1468 [PDF] (flagged for PaddleOCR table test)",
        description=(f"Ownerless-designation decree PDF, captured for a PaddleOCR "
                     f"PP-StructureV3 table-recognition test (user-flagged, "
                     f"expected to contain a real address/apartment table on "
                     f"page 4). {URL}"),
        content_type=r.headers.get("Content-Type", "application/pdf"),
        http_status=r.status_code, con=con,
    )
    con.close()
    print(f"captured sha256={sha}")
    print(f"\nnext: PYTHONPATH=src .venv-ocr/bin/python "
         f"scripts/334_paddleocr_structured.py --sha {sha}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
