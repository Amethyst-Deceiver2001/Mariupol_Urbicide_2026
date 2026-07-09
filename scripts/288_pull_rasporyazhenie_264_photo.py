#!/usr/bin/env python3
"""Pull the photo attached to @mrpl_besxozxata/31910 -- the ONE post found so
far that shows an actual paper purporting to be "Распоряжение 264" ("Order
No. 264"), the phantom decree residents have reported seeing named on
door-posted inventory notices for years without anyone tracing it to a real,
findable instrument (see docs/legal_mechanisms_review.md, the standing
No. 264 open question).

Context: the message (25.07.2024, forwarded from a since-deleted account,
caption "Распоряжение 264") is already in the raw store as message-metadata
JSON (scripts/148-151 bulk chat scrape), but the photo binary itself was
never pulled -- only message text/metadata is captured by that scrape, not
attached media. This is a single, targeted pull, not a channel-wide sweep.

Per the resident who supplied this lead: the text on the paper is
photographed at an angle / partially out of focus, so it may not be fully
legible even once captured -- expect this to raise more questions than it
answers (an unverified provenance photo from a deleted account is evidence
of "something calling itself 264 exists on paper," not confirmation of a
genuine numbered decree). Capture it anyway for the record and for future
OCR/visual review, and flag it explicitly as unresolved.

Claude must NEVER run this -- it hits Telegram (a geoblocked foreign-state-
adjacent service) and must be run by you, from your own terminal (CLAUDE.md).

Usage:
    .venv312/bin/python scripts/288_pull_rasporyazhenie_264_photo.py
"""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

CHANNEL = "mrpl_besxozxata"
MSG_ID = 31910
SOURCE_TYPE = "telegram_264_provenance_photo"
URL = f"https://t.me/{CHANNEL}/{MSG_ID}"
TITLE = (
    "Photo purporting to show a paper copy of \"Распоряжение 264\" "
    "(@mrpl_besxozxata/31910, 25.07.2024, fwd from a deleted account)"
)
DESCRIPTION = (
    "Единственный найденный к 2026-07-09 пост с фотографией бумаги, "
    "претендующей быть 'Распоряжением 264' -- документом, который годами "
    "упоминается жителями как название на печатных объявлениях об "
    "инвентаризации на дверях подъездов, но ни разу не был прослежен до "
    "существующего нормативного акта (см. docs/legal_mechanisms_review.md, "
    "открытый вопрос №264). Публикация переслана от УДАЛЁННОГО аккаунта -- "
    "происхождение и подлинность фотографии не установлены. Текст на "
    "снимке сфотографирован под углом / частично не в фокусе, поэтому "
    "может быть нечитаем полностью даже после захвата. Captured for the "
    "record and future OCR/visual review; flagged [UNRESOLVED] pending "
    "legibility check, not treated as confirmation of a real decree."
)


def _media_content_type(message) -> str:
    f = getattr(message, "file", None)
    mime = getattr(f, "mime_type", None) if f is not None else None
    if mime:
        return mime
    if getattr(message, "photo", None) is not None:
        return "image/jpeg"
    return "application/octet-stream"


def main() -> None:
    if not (config.TELEGRAM_API_ID and config.TELEGRAM_API_HASH):
        log.error("TELEGRAM_API_ID / TELEGRAM_API_HASH not set in .env -- aborting")
        sys.exit(1)
    try:
        import telethon  # noqa: F401
    except ImportError:
        log.error("telethon not installed -- run: pip install -e '.[telegram]'")
        sys.exit(1)

    from telethon.sync import TelegramClient
    from telethon import errors

    con = forensics.open_state()
    client = TelegramClient(
        config.TELEGRAM_SESSION, config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH)
    client.start(phone=config.TELEGRAM_PHONE_NUMBER)
    try:
        try:
            entity = client.get_entity(CHANNEL)
        except (errors.UsernameInvalidError, ValueError) as e:
            log.error("channel %r not resolvable: %s", CHANNEL, e)
            return

        msg = client.get_messages(entity, ids=MSG_ID)
        if msg is None:
            log.error("message %s/%s not found (deleted/inaccessible)", CHANNEL, MSG_ID)
            return
        if getattr(msg, "media", None) is None:
            log.error("message %s/%s has no media attached", CHANNEL, MSG_ID)
            return

        try:
            blob = client.download_media(msg, file=bytes)
        except Exception:  # noqa: BLE001
            log.exception("download failed for %s", URL)
            return
        if not blob:
            log.error("empty media blob for %s", URL)
            return

        ct = _media_content_type(msg)
        sha = forensics.capture_source(
            blob, url=URL + "/media", source_type=SOURCE_TYPE,
            title=TITLE, description=DESCRIPTION,
            content_type=ct, http_status=200, con=con,
        )
        log.info("captured photo -> sha=%s (%d bytes, %s)", sha[:12], len(blob), ct)
        log.info("done. Review the image, then tell Claude what's legible so the "
                  "No. 264 open question can be updated.")
    finally:
        con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
