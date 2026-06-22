#!/usr/bin/env python3
"""Stage 2g: parse the post-ФКЗ-4 ownerless-property registry XLSX files.

Reads the 4 captured district registries (source_type='ownerless_registry_xlsx',
one per enabled court: zhovtnevy, primorsky, ilyichevsky, ordzhonikidzevsky --
captured 2026-06-09). Under ФКЗ-4 (15.12.2025) the court "признание права
муниципальной собственности" stage was abolished: inclusion in this registry
IS now the seizure act (see docs/reconceptualization_2026.md /
federal_law_dec2025_pivot memory). 12,948 rows total -- this is the new master
seizure-candidate list.

Each row's "Адрес" cell is ';'-delimited:
  5 fields: <settlement>; <street_type>; <street_name>; <house_no>; <apt>
  4 fields: <settlement>; <street_type_or_combined_name>; <house_no_or_name>; <apt_or_house_no>
  3 fields: <settlement>; <combined_name>; <house_no>           (2 rows, no apt)

For 4-field rows, parts[1] is checked against
toponym._CLASS_MAP: a recognised street-type word (улица/переулок/проспект/
бульвар/мкр/...) means parts[1]+parts[2] is the street and parts[3] is the
house (whole-building entry, no apartment); otherwise parts[1] is itself a
combined place name (e.g. "квартал Азовье", "МКР Азовье") and parts[2]/parts[3]
are house/apt. 3-field rows take the same "combined name" branch with no apt.

Output: data/parsed/ownerless_registry.jsonl -- one row per registry entry
(apartment/unit), each carrying source_sha256 for chain of custody, plus
street_raw/house_raw ready for scripts/21's Registry.add() (a new
_from_ownerless_registry extractor is added there separately).

Run locally, no network: python3 scripts/26_parse_ownerless_registry.py
"""
from __future__ import annotations

import json
import logging
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402
from mariupol_seizures.normalize.toponym import _CLASS_MAP  # noqa: E402

try:
    import openpyxl
except ImportError:
    sys.exit("openpyxl not installed — run: .venv/bin/pip install openpyxl")

log = logging.getLogger(__name__)

PARSED_DIR = config.PROJECT_ROOT / "data" / "parsed"

# Map source_document.title (set at capture time, see CLAUDE.md crawl notes)
# -> district_key, matching the convention used by damage_assessment.jsonl
# (e.g. "primorsky_mariupol"). Extracted from the "(court: ...)" suffix.
_COURT_RE = re.compile(r"\(court:\s*([a-z_]+)\)")

# apt_raw classification. Order matters: more specific patterns first.
# All 10 non-numeric/non-plain values found in the 4 registries (2026-06-10
# survey) are covered -- "other" should never fire on this dataset; if it
# does, the row is flagged for human review rather than dropped.
_APT_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^\d+/\d+$"), "apartment_subdivided"),
    (re.compile(r"^\d+-\d+$"), "apartment_range"),
    (re.compile(r"^\d+(?:,\d+)+$"), "apartment_list"),
    (re.compile(r"^кв\.?\s*\d+[а-яё]?$", re.I), "apartment"),
    (re.compile(r"^\d+[а-яё]?$", re.I), "apartment"),
    (re.compile(r"^ком\.?\s*\S+$", re.I), "room"),
    (re.compile(r"^\(разрушен акт\)$", re.I), "destroyed"),
    (re.compile(r"^\(участок\)$", re.I), "plot"),
    (re.compile(r"^строение\s+\S+$", re.I), "structure"),
]


def _apt_kind(apt_raw: str | None) -> tuple[str | None, list[str]]:
    """Classify apt_raw; return (apt_kind, flags). apt_kind is None for
    whole-building entries (no apt field at all -- 4/3-field combined-name
    rows). flags is non-empty only if apt_raw is non-empty but matches none
    of the known patterns (should not happen on this dataset)."""
    if apt_raw is None or apt_raw == "":
        return None, []
    for pattern, kind in _APT_PATTERNS:
        if pattern.match(apt_raw):
            return kind, []
    return "other", ["apt_format_unrecognized"]


def _split_address(addr: str) -> tuple[list[str], str | None, str | None,
                                         str | None, str | None, list[str]]:
    """Split a ';'-delimited 'Адрес' cell into
    (settlement, street_raw, house_raw, apt_raw, flags)."""
    parts = [p.strip() for p in addr.split(";")]
    flags: list[str] = []
    settlement = parts[0] if parts else None

    if len(parts) == 5:
        street_raw = f"{parts[1]} {parts[2]}".strip()
        house_raw = parts[3]
        apt_raw = parts[4]
    elif len(parts) == 4:
        if parts[1].lower() in _CLASS_MAP:
            street_raw = f"{parts[1]} {parts[2]}".strip()
            house_raw = parts[3]
            apt_raw = None
        else:
            street_raw = parts[1]
            house_raw = parts[2]
            apt_raw = parts[3]
    elif len(parts) == 3:
        # e.g. "г. Мариуполь; п Осовиахима Старокрымская; 2" -- combined-name
        # branch, no apt field. 2 rows total (both zhovtnevy).
        street_raw = parts[1]
        house_raw = parts[2]
        apt_raw = None
        flags.append("field_count_3")
    else:
        street_raw = parts[1] if len(parts) > 1 else None
        house_raw = parts[2] if len(parts) > 2 else None
        apt_raw = parts[3] if len(parts) > 3 else None
        flags.append(f"field_count_{len(parts)}")

    return parts, settlement, street_raw, house_raw, apt_raw, flags


def _district_key(title: str) -> str | None:
    m = _COURT_RE.search(title or "")
    return m.group(1) if m else None


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")

    con = forensics.open_state()
    sources = con.execute(
        """SELECT sha256, raw_path, title FROM source_document
           WHERE source_type = 'ownerless_registry_xlsx'
           ORDER BY title"""
    ).fetchall()
    if not sources:
        log.error("No ownerless_registry_xlsx sources captured -- run the VPS crawler first.")
        sys.exit(1)

    out_path = PARSED_DIR / "ownerless_registry.jsonl"
    PARSED_DIR.mkdir(parents=True, exist_ok=True)

    total = 0
    field_count_tally: Counter = Counter()
    apt_kind_tally: Counter = Counter()
    flag_tally: Counter = Counter()
    district_tally: Counter = Counter()

    with out_path.open("w", encoding="utf-8") as fh:
        for sha256, raw_path, title in sources:
            p = Path(raw_path)
            if not p.exists():
                log.error("XLSX missing: %s", raw_path)
                continue
            district_key = _district_key(title)
            wb = openpyxl.load_workbook(p, read_only=True)
            ws = wb["Лист1"]
            rows_iter = ws.iter_rows(values_only=True)
            next(rows_iter)  # header

            n = 0
            for row in rows_iter:
                seq_raw, addr = row[0], row[1]
                if addr is None:
                    continue
                recognition_marker = row[-1]
                parts, settlement, street_raw, house_raw, apt_raw, flags = _split_address(addr)
                field_count_tally[len(parts)] += 1
                apt_kind, apt_flags = _apt_kind(apt_raw)
                flags = flags + apt_flags
                for f in flags:
                    flag_tally[f] += 1
                apt_kind_tally[apt_kind] += 1

                rec = {
                    "source_sha256": sha256,
                    "district_key": district_key,
                    "seq_no": seq_raw,
                    "address_raw": addr,
                    "settlement_raw": settlement,
                    "street_raw": street_raw,
                    "house_raw": house_raw,
                    "apt_raw": apt_raw,
                    "apt_kind": apt_kind,
                    "recognition_marker": (recognition_marker or "").strip() or None,
                    "flags": flags,
                    "row_confidence": 0.9 if flags else 1.0,
                }
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                n += 1
            wb.close()
            district_tally[district_key] = n
            total += n
            log.info("%s (%s): %d rows", title, district_key, n)

    log.info("Wrote %d rows -> %s", total, out_path)
    log.info("  by district: %s", dict(district_tally))
    log.info("  field-count distribution: %s", dict(sorted(field_count_tally.items())))
    log.info("  apt_kind distribution: %s", dict(apt_kind_tally.most_common()))
    if flag_tally:
        log.info("  flags: %s", dict(flag_tally.most_common()))
    log.info("  claim-grade (row_confidence >= 0.8): %d / %d",
             total - sum(flag_tally.values()), total)


if __name__ == "__main__":
    main()
