#!/usr/bin/env python3
"""Stage 2l: re-filter the 282 lexicon-matched, non-Мариуполь entries from
script 43's index (data/parsed/denis_pushilin_archive_index.jsonl) against a
tighter property/land/construction keyword set, splitting the review report
(scripts/45 Part A) into a prioritized subset vs. the rest.

The 282 entries already matched the broad DISPOSSESSION_LEXICON (which
includes toponymy/cadastral/admin terms like "наименован", "улиц",
"планировк" that are not directly about property rights or building works).
This pass tags each entry with which of a narrower PROPERTY_LEXICON terms hit,
so the highest-signal entries (помещения, имущество, недвижимое, жилье,
бесхозяйное, земельные участки, изъятие, снос, строительство, реконструкция,
ремонт, восстановление, повреждённые/разрушенные) surface first.

Local-only, no network. Run:
  PYTHONPATH=src .venv/bin/python scripts/46_filter_lexicon_review_property.py
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402

log = logging.getLogger(__name__)

PARSED_DIR = config.PROJECT_ROOT / "data" / "parsed"
REPORTS_DIR = config.PROJECT_ROOT / "data" / "reports"
ARCHIVE_INDEX = PARSED_DIR / "denis_pushilin_archive_index.jsonl"

# stems for the property/land/construction keyword set requested for review
PROPERTY_LEXICON = (
    "помещен",       # помещения
    "имуществ",      # имущество
    "недвижим",      # недвижимое
    "жил",           # жильё / жилой / жилищ-
    "бесхозяйн",     # бесхозяйное
    "земельн",       # земельные участки
    "изъят",         # изъятие
    "снос",          # снос зданий
    "строительств",  # строительство
    "реконструкц",   # реконструкция
    "ремонт",        # ремонт
    "восстановлен",  # восстановление
    "повреждён", "поврежден",  # повреждённые
    "разрушен",      # разрушенные
)


def _fold(s: str) -> str:
    return (s or "").replace("ё", "е").replace("Ё", "Е").lower()


def matched_terms(row: dict) -> list[str]:
    blob = _fold(f"{row.get('title_text', '')} {row.get('description_text', '')}")
    return [term for term in PROPERTY_LEXICON if _fold(term) in blob]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")

    rows = []
    with ARCHIVE_INDEX.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r.get("lexicon_match") and not r.get("mariupol_match"):
                rows.append(r)

    log.info("base set: %d lexicon-matched, non-Мариуполь entries", len(rows))

    tagged = []
    for r in rows:
        terms = matched_terms(r)
        tagged.append((r, terms))

    priority = [(r, t) for r, t in tagged if t]
    rest = [(r, t) for r, t in tagged if not t]
    log.info("property/construction-relevant: %d", len(priority))
    log.info("remaining (toponymy/admin/other lexicon terms only): %d", len(rest))

    def write_section(lines: list[str], items: list[tuple[dict, list[str]]], with_terms: bool) -> None:
        by_archive: dict[str, list[tuple[dict, list[str]]]] = {}
        for r, terms in items:
            by_archive.setdefault(r["archive"], []).append((r, terms))
        for archive, sub in by_archive.items():
            sub_sorted = sorted(sub, key=lambda rt: rt[0].get("filename_date") or "")
            lines.append(f"### {archive} ({len(sub_sorted)})")
            lines.append("")
            if with_terms:
                lines.append("| Date | Filename | Matched terms | Title | Description | SHA |")
                lines.append("|---|---|---|---|---|---|")
                for r, terms in sub_sorted:
                    lines.append(
                        f"| {r.get('filename_date') or '?'} | `{r['filename']}` | "
                        f"{', '.join(terms)} | {r['title_text']} | "
                        f"{r['description_text']} | `{r['sha256'][:12]}..` |"
                    )
            else:
                lines.append("| Date | Filename | Title | Description | SHA |")
                lines.append("|---|---|---|---|---|")
                for r, _ in sub_sorted:
                    lines.append(
                        f"| {r.get('filename_date') or '?'} | `{r['filename']}` | "
                        f"{r['title_text']} | {r['description_text']} | "
                        f"`{r['sha256'][:12]}..` |"
                    )
            lines.append("")

    lines = [
        "# denis-pushilin.ru lexicon-matched, non-Мариуполь entries -- "
        "property/construction-prioritized review",
        "",
        f"Base set: {len(rows)} entries (script 43 index, lexicon_match=True, "
        "mariupol_match=False; see scripts/45 for the unsplit version). Split "
        "here by a narrower property/land/construction keyword set: "
        f"{', '.join(PROPERTY_LEXICON)}.",
        "",
        f"## Priority: property/construction-relevant ({len(priority)})",
        "",
        "Review these first -- each row shows which keyword(s) matched.",
        "",
    ]
    write_section(lines, priority, with_terms=True)

    lines.append(f"## Remaining (other lexicon terms only, e.g. toponymy/cadastral/admin) ({len(rest)})")
    lines.append("")
    write_section(lines, rest, with_terms=False)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORTS_DIR / "denis_pushilin_lexicon_review_property.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    log.info("wrote %s", out_path)


if __name__ == "__main__":
    main()
