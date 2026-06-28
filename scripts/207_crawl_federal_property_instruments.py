#!/usr/bin/env python3
"""Capture four primary legal instruments identified by the outsourced
research report (docs/research_outsourcing/mariupol_urbicide_research_
aggregation.md, Q1/Q2/Q3/Q8), each previously [CITED]-only in the project:

1. Постановление Правительства РФ от 31.12.2022 № 2565 (Q1) -- the FOUNDING
   instrument of the 2% subsidized-mortgage program in the occupied regions
   (ДОМ.РФ subsidy rules; later amended by №1123/08.07.2023 and №2166/
   15.12.2023, the latter already captured in scripts/197). Closes the
   "original launch decree unknown" sub-gap left open by scripts/197.
   pravo.gov.ru publication id 0001202301030011 (published 03.01.2023 --
   matches the early-Jan-2023 press timing).

2. Постановление Правительства РФ от 29.12.2022 № 2501 (Q2) -- federal/
   municipal property demarcation framework for DNR/LNR/Zaporizhzhia/
   Kherson; the legal basis cited inside Закон №269-РЗ for routing some
   housing into FEDERAL (not municipal) ownership. Housing enters via
   Приложение №2 item 9 ("Жилищный фонд...") -- the "may be federal,
   regional or municipal" class, assignable by Росимущество + a collegiate
   body (Arts 6¹/7/19). pravo.gov.ru publication id 0001202212300029.

3. Постановление Правительства РФ от 22.12.2023 № 2255 (Q3) -- the federal
   reconstruction госпрограмма whose Приложение №4 sets the per-m²
   housing-loss compensation rate that Закон №269-РЗ Ст.7 п.3 defers to.
   NOTE: the research report DEDUCED the rate (51,500 ₽/m²) from an
   amendment DRAFT that lists the old values being replaced -- it did NOT
   read the rate from the primary Приложение №4 text. Treat 51,500 ₽/m² as
   UNCONFIRMED pending this capture + a read of the actual annex (same
   press-paraphrase-vs-primary-text discipline as the 25 m² cap correction;
   see RESEARCH_BRIEF.md §4). pravo.gov.ru publication id 0001202312290053
   (this госпрограмма is large; the View page may link a multi-part PDF --
   capture whatever it returns, parse the annex afterward).

4. Распоряжение главы администрации г. Мариуполя от 03.11.2022 № 61 (Q8) --
   the municipal property-lease rulebook (Временный порядок передачи в
   аренду + Временная методика расчёта арендной платы), registered by the
   Mariupol gorupravlenie yustitsii under №5351 on 14.11.2022. The PDF on
   нпа.днронлайн was dead-linked (project's prior known dead end); the
   research report found a WORKING HTML mirror of the full text on the same
   platform's article route -- captured here.

WHY THIS IS USER-RUN-ONLY
--------------------------
pravo.gov.ru (Russian Federal official legal-publication portal) and
npa.dnronline.su (DNR normative-acts platform) fall under the same
geoblocked-foreign-state-system rule as court_crawler.py / ownerless_lists.py
(CLAUDE.md). Same posture as scripts/197, which the user ran successfully
from their own machine -- run this the same way. If a domain turns out
directly reachable, no harm; it exits the same way. (The HRW/East SOS
Western-NGO captures for Q5 are in scripts/206, which Claude ran directly --
those are NOT geoblocked.)

Run:
    PYTHONPATH=src python scripts/207_crawl_federal_property_instruments.py
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
        "url": "http://publication.pravo.gov.ru/document/0001202301030011",
        "source_type": "federal_mortgage_decree_2565",
        "title": "Постановление Правительства РФ от 31.12.2022 № 2565 (2% mortgage founding decree)",
        "description": (
            "FOUNDING instrument of the 2% subsidized-mortgage program for "
            "DNR/LNR/Zaporizhzhia/Kherson (ДОМ.РФ subsidy rules); amended by "
            "№2166 (scripts/197). Closes the Q1 launch-decree gap. "
            "progress_report_2026-06.md §5 item 11."
        ),
    },
    {
        "url": "http://publication.pravo.gov.ru/document/0001202212300029",
        "source_type": "federal_property_demarcation_2501",
        "title": "Постановление Правительства РФ от 29.12.2022 № 2501 (property demarcation)",
        "description": (
            "Federal/municipal property-demarcation framework for the "
            "occupied regions; legal basis cited in Закон №269-РЗ for routing "
            "housing (Приложение №2 item 9) into federal ownership. Q2. "
            "Read Приложение №2 + Arts 6¹/7/19 after capture."
        ),
    },
    {
        "url": "http://publication.pravo.gov.ru/document/0001202312290053",
        "source_type": "federal_reconstruction_program_2255",
        "title": "Постановление Правительства РФ от 22.12.2023 № 2255 (reconstruction госпрограмма)",
        "description": (
            "Federal reconstruction program; Приложение №4 sets the per-m² "
            "housing-loss compensation rate that Закон №269-РЗ Ст.7 п.3 "
            "defers to. Q3. The 51,500 ₽/m² figure is DEDUCED from an "
            "amendment draft, NOT yet read from the primary annex -- confirm "
            "against the captured Приложение №4 before treating as fact."
        ),
    },
    {
        "url": "http://npa.dnronline.su/2022-11-15/"
               "rasporyazhenie-glavy-administratsii-goroda-mariupolya-"
               "donetskoj-narodnoj-respubliki-61-ot-03-11-2022-g.html",
        "source_type": "mariupol_lease_rulebook_61",
        "title": "Распоряжение главы администрации г. Мариуполя от 03.11.2022 № 61 (lease rulebook)",
        "description": (
            "Municipal property-lease rulebook (Временный порядок передачи в "
            "аренду + Временная методика расчёта арендной платы), reg. №5351 "
            "(14.11.2022). Working HTML mirror found by Q8 research -- the "
            "PDF route on this platform was previously dead-linked. "
            "progress_report_2026-06.md §5 item 12."
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
            content_type=r.headers.get("Content-Type", "application/octet-stream"),
            http_status=r.status_code, con=con,
        )
        log.info("  status=%d sha=%s bytes=%d", r.status_code, sha[:16], len(r.content))

    log.info("Done. Next: for the pravo.gov.ru postановления, the View page "
              "often links a signed PDF -- follow + capture it, then OCR "
              "(scripts/06a pattern, ocrmypdf in .venv not .venv312). Priority "
              "read: Приложение №4 of №2255 to CONFIRM-or-correct the deduced "
              "51,500 ₽/m² rate before it enters any doc as fact.")


if __name__ == "__main__":
    main()
