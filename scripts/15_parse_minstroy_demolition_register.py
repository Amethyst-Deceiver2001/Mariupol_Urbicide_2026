#!/usr/bin/env python3
"""Stage 2e: parse DNR MinStroy Unified Demolition Register CSVs into structured records,
then run a crosswalk join against demolition_decrees.jsonl, ownerless_decrees.jsonl,
and dnr_land_orders.jsonl.

Reads source_type='minstroy_demolition_register_csv' from the forensics store.
Uses the most recent CSV version (by captured_at); earlier versions are kept in
the store for provenance but not re-parsed.

OUTPUT FILES
------------
  data/parsed/minstroy_demolition_register.jsonl
    One record per building row in the register. Fields:
      source_sha256, csv_version_date,
      order_reference_raw, order_authority, order_number, order_date,
      address_raw, address_city, address_street, address_building,
      building_type, district_raw, district_normalized, flags

  data/parsed/minstroy_crosswalk.jsonl
    Legal-grade linkage records joining the MinStroy register to other
    parsed sources. Each record represents ONE confirmed crosswalk hit:
      minstroy_address_raw, minstroy_order_reference,
      matched_source (demolition_decrees | ownerless_decrees | dnr_land_orders),
      matched_address_raw, match_score, match_method (exact | fuzzy),
      supporting_sources (list — ≥2 required for legal_grade=True),
      legal_grade (bool: score≥0.8 AND ≥2 independent sources),
      flags

TROIANDA-M SPECIFIC JOIN
------------------------
The MinStroy register contains 12 пр-т Ленина buildings under GKO №56 (rows 247–258,
Жовтневый district). ТСЖ «Троянда-М» is one of these. The crosswalk attempts to
identify which by joining the 12 candidates against:
  - dnr_land_orders.jsonl (РКС-Девелопмент parcel — address + area 3,136 m²)
  - demolition_decrees.jsonl (address_raw from OCR'd city administration decrees)

Chain of command confirmed once address is identified:
  GKO ДНР №56 (29.09.2022) → ТСЖ «Троянда-М» address → case 2-259/2025

Re-running is safe — output overwritten.
"""
from __future__ import annotations

import csv
import io
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
    from rapidfuzz import fuzz, process as rf_process
except ImportError:
    sys.exit("rapidfuzz not installed — run: .venv/bin/pip install rapidfuzz")


# ── regex patterns ────────────────────────────────────────────────────────────

# Order reference: "Распоряжение ГКО ДНР № 56 от 29.09.2022"
# or "Постановление администрации г. Мариуполя от 12.12.2022 № 144"
_ORDER_NUM = re.compile(r"№\s*(\d+[\w/-]*)")
_ORDER_DATE = re.compile(r"от\s+(\d{2}\.\d{2}\.\d{4})")
_ORDER_DATE_DOT = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")

# Issuing authority
_AUTHORITY_GKO = re.compile(r"ГКО\s+ДНР", re.I)
_AUTHORITY_MARIUPOL = re.compile(
    r"администрации?\s+(?:г\.?\s*)?(?:города?\s+)?Мариуполя?", re.I
)
_AUTHORITY_VOLNOVAKHA = re.compile(r"Волновахского", re.I)
_AUTHORITY_TELMAN = re.compile(r"Тельмановского", re.I)
_AUTHORITY_GORLOVKA = re.compile(r"Горловк", re.I)
_AUTHORITY_DONETSK = re.compile(r"городского\s+округа?\s+Донецк", re.I)
_AUTHORITY_DOKUCHAEVSK = re.compile(r"Докучаевск", re.I)

# Address: "г. Мариуполь, ул. Артема, д. 59-47 (Здание жилого дома)"
# Split off city, building type annotation, keep street+building
# "г.Мариуполь" (no space before the city name) is common -- \s* (not \s+).
_CITY = re.compile(r"^г\.?\s*([А-ЯЁа-яё]+(?:\s+[А-ЯЁа-яё]+)?)\s*,\s*", re.I)
# Some rows prefix a building-type description BEFORE "г. Мариуполь" instead
# of (or in addition to) the trailing "(...)" annotation, e.g.
# "МКД, г. Мариуполь, ул. X, д. 5" or "Торговый объект, г. Мариуполь, ул. X, 5".
_CITY_PREFIX = re.compile(r",\s*(г\.?\s*Мариуполь)\b", re.I)
_BUILDING_TYPE = re.compile(r"\(([^)]+)\)\s*$")
_BUILDING_NUM = re.compile(
    r"(?:д\.|дом)\s*([\d]+(?:[/-][\d\w]+)?(?:\s*[а-яёА-ЯЁ](?:-\d+)?)?)",
    re.I,
)
_ЖИЛОЙ_МАССИВ = re.compile(r"жилмассив\s+(\S+)", re.I)
# Fallback when there's no "д."/"дом" token: a bare trailing house number,
# optionally with a letter suffix, e.g. "бул. 50 лет Октября, 38" or "38 А".
_TRAILING_BARE_NUM = re.compile(r"(?:,\s*|\s)(\d+\s*[а-яёА-ЯЁ]?)\s*$")

# District normalization mapping
_DISTRICT_MAP = {
    "Жовтневого":        "Жовтневый",
    "Орджоникидзевского": "Орджоникидзевский",
    "Приморского":       "Приморский",
    "Ильичевского":      "Ильичевский",
    "Волновахского":     "Волновахский",
    "Горловка":          "Горловка",
    "Донецк":            "Донецк",
    "Докучаевск":        "Докучаевск",
    "Тельмановского":    "Тельмановский",
}


def _parse_dot_date(s: str) -> str | None:
    m = _ORDER_DATE_DOT.search(s)
    if not m:
        return None
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
    except ValueError:
        return None


def _parse_authority(ref: str) -> str:
    if _AUTHORITY_GKO.search(ref):
        return "ГКО ДНР"
    if _AUTHORITY_MARIUPOL.search(ref):
        return "Администрация г. Мариуполя"
    if _AUTHORITY_VOLNOVAKHA.search(ref):
        return "Администрация Волновахского района/округа"
    if _AUTHORITY_TELMAN.search(ref):
        return "Администрация Тельмановского района"
    if _AUTHORITY_GORLOVKA.search(ref):
        return "Администрация г. Горловка"
    if _AUTHORITY_DONETSK.search(ref):
        return "Администрация г.о. Донецк"
    if _AUTHORITY_DOKUCHAEVSK.search(ref):
        return "Администрация г.о. Докучаевск"
    return "unknown"


def _parse_district(district_raw: str) -> str | None:
    for key, norm in _DISTRICT_MAP.items():
        if key in district_raw:
            return norm
    return None


_ADDR_AFTER_COLON = re.compile(r"по\s+адресу\s*:\s*", re.I)


def _parse_address(addr_raw: str) -> dict:
    """Split raw address into city, street, building number, building type."""
    s = addr_raw.strip()

    # Some non-Mariupol rows start with a building description before the address:
    # "Здание ... по адресу: г. Докучаевск, ...".  Strip that prefix so city parses.
    colon_m = _ADDR_AFTER_COLON.search(s)
    if colon_m:
        s = s[colon_m.end():].strip()

    # Some rows have a building-type description before "г. Мариуполь" with no
    # "по адресу:" marker, e.g. "МКД, г. Мариуполь, ..." or "Торговый объект,
    # г. Мариуполь, ...". Drop everything up to "г.Мариуполь"/"г. Мариуполь".
    prefix_m = _CITY_PREFIX.search(s)
    if prefix_m:
        s = s[prefix_m.start(1):]

    # Building type annotation at end "(Здание жилого дома)" etc.
    bt_m = _BUILDING_TYPE.search(s)
    building_type = bt_m.group(1).strip() if bt_m else None
    if bt_m:
        s = s[:bt_m.start()].strip().rstrip(",")

    # City
    city_m = _CITY.match(s)
    city = city_m.group(1) if city_m else None
    if city_m:
        s = s[city_m.end():].strip()

    # Building number
    bn_m = _BUILDING_NUM.search(s)
    building_number = None
    if bn_m:
        building_number = bn_m.group(1).strip()
        # Street is everything before "д." token
        street = s[:bn_m.start()].strip().rstrip(",")
    else:
        # жилмассив form: no "д." token
        jm = _ЖИЛОЙ_МАССИВ.search(s)
        if jm:
            bn_inner = _BUILDING_NUM.search(s[jm.end():])
            if bn_inner:
                building_number = bn_inner.group(1).strip()
            street = s
        else:
            # Fallback: bare trailing house number, no "д."/"дом" token, e.g.
            # "бул. 50 лет Октября, 38" (common for "Торговый объект, ..." rows).
            tb_m = _TRAILING_BARE_NUM.search(s)
            if tb_m:
                building_number = tb_m.group(1).strip()
                street = s[:tb_m.start()].strip().rstrip(",")
            else:
                street = s

    street = re.sub(r"\s+", " ", street).strip().rstrip(",")

    return {
        "address_city": city,
        "address_street": street or None,
        "address_building": building_number,
        "building_type": building_type,
    }


def parse_register_row(row: list[str], source_sha256: str, csv_version_date: str | None) -> dict:
    """Parse one CSV row into a structured demolition register record."""
    flags: list[str] = []

    if len(row) < 4:
        flags.append("row_too_short")
        row = row + [""] * (4 - len(row))

    order_ref_raw = re.sub(r"\s+", " ", row[1]).strip()
    address_raw = re.sub(r"\s+", " ", row[2]).strip()
    district_raw = re.sub(r"\s+", " ", row[3]).strip()

    # Order reference parsing
    order_authority = _parse_authority(order_ref_raw)
    order_num_m = _ORDER_NUM.search(order_ref_raw)
    order_number = order_num_m.group(1).strip() if order_num_m else None
    order_date_m = _ORDER_DATE.search(order_ref_raw)
    order_date = _parse_dot_date(order_date_m.group(1)) if order_date_m else None

    if not order_number:
        flags.append("order_number_missing")
    if not order_date:
        flags.append("order_date_missing")
    if order_authority == "unknown":
        flags.append("order_authority_unknown")

    # Address parsing
    addr_parts = _parse_address(address_raw)
    if not addr_parts["address_city"]:
        flags.append("city_missing")
    if not addr_parts["address_building"]:
        flags.append("building_number_missing")

    # District
    district_normalized = _parse_district(district_raw)
    if not district_normalized:
        flags.append("district_unrecognized")

    return {
        "source_sha256": source_sha256,
        "csv_version_date": csv_version_date,
        "order_reference_raw": order_ref_raw,
        "order_authority": order_authority,
        "order_number": order_number,
        "order_date": order_date,
        "address_raw": address_raw,
        **addr_parts,
        "district_raw": district_raw,
        "district_normalized": district_normalized,
        "flags": flags,
    }


# ── cross walk join ───────────────────────────────────────────────────────────

def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return out


_BLDG_NUM_EXTRACT = re.compile(r"(?:д\.|дом)\s*([\d]+)", re.I)
# Fallback: bare trailing number for commercial entries like "ул. Куприна, 2" or "77 Б"
_BLDG_NUM_BARE = re.compile(r"(?:,\s*|\s)(\d+)\s*[а-яё]?\s*$", re.I)


def _canonical_address(raw: str) -> str:
    """Strip city prefix, building type annotations, extra spaces for comparison."""
    s = re.sub(r"\s+", " ", raw).strip()
    s = re.sub(r"г\.?\s*Мариуполь,?\s*", "", s, flags=re.I)
    s = re.sub(r"\([^)]+\)\s*$", "", s).strip().rstrip(",")
    s = re.sub(r"\s+", " ", s).strip()
    return s.lower()


def _extract_bldg_num(canon: str) -> str | None:
    """Return building number for same-building verification.

    Tries д./дом prefix first; falls back to trailing bare number for
    commercial entries like 'ул. Куприна, 2'.
    """
    m = _BLDG_NUM_EXTRACT.search(canon)
    if m:
        return m.group(1)
    m = _BLDG_NUM_BARE.search(canon)
    return m.group(1) if m else None


def run_crosswalk(
    register: list[dict],
    other_sources: dict[str, list[dict]],
    fuzzy_threshold: float = 80.0,
) -> list[dict]:
    """Join register addresses to other sources; return legal-grade linkage records.

    Matching strategy (in order):
      1. Exact canonical string match → score 100, method 'exact'
      2. token_set_ratio ≥ threshold AND building numbers equal (or one side has no number)
         → method 'fuzzy'

    token_set_ratio is used (not sort_ratio) because ownerless records include extra
    tokens like «кв.7» that are not in the MinStroy building-level addresses. token_set_ratio
    scores the intersection of token sets, so extra tokens don't penalise the score.

    Building-number equality is required when both sides have one, to prevent
    street-only false positives (e.g. Мамина-Сибиряка 36 ≠ 43).

    legal_grade: score ≥ 80 AND ≥ 2 independent sources.
    """
    hits: list[dict] = []

    # Strip apartment suffix from ownerless records before indexing — they are
    # apartment-level but we match at building level.
    _APT_SUFFIX = re.compile(r",?\s*кв\.?\s*\d+.*$", re.I)

    indices: dict[str, dict[str, list[dict]]] = {}
    for source_name, records in other_sources.items():
        addr_field = "address_raw" if source_name != "dnr_land_orders" else "address_normalized"
        idx: dict[str, list[dict]] = {}
        for rec in records:
            raw = rec.get(addr_field) or rec.get("address_raw") or ""
            if not raw:
                continue
            if source_name == "ownerless_decrees":
                raw = _APT_SUFFIX.sub("", raw).strip().rstrip(",")
            key = _canonical_address(raw)
            # Reject OCR garbage — a real street+building address has ≥10 chars
            # and at least one letter (street name) plus one digit (building number).
            if len(key) < 10 or not re.search(r"[а-яёa-z]", key) or not re.search(r"\d", key):
                continue
            idx.setdefault(key, []).append(rec)
        indices[source_name] = idx

    addr_lists: dict[str, list[str]] = {
        name: list(idx.keys()) for name, idx in indices.items()
    }

    for reg_rec in register:
        if reg_rec.get("address_city") not in (None, "Мариуполь"):
            continue

        canon = _canonical_address(reg_rec["address_raw"])
        if not canon:
            continue

        reg_bldg = _extract_bldg_num(canon)
        source_hits: dict[str, dict] = {}

        for source_name, addrs in addr_lists.items():
            if not addrs:
                continue

            if canon in indices[source_name]:
                for matched_rec in indices[source_name][canon]:
                    source_hits[source_name] = {
                        "matched_address_raw": matched_rec.get("address_raw", ""),
                        "match_score": 100.0,
                        "match_method": "exact",
                        "matched_record": matched_rec,
                    }
                continue

            # Fuzzy: token_set_ratio handles extra tokens (apt numbers) gracefully.
            # Building-number equality guards against street-only matches.
            best = rf_process.extractOne(
                canon, addrs,
                scorer=fuzz.token_set_ratio,
                score_cutoff=fuzzy_threshold,
            )
            if best:
                matched_canon, score, _ = best
                matched_bldg = _extract_bldg_num(matched_canon)
                # Reject if both sides have building numbers and they differ
                if reg_bldg and matched_bldg and reg_bldg != matched_bldg:
                    continue
                for matched_rec in indices[source_name][matched_canon]:
                    source_hits[source_name] = {
                        "matched_address_raw": matched_rec.get("address_raw", ""),
                        "match_score": float(score),
                        "match_method": "fuzzy",
                        "matched_record": matched_rec,
                    }
                    break

        if not source_hits:
            continue

        supporting = list(source_hits.keys())
        best_score = max(v["match_score"] for v in source_hits.values())
        legal_grade = best_score >= 80.0 and len(supporting) >= 2

        hit = {
            "minstroy_address_raw": reg_rec["address_raw"],
            "minstroy_order_reference": reg_rec["order_reference_raw"],
            "minstroy_order_number": reg_rec["order_number"],
            "minstroy_order_date": reg_rec["order_date"],
            "minstroy_district": reg_rec["district_normalized"],
            "supporting_sources": supporting,
            "best_match_score": best_score,
            "legal_grade": legal_grade,
            "matches": {
                name: {
                    "matched_address_raw": info["matched_address_raw"],
                    "match_score": info["match_score"],
                    "match_method": info["match_method"],
                }
                for name, info in source_hits.items()
            },
            "flags": [] if legal_grade else (
                ["score_below_threshold"] if best_score < 80.0 else ["single_source_only"]
            ),
        }
        hits.append(hit)

    return hits


# ── Троянда-М specific: пр-т Ленина under №56 vs dnr_land_orders ─────────────

def troianda_candidate_analysis(
    register: list[dict],
    land_orders: list[dict],
) -> None:
    """Log the best address match between the 12 пр-т Ленина №56 candidates
    and РКС-Девелопмент land orders, to identify the Троянда-М building."""
    candidates = [
        r for r in register
        if r.get("order_number") == "56"
        and r.get("district_normalized") == "Жовтневый"
        and r.get("address_street") and "Ленина" in (r.get("address_street") or "")
    ]
    if not candidates:
        log.warning("Troianda analysis: no пр-т Ленина №56 candidates found in register")
        return

    rks_orders = [
        lo for lo in land_orders
        if lo.get("beneficiary_name") and (
            "РКС" in lo.get("beneficiary_name", "")
            or "Новое время" in lo.get("beneficiary_name", "")
        )
    ]

    log.info("Troianda-М candidate analysis:")
    log.info("  %d пр-т Ленина buildings under №56 (Жовтневый)", len(candidates))
    log.info("  %d РКС/Новое время land orders in dnr_land_orders.jsonl", len(rks_orders))

    if not rks_orders:
        log.warning("  No РКС/Новое время orders found — load dnr_land_orders.jsonl first.")
        for c in candidates:
            log.info("    candidate: %s", c["address_raw"])
        return

    for lo in rks_orders:
        addr_norm = lo.get("address_normalized") or lo.get("address_raw") or ""
        area = lo.get("area_sqm")
        project = lo.get("project_name") or ""
        cadastrals = lo.get("cadastral_numbers") or []
        log.info("  RKS order №%s (%s): project=%r area=%s m² cadastrals=%s",
                 lo.get("decree_number"), lo.get("decree_date"), project, area, cadastrals)
        log.info("    addr=%r", addr_norm[:120])
        if addr_norm:
            # For territorial descriptions spanning two avenues, check all candidates
            # against both the full address and each avenue name individually.
            for c in candidates:
                c_canon = _canonical_address(c["address_raw"])
                score_full = fuzz.token_sort_ratio(c_canon, _canonical_address(addr_norm))
                # Check if candidate street appears in the land order address
                street = (c.get("address_street") or "").lower()
                street_in_order = street and street in addr_norm.lower()
                if score_full >= 50 or street_in_order:
                    log.info("    candidate (score=%d, street_in_order=%s): %s",
                             score_full, street_in_order, c["address_raw"])
        log.info("    IDENTIFICATION: if project «%s» is the Троянда-М replacement, "
                 "the original building is one of the %d пр-т Ленина candidates above. "
                 "Search ЕИСЖС / наш.дом.рф for «%s» to find the new address, "
                 "then back-trace cadastrals %s to the old address.",
                 project, len(candidates), project, cadastrals)


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    con = forensics.open_state()

    sources = con.execute(
        """SELECT sha256, raw_path, title, captured_at
           FROM source_document
           WHERE source_type = 'minstroy_demolition_register_csv'
             AND http_status = 200"""
    ).fetchall()

    if not sources:
        log.warning(
            "No minstroy_demolition_register_csv in store — "
            "run 14_crawl_minstroy_demolition_register.py first."
        )
        return

    # Pick the version with the most recent date embedded in its title.
    # Do NOT sort by captured_at — the crawler writes files in reverse order
    # (current→older) so the original ends up with the latest captured_at.
    def _version_date_key(row):
        title = row[2]
        m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", title)
        if m:
            try:
                return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            except ValueError:
                pass
        return date(2000, 1, 1)  # "оригинал" titles with no date sort last

    best_sha, best_path, best_title, best_ts = max(sources, key=_version_date_key)
    log.info("Parsing: %s (captured %s)", best_title[:80], best_ts)

    p = Path(best_path)
    if not p.exists():
        log.error("Raw file missing on disk: %s", best_path)
        return

    raw_bytes = p.read_bytes()
    text = raw_bytes.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text), delimiter=";")
    all_rows = list(reader)

    header = all_rows[0] if all_rows else []
    data_rows = all_rows[1:]
    log.info("Header: %s", header)
    log.info("Data rows: %d", len(data_rows))

    # Extract version date from title (e.g. "… — 16.03.2026")
    vd_m = re.search(r"(\d{2}\.\d{2}\.\d{4})", best_title)
    csv_version_date = _parse_dot_date(vd_m.group(1)) if vd_m else None

    out_dir = config.PROJECT_ROOT / "data" / "parsed"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "minstroy_demolition_register.jsonl"

    records: list[dict] = []
    flag_tally: Counter = Counter()

    with out_path.open("w", encoding="utf-8") as fh:
        for row in data_rows:
            if not any(cell.strip() for cell in row):
                continue  # skip blank rows
            rec = parse_register_row(row, best_sha, csv_version_date)
            records.append(rec)
            for f in rec["flags"]:
                flag_tally[f] += 1
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    clean = sum(1 for r in records if not r["flags"])
    mariupol = sum(1 for r in records if r.get("address_city") == "Мариуполь")
    gko56 = sum(1 for r in records
                if r.get("order_authority") == "ГКО ДНР" and r.get("order_number") == "56")

    log.info("done — %d records written to %s", len(records), out_path)
    log.info("  clean (no flags): %d / %d", clean, len(records))
    log.info("  Mariupol addresses: %d", mariupol)
    log.info("  GKO №56 entries: %d", gko56)
    if flag_tally:
        log.info("  flags: %s", dict(flag_tally.most_common()))

    # ── crosswalk join ─────────────────────────────────────────────────────────
    parsed_dir = config.PROJECT_ROOT / "data" / "parsed"
    other_sources: dict[str, list[dict]] = {}
    for name, filename in [
        ("demolition_decrees",  "demolition_decrees.jsonl"),
        ("ownerless_decrees",   "ownerless_decrees.jsonl"),
        ("dnr_land_orders",     "dnr_land_orders.jsonl"),
    ]:
        recs = _load_jsonl(parsed_dir / filename)
        if recs:
            log.info("crosswalk: loaded %d records from %s", len(recs), filename)
            other_sources[name] = recs
        else:
            log.info("crosswalk: %s not found or empty — skipping that source", filename)

    if other_sources:
        hits = run_crosswalk(records, other_sources)
        legal_hits = [h for h in hits if h["legal_grade"]]

        xwalk_path = out_dir / "minstroy_crosswalk.jsonl"
        with xwalk_path.open("w", encoding="utf-8") as fh:
            for hit in hits:
                fh.write(json.dumps(hit, ensure_ascii=False) + "\n")

        log.info("crosswalk: %d total hits, %d legal-grade (≥2 sources + score≥80)",
                 len(hits), len(legal_hits))
        log.info("  written to %s", xwalk_path)

        # Summary by order
        order_hit_counts: Counter = Counter()
        for h in legal_hits:
            order_hit_counts[h.get("minstroy_order_reference", "?")[:60]] += 1
        for ref, count in order_hit_counts.most_common(10):
            log.info("    %3d hits — %s", count, ref)

        # Troianda-M address identification
        land_orders = other_sources.get("dnr_land_orders", [])
        troianda_candidate_analysis(records, land_orders)
    else:
        log.info("crosswalk: no other parsed sources available yet — "
                 "run 09_parse_demolition_decrees.py, 06_parse_ownerless_decrees.py, "
                 "11_parse_dnr_land_orders.py first to enable joining.")


if __name__ == "__main__":
    main()
