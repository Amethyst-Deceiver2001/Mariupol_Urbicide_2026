#!/usr/bin/env python3
"""Stage 2m: OCR a Tier-1 batch of newly-identified DNR-wide legal-scaffolding
instruments from the denis-pushilin.ru archive (scripts 39/43), surfaced by
script 46's property/construction keyword filter plus a manual rung-by-rung
review against docs/legal_mechanisms_review.md (2026-06-12).

These 12 PDFs (postanovleniya_gko, ukazy_glavy, zakony) were never OCR'd --
their script-43 archive_index entries carry only the listing-page
title/description (several truncated mid-sentence, one empty). OCRing them
confirms full titles, surfaces any Mariupol-specific content not visible in
the truncated description, and resolves the 29.09.2022 GKO "package"
requisition decrees (#283/284/285, "Об изъятии имущества для государственных
нужд" -- targets unknown from the index alone).

Targets and hypothesized rung (see docs/legal_mechanisms_review.md):
  - Post_GKO_153 (08.07.2022) -- [A] candidate master predicate: "признание
    права собственности на недвижимое имущество... ранее временно
    находившихся под контролем Украины"
  - Post_GKO_267 (29.09.2022) -- [A] "обращение недвижимого имущества в
    муниципальную собственность" (DNR-wide sibling of Post_GKO_300, same
    29.09.2022 batch)
  - Post_GKO_282 (29.09.2022) -- [D] land-for-reconstruction seizure,
    predates закон №39-РЗ (2023) by 15 months
  - Ukaz_40_02122022 (врио Главы, empty title in index) -- [C] "порядок
    выявления и сноса объектов, поврежденных в результате боевых действий"
    (parent of amendments №657/2024 and №513/2025)
  - Post_GKO_175 (30.07.2022) -- [G] base compensation-for-lost-housing
    procedure, candidate primary text for the [REPORTED] 25 sq.m cap
  - Ukaz_N515 (02.11.2023) -- [A] forced-entry/inspection of owner-absent
    flats in apartment buildings
  - Post_GKO_228 (06.09.2022) -- nationalization of "Комбинат Каргилл"
    assets; confirm Mariupol sea-port location
  - Post_GKO_283/284/285 (29.09.2022) -- "изъятие имущества для
    государственных нужд" x3, targets unknown
  - 279rz (Закон №279-РЗ, 15.05.2026) -- [A] newest property
    identification/categorization framework
  - Ukaz_290_16082023 (врио Главы) -- [E] EGRN cadastral bridge for
    "previously recorded" real estate objects

Output: data/parsed/dnr_scaffolding_tier1_202606.jsonl (text + flags per doc).

Local-only, no network. Run:
  PYTHONPATH=src .venv/bin/python scripts/47_ocr_dnr_scaffolding_tier1.py
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

_CADASTRAL_RE = re.compile(r"\d{2}:\d{2}:\d{6,7}:\d+")
_MARIUPOL_RE = re.compile(r"мариупол", re.IGNORECASE)
_SQM_RE = re.compile(r"\d+\s*(?:кв\.?\s*м|квадратных\s+метр)", re.IGNORECASE)

# filename -> (sha256, label)
TARGETS: dict[str, tuple[str, str]] = {
    "Post_GKO_153.pdf": (
        "cd5cd9bf101271bdd6662fcf2bbbeb895d072e22c59294a44e2ed7174671843e",
        "Постановление ГКО №153 от 08.07.2022 -- О признании права собственности "
        "на недвижимое имущество, расположенное на освобожденных территориях ДНР, "
        "ранее временно находившихся под контролем Украины",
    ),
    "Post_GKO_267.pdf": (
        "b6fd0c04c0b93bc2a5b9f040518c0b3a4ce1951f8bab6112c03358b4cc2dc370",
        "Постановление ГКО №267 от 29.09.2022 -- Об обращении недвижимого "
        "имущества в муниципальную собственность",
    ),
    "Post_GKO_282.pdf": (
        "301263e3ef29bcc4622789ff97302e990907c6b07d6fbd776aa8c22382e73e68",
        "Постановление ГКО №282 от 29.09.2022 -- Об особенностях изъятия и "
        "предоставления земельных участков, необходимых для работ по "
        "восстановлению объектов капитального строительства",
    ),
    "Ukaz_40_02122022.pdf": (
        "fc4085b07ad3c351f4a469e5bdf83dafc0702e38ef7db97698cc84e2218f6a95",
        "Указ врио Главы ДНР №40 от 02.12.2022 -- (title empty in archive index; "
        "amended by №657/2024 and №513/2025 'О порядке выявления и сноса "
        "объектов, поврежденных в результате боевых действий')",
    ),
    "Post_GKO_175.pdf": (
        "63b87ec3a9159ad755e7f0ecaf943cfe4e0aecaa604c4484e80354364770bf2b",
        "Постановление ГКО №175 от 30.07.2022 -- О компенсации за утраченное "
        "или поврежденное жилье, а также за утраченное имущество первой "
        "необходимости лицам, пострадавшим в результате боевых действий",
    ),
    "Ukaz_N515_02112023.pdf": (
        "3e763b6843a1af0893f7a692871fba2f440ca63895062df75b62d72bc7df16be",
        "Указ Главы ДНР №515 от 02.11.2023 -- О порядке вскрытия жилых и "
        "нежилых помещений в многоквартирных домах при отсутствии их "
        "собственника (владельца, пользователя)",
    ),
    "Post_GKO_228.pdf": (
        "afaecc9b9d123e0d0016aa6d3602b962d14f6bfc3f7699ec90b309390ff9c091",
        "Постановление ГКО №228 от 06.09.2022 -- Об обращении имущества "
        "ООО «КОМБИНАТ «КАРГИЛЛ» в государственную собственность",
    ),
    "Post_GKO_283.pdf": (
        "add1aecc771d13d7f8370c444663bdab1e09e5ba263d7f6700216681554ac716",
        "Постановление ГКО №283 от 29.09.2022 -- Об изъятии имущества для "
        "государственных нужд (target unknown)",
    ),
    "Post_GKO_284.pdf": (
        "3d69d2d157f44263a937fa572bdf1eaafb9171e95a10ffea3056f47618ffe0f1",
        "Постановление ГКО №284 от 29.09.2022 -- Об изъятии имущества для "
        "государственных нужд (target unknown)",
    ),
    "Post_GKO_285.pdf": (
        "a258463ae5019573e218346f47732b695182341bdc1d9f1f093172cc06b64233",
        "Постановление ГКО №285 от 29.09.2022 -- Об изъятии имущества для "
        "государственных нужд (target unknown)",
    ),
    "279rz.pdf": (
        "4ab965fe0ed3ca59d0cf1150072c44143e6a7258256919001fdeff4abc6c6a2e",
        "Закон ДНР №279-РЗ (Опубликован 15.05.2026) -- Об особенностях "
        "выявления, учета, изменения категорий (перечней) и использования "
        "объектов имущества, расположенных на территории ДНР, на которые "
        "возникает право государственной собственности",
    ),
    "Ukaz_290_16082023.pdf": (
        "cb2206fc29a1301c18f649aa3d01e9629841a0960acc45f3bc22448c78995365",
        "Указ врио Главы ДНР №290 от 16.08.2023 -- Об особенностях внесения в "
        "Единый государственный реестр недвижимости сведений о ранее учтенных "
        "объектах недвижимости и выполнения комплексных кадастровых работ",
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
                    f"sha256={sha}). Transform: {TRANSFORM}. DNR-wide "
                    "legal-scaffolding candidate, screened for rung "
                    "classification (scripts/47). Derived artifact -- raw "
                    f"scan ({sha[:16]}..) remains the immutable original."
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

        cadastral_numbers = sorted(set(_CADASTRAL_RE.findall(text)))
        mariupol_mention = bool(_MARIUPOL_RE.search(text))
        sqm_mentions = sorted(set(_SQM_RE.findall(text)))

        out_rows.append({
            "filename": filename,
            "label": label,
            "source_sha256": sha,
            "ocr_sha256": ocr_sha,
            "text": text.strip(),
            "cadastral_numbers": cadastral_numbers,
            "mariupol_mention": mariupol_mention,
            "sqm_mentions": sqm_mentions,
        })
        log.info(
            "%s: extracted %d chars, mariupol_mention=%s, cadastral=%s, sqm=%s",
            filename, len(text), mariupol_mention, cadastral_numbers, sqm_mentions,
        )

    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PARSED_DIR / "dnr_scaffolding_tier1_202606.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for r in out_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    log.info("wrote %s (%d rows)", out_path, len(out_rows))


if __name__ == "__main__":
    main()
