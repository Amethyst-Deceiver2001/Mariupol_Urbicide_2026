"""Stage 1b: capture Tier-1 "ownerless property" registers (the upstream of the
court docket).

Claude must never run this — see CLAUDE.md. Run only from a Russia-routed VPS.

WHY THIS EXISTS
---------------
The Zhovtnevy court docket (827 cases, see reports/zhovtnevy_summary_*.md) is
almost entirely (97%) petitioned by "Администрация городского округа
Мариуполь" — the Mariupol occupation municipal administration. That body
publishes its own "ownerless property" register directly: this is the actual
*upstream* record of the `notice` / `ownerless_designation` lifecycle stages
that never appear in the court-card HTML (see docs/pre_petition_sourcing.md).

WHAT THIS CAPTURES
------------------
1. Four district XLSX registries — one per court jurisdiction (Жовтневый,
   Приморский, Ильичевский, Орджоникидзевский) — an exact join key to
   `court_case.court`. These are LIVING DOCUMENTS: capture every dated
   snapshot as its own immutable artifact (never overwrite); the sequence of
   snapshots IS the evidence of the designation flow over time.
2. Numbered, dated administrative decree pages (постановления) — both
   designations ("...о признании бесхозяйным и включении в реестр") and
   removals ("...о снятии с учета" / "...об исключении имущества"). Each
   names a signing official: in-scope accountability actors per CLAUDE.md.

Re-running this script is the intended usage: each run discovers what's new
since the last capture (by content hash, not by URL — `forensics.capture_source`
already dedupes on SHA-256 and is append-only) and adds it to the timeline.
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from urllib.parse import urljoin

import requests
import urllib3
from bs4 import BeautifulSoup

from .. import config, forensics

log = logging.getLogger(__name__)

# Russian Gosuslugi portals use Минцифры CA certificates not in standard trust
# stores. Suppress the per-request InsecureRequestWarning since we log it once.
if not config.SSL_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Primary origin (mirror exists at mariupol-r897.gosweb.gosuslugi.ru — try it
# if this one is unreachable; both should be captured if both respond, since
# divergence between mirrors is itself evidence of edits).
ORIGIN = "https://mariupol.gosuslugi.ru"
MIRROR_ORIGIN = "https://mariupol-r897.gosweb.gosuslugi.ru"

# Official documents section, filtered to бесхозяйное-related постановления.
# Returns 75 results (as of 2026-06-09), paginated 20/page via curPos.
# cc=4721 is the section code; document_search filters by keyword in title.
DECREES_PATH = "/ofitsialno/dokumenty/postanovleniya-administratsii-gorodskogo-okruga-mariupol/"
DECREES_PARAMS = "cc=4721&document_search=%D0%B1%D0%B5%D1%81%D1%85%D0%BE%D0%B7%D1%8F%D0%B9%D0%BD%D0%BE%D0%B3%D0%BE&document_publication_date="
DECREES_PAGE_SIZE = 20

# Purpose-built ownerless section on the residents portal — the administration's
# own curated list of all housing-lifecycle postanovleniya.  More complete than
# the keyword-filtered view above (107 docs vs 75 as of 2026-06-09) because it
# also includes demolition declarations ("аварийными и подлежащими сносу") and
# exclusion-from-register orders with varying title phrasing.
# Found at: mariupol-r897.gosweb.gosuslugi.ru/dlya-zhiteley/poleznye-materialy/ownerless/
# Pagination: ?cur_cc=7767&curPos=N
OWNERLESS_SECTION_PATH = "/dlya-zhiteley/poleznye-materialy/ownerless/"
OWNERLESS_SECTION_PARAMS = "cur_cc=7767"

# District key -> (court key it joins to, relative XLSX path under /netcat_files/...).
# Court keys must match crawl/courts.py so loaders can join district -> court directly.
DISTRICT_REGISTRIES: dict[str, tuple[str, str]] = {
    "zhovtnevy":        ("zhovtnevy_mariupol",        "/netcat_files/418/7755/Zhovtnevyi_r_n.xlsx"),
    "primorsky":        ("primorsky_mariupol",        "/netcat_files/418/7755/Primorskii_r_n.xlsx"),
    "ilyichevsky":      ("ilyichevsky_mariupol",      "/netcat_files/418/7755/Il_ichevskii_r_n.xlsx"),
    "ordzhonikidzevsky":("ordzhonikidzevsky_mariupol","/netcat_files/418/7755/Ordzhonikidzevskii_r_n.xlsx"),
}

# Decree title patterns -> event kind, for cataloguing before parsing in detail.
# NB: Russian declension — the verbal nouns appear in the prepositional case with
# an -ии ending (признани·и, включени·и, исключени·и), so the stem must allow
# \w+ after it, not just [ея]. The gap before реестр is wide ("включении
# бесхозяйных объектов недвижимости в Реестр" ~= 40 chars).
#
# CRITICAL discriminator: use признани\w+ (the DECLARATION — "О признании ...
# бесхозяйными", the seizure act), NOT призна\w+ — the latter also matches
# признаки ("signs"), which appears in the boilerplate of *removal* titles
# ("из Реестра объектов ... имеющих признаки бесхозяйного") and would
# misclassify de-listings as seizures. Likewise включени (INTO register) vs
# исключени (OUT of register) never cross-match (исключени has no leading в),
# so the two kinds are mutually exclusive regardless of test order.
_DECREE_DESIGNATION = re.compile(
    r"признани\w+.{0,40}бесхозяйн|включени\w+.{0,45}реестр", re.I)
_DECREE_REMOVAL = re.compile(
    r"снят\w+.{0,15}учет|исключени\w+.{0,25}(?:имуществ|реестр)", re.I)
# Demolition declarations: "О признании МКД аварийными и подлежащими сносу"
# — appear in the ownerless section because demolition precedes municipal
# acquisition.  Classified separately so the parse stage routes them to the
# demolition_decree table rather than the ownerless table.
_DECREE_DEMOLITION = re.compile(
    r"признани\w+.{0,60}аварийн.{0,30}(?:снос|расселен)", re.I)
# Administrative machinery (the procedure itself, inspection commission, amendments)
# — not property lists, but high-value accountability evidence: intent + system +
# named officials. Classify separately so the parse stage doesn't treat them as
# property registries.
_DECREE_PROCEDURE = re.compile(
    r"утвержден\w+\s+(?:положени|порядк)|создани\w+\s+комисси"
    r"|внесени\w+\s+изменени", re.I)

_XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@dataclass(frozen=True)
class DecreeLink:
    decree_no: str
    title: str
    url: str
    kind: str  # 'designation' | 'removal' | 'unknown'


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


def capture_landing_and_find_decrees(s: requests.Session, con, origin: str) -> list[DecreeLink]:
    """Capture all search-result pages and return decree links found.

    Uses the official documents section filtered by keyword «бесхозяйного»
    (75 results as of 2026-06-09), paginated 20/page via the curPos parameter.
    Walks pages until a page yields no URLs not already seen (handles nav links
    that appear on every page and would otherwise loop forever).
    """
    decrees: list[DecreeLink] = []
    seen_urls: set[str] = set()
    cur_pos = 0
    while True:
        base = urljoin(origin, DECREES_PATH)
        url = f"{base}?{DECREES_PARAMS}&curPos={cur_pos}" if cur_pos else f"{base}?{DECREES_PARAMS}"
        r = _get(s, url)
        polite_sleep()
        if r is None or r.status_code != 200:
            break
        forensics.capture_source(
            r.content, url=url, source_type="ownerless_list_index",
            title=f"Mariupol бесхозяйное постановления index, offset {cur_pos}",
            description="Filtered search results: постановления Администрации "
                        "городского округа Мариуполь relating to бесхозяйное имущество.",
            content_type=r.headers.get("Content-Type", "text/html"),
            http_status=r.status_code, con=con,
        )
        soup = BeautifulSoup(r.text, "lxml")
        page_links = list(_extract_decree_links(soup, origin))
        new_links = [d for d in page_links if d.url not in seen_urls]
        if not new_links:
            log.info("offset %d: no new decree URLs — end of listing", cur_pos)
            break
        for d in new_links:
            seen_urls.add(d.url)
        decrees.extend(new_links)
        log.info("offset %d: %d new decrees (total %d)", cur_pos, len(new_links), len(decrees))
        cur_pos += DECREES_PAGE_SIZE
    log.info("search pages done: %d decree links discovered", len(decrees))
    return decrees


def _extract_decree_links(soup: BeautifulSoup, origin: str):
    """Yield DecreeLink for each постановление anchor on a search-result page.

    Anchor text typically reads like:
      "Постановление Администрации от 20 февраля 2026 года № 194 'О признании ...'"
    We keep the full title (it's the citation) and classify by keyword.
    """
    for a in soup.find_all("a", href=re.compile(r"postanovleniya-administratsii")):
        title = a.get_text(" ", strip=True)
        if not title or "Постановлен" not in title:
            continue
        m = re.search(r"№\s*(\d+)", title)
        no = m.group(1) if m else ""
        # Skip the section/breadcrumb link ("Постановления Администрации
        # городского округа Мариуполь") — it has no decree number and points at
        # the listing page itself, not an individual decree.
        if not no:
            continue
        # Order matters: amendments trump designations; demolition before
        # бесхозяйное designation since an МКД can be both аварийный and
        # бесхозяйный but the demolition path is the distinct pipeline.
        if _DECREE_PROCEDURE.search(title):
            kind = "procedure"
        elif _DECREE_DEMOLITION.search(title):
            kind = "demolition_declaration"
        elif _DECREE_DESIGNATION.search(title):
            kind = "designation"
        elif _DECREE_REMOVAL.search(title):
            kind = "removal"
        else:
            kind = "unknown"
        yield DecreeLink(decree_no=no, title=title,
                         url=urljoin(origin, a["href"]), kind=kind)


def _extract_pdf_links(soup: BeautifulSoup, origin: str) -> list[str]:
    """Return absolute URLs of PDF attachments linked from a decree page."""
    urls = []
    for a in soup.find_all("a", href=re.compile(r"\.pdf", re.I)):
        href = a.get("href", "")
        if href:
            urls.append(urljoin(origin, href))
    return urls


def capture_decree_pages(s: requests.Session, con, decrees: list[DecreeLink], origin: str) -> None:
    for d in decrees:
        key = f"decree::{d.url}"
        if forensics.is_done(con, key):
            continue
        r = _get(s, d.url)
        polite_sleep()
        if r is None or r.status_code != 200:
            continue
        forensics.capture_source(
            r.content, url=d.url, source_type=f"ownerless_decree_{d.kind}",
            title=d.title,
            description=f"№{d.decree_no} — {d.kind}; "
                         "ownerless-property designation/removal decree page "
                         "(names the signing official; in scope for accountability).",
            content_type=r.headers.get("Content-Type", "text/html"),
            http_status=r.status_code, con=con,
        )
        # Also capture any PDF annexes linked from this page. The annex is the
        # registry table listing the affected properties with addresses, areas,
        # cadastral numbers, and Rosreestr acceptance dates — the primary
        # evidence payload for the ownerless_designation lifecycle event.
        soup = BeautifulSoup(r.text, "lxml")
        for pdf_url in _extract_pdf_links(soup, origin):
            pdf_key = f"decree_pdf::{pdf_url}"
            if forensics.is_done(con, pdf_key):
                continue
            pr = _get(s, pdf_url)
            polite_sleep()
            if pr is None or pr.status_code != 200:
                log.warning("decree PDF not fetched: %s", pdf_url)
                continue
            ct = pr.headers.get("Content-Type",
                                 "application/pdf")
            forensics.capture_source(
                pr.content, url=pdf_url,
                source_type=f"ownerless_decree_{d.kind}_pdf",
                title=f"{d.title} [PDF annex]",
                description=f"№{d.decree_no} — PDF annex; "
                             "registry table with property addresses, areas, "
                             "cadastral numbers, and Rosreestr acceptance dates.",
                content_type=ct, http_status=pr.status_code, con=con,
            )
            forensics.mark_done(con, pdf_key)
            log.info("captured decree №%s PDF annex: %s", d.decree_no, pdf_url)
        forensics.mark_done(con, key)
        log.info("captured decree №%s (%s): %s", d.decree_no, d.kind, d.title[:80])


def capture_district_registries(s: requests.Session, con, origin: str) -> None:
    """Capture each district's XLSX as a DATED snapshot.

    Deliberately does NOT skip on URL — these are living documents. SHA-256
    dedupes identical re-downloads automatically (forensics.capture_source);
    a changed file gets a new hash and a new row, which is the point: the
    sequence of dated snapshots is the evidence of designations accruing.
    """
    for district, (court_key, rel_path) in DISTRICT_REGISTRIES.items():
        url = urljoin(origin, rel_path)
        r = _get(s, url)
        polite_sleep()
        if r is None or r.status_code != 200:
            log.warning("district registry unreachable: %s (%s)", district, url)
            continue
        sha = forensics.capture_source(
            r.content, url=url, source_type="ownerless_registry_xlsx",
            title=f"Ownerless-property registry — {district} district "
                  f"(court: {court_key})",
            description="District XLSX snapshot of residential premises with "
                         "'signs of being ownerless' (Перечень жилых помещений "
                         "с признаками бесхозяйных). Joins to court_case via "
                         "court=" + court_key + ". Capture every dated snapshot; "
                         "never overwrite — the sequence is the evidence.",
            content_type=r.headers.get("Content-Type", _XLSX_CONTENT_TYPE),
            http_status=r.status_code, con=con,
        )
        log.info("captured %s registry: sha256=%s… (%d bytes)",
                 district, sha[:16], len(r.content))


def capture_ownerless_section(s: requests.Session, con, origin: str) -> list[DecreeLink]:
    """Capture the purpose-built ownerless section (cur_cc=7767) and return decree links.

    This is more complete than the keyword-filtered search: the administration
    curates it directly, so it includes demolition declarations and exclusion
    orders with varying title phrasing that don't match the бесхозяйного keyword.
    107 documents as of 2026-06-09 vs 75 from the filtered search.
    Both sources are captured; the union covers any divergence.
    """
    decrees: list[DecreeLink] = []
    seen_urls: set[str] = set()

    # Capture the landing page itself (evidence of the section's existence).
    landing_url = urljoin(origin, OWNERLESS_SECTION_PATH)
    r = _get(s, landing_url)
    polite_sleep()
    if r is None or r.status_code != 200:
        log.warning("ownerless section landing unreachable: %s", landing_url)
        return decrees
    forensics.capture_source(
        r.content, url=landing_url,
        source_type="ownerless_section_landing",
        title="Mariupol ownerless section landing — /dlya-zhiteley/poleznye-materialy/ownerless/",
        description="Administration's curated ownerless-property section. "
                    "Contains 4 district XLSX links + full document index (cur_cc=7767).",
        content_type=r.headers.get("Content-Type", "text/html"),
        http_status=r.status_code, con=con,
    )
    soup = BeautifulSoup(r.text, "lxml")
    for d in _extract_decree_links(soup, origin):
        if d.url not in seen_urls:
            seen_urls.add(d.url)
            decrees.append(d)

    # Paginate through the section document index.
    cur_pos = DECREES_PAGE_SIZE
    while True:
        url = f"{landing_url}?{OWNERLESS_SECTION_PARAMS}&curPos={cur_pos}"
        r = _get(s, url)
        polite_sleep()
        if r is None or r.status_code != 200:
            break
        forensics.capture_source(
            r.content, url=url,
            source_type="ownerless_section_index",
            title=f"Mariupol ownerless section index, offset {cur_pos}",
            description="Paginated document list from cur_cc=7767 section.",
            content_type=r.headers.get("Content-Type", "text/html"),
            http_status=r.status_code, con=con,
        )
        soup = BeautifulSoup(r.text, "lxml")
        page_links = list(_extract_decree_links(soup, origin))
        new_links = [d for d in page_links if d.url not in seen_urls]
        if not new_links:
            log.info("section offset %d: no new URLs — end of listing", cur_pos)
            break
        for d in new_links:
            seen_urls.add(d.url)
        decrees.extend(new_links)
        log.info("section offset %d: %d new decrees (total %d)", cur_pos, len(new_links), len(decrees))
        cur_pos += DECREES_PAGE_SIZE

    log.info("ownerless section: %d decree links discovered", len(decrees))
    return decrees


def run() -> None:
    con = forensics.open_state()
    s = make_session()
    for origin in (ORIGIN, MIRROR_ORIGIN):
        try:
            log.info("== ownerless registry: %s ==", origin)
            # Primary: keyword-filtered search (бесхозяйного)
            decrees_kw = capture_landing_and_find_decrees(s, con, origin)
            # Secondary: administration's curated ownerless section — more complete
            decrees_sec = capture_ownerless_section(s, con, origin)
            # Union: capture any URLs not already done via the other path
            all_decrees = {d.url: d for d in decrees_kw}
            for d in decrees_sec:
                all_decrees.setdefault(d.url, d)
            capture_decree_pages(s, con, list(all_decrees.values()), origin)
            capture_district_registries(s, con, origin)
        except KeyboardInterrupt:
            log.warning("interrupted — state saved, safe to rerun.")
            break
        except Exception:
            log.exception("%s errored — continuing to next origin", origin)
    n = con.execute(
        "SELECT COUNT(*) FROM source_document WHERE source_type LIKE 'ownerless_%'"
    ).fetchone()[0]
    log.info("done; %d ownerless-source artifacts in store", n)
