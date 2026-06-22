#!/usr/bin/env python3
"""Capture two specific apartment-resale listing pages for пр. Ленина 108
(property_id 4421) -- demand-side [F] resale evidence for the case study.

Claude must never run this -- same policy as scripts/49 (CLAUDE.md):
dnr.red and dnr.domick.ru are Russian/DNR-administered marketplaces, the same
class of anti-bot/geoblocked site as Avito/CIAN/Domclick. Run from the
Russia-routed VPS (config.PROXY).

Capture-before-parse: each detail page is written verbatim to data/raw/,
SHA-256-keyed, with a .meta.json sidecar -- no field extraction happens here,
that's a follow-on parse step once the pages are actually in hand.

Usage (on the VPS):
    python3 scripts/158_capture_lenina108_resale_listings.py
"""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402
from mariupol_seizures.crawl.realestate_listings import make_session, _get  # noqa: E402

log = logging.getLogger(__name__)

# Detail-page URLs supplied by the user 2026-06-19 as resale evidence for
# пр. Ленина 108 (property_id 4421, decree №56 demolition order on record but
# the building was NOT fully razed -- see the case study's restoration-vs-
# demolition contradiction).
TARGETS = [
    {
        "url": "https://dnr.red/mariupol/search/nedvizhimost/prodazha-nedvizhimosti/"
               "prodazha-kvartir/vtorichnyy-rynok/"
               "prodajotsa-3kh-komnatnaja-kvartira-v-centre-goroda-pod-vash-remont-pr-lenina-d108-1506303.html",
        "title": "dnr.red — 3-room apartment, пр. Ленина 108",
    },
    {
        "url": "https://dnr.domick.ru/mariupol/tsientral-nyi/kupit/kvartiru/3-komnatnuiu/"
               "prodazha-3-kh-komnatnoi-kvartiry-mariupol-dnr-59304.html",
        "title": "dnr.domick.ru — 3-room apartment, Ленина 108 (центральный район)",
    },
]


def main() -> None:
    con = forensics.open_state()
    s = make_session()
    for t in TARGETS:
        log.info("fetching %s", t["url"])
        resp = _get(s, t["url"])
        if resp is None:
            log.error("no response for %s", t["url"])
            continue
        sha = forensics.capture_source(
            resp.content,
            url=t["url"],
            source_type="realestate_listing_detail",
            title=t["title"],
            description="Apartment-resale listing for пр. Ленина 108 (property_id 4421), "
                         "cited as demand-side resale evidence 2026-06-19.",
            content_type=resp.headers.get("content-type", "text/html"),
            http_status=resp.status_code,
            con=con,
        )
        log.info("captured %s -> sha=%s status=%s", t["url"], sha[:12], resp.status_code)
    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
