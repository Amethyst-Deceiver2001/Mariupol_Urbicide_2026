#!/usr/bin/env python3
"""Capture the exact ЕГРН parcel polygon for every cadastral number on file,
from the Rosreestr Public Cadastral Map — the real "borders, not center points"
source for allocated land parcels.

WHAT IT CAPTURES
----------------
Cadastral numbers come from two parsed sources:
  - land grants (scripts/10/68): 26 records carry `cadastral_numbers`
  - non-residential industrial parcels (scripts/290): 11 carry `cadastral_no`
~37 parcels total (deduplicated). For each, this queries BOTH public endpoints
and captures every response verbatim to the raw store (forensic custody):
  1. nspd.gov.ru  — National Spatial Data Platform (the current portal that
     replaced pkk.rosreestr.ru); its search returns GeoJSON with geometry.
  2. pkk.rosreestr.ru — the legacy Public Cadastral Map feature API, as a
     fallback for numbers the new portal doesn't resolve.

CAPTURE-THEN-PARSE (do not parse here). These endpoints are geoblocked and I
(Claude) cannot see a live response, and the annexed-territory cadastral
numbering may be the DNR's own format (`1412300000:02:001:0080`) rather than
standard ЕГРН `RR:DD:…`. So this script only *captures* — scripts/296 extracts
the polygon from whatever actually came back, and you tell Claude what the
responses look like if the shape is unexpected. Both raw-number and a
digit-regrouped variant are tried so a format mismatch is visible in the logs.

Claude must NEVER run this — it hits Russian federal geo-services and must be
run by you, from your Russia-routed VPS (CLAUDE.md). verify=False is
intentional (same rationale as scripts/289/293); SHA-256 is the integrity
anchor.

Usage (from the VPS):
    .venv312/bin/python scripts/295_crawl_cadastral_parcels.py
    .venv312/bin/python scripts/295_crawl_cadastral_parcels.py --only 1412300000:02:001:0080
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests
import urllib3

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger("cadastral_crawl")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

LAND_ORDERS = ROOT / "data" / "parsed" / "dnr_land_orders.jsonl"
NONRES = ROOT / "data" / "parsed" / "nonresidential_ownerless.jsonl"
MIN_INTERVAL = 1.5


def collect_cadastrals() -> dict[str, list[str]]:
    """cadastral_no -> list of provenance labels."""
    out: dict[str, list[str]] = {}
    if LAND_ORDERS.exists():
        for line in LAND_ORDERS.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            cads = r.get("cadastral_numbers") or []
            if isinstance(cads, str):
                cads = [cads]
            for c in cads:
                c = (c or "").strip()
                if c:
                    out.setdefault(c, []).append(f"land_grant decree {r.get('decree_number')}")
    if NONRES.exists():
        for line in NONRES.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            c = (r.get("cadastral_no") or "").strip()
            if c and ":" in c:  # skip the one row that stored coordinates here
                out.setdefault(c, []).append(f"industrial parcel {r.get('address_raw')}")
    return out


def _regroup(cad: str) -> str | None:
    """Best-effort standard-ЕГРН regrouping of a DNR-format number, so a
    format mismatch is at least attempted rather than silently failing.
    `1412300000:02:001:0080` -> `14:12:0300000:0080`-ish. Returns None if it
    doesn't look regroupable."""
    parts = cad.split(":")
    if len(parts) == 4 and len(parts[0]) >= 4 and parts[0].isdigit():
        region, district = parts[0][:2], parts[0][2:4]
        quarter = (parts[0][4:] + parts[1] + parts[2]).lstrip("0") or "0"
        return f"{region}:{district}:{quarter}:{parts[3].lstrip('0') or '0'}"
    return None


def fetch(url: str, con, label: str, method="GET", data=None):
    for attempt in range(config.MAX_RETRIES):
        try:
            if method == "POST":
                resp = requests.post(url, data=data, headers={"User-Agent": config.USER_AGENT},
                                     timeout=config.TIMEOUT, verify=False)
            else:
                resp = requests.get(url, headers={"User-Agent": config.USER_AGENT},
                                    timeout=config.TIMEOUT, verify=False)
            forensics.capture_source(
                resp.content, url=url, source_type="rosreestr_cadastral_parcel",
                title=f"Cadastral parcel — {label}",
                description=("Rosreestr/NSPD cadastral geometry response captured for a land "
                             "parcel (scripts/295). Parsed by scripts/296."),
                content_type=resp.headers.get("Content-Type", "application/json"),
                http_status=resp.status_code, con=con,
            )
            return resp.status_code, len(resp.content)
        except requests.exceptions.RequestException as exc:
            if attempt == config.MAX_RETRIES - 1:
                log.warning("giving up on %s: %s", url, exc)
                return None, 0
            time.sleep(2.0 * (attempt + 1))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="crawl a single cadastral number")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    con = forensics.open_state()
    cadastrals = collect_cadastrals()
    if args.only:
        cadastrals = {args.only: ["--only"]}
    log.info("%d distinct cadastral numbers to crawl", len(cadastrals))

    for cad, provenance in cadastrals.items():
        variants = [cad]
        rg = _regroup(cad)
        if rg and rg != cad:
            variants.append(rg)
        log.info("=== %s (%s) — variants: %s", cad, "; ".join(provenance), variants)
        for v in variants:
            # 1) NSPD geoportal search (current portal, returns GeoJSON geometry)
            nspd = (f"https://nspd.gov.ru/api/geoportal/v2/search/geoportal"
                    f"?query={quote(v)}&thematicSearchId=1")
            st, n = fetch(nspd, con, f"nspd {v}") or (None, 0)
            log.info("  nspd %s -> %s (%s bytes)", v, st, n)
            time.sleep(MIN_INTERVAL)
            # 2) legacy PKK feature API (fallback)
            pkk = f"https://pkk.rosreestr.ru/api/features/1/{quote(v)}"
            st, n = fetch(pkk, con, f"pkk {v}") or (None, 0)
            log.info("  pkk  %s -> %s (%s bytes)", v, st, n)
            time.sleep(MIN_INTERVAL)

    con.close()
    log.info("done — all responses captured to the raw store. Next: "
             "scripts/296_parse_cadastral_parcels.py (and tell Claude if the "
             "geometry shape is unexpected).")


if __name__ == "__main__":
    main()
