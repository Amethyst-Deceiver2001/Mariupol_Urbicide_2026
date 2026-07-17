#!/usr/bin/env python3
"""Local-only sweep of the 89 generic-catch-all decree PDFs scripts/346
captured (source_type='mariupol_gosuslugi_postanovlenie_pdf', no landing-page
title resolved) to find any that are actually bezkhoz-related and were
missed at classification time. No network — everything is already in the
raw store; this just OCRs page 1 of each and checks for the бесхозяйн root
and its 3 known decree-kind shapes (registration/designation/removal).

Parallelized across CPU cores (unlike the sequential version run earlier)
so it finishes in a couple minutes instead of ~15.

Run:
    PYTHONPATH=src .venv312/bin/python scripts/349_sweep_stub_decrees_for_bezkhoz.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

OCRMYPDF = str(ROOT / ".venv" / "bin" / "ocrmypdf")
BEZKHOZ_RX = re.compile(r"бесхоз(?:яй)?н\w*", re.I)
REMOVAL_RX = re.compile(r"сня[тл]\w*\s+с\s+учет|исключ\w*.{0,150}из\s+Реестр", re.I)
REGISTRATION_RX = re.compile(r"постановке\s+на\s+учет", re.I)
DESIGNATION_RX = re.compile(r"признани\w*.{0,60}бесхоз|включени\w*.{0,60}Реестр", re.I)


def _check_one(sha: str, raw_path: str, out_dir: str) -> dict:
    out_pdf = str(Path(out_dir) / f"{sha[:10]}_p1ocr.pdf")
    subprocess.run(
        [OCRMYPDF, "--language", "rus", "--skip-text", "--quiet", "--pages", "1",
         raw_path, out_pdf],
        cwd=str(ROOT), capture_output=True, timeout=120,
    )
    r = subprocess.run(["pdftotext", "-f", "1", "-l", "1", out_pdf, "-"],
                       capture_output=True, text=True, timeout=30)
    text = r.stdout
    has_bezkhoz = bool(BEZKHOZ_RX.search(text))
    kind = None
    if has_bezkhoz:
        if REMOVAL_RX.search(text):
            kind = "removal"
        elif REGISTRATION_RX.search(text):
            kind = "registration"
        elif DESIGNATION_RX.search(text):
            kind = "designation"
        else:
            kind = "bezkhoz_other"
    return {"sha": sha, "has_bezkhoz": has_bezkhoz, "kind": kind, "snippet": text[:300]}


def main() -> None:
    con = forensics.open_state()
    rows = con.execute(
        """SELECT sha256, raw_path FROM source_document
           WHERE source_type = 'mariupol_gosuslugi_postanovlenie_pdf'
             AND captured_at >= '2026-07-17'"""
    ).fetchall()
    print(f"{len(rows)} stub PDFs to check\n")

    out_dir = config.DATA_DIR / "reports" / "stub_decree_sweep"
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    with ProcessPoolExecutor() as ex:
        futs = {ex.submit(_check_one, sha, path, str(out_dir)): sha for sha, path in rows}
        for i, fut in enumerate(as_completed(futs), 1):
            try:
                r = fut.result()
            except Exception as e:  # noqa: BLE001
                print(f"[{i}/{len(rows)}] {futs[fut][:10]} ERROR: {e}")
                continue
            results.append(r)
            flag = f" *** {r['kind'].upper()}" if r["kind"] else ""
            print(f"[{i}/{len(rows)}] {r['sha'][:10]} bezkhoz={r['has_bezkhoz']}{flag}")

    hits = [r for r in results if r["has_bezkhoz"]]
    out_json = out_dir / "sweep_results.json"
    out_json.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\ndone — {len(hits)}/{len(results)} bezkhoz-related hits found")
    for r in hits:
        print(f"  {r['sha']} [{r['kind']}]")
    print(f"\nfull results: {out_json}")
    print("Next: reclassify the hits' source_type in the DB, then re-run "
          "06a_ocr_decrees.py -> 06_parse_ownerless_decrees.py -> 21/27.")


if __name__ == "__main__":
    main()
