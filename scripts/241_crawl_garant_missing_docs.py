#!/usr/bin/env python3
"""Crawl base.garant.ru for the primary texts this project is still missing.

GARANT is a Russian commercial legal-reference database. Some pages resolve
fine from outside Russia; others 403/redirect to a login wall or are geoblocked
outright -- treat this the same as the court portals: **run this yourself**,
from your Russia-routed VPS if the direct attempt below fails.

Two kinds of target:

  DIRECT  -- a candidate GARANT URL is already known (found during earlier
             review/research passes). Fetched directly and captured verbatim.
  SEARCH  -- no URL is known yet. This script hits GARANT's site search with a
             query built from the decree's number/date/title and captures the
             *raw search-results HTML* -- it does NOT try to auto-follow the
             top hit, because guessing wrong and capturing the wrong decree
             under the right decree's name would be worse than not capturing
             it at all. After running, open the captured search HTML (path
             printed at the end) and read off the correct base.garant.ru/NNNN/
             link yourself; add it to the DIRECT list on a re-run to capture
             the actual document.

Every fetch (hit or miss, 200 or not) is written to data/raw/ with a sidecar
.meta.json via forensics.capture_source -- per project rule, capture before
parse, and capture the miss too so the attempt is on the record.

Run:
    PYTHONPATH=src python scripts/241_crawl_garant_missing_docs.py
    PYTHONPATH=src python scripts/241_crawl_garant_missing_docs.py --search-only
    PYTHONPATH=src python scripts/241_crawl_garant_missing_docs.py --direct-only
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import requests  # noqa: E402
import urllib3  # noqa: E402

from mariupol_seizures import config, forensics  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
log = logging.getLogger(__name__)

if not config.SSL_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@dataclass
class DirectTarget:
    url: str
    source_type: str
    title: str
    description: str


@dataclass
class SearchTarget:
    query: str
    source_type: str
    title: str
    description: str


# ── DIRECT: candidate URLs already found, never yet captured ────────────────
DIRECT: list[DirectTarget] = [
    DirectTarget(
        url="https://base.garant.ru/406063821/",
        source_type="gko_rf_resolution_2501",
        title="Постановление Правительства РФ №2501 (29.12.2022) — GARANT mirror",
        description=(
            "Task 6 / the federal property-demarcation parent decree for all 4 "
            "annexed regions. publication.pravo.gov.ru has the document but only "
            "as a JS shell (no text landed); this is the alternate GARANT mirror "
            "candidate, cited by the outsourced researcher without ever being "
            "fetched by them."
        ),
    ),
    DirectTarget(
        url="https://www.garant.ru/products/ipo/prime/doc/411086311/",
        source_type="presidential_decree_1103",
        title="Указ Президента РФ №1103 (24.12.2024) — GARANT card",
        description=(
            "Task 9. Same JS-shell problem on publication.pravo.gov.ru. Also the "
            "page needed to settle whether 'совершения отдельных нотариальных "
            "действий' belongs to №1103's own title or was conflated from a "
            "later amendment (likely №1006) -- a prior ad hoc curl fetch to this "
            "exact URL returned empty output and was never retried."
        ),
    ),
    # №87-1 removed 2026-07-04: confirmed via scripts/242 (headless browser,
    # cleared DDoS-Guard fine) that the previously-cited URL is a genuine 404,
    # AND confirmed via ivo.garant.ru's own search ("Информация по данному
    # запросу отсутствует в вашем комплекте") that this document simply isn't
    # in GARANT's index at all. Settled negative, not a gap to keep chasing here.
    DirectTarget(
        url="https://base.garant.ru/411965330/",
        source_type="gko_rf_resolution_594",
        title="Постановление Правительства РФ №594 (30.04.2025) — amends №2501",
        description=(
            "New lead surfaced inside №2501's own captured text (scripts/241 "
            "earlier run): 'Пункт 2 изменен с 9 мая 2025 г. — Постановление "
            "Правительства России от 30 апреля 2025 г. N 594'. Found via "
            "ivo.garant.ru search (scripts/242) -- confirmed same base.garant.ru "
            "ID space (this ID matches the ivo.garant.ru/#/document/411965330/ "
            "search hit exactly), so a plain fetch should work without the browser."
        ),
    ),
    DirectTarget(
        url="https://base.garant.ru/406063823/",
        source_type="gko_rf_resolution_2502",
        title="Постановление Правительства РФ №2502 (29.12.2022) — sibling coordination decree to №2501",
        description=(
            "New lead, never previously documented in this project: surfaced as "
            "the #3 hit alongside №594/№2501 during the same ivo.garant.ru search "
            "(scripts/242). Title: «О порядке и случаях согласования правовых "
            "актов и других решений органов государственной власти ДНР и ЛНР, "
            "органов публичной власти Запорожской области и Херсонской области в "
            "отношении управления и распоряжения отдельными объектами имущества» "
            "-- a federal-DNR/LNR/Zaporizhzhia/Kherson coordination-procedure "
            "decree, issued the same day as №2501. Possibly relevant to the "
            "still-open Task 8 (ФКЗ-4's Rosreestr/Rosimushchestvo 'по "
            "согласованию' coordination requirement) -- read the full text "
            "before assuming that connection, don't state it as confirmed."
        ),
    ),
    # Foundational RF codes -- found via scripts/242 ivo.garant.ru search,
    # 2026-07-04. These IDs are the whole code (all parts), not single-article
    # extracts -- codes are large, so this fetches the full document; the
    # specific article text needs to be located within it after capture.
    DirectTarget(
        url="https://base.garant.ru/10164072/",
        source_type="gk_rf_full_text",
        title="Гражданский кодекс РФ (ГК РФ, части I-IV) — full text",
        description=(
            "Contains ст. 225 (бесхозяйные вещи -- substantive basis for the "
            "ownerless-registry track, previously [REPORTED] only) and ст. 1067 "
            "(крайняя необходимость -- cited inside Указ №515 as forced-entry "
            "basis, previously cited-only). Whole code, not a single-article "
            "extract -- locate both articles within it after capture."
        ),
    ),
    DirectTarget(
        url="https://base.garant.ru/12138291/",
        source_type="zhk_rf_full_text",
        title="Жилищный кодекс РФ (ЖК РФ) — full text",
        description=(
            "Contains ч.3 ст.3 (home-inviolability exception, also cited inside "
            "Указ №515 alongside ГК РФ ст.1067). Whole code -- locate the article "
            "within it after capture."
        ),
    ),
    DirectTarget(
        url="https://base.garant.ru/12128809/",
        source_type="gpk_rf_full_text",
        title="Гражданский процессуальный кодекс РФ (ГПК РФ) — full text",
        description=(
            "Bonus find alongside the others (same search batch). Гл. 33 "
            "(особое производство) is the case-type basis for the whole occupation "
            "court layer -- already [CAPTURED] separately per scripts 03/178/182-185, "
            "but the code's own full text was never itself in the raw store."
        ),
    ),
]

# ── SEARCH: no URL known yet -- capture the search-results page, follow up by hand ──
SEARCH: list[SearchTarget] = [
    SearchTarget(
        query="Постановление Правительства Донецкой Народной Республики 38-7 11.04.2024 компенсация",
        source_type="search_dnr_resolution_38_7",
        title="GARANT search — Постановление ПравДНР №38-7 (11.04.2024, compensation amendment)",
        description=(
            "Task 10. Known only via a citation inside a Счетная палата reply "
            "letter; whether it raised/lowered the compensation sum is unknown. "
            "No direct URL found yet."
        ),
    ),
    SearchTarget(
        query="Закон Донецкой Народной Республики 71-РЗ внесение изменений 52-РЗ бесхозяйные движимые вещи",
        source_type="search_dnr_law_71rz",
        title="GARANT search — Закон ДНР №71-РЗ (amendment to №52-РЗ)",
        description=(
            "Both the outsourced researcher's cited gb-dnr.ru URL and a "
            "'corrected' one found during review 404 -- no working URL for this "
            "amendment exists anywhere yet."
        ),
    ),
    SearchTarget(
        query="Распоряжение главы администрации города Мариуполя 619 12.10.2023 сплошная инвентаризация",
        source_type="search_mariupol_order_619",
        title="GARANT search — Распоряжение главы администрации г. Мариуполя №619 (12.10.2023)",
        description=(
            "Task 11. Citywide property-inventory order; text confirmed verbatim "
            "inside multiple resident Telegram chats, but the primary scan itself "
            "was never captured. GARANT rarely mirrors municipal-level orders -- "
            "low-probability hit, worth one try before falling back to VPS/"
            "mariupol.gosuslugi.ru."
        ),
    ),
    SearchTarget(
        query="Постановление Администрации города Мариуполя 1592 17.10.2025",
        source_type="search_mariupol_resolution_1592",
        title="GARANT search — Постановление Администрации г. Мариуполя №1592 (17.10.2025)",
        description="Task 4. Municipal ownerless-designation decree, not yet pulled.",
    ),
    SearchTarget(
        query="маневренный фонд Кольцов 493 05.03.2026 Жилсервис",
        source_type="search_dnr_decree_493",
        title="GARANT search — маневренный фонд Decree №493 (05.03.2026, Кольцов)",
        description=(
            "Task 5. The one specific allocation decree left uncaptured after the "
            "general маневренный-фонд/служебное-жильё framework was resolved."
        ),
    ),
    SearchTarget(
        query="Постановление ГКО ДНР 341 29.09.2022 Перечень имущества обращенного в собственность",
        source_type="search_gko_341",
        title="GARANT search — Постановление ГКО №341 (29.09.2022, property-transfer list)",
        description=(
            "Task 2. Title confirmed via Указ №299's captured text; lead suspect "
            "for the 2024 registration-freeze episode. Primary text not captured."
        ),
    ),
    SearchTarget(
        query='Указ 307 Донецкая Народная Республика реестр регистрация',
        source_type="search_ukaz_307",
        title="GARANT search — \"Указ №307\" (freeze-fix decree vs. №299 amendment disambiguation)",
        description="Task 3. Unclear if this is a standalone decree or one of №299's 10 amendments.",
    ),
]


def _search_url(query: str) -> str:
    return f"https://base.garant.ru/search/?search_query={quote(query)}"


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": config.USER_AGENT,
        "Accept-Language": "ru,en;q=0.8",
    })
    if config.PROXY:
        s.proxies.update({"http": config.PROXY, "https": config.PROXY})
    return s


def run_direct(s: requests.Session, con) -> None:
    log.info("=== DIRECT targets (%d) ===", len(DIRECT))
    for t in DIRECT:
        log.info("Fetching %s", t.url)
        try:
            r = s.get(t.url, timeout=config.TIMEOUT, verify=config.SSL_VERIFY, allow_redirects=True)
        except requests.RequestException as e:
            log.error("  FAILED: %s -- retry from the VPS if connection/TLS error", e)
            continue
        if r.status_code != 200:
            log.warning("  HTTP %d for %s -- captured anyway for the record", r.status_code, t.url)
        sha = forensics.capture_source(
            r.content, url=t.url, source_type=t.source_type, title=t.title,
            description=t.description,
            content_type=r.headers.get("Content-Type", "text/html"),
            http_status=r.status_code, con=con,
        )
        log.info("  status=%d sha=%s bytes=%d -> data/raw/%s.*", r.status_code, sha[:16], len(r.content), sha[:16])
        time.sleep(1.5)


def run_search(s: requests.Session, con) -> None:
    log.info("=== SEARCH targets (%d) ===", len(SEARCH))
    for t in SEARCH:
        url = _search_url(t.query)
        log.info("Searching: %s", t.query)
        try:
            r = s.get(url, timeout=config.TIMEOUT, verify=config.SSL_VERIFY, allow_redirects=True)
        except requests.RequestException as e:
            log.error("  FAILED: %s -- retry from the VPS if connection/TLS error", e)
            continue
        if r.status_code != 200:
            log.warning("  HTTP %d for %s -- captured anyway for the record", r.status_code, url)
        sha = forensics.capture_source(
            r.content, url=url, source_type=t.source_type, title=t.title,
            description=t.description,
            content_type=r.headers.get("Content-Type", "text/html"),
            http_status=r.status_code, con=con,
        )
        raw_path = ROOT / "data" / "raw"
        matches = [p for p in raw_path.glob(f"{sha}.*") if p.suffix != ".json"]
        log.info("  status=%d sha=%s bytes=%d -> %s", r.status_code, sha[:16], len(r.content),
                  matches[0] if matches else "?")
        time.sleep(1.5)

    log.info(
        "Done with SEARCH targets. Open each captured file above and read off the "
        "real base.garant.ru/NNNNNNN/ or garant.ru/products/ipo/prime/doc/NNNNNNN/ "
        "link for the actual decree -- do not assume the first hit is correct. "
        "Add confirmed URLs to the DIRECT list and re-run with --direct-only."
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--direct-only", action="store_true")
    ap.add_argument("--search-only", action="store_true")
    args = ap.parse_args()

    con = forensics.open_state()
    s = _session()

    if not args.search_only:
        run_direct(s, con)
    if not args.direct_only:
        run_search(s, con)


if __name__ == "__main__":
    main()
