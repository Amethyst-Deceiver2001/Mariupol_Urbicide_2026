#!/usr/bin/env python3
"""Enumerate the COMPLETE bezkhoz (ownerless-property) docket of the **Second
Cassation Court of General Jurisdiction** (2kas.sudrf.ru), filtered to DNR
region 93 — the next tier up from the DNR Supreme Court appeals analyzed in
`scripts/175`-`178`.

WHY THIS TIER MATTERS
----------------------
The court hierarchy for this case type is:
  district/city court (first instance, `crawl/court_crawler.py` + `courts.py`)
    -> ВС ДНР appellate review (`crawl/dnr_supreme_court.py`, `scripts/175/178`)
    -> **2-й кассационный суд общей юрисдикции** (cassation review — this script)
A losing party at ВС ДНР can seek cassation review here. This is the last stop
before any theoretical RF Supreme Court review, and captures the cases the
occupation court system itself considered contestable enough to escalate twice.

SAME PATTERN AS scripts/178, ONE LAYER UP
-------------------------------------------
Same district-crawler pagination pattern (`crawl/court_crawler.parse_results`:
`name_op=r` results list -> `name_op=case` card per row), pointed at
2kas.sudrf.ru with a category filter (`lawbookarticles[]`) for the bezkhoz case
type AND a region filter (`G33_CASE__COURT_I_REGION_ID`) restricting results to
courts of origin in DNR (region code 913830090). The results-page field
prefixes here are `G33_case__*`/`g33_case__*` (this portal's cassation-civil
schema) rather than `G1_case__*` — a different GAS «Правосудие» module
generation, but the same `table#tablcont` row structure and `name_op=case`
link convention, so `court_crawler.parse_results` is reused unchanged.

THE WORKING FILTER URL (user-supplied, 2026-06-27)
----------------------------------------------------
https://2kas.sudrf.ru/modules.php?name=sud_delo&srv_num=1&name_op=r&delo_id=2800001
  &case_type=0&new=2800001&delo_table=g33_case
  &g33_case__ENTRY_DATE1D=01.10.2022&g33_case__ENTRY_DATE2D=27.06.2026
  &G33_CASE__COURT_I_REGION_ID=913830090
  &lawbookarticles%5B%5D=<cp1251 "О признании движимой вещи бесхозяйной и
    признании права муниципальной собственности на бесхозяйную недвижимую вещь">
  &Submit=%CD%E0%E9%F2%E8

Decoded: delo_id=2800001 (cassation-civil instance), region_id=913830090 = DNR,
lawbookarticles[] = exactly the bezkhoz case-type string already used in
scripts/175/178. No {page} param was present in the supplied URL (defaults to
page 1) — this script appends `&list=ON&page={page}` before `&Submit=`,
mirroring `config.RESULTS_TEMPLATE`'s convention, and genericizes the two
hardcoded dates into {date_from}/{date_to} so the range doesn't go stale.
Override via env if the portal's pagination differs or the guessed template
doesn't render results:

  export CASS_RESULTS_TEMPLATE='https://2kas.sudrf.ru/modules.php?...&page={page}&...'
  export CASS_DATE_FROM=01.10.2022      # DNR's accession to the RF judiciary
  export CASS_DATE_TO=01.07.2026
  export COURT_PROXY=...                # your Russia-routed VPS

Claude must never run this (geoblocked foreign-state system) — you run it from
your VPS, like every other court crawl (CLAUDE.md).

  .venv312/bin/python scripts/179_crawl_2kas_cassation_bezkhoz.py

Output:
  * case cards  -> data/raw/<sha>.html (source_type=dnr_cassation_2kas_case)
  * index pages -> data/raw/<sha>.html (source_type=dnr_cassation_2kas_index)
  * manifest    -> data/parsed/dnr_cassation_2kas_manifest.jsonl
"""
import json
import logging
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import requests  # noqa: E402

from mariupol_seizures import config, forensics  # noqa: E402
from mariupol_seizures.crawl import court_crawler  # noqa: E402 (reuse parse_results/session)

log = logging.getLogger(__name__)

ORIGIN = "https://2kas.sudrf.ru"
SOURCE_TYPE_CASE = "dnr_cassation_2kas_case"
SOURCE_TYPE_INDEX = "dnr_cassation_2kas_index"
MANIFEST = ROOT / "data" / "parsed" / "dnr_cassation_2kas_manifest.jsonl"

_LAWBOOKARTICLES = (
    "О признании движимой вещи бесхозяйной и признании права муниципальной "
    "собственности на бесхозяйную недвижимую вещь"
)
_REGION_ID = "913830090"   # G33_CASE__COURT_I_REGION_ID -- restricts to DNR courts of origin

CASS_DATE_FROM = os.environ.get("CASS_DATE_FROM", "01.10.2022")
CASS_DATE_TO = os.environ.get("CASS_DATE_TO", "01.07.2026")


def _build_default_template() -> str:
    """Reconstruct the user-supplied URL with {page}/{date_from}/{date_to} slots.

    Builds the query with urlencode (correct percent/cp1251 escaping for every
    static value) and then substitutes the three placeholder tokens back in
    verbatim, since urlencode would otherwise escape their braces.
    """
    params = [
        ("name", "sud_delo"), ("srv_num", "1"), ("name_op", "r"),
        ("delo_id", "2800001"), ("case_type", "0"), ("new", "2800001"),
        ("G33_PARTS__NAMESS", ""), ("g33_case__CASE_NUMBERSS", ""),
        ("g33_case__JUDICIAL_UIDSS", ""), ("delo_table", "g33_case"),
        ("g33_case__ENTRY_DATE1D", "DATE_FROM_TOKEN"),
        ("g33_case__ENTRY_DATE2D", "DATE_TO_TOKEN"),
        ("G33_CASE__COURT_I_REGION_ID", _REGION_ID),
        ("G33_CASE__COURT_I", ""), ("G33_CASE__CASE_NUMBER_ISS", ""),
        ("g33_case__RESULT_DATE_I1D", ""), ("g33_case__RESULT_DATE_I2D", ""),
        ("lawbookarticles[]", _LAWBOOKARTICLES),
        ("G33_CASE__M_SUB_TYPE", ""), ("G33_CASE__WRIT_TYPE", ""),
        ("G33_CASE__VSRFID_NOTPOST", ""), ("G33_CASE__JUDGE", ""),
        ("g33_case__RESULT_DATE1D", ""), ("g33_case__RESULT_DATE2D", ""),
        ("G33_CASE__RESULT", ""), ("G33_CASE__RESULT_FOR_I_VERDICT_ID", ""),
        ("G33_CASE__RESULT_FOR_A_VERDICT_ID", ""), ("G33_CASE__BUILDING_ID", ""),
        ("G33_CASE__COURT_STRUCT", ""), ("G33_CASE__JUDGE_I", ""),
        ("G33_EVENT__EVENT_NAME", ""), ("G33_EVENT__EVENT_DATEDD", ""),
        ("G33_PARTS__PARTS_TYPE", ""), ("G33_PARTS__INN_STRSS", ""),
        ("G33_PARTS__KPP_STRSS", ""), ("G33_PARTS__OGRN_STRSS", ""),
        ("G33_PARTS__OGRNIP_STRSS", ""),
        ("G33_RKN_ACCESS_RESTRICTION__RKN_REASON", ""),
        ("g33_rkn_access_restriction__RKN_RESTRICT_URLSS", ""),
        ("G3_DOCUMENT__PUBL_DATE1D", ""), ("G3_DOCUMENT__PUBL_DATE2D", ""),
        ("G3_DOCUMENT__VALIDITY_DATE1D", ""), ("G3_DOCUMENT__VALIDITY_DATE2D", ""),
        ("list", "ON"), ("page", "PAGE_TOKEN"), ("Submit", "Найти"),
    ]
    query = urlencode(params, encoding="cp1251", errors="ignore")
    query = (query.replace("DATE_FROM_TOKEN", "{date_from}")
                  .replace("DATE_TO_TOKEN", "{date_to}")
                  .replace("PAGE_TOKEN", "{page}"))
    return f"{ORIGIN}/modules.php?{query}"


CASS_RESULTS_TEMPLATE = os.environ.get("CASS_RESULTS_TEMPLATE", "") or _build_default_template()


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": config.USER_AGENT, "Accept-Language": "ru,en;q=0.8"})
    if config.PROXY:
        s.proxies.update({"http": config.PROXY, "https": config.PROXY})
    return s


def polite_sleep() -> None:
    time.sleep(4.0)


def _get(s: requests.Session, url: str):
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            r = s.get(url, timeout=config.TIMEOUT, verify=config.SSL_VERIFY)
            if "charset" not in r.headers.get("content-type", "").lower():
                r.encoding = "cp1251"
            return r
        except requests.RequestException as e:
            wait = min(60, 2 ** attempt)
            log.warning("GET failed (%d/%d): %s; wait %ds", attempt, config.MAX_RETRIES, e, wait)
            time.sleep(wait)
    log.error("giving up on %s", url)
    return None


def crawl(s: requests.Session, con, manifest_fh) -> int:
    page, empty_streak, n_rows, n_cards = 1, 0, 0, 0
    prev_uids: set | None = None
    while True:
        url = CASS_RESULTS_TEMPLATE.format(page=page, date_from=CASS_DATE_FROM, date_to=CASS_DATE_TO)
        r = _get(s, url)
        polite_sleep()
        if r is None or r.status_code != 200:
            log.warning("results page %d unavailable", page)
            break
        forensics.capture_source(
            r.content, url=url, source_type=SOURCE_TYPE_INDEX,
            title=f"2-й КСОЮ bezkhoz (ДНР) results — page {page}",
            description=("Second Cassation Court of General Jurisdiction, "
                         "ownerless-property docket filtered to DNR region, "
                         f"page {page}, full-population enumeration."),
            content_type=r.headers.get("Content-Type", "text/html"),
            http_status=r.status_code, con=con,
        )
        rows = list(court_crawler.parse_results(r.text, ORIGIN))
        uids = {row["case_uid"] for row in rows}
        empty_streak = empty_streak + 1 if not rows else 0
        for row in rows:
            n_rows += 1
            key = f"dnr_cassation_2kas::{row['case_uid']}"
            already = forensics.is_done(con, key)
            if not already:
                cr = _get(s, row["card_url"])
                polite_sleep()
                if cr is not None and cr.status_code == 200:
                    forensics.capture_source(
                        cr.content, url=row["card_url"], source_type=SOURCE_TYPE_CASE,
                        title=f"2-й КСОЮ — карточка дела {row['case_number']}",
                        description=("Cassation-level ownerless-property case, DNR "
                                    f"region. Row: {row['category'][:200]}"),
                        content_type=cr.headers.get("Content-Type", "text/html; charset=cp1251"),
                        http_status=cr.status_code, con=con,
                    )
                    forensics.mark_done(con, key)
                    n_cards += 1
                    log.info("captured cassation case %s (%s)",
                            row["case_number"], row["case_uid"][:12])
                else:
                    log.warning("card not fetched: %s", row["card_url"])
            manifest_fh.write(json.dumps({
                "case_number": row["case_number"], "case_uid": row["case_uid"],
                "category": row["category"], "card_url": row["card_url"],
                "already_captured": already,
            }, ensure_ascii=False) + "\n")
            manifest_fh.flush()
        log.info("page %d: %d rows (%d cumulative)", page, len(rows), n_rows)
        if empty_streak >= 2:
            break
        if rows and uids == prev_uids:
            log.info("page %d repeats page %d verbatim (server clamp) — end", page, page - 1)
            break
        prev_uids = uids
        page += 1
    return n_cards


def main():
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    con = forensics.open_state()
    s = make_session()
    with MANIFEST.open("a", encoding="utf-8") as fh:
        n = crawl(s, con, fh)
    total = con.execute(
        "SELECT COUNT(*) FROM source_document WHERE source_type=?", (SOURCE_TYPE_CASE,)
    ).fetchone()[0]
    log.info("done; %d cards captured this run; %d total cassation cards in store", n, total)
    log.info("manifest -> %s", MANIFEST)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
