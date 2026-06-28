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
    (
        1166152,
        "33-641/2024 (1st instance 2-1099/2024)",
        "CAPTURED + READ 2026-06-26. Found via @mrpl_besxozxata msg 84043 "
        "(2026-02-26), posted as supporting evidence in a thread about foreign "
        "(Ukrainian) citizens being deemed to have renounced ownerless-registry "
        "rights for not appearing in person, per Закон ДНР №66-РЗ. Case: пр-т "
        "Нахимова (house no. redacted), Приморский district court, owner Кривонос "
        "Т.И., outside RF territory, utilities paid via trusted agent/POA, clean "
        "registry title on file. 1st instance left admin's petition without "
        "consideration (genuine dispute). ВС ДНР (Храпин/Черткова/Могутова, "
        "02.04.2025) REVERSED and remanded for merits -- opposite outcome "
        "direction from 1211787 -- on the ground the lower court never checked "
        "(a) whether the owner personally appeared within 30 days with "
        "'паспортом гражданина Российской Федерации' per Закон №66-РЗ ст.5(3)(а) "
        "-- the ONLY ID document the statute names, no foreign-passport clause -- "
        "and (b) the 6-month-outside-RF-territory trigger. DOCUMENT-CONFIRMED "
        "STRUCTURAL MECHANISM: an RF-citizen-only personal-confirmation safety "
        "valve forecloses the one procedural escape from bezkhoz designation for "
        "non-RF-citizen owners specifically, regardless of POA or paid utilities. "
        "Ruling text itself never states Кривонос Т.И.'s citizenship -- 'outside "
        "RF territory' is confirmed, citizenship is inferred from the mechanism "
        "the court applies, not asserted as fact. Differs from 1211787's reversal "
        "ground (failure to join co-owners) -- matched outcome-direction pair, "
        "not a matched doctrinal pair. See "
        "memory/mrpl_besxozxata_deep_intel_2026-06-26.md.",
    ),
    (
        1211787,
        "33-689/2025 (1st instance 2-2030/2024)",
        "CAPTURED + READ 2026-06-26. Originally flagged via an @mrpl_besxozxata chat "
        "post as one side of an alleged citizenship double standard (Russian- vs. "
        "Ukrainian-citizen owners treated oppositely) -- that framing did NOT hold up: "
        "the ruling text never mentions citizenship at all (grepped, zero hits). Actual "
        "holding is citizenship-neutral and procedural: admin decree no.130 "
        "(27.02.2024) registered a Zhovtnevy-district flat as ownerless; 1st instance "
        "granted municipal ownership 13.09.2024; DNR Supreme Court reversed because the "
        "lower court failed to join all 4 co-owners as parties, and a genuine ownership "
        "dispute (occupied, utilities paid, 2007 Ukrainian privatization title on file) "
        "can't go through the simplified special-proceedings track at all -- left "
        "without consideration, not decided on the merits; admin can re-file as an "
        "ordinary suit. Genuinely new finding instead: one co-owner had ALREADY received "
        "a war-damage compensation payment for this same flat (04.07.2024, 10,000 "
        "RUB/sqm) while a different city-admin arm tried to register it as abandoned -- "
        "an administrative self-contradiction. Judge Гуридова Н.Н. also sat on the "
        "Troianda-M appeal (33-2575/2025). The alleged mirror-image foreign-citizen "
        "case is still unconfirmed/unfound. See memory/mrpl_besxozxata_deep_intel_2026-06-26.md.",
    ),
]

# Arbitrary docket pages from other courts in the same case chain.
# Tuple: (url, source_type, title, description)
KNOWN_DOCKET_PAGES: list[tuple[str, str, str, str]] = [
    (
        "https://vs--dnr.sudrf.ru/modules.php?name=sud_delo&srv_num=1"
        "&name_op=case&case_id=1988037"
        "&case_uid=32bca921-244a-4379-a3bc-766a469ecfd3&delo_id=5&new=5",
        "dnr_supreme_court_docket_case",
        "ВС ДНР — карточка дела №33-1731/2025 (Докучаевск) — non-Mariupol bezkhoz, user-supplied 2026-06-26",
        "READ 2026-06-26. Дело №33-1731/2025 (1st instance 2-1065/2024, "
        "Докучаевский городской суд). Ruling text embedded directly in the case-"
        "card page (no separate doc_id needed). Owner Швець Н.Н., bought 2014, "
        "evacuated due to combat July 2024, learned of bezkhoz designation March "
        "2025 -- APPEARED on appeal in person, cited п.5 ч.1 ст.12 №5-ФКЗ "
        "(right to register property until 01.01.2028). REVERSED for failure to "
        "join her as a party -- WON (left without consideration). One of 4 "
        "non-Mariupol comparison cases; see "
        "memory/mrpl_besxozxata_deep_intel_2026-06-26.md.",
    ),
    (
        "https://vs--dnr.sudrf.ru/modules.php?name=sud_delo&srv_num=1"
        "&name_op=case&case_id=1986749"
        "&case_uid=71cd8992-4384-4c4f-a6fa-61e2b356f917&delo_id=5&new=5",
        "dnr_supreme_court_docket_case",
        "ВС ДНР — карточка дела №33-1590/2025 (Торез) — non-Mariupol bezkhoz, user-supplied 2026-06-26",
        "READ 2026-06-26. Дело №33-1590/2025 (1st instance 2-8490/2024, "
        "Харцызский межрайонный суд). Owner Елисеева С.Г., owner since 2006, "
        "APPEARED on appeal, argued she wasn't properly notified, also cited "
        "п.5 ч.1 ст.12 №5-ФКЗ. REVERSED for improper notice -- WON (admin's "
        "claim denied outright). Pairs with case_id 1988037 -- both owners who "
        "personally appeared, both won.",
    ),
    (
        "https://vs--dnr.sudrf.ru/modules.php?name=sud_delo&srv_num=1"
        "&name_op=case&case_id=1986186"
        "&case_uid=9802d0b1-eb0b-4542-8327-31e89bd78da5&delo_id=5&new=5",
        "dnr_supreme_court_docket_case",
        "ВС ДНР — карточка дела №33-1529/2025 (Донецк) — non-Mariupol bezkhoz, user-supplied 2026-06-26",
        "READ 2026-06-26. Дело №33-1529/2025 (1st instance 2-4192/2024, "
        "Ворошиловский межрайонный суд г. Донецка). Owner Шухнин А.С. -- ruling "
        "text states EXPLICITLY 'находится за пределами Российской Федерации' "
        "(outside RF territory); had title docs, prior use, paid utilities, legal "
        "counsel (Galushko V.V.) but did NOT appear personally. Claim "
        "GRANTED (ИСК УДОВЛЕТВОРЕН) -- LOST despite a complete paper trail. "
        "Strongest comparator yet for the personal-appearance-defeats-absentee-"
        "owners mechanism (Закон №66-РЗ ст.5(3)(а), case 1166152).",
    ),
    (
        "https://vs--dnr.sudrf.ru/modules.php?name=sud_delo&srv_num=1"
        "&name_op=case&case_id=1985702"
        "&case_uid=b887d09a-9a3a-4766-b9d6-bb3a35007911&delo_id=5&new=5",
        "dnr_supreme_court_docket_case",
        "ВС ДНР — карточка дела №33-1509/2025 (Володарское) — non-Mariupol bezkhoz, user-supplied 2026-06-26",
        "READ 2026-06-26. Дело №33-1509/2025 (1st instance 2-66/2025, "
        "Володарский районный суд). Owner Носенко Н.В. absent; tenant Мелихова "
        "С.В. holds a Dec-2024 POA to manage/dispose, lives there since 2021, "
        "pays utilities -- appealed for standing, REJECTED OUTRIGHT (оставлена "
        "без рассмотрения), trial court's grant of municipal ownership AFFIRMED. "
        "Confirms the pattern holds even for a present, paying, POA-holding "
        "occupant -- only the absent TITLE OWNER's personal appearance counts, "
        "not a representative's.",
    ),
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
    {
        # Added 2026-06-26: doc_id 1211787 (case 2-2030/2024 -> appeal 33-689/2025)
        # is this exact case type. A chat poster claimed a "mirror-image" sibling
        # ruling exists involving a foreign(Ukrainian)-citizen owner, treated
        # oppositely -- unconfirmed. The search field is case-subject text, not
        # litigant nationality, so this casts the widest net over the same case
        # type/period rather than guessing at a citizenship keyword that won't
        # appear in the subject line.
        "name": "sud_delo", "srv_num": 1, "name_op": "sf",
        "delo_id": 5, "nc": 1,
        "text_namecase": "признание права муниципальной собственности на бесхозяйную",
    },
    {
        # Same rationale, narrower phrasing variant -- GAS Правосудие's search
        # appears to do substring/stem matching, not always consistently, so two
        # phrasings of the same case-type name catch different indexing quirks.
        "name": "sud_delo", "srv_num": 1, "name_op": "sf",
        "delo_id": 5, "nc": 1,
        "text_namecase": "бесхозяйную недвижимую вещь",
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
