#!/usr/bin/env python3
"""Reclassify the 9 bezkhoz hits scripts/349 found inside the 89-doc generic
catch-all bucket (source_type='mariupol_gosuslugi_postanovlenie_pdf') into
the correct ownerless_decree_* source_type so 06a_ocr_decrees.py picks them
up for full-document OCR and 06_parse_ownerless_decrees.py can parse them.

'bezkhoz_other' hits (has бесхозя root but didn't match any of the 3 known
kind regexes) are reclassified as 'ownerless_decree_procedure_pdf' -- the
existing catch-all for bezkhoz decrees that aren't a clean designation/
registration/removal shape; 06_parse's dispatcher will attempt its usual
strategies against them and simply yield 0 rows if the text genuinely
doesn't fit (same behavior as any other procedure-kind doc).

Local-only, no network. Idempotent (re-run finds already-reclassified rows
have a source_type outside the WHERE clause and no-ops on them).

Run:
    PYTHONPATH=src .venv312/bin/python scripts/359_reclassify_stub_sweep_hits.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import forensics  # noqa: E402

KIND_TO_SOURCE_TYPE = {
    "removal": "ownerless_decree_removal_pdf",
    "registration": "ownerless_decree_registration_pdf",
    "designation": "ownerless_decree_designation_pdf",
    "bezkhoz_other": "ownerless_decree_procedure_pdf",
}


def main() -> None:
    results_path = ROOT / "data" / "reports" / "stub_decree_sweep" / "sweep_results.json"
    results = json.loads(results_path.read_text(encoding="utf-8"))
    hits = [r for r in results if r["has_bezkhoz"]]
    print(f"{len(hits)} hits to reclassify")

    con = forensics.open_state()
    n = 0
    for r in hits:
        sha, kind = r["sha"], r["kind"]
        new_type = KIND_TO_SOURCE_TYPE[kind]
        cur = con.execute(
            """UPDATE source_document SET source_type = ?
               WHERE sha256 = ? AND source_type = 'mariupol_gosuslugi_postanovlenie_pdf'""",
            (new_type, sha),
        )
        if cur.rowcount:
            n += 1
            print(f"  {sha[:10]} -> {new_type}")
        else:
            print(f"  {sha[:10]} SKIP (already reclassified or not found)")
    con.commit()
    con.close()
    print(f"\ndone — {n} rows reclassified")
    print("Next: PYTHONPATH=src .venv312/bin/python scripts/06a_ocr_decrees.py")
    print("      PYTHONPATH=src .venv/bin/python scripts/06_parse_ownerless_decrees.py")
    print("      PYTHONPATH=src .venv/bin/python scripts/21_build_address_registry.py")
    print("      PYTHONPATH=src .venv/bin/python scripts/27_load_registry.py")


if __name__ == "__main__":
    main()
