#!/usr/bin/env python3
"""Stage 1j: scan Telegram channels for Mariupol apartment-sale offers (MTProto).

Demand-side [F]-resale evidence. Forensic capture only — the apartment-sale filter
runs in scripts/51_parse_realestate_offers.py (capture before parse).

Uses the user's Telegram credentials (config.TELEGRAM_*, from .env) and a persisted
login session. Claude must never run this (CLAUDE.md). The user runs it:

    pip install -e '.[telegram]'                              # first time
    python3 scripts/50_crawl_telegram_channels.py             # all configured channels
    python3 scripts/50_crawl_telegram_channels.py nemariupol mariupolskiy_uezd

First run is interactive (Telethon prompts for the SMS/app code + any 2FA password);
subsequent runs are non-interactive and incremental (only messages newer than the
highest id already captured per channel). Channels: config.TELEGRAM_CHANNELS.
"""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures.crawl import telegram_channels  # noqa: E402

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    only = sys.argv[1:] or None
    telegram_channels.run(only=only)
