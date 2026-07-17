"""Source 23 — archive-copy lookup for every original-source URL already on
record for this property (local_evidence's `collect_source_urls()`).

For each URL, checks:
  1. **Wayback Machine** — reliable public API (`archive.org/wayback/
     available`), no key. Works even for geoblocked-from-here sources,
     since Wayback's own crawler isn't Russia-blocked the way this
     project's fetches are.
  2. **archive.today** (archive.ph/is/li/vn — same service, several TLDs) —
     no official API; best-effort via `archive.ph/newest/<url>`, which
     302s to the latest snapshot if one exists. archive.today is known to
     rate-limit/Cloudflare-gate scripted access, so a "not found" result
     here is NOT proof no snapshot exists — flagged as best-effort in the
     dossier, matching the project's own "geoblock ≠ omit the link" stance:
     absence of an automated hit just means check manually.

This module never fetches the ORIGINAL geoblocked page itself — only asks
two third-party archive services whether THEY already have a copy. Safe to
run from anywhere, no VPN/VPS needed.
"""
from __future__ import annotations

import logging
import time

import requests

from ... import forensics
from .base import SourceResult, http_headers
from .local_evidence import collect_source_urls

log = logging.getLogger(__name__)

NAME = "archives"
RUN = "C"
NETWORK = True
DESCRIPTION = "Wayback Machine + archive.today lookup for every on-record source URL"

WAYBACK_AVAILABLE = "https://archive.org/wayback/available"
ARCHIVE_TODAY_NEWEST = "https://archive.ph/newest/{url}"
MAX_URLS = 40
PAUSE = 0.3


def plan(bundle) -> str:
    return "for each collect_source_urls() row: Wayback available-API + archive.ph/newest best-effort"


def _check_wayback(url: str) -> dict | None:
    for attempt in range(3):
        try:
            r = requests.get(WAYBACK_AVAILABLE, params={"url": url},
                             headers=http_headers(), timeout=20)
        except requests.RequestException:
            log.debug("wayback check failed for %s", url, exc_info=True)
            return None
        if r.status_code == 429:
            wait = 5.0 * (attempt + 1)
            log.warning("wayback 429, backing off %.0fs (attempt %d/3)", wait, attempt + 1)
            time.sleep(wait)
            continue
        try:
            r.raise_for_status()
        except requests.RequestException:
            log.debug("wayback error for %s: %s", url, r.status_code)
            return None
        snap = r.json().get("archived_snapshots", {}).get("closest")
        if not snap or not snap.get("available"):
            return None
        return {"archived_url": snap.get("url"), "timestamp": snap.get("timestamp")}
    log.warning("wayback still 429 after retries for %s — treating as unknown, "
               "not confirmed-absent", url)
    return {"rate_limited": True}


def _check_archive_today(url: str) -> dict | None:
    try:
        r = requests.get(ARCHIVE_TODAY_NEWEST.format(url=url),
                         headers=http_headers(), timeout=20,
                         allow_redirects=True)
    except requests.RequestException:
        log.debug("archive.today check failed for %s", url, exc_info=True)
        return None
    # a real snapshot redirect lands on archive.ph/<hash>/<original-url>;
    # "newest" with no snapshot serves its own search/submit page at the
    # SAME url (no redirect) — so "did the URL change" is the signal.
    if r.url and r.url != ARCHIVE_TODAY_NEWEST.format(url=url) and "/newest/" not in r.url:
        return {"archived_url": r.url}
    return None


def fetch(bundle, con, radius_m: float = 150.0) -> SourceResult:
    urls = collect_source_urls(bundle)
    if not urls:
        return SourceResult(NAME, True, "no original-source URLs on record for this property")

    findings: list[dict] = []
    n_wayback = n_archive_today = n_rate_limited = 0
    for src in urls[:MAX_URLS]:
        url = src["url"]
        wb = _check_wayback(url)
        time.sleep(PAUSE)
        at = _check_archive_today(url)
        time.sleep(PAUSE)
        wb_rate_limited = bool(wb and wb.get("rate_limited"))
        if wb and not wb_rate_limited:
            n_wayback += 1
        if wb_rate_limited:
            n_rate_limited += 1
        if at:
            n_archive_today += 1
        findings.append({
            "kind": "archive_match",
            "url": url,
            "geoblocked": src["geoblocked"],
            "via": src["via"],
            "wayback_url": "" if wb_rate_limited else (wb or {}).get("archived_url", ""),
            "wayback_timestamp": "" if wb_rate_limited else (wb or {}).get("timestamp", ""),
            "wayback_rate_limited": wb_rate_limited,
            "archive_today_url": (at or {}).get("archived_url", ""),
            "archive_today_note": "" if at else "no automated hit — check manually, "
                                                  "archive.today rate-limits scripts",
        })

    if len(urls) > MAX_URLS:
        findings.append({"kind": "archives_overflow", "total": len(urls),
                         "checked": MAX_URLS})

    rl_note = f", {n_rate_limited} Wayback checks rate-limited (re-run to retry)" if n_rate_limited else ""
    return SourceResult(
        NAME, True,
        f"{len(findings)} URLs checked, {n_wayback} on Wayback, "
        f"{n_archive_today} on archive.today (automated hits only){rl_note}",
        findings)
