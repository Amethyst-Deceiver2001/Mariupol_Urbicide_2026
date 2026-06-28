#!/usr/bin/env python3
"""Bulk capture + structured extraction for DNR Supreme Court appeal cases of
the type "Дела особого производства -> О признании движимой вещи бесхозяйной
и признании права муниципальной собственности на бесхозяйную недвижимую
вещь" (ownerless-property recognition appeals), DNR-wide (not Mariupol-only).

Claude must never run this -- see CLAUDE.md. The portal search itself only
returns real results inside an authenticated/cookie-bearing browser session;
a bare scripted GET against the search form returns an empty form shell
(confirmed 2026-06-26). The user pages through the portal's own search UI
(category + date range 04.10.2022 [DNR formal accession, 5-ФКЗ] -> today)
and feeds this script the resulting case_id/case_uid pairs (or full case
URLs) found that way -- this script does NOT discover cases on its own.

WHY THIS EXISTS
----------------
2026-06-26 manual analysis of 5 cases of this type (1 Mariupol + 4 other DNR
municipalities -- Докучаевск/Торез/Донецк/Володарское) found the ruling text
is embedded directly in the case-card HTML (no separate doc_id/name_op=doc
fetch needed for этот case type) and surfaced a real, replicated mechanism:
owners who personally appear win procedurally; absentee owners (even with
full paper trail, even represented by a paying, long-resident POA-holder)
lose outright. This script scales that manual read-and-tag process: capture
each case card, then regex-extract the same fields (court, owner, dates,
appearance status, outcome) into a structured JSONL for review, instead of
re-doing the BeautifulSoup dig by hand per case.

Usage
-----
Add case identifiers to CASE_IDS below (case_id, case_uid pairs -- case_uid
is in the URL but not strictly required for the fetch; case_id alone works).
Then run:

    .venv312/bin/python scripts/175_crawl_dnr_bezkhoz_case_batch.py

Idempotent / resumable: already-captured case_ids are skipped on capture,
but extraction re-runs over everything captured so far every time (cheap,
local-only, no network).

Output: data/parsed/dnr_bezkhoz_cases_{records.jsonl,summary.json}
"""
from __future__ import annotations

import json
import logging
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import requests  # noqa: E402
import urllib3  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

if not config.SSL_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ORIGIN = "https://vs--dnr.sudrf.ru"
SOURCE_TYPE = "dnr_supreme_court_docket_case"

OUT_RECORDS = ROOT / "data" / "parsed" / "dnr_bezkhoz_cases_records.jsonl"
OUT_SUMMARY = ROOT / "data" / "parsed" / "dnr_bezkhoz_cases_summary.json"

# ---------------------------------------------------------------------------
# ADD NEW CASES HERE as the user pages through the portal's own search UI.
# Tuple: (case_id, case_uid, note). case_uid can be "" if unknown -- the
# fetch only strictly needs case_id, case_uid is kept for traceability back
# to the exact URL the user found.
# ---------------------------------------------------------------------------
CASE_IDS: list[tuple[int, str, str]] = [
    (1988037, "32bca921-244a-4379-a3bc-766a469ecfd3", "Докучаевск, 33-1731/2025"),
    (1986749, "71cd8992-4384-4c4f-a6fa-61e2b356f917", "Торез, 33-1590/2025"),
    (1986186, "9802d0b1-eb0b-4542-8327-31e89bd78da5", "Донецк, 33-1529/2025"),
    (1985702, "b887d09a-9a3a-4766-b9d6-bb3a35007911", "Володарское, 33-1509/2025"),
    # Batch 2, user-supplied 2026-06-26, found via portal search by category +
    # date range. Notes/case numbers/municipality not yet read -- extraction
    # below fills appeal_case_no etc. automatically; "batch2-unread" is just
    # a placeholder marking these weren't manually triaged before capture.
    (2338899, "26f754c0-94d0-4763-ad55-56182bd82d56", "batch2-unread"),
    (2257291, "e528b753-fe42-424d-9cab-34016ba0125d", "batch2-unread"),
    (2202468, "9bfeafb3-47c1-4b3c-b933-4dbb6f2fd16a", "batch2-unread"),
    (2165216, "b2f382f0-1b1c-4540-a28e-d379ee785837", "batch2-unread"),
    (2162970, "28bcd39b-d2e2-42ec-9cd0-7d97f80e38e7", "batch2-unread"),
    (2155034, "b90dc122-ab55-4883-9ab1-ec6a3efab86a", "batch2-unread"),
    (2145633, "36426d21-6181-4c1b-8c0b-4877c47cf1cb", "batch2-unread"),
    (2075616, "94a58da1-52ba-445b-9591-d1f8a4d51df8", "batch2-unread"),
    (2065758, "08bec872-e85a-484a-b8cb-4405ef007d41", "batch2-unread"),
    (2065779, "2e347ea7-1bbd-467d-89de-ac66bc904d11", "batch2-unread"),
    (2054032, "74375a17-0c75-4d37-8869-99c76e075c9c", "batch2-unread"),
    (2054011, "4c3b056b-62cc-4c96-9887-b2522d255337", "batch2-unread"),
    (2053975, "dfd841b8-0bdf-42d1-96db-3c45115046cd", "batch2-unread"),
    (2045103, "4946d66d-de3a-4dee-9c7e-16c6b673a82d", "batch2-unread"),
    (1996465, "df146a7b-f8d8-4b4b-88e9-c913c94d5325", "batch2-unread"),
    (1996111, "b01f5abe-4874-4711-804e-1825ef109d64", "batch2-unread"),
    (1996407, "939c83df-182b-40b1-82c8-3e54a2a3fa01", "batch2-unread"),
    (1996366, "e6c92def-7f97-45bb-ac74-9bf5f7d7a358", "batch2-unread"),
    (1996128, "5e9ed1f5-1d40-4ba4-bb9c-318f2d258870", "batch2-unread"),
    (1995595, "b9534336-115e-4432-b306-e2cad813e811", "batch2-unread"),
    (1995520, "fe5381ef-aa66-49c2-b6d2-a1a1a6ce58fd", "batch2-unread"),
    (1995161, "740387d4-920d-46b1-9d50-57b5d7c3a7a1", "batch2-unread"),
    (1994697, "0855fd80-80a0-4144-adfa-75ea473359c1", "batch2-unread"),
    (1994159, "3cdeddd7-a561-46cd-8a4c-907ab335d6ca", "batch2-unread"),
    (1993673, "dd586303-05ad-438f-94bf-e4f96645dc55", "batch2-unread"),
    (1993531, "84b62950-7902-4d6e-87df-e90003a6d3e7", "batch2-unread"),
    # Batch 3, user-supplied 2026-06-26 (53 new, 4 duplicates of batch 1/2 dropped).
    (1993321, "6eb02b4c-4b55-417c-aa3c-0e02af5d30a0", "batch3-unread"),
    (1993082, "5b199e6f-f8b2-421e-b0b0-4bd1b82a6dc0", "batch3-unread"),
    (1992901, "135b2d87-3e86-4150-9533-e0832bc6db0f", "batch3-unread"),
    (1992854, "780db7b4-bf1f-4f5b-9c5a-fb6651e00a67", "batch3-unread"),
    (1992843, "aa4512e8-9ab8-4486-ba01-775782570e2e", "batch3-unread"),
    (1992740, "88213f17-bb16-4d97-a4b0-ac9d805bd615", "batch3-unread"),
    (1991642, "9311ed51-9d04-41a5-85df-8fb400158020", "batch3-unread"),
    (1991726, "dafc5fc8-d6c4-47b8-b49c-8c5bb090d4c0", "batch3-unread"),
    (1991382, "a69f9da4-1205-45ff-ad91-c377bfcb0670", "batch3-unread"),
    (1991112, "ff512cd2-1b7b-408d-916c-b61de3eb6020", "batch3-unread"),
    (1991244, "51cb32ec-4537-4a2a-9e62-59626e354dde", "batch3-unread"),
    (1977388, "ad5fb220-d784-4e86-9483-f32f29485b42", "batch3-unread"),
    (1989560, "3983a4d6-9b2e-420f-8b49-76feb070fd4e", "batch3-unread"),
    (1989304, "24c26629-6581-44ba-8053-5086c92322c3", "batch3-unread"),
    (1989193, "dea74373-462d-47f4-8cbb-d384f417e639", "batch3-unread"),
    (1989325, "3cb3a1fc-e807-4e9f-8873-daf89dcdcfb9", "batch3-unread"),
    (1988958, "8909afbe-6154-46ac-bfe5-2c3f0df92cac", "batch3-unread"),
    (1988122, "59a3d1eb-a1c8-49ba-b543-7486225540cc", "batch3-unread"),
    (1986861, "82821f75-b4f3-428f-9d0d-e13dd201779a", "batch3-unread"),
    (1984929, "8de6c5da-e369-4da8-9384-7e2f5c278403", "batch3-unread"),
    (1983967, "eae4e613-ae3c-4750-b677-332f373f0634", "batch3-unread"),
    (1983672, "8afeda6f-dd90-40c3-afe8-cdd5035128fb", "batch3-unread"),
    (1982488, "3b1ac31d-bdca-450c-9d0e-d879d5a02716", "batch3-unread"),
    (1982358, "deeb41e7-86e3-4604-be92-3040c2fcf38d", "batch3-unread"),
    (1982019, "5c0f1fc8-c74d-4ef1-a81c-55968b8b4754", "batch3-unread"),
    (1980581, "b301b5ae-e382-442c-a99c-6e1845231af2", "batch3-unread"),
    (1979027, "0e8737fd-9674-40dc-9e5b-5465db51b6b7", "batch3-unread"),
    (1978845, "ac4adc64-3f91-42c9-854f-9318c77fefb7", "batch3-unread"),
    (1978888, "dca2322a-1a33-4829-a2cf-03b22342c8bb", "batch3-unread"),
    (1977070, "e83d1bc1-4f71-4668-991c-88b0ef97fcd3", "batch3-unread"),
    (1976940, "97dc2bc4-74d1-4139-a96c-bd475854181d", "batch3-unread"),
    (1976412, "c2901a8a-7ac3-4cdb-9b21-6508eaf7e428", "batch3-unread"),
    (1974479, "b51a8efa-c504-4191-819f-bb52d034c248", "batch3-unread"),
    (1974339, "7d177ad9-4ffd-49e6-9fad-7c5bc194402f", "batch3-unread"),
    (1974119, "96c02562-9eb9-4efa-9ffb-9db54e091fb0", "batch3-unread"),
    (1973272, "560d9276-7841-42cb-b240-df705c852392", "batch3-unread"),
    (1972683, "39e55b4b-1a5c-41f8-9349-82d6e7315fe9", "batch3-unread"),
    (1972635, "07e2a4e1-a70b-43ab-abe7-a7847223a172", "batch3-unread"),
    (1972576, "d65ab594-da21-482d-a434-cafd64dad030", "batch3-unread"),
    (1971795, "7b7f15ff-5808-446c-934b-08c9fbc5f3e4", "batch3-unread"),
    (1971648, "b86f5e9d-8f01-44da-92c7-18d645511b08", "batch3-unread"),
    (1971027, "b6bb356f-5794-46ff-bbb7-87b0e1512fd6", "batch3-unread"),
    (1970667, "fa22a614-1180-42ac-bd79-c21368006e4f", "batch3-unread"),
    (1968660, "2770721b-891e-4f7f-b88b-10f73512a787", "batch3-unread"),
    (1968429, "49fed4a9-a904-40aa-b9ee-f6fc68dba986", "batch3-unread"),
    (1968319, "2a973e46-674d-4033-97a3-02b8599a2c11", "batch3-unread"),
    (1968286, "dc332611-5380-405d-b0fb-f2e42f218d3f", "batch3-unread"),
    (1968303, "95b47c17-08dc-41fc-b00f-94bf8208cd5f", "batch3-unread"),
    (1967829, "e007419b-475b-4966-b6c5-e6c468a8a8a3", "batch3-unread"),
    (1962616, "b6597c46-291b-4e6c-b91b-7fa902fd80d6", "batch3-unread"),
    (1962139, "d5f6ceb3-c78e-4247-9bfe-d9d94fedde4d", "batch3-unread"),
    (1956978, "22a60ec9-b235-48b3-875e-815b390b525c", "batch3-unread"),
    (1953359, "5eb4d35a-dbf7-478e-bb2c-6c73861b9750", "batch3-unread"),
    # Batch 4 (FINAL), user-supplied 2026-06-26: "that's going to be all
    # bezkhoz cases with resolution text in ВС ДНР" -- treat this as the
    # complete population for this case type/court as of 2026-06-26, not
    # just another incremental batch.
    (1965872, "ad276d3e-6eee-4366-ad9b-edb071d20957", "batch4-unread"),
    (1967640, "da30aa16-cf27-47e9-9269-3cb44f94b59e", "batch4-unread"),
    (1967550, "69b12c4b-d862-40d1-8df5-1bdfe4f7aa9e", "batch4-unread"),
    (1967543, "f8c014bc-446a-400e-a06f-08087e6c57ca", "batch4-unread"),
    (1967536, "7802de64-feb4-4f56-953b-bb2fd8604d8b", "batch4-unread"),
    (1967529, "929633a6-b4bb-4979-82f7-d8160e891412", "batch4-unread"),
    (1966011, "eef289b3-dd6d-43fe-b8ec-37cd2af73927", "batch4-unread"),
    (1964308, "2fd83a6c-561c-41cd-9fd0-bde14ab6dd3c", "batch4-unread"),
    (1965029, "a7f2ef61-9eb8-4180-9564-04b5f3dba309", "batch4-unread"),
    (1964383, "94de439b-0a8e-4d15-8b5e-0b5471caf607", "batch4-unread"),
    (1961498, "de4935fe-6dfc-4971-a1cd-860f98d16af2", "batch4-unread"),
    (1960506, "fea1e031-236b-4d7d-b44c-9934f4eb638b", "batch4-unread"),
    (1960344, "01594309-fd5b-4c9d-9425-335d611837ad", "batch4-unread"),
    (1957317, "e21eeaa0-5e61-4b38-b89e-88b73369f505", "batch4-unread"),
    (1953444, "a6de0ae8-eaea-48cd-9f06-ddf27cd4e3dd", "batch4-unread"),
]

_ABSENT_RX = re.compile(
    r"находится за пределами Российской Федерации"
    r"|за пределами Российской Федерации",
    re.I,
)
_NOT_APPEARED_RX = re.compile(
    r"в судебное заседание не явил|надлежащим образом извещен.{0,40}не явил",
    re.I,
)
_APPEARED_RX = re.compile(
    r"объяснения (?:заинтересованного лица|представителя заинтересованного лица|"
    r"Мелиховой|Шухнина)|поддержавш\w+ доводы (?:апелляционной )?жалобы",
    re.I,
)
# "отменить" (reverse) is genuinely ambiguous without knowing what's being
# reversed -- reversing a GRANT to the municipality helps the owner; reversing
# a DENIAL and remanding for fresh merits review does not (the claim against
# the owner is just alive again). Collapsing this into one owner_won/lost
# guess was the 2026-06-26 bug (see memory/mrpl_besxozxata_deep_intel...).
# Instead extract THREE independent raw signals and let a human (or a later
# pass) combine them -- never present the combination as confirmed without
# reading the actual text.
#
# Signal 1: what the FIRST INSTANCE actually decided (from the facts
# recital, before the disposition).
_LOWER_GRANTED_RX = re.compile(
    r"(?:заявление|иск).{0,60}удовлетворен"
    r"|признан\w+ право муниципальной собственности", re.I)
_LOWER_DENIED_RX = re.compile(
    r"(?:заявление|иск).{0,60}(?:оставлен\w+ без рассмотрения|отказан\w+)"
    r"|оставлено без рассмотрения.{0,40}наличи\w+ спора", re.I)

# Signal 2: what ВС ДНР's disposition actually DOES to the lower ruling.
_DISP_AFFIRMED_RX = re.compile(r"оставить без изменения", re.I)
_DISP_REVERSED_RX = re.compile(r"отменить", re.I)
_DISP_GRANTED_DIRECTLY_RX = re.compile(
    r"заявление.{0,60}удовлетворить(?!\s*частн)", re.I)
_DISP_DENIED_DIRECTLY_RX = re.compile(
    r"отказать в удовлетворении заявления", re.I)

# Signal 3: if reversed, what happens NEXT -- this is what actually
# disambiguates "отменить".
_REMAND_WITHOUT_CONSIDERATION_RX = re.compile(
    r"оставить без рассмотрения", re.I)
_REMAND_FOR_MERITS_RX = re.compile(
    r"возвратить.{0,60}для рассмотрения по существу"
    r"|направить.{0,60}на новое рассмотрение", re.I)

# The court's operative holding starts at "ОПРЕДЕЛИЛ" / "ОПРЕДЕЛИЛА" / "РЕШИЛ" /
# "РЕШИЛА" (all-caps heading in these documents) -- single-judge rulings use
# the masculine singular ("установил:" / "ОПРЕДЕЛИЛ:"), panel rulings use
# feminine plural ("установила:" / "ОПРЕДЕЛИЛА:"). Match both.
_FACTS_ANCHOR_RX = re.compile(r"установил[а]?\s*:", re.I)
_DISPOSITION_ANCHOR_RX = re.compile(r"(?:ОПРЕДЕЛИЛ[А]?|РЕШИЛ[А]?)\s*:", re.I)
# Category filter -- the shared dnr_supreme_court_ruling source type also
# holds Troianda-M (doc_id 2122362), a DIFFERENT case type (residents' demolition-
# compensation claim, not a bezkhoz petition). Only keep cases whose own text
# names this category explicitly.
_CATEGORY_RX = re.compile(
    r"бесхозя[йн]\w* (?:недвижим\w*|объект|вещь)"
    r"|признании права муниципальной собственности на бесхозя", re.I)
_POA_RX = re.compile(r"доверенност", re.I)
_CASE_NO_RX = re.compile(r"№\s*33-\d+/\d{4}")
_FIRST_INSTANCE_NO_RX = re.compile(r"№\s*2-\d+/\d{4}")
_COURT_RX = re.compile(
    r"(?:Администрация|администрация)\s+(?:городского округа|"
    r"муниципального округа|городск\w+|района)?\s*([А-ЯЁ][а-яё\-]+)"
)


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": config.USER_AGENT,
        "Accept-Language": "ru,en;q=0.8",
    })
    if config.PROXY:
        s.proxies.update({"http": config.PROXY, "https": config.PROXY})
    return s


def _get(s: requests.Session, url: str):
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            r = s.get(url, timeout=config.TIMEOUT, verify=config.SSL_VERIFY)
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


def _case_url(case_id: int, case_uid: str = "") -> str:
    uid_part = f"&case_uid={case_uid}" if case_uid else ""
    return (
        f"{ORIGIN}/modules.php?name=sud_delo&srv_num=1"
        f"&name_op=case&case_id={case_id}{uid_part}&delo_id=5&new=5"
    )


def capture_cases(s: requests.Session, con) -> None:
    for case_id, case_uid, note in CASE_IDS:
        key = f"dnr_bezkhoz_case::{case_id}"
        if forensics.is_done(con, key):
            log.debug("skip (already done): case_id %d (%s)", case_id, note)
            continue
        url = _case_url(case_id, case_uid)
        r = _get(s, url)
        time.sleep(2.0)
        if r is None or r.status_code != 200:
            log.warning("case not fetched: case_id %d (%s)", case_id, note)
            continue
        forensics.capture_source(
            r.content, url=url,
            source_type=SOURCE_TYPE,
            title=f"ВС ДНР — карточка дела (case_id {case_id}) — {note}",
            description=(
                f"Bulk-captured DNR-wide ownerless-property (бесхозяйная "
                f"недвижимая вещь) appeal case, found via the portal's own "
                f"search by category + date range (04.10.2022 -> today). {note}."
            ),
            content_type=r.headers.get("Content-Type", "text/html; charset=cp1251"),
            http_status=r.status_code, con=con,
        )
        forensics.mark_done(con, key)
        log.info("captured case_id %d (%s)", case_id, note)


def extract_all(con) -> None:
    """Local-only, no network: re-extract structured fields from every
    dnr_bezkhoz_case (and the two earlier KNOWN_CASES rulings, if present)
    captured so far."""
    rows = con.execute(
        "SELECT sha256, url, title, raw_path FROM source_document "
        "WHERE source_type IN (?, 'dnr_supreme_court_ruling')",
        (SOURCE_TYPE,),
    ).fetchall()
    log.info("extracting from %d captured documents", len(rows))

    OUT_RECORDS.parent.mkdir(parents=True, exist_ok=True)
    records = []
    with OUT_RECORDS.open("w", encoding="utf-8") as fh:
        for sha, url, title, raw_path in rows:
            if not raw_path:
                continue
            p = ROOT / raw_path if not Path(raw_path).is_absolute() else Path(raw_path)
            if not p.exists():
                continue
            try:
                html = p.read_text(encoding="cp1251", errors="replace")
            except Exception:
                continue
            soup = BeautifulSoup(html, "lxml")
            text = soup.get_text("\n", strip=True)

            if not _CATEGORY_RX.search(text):
                log.info("skip (not bezkhoz category, e.g. Troianda-M-type): %s", title[:70])
                continue

            case_no_m = _CASE_NO_RX.search(text)
            first_no_m = _FIRST_INSTANCE_NO_RX.search(text)
            court_m = _COURT_RX.search(text)

            absent = bool(_ABSENT_RX.search(text))
            not_appeared = bool(_NOT_APPEARED_RX.search(text))
            appeared = bool(_APPEARED_RX.search(text))
            has_poa = bool(_POA_RX.search(text))

            facts_m = _FACTS_ANCHOR_RX.search(text)
            facts_text = text[facts_m.end():facts_m.end() + 1500] if facts_m else ""
            disp_m = _DISPOSITION_ANCHOR_RX.search(text, facts_m.end() if facts_m else 0)
            disposition_text = text[disp_m.end():disp_m.end() + 700] if disp_m else ""

            lower_court_signal = (
                "granted_to_admin" if _LOWER_GRANTED_RX.search(facts_text) else
                "denied_or_without_consideration" if _LOWER_DENIED_RX.search(facts_text) else
                None
            )
            disposition_action = (
                "affirmed" if _DISP_AFFIRMED_RX.search(disposition_text) else
                "reversed" if _DISP_REVERSED_RX.search(disposition_text) else
                "granted_directly" if _DISP_GRANTED_DIRECTLY_RX.search(disposition_text) else
                "denied_directly" if _DISP_DENIED_DIRECTLY_RX.search(disposition_text) else
                None
            )
            remand_signal = (
                "left_without_consideration" if _REMAND_WITHOUT_CONSIDERATION_RX.search(disposition_text) else
                "remanded_for_merits" if _REMAND_FOR_MERITS_RX.search(disposition_text) else
                None
            )

            rec = {
                "sha256": sha[:16],
                "url": url,
                "title": title,
                "appeal_case_no": case_no_m.group(0) if case_no_m else None,
                "first_instance_case_no": first_no_m.group(0) if first_no_m else None,
                "court_guess": court_m.group(1) if court_m else None,
                "owner_absent_explicit": absent,
                "owner_or_party_not_appeared": not_appeared,
                "owner_or_party_appeared": appeared,
                "poa_mentioned": has_poa,
                "lower_court_signal": lower_court_signal,
                "disposition_action": disposition_action,
                "remand_signal": remand_signal,
                "disposition_anchor_found": bool(disp_m),
                "disposition_excerpt": disposition_text,
                "text_excerpt": text[facts_m.start():facts_m.start() + 1200]
                if facts_m else text[:1200],
            }
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            records.append(rec)

    summary = {
        "total_cases": len(records),
        "owner_absent_explicit": sum(1 for r in records if r["owner_absent_explicit"]),
        "appeared": sum(1 for r in records if r["owner_or_party_appeared"]),
        "not_appeared": sum(1 for r in records if r["owner_or_party_not_appeared"]),
        "poa_mentioned": sum(1 for r in records if r["poa_mentioned"]),
        "lower_court_signal": {}, "disposition_action": {}, "remand_signal": {},
    }
    for field in ("lower_court_signal", "disposition_action", "remand_signal"):
        for r in records:
            t = r[field] or "unclassified"
            summary[field][t] = summary[field].get(t, 0) + 1
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{'='*72}")
    print(f"DNR bezkhoz case batch — {len(records)} documents extracted")
    print(f"{'='*72}")
    for r in records:
        print(f"  {r['appeal_case_no'] or '?':16s} appeared={r['owner_or_party_appeared']!s:5s} "
              f"absent_explicit={r['owner_absent_explicit']!s:5s} poa={r['poa_mentioned']!s:5s} "
              f"lower={r['lower_court_signal']} disp={r['disposition_action']} "
              f"remand={r['remand_signal']}")
    print(f"\n  NOTE: these are 3 independent raw regex SIGNALS, deliberately NOT")
    print(f"  collapsed into a single owner_won/lost verdict -- 'reversed' is")
    print(f"  ambiguous without lower_court_signal+remand_signal context. Always")
    print(f"  read disposition_excerpt/text_excerpt before citing a case's outcome.")
    print(f"  Records → {OUT_RECORDS}")
    print(f"  Summary → {OUT_SUMMARY}")


def run() -> None:
    con = forensics.open_state()
    s = make_session()
    try:
        capture_cases(s, con)
    except KeyboardInterrupt:
        log.warning("interrupted — state saved, safe to rerun.")
    extract_all(con)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run()
