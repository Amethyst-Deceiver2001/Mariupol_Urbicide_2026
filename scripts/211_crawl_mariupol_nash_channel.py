#!/usr/bin/env python3
"""Scan @mariupol_nash, a Telegram channel (not yet profiled in this project).

Not a single-building resident chat -- a city-wide channel, same category as
@mizodnr/@advocate_Basivskiy/etc. (scripts/174). Channel content/affiliation
(official, news-aggregator, or independent commentary) is not yet known --
verify before treating any claim from it as primary-source-grade; default to
treating it as commentary/leads until an official affiliation is confirmed,
same posture taken for the scripts/174 legal-advice channels.

Full-history capture (same pattern as scripts/165/168/174) -- no content
filter, since the channel hasn't been profiled enough to write one safely.

Claude must never run this (CLAUDE.md). The user runs it themselves:

    .venv312/bin/python scripts/211_crawl_mariupol_nash_channel.py

Re-runs are incremental (only new message ids).
"""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures.crawl import telegram_building_chats  # noqa: E402

CHANNELS = [
    "mariupol_nash",
]

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                         format="%(asctime)s %(levelname)s %(message)s")
    telegram_building_chats.run(
        CHANNELS,
        building_note=("Not a single-building chat -- a city-wide channel. "
                        "Affiliation/reliability not yet profiled -- treat as "
                        "commentary/leads, not primary source, until verified. "
                        "No spine property_id mapping."),
    )
