#!/usr/bin/env python3
"""Capture the Администрация городского округа Мариуполь (AGO) official
compensation-housing DISTRIBUTION lists + housing queue -- the primary-source
counterpart to the crowd-sourced reallocation ledger (scripts/391). Surfaced
by the 2026-07-21 monitored-channel scan; located on
mariupol.gosuslugi.ru/dlya-zhiteley/poleznye-materialy/kvartirnaya-ochered/
(recon 2026-07-21). See memory/monitored_scan_findings_2026-07-21.md.

These are the official record of WHICH municipal apartments were distributed
as compensation and the standing quartira queue -- the government's own
version of the "перечень адресов" residents cite. Forensic capture into the
raw store (SHA-256 + .meta.json sidecar), per CLAUDE.md.

GEOBLOCK / RUN LOCATION: mariupol.gosuslugi.ru is Russia-hosted. Per CLAUDE.md
this bulk artifact capture goes through the USER's Russia-routed VPN
connection, not Claude's environment:

    PYTHONPATH=src .venv312/bin/python scripts/392_capture_compensation_distribution_lists.py

Idempotent: forensics.capture_source() is keyed by SHA-256, so re-running skips
bytes already stored. Re-run periodically -- the administration replaces the
"Распределение жилья от <date>" file as each distribution stage completes, so
new dates should be added to TARGETS below as they appear on the queue page.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

BASE = "https://mariupol.gosuslugi.ru"

# (relative_url, source_type, human label). Distribution lists are the
# high-value ones (which flats went out as compensation); the queue snapshot
# is the demand side.
TARGETS = [
    ("/netcat_files/602/8217/Raspredelenie_zhil_ya_ot_21.07.2026.pdf",
     "ago_mariupol_housing_distribution_pdf", "Распределение жилья от 21.07.2026 (PDF)"),
    ("/netcat_files/602/8217/Raspredelenie_zhil_ya_ot_21.07.2026.xlsx",
     "ago_mariupol_housing_distribution_xlsx", "Распределение жилья от 21.07.2026 (XLSX)"),
    ("/netcat_files/602/8696/Raspredelenie_zhil_ya_ot_27.05.2026.pdf",
     "ago_mariupol_housing_distribution_pdf", "Распределение жилья от 27.05.2026 (PDF, stage 1)"),
    ("/netcat_files/multifile/252/2046/Raspredelenie_zhil_ya_ot_27.05.2026.xlsx",
     "ago_mariupol_housing_distribution_xlsx", "Распределение жилья от 27.05.2026 (XLSX, stage 1)"),
    ("/netcat_files/602/7469/Ochered_Sayt_27.05.2026.xlsx",
     "ago_mariupol_housing_queue_xlsx", "Квартирная очередь 27.05.2026 (XLSX)"),
    ("/netcat_files/602/7469/Ochered_Sayt_27.05.2026.pdf",
     "ago_mariupol_housing_queue_pdf", "Квартирная очередь 27.05.2026 (PDF)"),
]


def fetch(url: str) -> tuple[bytes | None, str, int]:
    try:
        resp = requests.get(url, headers={"User-Agent": config.USER_AGENT},
                            timeout=90, allow_redirects=True)
        ct = resp.headers.get("Content-Type", "application/octet-stream")
        return (resp.content if resp.ok else None), ct, resp.status_code
    except requests.exceptions.RequestException as e:
        log.error("fetch failed for %s: %s", url, e)
        return None, "", 0


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    con = forensics.open_state()
    ok = 0
    for rel, source_type, label in TARGETS:
        url = BASE + rel
        blob, ct, status = fetch(url)
        if not blob:
            log.warning("SKIP (status=%s) %s", status, url)
            continue
        sha = forensics.capture_source(
            blob, url=url, source_type=source_type, title=label,
            description=(f"AGO Mariupol official compensation-housing record: {label}. "
                         f"Captured for MUP-CS reallocation evidence "
                         f"(memory/monitored_scan_findings_2026-07-21.md)."),
            content_type=ct, http_status=status, con=con,
        )
        ok += 1
        log.info("captured %s (%d bytes) sha=%s", label, len(blob), sha[:12])
    log.info("done — %d/%d targets captured", ok, len(TARGETS))
    print(f"captured {ok}/{len(TARGETS)} AGO Mariupol distribution/queue files")


if __name__ == "__main__":
    main()
