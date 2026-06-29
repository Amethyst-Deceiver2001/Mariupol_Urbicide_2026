#!/usr/bin/env python3
"""Follow-up to scripts/214. Two parts:

1. ФКЗ-4 is CONFIRMED FOUND: nd=609234940 in the scripts/214 list_itself
   capture for the ФКЗ-4 query is "Федеральный конституционный закон от
   15.12.2025 № 4-ФКЗ -- О внесении изменений в отдельные федеральные
   конституционные законы" -- exact number+date match. This fetches its
   full text via the "docbody" link (the same param pattern as the
   "Текст документа" link in the list row).

2. Decree No. 201 search is REFINED, not yet found: the prior free-text
   query ("Указ Президента 201 20.03.2020") matched dozens of unrelated
   "№ 201" decrees from other years, sorted by date descending -- the 2020
   one never surfaced in the first page. Decree No. 201 (20.03.2020) is
   recalled (general knowledge, NOT yet confirmed) to be an AMENDMENT to
   Presidential Decree No. 26 (09.01.2011), which originally listed the
   border territories where foreigners can't own land -- No. 201 added
   Crimean territories to that list. Retrying with a query naming Decree
   No. 26 should rank the right amendment much higher. If this still
   doesn't surface it, the next step is paginating the original query
   (page=2,3... via the &start=20/40/... links already visible in the
   captured searchlist HTML) instead of refining the query further.

Run:
    PYTHONPATH=src python scripts/215_fetch_pravo_doc_text.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import requests  # noqa: E402
import urllib3  # noqa: E402

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

if not config.SSL_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE = "http://pravo.gov.ru/proxy/ips/"

# Part 1 -- direct document fetch by known nd= id (FKZ-4, confirmed).
DOC_TARGETS = [
    {
        "nd": "609234940",
        "q": "Федеральный конституционный закон 4 15.12.2025",
        "source_type": "fkz4_full_text",
        "title": "ФКЗ от 15.12.2025 № 4-ФКЗ -- О внесении изменений в отдельные федеральные конституционные законы (full text)",
        "description": (
            "Q13 -- CONFIRMED match (exact number+date) found via "
            "scripts/214's list_itself capture, nd=609234940. This is "
            "ФКЗ-4 itself, still only [REPORTED] in legal_mechanisms_"
            "review.md -- this fetch attempts the primary text."
        ),
    },
]

# Part 2 -- refined search query for Decree No. 201, naming the decree it
# amends (No. 26/09.01.2011) to rank it above unrelated same-numbered acts.
SEARCH_TARGETS = [
    {
        "q": "Указ Президента 201 20.03.2020 26 09.01.2011 иностранные граждане земельные участки приграничные territории",
        "source_type": "crimea_decree_201_refined_searchlist",
        "title": "pravo.gov.ru ИПС searchlist (refined) -- Указ №201 20.03.2020, amendment to Указ №26",
        "description": (
            "Q12 refined query -- Decree No. 201 is recalled (unconfirmed) "
            "to amend Presidential Decree No. 26 (09.01.2011, original "
            "border-territory foreign-land-ownership list). Naming No. 26 "
            "should rank the right document above unrelated same-numbered "
            "acts from other years that buried it in the first query."
        ),
    },
]


def fetch_and_capture(con, s, url, source_type, title, description, content_type="text/html"):
    log.info("Fetching %s", url)
    try:
        r = s.get(url, timeout=config.TIMEOUT, verify=config.SSL_VERIFY, allow_redirects=True)
    except requests.RequestException as e:
        log.error("  FAILED: %s -- retry from the VPS if connection/TLS error", e)
        return
    if r.status_code != 200:
        log.warning("  HTTP %d for %s -- captured anyway for the record", r.status_code, url)
    sha = forensics.capture_source(
        r.content, url=url, source_type=source_type, title=title,
        description=description, content_type=r.headers.get("Content-Type", content_type),
        http_status=r.status_code, con=con,
    )
    log.info("  status=%d sha=%s bytes=%d", r.status_code, sha[:16], len(r.content))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    con = forensics.open_state()
    s = requests.Session()
    s.headers.update({"User-Agent": config.USER_AGENT, "Accept-Language": "ru,en;q=0.8"})
    if config.PROXY:
        s.proxies.update({"http": config.PROXY, "https": config.PROXY})

    for t in DOC_TARGETS:
        url = (f"{BASE}?docbody=&link_id=3&nd={t['nd']}&bpa=cd00000&bpas=cd00000"
               f"&intelsearch={quote(t['q'])}&firstDoc=1")
        fetch_and_capture(con, s, url, t["source_type"], t["title"], t["description"])

    for t in SEARCH_TARGETS:
        url = f"{BASE}?searchlist=&bpas=cd00000&intelsearch={quote(t['q'])}&sort=7"
        fetch_and_capture(con, s, url, t["source_type"], t["title"], t["description"])

    log.info("Done. For DOC_TARGETS: decode windows-1251, check this is "
              "actually the FKZ-4 article text (not another wrapper). For "
              "SEARCH_TARGETS: same drill as before -- searchlist may need "
              "one more list_itself hop (scripts/214's pattern) before the "
              "real hits show.")


if __name__ == "__main__":
    main()
