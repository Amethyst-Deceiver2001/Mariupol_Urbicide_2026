#!/usr/bin/env python3
"""Incremental re-scan of every monitored Telegram INTEL channel (news,
official DNR/Mariupol admin, legal-advice, forwarding-network, and 5-channel
flagged-media source channels) for new messages since the last capture.

Deliberately EXCLUDES the 28 per-building resident chats (scripts/62,
140-147, etc. -- mostly dormant/spam per user 2026-07-20) and the demand-side
apartment-resale marketplace channels (config.TELEGRAM_CHANNELS, run
separately via scripts/50 -- a different evidentiary track).

This is a consolidated union of every CHANNELS list scattered across the
one-off capture scripts below -- written because there was no single place
to "just check what's new" across the channels we actually monitor:
  - scripts/165 (mrpl_besxozxata), 174 (mizodnr + legal-advice trio),
    211/212 (mariupol_nash), 227 (ssaniaworld), 234 (nmrpl),
    257 (fwd-network tiers 1-3), 262 (district admin / DNR ministries),
    302 (mariupolRIP), 317 (kadryVoynyMariypol2022),
    335-339 (mrplSprotyv/novosti_mariupol1/mariupol24tv/mrpl_ctzn/
    NickolayOsychenko -- the scripts/367 5-channel flagged-media set).

Reuses telegram_building_chats.run(), whose "already captured" check keys
off source_type='telegram_building_chat_msg' -- a source_type NONE of these
channels have ever used before (their prior one-off capture scripts, e.g.
302/165/174/227/234, each used their own distinct source_type). So on first
run every channel here is NOT actually incremental: it triggers a full
history backfill (HISTORY_LIMIT=20000 msgs/channel) -- and the underlying
module downloads media UNCONDITIONALLY, since it was written for tiny
single-building resident chats, not scaled to large public/official
channels. CORRECTED 2026-07-21 after a first run stalled ~15.5h on ONE
channel (prav_dnr, the DNR government press channel) and pulled 54GB/11,178
media files before being stopped -- see memory/telegram_media_blowup_
2026-07-21.md. Now runs TEXT-ONLY (download_media=False): captures every
message's text/metadata (still fully incremental thereafter, once each
channel has at least one telegram_building_chat_msg row) but skips media
entirely. Pull media for a specific channel/message deliberately via a
targeted script instead (the project's established pattern -- see
scripts/226/367) once the text pass shows it's worth it.

Claude must never run this (CLAUDE.md). The user runs it themselves:

    .venv312/bin/python scripts/385_scan_monitored_channels_latest.py
    .venv312/bin/python scripts/385_scan_monitored_channels_latest.py mizodnr donurcenter   # subset
"""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures.crawl import telegram_building_chats  # noqa: E402

CHANNELS = [
    # official / primary-source
    "mizodnr", "rosreestr80", "minstroydnr", "AG_DPR", "prav_dnr",
    "KoltsovAnton", "PushilinDenis", "mkhusnullin",
    "ordjonikidzadmin", "ilichevskiy", "mariupol_primorskiy",
    "zhovtnevyy", "news_oktyabrskiy",
    "mtspdnr", "mzdnr_official", "minobrnauki_dnr", "merdnr",
    "rks_nr", "ivashchenko_kv", "morgun_ov",
    # legal-advice / commentary
    "advocate_Basivskiy", "yuridicheskiyeuslugiMariupolDon", "donurcenter",
    # city-wide ownerless/bezkhoz-relevant
    "mrpl_besxozxata",
    # news / citizen-intel (deep-mined or flagged-media source channels)
    "mariupol_nash", "ssaniaworld", "nmrpl", "mariupolRIP",
    "kadryVoynyMariypol2022", "mrplSprotyv", "novosti_mariupol1",
    "mariupol24tv", "mrpl_ctzn", "NickolayOsychenko",
    # fwd-network tier 1 (high flagged-content rate)
    "mariupol_po_faktu", "solntsev_official",
    # fwd-network tier 2
    "Nash_Mariupol", "CHYORNYY_SPISOK", "infrMariupol", "Mangush_Podslushano",
    # fwd-network tier 3 (lower relevance, included for completeness)
    "Mariupol_Photograph", "Mariupol_Kultura", "black_pirat_news",
    "Mariupol_Media", "Svyatoy_Matros", "TLenamrpl", "Mariupol_Yumor",
    "ZV_MRPL", "rusgorod", "khartsyz", "marmgu", "Papochki_ru",
    "yagodkin_d", "sport_dlya_vsekh_Mariupol", "molodoy_mrpl",
    "gorizont_mariupol",
]

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                         format="%(asctime)s %(levelname)s %(message)s")
    only = sys.argv[1:] or CHANNELS
    log = logging.getLogger(__name__)
    log.info("scanning %d channel(s) for new messages since last capture "
              "(TEXT ONLY -- media download disabled, see module docstring)",
              len(only))
    telegram_building_chats.run(
        only,
        building_note=("Monitored intel channel, not a per-building resident "
                        "chat -- scripts/385 consolidated re-scan, "
                        "2026-07-20. No spine property_id mapping unless "
                        "separately established."),
        download_media=False,
    )
