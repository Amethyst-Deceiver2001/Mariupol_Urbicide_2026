"""Source 18 — pre-war Ukrainian real-estate listings via the Wayback CDX API.

Dead dom.ria.com / olx.ua / lun.ua / mesto.ua listing pages for the address
carry interior photos, declared floor area, and asking price as they stood
BEFORE the invasion — direct evidence of private ownership and pre-war value
(RD4U quantum). The live pages are gone/geoblocked, but archive.org's CDX
index surfaces every snapshot it holds, keyed by URL pattern. Keyless.

CDX is queried per host with a wildcard URL and a Ukrainian city/street
token, then each candidate snapshot's stored copy is captured. Matching is
loose at the CDX stage (host + street token) and tightened per-candidate by
re-checking the address variants against the snapshot's own stored text.
"""
from __future__ import annotations

import logging
import time

import requests

from ... import forensics
from ..variants import match_regexes
from .base import SourceResult, http_headers

log = logging.getLogger(__name__)

NAME = "realestate_prewar"
RUN = "C"
NETWORK = True
DESCRIPTION = "pre-war UA listings (dom.ria/olx/lun/mesto) via Wayback CDX — ownership+value"

CDX = "https://web.archive.org/cdx/search/cdx"
WB_SNAPSHOT = "https://web.archive.org/web/{ts}id_/{url}"
HOSTS = ("dom.ria.com", "olx.ua", "lun.ua", "mesto.ua", "flatfy.ua")
MAX_SNAPSHOTS = 25
MAX_CAPTURE = 12
PAUSE = 0.4


def plan(bundle) -> str:
    return (f"CDX per host {HOSTS} filtered to 2019-2022 snapshots mentioning "
            "the street; capture + address-verify each candidate")


def _translit_street_token(bundle) -> str:
    """A distinctive Latin street token for CDX URL-substring matching
    (dom.ria/lun slugs are transliterated), e.g. 'zelinskogo'."""
    for v in bundle.variants:
        if v.lang == "translit":
            return v.text.split()[0].lower()
    return ""


def fetch(bundle, con, radius_m: float = 0.0) -> SourceResult:
    token = _translit_street_token(bundle)
    if not token:
        return SourceResult(NAME, True, "no transliterated street token to query CDX with")

    regexes = match_regexes(bundle)
    findings: list[dict] = []
    captured: list[str] = []
    n_captured = 0

    for host in HOSTS:
        params = {
            "url": f"{host}/*{token}*",
            "output": "json",
            "from": "2019", "to": "2022",
            "filter": "statuscode:200",
            "collapse": "urlkey",
            "limit": str(MAX_SNAPSHOTS),
        }
        try:
            r = requests.get(CDX, params=params, headers=http_headers(), timeout=45)
            if r.status_code == 429:
                findings.append({"kind": "cdx_rate_limited", "host": host,
                                 "note": "archive.org CDX 429 — re-run this source later"})
                time.sleep(2.0)
                continue
            r.raise_for_status()
            rows = r.json()
        except requests.RequestException as e:
            log.warning("CDX query failed for %s: %s", host, e)
            findings.append({"kind": "error", "stage": f"cdx:{host}", "error": str(e)})
            continue
        if not rows or len(rows) < 2:
            continue
        header, *entries = rows
        for entry in entries:
            rec = dict(zip(header, entry))
            ts, orig = rec.get("timestamp", ""), rec.get("original", "")
            cand = {
                "kind": "prewar_listing_candidate",
                "host": host, "timestamp": ts,
                "original_url": orig,
                "wayback_url": f"https://web.archive.org/web/{ts}/{orig}",
                "address_verified": None,
            }
            # capture + verify the snapshot text against our address variants
            if n_captured < MAX_CAPTURE:
                try:
                    sr = requests.get(WB_SNAPSHOT.format(ts=ts, url=orig),
                                      headers=http_headers(), timeout=45)
                    time.sleep(PAUSE)
                    if sr.status_code == 200 and sr.content:
                        text = sr.text
                        verified = any(rx.search(text) for rx in regexes)
                        cand["address_verified"] = verified
                        if verified:
                            sha = forensics.capture_source(
                                sr.content, url=cand["wayback_url"],
                                source_type="osint_prewar_listing",
                                title=f"pre-war listing {host} {ts[:8]} {bundle.slug}",
                                description=(f"Pre-war UA real-estate listing snapshot "
                                             f"({host}, {ts}), address-verified against "
                                             f"pid={bundle.pid} variants. Original: {orig}"),
                                content_type=sr.headers.get("Content-Type", "text/html"),
                                http_status=200, con=con,
                            )
                            cand["sha256"] = sha
                            captured.append(sha)
                            n_captured += 1
                except requests.RequestException:
                    log.debug("snapshot fetch failed %s", orig, exc_info=True)
            findings.append(cand)

    n_cand = sum(1 for f in findings if f["kind"] == "prewar_listing_candidate")
    n_ver = sum(1 for f in findings if f.get("address_verified") is True)
    return SourceResult(NAME, True,
                        f"{n_cand} CDX candidates across {len(HOSTS)} hosts, "
                        f"{n_ver} address-verified + captured",
                        findings, captured)
