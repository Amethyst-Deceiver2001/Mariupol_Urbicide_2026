#!/usr/bin/env python3
"""Lifecycle QA cross-check: validate decree-signing dates in
ownerless_decrees.jsonl / demolition_decrees.jsonl against the now-known
tenure windows of each head of the Mariupol occupation administration
(Иващенко / Моргун / Кольцов — docs/stakeholder_network.md, "Command-chain
chronology", script 44, OCR'd 2026-06-12). progress_report_2026-06.md §5
item 3 — "never run" until now.

A decree dated outside its named signer's tenure window is either a parse
error (decree_date misread by OCR/regex) or a signer-attribution error
(wrong name extracted) — either way, evidence of a pipeline bug worth a
manual look, not evidence about the occupation itself.

Local-only, no network. Run:
  PYTHONPATH=src .venv312/bin/python scripts/193_lifecycle_tenure_qa.py
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Tenure windows per docs/stakeholder_network.md "Tenure summary".
# Released-same-day-as-appointed gaps (22.01.2023, 06.11.2023, 12-13.06.2025)
# are real per the chronology, not parse slop — kept exact, no padding.
TENURES = {
    "иващенко": (date(2022, 4, 6), date(2023, 1, 22)),
    "моргун": (date(2023, 1, 23), date(2025, 6, 12)),
    "кольцов": (date(2025, 6, 13), date(2026, 12, 31)),  # current as of capture; open-ended upper bound
}

FILES = {
    "ownerless_decrees.jsonl": ROOT / "data/parsed/ownerless_decrees.jsonl",
    "demolition_decrees.jsonl": ROOT / "data/parsed/demolition_decrees.jsonl",
}


def match_signer(name: str | None) -> str | None:
    if not name:
        return None
    low = name.lower()
    for key in TENURES:
        if key in low:
            return key
    return None


def main() -> None:
    total = 0
    out_of_window = []
    unmatched_signers: dict[str, int] = {}
    no_date = 0

    for fname, path in FILES.items():
        if not path.exists():
            print(f"SKIP {fname}: not found")
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            total += 1
            signer = rec.get("signing_official")
            dstr = rec.get("decree_date")
            if not dstr:
                no_date += 1
                continue
            try:
                d = date.fromisoformat(dstr)
            except ValueError:
                no_date += 1
                continue
            key = match_signer(signer)
            if key is None:
                unmatched_signers[signer or "(none)"] = unmatched_signers.get(signer or "(none)", 0) + 1
                continue
            start, end = TENURES[key]
            if not (start <= d <= end):
                out_of_window.append({
                    "file": fname,
                    "decree_number": rec.get("decree_number"),
                    "decree_date": dstr,
                    "signing_official": signer,
                    "tenure_window": f"{start.isoformat()}..{end.isoformat()}",
                    "source_sha256": rec.get("source_sha256"),
                    "address_raw": rec.get("address_raw"),
                })

    print(f"Rows checked: {total}")
    print(f"Rows with no parseable decree_date: {no_date}")
    print(f"Rows with unmatched signer name: {sum(unmatched_signers.values())}")
    for name, n in sorted(unmatched_signers.items(), key=lambda kv: -kv[1]):
        print(f"  {n:>5}  {name!r}")
    print(f"\nOut-of-tenure-window rows: {len(out_of_window)}")
    for r in out_of_window:
        print(f"  {r['file']:<24} decree #{r['decree_number']!s:<6} {r['decree_date']} "
              f"signer={r['signing_official']!r} tenure={r['tenure_window']} "
              f"addr={r['address_raw']!r}")

    if out_of_window:
        out_path = ROOT / "data/reports/lifecycle_tenure_qa_violations.jsonl"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as fh:
            for r in out_of_window:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"\nWrote {len(out_of_window)} violations to {out_path}")


if __name__ == "__main__":
    main()
