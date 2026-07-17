"""Source 17 — occupation resale-market listings FOR the address.

A live sale listing for a seized/rebuilt address is the demolish→rebuild→
resell endpoint the project's mass-registry-to-resale case study documents.
This queries the occupation real-estate marketplaces already configured in
config.REALESTATE_TARGETS (avito/cian/domclick/…) with the address as a
search term, capturing result pages for the parser (scripts/51-style) to
extract listings from.

These are Russian, anti-bot, geoblocked sites → RUN=V: the user runs this
from the Russia-routed VPS (config.PROXY), exactly like the court crawler.
Claude never executes it. Captures raw result HTML only (capture-before-
parse); listing extraction stays in the existing resale parser.
"""
from __future__ import annotations

import logging
import time
import urllib.parse

import requests

from ... import config, forensics
from .base import SourceResult

log = logging.getLogger(__name__)

NAME = "resale"
RUN = "V"
NETWORK = True
DESCRIPTION = "occupation resale boards (avito/cian/…) queried FOR this address — VPS"

PAUSE = 3.0


def plan(bundle) -> str:
    n = len(getattr(config, "REALESTATE_TARGETS", []))
    return f"query {n} resale boards with the address as search term, capture result HTML"


def _proxies() -> dict | None:
    if config.PROXY:
        return {"http": config.PROXY, "https": config.PROXY}
    return None


def fetch(bundle, con, radius_m: float = 0.0) -> SourceResult:
    targets = getattr(config, "REALESTATE_TARGETS", [])
    if not targets:
        return SourceResult(NAME, True, "no REALESTATE_TARGETS configured")

    term = bundle.occupation_address or bundle.prewar_address or ""
    if not term:
        return SourceResult(NAME, False, "no address term to search with")
    q = urllib.parse.quote(term)

    findings: list[dict] = []
    captured: list[str] = []
    headers = {"User-Agent": config.USER_AGENT}
    verify = config.SSL_VERIFY

    for t in targets:
        # append the address as a query string; each board's own search
        # param differs, so use a generic ?q= / &text= dual attempt via the
        # entry URL — the parser tightens per-board. Keep it best-effort.
        base = t["entry"]
        sep = "&" if "?" in base else "?"
        board_ok = False
        last_status = None
        last_url = None
        for param in ("q", "text", "search"):
            url = f"{base}{sep}{param}={q}"
            try:
                r = requests.get(url, headers=headers, proxies=_proxies(),
                                 timeout=config.TIMEOUT, verify=verify)
            except requests.RequestException as e:
                log.warning("resale %s query failed: %s", t["key"], e)
                findings.append({"kind": "error", "board": t["key"], "error": str(e)})
                board_ok = True  # exception already logged — don't also log non-200 below
                break
            last_status, last_url = r.status_code, url
            if r.status_code != 200:
                continue
            sha = forensics.capture_source(
                r.content, url=url,
                source_type="osint_resale_query",
                title=f"resale {t['key']} query {bundle.slug}",
                description=(f"Occupation resale board {t['name']} queried for "
                             f"{term!r} (pid={bundle.pid}). Parse for listings "
                             f"referencing this address (scripts/51-style)."),
                content_type=r.headers.get("Content-Type", "text/html"),
                http_status=r.status_code, con=con,
            )
            captured.append(sha)
            findings.append({
                "kind": "resale_query", "board": t["key"], "url": url,
                "http_status": r.status_code, "sha256": sha,
                "note": "raw result page captured; run the resale parser to "
                        "extract listings for this address",
            })
            time.sleep(PAUSE)
            board_ok = True
            break  # first working param wins per board
        if not board_ok:
            log.warning("resale %s: all params returned non-200 (last: %s at %s)",
                       t["key"], last_status, last_url)
            findings.append({"kind": "error", "board": t["key"],
                             "error": f"HTTP {last_status} on all query-param variants "
                                      f"tried (likely anti-bot block)",
                             "url": last_url})

    n_ok = sum(1 for f in findings if f["kind"] == "resale_query")
    return SourceResult(NAME, True,
                        f"{n_ok}/{len(targets)} boards captured a result page",
                        findings, captured)
