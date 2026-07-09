#!/usr/bin/env python3
"""Capture the mariupol.gosuslugi.ru news article announcing "phase 2" of the
housing inventory (09.01.2025) plus its attached 170/171-building address
list, both user-supplied (2026-07-08).

The article states this phase targets apartment owners in 170 multi-storey
buildings still under repair/restoration ("ремонтно-восстановительные
работы"), gives owners until 01.04.2025 to personally register title in
Rosreestr via MFC, and states unregistered units get added to the ownerless
(бесхозяйный) list -- i.e. this is the registration-deadline enforcement
mechanism, downstream of the door-to-door inventory (Распоряжение №619)
already logged in docs/legal_mechanisms_review.md. Distinct from №619: that
decree covers the initial citywide survey (Oct 2023); this "phase 2" article
is specifically the restoration-building registration deadline (Jan-Apr
2025), targeting a much narrower, named list of buildings.

The attached MKD_Invintarizatsiya.xlsx (171 addresses, 4 districts: ЖРА 72,
ОРА 68, ИРА 16, ПРА 14) includes проспект Ленина (Мира) д.104/106/108/110 --
all four buildings in the existing Ленина 104/106/108/110
restoration-without-restitution case study
(docs/case_studies/lenina_104_106_108_110_restoration_without_restitution.md)
-- direct confirmation those buildings were formally on a citywide
inventory/registration-deadline list, not just individually identified via
chat-corpus research.

Same TLS trust-store situation as scripts/269/273 (mariupol.gosuslugi.ru):
verification disabled below since forensic integrity comes from the recorded
SHA-256, not TLS trust.
"""
import logging
import sys
import time
from pathlib import Path

import requests
import urllib3

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TARGETS = [
    (
        "https://mariupol.gosuslugi.ru/dlya-zhiteley/novosti-i-reportazhi/novosti_284.html",
        "mariupol.gosuslugi.ru novosti_284 -- \"В Мариуполе стартовал второй "
        "этап инвентаризации\" (09.01.2025)",
        "User-supplied (2026-07-08). Announces 'phase 2' of the housing "
        "inventory: owners in 170 restoration-in-progress buildings must "
        "register title via MFC/Rosreestr by 01.04.2025 or the unit is "
        "added to the ownerless list.",
        "mariupol_gosuslugi_news",
    ),
    (
        "https://mariupol.gosuslugi.ru/netcat_files/userfiles/MKD_Invintarizatsiya.xlsx",
        "MKD_Invintarizatsiya.xlsx -- 171-address building list attached to "
        "novosti_284 (phase-2 inventory/registration-deadline targets)",
        "User-supplied (2026-07-08), linked from novosti_284.html "
        "(\"Перечень адресов доступен по ссылке\"). 171 addresses across 4 "
        "districts (ЖРА 72, ОРА 68, ИРА 16, ПРА 14). Includes проспект "
        "Ленина (Мира) д.104/106/108/110 -- all four buildings in the "
        "existing Ленина 104/106/108/110 case study.",
        "mariupol_gosuslugi_attachment_xlsx",
    ),
]


def fetch(url: str) -> tuple[bytes, str, int]:
    for attempt in range(config.MAX_RETRIES):
        try:
            resp = requests.get(
                url, headers={"User-Agent": config.USER_AGENT},
                timeout=config.TIMEOUT, allow_redirects=True, verify=False,
            )
            resp.raise_for_status()
            return resp.content, resp.headers.get("Content-Type", "application/octet-stream"), resp.status_code
        except requests.exceptions.RequestException as exc:
            if attempt == config.MAX_RETRIES - 1:
                raise
            log.warning("transient error fetching %s (attempt %d/%d): %s -- retrying",
                        url, attempt + 1, config.MAX_RETRIES, exc)
            time.sleep(2.0 * (attempt + 1))


def main() -> None:
    con = forensics.open_state()

    for url, title, description, source_type in TARGETS:
        content, ctype, status = fetch(url)
        sha = forensics.capture_source(
            content, url=url, source_type=source_type,
            title=title, description=description,
            content_type=ctype, http_status=status, con=con,
        )
        log.info("captured %s -> sha=%s status=%s (%d bytes)", title, sha[:12], status, len(content))
        time.sleep(1.0)

    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
