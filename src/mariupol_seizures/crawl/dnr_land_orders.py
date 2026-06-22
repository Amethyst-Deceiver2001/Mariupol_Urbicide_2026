"""Stage 1d: capture DNR head's land-allocation распоряжения for Mariupol.

Claude must never run this — see CLAUDE.md. Can run locally or from VPS
(portal is not geoblocked, but use VPS to keep capture provenance uniform).

WHY THIS EXISTS
---------------
The DNR legislative portal publishes распоряжения Главы ДНР that allocate
cleared Mariupol land parcels to developer SPVs **without auction**
("в аренду без проведения торгов").  Each order names:
  - the beneficiary (accountability-track subject)
  - the cadastral number of the parcel
  - the address on which the replacement building will be erected

This is the RIGHT-HAND side of the demolish→rebuild footprint crosswalk:

  demolition_decrees.jsonl   (old address — condemned building)
  ↕  cadastral / address match
  dnr_land_orders            (parcel → beneficiary — allocation act)
  ↕  ЕГРЮЛ / ЕИСЖС
  new building registered under new address

Named developer beneficiaries confirmed by reconnaissance (2026-06-09):
  ООО СЗ ЭВОЛДОМ-5 (≥7 orders 2025-06 → 2025-11)
  АО «ЭВЕРЕСТ ДОМОСТРОЕНИЕ» (распоряжение №192, 05.06.2026 — cadastral
    93:37:0010318:779, ул. Станиславского 56, 17 552 m²)

Also captures:
  Указ Главы ДНР №420 (30.07.2022) «концепция разработки генплана Мариуполя»
  — the top-of-chain legal authority for the demolish-rebuild programme.

WHAT THIS CAPTURES
------------------
Per order: the HTML detail page (beneficiary, cadastral number, address, date,
legal basis) + the PDF attachment (signed original).  Source types:
  dnr_land_order        HTML page
  dnr_land_order_pdf    PDF attachment (signed original)

Portal: https://xn--80azg.xn--80ahqgjaddr.xn--p1ai/
  (WordPress-based; search at /?s=TERM; pagination at /page/N/?s=TERM)
"""
from __future__ import annotations

import logging
import re
import time
from urllib.parse import quote_plus, urljoin

import requests
import urllib3
from bs4 import BeautifulSoup

from .. import config, forensics

log = logging.getLogger(__name__)

# Suppress InsecureRequestWarning if SSL verification is disabled project-wide.
if not config.SSL_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ORIGIN = "https://xn--80azg.xn--80ahqgjaddr.xn--p1ai"

# Search terms that collectively sweep the relevant corpus.
#
# GROUP 1 — Topical (catch all no-auction land-allocation orders for Mariupol).
# "земельного участка" catches the standard decree form.
# "генеральный план" catches Указ №420 (master-plan authority decree).
#
# GROUP 2 — Company-specific (catch orders for the 6 developer INNs that are
# registered in ЕИСЖС but whose land orders were not returned by the topical
# queries, likely because they were issued in 2024–2025 under variant titles
# or deeper pagination).
#
# ЕИСЖС → INN → full legal name (from ЕИСЖС developer block):
#   9303038232  ООО СЗ ЭВОДОМ-5 (also try ЭВОЛДОМ variant)
#   9311026992  ООО СЗ СОЛНЕЧНАЯ
#   9310017508  ООО СЗ КОРПОРАЦИЯ СМУ-5
#   9310015807  ООО СЗ СТРОИТЕЛЬНОЕ УПРАВЛЕНИЕ-2007 ИНВЕСТ
#   9310014320  ООО СЗ СИРИУС БИЛД
#   9309026106  ООО СЗ РЕГИОНАЛЬНАЯ СТРОИТЕЛЬНАЯ КОМПАНИЯ
#
# GROUP 3 — Street-specific fallback (for projects on streets not mentioned
# in the topical queries; complements company-name searches).
SEARCH_TERMS = [
    # Group 1 — topical
    "Мариуполь земельного участка",
    "Мариуполь предоставлении земельного",
    "Мариуполь генеральный план",
    # Group 2 — company-name targeted (one per uncovered INN)
    "ЭВОДОМ-5",
    "ЭВОЛДОМ",          # variant spelling seen in reconnaissance
    "СОЛНЕЧНАЯ застройщик",
    "СМУ-5 Мариуполь",
    "Строительное управление-2007 Инвест",
    "Сириус Билд",
    "Региональная строительная компания Мариуполь",
    # Group 3 — street-specific fallback
    "Зелинского земельного участка",
    "Покрышкина земельного участка",
    "Куприна земельного участка",
    "Маршала Жукова земельного участка",
    "Миклухо-Маклая земельного участка",
]

# A Mariupol-relevant result must have at least one of these strings in the
# title or excerpt.  Catches land-parcel orders, master-plan decrees, and
# demolition-authorising acts while skipping veterinary / quarantine noise.
_RELEVANT = re.compile(
    r"земельн\w+\s+участ|предоставлен\w+|генеральн\w+\s+план"
    r"|снос|аварийн|реконструкц|мариуполь"
    r"|эводом|эволдом|солнечная|сму.5|сириус.билд|покрышкин|зелинск",
    re.I,
)

# Decree number: «№ 192» or «N 192»
_DECREE_NO = re.compile(r"№\s*(\d+)")


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
            log.warning("GET %s failed (%d/%d): %s; wait %ds",
                        url, attempt, config.MAX_RETRIES, e, wait)
            time.sleep(wait)
    log.error("giving up on %s", url)
    return None


def _search_url(term: str, page: int) -> str:
    q = quote_plus(term)
    if page <= 1:
        return f"{ORIGIN}/?s={q}"
    return f"{ORIGIN}/page/{page}/?s={q}"


def _extract_result_links(soup: BeautifulSoup) -> list[tuple[str, str]]:
    """Return (absolute_url, title_text) for each document link on a results page.

    The portal uses a WordPress theme; document titles are in <h2> or <h3>
    elements containing an <a> that links to the document page.  We accept any
    <a> whose href matches the /{date}/{slug}.html pattern.
    """
    found: list[tuple[str, str]] = []
    slug_re = re.compile(r"/\d{4}-\d{2}-\d{2}/[^/]+\.html$")
    for a in soup.find_all("a", href=slug_re):
        title = a.get_text(" ", strip=True)
        if not title:
            # Title may be in the parent element
            parent = a.find_parent(["h2", "h3", "h4"])
            if parent:
                title = parent.get_text(" ", strip=True)
        if title:
            found.append((urljoin(ORIGIN, a["href"]), title))
    return found


def _has_next_page(soup: BeautifulSoup) -> bool:
    """True if the results page has a 'next' pagination link."""
    for a in soup.find_all("a", class_=re.compile(r"next|следующ", re.I)):
        return True
    # WordPress numeric pagination: look for a link to /page/N+1/
    next_re = re.compile(r"/page/\d+/")
    current_page_els = soup.find_all(class_=re.compile(r"current|active"))
    for el in current_page_els:
        try:
            current = int(el.get_text(strip=True))
            if soup.find("a", href=re.compile(f"/page/{current + 1}/")):
                return True
        except (ValueError, AttributeError):
            pass
    return False


# Older PDFs on this portal are served from doc.нпа.днронлайн.рф, a subdomain
# that doesn't resolve outside Russia (DNS failure).  The /wp-content/uploads/
# path is shared with the main origin, so a host rewrite recovers the file
# without needing Russia-routed access.
_DOC_SUBDOMAIN = re.compile(r"^https?://[^/]*doc\.[^/]+", re.I)


def _normalize_pdf_url(url: str) -> str:
    m = _DOC_SUBDOMAIN.match(url)
    if m:
        return ORIGIN + url[m.end():]
    return url


def _extract_pdf_links(soup: BeautifulSoup) -> list[str]:
    """Return absolute URLs of PDF attachments on a document page."""
    urls = []
    for a in soup.find_all("a", href=re.compile(r"\.pdf", re.I)):
        href = a.get("href", "")
        if href:
            raw = href if href.startswith("http") else urljoin(ORIGIN, href)
            urls.append(_normalize_pdf_url(raw))
    return urls


def capture_search_results(s: requests.Session, con) -> list[tuple[str, str]]:
    """Walk all search terms and return deduplicated (url, title) list."""
    seen_urls: set[str] = set()
    all_results: list[tuple[str, str]] = []

    for term in SEARCH_TERMS:
        page = 1
        while True:
            url = _search_url(term, page)
            r = _get(s, url)
            polite_sleep()
            if r is None or r.status_code != 200:
                log.warning("search page unavailable: %s", url)
                break

            forensics.capture_source(
                r.content, url=url,
                source_type="dnr_land_order_index",
                title=f"DNR land-order search index — «{term}», page {page}",
                description=(
                    "Search-results page from the DNR legislative portal "
                    f"(xn--80azg.xn--80ahqgjaddr.xn--p1ai) for «{term}». "
                    "Contains распоряжения Главы ДНР allocating Mariupol land "
                    "parcels to developer beneficiaries without auction."
                ),
                content_type=r.headers.get("Content-Type", "text/html"),
                http_status=r.status_code, con=con,
            )

            soup = BeautifulSoup(r.text, "lxml")
            page_results = _extract_result_links(soup)
            new = [(u, t) for u, t in page_results if u not in seen_urls]

            if not new:
                log.info("term «%s» page %d: no new results — done", term, page)
                break

            for u, t in new:
                seen_urls.add(u)
            all_results.extend(new)
            log.info("term «%s» page %d: %d new results (total %d)",
                     term, page, len(new), len(all_results))

            if not _has_next_page(soup):
                break
            page += 1

    log.info("search complete: %d unique document pages found", len(all_results))
    return all_results


def capture_document_pages(
    s: requests.Session,
    con,
    results: list[tuple[str, str]],
) -> None:
    """Capture each document's HTML page and every PDF attachment."""
    for doc_url, title in results:
        page_key = f"dnr_order::{doc_url}"
        if forensics.is_done(con, page_key):
            log.debug("skip (already done): %s", doc_url)
            continue

        r = _get(s, doc_url)
        polite_sleep()
        if r is None or r.status_code != 200:
            log.warning("document page not fetched: %s", doc_url)
            continue

        m = _DECREE_NO.search(title)
        decree_no = m.group(1) if m else "?"

        forensics.capture_source(
            r.content, url=doc_url,
            source_type="dnr_land_order",
            title=title,
            description=(
                f"DNR head's распоряжение №{decree_no} — HTML page. "
                "Names the beneficiary (company or individual), the cadastral "
                "number and address of the allocated land parcel, and the legal "
                "basis for no-auction allocation. Named beneficiaries are "
                "accountability-track subjects per CLAUDE.md (officials / "
                "beneficiaries acting in official capacity)."
            ),
            content_type=r.headers.get("Content-Type", "text/html"),
            http_status=r.status_code, con=con,
        )

        soup = BeautifulSoup(r.text, "lxml")
        for pdf_url in _extract_pdf_links(soup):
            pdf_key = f"dnr_order_pdf::{pdf_url}"
            if forensics.is_done(con, pdf_key):
                continue
            pr = _get(s, pdf_url)
            polite_sleep()
            if pr is None or pr.status_code != 200:
                log.warning("PDF not fetched: %s", pdf_url)
                continue
            ct = pr.headers.get("Content-Type", "application/pdf")
            forensics.capture_source(
                pr.content, url=pdf_url,
                source_type="dnr_land_order_pdf",
                title=f"{title} [PDF]",
                description=(
                    f"DNR head's распоряжение №{decree_no} — signed PDF original. "
                    "Contains the beneficiary name, cadastral number, land parcel "
                    "area, address, and no-auction legal basis. "
                    "Right-hand side of the demolish→rebuild footprint crosswalk."
                ),
                content_type=ct, http_status=pr.status_code, con=con,
            )
            forensics.mark_done(con, pdf_key)
            log.info("captured распоряжение №%s PDF: %s", decree_no, pdf_url)

        forensics.mark_done(con, page_key)
        log.info("captured распоряжение №%s: %s", decree_no, title[:80])


def run() -> None:
    con = forensics.open_state()
    s = make_session()
    try:
        results = capture_search_results(s, con)
        capture_document_pages(s, con, results)
    except KeyboardInterrupt:
        log.warning("interrupted — state saved, safe to rerun.")

    n = con.execute(
        "SELECT COUNT(*) FROM source_document WHERE source_type LIKE 'dnr_%'"
    ).fetchone()[0]
    log.info("done; %d DNR-portal artifacts in store", n)
