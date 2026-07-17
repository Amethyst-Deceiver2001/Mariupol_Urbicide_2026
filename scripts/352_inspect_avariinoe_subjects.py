#!/usr/bin/env python3
"""One-off: OCR page 1 of each captured 'аварийное' document (scripts/351)
and print its subject line, so a classification scheme can be designed from
real content — mirrors how scripts/346's registration/designation/removal
split was established. Local-only, no network.

Run:
    PYTHONPATH=src .venv312/bin/python scripts/352_inspect_avariinoe_subjects.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

OCRMYPDF = str(ROOT / ".venv" / "bin" / "ocrmypdf")


def _subject(sha: str, raw_path: str, out_dir: str) -> tuple[str, str]:
    out_pdf = str(Path(out_dir) / f"{sha[:10]}_p1.pdf")
    subprocess.run(
        [OCRMYPDF, "--language", "rus", "--skip-text", "--quiet", "--pages", "1",
         raw_path, out_pdf],
        cwd=str(ROOT), capture_output=True, timeout=120,
    )
    r = subprocess.run(["pdftotext", "-f", "1", "-l", "1", out_pdf, "-"],
                       capture_output=True, text=True, timeout=30)
    lines = [l.strip() for l in r.stdout.splitlines()]
    try:
        start = next(i for i, l in enumerate(lines) if l.startswith("от") or l.startswith("ОТ"))
    except StopIteration:
        return sha, "<no от-line found>"
    subj = []
    for l in lines[start + 1:]:
        if not l:
            continue
        if re.match(r"^(С\s+целью|В\s+целях|В\s+соответствии|Руководствуясь)", l):
            break
        subj.append(l)
        if len(subj) >= 4:
            break
    return sha, " ".join(subj)[:160]


def main() -> None:
    con = forensics.open_state()
    rows = con.execute(
        "SELECT sha256, raw_path FROM source_document WHERE source_type='mariupol_gosuslugi_avariinoe_pdf'"
    ).fetchall()
    print(f"{len(rows)} docs to inspect\n")

    out_dir = config.DATA_DIR / "reports" / "avariinoe_inspect"
    out_dir.mkdir(parents=True, exist_ok=True)

    with ProcessPoolExecutor() as ex:
        futs = {ex.submit(_subject, sha, path, str(out_dir)): sha for sha, path in rows}
        for fut in as_completed(futs):
            sha, subj = fut.result()
            print(f"{sha[:12]} | {subj}")


if __name__ == "__main__":
    main()
