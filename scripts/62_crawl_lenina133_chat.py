#!/usr/bin/env python3
"""Scan the @Lenina133 Telegram resident chat (property_id 4442, просп. Ленина
(Мира), 133) for siege/occupation-era evidence — text + ALL attached media.

Background: the federal damage tracker (corroboration id 1412) lists this
building at 100% destruction, Phase II demolition — but satellite imagery shows
it still standing as of 9 May 2022, and the resident chat has photos posted
25 Nov 2022 showing extensive (but non-collapse) siege damage. This scan pulls
the full chat history so we can build a dated damage timeline and cross-check
the "100% destruction" claim against primary-source photos.

Claude must never run this (CLAUDE.md — see also scripts/50). The user runs it:

    .venv312/bin/python scripts/62_crawl_lenina133_chat.py

First run is interactive only if the Telegram session isn't already authed
(scripts/50 already created data/telegram_session, so this should be
non-interactive). Re-runs are incremental (only new message ids).
"""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures.crawl import telegram_building_chats  # noqa: E402

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                         format="%(asctime)s %(levelname)s %(message)s")
    channels = sys.argv[1:] or ["Lenina133"]
    telegram_building_chats.run(
        channels,
        building_note=("property_id=4442, building_id=AVENUE:ленина|133, "
                        "просп. Ленина (Мира), 133."),
    )
