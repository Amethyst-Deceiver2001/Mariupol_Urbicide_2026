#!/usr/bin/env python3
"""Capture step 1 (discovery) for two primary-text gaps flagged in
docs/exhibits/two-property-systems.html and tracked as Q12/Q13 in
docs/research_outsourcing/OPEN_QUESTIONS_2026-06-29.md:

1. Q12 -- Presidential Decree No. 201 (20.03.2020), the Crimea border-
   territory foreign-ownership ban that is the genealogical first step in
   the property-law sequence later used in Mariupol. We have the number and
   date (from secondary reporting -- Moscow Times, HRH Crimea) but no
   pravo.gov.ru publication id, so unlike scripts/207/208 (which already had
   the eoNumber) this has to start with a SEARCH, not a direct document/view
   fetch.

2. Q13 -- ФКЗ-4 (15.12.2025) itself, still only [REPORTED] in
   legal_mechanisms_review.md -- we have its DNR implementing acts
   (закон №134-РЗ/№240-РЗ/№275-РЗ, captured) but never the federal text
   itself, including the Rosreestr/Rosimushchestvo "signs of ownerless
   property" provisions a research synthesis attributed to it.

This uses pravo.gov.ru's public full-text search ("ИПС «Законодательство
России»", bpas=cd00000) rather than a guessed document id. WHATEVER the
search page returns gets captured verbatim (forensic-first, per CLAUDE.md) --
even if it's a JS-shell SPA wrapper like the View pages in scripts/207, that
shell is still evidence of what the search returned, and likely still
embeds the real document link/eoNumber the same way those did. Inspect the
captured HTML afterward (grep for "eoNumber=", "/document/view/", or the
decree number) and write a follow-up script (213) mirroring scripts/208's
direct-PDF fetch once a real id surfaces -- do not guess one now.

WHY THIS IS USER-RUN-ONLY
--------------------------
pravo.gov.ru is the same geoblocked Russian federal legal-publication portal
as scripts/207/208 (confirmed geoblocked again this session -- a direct
fetch attempt failed even before reaching the user's network). Run this from
the Russia-routed VPS, same as every other pravo.gov.ru/npa.dnronline.su
capture in this project.

Run:
    PYTHONPATH=src python scripts/212_search_crimea201_fkz4_sources.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import requests  # noqa: E402
import urllib3  # noqa: E402

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

if not config.SSL_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TARGETS = [
    {
        # pravo.gov.ru free-text search ("ИПС «Законодательство России»").
        # bpas=cd00000 = the standing legal-acts database code; intelsearch
        # is the free-text query, sort=7 = by date descending. If this
        # param set is stale/wrong, the page still returns SOMETHING --
        # capture it anyway and read the actual search form HTML for the
        # current param names before retrying.
        "url": ("http://pravo.gov.ru/proxy/ips/"
                "?searchres=&bpas=cd00000&intelsearch="
                "Указ+Президента+201+20.03.2020&sort=7"),
        "source_type": "crimea_decree_201_search",
        "title": "pravo.gov.ru search -- Указ Президента РФ №201 от 20.03.2020",
        "description": (
            "Discovery fetch for Q12 (docs/research_outsourcing/"
            "OPEN_QUESTIONS_2026-06-29.md). No known publication id yet -- "
            "this is a free-text search, not a direct document fetch. "
            "Genealogical first step in docs/exhibits/two-property-"
            "systems.html, currently [Crawl gap]."
        ),
    },
    {
        "url": ("http://pravo.gov.ru/proxy/ips/"
                "?searchres=&bpas=cd00000&intelsearch="
                "Федеральный+конституционный+закон+4+15.12.2025&sort=7"),
        "source_type": "fkz4_search",
        "title": "pravo.gov.ru search -- ФКЗ-4 от 15.12.2025",
        "description": (
            "Discovery fetch for Q13 (docs/research_outsourcing/"
            "OPEN_QUESTIONS_2026-06-29.md). ФКЗ-4 is still only [REPORTED] "
            "in legal_mechanisms_review.md -- DNR implementing acts are "
            "captured, the federal text itself never has been."
        ),
    },
    {
        # If the ИПС search above 404s or comes back empty, this is the
        # alternate/legacy human search UI worth trying by hand in a
        # browser session over the VPS (not scriptable the same way -- it
        # may require a POST + session cookie). Captured here anyway as a
        # landing-page fallback so the raw HTML is on record either way.
        "url": "http://publication.pravo.gov.ru/",
        "source_type": "pravo_gov_ru_landing",
        "title": "publication.pravo.gov.ru landing page (fallback reference)",
        "description": (
            "Captured only as a fallback reference for manual search if "
            "the ИПС query above doesn't resolve -- not itself evidence of "
            "either target instrument."
        ),
    },
]


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": config.USER_AGENT, "Accept-Language": "ru,en;q=0.8"})
    if config.PROXY:
        s.proxies.update({"http": config.PROXY, "https": config.PROXY})
    return s


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    con = forensics.open_state()
    s = make_session()

    for t in TARGETS:
        log.info("Fetching %s", t["url"])
        try:
            r = s.get(t["url"], timeout=config.TIMEOUT, verify=config.SSL_VERIFY,
                      allow_redirects=True)
        except requests.RequestException as e:
            log.error("  FAILED: %s -- if this is a connection/TLS error, retry from the VPS", e)
            continue

        if r.status_code != 200:
            log.warning("  HTTP %d for %s -- captured anyway for the record", r.status_code, t["url"])

        sha = forensics.capture_source(
            r.content, url=t["url"], source_type=t["source_type"],
            title=t["title"], description=t["description"],
            content_type=r.headers.get("Content-Type", "text/html"),
            http_status=r.status_code, con=con,
        )
        log.info("  status=%d sha=%s bytes=%d", r.status_code, sha[:16], len(r.content))

    log.info("Done. Next: read each captured search-result page for a real "
              "document link (grep for 'eoNumber=', '/document/', or the "
              "decree number/date). Paste the resulting URL(s) back and a "
              "follow-up script (213, mirroring scripts/208's direct PDF "
              "fetch) can pull the signed text.")


if __name__ == "__main__":
    main()
