"""Stage 1e: capture DNR Supreme Court appellate rulings on housing/demolition disputes.

Claude must never run this — see CLAUDE.md. The portal is not geoblocked but
run from the VPS to keep capture provenance uniform.

WHY THIS EXISTS
---------------
The DNR Supreme Court hears appeals from Mariupol district courts on housing
rights cases brought by residents whose apartments were demolished under GKO
ДНР Распоряжение №56 (29.09.2022) and the framework Постановления №162/205/245.
These appellate decisions are self-incriminating in three ways:

1. The court's own narrative reconstructs the full demolish→rebuild lifecycle
   (inspection → commission → GKO order → demolition → land reallocation to
   developer SPV without auction) in a single document.

2. The rulings deny residents' claims for compensatory housing, making the
   occupation courts complicit in the ongoing deprivation and satisfying the
   ICC "exhaustion of local remedies" element for Rome Statute art. 8(2)(b)(xiii).

3. The reasoning acknowledges procedural violations (no notice to owners, no
   direct inspection) while declaring them immaterial — an on-the-record
   admission of the violations.

CASE ALREADY CAPTURED
---------------------
Case 33-2575/2025 (appeal of Zhovtnevy district court 2-259/2025):
  ~60 residents + ТСЖ «Троянда-М» v. Администрация г.о. Мариуполь et al.
  Subject: building demolished Dec 2022 under ГКО №56; land given to
    ООО «РКС-Девелопмент» (3,136 m²), developer ООО СЗ «Новое время 2»
    building a 9-storey МКД on the same footprint (address + «А» suffix).
  Outcome: both levels denied; DNR Supreme Court ruling 13.11.2025.
  Internal document ID: 2122362 (srv_num=1, delo_id=5).

WHAT THIS CAPTURES
------------------
Source types:
  dnr_supreme_court_ruling    HTML ruling page
  dnr_supreme_court_index     search/docket results page (for reproducibility)

Portal: https://vs--dnr.sudrf.ru/
  GAS «Правосудие» system — same engine as Mariupol district courts.
  delo_id=5 → civil appellate cases (33-XXXX/YYYY numbering).
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

ORIGIN = "https://vs--dnr.sudrf.ru"

# Known ruling pages to capture at the DNR Supreme Court.
# List of (internal_doc_id, case_number, description).
KNOWN_CASES: list[tuple[int, str, str]] = [
    (
        2122362,
        "33-2575/2025",
        "Appeal: ~60 residents + ТСЖ «Троянда-М» v. Администрация г.о. Мариуполь. "
        "Building demolished Dec 2022 under ГКО №56; land (3136 m²) allocated to "
        "РКС-Девелопмент without auction; replaced by ООО СЗ «Новое время 2» 9-storey МКД. "
        "DNR Supreme Court upheld denial. Ruling: 13.11.2025.",
    ),
]

# Arbitrary docket pages from other courts in the same case chain.
# Tuple: (url, source_type, title, description)
KNOWN_DOCKET_PAGES: list[tuple[str, str, str, str]] = [
    (
        "https://mar-zhovt--dnr.sudrf.ru/modules.php?name=sud_delo&srv_num=1"
        "&name_op=case&case_id=5346922"
        "&case_uid=27ec6a82-91b2-4a41-a176-0a946daa493d&delo_id=1540005",
        "dnr_district_court_docket",
        "Дело 2-259/2025 — Жовтневый районный суд г. Мариуполя — карточка дела",
        "First-instance civil case docket. UID 93RS0006-01-2024-005922-91. "
        "~63 residents + ТСЖ «Троянда-М» (ИНН 9310015564, ОГРН 1249300014347) "
        "v. Администрация г.о. Мариуполь (ИНН 9310000198, ОГРН 1229300128078) et al. "
        "Building demolished Dec 2022 under GKO ДНР №56 (29.09.2022). "
        "Land allocated to РКС-Девелопмент without auction (3136 m²). "
        "ООО СЗ «Новое время 2» contracted to build 9-storey МКД on same footprint. "
        "Judge: Сазонова Юлия Юрьевна. DENIED 21.07.2025. "
        "Property address NOT shown in docket — see ruling text.",
    ),
    (
        "https://2kas.sudrf.ru/modules.php?name=sud_delo&srv_num=1"
        "&name_op=case&case_id=17997342"
        "&case_uid=8741fb33-2475-4145-89e4-631f55aededc&new=2800001&delo_id=2800001",
        "ksoj2_cassation_docket",
        "Дело 8Г-12687/2026 [88-13102/2026] — 2й КСОЮ — кассация",
        "Cassation docket at the 2nd Court of General Jurisdiction (federal, Moscow). "
        "UID 93RS0006-01-2024-005922-91. Same case as 2-259/2025 and 33-2575/2025. "
        "Filed 06.04.2026 by Жованик К.И., Трусова Е.В., Ивахненко С.В. и др. "
        "Judge: Васильева Татьяна Геннадьевна. Hearing: 05.05.2026. "
        "Result: ОСТАВЛЕНО БЕЗ УДОВЛЕТВОРЕНИЯ — all three Russian court levels exhausted. "
        "New third parties: Администрация Главы ДНР (Пушилин chain); "
        "ППК «Единый заказчик в сфере строительства» (demolition executor).",
    ),
]

# Search terms for finding similar cases in the docket.
# The docket search uses GET params on the sf (search form) endpoint.
# text_namecase = subject/name-of-case field; text_name = party names.
SEARCH_PARAMS_LIST: list[dict] = [
    {
        "name": "sud_delo", "srv_num": 1, "name_op": "sf",
        "delo_id": 5, "nc": 1,
        "text_namecase": "снос многоквартирного жилого дома",
    },
    {
        "name": "sud_delo", "srv_num": 1, "name_op": "sf",
        "delo_id": 5, "nc": 1,
        "text_namecase": "компенсационного жилья",
    },
    {
        "name": "sud_delo", "srv_num": 1, "name_op": "sf",
        "delo_id": 5, "nc": 1,
        "text_namecase": "Мариуполь снос",
    },
]

_CASE_LINK = re.compile(
    r"name_op=case&.*?number=(\d+).*?delo_id=(\d+)", re.I
)
_DOC_LINK = re.compile(
    r"name_op=doc&.*?number=(\d+).*?delo_id=(\d+)", re.I
)
_CASE_NO = re.compile(r"\d{2}-\d+/\d{4}")


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
            r = s.get(url, timeout=config.TIMEOUT, verify=config.SSL_VERIFY)
            # GAS Pravosudie serves cp1251; re-encode to utf-8 for BeautifulSoup
            if "charset" not in r.headers.get("content-type", "").lower():
                r.encoding = "cp1251"
            return r
        except requests.RequestException as e:
            wait = min(60, 2 ** attempt)
            log.warning("GET %s failed (%d/%d): %s; wait %ds",
                        url, attempt, config.MAX_RETRIES, e, wait)
            time.sleep(wait)
    log.error("giving up on %s", url)
    return None


def _doc_url(number: int, delo_id: int = 5) -> str:
    return (
        f"{ORIGIN}/modules.php?name=sud_delo&srv_num=1"
        f"&name_op=doc&number={number}&delo_id={delo_id}&new=5&text_number=1"
    )


def capture_known_cases(s: requests.Session, con) -> None:
    """Capture each case in KNOWN_CASES."""
    for doc_id, case_no, description in KNOWN_CASES:
        key = f"dnr_supreme_court::{doc_id}"
        if forensics.is_done(con, key):
            log.debug("skip (already done): case %s doc %d", case_no, doc_id)
            continue

        url = _doc_url(doc_id)
        r = _get(s, url)
        polite_sleep()
        if r is None or r.status_code != 200:
            log.warning("ruling not fetched: %s (doc %d)", case_no, doc_id)
            continue

        forensics.capture_source(
            r.content, url=url,
            source_type="dnr_supreme_court_ruling",
            title=f"Апелляционное определение ВС ДНР по делу №{case_no}",
            description=description,
            content_type=r.headers.get("Content-Type", "text/html; charset=cp1251"),
            http_status=r.status_code, con=con,
        )
        forensics.mark_done(con, key)
        log.info("captured Supreme Court ruling: case %s (doc %d)", case_no, doc_id)


def capture_docket_search(s: requests.Session, con) -> list[tuple[str, int]]:
    """Search docket for demolition/housing cases; return (case_number, doc_id) list.

    Captures each search results page to the raw store for reproducibility,
    then extracts document links for individual capture.
    """
    found: list[tuple[str, int]] = []
    seen_doc_ids: set[int] = set()

    for params in SEARCH_PARAMS_LIST:
        from urllib.parse import urlencode
        query = urlencode(params)
        url = f"{ORIGIN}/modules.php?{query}"

        r = _get(s, url)
        polite_sleep()
        if r is None or r.status_code != 200:
            log.warning("docket search unavailable: %s", url)
            continue

        term_label = params.get("text_namecase", "")
        forensics.capture_source(
            r.content, url=url,
            source_type="dnr_supreme_court_index",
            title=f"ВС ДНР дocket search — «{term_label}»",
            description=(
                "DNR Supreme Court civil docket search for housing/demolition cases. "
                f"Search term: «{term_label}». "
                "Captured to preserve the docket state at time of crawl "
                "(GAS Правосудие search results are not permalink-stable)."
            ),
            content_type=r.headers.get("Content-Type", "text/html"),
            http_status=r.status_code, con=con,
        )

        soup = BeautifulSoup(r.text, "lxml")
        # GAS Праводсудие wraps each case row in a link with name_op=case or name_op=doc
        for a in soup.find_all("a", href=True):
            href = a["href"]
            m = _DOC_LINK.search(href)
            if m:
                doc_id = int(m.group(1))
                if doc_id not in seen_doc_ids:
                    seen_doc_ids.add(doc_id)
                    case_m = _CASE_NO.search(a.get_text())
                    case_no = case_m.group(0) if case_m else "?"
                    found.append((case_no, doc_id))

        log.info("docket search «%s»: %d total case docs found", term_label, len(found))

    return found


def capture_ruling_pages(
    s: requests.Session,
    con,
    cases: list[tuple[str, int]],
) -> None:
    """Capture individual ruling HTML pages for cases found by docket search."""
    for case_no, doc_id in cases:
        key = f"dnr_supreme_court::{doc_id}"
        if forensics.is_done(con, key):
            log.debug("skip (already done): doc %d", doc_id)
            continue

        url = _doc_url(doc_id)
        r = _get(s, url)
        polite_sleep()
        if r is None or r.status_code != 200:
            log.warning("ruling not fetched: doc %d", doc_id)
            continue

        forensics.capture_source(
            r.content, url=url,
            source_type="dnr_supreme_court_ruling",
            title=f"Апелляционное определение ВС ДНР по делу №{case_no}",
            description=(
                f"DNR Supreme Court appellate ruling in case {case_no}. "
                "Found via docket search for housing/demolition cases. "
                "May document demolish→rebuild lifecycle, GKO ДНР orders, "
                "or developer SPV beneficiaries."
            ),
            content_type=r.headers.get("Content-Type", "text/html; charset=cp1251"),
            http_status=r.status_code, con=con,
        )
        forensics.mark_done(con, key)
        log.info("captured ruling: case %s (doc %d)", case_no, doc_id)


def capture_docket_pages(s: requests.Session, con) -> None:
    """Capture known docket pages from district and federal courts in the same case chain."""
    for url, source_type, title, description in KNOWN_DOCKET_PAGES:
        key = f"docket::{url}"
        if forensics.is_done(con, key):
            log.debug("skip (already done): %s", title)
            continue
        r = _get(s, url)
        polite_sleep()
        if r is None or r.status_code != 200:
            log.warning("docket page not fetched (HTTP %s): %s",
                        r.status_code if r else "N/A", url)
            continue
        forensics.capture_source(
            r.content, url=url,
            source_type=source_type,
            title=title,
            description=description,
            content_type=r.headers.get("Content-Type", "text/html; charset=cp1251"),
            http_status=r.status_code, con=con,
        )
        forensics.mark_done(con, key)
        log.info("captured docket: %s", title[:80])


def run() -> None:
    con = forensics.open_state()
    s = make_session()
    try:
        capture_docket_pages(s, con)
        capture_known_cases(s, con)
        cases = capture_docket_search(s, con)
        if cases:
            log.info("found %d cases in docket search; capturing rulings…", len(cases))
            capture_ruling_pages(s, con, cases)
    except KeyboardInterrupt:
        log.warning("interrupted — state saved, safe to rerun.")

    n = con.execute(
        "SELECT COUNT(*) FROM source_document "
        "WHERE source_type LIKE 'dnr_supreme_court%' "
        "OR source_type IN ('dnr_district_court_docket','ksoj2_cassation_docket')"
    ).fetchone()[0]
    log.info("done; %d court artifacts in store", n)
