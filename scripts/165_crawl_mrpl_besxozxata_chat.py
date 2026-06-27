#!/usr/bin/env python3
"""Scan the @mrpl_besxozxata Telegram channel for ownerless-registry evidence.

Background: this channel's name itself ("mrpl_besxozxata" — Mariupol +
"бесхозяйность"/ownerless) suggests it is a dedicated, city-wide channel about
the ownerless-registry process, not a single-building resident chat like the
28 already in `chat_buildings.py`. It is not yet in `config.TELEGRAM_CHANNELS`
and has never been crawled by this project. Full-history capture is the right
call here (same as the building-chat scanner, not the apartment-sale-gated
scripts/50 scanner): if the channel really is about ownerless designations
city-wide, every message is potentially evidence — named addresses, decree
citations, registry screenshots, resident reactions — and we don't yet know
its structure well enough to write a content filter.

Claude must never run this (CLAUDE.md, see also scripts/50, scripts/62). The
user runs it, from their own machine/session, using their Telegram credentials:

    pip install -e '.[telegram]'        # first time, if not already done
    .venv312/bin/python scripts/165_crawl_mrpl_besxozxata_chat.py

First run is interactive only if the Telegram session isn't already authed
(scripts/50 already created data/telegram_session, so this should be
non-interactive). Re-runs are incremental (only new message ids).

NEXT STEP AFTER THIS RUNS
--------------------------
This script only captures (Berkeley Protocol: capture before parse). Once it
has run and the raw store has the messages, a follow-up parser script will be
needed to actually extract addresses/decree citations/dates and decide how
this channel's content maps onto the spine (likely multi-building, unlike the
existing per-chat parsers) — that script can't be written sensibly until we
can see what the channel's messages actually look like.
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
    channels = sys.argv[1:] or ["mrpl_besxozxata"]
    telegram_building_chats.run(
        channels,
        building_note=("Not a single-building chat — appears to be a "
                        "city-wide ownerless-registry channel (no spine "
                        "property_id mapping yet; see chat_buildings.py "
                        "before assuming single-building scope)."),
    )
