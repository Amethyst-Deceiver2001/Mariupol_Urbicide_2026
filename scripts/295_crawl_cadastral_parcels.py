#!/usr/bin/env python3
"""HARD BLOCK, confirmed 2026-07-10 -- do not re-run expecting a different
result. All 39 cadastral numbers on file (both the `93:37:…` Mariupol/DNR-
issued ones and the DNR-format industrial-parcel ones) return a genuine,
well-formed "no objects found" from NSPD's own search across every layer/
theme tried (layersId=36048 land plots, thematicSearchId=1 real-estate
objects) -- and confirmed by manually searching one number
(93:37:0010410:173) in NSPD's own map UI at nspd.rosreetr.gov.ru, which also
finds nothing. Conclusion: Rosreestr's federal cadastre (ЕГРН/NSPD) simply
does not carry "new regions" (annexed territory) parcels at all -- DNR-issued
cadastral numbers were never entered into the federal system. This is not an
API, header, or WAF problem (those were all separately diagnosed and fixed
in this script's history -- see git log); it's a real data-availability gap
upstream, and this script is left in place only as a record of that finding
in case NSPD adds annexed-territory coverage later. The land-grant "borders,
not center points" goal is instead served by scripts/294 (approximate
street-boundary hull polygons from OSM), which IS live in the map.

Capture the exact ЕГРН parcel polygon for every cadastral number on file,
from the Rosreestr Public Cadastral Map — the real "borders, not center points"
source for allocated land parcels.

WHAT IT CAPTURES
----------------
Cadastral numbers come from two parsed sources:
  - land grants (scripts/10/68): 26 records carry `cadastral_numbers`
  - non-residential industrial parcels (scripts/290): 11 carry `cadastral_no`
~37 parcels total (deduplicated). For each, this queries the NSPD (National
Spatial Data Platform, the portal that replaced pkk.rosreestr.ru) geoportal
search and captures every response verbatim to the raw store (forensic
custody).

Uses the `pynspd` package (pip install pynspd) for the actual HTTP request:
a bare `requests` call to the NSPD API gets WAF-blocked (403 "Forbidden" with
a rule ID — confirmed 2026-07-10, not geoblocking, since a Russia-routed IP
gets through to the WAF just fine) even with browser-shaped headers.
`pynspd` reproduces the exact request shape the site's own map UI sends
(rotating User-Agent, `Referer: https://nspd.gov.ru/map?thematic=PKK`,
explicit `Host` header, and a relaxed-cipher SSL context some Russian
gov-issued certs need) and already treats occasional 403s as a retryable
`BlockedIP` condition — so it's used here instead of reimplementing that
dance by hand. https://github.com/yazmolod/pynspd

CAPTURE-THEN-PARSE (do not parse here). The annexed-territory cadastral
numbering may be the DNR's own format (`1412300000:02:001:0080`) rather than
standard ЕГРН `RR:DD:…`. So this script only *captures* — scripts/296 extracts
the polygon from whatever actually came back, and you tell Claude what the
responses look like if the shape is unexpected. Both raw-number and a
digit-regrouped variant are tried so a format mismatch is visible in the logs.

Claude must NEVER run this — it hits Russian federal geo-services and must be
run by you, from your Russia-routed VPS (CLAUDE.md). SHA-256 is the integrity
anchor.

Usage (from the VPS) — left for the record only, see the hard-block note above;
running this will not produce different results:
    .venv312/bin/pip install pynspd
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

try:
    from pynspd import Nspd
    from pynspd import errors as nspd_errors
except ImportError:
    Nspd = None
    nspd_errors = None

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


LANDPLOT_LAYER_ID = 36048  # "Земельные участки из ЕГРН" -- confirmed via pynspd's Layer36048Feature


def _capture_nspd_response(resp, con, label: str, url: str):
    forensics.capture_source(
        resp.content, url=url, source_type="rosreestr_cadastral_parcel",
        title=f"Cadastral parcel — {label}",
        description=("NSPD cadastral geometry response captured for a land parcel "
                     "(scripts/295, via pynspd). Parsed by scripts/296."),
        content_type=resp.headers.get("Content-Type", "application/json"),
        http_status=resp.status_code, con=con,
    )
    return resp.status_code, len(resp.content)


def fetch_nspd(nspd_client, v: str, con, label: str):
    """Query NSPD's search API via pynspd.safe_request() — which already
    retries internally (default 10 attempts, with backoff) on BlockedIP/
    TooManyRequests/server errors/timeouts, matching the site's own request
    shape. Tries layersId=36048 ("Земельные участки из ЕГРН", the land-plot
    layer) first -- thematicSearchId=1 (generic "real estate objects" theme)
    came back "no objects found" for every parcel tested, since it searches
    a different scope than the actual ЕГРН land-plot layer. Falls back to
    thematicSearchId=1 for numbers layersId doesn't resolve (e.g. the DNR-
    format industrial-parcel numbers, which may not be standard ЕГРН land
    plots). Captures the raw response verbatim regardless of outcome."""
    attempts = [
        ("layersId", LANDPLOT_LAYER_ID,
         f"https://nspd.gov.ru/api/geoportal/v2/search/geoportal?query={quote(v)}&layersId={LANDPLOT_LAYER_ID}"),
        ("thematicSearchId", 1,
         f"https://nspd.gov.ru/api/geoportal/v2/search/geoportal?query={quote(v)}&thematicSearchId=1"),
    ]
    last = (None, 0)
    for param_name, param_val, url in attempts:
        try:
            resp = nspd_client.safe_request(
                "get", "/api/geoportal/v2/search/geoportal",
                params={"query": v, param_name: param_val},
            )
        except nspd_errors.NotFound as exc:
            resp = exc.response
        except nspd_errors.PynspdResponseError as exc:
            log.warning("  pynspd gave up for %s (%s): %s", v, param_name, exc)
            resp = exc.response
        except Exception as exc:
            log.warning("  pynspd error for %s (%s): %s", v, param_name, exc)
            continue
        last = _capture_nspd_response(resp, con, f"{label} [{param_name}={param_val}]", url)
        if resp.status_code == 200:
            return last
    return last


def fetch(url: str, con, label: str, method="GET", data=None, headers=None):
    hdrs = headers or {"User-Agent": config.USER_AGENT}
    for attempt in range(config.MAX_RETRIES):
        try:
            if method == "POST":
                resp = requests.post(url, data=data, headers=hdrs,
                                     timeout=config.TIMEOUT, verify=False)
            else:
                resp = requests.get(url, headers=hdrs,
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

    if Nspd is None:
        log.error("pynspd is not installed. Run: .venv312/bin/pip install pynspd")
        sys.exit(1)

    con = forensics.open_state()
    cadastrals = collect_cadastrals()
    if args.only:
        cadastrals = {args.only: ["--only"]}
    log.info("%d distinct cadastral numbers to crawl", len(cadastrals))

    with Nspd() as nspd_client:
        for cad, provenance in cadastrals.items():
            variants = [cad]
            rg = _regroup(cad)
            if rg and rg != cad:
                variants.append(rg)
            log.info("=== %s (%s) — variants: %s", cad, "; ".join(provenance), variants)
            for v in variants:
                # 1) NSPD geoportal search (current portal, returns GeoJSON
                # geometry), via pynspd — see module docstring for why.
                st, n = fetch_nspd(nspd_client, v, con, f"nspd {v}") or (None, 0)
                log.info("  nspd %s -> %s (%s bytes)", v, st, n)
                time.sleep(MIN_INTERVAL)
                # 2) legacy PKK feature API (fallback; as of 2026-07 this domain
                # just proxies to the NSPD SPA shell for every request, but kept
                # in case that changes back or resolves for some numbers).
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
