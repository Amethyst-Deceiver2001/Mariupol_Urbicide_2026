#!/usr/bin/env python3
"""Parse the Mariupol land-grant Распоряжения found in the denis-pushilin.ru
archive's /doc/rasp/ folder (scripts/249's OCR survey, 2026-07-05), and
diff against data/parsed/dnr_land_orders.jsonl (built by scripts/10-11 from
a different portal, glavadnr.ru/HTML) to find genuinely new ones.

IMPORTANT (bug found + fixed 2026-07-05): decree NUMBERS reset annually on
this portal -- e.g. "rasporiazhglavaN10_" exists for 2024, 2025, AND 2026 as
three unrelated decrees (same pattern as the №619 non-find earlier this
session). An earlier version of this script resolved target decrees by
number alone via the URL, which silently grabbed the wrong year's decree for
any reused number. Fixed by working from the content-VERIFIED candidate set
directly (every doc whose OCR text actually contains the land-grant-specific
phrase combination, matched in the audit that produced the 45-new-number
claim in docs/legal_mechanisms_review.md) and keying dedup on
(decree_number, decree_date) pairs, not decree_number alone.

Output: data/parsed/dnr_land_orders_pushilin_new.jsonl -- one record per
NEW decree, schema-compatible with dnr_land_orders.jsonl. Kept as a SEPARATE
file rather than appended in-place, so a bad parse here can't corrupt the
already-working 52-row file; merge by hand (or with scripts/11's own
loader, once this is spot-checked) once verified.

Run:
    python3 scripts/250_parse_pushilin_land_grants.py
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

STATE_DB = ROOT / "data" / "state.sqlite"
OCR_DIR = ROOT / "data" / "parsed" / "pushilin_rasp_ukazy_ocr"
OUT_PATH = ROOT / "data" / "parsed" / "dnr_land_orders_pushilin_new.jsonl"
EXISTING_PATH = ROOT / "data" / "parsed" / "dnr_land_orders.jsonl"

_ORG_ANCHOR = re.compile(
    r"(?:акционерн\w+\s+обществ\w+"
    r"|обществ\w+\s+с\s+ограниченн\w+\s+ответственность\w+"
    r"|ООО|АО|ПАО)\s*[«\"]",
    re.I,
)
_BEN_TERM = re.compile(
    r"\s*(?:о\s+предоставлении|в\s+аренду|земельн\w+\s+участ"
    r"|,\s*(?:ОГРН|ИНН|\()|\(ОГРН)",
    re.I,
)
_OGRN = re.compile(r"ОГРН\s+(\d{13,15})")
_INN = re.compile(r"ИНН\s+(\d{10,12})")
_CADASTRAL = re.compile(r"93:\d+:\d+:\d+")
_AREA = re.compile(r"([\d][\d\s]{0,9})\s*(?:\+/?-?[\d\s]*)?\s*м\s*2", re.I)
_ADDRESS_BLOCK = re.compile(
    r"по\s+адресу\s*:?\s*(.*?)(?=,?\s*находящ|,\s*для\s+реализации|\.\s|\Z)",
    re.S | re.I,
)
_ADDR_BOILERPLATE = re.compile(
    r"^Российская\s+Федерация,?\s+Донецка[яйе]\s+Народна[яйе]\s+Республика,?\s+"
    r"(?:городской\s+округ\s+Мариуполь,?\s+)?"
    r"(?:город\s+Мариуполь,?\s*)?",
    re.I,
)
_PROJECT = re.compile(r"инвестиционного\s+проекта\s*[«\"]([^»\"]{3,120})", re.I)
_DATE_DOT = re.compile(r"(\d{2})[.\s](\d{2})[.\s](\d{4})")
_SIGNER = re.compile(r"Глава\s+Донецкой\s+Народной\s+Республики\s+([А-ЯЁ]\.\s*[А-ЯЁ]\.\s*[А-ЯЁ][а-яё]+)", re.I)
_SIGNER_VRIO = re.compile(r"врио\s+Главы\s+.{0,30}?\s+([А-ЯЁ]\.\s*[А-ЯЁ]\.\s*[А-ЯЁ][а-яё]+)", re.I)
_BODY_GOVT = re.compile(r"ПРАВИТЕЛЬСТВО\s+ДОНЕЦКОЙ\s+НАРОДНОЙ\s+РЕСПУБЛИКИ", re.I)


def _parse_dot_date(s: str) -> str | None:
    m = _DATE_DOT.search(s)
    if not m:
        return None
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
    except ValueError:
        return None


def _parse_area(raw: str) -> float | None:
    digits = re.sub(r"\s+", "", raw.split("+")[0].split("-")[0].strip())
    try:
        return float(digits)
    except ValueError:
        return None


def _strip_boilerplate(addr: str) -> str:
    return _ADDR_BOILERPLATE.sub("", addr.strip()).strip().rstrip(",")


def _find_beneficiary(text: str) -> str | None:
    m = _ORG_ANCHOR.search(text)
    if not m:
        return None
    start = m.end()
    term = _BEN_TERM.search(text, start)
    end = term.start() if term else min(start + 120, len(text))
    candidate = text[start:end].strip()
    if candidate.endswith("»") and "«" not in candidate:
        candidate = candidate[:-1].strip()
    return candidate if len(candidate) > 2 else None


def _extract_decree_number(text: str) -> str | None:
    """The decree number sits in the signature block near the very end,
    typically '№ NNN' on its own line right after the city/date and before
    the signer's name. Take the LAST '№ <digits>' match in the whole text,
    not the first (which risks matching a citation to some OTHER decree
    referenced in the body, e.g. 'Указом ... № 121')."""
    matches = list(re.finditer(r"№\s*(\d{1,4})(?:[\s,.]|$)", text))
    return matches[-1].group(1) if matches else None


def parse_ocr_text(text: str, source_sha256: str, url: str) -> dict:
    tt = re.sub(r"\s+", " ", text)
    flags: list[str] = []

    decree_number = _extract_decree_number(tt)
    if not decree_number:
        flags.append("decree_number_missing")

    # Date -- use the filename's own DDMMYYYY (ground truth, see
    # _filename_date's docstring); in-body OCR date search is kept only as a
    # fallback for the rare case the filename itself lacks one, and is
    # markedly less reliable (decrees cite other dates in the body, e.g.
    # "с 14 мая 2014 года" as a legal-basis boilerplate reference).
    decree_date = _filename_date(url)
    if not decree_date:
        flags.append("date_from_ocr_fallback")
        tail = tt[-400:]
        months = ["январ", "феврал", "март", "апрел", "ма", "июн", "июл", "август",
                  "сентябр", "октябр", "ноябр", "декабр"]
        word_matches = list(re.finditer(
            r"(\d{1,2})\s+(январ\w+|феврал\w+|март\w+|апрел\w+|ма[йя]\w*|июн\w+|"
            r"июл\w+|август\w+|сентябр\w+|октябр\w+|ноябр\w+|декабр\w+)\s+(\d{4})", tail, re.I))
        if word_matches:
            m = word_matches[-1]
            mon_word = m.group(2).lower()
            mon = next((i + 1 for i, mm in enumerate(months) if mon_word.startswith(mm)), None)
            if mon:
                try:
                    decree_date = date(int(m.group(3)), mon, int(m.group(1))).isoformat()
                except ValueError:
                    pass
        if not decree_date:
            dot_matches = list(_DATE_DOT.finditer(tail))
            if dot_matches:
                decree_date = _parse_dot_date(dot_matches[-1].group(0))
    if not decree_date:
        flags.append("date_missing")

    issuing_body = "Правительство ДНР" if _BODY_GOVT.search(tt) else (
        "врио Главы ДНР" if _SIGNER_VRIO.search(tt) else "Глава ДНР"
    )
    sm = _SIGNER.search(tt) or _SIGNER_VRIO.search(tt)
    signing_official = sm.group(1).strip() if sm else None

    beneficiary = _find_beneficiary(tt)
    if not beneficiary:
        flags.append("beneficiary_missing")

    om, im = _OGRN.search(tt), _INN.search(tt)
    ogrn = om.group(1) if om else None
    inn = im.group(1) if im else None
    inn_source = "decree_text" if inn else None

    cadastrals = list(dict.fromkeys(_CADASTRAL.findall(tt)))
    if not cadastrals:
        flags.append("cadastral_missing")

    am = _AREA.search(tt)
    area_sqm = _parse_area(am.group(1)) if am else None
    if area_sqm is None:
        flags.append("area_missing")

    adm = _ADDRESS_BLOCK.search(tt)
    address_raw = adm.group(1).strip() if adm else None
    address_norm = _strip_boilerplate(address_raw) if address_raw else None
    if not address_norm:
        flags.append("address_missing")

    pm = _PROJECT.search(tt)
    project_name = pm.group(1).strip() if pm else None

    return {
        "source_sha256": source_sha256,
        "decree_number": decree_number,
        "decree_date": decree_date,
        "issuing_body": issuing_body,
        "signing_official": signing_official,
        "beneficiary_name": beneficiary,
        "beneficiary_ogrn": ogrn,
        "beneficiary_inn": inn,
        "beneficiary_inn_source": inn_source,
        "cadastral_numbers": cadastrals,
        "area_sqm": area_sqm,
        "address_raw": address_raw,
        "address_normalized": address_norm,
        "project_name": project_name,
        "legal_basis": [],
        "flags": flags,
        "source_portal": "denis-pushilin.ru",  # distinguishes this source from glavadnr.ru rows
    }


LAND_SURVEY_PATH = ROOT / "data" / "parsed" / "pushilin_rasp_ukazy_survey.jsonl"


_FILENAME_DATE_RE = re.compile(r"_(\d{2})(\d{2})(\d{4})\.pdf$")


def _filename_date(url: str) -> str | None:
    """The ground-truth date for these decrees: it's baked into the crawl
    filename itself (rasporiazhglavaNNN_DDMMYYYY.pdf), set by the SOURCE
    SITE, not by any parser here. Confirmed 2026-07-05 that in-body OCR date
    extraction is unreliable (picked up citation dates, e.g. a wrong '2023-
    07-20' for a decree the filename itself dates 07.09.2023) and that
    decree numbers genuinely repeat across years (rasporiazhglavaN291_ exists
    for 2022, 2023, AND 2024 as three distinct real decrees) -- so the
    filename date is both more trustworthy AND the only way to tell which
    same-numbered decree a given file actually is."""
    m = _FILENAME_DATE_RE.search(url)
    if not m:
        return None
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        return date(y, mo, d).isoformat()
    except ValueError:
        return None


def _content_verified_candidates() -> list[tuple[str, str]]:
    """The rasp/-folder (sha256, url) pairs whose OCR text actually contains
    the land-grant phrase combination (предоставл + земельн + Мариупол +
    аренду/собственность) -- the same content filter used in the session
    audit that produced docs/legal_mechanisms_review.md's [D] write-up.
    Working from verified content, not a bare URL-embedded number, is what
    avoids treating an unrelated same-numbered decree as this one; the url
    is carried through so its filename date can be used as ground truth."""
    out = []
    for line in LAND_SURVEY_PATH.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("folder") != "rasp" or "error" in r:
            continue
        txt_path = OCR_DIR / f"{r['sha256']}.txt"
        if not txt_path.exists():
            continue
        t = txt_path.read_text(encoding="utf-8", errors="replace")
        # Case-insensitive: the OCR routinely capitalises the clause-initial
        # "Земельного участка" and uses the genitive "собственности", so a
        # case-sensitive lowercase test for "земельн"/"собственность" silently
        # dropped genuine grants (e.g. №122/2024, №178/2025 Корпорация СМУ-5).
        # The land-grant signature that actually discriminates is the no-tender
        # investment-lease formula, so key on that.
        tl = t.lower()
        if ("без проведения торгов" in tl and "мариупол" in tl
                and "инвестиционного проекта" in tl and "земельн" in tl):
            out.append((r["sha256"], r["url"]))
    return out


def _existing_by_number() -> dict[str, list[dict]]:
    """Keyed on decree_number ALONE, not (number, date) -- but collecting
    EVERY existing row for that number, not just the first (bug found +
    fixed 2026-07-05: an earlier version used dict.setdefault(), which
    silently kept only the FIRST date seen per number; decree numbers that
    legitimately recur 2-3 times in dnr_land_orders.jsonl -- e.g. №178
    (2024-04-19 / 2025-05-26 / 2026-05-25), №392-394 (2024-10-24 placeholder
    + 2025-11-06 real) -- then got compared against only ONE of their real
    dates, so a re-parse of an ALREADY-KNOWN decree with a different
    (but also already-known) date was wrongly flagged as new/mismatched).

    Both this script's candidates and dnr_land_orders.jsonl are already
    scoped to CONFIRMED Mariupol land-grant decrees (not the general decree
    population where numbers genuinely reset/collide across years) -- within
    that narrower scope a repeated number is overwhelmingly likely to be the
    same decree read by two different parsers, not two independent land
    grants that coincidentally share a number. Confirmed empirically
    2026-07-05: №289-291 showed up as 'new' under (number,date) keying purely
    because this script's OCR-based date extraction disagreed with
    scripts/11's HTML-based one for the same real decree -- so we still key
    on number alone, but now check the new record's date against ALL of that
    number's known dates before deciding it's a mismatch."""
    by_num: dict[str, list[dict]] = {}
    if not EXISTING_PATH.exists():
        return by_num
    for line in EXISTING_PATH.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        num = str(r.get("decree_number"))
        by_num.setdefault(num, []).append(r)
    return by_num


def main() -> None:
    candidates = _content_verified_candidates()
    print(f"{len(candidates)} content-verified Mariupol land-grant PDFs in rasp/", file=sys.stderr)

    existing = _existing_by_number()
    print(f"{len(existing)} distinct decree numbers already in {EXISTING_PATH.name}", file=sys.stderr)

    flag_tally: Counter = Counter()
    clean = 0
    written = 0
    skipped_dupe = 0
    date_mismatches: list[str] = []
    seen_this_run: set[str] = set()

    with open(OUT_PATH, "w", encoding="utf-8") as out:
        for sha, url in candidates:
            text = (OCR_DIR / f"{sha}.txt").read_text(encoding="utf-8", errors="replace")
            rec = parse_ocr_text(text, sha, url)
            num = rec["decree_number"]

            if num in existing:
                ex_dates = {e.get("decree_date") for e in existing[num] if e.get("decree_date")}
                if rec["decree_date"] in ex_dates:
                    # Already present under this exact (number, date) -- a genuine
                    # duplicate, not new data.
                    skipped_dupe += 1
                    continue
                if ex_dates and rec["decree_date"]:
                    # Known dates for this number, none of which match this parse --
                    # given the filename-date fix, this decree number genuinely
                    # recurs across years (confirmed by checking source_document
                    # directly for a few of these, e.g. rasporiazhglavaN291_ exists
                    # for 2022/2023/2024) -- this is very likely a genuinely
                    # DIFFERENT decree, not a duplicate. Keep it rather than
                    # silently drop it, but flag loudly for a human to confirm.
                    date_mismatches.append(
                        f"№{num}: existing dates={sorted(ex_dates)} vs this-parse={rec['decree_date']} "
                        f"-- KEPT as likely-distinct")
                    rec["flags"].append("same_number_different_year_verify_manually")
                else:
                    skipped_dupe += 1
                    continue
            run_key = (num, rec["decree_date"])
            if run_key in seen_this_run:
                # Exact same (number, date) seen twice this run -- a genuine
                # re-capture, not a distinct decree (distinct decrees sharing a
                # number get distinct dates and so a distinct run_key).
                skipped_dupe += 1
                continue
            seen_this_run.add(run_key)

            if not rec["flags"]:
                clean += 1
            for f in rec["flags"]:
                flag_tally[f] += 1
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            written += 1
            print(f"  №{rec['decree_number']} ({rec['decree_date'] or '?'}): "
                  f"ben={rec['beneficiary_name']!r:.45} cad={rec['cadastral_numbers']} "
                  f"area={rec['area_sqm']} addr={rec['address_normalized']!r:.50} "
                  f"flags={rec['flags'] or 'none'}", file=sys.stderr)

    print(f"\nDone. {written} new records -> {OUT_PATH} "
          f"({skipped_dupe} skipped as already-known by decree_number)", file=sys.stderr)
    print(f"  clean (no flags): {clean}/{written}", file=sys.stderr)
    if flag_tally:
        print(f"  flags: {dict(flag_tally.most_common())}", file=sys.stderr)
    if date_mismatches:
        print(f"  DATE MISMATCHES (same decree number, different date between the two "
              f"parsers -- worth a manual check, not necessarily an error in either):",
              file=sys.stderr)
        for dm in date_mismatches:
            print(f"    {dm}", file=sys.stderr)


if __name__ == "__main__":
    main()
