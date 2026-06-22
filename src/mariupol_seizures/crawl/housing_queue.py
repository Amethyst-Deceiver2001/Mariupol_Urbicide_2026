"""Stage 1h: capture Mariupol occupation housing queue and distribution lists.

Claude must never run this — see CLAUDE.md.

WHY THIS EXISTS
---------------
The occupation administration publishes two living documents at:
  mariupol-r897.gosweb.gosuslugi.ru/dlya-zhiteley/poleznye-materialy/kvartirnaya-ochered/

1. «Квартирная очередь» (queue list) — XLSX + PDF: the ranked list of
   displaced persons waiting for replacement housing.  This is the occupation's
   own acknowledgment that specific people lost homes.  Contains victim PII
   (names, identifiers) → routed to the secured owner table, never committed.

2. «Распределение жилья» (distribution list) — XLSX + PDF: who was allocated
   what replacement unit.  This is the OUTPUT of the demolish→rebuild pipeline:
   new units from developers (РКС-Девелопмент, ЭВОЛДОМ-5, etc.) being assigned
   to displaced persons.  Parsing it can close the old-address → new-address
   chain for buildings like ТСЖ «Троянда-М».

Both files are LIVING DOCUMENTS: the page overwrites them on each update.
Each run captures a DATED SNAPSHOT.  The sequence of snapshots IS the evidence
(queue length, allocation rate, rate of disappearance = transfer complete).

Not geoblocked as of 2026-06-09 — accessible without Russian routing.
Still run via VPS for uniform provenance (matching court captures).

Re-run periodically (weekly minimum; daily in July 2026 ahead of the
01.07.2026 re-registration deadline when queue movement will accelerate).
"""
from __future__ import annotations

import logging
import time
from urllib.parse import urljoin

import requests
import urllib3

from .. import config, forensics

log = logging.getLogger(__name__)

if not config.SSL_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ORIGIN = "https://mariupol-r897.gosweb.gosuslugi.ru"

SECTION_PATH = "/dlya-zhiteley/poleznye-materialy/kvartirnaya-ochered/"

# Known file paths.  These change with each update (filename encodes the date).
# The crawler discovers current filenames by scraping the landing page, so
# adding new dated versions here is not required — but the list serves as a
# fallback and documents what has been observed.
KNOWN_FILES: dict[str, dict] = {
    # key → {rel_path, source_type, description}
    "queue_xlsx_20260527": {
        "path": "/netcat_files/602/7469/Ochered_Sayt_27.05.2026.xlsx",
        "source_type": "housing_queue_list",
        "description": "Квартирная очередь — 27.05.2026. "
                       "PRIVACY: contains displaced-person PII. "
                       "Route to secured owner table; never commit.",
    },
    "queue_pdf_20260527": {
        "path": "/netcat_files/602/7469/Ochered_Sayt_27.05.2026.pdf",
        "source_type": "housing_queue_list",
        "description": "Квартирная очередь — 27.05.2026 [PDF]. "
                       "PRIVACY: contains displaced-person PII.",
    },
    "distribution_pdf_20260527": {
        "path": "/netcat_files/602/8217/Raspredelenie_zhil_ya_ot_27.05.2026.pdf",
        "source_type": "housing_distribution_list",
        "description": "Распределение жилья — 27.05.2026. "
                       "Maps displaced persons to allocated replacement units. "
                       "Closes old-address→new-address chain for demolish→rebuild cases.",
    },
    "distribution_xlsx_20260527": {
        "path": "/netcat_files/602/8217/Raspredelenie_zhil_ya_ot_27.05.2026.xlsx",
        "source_type": "housing_distribution_list",
        "description": "Распределение жилья — 27.05.2026 [XLSX]. "
                       "Maps displaced persons to allocated replacement units.",
    },
}

_XLSX_CT = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_PDF_CT = "application/pdf"


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": config.USER_AGENT, "Accept-Language": "ru,en;q=0.8"})
    if config.PROXY:
        s.proxies.update({"http": config.PROXY, "https": config.PROXY})
    return s


def _polite_sleep() -> None:
    time.sleep(2.0)


def _get(s: requests.Session, url: str):
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            r = s.get(url, timeout=config.TIMEOUT, verify=config.SSL_VERIFY)
            if r.status_code == 404:
                log.warning("404 %s", url)
                return r
            return r
        except requests.RequestException as e:
            wait = min(60, 2 ** attempt)
            log.warning("GET %s failed (attempt %d/%d): %s; wait %ds",
                        url, attempt, config.MAX_RETRIES, e, wait)
            time.sleep(wait)
    log.error("giving up on %s", url)
    return None


def _discover_files(html: str) -> list[dict]:
    """Parse landing page HTML to find current queue/distribution file links.

    Returns list of dicts with keys: path, source_type, description.
    Falls back gracefully to KNOWN_FILES if scraping finds nothing new.
    Detects both XLSX and PDF variants; classifies by filename keyword.
    """
    from bs4 import BeautifulSoup
    import re

    soup = BeautifulSoup(html, "lxml")
    discovered = []
    seen_paths: set[str] = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/netcat_files/" not in href:
            continue
        path = href if href.startswith("/") else "/" + href
        if path in seen_paths:
            continue
        seen_paths.add(path)

        lower = path.lower()
        if lower.endswith(".xlsx"):
            ext_ct = _XLSX_CT
        elif lower.endswith(".pdf"):
            ext_ct = _PDF_CT
        else:
            continue

        # Classify by filename
        fname = path.rsplit("/", 1)[-1].lower()
        if re.search(r"ochered|очередь|queue", fname, re.I):
            source_type = "housing_queue_list"
            label = "Квартирная очередь"
            privacy = (" PRIVACY: contains displaced-person PII. "
                       "Route to secured owner table; never commit.")
        elif re.search(r"raspredel|распредел|distrib", fname, re.I):
            source_type = "housing_distribution_list"
            label = "Распределение жилья"
            privacy = (" Maps displaced persons to allocated replacement units. "
                       "Closes old-address→new-address chain.")
        else:
            source_type = "housing_queue_unknown"
            label = fname
            privacy = ""

        discovered.append({
            "path": path,
            "source_type": source_type,
            "content_type": ext_ct,
            "description": f"{label} — discovered from landing page.{privacy}",
        })
        log.info("discovered file: %s (%s)", path, source_type)

    return discovered


def run() -> None:
    con = forensics.open_state()
    s = make_session()

    landing_url = urljoin(ORIGIN, SECTION_PATH)

    # 1. Capture landing page.
    log.info("capturing housing queue landing: %s", landing_url)
    r = _get(s, landing_url)
    _polite_sleep()
    if r is None or r.status_code != 200:
        log.error("landing page unreachable — aborting")
        return

    forensics.capture_source(
        r.content, url=landing_url,
        source_type="housing_queue_landing",
        title="Mariupol housing queue section — квартирная очередь",
        description="Landing page listing current queue list and distribution list. "
                    "Contains links to XLSX/PDF snapshots of the housing queue. "
                    "Living document: capture on every run.",
        content_type=r.headers.get("Content-Type", "text/html"),
        http_status=r.status_code, con=con,
    )

    # 2. Discover current file links from the page HTML.
    discovered = _discover_files(r.text)
    if not discovered:
        log.warning("no files discovered from landing HTML — falling back to KNOWN_FILES")
        discovered = [
            {
                "path": v["path"],
                "source_type": v["source_type"],
                "content_type": (
                    _XLSX_CT if v["path"].endswith(".xlsx") else _PDF_CT
                ),
                "description": v["description"],
            }
            for v in KNOWN_FILES.values()
        ]

    # 3. Capture each file.  Do NOT skip if already done — living documents
    #    update in place; SHA-256 deduplication in forensics.capture_source
    #    handles the "no change" case cheaply without re-storing identical bytes.
    for f in discovered:
        url = urljoin(ORIGIN, f["path"])
        log.info("fetching: %s [%s]", url, f["source_type"])
        fr = _get(s, url)
        _polite_sleep()
        if fr is None or fr.status_code != 200:
            log.warning("file not fetched (%s): %s",
                        fr.status_code if fr else "timeout", url)
            # Capture the 404 response — documents the file being removed.
            if fr is not None:
                forensics.capture_source(
                    fr.content, url=url,
                    source_type=f["source_type"] + "_404",
                    title=f"404 — {f['path'].rsplit('/', 1)[-1]}",
                    description="File returned 404 — version no longer available. "
                                "Timestamp documents when it was removed.",
                    content_type="text/html",
                    http_status=fr.status_code, con=con,
                )
            continue

        sha = forensics.capture_source(
            fr.content, url=url,
            source_type=f["source_type"],
            title=f["path"].rsplit("/", 1)[-1],
            description=f["description"],
            content_type=fr.headers.get("Content-Type", f["content_type"]),
            http_status=fr.status_code, con=con,
        )
        log.info("captured %s: sha256=%s… (%d bytes)",
                 f["source_type"], sha[:16], len(fr.content))

    n_queue = con.execute(
        "SELECT COUNT(*) FROM source_document "
        "WHERE source_type LIKE 'housing_queue%'"
    ).fetchone()[0]
    n_dist = con.execute(
        "SELECT COUNT(*) FROM source_document "
        "WHERE source_type LIKE 'housing_distribution%'"
    ).fetchone()[0]
    log.info("done — %d housing_queue artifacts, %d housing_distribution artifacts in store",
             n_queue, n_dist)
