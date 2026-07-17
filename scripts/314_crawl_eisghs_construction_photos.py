#!/usr/bin/env python3
"""Stage 1i-photos: capture ЕИСЖС 'Ход строительства' construction-progress
photo galleries for every Mariupol new-construction object already on file.

WHY THIS EXISTS
---------------
scripts/17/18 capture+parse the ЕИСЖС object detail record for all 91
Mariupol new-construction objects, including each object's own geocoded
point (objLkLatitude/objLkLongitude). A 2026-07-14 ad-hoc spatial join of
that point against demolished property.geom found 17 objects sitting within
30m of a demolished building's own geocoded point — but many of those
objects' ЕИСЖС `address` field is street-only ("б-р Богдана Хмельницкого",
no house number), so the spatial signal alone can't safely become a
crosswalk entry (see scripts/164_export_map_layers.py's
DEMOLITION_NEWBUILD_CROSSWALK — proximity/address-similarity alone was
already ruled insufficient there, after the Жукова 90Б false-positive).

Manual inspection of object id=66544 (наш.дом.рф's own 'Расположение' tab +
'Ход строительства' gallery) found the missing piece: the developer's own
monthly progress photos carry a burned-in caption in the lower-left corner —
for id=66544: "БУЛЬВАР БОГДАНА ХМЕЛЬНИЦКОГО 12А 25.11.2025" — giving the
exact house number the ЕИСЖС address field omits. This is a primary-source
disclosure independent of both the ЕИСЖС API's address field and the spatial
match, from an endpoint the crawler already documented but never called:
/сервисы/api/object/construction/progress/photo/<id>.

SCOPE — CONFIRMED 2026-07-15: the burned-in caption is a СЗ-1 ПОРФИР house
style only; other developers' galleries carry no caption. This script still
captures every developer's gallery (JSON listing + every image file) for
every object already captured by scripts/17 — the photos remain useful
dated primary-source construction-progress documentation even without a
caption, and capturing everything now avoids a second VPS run later if that
changes. scripts/315's OCR pass is scoped to Porfir objects only; see its
docstring. Idempotent — safe to re-run; already-captured (house_id, photo)
pairs are skipped.

Run from a Russia-routed VPS only — наш.дом.рф is geoblocked and
WAF-protected (servicepipe.ru; curl_cffi Chrome-impersonation required,
already handled by eisghs_mariupol.make_object_session()).

After capture, run scripts/315_ocr_construction_photo_addresses.py to OCR
the burned-in captions — that step is pure local tesseract, no network.
"""
from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import forensics  # noqa: E402
from mariupol_seizures.crawl import eisghs_mariupol as em  # noqa: E402

log = logging.getLogger(__name__)


def _known_object_ids(con) -> list[str]:
    """Every ЕИСЖС object ID already captured by scripts/17 (eisghs_house_detail)."""
    rows = con.execute(
        "SELECT DISTINCT title FROM source_document WHERE source_type='eisghs_house_detail'"
    ).fetchall()
    ids: set[str] = set()
    for (title,) in rows:
        m = re.search(r"\bid=(\d+)", title)
        if m:
            ids.add(m.group(1))
    return sorted(ids, key=int)


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                         format="%(asctime)s %(levelname)s %(message)s")

    con = forensics.open_state()
    ids = _known_object_ids(con)
    if not ids:
        log.error("No eisghs_house_detail records in state DB — "
                   "run scripts/17_crawl_eisghs_mariupol.py first.")
        return
    log.info("capturing construction-progress galleries for %d objects", len(ids))

    s_obj = em.make_object_session()
    if not em.warm_object_session(s_obj):
        log.warning("object session warm-up failed — endpoint may return 403")

    total_photos = 0
    objects_with_photos = 0
    for i, house_id in enumerate(ids, 1):
        n = em.capture_construction_progress_photos(
            s_obj, con, house_id, gk_name="manual_catalog"
        )
        if n:
            objects_with_photos += 1
        total_photos += n
        log.info("[%d/%d] id=%s → %d new photos captured", i, len(ids), house_id, n)

    log.info("done: %d photos captured across %d/%d objects",
              total_photos, objects_with_photos, len(ids))
    log.info("Next step: python scripts/315_ocr_construction_photo_addresses.py")


if __name__ == "__main__":
    main()
