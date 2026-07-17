#!/usr/bin/env python3
"""Capture the full "Mariupol Destruction and Victims Map" named-victims
sheet (user-supplied Google Sheets link, 2026-07-11), CSV export.

https://docs.google.com/spreadsheets/d/1J9g25xlQ2nHiwa-lpOcgbGMfhVvoeUvA/edit?gid=303215195

This is the same underlying source as the mariupoldestruction.com TSV export
already captured in scripts/239 (see memory/mariupoldestruction_victims_tsv.md
and docs/case_studies/death_sites_new_construction.md), but fetched directly
from the live workbook by its real spreadsheet ID + gid rather than the
published /pub?output=tsv mirror -- captured separately here so the two
snapshots each have their own hash and timestamp rather than conflating them.

Public/unauthenticated, non-geoblocked Google Sheets export -- same precedent
as scripts/159/160/161/162/239, Claude runs this directly, no VPS needed.
"""
import logging
import sys
import time

from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

SHEET_ID = "1J9g25xlQ2nHiwa-lpOcgbGMfhVvoeUvA"
GID = "303215195"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"
SHEET_EDIT_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit?gid={GID}"


def fetch(url: str) -> tuple[bytes, str, int]:
    for attempt in range(config.MAX_RETRIES):
        try:
            resp = requests.get(
                url, headers={"User-Agent": config.USER_AGENT},
                timeout=config.TIMEOUT, allow_redirects=True,
            )
            resp.raise_for_status()
            return resp.content, resp.headers.get("Content-Type", "text/csv"), resp.status_code
        except requests.exceptions.RequestException as exc:
            if attempt == config.MAX_RETRIES - 1:
                raise
            log.warning("transient error fetching %s (attempt %d/%d): %s -- retrying",
                        url, attempt + 1, config.MAX_RETRIES, exc)
            time.sleep(2.0 * (attempt + 1))


def main() -> None:
    con = forensics.open_state()

    content, ctype, status = fetch(SHEET_URL)
    sha = forensics.capture_source(
        content, url=SHEET_EDIT_URL, source_type="mariupoldestruction_victims_full_sheet",
        title="mariupoldestruction.com -- «Поименный список жертв» "
              "(List of victims by name), full Google Sheets CSV export "
              "(user-supplied link, sheet gid 303215195)",
        description=(
            "Citywide named-victims spreadsheet, same underlying source as "
            "scripts/239's mariupoldestruction_victims_tsv capture, fetched "
            "directly from the live workbook (real spreadsheet ID, not the "
            "/pub mirror) at user request 2026-07-11 to inspect for ad-hoc "
            "grave sites (место захоронения matching or co-located with "
            "место смерти / место проживания -- courtyard/yard burials)."
        ),
        content_type=ctype, http_status=status, con=con,
    )
    con.close()

    log.info("captured victims sheet -> sha=%s status=%s bytes=%d", sha, status, len(content))
    print(f"SHA_VICTIMS_FULL_SHEET = {sha!r}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
