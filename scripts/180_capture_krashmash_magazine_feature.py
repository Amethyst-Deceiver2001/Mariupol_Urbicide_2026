#!/usr/bin/env python3
"""Capture a trade-press magazine feature, hosted on KrashMash's own site,
that independently corroborates the company's Mariupol demolition contract:
an on-the-record interview with general director Viktor Kazakov stating
KrashMash began work in Mariupol in October 2022, names the equipment and
team scale (35 specialists, 25 units, a unique 60-metre-boom Caterpillar
390DLME), and the standard 5-12 day demolition timeline -- consistent with,
though not itself naming, the pr. Metallurgov 47 case study's timeline.

Direct HTTPS fetch of a normal Russian corporate site, no geoblock/VPS
needed (unlike the court-portal crawlers) -- safe to run directly.

Usage:
    .venv312/bin/python scripts/180_capture_krashmash_magazine_feature.py
"""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import requests  # noqa: E402

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)


def main() -> None:
    con = forensics.open_state()
    url = ("https://crushmash.com/upload/iblock/9cf/"
           "9cf839c4a1af543ed17d0c69980a5f90.pdf")
    try:
        r = requests.get(url, headers={"User-Agent": config.USER_AGENT}, timeout=30)
    except requests.RequestException as e:
        log.error("fetch failed: %s", e)
        return
    if r.status_code != 200:
        log.warning("HTTP %s for %s", r.status_code, url)
        return
    sha = forensics.capture_source(
        r.content,
        url=url,
        source_type="press_article",
        title="Trade-press feature (hosted on crushmash.com): "
              "«Mariupol: destruction for restoration», interview "
              "with KrashMash general director Viktor Kazakov",
        description="One-page magazine spread (Adobe InDesign PDF, created "
                     "10.02.2023), Russian construction-trade press. Interview "
                     "with KrashMash («KrashMash» group) general director "
                     "Viktor Aleksandrovich Kazakov (Виктор "
                     "Александрович "
                     "Казаков). On the record: work in "
                     "Mariupol began October 2022; panel apartment buildings up to 40m "
                     "tall demolished after MChS/Defense Ministry inspection and "
                     "resettlement; team of 35 KrashMash specialists and 25 units of "
                     "specialized equipment on site, incl. the only 60-metre-boom "
                     "demolition excavator in Russia (Caterpillar 390DLME); typical "
                     "demolition takes 5-12 days; company uses only its own equipment "
                     "fleet (never rented) and can run up to 50 projects nationwide "
                     "simultaneously. No individual address named on this page -- "
                     "corroborates KrashMash's scale and operating method in Mariupol "
                     "generally, consistent with (not itself proof of) the Metallurgov "
                     "47 demolition.",
        content_type=r.headers.get("Content-Type", "application/pdf"),
        http_status=r.status_code,
        con=con,
    )
    log.info("captured crushmash.com magazine feature -> sha=%s", sha[:12])
    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
