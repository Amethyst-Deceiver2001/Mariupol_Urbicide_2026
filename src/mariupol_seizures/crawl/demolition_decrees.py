"""Stage 1c: capture demolition (снос) decrees from the Mariupol admin portal.

Claude must never run this — see CLAUDE.md. Run only from a Russia-routed VPS.

WHY THIS EXISTS
---------------
Beyond the "ownerless" (бесхозяйная) court track, the occupation administration
operates a parallel demolition track under ЖК РФ ст. 15 / ПП РФ № 47: it
declares apartment blocks and other buildings «аварийными и подлежащими сносу»
(emergency, subject to demolition), then razes them and hands the cleared land
to developer SPVs without auction. The replacement building is assigned a NEW
address and a NEW cadastral number — severing the identity chain to the original
property and defeating RD4U restitution claims
("такого адреса в Мариуполе физически не существует", Morhun, 2024).

The Russian state's own ЕИСЖС registry self-incriminates: e.g. the building at
пер. Черноморский 1Б (built Q4 2023, developer ООО «СЗ-1 «Порфир»», ИНН
9310009271) is listed there under the project name «Дом на Нахимова» — proving
same-spot identity (name) while the registered address destroys the paper trail.

This script captures the OLD side of that crosswalk: the signed demolition
постановления from mariupol.gosuslugi.ru, with their per-building перечни
attachments (same scanned-PDF format as the ownerless annexes). The new-side
crosswalk (ЕИСЖС / наш.дом.рф) is a separate research artefact.

As of 2026-06-09 the search returns 6 decrees (2024-11 → 2026-05), no
pagination. The register is live — re-run to catch new demolition waves.

WHAT THIS CAPTURES
------------------
Per decree: the HTML detail page (signing official, date, legal basis) + each
PDF annex (перечень зданий — building address, description, committee reference).
Source types follow the same convention as ownerless_lists.py so the OCR and
parse stages can handle both families uniformly:
  demolition_decree_{kind}        HTML page
  demolition_decree_{kind}_pdf    scanned PDF annex

Kinds:
  mkd         — многоквартирные дома, аварийные (ЖК РФ track)
  oks         — объекты капитального строительства
  building    — здания (generic building category)
  amendment   — внесение изменений в prior decree
  unknown     — doesn't match any of the above classifiers
"""
from __future__ import annotations

import logging
import re
import time
from urllib.parse import urljoin, urlencode

import requests
import urllib3
from bs4 import BeautifulSoup

from .. import config, forensics

log = logging.getLogger(__name__)

if not config.SSL_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ORIGIN = "https://mariupol.gosuslugi.ru"
MIRROR_ORIGIN = "https://mariupol-r897.gosweb.gosuslugi.ru"

# Search endpoint — note different path and cc than ownerless_lists.py.
# cc=469 is the "документы" section; document_search filters by title keyword.
SEARCH_PATH = "/ofitsialno/dokumenty/"
SEARCH_CC = "469"
SEARCH_PAGE_SIZE = 20

# Two search terms sweep the full register:
#   "подлежащими сносу"  — catches all variants (MKD, OKS, buildings, amendments)
#   "аварийными"         — belt-and-suspenders for MKD track
# Results are deduped by URL (seen_urls) and by SHA-256 in forensics.
SEARCH_TERMS = [
    "подлежащими сносу",
    "аварийными",
]

# ── decree classifiers ────────────────────────────────────────────────────────
# Order: amendment first (a title like «О внесении изменений в постановление
# … о признании МКД аварийными» has both amendment and MKD markers — we want
# the outer category).
_DEM_AMENDMENT = re.compile(r"внесени\w+\s+изменени", re.I)
_DEM_MKD = re.compile(r"многоквартирн", re.I)
_DEM_OKS = re.compile(r"объект\w+\s+капитальн", re.I)
_DEM_BUILDING = re.compile(r"здани[йяе]", re.I)


def _classify(title: str) -> str:
    if _DEM_AMENDMENT.search(title):
        return "amendment"
    if _DEM_MKD.search(title):
        return "mkd"
    if _DEM_OKS.search(title):
        return "oks"
    if _DEM_BUILDING.search(title):
        return "building"
    return "unknown"


# ── HTTP helpers (mirrors ownerless_lists.py exactly) ─────────────────────────

def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": config.USER_AGENT, "Accept-Language": "ru,en;q=0.8"})
    if config.PROXY:
        s.proxies.update({"http": config.PROXY, "https": config.PROXY})
    return s


def polite_sleep() -> None:
    time.sleep(2.0)


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


# ── search-page crawl ─────────────────────────────────────────────────────────

def _search_url(origin: str, term: str, cur_pos: int) -> str:
    params: dict = {
        "cc": SEARCH_CC,
        "document_search": term,
        "document_category": "",
        "document_publication_date": "",
    }
    if cur_pos:
        params["curPos"] = cur_pos
    return urljoin(origin, SEARCH_PATH) + "?" + urlencode(params)


def _extract_decree_links(soup: BeautifulSoup, origin: str) -> list[tuple[str, str, str]]:
    """Return list of (url, title, kind) for each decree anchor on the page.

    Filters out section/breadcrumb links (no decree number in the title).
    """
    results = []
    for a in soup.find_all("a", href=re.compile(r"postanovleniya-administratsii")):
        title = a.get_text(" ", strip=True)
        if not title or "Постановлен" not in title:
            continue
        m = re.search(r"№\s*(\d+)", title)
        if not m:
            continue  # breadcrumb / nav link with no number
        url = urljoin(origin, a["href"])
        kind = _classify(title)
        results.append((url, title, kind))
    return results


def _extract_pdf_links(soup: BeautifulSoup, origin: str) -> list[str]:
    """Return absolute URLs of all PDF attachments on a decree detail page."""
    return [
        urljoin(origin, a["href"])
        for a in soup.find_all("a", href=re.compile(r"\.pdf", re.I))
        if a.get("href")
    ]


def capture_search_results(s: requests.Session, con, origin: str) -> list[tuple[str, str, str]]:
    """Walk all search terms; return deduplicated list of (url, title, kind)."""
    seen_urls: set[str] = set()
    all_decrees: list[tuple[str, str, str]] = []

    for term in SEARCH_TERMS:
        cur_pos = 0
        while True:
            url = _search_url(origin, term, cur_pos)
            r = _get(s, url)
            polite_sleep()
            if r is None or r.status_code != 200:
                log.warning("search page unavailable: %s", url)
                break
            forensics.capture_source(
                r.content, url=url,
                source_type="demolition_list_index",
                title=f"Mariupol demolition decrees index — «{term}», offset {cur_pos}",
                description=(
                    "Search results page: постановления Администрации городского "
                    "округа Мариуполь recognising buildings as subject to "
                    f"demolition (снос). Search term: «{term}»."
                ),
                content_type=r.headers.get("Content-Type", "text/html"),
                http_status=r.status_code, con=con,
            )
            soup = BeautifulSoup(r.text, "lxml")
            page_decrees = _extract_decree_links(soup, origin)
            new = [(u, t, k) for u, t, k in page_decrees if u not in seen_urls]
            if not new:
                log.info("term «%s» offset %d: no new URLs — done", term, cur_pos)
                break
            for u, t, k in new:
                seen_urls.add(u)
            all_decrees.extend(new)
            log.info("term «%s» offset %d: %d new decrees (total %d)",
                     term, cur_pos, len(new), len(all_decrees))
            cur_pos += SEARCH_PAGE_SIZE

    log.info("search complete: %d unique demolition decrees found", len(all_decrees))
    return all_decrees


# ── decree + PDF capture ──────────────────────────────────────────────────────

def capture_decree_pages(
    s: requests.Session,
    con,
    decrees: list[tuple[str, str, str]],
    origin: str,
) -> None:
    """Capture each decree's HTML page and every PDF annex linked from it."""
    for dec_url, title, kind in decrees:
        page_key = f"demolition::{dec_url}"
        if forensics.is_done(con, page_key):
            log.debug("skip (already done): %s", dec_url)
            continue

        r = _get(s, dec_url)
        polite_sleep()
        if r is None or r.status_code != 200:
            log.warning("decree page not fetched: %s", dec_url)
            continue

        m = re.search(r"№\s*(\d+)", title)
        decree_no = m.group(1) if m else "?"
        forensics.capture_source(
            r.content, url=dec_url,
            source_type=f"demolition_decree_{kind}",
            title=title,
            description=(
                f"Demolition decree №{decree_no} ({kind}). "
                "Signed by the Mariupol occupation administration; "
                "names the issuing official (in scope for accountability). "
                "Legal basis: ЖК РФ ст. 15, ПП РФ № 47 (28.01.2006). "
                "This is evidence of the OLD address — the cleaned plot is "
                "reallocated under a new address, severing RD4U claim chains."
            ),
            content_type=r.headers.get("Content-Type", "text/html"),
            http_status=r.status_code, con=con,
        )

        soup = BeautifulSoup(r.text, "lxml")
        for pdf_url in _extract_pdf_links(soup, origin):
            pdf_key = f"demolition_pdf::{pdf_url}"
            if forensics.is_done(con, pdf_key):
                continue
            pr = _get(s, pdf_url)
            polite_sleep()
            if pr is None or pr.status_code != 200:
                log.warning("decree PDF not fetched: %s", pdf_url)
                continue
            ct = pr.headers.get("Content-Type", "application/pdf")
            forensics.capture_source(
                pr.content, url=pdf_url,
                source_type=f"demolition_decree_{kind}_pdf",
                title=f"{title} [PDF annex]",
                description=(
                    f"Demolition decree №{decree_no} ({kind}) — PDF annex "
                    "(перечень зданий / объектов). Scanned image; run 06a_ocr "
                    "to add a text layer before parsing. Contains building "
                    "addresses, description, межведомственная комиссия "
                    "references — the primary OLD-address evidence payload for "
                    "the demolition→rebuild footprint crosswalk."
                ),
                content_type=ct, http_status=pr.status_code, con=con,
            )
            forensics.mark_done(con, pdf_key)
            log.info("captured decree №%s PDF: %s", decree_no, pdf_url)

        forensics.mark_done(con, page_key)
        log.info("captured decree №%s (%s): %s", decree_no, kind, title[:80])


# ── entry point ───────────────────────────────────────────────────────────────

def run() -> None:
    con = forensics.open_state()
    s = make_session()
    for origin in (ORIGIN, MIRROR_ORIGIN):
        try:
            log.info("== demolition decrees: %s ==", origin)
            decrees = capture_search_results(s, con, origin)
            capture_decree_pages(s, con, decrees, origin)
        except KeyboardInterrupt:
            log.warning("interrupted — state saved, safe to rerun.")
            break
        except Exception:
            log.exception("%s errored — continuing to next origin", origin)

    n = con.execute(
        "SELECT COUNT(*) FROM source_document WHERE source_type LIKE 'demolition_%'"
    ).fetchone()[0]
    log.info("done; %d demolition-source artifacts in store", n)
