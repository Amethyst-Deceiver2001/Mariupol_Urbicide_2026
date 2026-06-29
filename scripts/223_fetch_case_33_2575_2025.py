#!/usr/bin/env python3
"""Capture DNR "Supreme Court" appellate case 33-2575/2025 (13.11.2025,
reporting judge N.N. Guridova / Гуридова Н.Н.) -- the Troianda-M /
Metallurgov 47 collective-claim appeal (60 residents, lost; see
docs/exhibits/case-study-troianda-metallurgov.html), also cited as a
[CITED]-not-[CAPTURED] source for DNR State-Committee Directive No. 56
in docs/exhibits/case-study-III-stroiteley.html / -ru.html's source
catalogue.

URL supplied directly by the user (2026-06-30):
    https://vs--dnr.sudrf.ru/modules.php?name=sud_delo&srv_num=1&name_op=doc&number=2122362&delo_id=5&new=5&text_number=1

vs--dnr.sudrf.ru is the geoblocked DNR "Supreme Court" portal (see
src/mariupol_seizures/crawl/dnr_supreme_court.py) -- per project policy
Claude does not execute crawls against geoblocked foreign-state systems.
This script is generated for the USER to run from their own
Russia-routed VPS; it is NOT run by Claude.

Run:
    PYTHONPATH=src python scripts/223_fetch_case_33_2575_2025.py
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

URL = (
    "https://vs--dnr.sudrf.ru/modules.php?name=sud_delo&srv_num=1"
    "&name_op=doc&number=2122362&delo_id=5&new=5&text_number=1"
)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    con = forensics.open_state()
    s = requests.Session()
    s.headers.update({"User-Agent": config.USER_AGENT, "Accept-Language": "ru,en;q=0.8"})
    if config.PROXY:
        s.proxies.update({"http": config.PROXY, "https": config.PROXY})

    log.info("Fetching %s", URL)
    r = s.get(URL, timeout=config.TIMEOUT, verify=config.SSL_VERIFY, allow_redirects=True)
    if r.status_code != 200:
        log.warning("HTTP %d for %s -- captured anyway for the record", r.status_code, URL)
    sha = forensics.capture_source(
        r.content, url=URL, source_type="vs_dnr_case_33_2575_2025",
        title="DNR «Supreme Court» case 33-2575/2025 (13.11.2025) -- Troianda-M / Metallurgov 47 appeal",
        description=(
            "Appellate ruling upholding denial of the 60-resident collective claim "
            "over the Metallurgov 47 / Troianda-M demolition. Also cited in Case "
            "Study III's source catalogue re: Directive No. 56. URL supplied "
            "directly by the user."
        ),
        content_type=r.headers.get("Content-Type", "text/html"),
        http_status=r.status_code, con=con,
    )
    log.info("status=%d sha=%s bytes=%d", r.status_code, sha[:16], len(r.content))
    print(f"captured: sha={sha} bytes={len(r.content)}")


if __name__ == "__main__":
    main()
