"""Stage 1i: capture residential-apartment SALE listings for occupied Mariupol.

Claude must never run this — see CLAUDE.md. Run from the VPS (config.PROXY).

WHY THIS EXISTS
---------------
The demand side of the seizure pipeline ([F] resale, Rome Statute 8(2)(b)(viii)):
seized/rebuilt Mariupol flats being resold into the Russian property market to the
occupier's population. Each live "продаётся квартира в Мариуполе" listing is a
dated, public, self-incriminating artifact — the occupier's own market openly
trading dwellings in occupied territory. Pairing a listing's address with our
seizure spine (ownerless registry / demolition / ЕИСЖС new-build) turns a market
ad into corroboration of disposal.

SCOPE (this pass): offers to SELL RESIDENTIAL APARTMENTS only. The crawler captures
sale-scoped marketplace search pages and the per-listing detail pages verbatim;
the residential-apartment-only filter and field extraction happen in the parser
(scripts/51 — capture before parse). Commercial / land / garages / rentals / wanted
ads are filtered out downstream, not here.

FORENSICS (CLAUDE.md, non-negotiable)
-------------------------------------
- Capture before parse. Every HTTP body (search page AND detail page, including
  anti-bot block pages and 404s — those document the obstruction) is written
  verbatim to data/raw/, SHA-256-keyed, with a .meta.json custody sidecar, BEFORE
  any parsing.
- These are live market listings, not occupation records: they are evidence of an
  open market in occupied-territory property, never valid title. A private seller
  may be an innocent departing resident OR a beneficiary reselling seized stock —
  the parser isolates seller contact PII so shared outputs can minimize it.

ANTI-BOT / GEOBLOCK
-------------------
Avito/CIAN/Domclick are aggressive (JS challenges, IP rate limits) and several are
geoblocked outside Russia. Run from the Russia-routed VPS. We stay polite
(config.REQUEST_DELAY), capture whatever the server returns, and never hammer:
a captured block page is itself a dated record. Targets + caps are in config
(REALESTATE_TARGETS / REALESTATE_MAX_PAGES / REALESTATE_MAX_DETAIL); edit there.

Re-run periodically — the sequence of dated snapshots is a demand-velocity series
(how fast seized stock turns over). Daily around the 01.07.2026 deadline.
"""
from __future__ import annotations

import logging
import random
import re
import time
from urllib.parse import urljoin, urlparse

import requests
import urllib3

from .. import config, forensics

log = logging.getLogger(__name__)

if not config.SSL_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# A listing-detail URL on each marketplace. Used to harvest detail links out of a
# captured search-results page. Deliberately permissive — over-capturing a few
# non-apartment detail pages is harmless (the parser filters); missing real ones
# is not. Keyed by target["key"].
_DETAIL_PATTERNS: dict[str, re.Pattern] = {
    "avito": re.compile(r"/mariupol/kvartiry/[^\"'?#]+_\d{6,}"),
    "cian": re.compile(r"/sale/flat/\d{6,}"),
    "domclick": re.compile(r"/(?:realty|card)/[^\"'?#]*\d{6,}"),
    "mirkvartir": re.compile(r"/prodazha/kvartiry/[^\"'?#]+-\d{5,}"),
    "ayax": re.compile(r"/kvartiry/[^\"'?#]+/\d{4,}"),
    "ligakvartir": re.compile(r"/mariupol/[^\"'?#]*kvartir[^\"'?#]*\d{4,}"),
}


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": config.USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru,en;q=0.8",
    })
    if config.PROXY:
        s.proxies.update({"http": config.PROXY, "https": config.PROXY})
    return s


def _polite_sleep() -> None:
    lo, hi = config.REQUEST_DELAY
    time.sleep(random.uniform(lo, hi))


def _get(s: requests.Session, url: str):
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            return s.get(url, timeout=config.TIMEOUT, verify=config.SSL_VERIFY)
        except requests.RequestException as e:
            wait = min(60, 2 ** attempt)
            log.warning("GET %s failed (attempt %d/%d): %s; wait %ds",
                        url, attempt, config.MAX_RETRIES, e, wait)
            time.sleep(wait)
    log.error("giving up on %s", url)
    return None


def _harvest_detail_links(html: str, base_url: str, key: str) -> list[str]:
    """Pull per-listing detail URLs out of a captured search-results page."""
    pat = _DETAIL_PATTERNS.get(key)
    if pat is None:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for m in pat.finditer(html):
        href = m.group(0)
        absolute = urljoin(base_url, href)
        if absolute not in seen:
            seen.add(absolute)
            out.append(absolute)
    return out


def _capture(con, content: bytes, *, url: str, source_type: str, title: str,
             description: str, content_type: str, http_status: int) -> str:
    return forensics.capture_source(
        content, url=url, source_type=source_type, title=title,
        description=description, content_type=content_type,
        http_status=http_status, con=con,
    )


def _scan_target(s: requests.Session, con, target: dict) -> None:
    key = target["key"]
    name = target["name"]
    detail_urls: list[str] = []

    # 1. Search-result pages (paginated).
    pages = config.REALESTATE_MAX_PAGES if target.get("paginate") else 1
    for page in range(1, pages + 1):
        url = (target["paginate"].format(page=page)
               if target.get("paginate") and page > 1 else target["entry"])
        log.info("[%s] search page %d: %s", key, page, url)
        r = _get(s, url)
        _polite_sleep()
        if r is None:
            break
        sha = _capture(
            con, r.content, url=url,
            source_type="realestate_search_page",
            title=f"{name} — search page {page}",
            description=(f"Sale-scoped Mariupol apartment search results "
                        f"({key}, page {page}). Live market snapshot; "
                        f"parse with scripts/51. HTTP {r.status_code}."),
            content_type=r.headers.get("Content-Type", "text/html"),
            http_status=r.status_code,
        )
        log.info("[%s] captured search page %d: sha=%s… http=%s (%d bytes)",
                 key, page, sha[:12], r.status_code, len(r.content))

        if r.status_code != 200:
            log.warning("[%s] non-200 (%s) — likely block/geoblock; "
                        "captured for the record, stopping pagination",
                        key, r.status_code)
            break

        found = _harvest_detail_links(r.text, url, key)
        for u in found:
            if u not in detail_urls:
                detail_urls.append(u)
        log.info("[%s] page %d → %d detail links (cumulative %d)",
                 key, page, len(found), len(detail_urls))
        if not found and page > 1:
            log.info("[%s] no new listings on page %d — end of results", key, page)
            break

    # 2. Detail pages (bounded by REALESTATE_MAX_DETAIL across the whole run-target).
    for i, url in enumerate(detail_urls[:config.REALESTATE_MAX_DETAIL], 1):
        # Detail pages are stable URLs — skip if already captured this run-day is
        # handled by SHA dedup in forensics; we still re-fetch to snapshot price
        # changes / removal. Use a done-key only to avoid re-fetch within one run.
        done_key = f"realestate:{key}:{urlparse(url).path}"
        if forensics.is_done(con, done_key):
            continue
        log.info("[%s] detail %d/%d: %s", key, i, min(len(detail_urls),
                 config.REALESTATE_MAX_DETAIL), url)
        r = _get(s, url)
        _polite_sleep()
        if r is None:
            continue
        _capture(
            con, r.content, url=url,
            source_type="realestate_listing",
            title=f"{name} — listing",
            description=(f"Individual apartment-sale listing detail page ({key}). "
                        f"Parse for address/price/rooms/area/floor + seller contact "
                        f"(seller PII isolated downstream). HTTP {r.status_code}."),
            content_type=r.headers.get("Content-Type", "text/html"),
            http_status=r.status_code,
        )
        forensics.mark_done(con, done_key)
        if i % 25 == 0:
            log.info("[%s] %d detail pages captured so far", key, i)


def run(only: list[str] | None = None) -> None:
    """Scan every configured marketplace target (or the subset in `only`)."""
    con = forensics.open_state()
    s = make_session()
    targets = [t for t in config.REALESTATE_TARGETS
               if only is None or t["key"] in only]
    if not targets:
        log.error("no matching targets (only=%s)", only)
        return

    for t in targets:
        try:
            _scan_target(s, con, t)
        except Exception:  # noqa: BLE001 — one bad target must not kill the run
            log.exception("[%s] target failed — continuing", t["key"])

    n = con.execute(
        "SELECT COUNT(*) FROM source_document "
        "WHERE source_type IN ('realestate_search_page','realestate_listing')"
    ).fetchone()[0]
    log.info("done — %d real-estate artifacts in store", n)
