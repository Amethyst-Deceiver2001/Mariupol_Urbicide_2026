"""Stage 1h: capture DNR/Mariupol normative acts from npa.dnronline.su — a
Latin-transliterated mirror of нпа.днронлайн.рф (the DNR normative-acts
archive targeted by scripts/13_crawl_gko_decrees.py).

CAN run directly from the user's Mac — no VPS/proxy needed. Discovered
2026-06-12: unlike the Cyrillic-punycode domain нпа.днронлайн.рф (которое
script 13 treats as geoblocked + Russian-CA TLS, VPS-only), this Latin mirror
is reachable over plain HTTP, with no geoblock, from outside Russia. Mirrors
the same WordPress content (same category tree, same posts); PDF attachments
are still hosted on the Cyrillic `doc.нпа.днронлайн.рф` subdomain, fetched
here with `verify=config.SSL_VERIFY` (default False) like script 13.

NOTE: only `http://` works for npa.dnronline.su — `https://` returns a
self-signed/Russian-CA cert error (curl exit 60). ORIGIN below is
intentionally http://.

WHAT THIS CAPTURES
------------------
Source types: npa_dnronline_html (HTML) + npa_dnronline_pdf (PDF attachments,
discovered dynamically from each page's `.pdf` links — same approach as
script 13's `_extract_pdf_links`).

KNOWN_DOCS, in order:

1. Указ Главы ДНР №301 (20.06.2022) — "О присвоении наименований,
   переименовании географических объектов и составных частей населённых
   пунктов ДНР". DNR-wide framework that delegates renaming of streets,
   microdistricts and other settlement components to district and
   republic-significance city administrations (incl. Mariupol). The enabling
   norm behind gap [H] (street-renaming decrees) in
   docs/legal_mechanisms_review.md. Signed Д.В. Пушилин.

2. Распоряжение главы администрации г. Мариуполя №61 (03.11.2022) — "Об
   утверждении Временного порядка передачи в аренду имущества муниципальной
   собственности города Мариуполя, Временной методики расчета арендной
   платы...". Municipal rulebook governing lease/disposal of Mariupol
   municipal property — including stock entering via the [A]
   ownerless/registry pipeline. The operational bridge from [A] to
   [D]/[F]/[G] in docs/legal_mechanisms_review.md. Registered Мариупольское
   горуправление юстиции №5351/14.11.2022, signed К.В. Иващенко.

3-5. The remaining 3 items in the "Распоряжения глав городов и районов ДНР"
   category (only 4 items total, across all years, on this portal) —
   Докучаевск №734 (2026, demolition decree for another DNR municipality —
   captured for template comparison against Mariupol's [C] demolition
   decrees), Макеевка №72 (2022), Донецк №40 (2022). Captured for completeness
   of this small, sparsely-populated category.

6-12. All 7 items in the "Распоряжения ГКО ДНР" 2022 category — №51, №10, №9,
   №8, №5, №2, №1. None is Распоряжение №56 (the Mariupol demolition list,
   gap [C]); capturing all 7 corroborates the negative finding (also 0 hits
   in the full region80 index, scripts 35/37) that №56 is not published on
   any normative-acts portal.

See docs/legal_mechanisms_review.md ([A], [H], and the region80-results
section) and docs/dispossession_pipeline.html (Card A, Card H, footer) for
how these citations are used.
"""
from __future__ import annotations

import logging
import re
import time
from urllib.parse import urljoin

import requests
import urllib3
from bs4 import BeautifulSoup
from urllib.parse import urlsplit, urlunsplit

from .. import config, forensics

log = logging.getLogger(__name__)

if not config.SSL_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Latin-transliterated mirror of нпа.днронлайн.рф — plain HTTP only.
ORIGIN = "http://npa.dnronline.su"

# Tuple: (url, title, description)
KNOWN_DOCS: list[tuple[str, str, str]] = [
    (
        f"{ORIGIN}/2022-06-20/ukaz-glavy-donetskoj-narodnoj-respubliki-301-ot-20-06-2022-goda-"
        "o-prisvoenii-naimenovanij-pereimenovanii-geograficheskih-obektov-i-sostavnyh-chastej-"
        "naselennyh-punktov-donetskoj-narodnoj-respubliki.html",
        "Указ Главы ДНР №301 от 20.06.2022 — О присвоении наименований, "
        "переименовании географических объектов и составных частей "
        "населённых пунктов ДНР",
        "DNR-wide framework approving the 'Временные правила присвоения "
        "наименований, переименования географических объектов и составных "
        "частей населённых пунктов ДНР' and delegating renaming authority "
        "over streets/microdistricts/other settlement components to "
        "district and republic-significance city administrations (incl. "
        "Mariupol). Enabling norm for gap [H] (street-renaming decrees) in "
        "docs/legal_mechanisms_review.md. Signed Д.В. Пушилин.",
    ),
    (
        f"{ORIGIN}/2022-11-15/rasporyazhenie-glavy-administratsii-goroda-mariupolya-"
        "donetskoj-narodnoj-respubliki-61-ot-03-11-2022-goda-ob-utverzhdenii-vremennogo-"
        "poryadka-peredachi-v-arendu-imushhestva-munitsipalnoj-sobstvennosti.html",
        "Распоряжение главы администрации г. Мариуполя №61 от 03.11.2022 — "
        "Об утверждении Временного порядка передачи в аренду имущества "
        "муниципальной собственности города Мариуполя",
        "Municipal rulebook governing lease/disposal of Mariupol municipal "
        "property — including stock entering via the [A] "
        "ownerless/registry-inclusion pipeline — with its own "
        "rent-calculation methodology. The operational bridge from [A] to "
        "[D]/[F]/[G] in docs/legal_mechanisms_review.md. Registered "
        "Мариупольское горуправление юстиции №5351/14.11.2022, signed "
        "К.В. Иващенко.",
    ),
    (
        f"{ORIGIN}/2026-03-23/postanovlenie-administratsii-gorodskogo-okruga-dokuchaevsk-"
        "donetskoj-narodnoj-respubliki-734-ot-02-03-2026-goda-o-snose-obektov-"
        "povrezhdennyh-v-rezultate-boevyh-dejstvij-raspolozhennyh-na-territorii-m.html",
        "Постановление Администрации г.о. Докучаевск ДНР №734 от 02.03.2026 — "
        "О снове объектов, повреждённых в результате боевых действий",
        "Demolition decree for a different DNR municipality (Докучаевск), "
        "captured for comparison — one of only 4 items total (all years) in "
        "the 'Распоряжения глав городов и районов ДНР' category on this "
        "portal. Helps establish whether Mariupol's [C] demolition-decree "
        "format follows a DNR-wide municipal template.",
    ),
    (
        f"{ORIGIN}/2022-11-11/rasporyazhenie-glavy-administratsii-goroda-makeevki-"
        "donetskoj-narodnoj-respubliki-72-ot-24-10-2022-goda-o-priostanovlenii-dejstviya-"
        "rasporyazheniya-glavy-administratsii-goroda-makeevki-ot-20-03-2020-2.html",
        "Распоряжение главы администрации г. Макеевки №72 от 24.10.2022",
        "Captured for completeness of the 'Распоряжения глав городов и "
        "районов ДНР' category (only 4 items total on this portal, across "
        "all years) — establishes the comparison set for municipal-decree "
        "publication patterns relevant to [A]/[H].",
    ),
    (
        f"{ORIGIN}/2022-01-27/rasporyazhenie-glavy-administratsii-goroda-donetska-"
        "donetskoj-narodnoj-respubliki-40-ot-17-01-2022-goda-o-vnesenii-izmenenij-v-"
        "rasporyazhenie-glavy-administratsii-g-donetska-ot-16-oktyabrya-2015-goda.html",
        "Распоряжение главы администрации г. Донецка №40 от 17.01.2022",
        "Captured for completeness of the 'Распоряжения глав городов и "
        "районов ДНР' category (only 4 items total on this portal, across "
        "all years) — establishes the comparison set for municipal-decree "
        "publication patterns relevant to [A]/[H].",
    ),
    (
        f"{ORIGIN}/2022-10-06/rasporyazhenie-gosudarstvennogo-komiteta-oborony-dnr-51-ot-"
        "29-09-2022-g.html",
        "Распоряжение ГКО ДНР №51 от 29.09.2022",
        "One of 7 items in the 'Распоряжения ГКО ДНР' 2022 category on this "
        "portal — captured to corroborate the [C] negative finding that "
        "Распоряжение ГКО ДНР №56 (29.09.2022, the Mariupol demolition list) "
        "is absent from this category (also 0 hits in the full region80 "
        "index, scripts 35/37). Concerns Donetsk unfinished construction, "
        "not Mariupol.",
    ),
    (
        f"{ORIGIN}/2022-04-25/rasporyazhenie-gosudarstvennogo-komiteta-oborony-dnr-10-ot-"
        "21-04-2022-g-o-sozdanii-rabochej-gruppy-po-uregulirovaniyu-organizatsionnyh-"
        "voprosov-morskogo-porta-goroda-mariupolya-donetskoj-narodnoj-res.html",
        "Распоряжение ГКО ДНР №10 от 21.04.2022 — О создании рабочей группы "
        "по урегулированию организационных вопросов морского порта города "
        "Мариуполя",
        "One of 7 items in the 'Распоряжения ГКО ДНР' 2022 category — "
        "Mariupol-relevant (sea port working group) but not "
        "demolition/property; captured for the [C] negative-finding "
        "corroboration set (№56 absent from this category, see №51 entry "
        "above).",
    ),
    (
        f"{ORIGIN}/2022-04-25/rasporyazhenie-gosudarstvennogo-komiteta-oborony-dnr-9-ot-"
        "21-04-2022-g-o-nekotoryh-voprosah-okazaniya-meditsinskoj-pomoshhi-v-gorode-"
        "mariupole.html",
        "Распоряжение ГКО ДНР №9 от 21.04.2022 — О некоторых вопросах "
        "оказания медицинской помощи в городе Мариуполе",
        "One of 7 items in the 'Распоряжения ГКО ДНР' 2022 category — "
        "Mariupol-relevant (medical aid) but not demolition/property; "
        "captured for the [C] negative-finding corroboration set (№56 "
        "absent from this category, see №51 entry above).",
    ),
    (
        f"{ORIGIN}/2022-04-25/rasporyazhenie-gosudarstvennogo-komiteta-oborony-dnr-8-ot-"
        "21-04-2022-g.html",
        "Распоряжение ГКО ДНР №8 от 21.04.2022",
        "One of 7 items in the 'Распоряжения ГКО ДНР' 2022 category — "
        "captured for the [C] negative-finding corroboration set (№56 "
        "absent from this category, see №51 entry above).",
    ),
    (
        f"{ORIGIN}/2022-04-09/rasporyazhenie-gosudarstvennogo-komiteta-oborony-dnr-5-ot-"
        "09-04-2022-g.html",
        "Распоряжение ГКО ДНР №5 от 09.04.2022",
        "One of 7 items in the 'Распоряжения ГКО ДНР' 2022 category — "
        "captured for the [C] negative-finding corroboration set (№56 "
        "absent from this category, see №51 entry above).",
    ),
    (
        f"{ORIGIN}/2022-04-06/rasporyazhenie-gosudarstvennogo-komiteta-oborony-dnr-2-ot-"
        "06-04-2022-g.html",
        "Распоряжение ГКО ДНР №2 от 06.04.2022",
        "One of 7 items in the 'Распоряжения ГКО ДНР' 2022 category — "
        "captured for the [C] negative-finding corroboration set (№56 "
        "absent from this category, see №51 entry above).",
    ),
    (
        f"{ORIGIN}/2022-04-06/rasporyazhenie-gosudarstvennogo-komiteta-oborony-dnr-1-ot-"
        "06-04-2022-g.html",
        "Распоряжение ГКО ДНР №1 от 06.04.2022",
        "One of 7 items in the 'Распоряжения ГКО ДНР' 2022 category — "
        "captured for the [C] negative-finding corroboration set (№56 "
        "absent from this category, see №51 entry above).",
    ),
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


def _fix_pdf_host(url: str) -> str:
    """Rewrite 'doc.<domain>' hosts to the bare domain.

    Confirmed 2026-06-12: doc.нпа.днронлайн.рф (and its punycode form
    doc.xn--80azg.xn--80ahqgjaddr.xn--p1ai) is NXDOMAIN globally -- not a
    geoblock, the hostname simply doesn't exist. The bare domain
    нпа.днронлайн.рф resolves and serves the same /wp-content/uploads/ paths
    (confirmed working for the Dokuchaevsk PDF in the same run).
    """
    parts = urlsplit(url)
    if parts.netloc.lower().startswith("doc."):
        parts = parts._replace(netloc=parts.netloc[len("doc."):])
        return urlunsplit(parts)
    return url


def _extract_pdf_links(soup: BeautifulSoup, page_url: str) -> list[str]:
    urls = []
    for a in soup.find_all("a", href=re.compile(r"\.pdf", re.I)):
        href = a.get("href", "")
        if href:
            url = href if href.startswith("http") else urljoin(page_url, href)
            urls.append(_fix_pdf_host(url))
    return urls


def capture_known_docs(s: requests.Session, con) -> None:
    """Capture each known npa.dnronline.su page and any PDF attachments."""
    for url, title, description in KNOWN_DOCS:
        key = f"npa_dnronline::{url}"
        if forensics.is_done(con, key):
            log.debug("skip (already done): %s", title)
            continue

        r = _get(s, url)
        polite_sleep()
        if r is None or r.status_code != 200:
            log.warning("page not fetched: %s (HTTP %s)",
                         title, r.status_code if r else "N/A")
            continue

        forensics.capture_source(
            r.content, url=url,
            source_type="npa_dnronline_html",
            title=title,
            description=description,
            content_type=r.headers.get("Content-Type", "text/html"),
            http_status=r.status_code, con=con,
        )

        soup = BeautifulSoup(r.text, "lxml")
        for pdf_url in _extract_pdf_links(soup, url):
            pdf_key = f"npa_dnronline_pdf::{pdf_url}"
            if forensics.is_done(con, pdf_key):
                continue
            pr = _get(s, pdf_url)
            polite_sleep()
            if pr is None or pr.status_code != 200:
                log.warning("PDF not fetched: %s", pdf_url)
                continue
            forensics.capture_source(
                pr.content, url=pdf_url,
                source_type="npa_dnronline_pdf",
                title=f"{title} [PDF]",
                description=f"Signed PDF original of: {description}",
                content_type=pr.headers.get("Content-Type", "application/pdf"),
                http_status=pr.status_code, con=con,
            )
            forensics.mark_done(con, pdf_key)
            log.info("captured PDF: %s", pdf_url)

        forensics.mark_done(con, key)
        log.info("captured: %s", title)


def run() -> None:
    con = forensics.open_state()
    s = make_session()
    try:
        capture_known_docs(s, con)
    except KeyboardInterrupt:
        log.warning("interrupted — state saved, safe to rerun.")

    n = con.execute(
        "SELECT COUNT(*) FROM source_document "
        "WHERE source_type LIKE 'npa_dnronline%'"
    ).fetchone()[0]
    log.info("done; %d npa.dnronline.su artifacts in store", n)
