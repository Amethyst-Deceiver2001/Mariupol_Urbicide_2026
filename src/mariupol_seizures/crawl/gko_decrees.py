"""Stage 1f: capture ГКО ДНР framework decrees from нпа.днронлайн.рф.

Claude must never run this — see CLAUDE.md. Run from VPS for provenance.

WHY THIS EXISTS
---------------
The Государственный комитет обороны ДНР (GKO DNR — State Defense Committee)
was the wartime governing body of the self-proclaimed DNR. It was dissolved on
30 September 2022 when DNR was formally absorbed into Russia. In its final
months it issued the legal framework authorising the demolition of all
war-damaged buildings in Mariupol and the reallocation of cleared land:

  Постановление №162 (23.07.2022) — Порядок сноса зданий и сооружений,
    повреждённых в результате ведения боевых действий. Defines the commission
    procedure, inspection requirements, and demolition authorisation chain.
    Signed: Д.В. Пушилин (Chairman GKO / Head DNR).

  Постановление №205 (27.08.2022) — Amendment to №162: adds mandatory
    review step by the Operational Headquarters for Reconstruction of DNR
    before a local administration demolition order can be forwarded to the
    Head Administration.

  Постановление №245 (19.09.2022) — Further amendment to №162 (full text
    needed; referenced in №162 revised text as the third amendment).

These three documents are the TOP OF THE CHAIN for all Mariupol demolitions:
every building condemned and demolished cites one of these as legal basis.
They pre-date and authorise GKO Распоряжение №56 (29.09.2022) — the Mariupol-
specific demolition list that triggered the demolition of ТСЖ «Троянда-М»
and many other buildings (case 33-2575/2025).

WHAT THIS CAPTURES
------------------
Source type: gko_decree_html (HTML) + gko_decree_pdf (PDF attachment if any).

Target: нпа.днронлайн.рф — the DNR normative-acts archive that survived
post-integration and remains the canonical published location of GKO acts.

Распоряжение №56 (the Mariupol demolition list) is NOT on this portal —
it is an operational order (not a normative act), likely internal or published
only on the mariupol.gosuslugi.ru admin portal circa Sep-Oct 2022. A separate
targeted search for pre-integration documents on the admin portal is needed.
"""
from __future__ import annotations

import logging
import re
import time
from urllib.parse import urljoin

import requests
import urllib3
from bs4 import BeautifulSoup

from .. import config, forensics

log = logging.getLogger(__name__)

if not config.SSL_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# нпа.днронлайн.рф Punycode — same domain as the DNR land-orders portal
ORIGIN = "https://xn--80azg.xn--80ahqgjaddr.xn--p1ai"

# Known GKO ДНР framework decrees — capture these immediately.
# Tuple: (url, source_type_suffix, title, description)
KNOWN_GKO_DOCS: list[tuple[str, str, str, str]] = [
    (
        "https://xn--80azg.xn--80ahqgjaddr.xn--p1ai/2022-07-23/"
        "postanovlenie-gosudarstvennogo-komiteta-oborony-dnr-162-ot-23-07-2022-g-"
        "ob-utverzhdenii-poryadka-snosa-zdanij-i-sooruzhenij-"
        "povrezhdennyh-v-rezultate-vedeniya-boevyh-dejstvij.html",
        "gko_decree_html",
        "Постановление ГКО ДНР №162 от 23.07.2022 — Порядок сноса зданий и сооружений",
        "Top-of-chain legal authority for all Mariupol demolitions. "
        "Establishes the commission procedure, inspection and technical assessment "
        "requirements, and authorisation chain for demolishing war-damaged buildings. "
        "Signed Д.В. Пушилин. Amended by №205 (27.08.2022) and №245 (19.09.2022). "
        "Cited in every demolition decree and court case.",
    ),
    (
        "https://xn--80azg.xn--80ahqgjaddr.xn--p1ai/2022-08-27/"
        "postanovlenie-gosudarstvennogo-komiteta-oborony-dnr-205-ot-27-08-2022-g-"
        "o-vnesenii-izmenenii-v-postanovlenie-gosudarstvennogo-"
        "komiteta-oborony-donetskoj-narodnoj-respubliki-ot-23-iyulya-2022-goda-162.html",
        "gko_decree_html",
        "Постановление ГКО ДНР №205 от 27.08.2022 — Поправки к Постановлению №162",
        "Amendment to №162: adds mandatory review by the Operational Headquarters "
        "for Reconstruction of DNR before local administration demolition orders "
        "can proceed. Introduces an additional approval layer between the local "
        "commission conclusion and the final GKO demolition распоряжение.",
    ),
]

# Search terms to find additional GKO documents on the portal.
GKO_SEARCH_TERMS = [
    "Государственного комитета обороны снос Мариуполь",
    "ГКО ДНР распоряжение снос",
    "постановление 245 2022 снос",
    # Распоряжение №56 (29.09.2022) — specific Mariupol demolition list cited in
    # case 33-2575/2025. Operational orders are typically not on normative-acts
    # portals but searching anyway; may appear if published post-integration.
    "распоряжение 56 сноса объектов Мариуполь",
]


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": config.USER_AGENT,
        "Accept-Language": "ru,en;q=0.8",
    })
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


def _extract_pdf_links(soup: BeautifulSoup, page_url: str) -> list[str]:
    urls = []
    for a in soup.find_all("a", href=re.compile(r"\.pdf", re.I)):
        href = a.get("href", "")
        if href:
            urls.append(href if href.startswith("http") else urljoin(page_url, href))
    return urls


def capture_known_docs(s: requests.Session, con) -> None:
    """Capture each known GKO decree HTML page and any PDF attachment."""
    for url, source_type, title, description in KNOWN_GKO_DOCS:
        key = f"gko_decree::{url}"
        if forensics.is_done(con, key):
            log.debug("skip (already done): %s", title)
            continue

        r = _get(s, url)
        polite_sleep()
        if r is None or r.status_code != 200:
            log.warning("decree not fetched: %s (HTTP %s)",
                        title, r.status_code if r else "N/A")
            continue

        forensics.capture_source(
            r.content, url=url,
            source_type=source_type,
            title=title,
            description=description,
            content_type=r.headers.get("Content-Type", "text/html"),
            http_status=r.status_code, con=con,
        )

        # Capture any PDF attachments
        soup = BeautifulSoup(r.text, "lxml")
        for pdf_url in _extract_pdf_links(soup, url):
            pdf_key = f"gko_decree_pdf::{pdf_url}"
            if forensics.is_done(con, pdf_key):
                continue
            pr = _get(s, pdf_url)
            polite_sleep()
            if pr is None or pr.status_code != 200:
                log.warning("PDF not fetched: %s", pdf_url)
                continue
            forensics.capture_source(
                pr.content, url=pdf_url,
                source_type="gko_decree_pdf",
                title=f"{title} [PDF]",
                description=f"Signed PDF original of: {description}",
                content_type=pr.headers.get("Content-Type", "application/pdf"),
                http_status=pr.status_code, con=con,
            )
            forensics.mark_done(con, pdf_key)
            log.info("captured PDF: %s", pdf_url)

        forensics.mark_done(con, key)
        log.info("captured: %s", title)


def search_for_additional(s: requests.Session, con) -> None:
    """Search нпа.днронлайн.рф for additional GKO demolition-related documents.

    Specifically looking for:
    - Постановление ГКО ДНР №245 from 19.09.2022
    - Any GKO Распоряжение listing specific Mariupol buildings for demolition
      (operational orders — may not be on this normative-acts portal)
    """
    from urllib.parse import quote_plus
    slug_re = re.compile(r"/\d{4}-\d{2}-\d{2}/[^/]+\.html$")

    for term in GKO_SEARCH_TERMS:
        url = f"{ORIGIN}/?s={quote_plus(term)}"
        r = _get(s, url)
        polite_sleep()
        if r is None or r.status_code != 200:
            log.warning("search unavailable: %s", url)
            continue

        forensics.capture_source(
            r.content, url=url,
            source_type="gko_decree_search_index",
            title=f"НПА ДНР search — «{term}»",
            description=(
                f"Search results from нпа.днронлайн.рф for «{term}». "
                "Captured to document search state and locate GKO ДНР "
                "demolition-related normative acts, especially №245 and "
                "any Распоряжения listing specific Mariupol buildings."
            ),
            content_type=r.headers.get("Content-Type", "text/html"),
            http_status=r.status_code, con=con,
        )

        soup = BeautifulSoup(r.text, "lxml")
        for a in soup.find_all("a", href=slug_re):
            title_text = a.get_text(" ", strip=True)
            href = a["href"]
            doc_url = href if href.startswith("http") else urljoin(ORIGIN, href)

            # Only capture GKO documents not already known
            if any(doc_url in known[0] for known in KNOWN_GKO_DOCS):
                continue
            if "gosudarstvennogo-komiteta" not in doc_url and "gko" not in doc_url.lower():
                if "245" not in doc_url and "снос" not in title_text.lower():
                    log.debug("skip non-GKO result: %s", title_text[:60])
                    continue

            key = f"gko_decree::{doc_url}"
            if forensics.is_done(con, key):
                continue

            dr = _get(s, doc_url)
            polite_sleep()
            if dr is None or dr.status_code != 200:
                log.warning("doc not fetched: %s", doc_url)
                continue

            forensics.capture_source(
                dr.content, url=doc_url,
                source_type="gko_decree_html",
                title=title_text or doc_url,
                description=(
                    f"GKO ДНР decree found via search «{term}». "
                    "May be Постановление №245 or a Распоряжение listing "
                    "Mariupol buildings for demolition."
                ),
                content_type=dr.headers.get("Content-Type", "text/html"),
                http_status=dr.status_code, con=con,
            )
            forensics.mark_done(con, key)
            log.info("captured additional GKO doc: %s", title_text[:80])


def run() -> None:
    con = forensics.open_state()
    s = make_session()
    try:
        capture_known_docs(s, con)
        search_for_additional(s, con)
    except KeyboardInterrupt:
        log.warning("interrupted — state saved, safe to rerun.")

    n = con.execute(
        "SELECT COUNT(*) FROM source_document "
        "WHERE source_type LIKE 'gko_decree%'"
    ).fetchone()[0]
    log.info("done; %d GKO decree artifacts in store", n)
