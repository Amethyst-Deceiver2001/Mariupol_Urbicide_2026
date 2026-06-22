#!/usr/bin/env python3
"""Stage 1h: capture DNR/Mariupol normative acts from npa.dnronline.su — a
Latin-transliterated, plain-HTTP mirror of нпа.днронлайн.рф.

Discovered 2026-06-12: unlike the Cyrillic-punycode нпа.днронлайн.рф domain
(script 13, treated as geoblocked/VPS-only), this mirror is reachable over
plain HTTP with no geoblock from outside Russia. Run directly from the user's
Mac — no VPS/proxy needed:

    PYTHONPATH=src python scripts/38_crawl_npa_dnronline_known.py

Captures 12 known documents (HTML + any linked PDFs):
  - Указ Главы ДНР №301 (20.06.2022) — renaming-authority delegation
    framework, the enabling norm for gap [H] in
    docs/legal_mechanisms_review.md
  - Распоряжение главы администрации г. Мариуполя №61 (03.11.2022) —
    municipal property-lease rulebook, the [A]→[D]/[F]/[G] disposal bridge
  - The 3 other items in the sparse "Распоряжения глав городов и районов
    ДНР" category (Докучаевск №734, Макеевка №72, Донецк №40), for
    completeness
  - All 7 items in the "Распоряжения ГКО ДНР" 2022 category, to corroborate
    that Распоряжение №56 (the Mariupol demolition list, gap [C]) is absent
    from this portal too

See src/mariupol_seizures/crawl/npa_dnronline.py for full design notes.
"""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures.crawl import npa_dnronline  # noqa: E402

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    npa_dnronline.run()
