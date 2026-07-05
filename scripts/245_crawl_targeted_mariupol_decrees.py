#!/usr/bin/env python3
"""Targeted capture of the 3 remaining genuinely-open Mariupol municipal decrees,
confirmed absent from GARANT (2026-07-04 session) and not yet in the raw store:

  - Распоряжение главы администрации г. Мариуполя №619 (12.10.2023) —
    citywide "сплошная инвентаризация" property-inventory order. Text already
    confirmed verbatim inside multiple resident Telegram chats, but the
    primary scan itself was never captured.
  - Постановление Администрации г. Мариуполя №1592 (17.10.2025) — municipal
    ownerless-designation decree.
  - маневренный фонд Decree №493 (05.03.2026, Кольцов) — allocation decree
    moving 18 named buildings to МУП «УК Жилсервис»; the general маневренный-
    фонд/служебное-жильё framework is already [CAPTURED], this specific
    allocation decree is not.

All three are Mariupol-administration acts on mariupol.gosuslugi.ru — the
SAME geoblocked domain src/mariupol_seizures/crawl/ownerless_lists.py already
targets, just filtered for different keywords than that module's standing
"бесхозяйное" search (№619 is an inventory order, №493 is a housing-
allocation decree — neither necessarily uses the "бесхозяйное" keyword the
existing crawler filters on). This script reuses that module's session/
parsing helpers rather than duplicating them.

Claude must never run this — see CLAUDE.md. Run only from a Russia-routed VPS.

Run:
    PYTHONPATH=src python scripts/245_crawl_targeted_mariupol_decrees.py
"""
from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
from urllib.parse import quote, urljoin

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import forensics  # noqa: E402
from mariupol_seizures.crawl import ownerless_lists as ol  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
log = logging.getLogger(__name__)

# decree_no -> search keyword to use against DECREES_PATH's document_search
# param, since each decree's own title may not contain "бесхозяйное".
#
# BUG FIXED 2026-07-04 (first live run): all 3 keywords returned 0 hits via the
# search endpoint -- ownerless_lists.py's own DECREES_PARAMS uses genitive case
# ("бесхозяйного", percent-encoded) not nominative ("бесхозяйное"); the portal's
# search appears to require the exact grammatical form, not a stem/fuzzy match.
# Fixed to genitive case throughout. (№1592 and №493 were still found via the
# broader curated-section sweep despite the bad keyword -- both already existed
# in the raw store from a much earlier general crawl, just never cross-
# referenced by decree number before this session.)
TARGET_SEARCHES: dict[str, str] = {
    "619": "инвентаризации",
    "1592": "бесхозяйного",
    "493": "маневренного",
}


def search_by_keyword(s, con, origin: str, keyword: str) -> list[ol.DecreeLink]:
    """Same pagination logic as ol.capture_landing_and_find_decrees(), but with
    an arbitrary keyword instead of the module's hardcoded DECREES_PARAMS.
    """
    decrees: list[ol.DecreeLink] = []
    seen_urls: set[str] = set()
    cur_pos = 0
    params = f"cc=4721&document_search={quote(keyword)}&document_publication_date="
    while True:
        base = urljoin(origin, ol.DECREES_PATH)
        url = f"{base}?{params}&curPos={cur_pos}" if cur_pos else f"{base}?{params}"
        r = ol._get(s, url)
        ol.polite_sleep()
        if r is None or r.status_code != 200:
            break
        forensics.capture_source(
            r.content, url=url, source_type="targeted_decree_search",
            title=f"Mariupol decree search — keyword '{keyword}', offset {cur_pos}",
            description=(
                f"Targeted search for keyword '{keyword}' (scripts/245) -- chasing "
                "specific municipal decrees not covered by ownerless_lists.py's "
                "standing 'бесхозяйное' filter."
            ),
            content_type=r.headers.get("Content-Type", "text/html"),
            http_status=r.status_code, con=con,
        )
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(r.text, "lxml")
        page_links = list(ol._extract_decree_links(soup, origin))
        new_links = [d for d in page_links if d.url not in seen_urls]
        if not new_links:
            log.info("  [%s] offset %d: no new links -- end of listing", keyword, cur_pos)
            break
        for d in new_links:
            seen_urls.add(d.url)
        decrees.extend(new_links)
        log.info("  [%s] offset %d: %d new (total %d)", keyword, cur_pos, len(new_links), len(decrees))
        cur_pos += ol.DECREES_PAGE_SIZE
    return decrees


# BUG FOUND 2026-07-04 (second live run): №619 was never found because it's a
# **Распоряжение** (Order), not a **Постановление** (Resolution) -- and every
# helper above (ol._extract_decree_links, the DECREES_PATH URL itself) is
# scoped to "postanovleniya-administratsii" specifically. The "инвентаризации"
# keyword search DID work this time (4 real hits), but all 4 were a
# *different*, later inventory-procedure chain (Постановление №1223,
# 05.08.2025, + 3 amendments) -- confirms №619 (12.10.2023) predates and is
# likely superseded by that 2025 formalisation, not the same instrument.
#
# Two fallback probes below: (1) try the analogous URL path with
# "rasporyazheniya" swapped in for "postanovleniya" (untested guess, probed
# empirically -- capture the response either way, 404 or not, for the record);
# (2) a raw anchor scan across the SAME search/section pages already fetched
# above, with NO href/title filter, just looking for "619" near "Распоряжен"
# in the visible text -- in case Распоряжения are mixed into the same listing
# under a differently-shaped anchor ol._extract_decree_links doesn't match.
RASPORYAZHENIYA_PATH_CANDIDATES = [
    "/ofitsialno/dokumenty/rasporyazheniya-administratsii-gorodskogo-okruga-mariupol/",
    "/ofitsialno/dokumenty/rasporyazheniya-glavy-administratsii-gorodskogo-okruga-mariupol/",
]


def probe_rasporyazheniya_paths(s, con, origin: str) -> None:
    log.info("=== Probing Распоряжения URL path candidates (untested guesses) ===")
    for path in RASPORYAZHENIYA_PATH_CANDIDATES:
        url = urljoin(origin, path)
        r = ol._get(s, url)
        ol.polite_sleep()
        if r is None:
            log.warning("  %s -> no response", url)
            continue
        forensics.capture_source(
            r.content, url=url, source_type="rasporyazheniya_path_probe",
            title=f"Probe: {path}",
            description="Untested URL-pattern guess (postanovleniya -> rasporyazheniya swap) "
                        "for №619, which is a Распоряжение not a Постановление -- captured "
                        "regardless of status so the probe itself is on the record.",
            content_type=r.headers.get("Content-Type", "text/html"),
            http_status=r.status_code, con=con,
        )
        log.info("  %s -> HTTP %d, %d bytes", url, r.status_code, len(r.content))


# CONFIRMED WORKING 2026-07-04 (third run): the first RASPORYAZHENIYA_PATH_CANDIDATE
# above is real -- a genuine Распоряжения listing (cur_cc=4723, same pagination
# shape as ol.DECREES_PATH's cur_cc=4721). Numbering appears to reset each
# calendar year (Dec 2025 was already at №210, but Feb 2026 starts back at
# №10) -- 2022-2023 plausibly had far higher decree volume (post-occupation
# administrative burst), so №619 (12.10.2023) may sit much deeper in that
# year's own count than the cross-year number jump suggests. This walks
# backward in time, matching on decree number AND checking the date text so a
# same-numbered decree from a different year isn't mistaken for the target.
RASPORYAZHENIYA_LISTING_PATH = RASPORYAZHENIYA_PATH_CANDIDATES[0]
RASPORYAZHENIYA_CC = "cc=4723"
_RASP_HREF_RE = re.compile(r"rasporyazheniya-administratsii-gorodskogo-okruga-mariupol_\d+\.html")
_RASP_NUM_RE = re.compile(r"№\s*(\d+)")
_RASP_DATE_RE = re.compile(
    r"от\s+(\d{1,2})[.\s]+(?:(\d{1,2})|"
    r"(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря))"
    r"[.\s]+(\d{4})", re.I)


def _parse_rasp_date(title: str) -> tuple[int, int, int] | None:
    m = _RASP_DATE_RE.search(title)
    if not m:
        return None
    day = int(m.group(1))
    year = int(m.group(4))
    if m.group(2):
        month = int(m.group(2))
    else:
        months = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля",
                  "августа", "сентября", "октября", "ноября", "декабря"]
        month = months.index(m.group(3).lower()) + 1
    return (year, month, day)


def find_rasporyazhenie_619(s, con, origin: str, max_pages: int = 80) -> list[tuple[str, str]]:
    """Paginate the confirmed-real Распоряжения listing backward in time,
    matching on decree number 619 -- checks EVERY page's dates so we know how
    far back we've gotten, and stops once we're clearly well past 12.10.2023
    (rather than assuming any fixed page count).
    """
    from bs4 import BeautifulSoup
    target_date = (2023, 10, 12)
    matches: list[tuple[str, str]] = []
    cur_pos = 0
    for _ in range(max_pages):
        base = urljoin(origin, RASPORYAZHENIYA_LISTING_PATH)
        url = f"{base}?{RASPORYAZHENIYA_CC}&curPos={cur_pos}" if cur_pos else f"{base}?{RASPORYAZHENIYA_CC}"
        r = ol._get(s, url)
        ol.polite_sleep()
        if r is None or r.status_code != 200:
            log.warning("  page at curPos=%d failed -- stopping", cur_pos)
            break
        forensics.capture_source(
            r.content, url=url, source_type="rasporyazheniya_listing",
            title=f"Mariupol Распоряжения listing, offset {cur_pos}",
            description="Chasing №619 (12.10.2023) -- paginating backward through the "
                        "newly-confirmed Распоряжения listing (scripts/245).",
            content_type=r.headers.get("Content-Type", "text/html"),
            http_status=r.status_code, con=con,
        )
        soup = BeautifulSoup(r.text, "lxml")
        anchors = soup.find_all("a", href=_RASP_HREF_RE)
        if not anchors:
            log.info("  curPos=%d: no Распоряжение anchors -- end of listing", cur_pos)
            break
        page_dates = []
        for a in anchors:
            title = a.get_text(" ", strip=True)
            num_m = _RASP_NUM_RE.search(title)
            date = _parse_rasp_date(title)
            if date:
                page_dates.append(date)
            if num_m and num_m.group(1) == "619" and date == target_date:
                matches.append((urljoin(origin, a["href"]), title))
                log.info("  MATCH at curPos=%d: %s", cur_pos, title[:150])
        if page_dates:
            oldest_on_page = min(page_dates)
            log.info("  curPos=%d: %d anchors, oldest date on page %s", cur_pos, len(anchors), oldest_on_page)
            if oldest_on_page < target_date:
                log.info("  page is already older than target date %s -- stopping", target_date)
                break
        cur_pos += ol.DECREES_PAGE_SIZE
    else:
        log.warning("  hit max_pages=%d without conclusively passing the target date -- "
                    "may need a higher max_pages if this portal has very high volume", max_pages)
    return matches


def raw_anchor_scan_for_619(html_sources: list[str]) -> list[tuple[str, str]]:
    """No href/title filter at all -- just find any <a> whose text contains
    both 'Распоряжен' and '619' anywhere in the same already-fetched pages.
    Returns (href, text) pairs for manual review -- does NOT assume a match
    here is definitely the right decree.
    """
    from bs4 import BeautifulSoup
    hits = []
    for path in html_sources:
        with open(path, encoding="utf-8", errors="replace") as f:
            html = f.read()
        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all("a"):
            text = a.get_text(" ", strip=True)
            if "Распоряжен" in text and "619" in text:
                hits.append((a.get("href", ""), text))
    return hits


def main() -> None:
    con = forensics.open_state()
    s = ol.make_session()

    all_found: dict[str, list[ol.DecreeLink]] = {}
    for target_no, keyword in TARGET_SEARCHES.items():
        log.info("=== Searching for №%s via keyword '%s' ===", target_no, keyword)
        hits = search_by_keyword(s, con, ol.ORIGIN, keyword)
        all_found[target_no] = hits
        log.info("  %d total decrees found for this keyword", len(hits))

    # Also sweep the broader curated ownerless section (cur_cc=7767) -- more
    # complete than the keyword-filtered search per ol.py's own docstring,
    # and may catch №1592/№493/№619 under phrasing the keyword search misses.
    log.info("=== Sweeping curated ownerless section (cur_cc=7767) ===")
    section_decrees = ol.capture_ownerless_section(s, con, ol.ORIGIN)
    log.info("  %d decrees in curated section", len(section_decrees))

    # Capture every decree page whose extracted number matches one of our 3
    # targets -- from EITHER source (keyword search or curated section) -- and
    # report which targets were never found so the gap stays honestly flagged
    # rather than silently dropped.
    matched: dict[str, list[ol.DecreeLink]] = {no: [] for no in TARGET_SEARCHES}
    for target_no in TARGET_SEARCHES:
        for pool in list(all_found.get(target_no, [])) + section_decrees:
            if pool.decree_no == target_no:
                matched[target_no].append(pool)

    for target_no, hits in matched.items():
        if not hits:
            log.warning("№%s: NOT FOUND in any search/section sweep -- still a genuine gap, "
                        "needs a closer look at the portal's own search UI or a different keyword", target_no)
            continue
        log.info("№%s: %d candidate page(s) found -- capturing", target_no, len(hits))
        ol.capture_decree_pages(s, con, hits, ol.ORIGIN)

    # №619-specific fallback, only if the normal path found nothing: it's a
    # Распоряжение, not a Постановление, so every helper above is scoped to
    # the wrong document type.
    if not matched["619"]:
        probe_rasporyazheniya_paths(s, con, ol.ORIGIN)

        log.info("=== Paginating the confirmed-real Распоряжения listing for №619 ===")
        rasp_hits = find_rasporyazhenie_619(s, con, ol.ORIGIN)
        if rasp_hits:
            log.info("  %d match(es) -- fetching the actual decree page(s)", len(rasp_hits))
            for url, title in rasp_hits:
                r = ol._get(s, url)
                ol.polite_sleep()
                if r is None or r.status_code != 200:
                    log.warning("  failed to fetch %s", url)
                    continue
                forensics.capture_source(
                    r.content, url=url, source_type="rasporyazhenie_619",
                    title=title,
                    description="Распоряжение главы администрации г. Мариуполя №619 "
                                "(12.10.2023) -- citywide сплошная инвентаризация order, "
                                "found via scripts/245's Распоряжения-listing pagination.",
                    content_type=r.headers.get("Content-Type", "text/html"),
                    http_status=r.status_code, con=con,
                )
                log.info("  captured: %s", url)
        else:
            log.warning("  no exact №619/12.10.2023 match found within the paginated range -- "
                        "check the log above for how far back the pagination actually reached; "
                        "may need a higher max_pages, or the date/number parsing may need "
                        "adjusting for a title format this listing uses that wasn't anticipated")

            # Last-resort: filter-free anchor scan across every page ever captured
            # from either listing, in case №619 is linked from an unexpected place.
            cur = con.execute(
                "SELECT raw_path FROM source_document WHERE url LIKE ? OR url LIKE ? OR url LIKE ?",
                (f"%{ol.DECREES_PATH}%", f"%{ol.OWNERLESS_SECTION_PATH}%", f"%{RASPORYAZHENIYA_LISTING_PATH}%"),
            )
            all_pages = [row[0] for row in cur.fetchall() if row[0] and Path(row[0]).exists()]
            log.info("  Last-resort raw anchor scan across %d previously-captured pages", len(all_pages))
            hits = raw_anchor_scan_for_619(all_pages)
            if hits:
                log.info("  found %d anchor(s) mentioning both 'Распоряжен' and '619' -- VERIFY BY EYE:", len(hits))
                for href, text in hits:
                    log.info("    %s | %s", href, text[:150])
            else:
                log.warning("  still nothing -- this is now a genuine settled gap for automated "
                            "capture; needs manual portal navigation or a different source.")

    log.info("Done. Check log above for any '№X: NOT FOUND' warnings -- those remain "
              "open gaps needing manual portal navigation rather than automated search.")


if __name__ == "__main__":
    main()
