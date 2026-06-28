#!/usr/bin/env python3
"""Scan four Telegram channels surfaced as top-cited URLs in the
@mrpl_besxozxata deep-intel pass (scripts/171, 2026-06-26): one apparent
official DNR property-ministry channel, and three legal-advice channels
residents link to for plain-language interpretation of the ownerless/
registration-ban regime.

@mizodnr -- apparent official channel of Минимущества ДНР (DNR Ministry of
Property and Land Relations), the body named in this project's stakeholder
network (docs/stakeholder_network.md Tier 2) as the property/land
administration authority. If genuinely official, this is a primary source
on the same footing as denis-pushilin.ru, not a citizen chat.

@advocate_Basivskiy, @yuridicheskiyeuslugiMariupolDon, @donurcenter -- legal-
services channels actively cited by residents for advice; useful for
plain-language interpretation of decrees (e.g. the No. 1103/145/1006
property-registration-ban chain, memory/mrpl_besxozxata_deep_intel_2026-06-26.md)
but NOT primary sources -- treat content as commentary, verify against the
decree text before citing as fact.

Full-history capture (same as scripts/165/168, not the apartment-sale-gated
scripts/50 scanner) -- channel content/structure not yet known well enough
to write a content filter.

Claude must never run this (CLAUDE.md). The user runs it themselves:

    .venv312/bin/python scripts/174_crawl_property_registration_ban_decrees.py

Re-runs are incremental (only new message ids per channel).
"""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures.crawl import telegram_building_chats  # noqa: E402

CHANNELS = [
    "mizodnr",
    "advocate_Basivskiy",
    "yuridicheskiyeuslugiMariupolDon",
    "donurcenter",
]

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                         format="%(asctime)s %(levelname)s %(message)s")
    telegram_building_chats.run(
        CHANNELS,
        building_note=("Not single-building chats. @mizodnr is a candidate "
                        "official DNR property-ministry channel (verify "
                        "before treating as primary-source-grade); the "
                        "other three are legal-advice channels cited by "
                        "residents in @mrpl_besxozxata -- commentary, not "
                        "primary source. No spine property_id mapping."),
    )
