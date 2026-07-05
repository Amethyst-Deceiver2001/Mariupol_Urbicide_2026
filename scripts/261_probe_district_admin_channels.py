#!/usr/bin/env python3
"""Probe for official district-administration Telegram channels for
Mariupol's other 3 districts, sibling to the already-found @ordjonikidzadmin
("УПРАВА ОРДЖОНИКИДЗЕВСКОГО ВНУТРИГОРОДСКОГО РАЙОНА ГОРОДА МАРИУПОЛЬ").

The @mariupol_nash forward-source graph surfaced @ordjonikidzadmin plus 4
PRIVATE, unofficial community channels named after all 4 districts (Жовтневый/
Ильичёвский/Орджоникидзевский/Приморский) -- but no OFFICIAL admin channel for
the other 3. This is a best-effort GUESS at the naming pattern, not a
confirmed finding -- every candidate below is unverified until this script
(or a manual check) actually resolves it.

Candidates are transliteration variants of "<district>admin" following
@ordjonikidzadmin's exact pattern, for each of Жовтневый, Ильичёвский,
Приморский:
  - zhovtnevadmin, zhovtadmin
  - ilichadmin, ilyichadmin, ilichevskadmin
  - primorskadmin, primoradmin

Claude must never run this (CLAUDE.md) — it hits Telegram, a geoblocked
foreign-state-adjacent service. Run from your own Russia-routed terminal:

    .venv312/bin/python scripts/261_probe_district_admin_channels.py
"""
from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402

log = logging.getLogger(__name__)

CANDIDATES = {
    "Жовтневый": ["zhovtnevadmin", "zhovtadmin", "zhovtnevskadmin"],
    "Ильичёвский": ["ilichadmin", "ilyichadmin", "ilichevskadmin", "ilichevskyadmin"],
    "Приморский": ["primorskadmin", "primoradmin", "primorskyadmin"],
}


def main() -> None:
    if not (config.TELEGRAM_API_ID and config.TELEGRAM_API_HASH):
        log.error("TELEGRAM_API_ID / TELEGRAM_API_HASH not set in .env — aborting")
        sys.exit(1)
    try:
        from telethon.sync import TelegramClient
        from telethon import errors
    except ImportError:
        log.error("telethon not installed — run: pip install -e '.[telegram]'")
        sys.exit(1)

    client = TelegramClient(config.TELEGRAM_SESSION, config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH)
    client.start(phone=config.TELEGRAM_PHONE_NUMBER)

    found = []
    try:
        for district, usernames in CANDIDATES.items():
            for uname in usernames:
                try:
                    entity = client.get_entity(uname)
                    title = getattr(entity, "title", None)
                    participants = getattr(entity, "participants_count", None)
                    log.info("HIT  @%s (%s) -- title=%r participants=%s",
                             uname, district, title, participants)
                    found.append({"district": district, "username": uname,
                                  "title": title, "participants_count": participants})
                except (errors.UsernameInvalidError, errors.UsernameNotOccupiedError, ValueError):
                    log.info("miss @%s (%s) -- not a valid/occupied username", uname, district)
                except errors.ChannelPrivateError:
                    log.info("EXISTS but private @%s (%s) -- confirms the handle is taken, "
                              "can't read without an invite", uname, district)
                    found.append({"district": district, "username": uname,
                                  "title": "(private, exists)", "participants_count": None})
                except Exception as e:  # noqa: BLE001
                    log.warning("error probing @%s: %s", uname, e)
                time.sleep(0.5)
    finally:
        client.disconnect()

    print(f"\n{'='*72}")
    if found:
        print(f"FOUND {len(found)} candidate(s):")
        for f in found:
            print(f"  {f['district']}: @{f['username']} -- {f['title']} "
                  f"(participants={f['participants_count']})")
    else:
        print("No candidates resolved -- none of the guessed usernames exist under this "
              "naming pattern. The other 3 districts either don't run an official Telegram "
              "channel, or use a naming convention this guess didn't anticipate (check the "
              "district administration's own website/VK page for a linked Telegram handle).")
    print(f"{'='*72}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
