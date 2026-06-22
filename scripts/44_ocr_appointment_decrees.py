#!/usr/bin/env python3
"""Stage 2j: OCR + extract text for the Mariupol-administration appointment
chronology found in the denis-pushilin.ru archives-only crawl (script 39 +
script 43's index).

These 9 Указы (all `denis_pushilin_doc_pdf`, scanned images with no text
layer -- pdfplumber returns 0 chars) bracket the command chain
Пушилин -> heads of Mariupol city administration -> Иващенко/Моргун
(see docs/stakeholder_network.md Tier 3):

  - Ukaz_N108_31032022.pdf  №108 31.03.2022 "Об администрации города Мариуполя"
      -- founding decree establishing the occupation administration itself.
  - Ukaz_N123_06042022.pdf  №123 06.04.2022 "О главе администрации города Мариуполя"
      -- appoints the first head of Mariupol administration.
  - Ukaz_13_22012023.pdf    №13(врио) 22.01.2023 "Об Иващенко К.В."
  - Ukaz_14_22012023.pdf    №14(врио) 22.01.2023 "О Моргуне О.В."
  - Ukaz_15_23012023.pdf    №15(врио) 23.01.2023 "О главе администрации города Мариуполя"
      -- same-week trio: likely installs a new head of administration with
      Иващенко/Моргун in supporting roles, or vice versa.
  - Ukaz_N541_06112023.pdf  №541 06.11.2023 "О Моргуне О.В."
  - Ukaz_N542_06112023.pdf  №542 06.11.2023 "О временно исполняющем полномочия
      главы муниципального образования городского округа Мариуполь"
      -- same-day pair: likely Моргун becomes врио head of Mariupol municipal
      formation.
  - Ukaz_N492_12062025.pdf  №492 12.06.2025 "О Моргуне О.В."
  - Ukaz_N493_13062025.pdf  №493 13.06.2025 "О временно исполняющем полномочия
      главы муниципального образования городского округа Мариуполь"
      -- same pattern repeated, 2025.

FORENSIC RULE: OCR is lossy -- raw scans are never modified. Each OCR output is
written as a DERIVED artifact (forensics.capture_derived), source_type
`denis_pushilin_doc_ocr_pdf`, recording derived_from + transform. Idempotent
(checks for an existing derivative before re-running ocrmypdf).

Output: data/parsed/denis_pushilin_appointment_chronology.jsonl (one row per
decree: filename, original sha256, ocr sha256, decree title/date, full
extracted text).

Prereqs: ocrmypdf + tesseract 'rus' model (already verified present in .venv).
Local-only, no network: PYTHONPATH=src python scripts/44_ocr_appointment_decrees.py
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

# filename -> (sha256, short label for the report)
TARGETS: dict[str, tuple[str, str]] = {
    "Ukaz_N108_31032022.pdf": ("46c61cd98fdf20962f73908adafcbb5786922c2665a4712a4ad88fab44887d23",
                                "Об администрации города Мариуполя (founding decree)"),
    "Ukaz_N123_06042022.pdf": ("3e8ed9b58a332752a628844d13a7160aca2af9d8e1b6c4e7afc4085281eeeb3e",
                                "О главе администрации города Мариуполя (first head)"),
    "Ukaz_13_22012023.pdf": ("996f028298b8a6978ad195d788f15a8fac01e38078b564d34c6795a7e1f9c316",
                              "Об Иващенко К.В."),
    "Ukaz_14_22012023.pdf": ("f856f85fea6bf2acdac77bf038c901ff106cf35b521683565d6b96b9a01ab242",
                              "О Моргуне О.В."),
    "Ukaz_15_23012023.pdf": ("cd4175305b32ab829b04271ceecbba30816d3bc20ba40a811956de501857ef74",
                              "О главе администрации города Мариуполя"),
    "Ukaz_N541_06112023.pdf": ("1a69abab3e86aff8f03aeb92be69b9ee8485ac83c46cd973a1a68fcff0afa057",
                                "О Моргуне О.В."),
    "Ukaz_N542_06112023.pdf": ("21ec2f1a2436cae4172363d1258748d8dd115378cf84affbc7aa7ea9018d6161",
                                "О временно исполняющем полномочия главы МО ГО Мариуполь"),
    "Ukaz_N492_12062025.pdf": ("005e412159538985901e1227bb65e9e401148eba378ea397fa17dc2636d1daeb",
                                "О Моргуне О.В."),
    "Ukaz_N493_13062025.pdf": ("0c00f58a3460e493ed2fd269b768a8bc346eadd1b5cf97dd8c05873ea9d519e9",
                                "О временно исполняющем полномочия главы МО ГО Мариуполь"),
}


def _already_ocrd(con, parent_sha: str) -> str | None:
    row = con.execute(
        "SELECT sha256, raw_path FROM source_document "
        "WHERE derived_from = ? AND transform = ? LIMIT 1",
        (parent_sha, TRANSFORM),
    ).fetchone()
    return row


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

    for filename, (sha, label) in TARGETS.items():
        row = con.execute(
            "SELECT raw_path FROM source_document WHERE sha256=?", (sha,)
        ).fetchone()
        if not row:
            log.error("%s: sha256 %s not in source_document", filename, sha)
            continue
        src_path = Path(row[0])

        existing = _already_ocrd(con, sha)
        if existing:
            ocr_sha, ocr_path = existing
            log.info("%s: already OCR'd -> %s", filename, ocr_sha[:16])
        else:
            log.info("%s: running ocrmypdf...", filename)
            ocr_bytes = _run_ocr(src_path)
            if ocr_bytes is None:
                continue
            ocr_sha = forensics.capture_derived(
                ocr_bytes,
                derived_from=sha,
                transform=TRANSFORM,
                source_type="denis_pushilin_doc_ocr_pdf",
                title=f"{filename} [OCR] -- {label}",
                description=(
                    f"OCR-derived searchable PDF of {filename} (parent "
                    f"sha256={sha}). Transform: {TRANSFORM}. Part of the "
                    "Mariupol-administration appointment chronology "
                    "(docs/stakeholder_network.md Tier 3). Derived artifact "
                    f"-- raw scan ({sha[:16]}..) remains the immutable original."
                ),
                content_type="application/pdf",
                con=con,
            )
            ocr_path = str(config.RAW_DIR / f"{ocr_sha}.pdf")
            log.info("%s: OCR done -> %s", filename, ocr_sha[:16])

        text = ""
        try:
            with pdfplumber.open(ocr_path) as pdf:
                text = "\n".join(p.extract_text() or "" for p in pdf.pages)
        except Exception as e:
            log.error("%s: text extraction failed: %s", filename, e)

        out_rows.append({
            "filename": filename,
            "label": label,
            "source_sha256": sha,
            "ocr_sha256": ocr_sha,
            "text": text.strip(),
        })
        log.info("%s: extracted %d chars", filename, len(text))

    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PARSED_DIR / "denis_pushilin_appointment_chronology.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for r in out_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    log.info("wrote %s (%d rows)", out_path, len(out_rows))


if __name__ == "__main__":
    main()
