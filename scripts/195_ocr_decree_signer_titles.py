#!/usr/bin/env python3
"""OCR one representative ownerless-decree scan per signing official who
lacks a known position title, to recover that title from the decree's own
signature block. progress_report_2026-06.md §5 item 6.

Кольцов А.В. and Моргун О.В. already have known titles (heads of Mariupol
administration, docs/stakeholder_network.md "Command-chain chronology").
The other 4 signers of ownerless_decrees.jsonl have never had their
position title captured -- only the bare name:

  Перепечай Б.Н.    (70 decrees)
  Дмитриев А.В.     (55 decrees, also demolition-commission member)
  Краснолуцкая Т.Ю. (25 decrees)
  Матейко В.А.      (8 decrees)

One raw scan per signer (the same raw_scan_sha256 already on file in
ownerless_decrees.jsonl) is OCR'd; the signature-block text is printed for
manual reading -- no automated title-extraction regex, since position
titles in DNR municipal decrees aren't a fixed enum and a wrong guess
would misattribute authority.

FORENSIC RULE: OCR is lossy -- raw scans are never modified. Each OCR output
is written as a DERIVED artifact (forensics.capture_derived), source_type
'ownerless_decree_ocr_pdf', recording derived_from + transform. Idempotent.

Output: data/parsed/decree_signer_titles_202606.jsonl

Local-only, no network. Run (needs ocrmypdf, present in .venv not .venv312):
  PYTHONPATH=src .venv/bin/python3 scripts/195_ocr_decree_signer_titles.py
"""
from __future__ import annotations

import json
import logging
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import pdfplumber  # noqa: E402

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

PARSED_DIR = config.PROJECT_ROOT / "data" / "parsed"

OCR_ARGS = ["--language", "rus", "--skip-text", "--rotate-pages", "--deskew"]
TRANSFORM = f"ocrmypdf {' '.join(OCR_ARGS)}"
_OCR_EXECUTABLE = str(Path(sys.executable).parent / "ocrmypdf")

TARGETS: dict[str, str] = {
    "Б.Н. Перепечай": "94b8e1197b5e198ffe5324353a5e7dc3a6e67b9955bc5a91c603a61fd82f5dd2",
    "А.В. Дмитриев": "bc46949c69565c72eb9e4e571222d6bd957eca4e693e86e280aad3d05f12a203",
    "Т.Ю. Краснолуцкая": "a4c9a6ee33126eab88b49cfd293738a745162b49dbee537d33c5a95f1e43ed41",
    "В.А. Матейко": "db0d9c607ba025bbe9856c03b6f43ee2c53aff67432240ca71eb86d53310982d",
}


def _already_ocrd(con, parent_sha: str):
    return con.execute(
        "SELECT sha256, raw_path FROM source_document "
        "WHERE derived_from = ? AND transform = ? LIMIT 1",
        (parent_sha, TRANSFORM),
    ).fetchone()


def _run_ocr(src: Path) -> bytes | None:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "ocr.pdf"
        cmd = [_OCR_EXECUTABLE, *OCR_ARGS, str(src), str(out)]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if res.returncode != 0:
            log.error("ocrmypdf failed (exit %d) on %s:\n%s",
                      res.returncode, src.name, res.stderr.strip()[:500])
            return None
        return out.read_bytes()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")

    con = forensics.open_state()
    out_rows = []

    for signer, sha in TARGETS.items():
        row = con.execute(
            "SELECT raw_path FROM source_document WHERE sha256=?", (sha,)
        ).fetchone()
        if not row:
            log.error("%s: sha256 %s not in source_document", signer, sha)
            continue
        src_path = Path(row[0])

        existing = _already_ocrd(con, sha)
        if existing:
            ocr_sha, ocr_path = existing
            log.info("%s: already OCR'd -> %s", signer, ocr_sha[:16])
        else:
            log.info("%s: running ocrmypdf on %s...", signer, src_path.name)
            ocr_bytes = _run_ocr(src_path)
            if ocr_bytes is None:
                continue
            ocr_sha = forensics.capture_derived(
                ocr_bytes,
                derived_from=sha,
                transform=TRANSFORM,
                source_type="ownerless_decree_ocr_pdf",
                title=f"Ownerless decree signed by {signer} [OCR]",
                description=(
                    f"OCR-derived searchable PDF of an ownerless-property decree "
                    f"signed by {signer} (parent sha256={sha}). Transform: "
                    f"{TRANSFORM}. Captured to recover this signer's position "
                    "title from the signature block -- progress_report_2026-06.md "
                    "§5 item 6. Derived artifact -- raw scan remains the "
                    "immutable original."
                ),
                content_type="application/pdf",
                con=con,
            )
            ocr_path = str(config.RAW_DIR / f"{ocr_sha}.pdf")
            log.info("%s: OCR done -> %s", signer, ocr_sha[:16])

        text = ""
        try:
            with pdfplumber.open(ocr_path) as pdf:
                text = "\n".join(p.extract_text() or "" for p in pdf.pages)
        except Exception as e:
            log.error("%s: text extraction failed: %s", signer, e)

        out_rows.append({
            "signer": signer,
            "source_sha256": sha,
            "ocr_sha256": ocr_sha,
            "text": text.strip(),
        })
        log.info("%s: extracted %d chars", signer, len(text))
        # Print the tail (signature block is usually at the end) for manual reading.
        tail = text.strip()[-400:]
        log.info("%s: signature-block tail:\n%s\n", signer, tail)

    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PARSED_DIR / "decree_signer_titles_202606.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for r in out_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    log.info("wrote %s (%d rows)", out_path, len(out_rows))


if __name__ == "__main__":
    main()
