#!/usr/bin/env python3
"""OCR the FULL body (all pages) of each of the 10 captured 'аварийное'
documents (scripts/351), dumping text to data/reports/avariinoe_inspect/ for
inspection — page 1 alone (scripts/352) wasn't enough to see whether
designation decrees carry a per-building address table/list, or how the
resettlement-program decrees are structured. Needed to design a real parser.

Local-only, no network. Parallelized across CPU cores.

Run:
    PYTHONPATH=src .venv312/bin/python scripts/353_full_ocr_avariinoe_sample.py
"""
from __future__ import annotations

import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

OCRMYPDF = str(ROOT / ".venv" / "bin" / "ocrmypdf")


def _ocr_full(sha: str, raw_path: str, out_dir: str) -> tuple[str, int, str]:
    out_pdf = str(Path(out_dir) / f"{sha[:10]}_full.pdf")
    subprocess.run(
        [OCRMYPDF, "--language", "rus", "--skip-text", "--quiet", raw_path, out_pdf],
        cwd=str(ROOT), capture_output=True, timeout=600,
    )
    info = subprocess.run(["pdfinfo", out_pdf], capture_output=True, text=True)
    pages = 0
    for line in info.stdout.splitlines():
        if line.startswith("Pages:"):
            pages = int(line.split(":")[1].strip())
    r = subprocess.run(["pdftotext", "-layout", out_pdf, "-"], capture_output=True, text=True, timeout=60)
    txt_path = Path(out_dir) / f"{sha[:10]}_full.txt"
    txt_path.write_text(r.stdout, encoding="utf-8")
    return sha, pages, str(txt_path)


def main() -> None:
    con = forensics.open_state()
    rows = con.execute(
        "SELECT sha256, raw_path FROM source_document WHERE source_type='mariupol_gosuslugi_avariinoe_pdf'"
    ).fetchall()
    print(f"{len(rows)} docs to OCR (full)\n")

    out_dir = config.DATA_DIR / "reports" / "avariinoe_inspect"
    out_dir.mkdir(parents=True, exist_ok=True)

    with ProcessPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(_ocr_full, sha, path, str(out_dir)): sha for sha, path in rows}
        for fut in as_completed(futs):
            sha, pages, txt_path = fut.result()
            print(f"{sha[:12]} {pages}p -> {txt_path}")

    print(f"\ndone — full text dumped to {out_dir}/")


if __name__ == "__main__":
    main()
