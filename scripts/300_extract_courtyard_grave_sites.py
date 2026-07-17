#!/usr/bin/env python3
"""Extract potential ad-hoc/informal grave sites from the full "Mariupol
Destruction and Victims Map" named-victims sheet captured in
scripts/299_capture_victims_map_full_sheet.py.

A row is flagged when the burial-place field ("Место захоронения") reads as
an informal, on-the-spot burial rather than a transfer to a cemetery/morgue
-- e.g. "похоронена во дворе", "похоронен за домом", "во дворе многоэтажки"
-- OR when the burial-place field textually echoes the same street named in
the death-place / residence fields (place of death and place of burial are
the same address).

Read-only analysis of an already-captured local file -- no network, no DB
write. Output: data/reports/courtyard_grave_sites.csv (full detail) +
a console summary.
"""
import csv
import logging
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402

log = logging.getLogger(__name__)

RAW_SHA = "17e0dd2c821dfecd01d1f11a499eb4f72cdf585cf9eb1e4520eb4efeaa9dc7a8"
RAW_FILE = config.RAW_DIR / f"{RAW_SHA}.csv"
OUT_FILE = ROOT / "data" / "reports" / "courtyard_grave_sites.csv"

COL_NAME, COL_DOB, COL_DOD, COL_CAUSE, COL_RESIDENCE, COL_DEATHPLACE, COL_BURIAL, COL_SOURCE, COL_NOTES = range(1, 10)

# Informal/on-the-spot burial language. Deliberately excludes plain "кладбище"
# (cemetery) and "морг" (morgue) -- those are formal disposition, not ad-hoc
# grave sites, even though grief and violence surround them too.
INFORMAL_KEYWORDS = [
    "во дворе", "во дворике", "в дворе", "дворике", "дворик",
    "за домом", "возле дома", "около дома", "у дома", "рядом с домом",
    "в саду", "в огороде", "огород",
    "у подъезда", "около подъезда", "подъезд",
    "в палисаднике", "палисадник",
    "на детской площад", "на клумбе", "клумб",
    "под окн",
    "в гараже", "гараж",
    "в подвале", "подвал",
    "в сарае", "сарай",
    "на месте гибели", "на месте смерти", "там же, где",
    "прямо во", "закопали", "закопан",
]

REBURIAL_KEYWORDS = ["перезахорон", "эксгум"]
CEMETERY_KEYWORDS = ["кладбищ"]
MORGUE_KEYWORDS = ["морг"]
# Negation: "тело лежит"/"не захоронен" etc. means the remains were left in
# place, NOT buried -- a real and distinct tragedy, but not a grave. Keyword
# classifiers are negation-blind by default (project precedent: see memory
# lifecycle_classifier_unreliable_siege_damage.md), so this is checked
# explicitly and reported as its own category rather than folded silently
# into "informal_keyword".
UNBURIED_KEYWORDS = [
    "не захоронен", "не захоронены", "не захоронена",
    "не погребен", "без захоронения", "тело лежит", "тела лежат",
    "не смогли похоронить", "не удалось похоронить",
]

STREET_TYPE = (
    r"(?:ул\.?|улица|пр-?кт\.?|просп\.?|проспект|б-р|бул\.?|бульвар|"
    r"пер\.?|переулок|пл\.?|площадь|наб\.?|набережная|проезд|шоссе)"
)
STREET_TOKEN_RE = re.compile(
    rf"{STREET_TYPE}\.?\s+([а-яёА-ЯЁ][а-яёА-ЯЁ\-\s]{{2,25}}?)[,\s]+(?:д\.?\s*)?(\d+[а-яА-Я]?)",
    re.IGNORECASE,
)
# fallback: bare "Name NN" without a recognised street-type prefix (common
# in this sheet, e.g. "Жигулевская, 67")
BARE_TOKEN_RE = re.compile(
    r"([А-ЯЁ][а-яё]{2,20}(?:ая|ой|ий|ый|ого)?)[,\s]+(\d+[а-яА-Я]?)\b"
)


def street_tokens(text: str) -> set[str]:
    if not text:
        return set()
    found = set()
    for name, num in STREET_TYPE and STREET_TOKEN_RE.findall(text):
        found.add(f"{name.strip().lower()} {num.lower()}")
    for name, num in BARE_TOKEN_RE.findall(text):
        found.add(f"{name.strip().lower()} {num.lower()}")
    return found


def classify(residence: str, deathplace: str, burial: str) -> tuple[list[str], list[str]]:
    """Return (flags, matched_keywords) for one row's burial field."""
    b = (burial or "").lower()
    flags: list[str] = []
    matched: list[str] = []

    if not b.strip():
        return flags, matched

    is_unburied = any(kw in b for kw in UNBURIED_KEYWORDS)
    if is_unburied:
        flags.append("unburied_remains")

    for kw in INFORMAL_KEYWORDS:
        if kw in b:
            flags.append("informal_keyword")
            matched.append(kw)
            break

    death_tokens = street_tokens(deathplace) | street_tokens(residence)
    burial_tokens = street_tokens(burial)
    if death_tokens and burial_tokens and (death_tokens & burial_tokens):
        flags.append("address_echo")

    if any(kw in b for kw in REBURIAL_KEYWORDS):
        flags.append("later_reburied")

    is_cemetery = any(kw in b for kw in CEMETERY_KEYWORDS)
    is_morgue = any(kw in b for kw in MORGUE_KEYWORDS)
    if is_cemetery and "informal_keyword" not in flags and "address_echo" not in flags:
        flags.append("formal_cemetery")  # excluded category, kept for the audit trail
    if is_morgue and "informal_keyword" not in flags and "address_echo" not in flags:
        flags.append("formal_morgue")

    return list(dict.fromkeys(flags)), matched


def main() -> None:
    if not RAW_FILE.exists():
        raise SystemExit(f"raw capture not found: {RAW_FILE} -- run scripts/299 first")

    with RAW_FILE.open(encoding="utf-8") as f:
        rows = list(csv.reader(f))
    header, data = rows[0], rows[1:]
    log.info("loaded %d data rows from %s", len(data), RAW_FILE.name)

    results = []
    flag_counts: Counter = Counter()
    for i, row in enumerate(data, start=2):  # +2: 1-indexed + header row
        row = row + [""] * (max(COL_NOTES, COL_BURIAL) + 1 - len(row))
        name = row[COL_NAME].strip()
        residence = row[COL_RESIDENCE].strip()
        deathplace = row[COL_DEATHPLACE].strip()
        burial = row[COL_BURIAL].strip()
        if not burial:
            continue

        flags, matched = classify(residence, deathplace, burial)
        grave_flags = [f for f in flags if f in ("informal_keyword", "address_echo")]
        if not grave_flags:
            continue

        for f in flags:
            flag_counts[f] += 1

        results.append({
            "sheet_row": i,
            "name": name,
            "dob": row[COL_DOB].strip(),
            "dod": row[COL_DOD].strip(),
            "cause": row[COL_CAUSE].strip(),
            "residence": residence,
            "death_place": deathplace,
            "burial_place": burial,
            "flags": ";".join(flags),
            "matched_keyword": ";".join(matched),
            "source": row[COL_SOURCE].strip(),
            "notes": row[COL_NOTES].strip(),
        })

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()) if results else [
            "sheet_row", "name", "dob", "dod", "cause", "residence", "death_place",
            "burial_place", "flags", "matched_keyword", "source", "notes",
        ])
        w.writeheader()
        w.writerows(results)

    unburied_only = sum(1 for r in results if "unburied_remains" in r["flags"])
    confirmed = len(results) - unburied_only

    log.info("=== SUMMARY ===")
    log.info("total data rows: %d", len(data))
    log.info("rows with any burial-place text: %d", sum(1 for r in data if len(r) > COL_BURIAL and r[COL_BURIAL].strip()))
    log.info("flagged as potential ad-hoc/informal grave site: %d", len(results))
    log.info("  of which explicitly note the body was NOT buried (remains left in place): %d", unburied_only)
    log.info("  confirmed informal burial (excl. unburied-remains rows): %d", confirmed)
    for k, v in flag_counts.most_common():
        log.info("  %s: %d", k, v)
    log.info("written -> %s", OUT_FILE)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
