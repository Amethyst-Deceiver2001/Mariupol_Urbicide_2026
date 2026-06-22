#!/usr/bin/env python3
"""Stage 2h: extract founders (СвУчредит) from already-captured EGRUL records.

Pure re-parse of the egrul.org JSON bodies already in the raw store (captured
by scripts/20_lookup_egrul.py). No network calls — local-only, safe to re-run.

For each beneficiary in data/parsed/egrul_inn_lookups.jsonl, loads the raw
JSON by source_sha256 and extracts every founder/shareholder entry under
СвУчредит:

  - УчрФЛ      individual founder  -> ФИО + ИННФЛ + share
  - УчрЮЛРос   Russian-entity founder -> full name + ИНН/ОГРН + share
  - УчрЮЛИн    foreign-entity founder -> name + country + share
  - УчрРФСубМО RF subject / municipality as founder
  - (anything else) recorded with founder_type=other_<key>, raw kept

Individual founders' ИНН carries a 2-digit region-code prefix from the
issuing tax authority (77/99=Moscow, 50=Moscow Oblast, 78=SPb, 93=DNR/
occupied Donetsk region, ...). Flags non-93 individual founders as
"mainland_rf" -- useful for tracing the multi-LLC operators' real backers
back to mainland Russia.

Output: data/parsed/egrul_founders.jsonl (one row per founder).
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

# Individual-ИНН region-code prefixes worth naming in the report (non-exhaustive).
_REGION_PREFIXES = {
    "77": "Moscow", "99": "Moscow", "50": "Moscow Oblast",
    "78": "St. Petersburg", "47": "Leningrad Oblast",
    "93": "DNR (occupied Donetsk region)",
}


def _attrs(node: object) -> dict:
    if isinstance(node, dict):
        a = node.get("@attributes")
        if isinstance(a, dict):
            return a
    return {}


def _share(node: dict) -> tuple[str | None, str | None]:
    """Return (nominal_value, percent_str) from a ДоляУстКап sub-node."""
    dol = node.get("ДоляУстКап")
    if not isinstance(dol, dict):
        return None, None
    nominal = _attrs(dol).get("НоминСтоим")
    rd = dol.get("РазмерДоли")
    percent = None
    if isinstance(rd, dict):
        percent = rd.get("Процент")
        if percent is None:
            drob = rd.get("Дробь")
            if isinstance(drob, dict):
                num = drob.get("Числит")
                den = drob.get("Знаменат")
                if num and den:
                    try:
                        percent = f"{float(num) / float(den) * 100:.4f}"
                    except (ValueError, ZeroDivisionError):
                        pass
    return nominal, percent


def _inn_region(inn: str | None) -> str | None:
    if not inn or len(inn) < 2 or not inn[:2].isdigit():
        return None
    return _REGION_PREFIXES.get(inn[:2], f"region-{inn[:2]}")


def _parse_individual(node: dict) -> dict:
    fl = node.get("СвФЛ") or {}
    a = _attrs(fl)
    name = " ".join(p for p in (a.get("Фамилия"), a.get("Имя"), a.get("Отчество")) if p) or None
    inn = a.get("ИННФЛ")
    nominal, percent = _share(node)
    return {
        "founder_type": "individual",
        "founder_name": name,
        "founder_inn": inn,
        "founder_inn_region": _inn_region(inn),
        "share_nominal": nominal,
        "share_percent": percent,
    }


def _parse_org(node: dict, country: str | None = None) -> dict:
    naimn = node.get("НаимИННЮЛ") or node.get("СвНаимЮЛ") or {}
    a = _attrs(naimn)
    nominal, percent = _share(node)
    return {
        "founder_type": "org" if not country else "foreign_org",
        "founder_name": a.get("НаимЮЛПолн") or a.get("НаимЮЛ"),
        "founder_inn": a.get("ИНН"),
        "founder_ogrn": a.get("ОГРН"),
        "founder_country": country,
        "share_nominal": nominal,
        "share_percent": percent,
    }


def _parse_subject_mo(node: dict) -> dict:
    a = _attrs(node.get("ВидНаимУчрПуб") or node)
    nominal, percent = _share(node)
    return {
        "founder_type": "rf_subject_or_municipality",
        "founder_name": a.get("НаимПолн") or a.get("Наим"),
        "share_nominal": nominal,
        "share_percent": percent,
    }


def _parse_founders(uchr: dict) -> list[dict]:
    out: list[dict] = []
    for key, val in uchr.items():
        entries = val if isinstance(val, list) else [val]
        for node in entries:
            if not isinstance(node, dict):
                continue
            if key == "УчрФЛ":
                rec = _parse_individual(node)
            elif key == "УчрЮЛРос":
                rec = _parse_org(node)
            elif key == "УчрЮЛИн":
                a = _attrs(node.get("СвЮЛИн") or {})
                rec = {
                    "founder_type": "foreign_org",
                    "founder_name": a.get("НаимПолн"),
                    "founder_country": a.get("НаимСтран") or a.get("КодСтран"),
                    **dict(zip(("share_nominal", "share_percent"), _share(node))),
                }
            elif key == "УчрРФСубМО":
                rec = _parse_subject_mo(node)
            else:
                rec = {"founder_type": f"other_{key}", "raw": node}
            rec["raw_key"] = key
            out.append(rec)
    return out


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")

    parsed_dir = config.PROJECT_ROOT / "data" / "parsed"
    lookups_path = parsed_dir / "egrul_inn_lookups.jsonl"
    out_path = parsed_dir / "egrul_founders.jsonl"
    raw_dir = config.PROJECT_ROOT / "data" / "raw"

    if not lookups_path.exists():
        log.error("%s not found -- run scripts/20_lookup_egrul.py first", lookups_path)
        sys.exit(1)

    rows = [json.loads(l) for l in lookups_path.read_text(encoding="utf-8").splitlines() if l.strip()]

    out_rows: list[dict] = []
    no_founder_data: list[str] = []
    for rec in rows:
        if rec.get("source") != "egrul_org":
            continue
        sha = rec.get("source_sha256")
        name = rec.get("beneficiary_name")
        company_inn = rec.get("inn")
        raw_path = raw_dir / f"{sha}.json"
        if not raw_path.exists():
            log.warning("raw capture missing for %s (sha %s)", name, sha)
            continue
        data = json.loads(raw_path.read_text(encoding="utf-8"))
        ul = data.get("СвЮЛ") or {}
        uchr_key = next((k for k in ul.keys() if k.startswith("СвУчредит")), None)
        uchr = ul.get(uchr_key) if uchr_key else None
        if not isinstance(uchr, dict):
            no_founder_data.append(name)
            continue
        for founder in _parse_founders(uchr):
            out_rows.append({
                "company_name": name,
                "company_inn": company_inn,
                "company_short_name": rec.get("short_name"),
                "source_sha256": sha,
                **founder,
            })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        for r in out_rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    log.info("Wrote %d founder records -> %s", len(out_rows), out_path)
    if no_founder_data:
        log.info("No СвУчредит node (e.g. АО without disclosed shareholders): %s",
                 ", ".join(no_founder_data))

    # Quick report: individuals grouped by INN-region, orgs, cross-references.
    individuals_by_region: dict[str, list[str]] = {}
    orgs: list[dict] = []
    for r in out_rows:
        if r["founder_type"] == "individual":
            region = r.get("founder_inn_region") or "unknown"
            individuals_by_region.setdefault(region, []).append(
                f"{r['founder_name']} (ИНН {r['founder_inn']}, {r.get('share_percent')}%) "
                f"<- {r['company_short_name'] or r['company_name']}"
            )
        elif r["founder_type"] in ("org", "foreign_org"):
            orgs.append(r)

    log.info("--- Individual founders by ИНН region ---")
    for region, entries in sorted(individuals_by_region.items()):
        log.info("  %s (%d):", region, len(entries))
        for e in entries:
            log.info("    %s", e)

    if orgs:
        log.info("--- Org founders (potential holding/cross-link nodes) ---")
        for o in orgs:
            log.info("  %s (ИНН %s, ОГРН %s, %s%%) <- %s",
                     o.get("founder_name"), o.get("founder_inn"), o.get("founder_ogrn"),
                     o.get("share_percent"), o["company_short_name"] or o["company_name"])

    # Cross-reference: does any org-founder INN also appear as a beneficiary
    # (developer) INN elsewhere in egrul_inn_lookups.jsonl, or as another
    # founder's INN (shared individual across multiple SPVs)?
    company_inns = {r.get("inn") for r in rows if r.get("inn")}
    founder_org_inns = {o.get("founder_inn") for o in orgs if o.get("founder_inn")}
    overlap = company_inns & founder_org_inns
    if overlap:
        log.info("--- CROSS-LINK: org founder INN also a developer-company INN: %s ---",
                 ", ".join(sorted(overlap)))

    # Same individual ИНН founding multiple companies.
    by_person_inn: dict[str, set[str]] = {}
    for r in out_rows:
        if r["founder_type"] == "individual" and r.get("founder_inn"):
            by_person_inn.setdefault(r["founder_inn"], set()).add(
                r["company_short_name"] or r["company_name"]
            )
    shared = {inn: cos for inn, cos in by_person_inn.items() if len(cos) > 1}
    if shared:
        log.info("--- Individuals founding >1 captured company ---")
        for inn, cos in shared.items():
            log.info("  ИНН %s -> %s", inn, ", ".join(sorted(cos)))


if __name__ == "__main__":
    main()
