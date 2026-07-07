#!/usr/bin/env python3
"""Capture the Mariupol occupation "housing queue" (жилищная очередь) explainer
page (user-supplied 2026-07-07): the published terms for compensational-housing
distribution to residents of demolished multi-apartment buildings, including
Nakhimova 82.

Cited in the Nakhimova 82 exhibit's "arithmetic of dispossession" section for
two claims, both confirmed on read-through of the captured text: (1) a unit
is assigned to the resident unilaterally with no choice of address -- accept
or refuse only, refusal re-queues for another unilateral assignment, a
second refusal forfeits in-kind housing entirely; (2) required documents
include "original Russian Federation citizen passports of all owners" --
i.e. compensation eligibility is conditioned on Russian citizenship.

Not geoblocked -- ran successfully from the user's own machine (2026-07-07).
The initial run failed with SSLCertVerificationError: the site's TLS chain
roots at a Russian state CA not present in standard OS/browser trust stores,
which is a trust-store gap, not a network block. Verification is disabled
below for this one capture since forensic integrity here comes from the
SHA-256 recorded by forensics.capture_source(), not from TLS trust.
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

URL = "https://mariupol.gosuslugi.ru/dlya-zhiteley/poleznye-materialy/kvartirnaya-ochered/"

# mariupol.gosuslugi.ru's TLS chain roots at a Russian state CA
# (Минцифры/"Russian Trusted Root CA") not present in standard OS/browser
# trust stores -- this is a trust-store gap, not a sign of tampering.
# Forensic integrity here comes from the SHA-256 recorded by
# forensics.capture_source(), not from TLS trust, so verification is
# disabled for this one capture rather than pinning a CA bundle.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def fetch(url: str) -> tuple[bytes, str, int]:
    for attempt in range(config.MAX_RETRIES):
        try:
            resp = requests.get(
                url, headers={"User-Agent": config.USER_AGENT},
                timeout=config.TIMEOUT, allow_redirects=True, verify=False,
            )
            resp.raise_for_status()
            return resp.content, resp.headers.get("Content-Type", "text/html"), resp.status_code
        except requests.exceptions.RequestException as exc:
            if attempt == config.MAX_RETRIES - 1:
                raise
            log.warning("transient error fetching %s (attempt %d/%d): %s -- retrying",
                        url, attempt + 1, config.MAX_RETRIES, exc)
            time.sleep(2.0 * (attempt + 1))


def main() -> None:
    con = forensics.open_state()

    content, ctype, status = fetch(URL)
    sha = forensics.capture_source(
        content, url=URL, source_type="gosuslugi_housing_queue_page",
        title="mariupol.gosuslugi.ru -- housing-queue (kvartirnaya ochered) explainer",
        description=(
            "Official occupation-administration explainer of the "
            "compensational-housing queue terms for residents of demolished "
            "multi-apartment buildings. Cited in the Nakhimova 82 exhibit's "
            "arithmetic section: the page states no right to choose a "
            "district for replacement housing, and conditions compensation "
            "eligibility on Russian citizenship."
        ),
        content_type=ctype, http_status=status, con=con,
    )
    log.info("captured mariupol.gosuslugi.ru housing-queue page -> sha=%s status=%s",
             sha[:12], status)

    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
