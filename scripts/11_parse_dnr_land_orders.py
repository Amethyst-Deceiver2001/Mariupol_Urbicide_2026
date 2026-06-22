#!/usr/bin/env python3
"""Stage 2d: parse DNR head's land-allocation распоряжения into structured records.

Reads source_type='dnr_land_order' HTML captures produced by
scripts/10_crawl_dnr_land_orders.py and extracts:

  decree_number | decree_date | issuing_body | beneficiary_name
  | beneficiary_ogrn | beneficiary_inn | cadastral_numbers (list)
  | area_sqm | address_raw | address_normalized | project_name
  | legal_basis | signing_official | flags

Each record is the RIGHT-HAND side of the demolish→rebuild crosswalk:
  demolition_decrees.jsonl (old address, condemned building)
  ↕  rapidfuzz address match (≥0.8) or cadastral join
  THIS FILE (beneficiary + parcel)
  ↕  ЕИСЖС / наш.дом.рф
  new building registered under new address

The DNR portal stores full decree text in div.post-content (WordPress theme).
Two structural forms appear:
  - DIRECT (2023): "О предоставлении [COMPANY] земельного участка ..."
  - PROPOSAL (2026): "Принять предложение ... и [COMPANY] о предоставлении
    указанному юридическому лицу ..."
  - IMPERATIVE (2026): "Предоставить [COMPANY] в аренду ..."

Output: data/parsed/dnr_land_orders.jsonl — one record per decree.
Re-running is safe (output overwritten).
"""
from __future__ import annotations

import json
import logging
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

try:
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit("beautifulsoup4 not installed — run: pip install beautifulsoup4 lxml")

try:
    from rapidfuzz import fuzz as _rfuzz
    _HAS_RAPIDFUZZ = True
except ImportError:
    _HAS_RAPIDFUZZ = False


def _build_inn_lookup() -> dict[str, tuple[str, str]]:
    """Load ЕИСЖС parsed objects → {canonical_name: (inn, full_name)} for name-fallback."""
    eisghs_path = config.PROJECT_ROOT / "data" / "parsed" / "eisghs_mariupol_objects.jsonl"
    lookup: dict[str, tuple[str, str]] = {}
    if not eisghs_path.exists():
        return lookup
    for line in eisghs_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        inn = obj.get("dev_inn")
        name_full = obj.get("dev_name_full") or ""
        name_short = obj.get("dev_name_short") or ""
        if not inn:
            continue
        for name in (name_full, name_short):
            if not name:
                continue
            key = re.sub(r"[«»\"\'\-]", " ", name).upper()
            key = re.sub(r"\s+", " ", key).strip()
            if key not in lookup:
                lookup[key] = (inn, name)
    return lookup


_INN_LOOKUP: dict[str, tuple[str, str]] = {}   # populated lazily in main()

# Manual INN overrides for companies not in ЕИСЖС.
# Populated from scripts/20_lookup_egrul.py results after human verification.
# Format: {beneficiary_name_substring (case-insensitive): inn}
MANUAL_INN_OVERRIDES: dict[str, str] = {
    # EGRUL-verified via egrul.org (data/parsed/egrul_inn_lookups.jsonl), inn_match=True.
    "СГМ МОНТАЖ": "9310018029",                    # ООО "СГМ МОНТАЖ"
    "МИРАСТРОЙ 3": "9303036524",                   # ООО "СЗ "МИРАСТРОЙ 3"
    "МИРАСТРОЙ 4": "9303036531",                   # ООО "СЗ "МИРАСТРОЙ 4"
    "НОВОЕ ВРЕМЯ 3": "9309028294",                 # ООО СЗ "НОВОЕ ВРЕМЯ 3"
    "ЭВЕРЕСТ ДОМОСТРОЕНИЕ": "9303042743",          # АО "ЭВЕРЕСТ ДОМОСТРОЕНИЕ"
    "ОЛИМПСТРОЙ НР": "9309027678",                 # ООО "СЗ ОЛИМПСТРОЙ НР"
    "ВОСХОД": "9310013976",                        # ООО "СЗ "ВОСХОД""
    "АНТАРЕС": "9310014480",                       # ООО "СЗ "АНТАРЕС""
}

# Strip boilerplate org-type prefix before fuzzy matching so that "ВОСХОД" vs
# "РКС ДЕВЕЛОПМЕНТ" scores near 0 rather than falsely matching via the shared
# "СПЕЦИАЛИЗИРОВАННЫЙ ЗАСТРОЙЩИК" prefix (token_set_ratio inflates scores when
# the intersection covers most of one string).
_ORG_PREFIX_STRIP = re.compile(
    r"^(?:СПЕЦИАЛИЗИРОВАННЫЙ\s+ЗАСТРОЙЩИК(?:\s*[\-\s]\s*\d+)?\s*|"
    r"СЗ\s+(?:\d+\s+)?|ООО\s+|АО\s+|ПАО\s+)+",
    re.I,
)


def _inn_from_name(beneficiary: str) -> tuple[str | None, float]:
    """Fuzzy-match beneficiary name against ЕИСЖС lookup → (inn, score) or (None, 0)."""
    if not _HAS_RAPIDFUZZ or not _INN_LOOKUP or not beneficiary:
        return None, 0.0
    query = re.sub(r"[«»\"\'\-]", " ", beneficiary).upper()
    query = re.sub(r"\s+", " ", query).strip()
    # Strip boilerplate prefix — match on the distinctive identifier only.
    query_d = _ORG_PREFIX_STRIP.sub("", query).strip() or query
    best_score = 0.0
    best_inn = None
    for key, (inn, _full) in _INN_LOOKUP.items():
        score = _rfuzz.token_set_ratio(query_d, key)
        if score > best_score:
            best_score = score
            best_inn = inn
    if best_score >= 88.0:
        return best_inn, best_score
    return None, best_score


# ── regex patterns ─────────────────────────────────────────────────────────────

# Date signed / published at the top of div.post-content
_DATE_SIGNED = re.compile(r"Дата\s+подписания\s+(\d{2}\.\d{2}\.\d{4})", re.I)

# Decree number — prefer the one at the bottom ("№ 161\n2026") but fall back
# to the page title regex
_DECREE_NO_TEXT = re.compile(r"№\s*(\d[\d-]*)")

# Signing official: "Д. В. Пушилин" at end
_SIGNER = re.compile(r"Глава\s+Донецкой\s+Народной\s+Республики\s+([А-ЯЁ]\.\s*[А-ЯЁ]\.\s+[А-ЯЁ][а-яё]+)", re.I)
# Acting head form: "врио Главы"
_SIGNER_VRIO = re.compile(r"врио\s+Главы\s+.{0,30}?\s+([А-ЯЁ]\.\s*[А-ЯЁ]\.\s+[А-ЯЁ][а-яё]+)", re.I)

# Issuing body: ГЛАВА / ПРАВИТЕЛЬСТВО in all-caps header
_BODY_GLAVA = re.compile(r"ГЛАВА\s+ДОНЕЦКОЙ\s+НАРОДНОЙ\s+РЕСПУБЛИКИ", re.I)
_BODY_GOVT  = re.compile(r"ПРАВИТЕЛЬСТВО\s+ДОНЕЦКОЙ\s+НАРОДНОЙ\s+РЕСПУБЛИКИ", re.I)

# Org-type keywords in various grammatical cases — anchor for beneficiary search
_ORG_ANCHOR = re.compile(
    r"(?:акционерн\w+\s+обществ\w+"
    r"|обществ\w+\s+с\s+ограниченн\w+\s+ответственность\w+"
    r"|ООО|АО|ПАО)\s*«",
    re.I,
)
# Known clause transitions that follow the company name
_BEN_TERM = re.compile(
    r"\s*(?:о\s+предоставлении|в\s+аренду|земельн\w+\s+участ"
    r"|,\s*(?:ОГРН|ИНН|\()|\(ОГРН)",
    re.I,
)

# ОГРН and ИНН (sometimes in parentheses after company name)
_OGRN = re.compile(r"ОГРН\s+(\d{13,15})")
_INN  = re.compile(r"ИНН\s+(\d{10,12})")

# Cadastral numbers (all of them — some orders cover multiple parcels)
_CADASTRAL = re.compile(r"93:\d+:\d+:\d+")

# Area: "17 552+/-46 м 2" or "3501 м 2" — spaces are thousands separators
_AREA = re.compile(r"([\d][\d\s]{0,9})\s*(?:\+/?-?[\d\s]*)?\s*м\s*2", re.I)

# Address block: after "по адресу:" up to ", находящ" or end of clause.
# Fallback pattern for territorial descriptions: "(территория ограничена ...)"
_ADDRESS_BLOCK = re.compile(
    r"по\s+адресу\s*:\s*(.*?)(?=,\s*находящ|,\s*для\s+реализации|\.\s|\Z)",
    re.S | re.I,
)
_ADDRESS_TERRITORY = re.compile(
    r"в\s+город[еа]\s+Мариуполе?\s*"
    r"(\(территория\s+ограничена[^)]{5,200}\))",
    re.I,
)
# Boilerplate prefix to strip from address.
# Use \s* (not \s+) on the last component so it also strips when the
# boilerplate fills the entire captured block (no street follows).
_ADDR_BOILERPLATE = re.compile(
    r"^Российская\s+Федерация,?\s+Донецкая?\s+Народная?\s+Республика,?\s+"
    r"(?:городской\s+округ\s+Мариуполь,?\s+)?"
    r"(?:город\s+Мариуполь,?\s*)?",
    re.I,
)

# Investment project name
_PROJECT = re.compile(r"инвестиционного\s+проекта\s+«([^»]+)»", re.I)

# Legal basis citations
_LEGAL_BASIS = re.compile(
    r"(?:подпункт\w*\s+\d+\s+пункт\w*\s+\d+\s+стать\w+\s+[\d.]+\s+Земельного\s+кодекса"
    r"|Закон\w*\s+Донецкой[^,]+№\s+[\w-]+)",
    re.I,
)

_DATE_DOT = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")


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
    """Extract the beneficiary company name from decree text.

    Handles nested guillemets («outer «inner»») and unclosed outer guillemets,
    which are common in Russian legal typesetting for SPV names.
    Strategy: find the org-type keyword + opening guillemet, then scan forward
    to the nearest clause terminator and truncate there.
    """
    m = _ORG_ANCHOR.search(text)
    if not m:
        return None
    start = m.end()  # position just after the opening «
    term = _BEN_TERM.search(text, start)
    end = term.start() if term else min(start + 120, len(text))
    candidate = text[start:end].strip()
    # If no nested guillemet, strip the trailing outer closing guillemet.
    # If there IS a nested «inner», keep the final » — it closes the inner
    # pair and is part of the registered name (e.g. «Специализированный
    # застройщик-1 «Порфир»).
    if candidate.endswith("»") and "«" not in candidate:
        candidate = candidate[:-1].strip()
    return candidate if len(candidate) > 2 else None


def parse_order_html(html: bytes, source_sha256: str, title: str) -> dict:
    """Parse a single DNR land-order HTML page into a structured record."""
    soup = BeautifulSoup(html, "lxml")
    el = soup.select_one("div.post-content")
    text = el.get_text(" ", strip=True) if el else soup.get_text(" ", strip=True)

    flags: list[str] = []

    # Date
    dm = _DATE_SIGNED.search(text)
    decree_date = _parse_dot_date(dm.group(1)) if dm else None

    # Decree number from title (most reliable)
    nm = _DECREE_NO_TEXT.search(title)
    decree_number = nm.group(1) if nm else None

    # Issuing body
    if _BODY_GOVT.search(text):
        issuing_body = "Правительство ДНР"
    elif _SIGNER_VRIO.search(text):
        issuing_body = "врио Главы ДНР"
    else:
        issuing_body = "Глава ДНР"

    # Signing official
    sm = _SIGNER.search(text) or _SIGNER_VRIO.search(text)
    signing_official = sm.group(1).strip() if sm else None

    # Beneficiary
    beneficiary = _find_beneficiary(text)
    if not beneficiary:
        flags.append("beneficiary_missing")

    # ОГРН / ИНН — direct extraction first; name-lookup fallback for 2024-2025 decrees
    # that omit registration numbers from both HTML and PDF.
    om = _OGRN.search(text)
    im = _INN.search(text)
    ogrn = om.group(1) if om else None
    inn  = im.group(1) if im else None
    inn_source = "decree_text" if inn else None

    if not inn and beneficiary:
        # Check manual overrides (EGRUL-verified, human-confirmed) first.
        ben_upper = beneficiary.upper()
        for substr, override_inn in MANUAL_INN_OVERRIDES.items():
            if substr.upper() in ben_upper:
                inn = override_inn
                inn_source = "manual_override"
                flags.append("inn_source_manual_override")
                break

    if not inn and beneficiary:
        inn_fuzzy, inn_score = _inn_from_name(beneficiary)
        if inn_fuzzy:
            inn = inn_fuzzy
            inn_source = f"eisghs_name_fuzzy:{inn_score:.0f}"
            flags.append(f"inn_source_name_fuzzy:{inn_score:.0f}")

    # Cadastral numbers (list — some orders cover multiple parcels)
    cadastrals = list(dict.fromkeys(_CADASTRAL.findall(text)))
    if not cadastrals:
        flags.append("cadastral_missing")

    # Area
    am = _AREA.search(text)
    area_sqm = _parse_area(am.group(1)) if am else None
    if area_sqm is None:
        flags.append("area_missing")

    # Address — standard "по адресу:" form first; territorial description fallback
    adm = _ADDRESS_BLOCK.search(text)
    address_raw = adm.group(1).strip() if adm else None
    address_norm = _strip_boilerplate(address_raw) if address_raw else None
    if not address_norm:
        # Some 2023 orders describe location as "(территория ограничена ...)"
        tm = _ADDRESS_TERRITORY.search(text)
        if tm:
            address_raw = tm.group(0).strip()
            address_norm = tm.group(1).strip()
    if not address_norm:
        flags.append("address_missing")

    # Project name
    pm = _PROJECT.search(text)
    project_name = pm.group(1).strip() if pm else None

    # Legal basis citations
    legal_basis = list(dict.fromkeys(
        re.sub(r"\s+", " ", m.group(0)).strip()
        for m in _LEGAL_BASIS.finditer(text)
    ))

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
        "legal_basis": legal_basis,
        "flags": flags,
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    con = forensics.open_state()
    sources = con.execute(
        """SELECT sha256, raw_path, title
           FROM source_document
           WHERE source_type = 'dnr_land_order'
           ORDER BY title"""
    ).fetchall()

    if not sources:
        log.warning("No dnr_land_order sources in store — run 10_crawl_dnr_land_orders.py first.")
        return

    global _INN_LOOKUP
    _INN_LOOKUP = _build_inn_lookup()
    if _INN_LOOKUP:
        log.info("INN lookup loaded: %d ЕИСЖС developer entries", len(_INN_LOOKUP))
    else:
        log.warning("INN lookup empty — eisghs_mariupol_objects.jsonl not found; "
                    "run scripts/18 first for name-fallback INN resolution")

    out_dir = config.PROJECT_ROOT / "data" / "parsed"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "dnr_land_orders.jsonl"

    total = clean_total = 0
    flag_tally: Counter = Counter()

    with out_path.open("w", encoding="utf-8") as fh:
        for sha, raw_path, title in sources:
            p = Path(raw_path)
            if not p.exists():
                log.error("raw file missing: %s", raw_path)
                continue
            try:
                rec = parse_order_html(p.read_bytes(), sha, title)
            except Exception:
                log.exception("failed to parse %s", raw_path)
                continue

            if not rec["flags"]:
                clean_total += 1
            for f in rec["flags"]:
                flag_tally[f] += 1

            preview = (
                f"ben={rec['beneficiary_name'] or '?'!r:.40} "
                f"cad={rec['cadastral_numbers']} "
                f"area={rec['area_sqm']} "
                f"addr={rec['address_normalized'] or '?'!r:.40}"
            )
            log.info("decree №%s (%s): %s | flags=%s",
                     rec["decree_number"] or "?",
                     rec["decree_date"] or "?",
                     preview,
                     rec["flags"] or "none")

            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            total += 1

    log.info("done — %d records written to %s", total, out_path)
    log.info("  clean (no flags): %d / %d", clean_total, total)
    if flag_tally:
        log.info("  flags: %s", dict(flag_tally.most_common()))


if __name__ == "__main__":
    main()
