#!/usr/bin/env python3
"""Capture a fresh snapshot of the mariupoldestruction.com citywide victims
TSV (see memory/mariupoldestruction_victims_tsv.md -- 4,515 rows as of the
2026-07-03 capture, sha256 3b10d33f...). Re-captured 2026-07-21 while
sweeping the Lomizova/50-let-Oktyabrya(Meotidy)/Azovstalskaya/Komsomolsky-
Morskoy quarter (Levoberezhny) for a possible new "demolish-and-abandon"
case-study candidate -- this TSV cross-reference surfaced ~60 additional
named deaths + dozens of "без вести" (missing) entries clustered on this
one quarter's streets, on top of what the mariupolRIP corpus sweep alone
found.

Public, unauthenticated Google Sheets TSV export -- same source already
captured once for the Metallurgov 47 case study (scripts/239 precedent);
Claude runs this directly per that precedent (single well-identified URL,
not a systematic/bulk crawl).
"""
import logging
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

TSV_URL = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vRClYf-zQAtTququ0nEPfQBMO6EHaTSltS-d5caPXVbjc0fElqGuDKyr9P1gBCByw/"
    "pub?output=tsv"
)


def fetch(url: str) -> tuple[bytes, str, int]:
    resp = requests.get(
        url, headers={"User-Agent": config.USER_AGENT},
        timeout=config.TIMEOUT, allow_redirects=True,
    )
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream"), resp.status_code


def main() -> None:
    con = forensics.open_state()
    content, ctype, status = fetch(TSV_URL)
    sha = forensics.capture_source(
        content, url=TSV_URL, source_type="victims_tsv_snapshot",
        title="Mariupol Destruction and Victims Map -- citywide victims TSV (2026-07-21 snapshot)",
        description=(
            "Public Google Sheets TSV export from mariupoldestruction.com, "
            "re-captured while sweeping the Lomizova/50 let Oktyabrya "
            "(Meotidy)/Azovstalskaya/Komsomolsky-Morskoy quarter for a "
            "possible new case-study candidate. Superset of the "
            "2026-07-03 capture (sha256 3b10d33f56cd47496a6f9a095ff487c"
            "818418f3acc724e61901f9cd009149ff5)."
        ),
        content_type=ctype, http_status=status, con=con,
    )
    con.close()
    log.info("captured -> sha=%s status=%s bytes=%d", sha, status, len(content))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
