"""Stage 1g: capture the DNR Ministry of Construction Unified Demolition Register.

Claude must never run this — see CLAUDE.md. Run from VPS for provenance,
though these files are NOT geoblocked (accessible without Russian routing).

WHY THIS EXISTS
---------------
The Министерство строительства, архитектуры и ЖКХ ДНР publishes an open-data
dataset titled «Единый реестр зданий и сооружений, подлежащих сносу» at:
  https://minstroy-dpr.gosuslugi.ru/opendata/7710474375-minstroydpropendatasnos-
    nabor-dannyh-1-obrazecz/

This is a four-column semicolon-delimited CSV:
  № п/п | Номер и дата распоряжения | Адрес объекта |
  Наименование административно-территориальной единицы ДНР

As of March 2026, the current version (reestr-snosa_16_03_2026.csv) contains
637 rows across DNR territory; 525 are Mariupol buildings.

EVIDENTIARY VALUE
-----------------
1. GKO ДНР Распоряжение №56 (29.09.2022) — 177 Mariupol buildings confirmed here,
   including пр-т Нахимова, д. 82 (the Нахимова→Черноморский 1Б crosswalk case)
   and 12 пр-т Ленина buildings (rows 247–258) that are the candidate addresses
   for the ТСЖ «Троянда-М» building (case 2-259/2025 / 33-2575/2025 / 8Г-12687/2026).

2. The register lists ALL Mariupol demolition orders from GKO №26 (09.08.2022)
   through the occupation city administration's own orders (2022–2024).

3. It is a self-incriminating official publication by the occupation authority —
   not a leaked document. Its versioned history (original → 23.10.2025 → 16.03.2026)
   shows the systematic character of demolitions (ongoing additions).

4. The «Номер и дата распоряжения» column directly links each building to the
   legal act authorising its demolition — chain of command in one table.

CSV VERSIONS AVAILABLE
----------------------
  reestr-snosa-2.csv               — original (618 rows)
  reestr-snosa_17_07_2025.csv      — 17 Jul 2025 (404 as of 09.06.2026)
  reestr-snosa_23_10_2025.csv      — 23 Oct 2025 (621 unique addrs)
  reestr-snosa_01_11_2025.csv      — 01 Nov 2025 (404 as of 09.06.2026)
  reestr-snosa_16_03_2026.csv      — 16 Mar 2026 (637 rows) — CURRENT

The WordPress API at /api/wp/v2/opendata/12812 has dataset metadata.

ESTRUCTURA FILE
---------------
  struktura.csv — column schema definition (4 columns described above).

NOTE ON GEOBLOCKING
-------------------
Unlike the court portals, these files were accessible from a non-Russian IP
(09.06.2026 test). Capture from VPS anyway to maintain uniform provenance —
all evidence in the chain should have the same capture origin.
"""
from __future__ import annotations

import logging
import time

import requests
import urllib3

from .. import config, forensics

log = logging.getLogger(__name__)

if not config.SSL_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ORIGIN = "https://minstroy-dpr.gosuslugi.ru"
DATASET_URL = (
    f"{ORIGIN}/opendata/7710474375-minstroydpropendatasnos-nabor-dannyh-1-obrazecz/"
)

# All known CSV files with their publication dates and sizes.
# Tuple: (url, source_type, title, description, known_rows)
KNOWN_CSV_FILES: list[tuple[str, str, str, str, int]] = [
    (
        f"{ORIGIN}/app/uploads/2024/09/eb14dd_reestr-snosa_16_03_2026.csv",
        "minstroy_demolition_register_csv",
        "Единый реестр зданий и сооружений, подлежащих сносу — 16.03.2026",
        "Current version (as of Mar 2026). 637 rows; 525 Mariupol buildings. "
        "Includes all GKO ДНР Распоряжения №26–56 (Aug–Sep 2022) plus later "
        "occupation city administration orders. "
        "Распоряжение №56 (29.09.2022): 177 Mariupol buildings including "
        "пр-т Нахимова д.82 (Нахимова→Черноморский 1Б crosswalk) and "
        "12 пр-т Ленина buildings (rows 247–258, Жовтневый district) "
        "which are the candidate addresses for ТСЖ «Троянда-М» case chain.",
        637,
    ),
    (
        f"{ORIGIN}/app/uploads/2024/09/f13682_reestr-snosa_23_10_2025.csv",
        "minstroy_demolition_register_csv",
        "Единый реестр зданий и сооружений, подлежащих сносу — 23.10.2025",
        "October 2025 version. 621 unique addresses. "
        "For diff against current to track new demolition orders.",
        621,
    ),
    (
        f"{ORIGIN}/app/uploads/2024/09/reestr-snosa-2.csv",
        "minstroy_demolition_register_csv",
        "Единый реестр зданий и сооружений, подлежащих сносу — оригинал (2024-09)",
        "Original publication (Sept 2024). 618 rows. Baseline for diff analysis. "
        "Delta vs current: +19 rows (all non-Mariupol: Докучаевск + Донецк).",
        618,
    ),
    (
        f"{ORIGIN}/app/uploads/2024/09/75b167_struktura.csv",
        "minstroy_demolition_register_schema",
        "Структура реестра зданий и сооружений, подлежащих сносу",
        "Column schema definition for the demolition register CSV. "
        "4 columns: № п/п, Номер и дата распоряжения, Адрес объекта, "
        "Наименование административно-территориальной единицы ДНР.",
        4,
    ),
]

# Also capture the dataset landing page and WP API metadata.
METADATA_URLS: list[tuple[str, str, str]] = [
    (
        DATASET_URL,
        "minstroy_demolition_register_page",
        "Страница набора данных «Единый реестр зданий и сооружений, подлежащих сносу»",
    ),
    (
        f"{ORIGIN}/api/wp/v2/opendata/12812",
        "minstroy_demolition_register_api",
        "WordPress REST API metadata for the demolition register dataset (post ID 12812)",
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


def capture_metadata(s: requests.Session, con) -> None:
    """Capture the dataset landing page and WordPress API metadata."""
    for url, source_type, title in METADATA_URLS:
        key = f"minstroy_register::{url}"
        if forensics.is_done(con, key):
            log.debug("skip (already done): %s", title)
            continue
        r = _get(s, url)
        polite_sleep()
        if r is None or r.status_code != 200:
            log.warning("metadata not fetched (HTTP %s): %s",
                        r.status_code if r else "N/A", url)
            continue
        forensics.capture_source(
            r.content, url=url,
            source_type=source_type,
            title=title,
            description=title,
            content_type=r.headers.get("Content-Type", "text/html"),
            http_status=r.status_code, con=con,
        )
        forensics.mark_done(con, key)
        log.info("captured metadata: %s", title[:80])


def capture_csv_files(s: requests.Session, con) -> None:
    """Capture all known CSV versions of the demolition register."""
    for url, source_type, title, description, expected_rows in KNOWN_CSV_FILES:
        key = f"minstroy_register::{url}"
        if forensics.is_done(con, key):
            log.debug("skip (already done): %s", title)
            continue
        r = _get(s, url)
        polite_sleep()
        if r is None or r.status_code not in (200, 404):
            log.warning("CSV not fetched (HTTP %s): %s",
                        r.status_code if r else "N/A", url)
            continue
        if r.status_code == 404:
            log.info("CSV not available (404 — removed from server): %s", url)
            # Still capture the 404 response to document the missing version.
            forensics.capture_source(
                r.content, url=url,
                source_type=source_type,
                title=f"{title} [404 — not available]",
                description=f"File removed from server. {description}",
                content_type=r.headers.get("Content-Type", "text/html"),
                http_status=r.status_code, con=con,
            )
            forensics.mark_done(con, key)
            continue
        forensics.capture_source(
            r.content, url=url,
            source_type=source_type,
            title=title,
            description=description,
            content_type=r.headers.get("Content-Type", "text/csv; charset=utf-8"),
            http_status=r.status_code, con=con,
        )
        forensics.mark_done(con, key)
        log.info("captured CSV (%d bytes, expected ~%d rows): %s",
                 len(r.content), expected_rows, title[:80])


def run() -> None:
    con = forensics.open_state()
    s = make_session()
    try:
        capture_metadata(s, con)
        capture_csv_files(s, con)
    except KeyboardInterrupt:
        log.warning("interrupted — state saved, safe to rerun.")

    n = con.execute(
        "SELECT COUNT(*) FROM source_document "
        "WHERE source_type LIKE 'minstroy_demolition_register%'"
    ).fetchone()[0]
    log.info("done; %d MinStroy register artifacts in store", n)
