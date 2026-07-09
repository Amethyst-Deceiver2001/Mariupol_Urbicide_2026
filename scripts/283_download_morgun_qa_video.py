#!/usr/bin/env python3
"""Download two videos via telethon, both too large for the unauthenticated
Telegram /s/ embed widget (yt-dlp cannot pull them directly -- the direct
.mp4 URL is only exposed via an authenticated API session's
message.download_media()):

1. Олег Моргун's own post (@morgun_ov/9992, 45:47) -- a Q&A livestream
   recording where Моргун and department specialists answer resident
   questions on forming the municipal housing fund, MKD/infrastructure
   restoration, and (per the post's own caption) walk through "the
   procedure of going through the inventory" and what a resident should do
   if their home appears on the bezkhoz-flagged list.

2. @allmarinews/39282 (37:29) -- Игнат Яремчук, the deputy head of the
   Mariupol administration already named across the №1223/№1565/№1727/
   №1740 inventory decrees (docs/legal_mechanisms_review.md) as the
   official responsible for oversight, walks through the inventory
   mechanism in detail with on-screen chapter timestamps: 01:01 legislative
   changes, 02:17 inventory progress/first results, 07:12 definition of
   bezkhoz property, 09:02 what happens if an owner evades registration,
   13:43 actions for RF-citizen owners physically in Mariupol, 16:31
   actions for owners abroad, 17:22 non-owner occupants, 20:21 social/
   commercial tenancy, 25:53 open inheritance cases, 29:27 replacement
   housing for owners of lost unprivatized apartments, 32:04 what to do if
   you find a notice on your door.

Claude must never run this (CLAUDE.md) -- it hits Telegram, a geoblocked
foreign-state-adjacent service. Run from your own Russia-routed terminal:

    .venv312/bin/python scripts/283_download_morgun_qa_video.py

Downloads to the scratchpad as morgun_9992.mp4 and allmarinews_39282.mp4.
Once downloaded, tell Claude -- scripts/284 will hash them into the raw
store and transcribe both with whisper (already installed in .venv312).
"""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402

log = logging.getLogger(__name__)

SCRATCH = Path(
    "/private/tmp/claude-501/-Users-ak-Downloads-mariupol-property-seizures/"
    "342b195a-6008-4b21-a81f-9d63615da8f5/scratchpad"
)

TARGETS = [
    ("morgun_ov", 9992, "morgun_9992.mp4"),
    ("allmarinews", 39282, "allmarinews_39282.mp4"),
]


def main() -> None:
    from telethon.sync import TelegramClient

    client = TelegramClient(config.TELEGRAM_SESSION, config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH)
    with client:
        for channel, message_id, filename in TARGETS:
            msg = client.get_messages(channel, ids=message_id)
            if msg is None:
                log.error("message %s/%s not found", channel, message_id)
                continue
            out_path = SCRATCH / filename
            log.info("downloading media for %s/%s -> %s", channel, message_id, out_path)
            client.download_media(msg, file=str(out_path))
            log.info("done: %s (%d bytes)", out_path, out_path.stat().st_size if out_path.exists() else -1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
