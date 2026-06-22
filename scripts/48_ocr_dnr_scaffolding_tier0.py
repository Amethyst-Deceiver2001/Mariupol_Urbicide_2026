#!/usr/bin/env python3
"""Stage 2n: OCR a Tier-0 batch of two foundational DNR-wide instruments
identified as master predicates while reviewing the Tier-1 batch (script 47,
2026-06-12):

  - Post_GKO_1.pdf -- Постановление ГКО №1 от 06.04.2022 "Об урегулировании
    вопросов строительства, реконструкции, капитального ремонта,
    восстановления поврежденных и разрушенных объектов на территории ДНР".
    Cited by Post_GKO_282 (29.09.2022, rung [D]) as the framework decree that
    establishes the contractor ("подрядная организация") and land-transfer
    procedure (подпункт 2.5 пункта 2) for reconstruction works -- the
    earliest GKO act (3 days after the GKO itself was created by Указ №121
    от 03.04.2022), likely the master predicate for the whole [C]/[D]/[E]
    demolition-land-rebuild chain.

  - Ukaz_73_28122022.pdf -- Указ врио Главы ДНР №73 от 28.12.2022 "Об
    особенностях регулирования имущественных отношений и отношений по
    государственному кадастровому учету недвижимого имущества,
    государственной регистрации прав на недвижимое имущество на территории
    ДНР". Cited repeatedly by Ukaz_290_16082023.pdf (rung [E], EGRN/РУОН
    bridge) as the source of пункты 11(1)/11(2)/11(7) governing "ранее
    учтенные объекты недвижимости" (РУОН) -- likely the master predicate for
    the whole cadastral-bridge / property-relations framework rung [E] (and
    possibly [A], if it defines what happens when a РУОН rights-holder is
    not identified).

Output: data/parsed/dnr_scaffolding_tier0_202606.jsonl (text + flags per doc).

Local-only, no network. Run:
  PYTHONPATH=src .venv/bin/python scripts/48_ocr_dnr_scaffolding_tier0.py
"""
from __future__ import annotations

import json
import logging
import re
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

_BEZHOZ_RE = re.compile(r"бесхозя", re.IGNORECASE)
_MARIUPOL_RE = re.compile(r"мариупол", re.IGNORECASE)

# filename -> (sha256, label)
TARGETS: dict[str, tuple[str, str]] = {
    "Post_GKO_1.pdf": (
        "378f56aa01696f782ffd37e47df73b2a9225edd17ed96f35b9aa8ae16639b52f",
        "Постановление ГКО №1 от 06.04.2022 -- Об урегулировании вопросов "
        "строительства, реконструкции, капитального ремонта, восстановления "
        "поврежденных и разрушенных объектов на территории ДНР",
    ),
    "Ukaz_73_28122022.pdf": (
        "c72912278f457e4c7c1144abfb7e3f5e57a2a8216bfafec8e24ad6d562d8d478",
        "Указ врио Главы ДНР №73 от 28.12.2022 -- Об особенностях "
        "регулирования имущественных отношений и отношений по "
        "государственному кадастровому учету недвижимого имущества, "
        "государственной регистрации прав на недвижимое имущество на "
        "территории ДНР",
    ),
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
                    f"sha256={sha}). Transform: {TRANSFORM}. Tier-0 "
                    "foundational DNR-wide legal-scaffolding instrument "
                    "(scripts/48). Derived artifact -- raw scan "
                    f"({sha[:16]}..) remains the immutable original."
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

        mariupol_mention = bool(_MARIUPOL_RE.search(text))
        bezhozyain_mention = bool(_BEZHOZ_RE.search(text))

        out_rows.append({
            "filename": filename,
            "label": label,
            "source_sha256": sha,
            "ocr_sha256": ocr_sha,
            "text": text.strip(),
            "mariupol_mention": mariupol_mention,
            "bezhozyain_mention": bezhozyain_mention,
        })
        log.info(
            "%s: extracted %d chars, mariupol_mention=%s, bezhozyain_mention=%s",
            filename, len(text), mariupol_mention, bezhozyain_mention,
        )

    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PARSED_DIR / "dnr_scaffolding_tier0_202606.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for r in out_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    log.info("wrote %s (%d rows)", out_path, len(out_rows))


if __name__ == "__main__":
    main()
