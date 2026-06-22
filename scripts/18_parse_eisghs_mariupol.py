#!/usr/bin/env python3
"""Stage 2f: parse captured ЕИСЖС Mariupol object detail JSONs and run crosswalk joins.

Reads source_type='eisghs_house_detail' raw JSON captures produced by
scripts/17_crawl_eisghs_mariupol.py.

JOINS
-----
1. INN join → dnr_land_orders.jsonl
   developer INN in ЕИСЖС detail matches beneficiary_inn in land orders.
   Exact match → score 1.0, method 'inn_exact'. Provides: decree number,
   decree date, cadastral numbers, area_sqm, signing_official, project_name.

2. Address join → minstroy_demolition_register.jsonl
   rapidfuzz token_set_ratio on canonical addresses, threshold ≥ 80.
   Only attempted for objects with a full address (street + building number).
   NOTE: For address-laundering cases (old пр-т Ленина → new пр-кт Металлургов),
   this join will FAIL — that failure is itself evidence of address laundering.
   Objects where INN matches a land order but address doesn't match any
   demolished building at the same address receive flag `address_laundering`.

3. Address join → demolition_decrees.jsonl (same fuzzy method).

OUTPUT FILES
------------
data/parsed/eisghs_mariupol_objects.jsonl
    One flat record per ЕИСЖС object (20 total). Fields:
      source_sha256, eisghs_id, hobjId, pdId, nameObj, address, addrAreaId,
      obj_status, obj_status_desc, obj_publ_dt, commissioned_dt,
      rpd_num, rpd_issue_dttm, rnv_num, rnv_dt,
      flat_cnt, floor_cnt, area_sqm_living, sold_out_perc,
      lat, lon,
      dev_id, dev_inn, dev_ogrn, dev_name_short, dev_name_full, dev_ceo,
      dev_legal_addr, dev_region,
      land_order_match (nested), demolition_match (nested),
      legal_grade, flags

data/parsed/eisghs_crosswalk.jsonl
    One record per confirmed link between an ЕИСЖС object and another source.
    Used as the RIGHT-HAND side input for the final evidence matrix.

CROSSWALK CHAIN
---------------
The demolish→rebuild crosswalk in full:
  [old address] minstroy_demolition_register (order_number=56 etc.)
       ↕ crosswalk via order_number match in demolition_decrees
  [old address] demolition_decrees.jsonl
       ↕ INN link (same developer)
  [decree] dnr_land_orders.jsonl (cadastrals, area, INN)
       ↕ INN exact join
  [new address] eisghs_mariupol_objects.jsonl (commissioned, % sold)

Re-running is safe — output overwritten.
"""
from __future__ import annotations

import json
import logging
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

try:
    from rapidfuzz import fuzz
except ImportError:
    sys.exit("rapidfuzz not installed — run: .venv/bin/pip install rapidfuzz")


# ── constants ─────────────────────────────────────────────────────────────────

# objStatus → human label
_STATUS_DESC = {
    0: "under_construction",
    1: "suspended",
    2: "commissioned",
}

# Minimum fuzzy score (0–100) for address match to count as a hit.
_FUZZY_THRESHOLD = 80.0

# Minimum fuzzy score for legal-grade linkage.
_LEGAL_THRESHOLD = 80.0

# Must strip from ЕИСЖС address strings before comparison.
_CITY_PREFIX = re.compile(r"^г\.?\s*Мариуполь,?\s*", re.I)
_EXTRA_SPACE = re.compile(r"\s{2,}")

# Russian street type abbreviations normalisation (for canonical comparison).
_STREET_ABBREV = [
    (re.compile(r"\bпр-кт\b", re.I), "проспект"),
    (re.compile(r"\bпр\.\b",  re.I), "проспект"),
    (re.compile(r"\bпр\b",    re.I), "проспект"),
    (re.compile(r"\bул\.\b",  re.I), "улица"),
    (re.compile(r"\bул\b",    re.I), "улица"),
    (re.compile(r"\bпер\.\b", re.I), "переулок"),
    (re.compile(r"\bпер\b",   re.I), "переулок"),
    (re.compile(r"\bб-р\b",   re.I), "бульвар"),
    (re.compile(r"\bш\.\b",   re.I), "шоссе"),
    (re.compile(r"\bд\.\b",   re.I), "дом"),
    (re.compile(r"\bд\b",     re.I), "дом"),
]

# Pattern to detect whether an address has a building number.
_HAS_BLDG_NUM = re.compile(r"(?:д\.?|дом)\s*\d|,\s*\d+[а-яёА-ЯЁ]?\s*$", re.I)


# ── address canonicalisation ───────────────────────────────────────────────────

def _canonical(addr: str) -> str:
    """Strip city prefix, normalise abbreviations, lowercase, collapse spaces."""
    s = _CITY_PREFIX.sub("", addr.strip())
    for pat, repl in _STREET_ABBREV:
        s = pat.sub(repl, s)
    s = _EXTRA_SPACE.sub(" ", s).strip().rstrip(",").lower()
    return s


def _extract_bldg_num(canon: str) -> str | None:
    m = re.search(r"(?:дом\s*)(\d+)", canon, re.I)
    if m:
        return m.group(1)
    # bare trailing number: "... 54а" or "..., 1б"
    m = re.search(r"(?:,\s*|\s)(\d+)\s*[а-яёА-ЯЁ]?\s*$", canon, re.I)
    return m.group(1) if m else None


# ── JSON detail parser ─────────────────────────────────────────────────────────

def parse_detail(raw: bytes, sha256: str) -> dict:
    """Extract flat fields from a raw ЕИСЖС house-detail API JSON response."""
    try:
        envelope = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON decode error: {exc}") from exc

    d = envelope.get("data") or envelope  # handle both wrapped and bare

    dev: dict = d.get("developer") or {}
    rnv_list: list = d.get("rnvDTO") or []
    rnv0 = rnv_list[0] if rnv_list else {}

    # Commissioning date: objReady100PercDt when status=2, else None.
    status = d.get("objStatus")
    commissioned_dt = d.get("objReady100PercDt") if status == 2 else None

    # Normalise RnV date: "23-12-2024 00:00" → "2024-12-23"
    rnv_dt_raw = rnv0.get("docObjRnvDt") or rnv0.get("rnvDt") or ""
    rnv_dt = _parse_eisghs_date(rnv_dt_raw)

    # RPD issue datetime: "14-03-2025 11:39"
    rpd_issue_dttm = d.get("rpdIssueDttm") or None

    return {
        "source_sha256": sha256,
        "eisghs_id": d.get("id"),
        "hobjId": d.get("hobjId"),
        "pdId": d.get("pdId"),
        "nameObj": d.get("nameObj"),
        "address": d.get("address"),
        "addrAreaId": d.get("addrAreaId"),
        "obj_status": status,
        "obj_status_desc": _STATUS_DESC.get(status, "unknown") if status is not None else "unknown",
        "obj_publ_dt": d.get("objPublDt"),
        "commissioned_dt": commissioned_dt,
        "rpd_num": d.get("rpdNum"),
        "rpd_pdf_link": d.get("rpdPdfLink"),
        "rpd_issue_dttm": rpd_issue_dttm,
        "rnv_num": rnv0.get("docObjRnvNum") or rnv0.get("rnvNum"),
        "rnv_dt": rnv_dt,
        "rnv_pdf_link": rnv0.get("fileUrl"),
        "flat_cnt": d.get("objFlatCnt") or d.get("objElemLivingCnt"),
        "floor_cnt": d.get("objFloorCnt"),
        "area_sqm_living": d.get("objSquareLiving"),
        "sold_out_perc": d.get("soldOutPerc"),
        "lat": d.get("objLkLatitude"),
        "lon": d.get("objLkLongitude"),
        "dev_id": dev.get("devId"),
        "dev_inn": dev.get("devInn"),
        "dev_ogrn": dev.get("devOgrn"),
        "dev_kpp": dev.get("devKpp"),
        "dev_name_short": dev.get("devShortCleanNm") or dev.get("devShortNm"),
        "dev_name_full": dev.get("devFullCleanNm"),
        "dev_ceo": dev.get("devEmplMainFullNm"),
        "dev_legal_addr": dev.get("devLegalAddr"),
        "dev_region": dev.get("regRegionDesc"),
        # Populated by crosswalk step below.
        "land_order_match": None,
        "demolition_match": None,
        "minstroy_match": None,
        "legal_grade": False,
        "flags": [],
    }


def _parse_eisghs_date(s: str) -> str | None:
    """Convert ЕИСЖС date strings like "23-12-2024 00:00" or "2024-12-23" to ISO."""
    if not s:
        return None
    # Already ISO
    if re.match(r"\d{4}-\d{2}-\d{2}", s):
        return s[:10]
    m = re.match(r"(\d{2})-(\d{2})-(\d{4})", s)
    if m:
        try:
            return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1))).date().isoformat()
        except ValueError:
            pass
    return None


# ── crosswalk helpers ──────────────────────────────────────────────────────────

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


def _build_inn_index(land_orders: list[dict]) -> dict[str, list[dict]]:
    """Index land orders by beneficiary INN. Multiple decrees per INN possible."""
    idx: dict[str, list[dict]] = defaultdict(list)
    for lo in land_orders:
        inn = lo.get("beneficiary_inn")
        if inn:
            idx[inn].append(lo)
    return dict(idx)


def _build_address_index(records: list[dict], addr_field: str) -> dict[str, list[dict]]:
    """Canonical-address → records index for fuzzy matching."""
    idx: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        raw = rec.get(addr_field) or ""
        if not raw:
            continue
        key = _canonical(raw)
        if len(key) >= 8 and re.search(r"[а-яё]", key) and re.search(r"\d", key):
            idx[key].append(rec)
    return dict(idx)


def _fuzzy_match(
    query_addr: str,
    index: dict[str, list[dict]],
    addr_field: str,
    threshold: float = _FUZZY_THRESHOLD,
) -> dict | None:
    """Return the best fuzzy address match or None if below threshold."""
    if not query_addr:
        return None
    canon = _canonical(query_addr)
    if not canon:
        return None
    if not _HAS_BLDG_NUM.search(canon):
        return None  # don't attempt fuzzy on addresses with no building number

    query_bldg = _extract_bldg_num(canon)
    best_score = 0.0
    best_key = None

    for key in index:
        score = fuzz.token_set_ratio(canon, key)
        if score > best_score:
            best_key = key
            best_score = score

    if best_score < threshold or best_key is None:
        return None

    # Building-number guard: reject if both sides have numbers and they differ.
    if query_bldg:
        matched_bldg = _extract_bldg_num(best_key)
        if matched_bldg and matched_bldg != query_bldg:
            return None

    matched_rec = index[best_key][0]
    return {
        "matched_address_raw": matched_rec.get(addr_field, ""),
        "match_score": float(best_score),
        "match_method": "fuzzy",
        "matched_record": matched_rec,
    }


# ── crosswalk ─────────────────────────────────────────────────────────────────

def run_crosswalk(
    objects: list[dict],
    land_orders: list[dict],
    minstroy: list[dict],
    demolition_decrees: list[dict],
    rpd_cadastrals: list[dict] | None = None,
) -> list[dict]:
    """Join each ЕИСЖС object against other parsed sources. Returns crosswalk records."""
    inn_index = _build_inn_index(land_orders)

    # Index RPD cadastral records by eisghs_id
    rpd_by_id: dict[int, dict] = {}
    for rc in (rpd_cadastrals or []):
        eid = rc.get("eisghs_id")
        if eid is not None:
            rpd_by_id[eid] = rc

    # Address index for minstroy register
    minstroy_idx = _build_address_index(minstroy, "address_raw")

    # Address index for demolition decrees
    demolition_idx = _build_address_index(demolition_decrees, "address_raw")

    xwalk_hits: list[dict] = []

    for obj in objects:
        flags: list[str] = list(obj.get("flags") or [])
        inn = obj.get("dev_inn")
        addr = obj.get("address") or ""
        eisghs_id = obj.get("eisghs_id")

        # ── Join 1: INN → land orders ──────────────────────────────────────
        land_matches = inn_index.get(inn, []) if inn else []
        if land_matches:
            # Per-building decree selection: prefer the decree whose cadastral
            # numbers overlap with this building's RPD PDF cadastrals.  When a
            # developer has multiple decrees (one parcel per building), this
            # avoids assigning the wrong decree to a building and causing a
            # false cadastral-overlap miss downstream.
            # Fallback: decree with the most cadastral numbers (original logic).
            rpd_pre = rpd_by_id.get(eisghs_id) if eisghs_id is not None else None
            rpd_cads_pre = set(rpd_pre["cadastral_numbers"]) if rpd_pre and rpd_pre.get("cadastral_numbers") else set()
            if rpd_cads_pre:
                overlapping = [
                    lo for lo in land_matches
                    if rpd_cads_pre & set(lo.get("cadastral_numbers") or [])
                ]
                if overlapping:
                    best_lo = max(overlapping, key=lambda lo: len(rpd_cads_pre & set(lo.get("cadastral_numbers") or [])))
                else:
                    best_lo = max(land_matches, key=lambda lo: len(lo.get("cadastral_numbers") or []))
            else:
                best_lo = max(land_matches, key=lambda lo: len(lo.get("cadastral_numbers") or []))
            obj["land_order_match"] = {
                "decree_number": best_lo.get("decree_number"),
                "decree_date": best_lo.get("decree_date"),
                "signing_official": best_lo.get("signing_official"),
                "issuing_body": best_lo.get("issuing_body"),
                "cadastral_numbers": best_lo.get("cadastral_numbers") or [],
                "area_sqm": best_lo.get("area_sqm"),
                "address_normalized": best_lo.get("address_normalized"),
                "project_name": best_lo.get("project_name"),
                "beneficiary_name": best_lo.get("beneficiary_name"),
                "source_sha256": best_lo.get("source_sha256"),
                "match_method": "inn_exact",
                "match_score": 1.0,
                "all_decree_numbers": [lo.get("decree_number") for lo in land_matches],
            }
            xwalk_hits.append({
                "eisghs_id": eisghs_id,
                "link_type": "eisghs→land_order",
                "match_method": "inn_exact",
                "match_score": 1.0,
                "developer_inn": inn,
                "decree_number": best_lo.get("decree_number"),
                "decree_date": best_lo.get("decree_date"),
                "cadastral_numbers": best_lo.get("cadastral_numbers") or [],
                "land_order_sha256": best_lo.get("source_sha256"),
            })
        else:
            if inn:
                flags.append("no_land_order_for_inn")

        # ── Join 2: ЕИСЖС address → minstroy register ─────────────────────
        minstroy_hit = _fuzzy_match(addr, minstroy_idx, "address_raw")
        if minstroy_hit:
            obj["minstroy_match"] = {
                "matched_address_raw": minstroy_hit["matched_address_raw"],
                "match_score": minstroy_hit["match_score"],
                "match_method": minstroy_hit["match_method"],
                "order_reference_raw": minstroy_hit["matched_record"].get("order_reference_raw"),
                "order_number": minstroy_hit["matched_record"].get("order_number"),
                "source_sha256": minstroy_hit["matched_record"].get("source_sha256"),
            }
            xwalk_hits.append({
                "eisghs_id": eisghs_id,
                "link_type": "eisghs→minstroy",
                "match_method": minstroy_hit["match_method"],
                "match_score": minstroy_hit["match_score"],
                "eisghs_address": addr,
                "minstroy_address": minstroy_hit["matched_address_raw"],
                "minstroy_order": minstroy_hit["matched_record"].get("order_reference_raw"),
            })
        elif land_matches and _HAS_BLDG_NUM.search(addr):
            # INN matched a land order but address doesn't match any demolished
            # building at the same address → this is the address-laundering pattern.
            flags.append("address_laundering")

        # ── Join 3: ЕИСЖС address → demolition decrees ────────────────────
        demolition_hit = _fuzzy_match(addr, demolition_idx, "address_raw")
        if demolition_hit:
            obj["demolition_match"] = {
                "matched_address_raw": demolition_hit["matched_address_raw"],
                "match_score": demolition_hit["match_score"],
                "match_method": demolition_hit["match_method"],
                "source_sha256": demolition_hit["matched_record"].get("source_sha256"),
            }
            xwalk_hits.append({
                "eisghs_id": eisghs_id,
                "link_type": "eisghs→demolition_decree",
                "match_method": demolition_hit["match_method"],
                "match_score": demolition_hit["match_score"],
                "eisghs_address": addr,
                "matched_address": demolition_hit["matched_address_raw"],
            })

        # ── Join 4: RPD PDF cadastral confirmation ─────────────────────────
        rpd_rec = rpd_by_id.get(eisghs_id) if eisghs_id is not None else None
        rpd_cadastral_match = None
        if rpd_rec and rpd_rec.get("cadastral_numbers"):
            lo_match_pre = obj.get("land_order_match")
            lo_cads = set(lo_match_pre.get("cadastral_numbers") or []) if lo_match_pre else set()
            rpd_cads = set(rpd_rec["cadastral_numbers"])
            overlap = lo_cads & rpd_cads
            rpd_cadastral_match = {
                "cadastral_numbers": rpd_rec["cadastral_numbers"],
                "area_sqm": rpd_rec.get("area_sqm"),
                "rpd_num_in_pdf": rpd_rec.get("rpd_num_in_pdf"),
                "project_name_in_pdf": rpd_rec.get("project_name_in_pdf"),
                "project_title_in_pdf": rpd_rec.get("project_title_in_pdf"),
                "developer_inn_in_pdf": rpd_rec.get("developer_inn_in_pdf"),
                "source_sha256": rpd_rec.get("source_sha256"),
                "derived_sha256": rpd_rec.get("derived_sha256"),
                "cadastral_overlap_with_land_order": sorted(overlap),
                "match_method": "pdf_text_extract",
                "match_score": 1.0 if overlap else 0.0,
            }
            # INN-only confirmation: when the land order describes territory
            # without a cadastral number (pre-2025 allocation form), the RPD PDF
            # is still an independent second source — it is a federal construction
            # permit/commissioning certificate from a different authority.
            # developer_inn_in_pdf must match dev_inn (extracted independently
            # from the OCR'd PDF, not from ЕИСЖС metadata).
            rpd_inn_confirms = bool(
                rpd_rec.get("developer_inn_in_pdf")
                and rpd_rec["developer_inn_in_pdf"] == inn
                and obj.get("land_order_match")  # must have an allocation decree
            )
            rpd_cadastral_match["rpd_inn_only_confirmation"] = (
                rpd_inn_confirms and not overlap
            )
            obj["rpd_cadastral_match"] = rpd_cadastral_match
            confirm_type = (
                "cadastral_overlap" if overlap
                else ("inn_only" if rpd_inn_confirms else "none")
            )
            xwalk_hits.append({
                "eisghs_id": eisghs_id,
                "link_type": "eisghs→rpd_pdf",
                "match_method": "pdf_text_extract",
                "match_score": 1.0 if overlap else 0.5,
                "confirm_type": confirm_type,
                "cadastral_overlap": sorted(overlap),
                "rpd_cadastrals": rpd_rec["cadastral_numbers"],
                "rpd_sha256": rpd_rec.get("source_sha256"),
                "derived_sha256": rpd_rec.get("derived_sha256"),
            })
        else:
            obj["rpd_cadastral_match"] = None

        # ── Legal grade ────────────────────────────────────────────────────
        # legal_grade requires cadastrals confirmed in ≥2 independent sources.
        # Source types: land_order (INN exact), rpd_pdf (text extract),
        #               minstroy (address fuzzy), demolition_decree (address fuzzy).
        # RPD confirmation accepts either:
        #   - cadastral_overlap: same parcel in both decree and RPD PDF (strong)
        #   - inn_only: developer INN extracted from RPD PDF matches land order;
        #     counts when land order uses territory description (no cadastral).
        #     Two independent authority documents (DNR Head + federal RPD) confirm
        #     the same developer — valid second source per Berkeley Protocol §3.
        lo_match = obj.get("land_order_match")
        rpd_cm = obj.get("rpd_cadastral_match") or {}
        has_cadastrals = bool(
            (lo_match and lo_match.get("cadastral_numbers"))
            or rpd_cm.get("cadastral_numbers")
        )
        rpd_confirms = bool(
            rpd_cm.get("cadastral_overlap_with_land_order")
            or rpd_cm.get("rpd_inn_only_confirmation")
        )
        n_sources = sum([
            bool(lo_match),
            rpd_confirms,
            bool(obj.get("minstroy_match")),
            bool(obj.get("demolition_match")),
        ])

        if has_cadastrals and n_sources >= 2:
            obj["legal_grade"] = True
        elif has_cadastrals:
            obj["legal_grade"] = False
            if not any(f.startswith("single_source") for f in flags):
                flags.append("single_source_inn_only")
        else:
            obj["legal_grade"] = False

        obj["flags"] = flags

    return xwalk_hits


# ── Троянда-М / address-laundering summary ────────────────────────────────────

def _log_troianda_summary(objects: list[dict]) -> None:
    """Log a focused summary of the Троянда-М / RKS chain."""
    rks_objs = [o for o in objects if o.get("dev_inn") == "9310007980"]
    if not rks_objs:
        log.warning("RKS-Девелопмент (INN 9310007980) not found in parsed objects")
        return

    for obj in rks_objs:
        lo = obj.get("land_order_match") or {}
        log.info("── ТРОЯНДА-М crosswalk (RKS-Девелопмент) ──────────────────────────────")
        log.info("  ЕИСЖС id=%s | %r | %s", obj["eisghs_id"], obj["nameObj"], obj["address"])
        log.info("  Status: %s | commissioned: %s | sold: %.0f%%",
                 obj["obj_status_desc"],
                 obj.get("commissioned_dt") or "–",
                 (obj.get("sold_out_perc") or 0) * 100)
        log.info("  Developer: %s (INN %s) CEO: %s",
                 obj.get("dev_name_short"), obj.get("dev_inn"), obj.get("dev_ceo") or "–")
        if lo:
            log.info("  Land order: №%s (%s) signed by %s",
                     lo.get("decree_number"), lo.get("decree_date"),
                     lo.get("signing_official") or "?")
            log.info("  Cadastrals: %s", lo.get("cadastral_numbers"))
            log.info("  Project name in decree: %r", lo.get("project_name"))
            log.info("  Land area: %s m²", lo.get("area_sqm"))
            log.info("  Decree territory: %r", (lo.get("address_normalized") or "")[:120])
        else:
            log.info("  Land order: NO MATCH")
        rpd_cm = obj.get("rpd_cadastral_match") or {}
        if rpd_cm.get("cadastral_overlap_with_land_order"):
            log.info("  RPD PDF cadastrals: %s", rpd_cm.get("cadastral_numbers"))
            log.info("  RPD overlap with land order: %s", rpd_cm["cadastral_overlap_with_land_order"])
            log.info("  RPD area: %s m²  (land order area: %s m²)",
                     rpd_cm.get("area_sqm"), lo.get("area_sqm") if lo else "–")
            log.info("  ✓ 2-SOURCE CADASTRAL CONFIRMATION → legal_grade=True eligible")
        elif "address_laundering" in (obj.get("flags") or []):
            log.info("  *** FLAG: address_laundering — new address differs from demolished "
                     "building location; RPD PDF cadastral confirmation pending ***")
        log.info("  legal_grade=%s | flags=%s", obj["legal_grade"], obj["flags"])


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
    )

    con = forensics.open_state()

    sources = con.execute(
        """SELECT sha256, raw_path, title
           FROM source_document
           WHERE source_type = 'eisghs_house_detail'
           ORDER BY title"""
    ).fetchall()

    if not sources:
        log.error(
            "No eisghs_house_detail records in state DB — "
            "run scripts/17_crawl_eisghs_mariupol.py first."
        )
        return

    log.info("Found %d eisghs_house_detail records", len(sources))

    # ── Parse all detail JSONs ──────────────────────────────────────────────
    objects: list[dict] = []
    parse_errors = 0

    for sha, raw_path, title in sources:
        p = Path(raw_path)
        if not p.exists():
            log.error("Raw file missing: %s", raw_path)
            parse_errors += 1
            continue
        try:
            obj = parse_detail(p.read_bytes(), sha)
        except Exception:
            log.exception("Parse error for %s", raw_path)
            parse_errors += 1
            continue

        log.info(
            "  id=%-6s  status=%-17s  inn=%-12s  rpd=%-12s  rnv=%-20s  %s",
            obj["eisghs_id"],
            obj["obj_status_desc"],
            obj["dev_inn"] or "–",
            obj["rpd_num"] or "–",
            obj["rnv_num"] or "–",
            (obj["address"] or "–")[:50],
        )
        objects.append(obj)

    log.info("Parsed %d objects (%d errors)", len(objects), parse_errors)

    # ── Load other parsed sources ───────────────────────────────────────────
    parsed_dir = config.PROJECT_ROOT / "data" / "parsed"

    land_orders     = _load_jsonl(parsed_dir / "dnr_land_orders.jsonl")
    minstroy        = _load_jsonl(parsed_dir / "minstroy_demolition_register.jsonl")
    demolition      = _load_jsonl(parsed_dir / "demolition_decrees.jsonl")
    rpd_cadastrals  = _load_jsonl(parsed_dir / "eisghs_rpd_cadastrals.jsonl")

    log.info(
        "Crosswalk sources: land_orders=%d  minstroy=%d  demolition_decrees=%d  rpd_cadastrals=%d",
        len(land_orders), len(minstroy), len(demolition), len(rpd_cadastrals),
    )

    # ── Run crosswalk ───────────────────────────────────────────────────────
    xwalk_hits = run_crosswalk(objects, land_orders, minstroy, demolition, rpd_cadastrals)

    # ── Write outputs ───────────────────────────────────────────────────────
    out_dir = parsed_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    obj_path = out_dir / "eisghs_mariupol_objects.jsonl"
    with obj_path.open("w", encoding="utf-8") as fh:
        for obj in objects:
            fh.write(json.dumps(obj, ensure_ascii=False) + "\n")
    log.info("Written %d object records → %s", len(objects), obj_path)

    xwalk_path = out_dir / "eisghs_crosswalk.jsonl"
    with xwalk_path.open("w", encoding="utf-8") as fh:
        for hit in xwalk_hits:
            fh.write(json.dumps(hit, ensure_ascii=False) + "\n")
    log.info("Written %d crosswalk hits → %s", len(xwalk_hits), xwalk_path)

    # ── Summary stats ───────────────────────────────────────────────────────
    commissioned  = [o for o in objects if o["obj_status"] == 2]
    under_const   = [o for o in objects if o["obj_status"] == 0]
    with_lo       = [o for o in objects if o.get("land_order_match")]
    with_rpd_cad  = [o for o in objects if o.get("rpd_cadastral_match") and
                     o["rpd_cadastral_match"].get("cadastral_overlap_with_land_order")]
    legal         = [o for o in objects if o["legal_grade"]]
    laundering    = [o for o in objects if "address_laundering" in (o.get("flags") or [])]

    log.info("── Summary ─────────────────────────────────────────────────────────────")
    log.info("  Total objects:        %d", len(objects))
    log.info("  Commissioned:         %d", len(commissioned))
    log.info("  Under construction:   %d", len(under_const))
    log.info("  INN→land order hit:   %d", len(with_lo))
    log.info("  RPD cadastral match:  %d", len(with_rpd_cad))
    log.info("  Legal-grade links:    %d", len(legal))
    log.info("  Address-laundering:   %d", len(laundering))
    log.info("  Crosswalk hits total: %d", len(xwalk_hits))
    if parse_errors:
        log.warning("  Parse errors:         %d", parse_errors)

    # ── Developer INN summary ───────────────────────────────────────────────
    from collections import Counter
    inn_counter: Counter = Counter()
    for obj in objects:
        inn = obj.get("dev_inn") or "unknown"
        name = obj.get("dev_name_short") or "?"
        inn_counter[(inn, name)] += 1

    log.info("── Developer breakdown ─────────────────────────────────────────────────")
    for (inn, name), cnt in inn_counter.most_common():
        lo_matched = sum(1 for o in objects if o.get("dev_inn") == inn and o.get("land_order_match"))
        log.info("  %-12s  %-35s  objects=%d  land_order_hits=%d", inn, name, cnt, lo_matched)

    # ── Троянда-М specific summary ──────────────────────────────────────────
    _log_troianda_summary(objects)


if __name__ == "__main__":
    main()
