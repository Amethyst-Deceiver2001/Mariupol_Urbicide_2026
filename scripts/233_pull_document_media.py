#!/usr/bin/env python3
"""Download every PDF/DOCX/XLSX flagged by scripts/232's document-media
manifest — the primary-source-document trove (decrees, ownerless-property
lists, court rulings, resident complaint letters) that every prior media pass
missed because it only ever looked at photo/video media.

Unlike scripts/226 (photo/video, tiered by priority, video-size-capped) this
pulls the WHOLE manifest — it's a few hundred files, mostly under a few MB
each (~68MB total on @mariupol_nash alone), trivial next to the channels'
video pool. No tiering needed.

Groups manifest rows by channel (parsed from the `url` column,
https://t.me/<channel>/<id>), resolves each channel's entity once, and fetches
each flagged msg_id fresh via client.get_messages(ids=[...]) in batches of 100
(file_reference in the manifest is stale by design — never reused) before
calling client.download_media(). Captured via forensics.capture_source() under
source_type "telegram_document_media", content-addressed (SHA-256) like every
other capture in this project — a document already seen byte-for-byte on
another channel collapses onto one stored file, same as scripts/226.

Claude must never run this (CLAUDE.md) — it hits Telegram, a geoblocked
foreign-state-adjacent service. Run from your own Russia-routed terminal:

    .venv312/bin/python scripts/233_pull_document_media.py
    .venv312/bin/python scripts/233_pull_document_media.py --channel mariupol_nash
"""
from __future__ import annotations

import argparse
import io
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

MANIFEST = ROOT / "data" / "parsed" / "document_media_manifest.jsonl"
SOURCE_TYPE = "telegram_document_media"


def _channel_of(url: str) -> str:
    return urlparse(url).path.strip("/").split("/")[0]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", default=None,
                     help="only pull documents from this one channel (default: all)")
    args = ap.parse_args()

    if not (config.TELEGRAM_API_ID and config.TELEGRAM_API_HASH):
        log.error("TELEGRAM_API_ID / TELEGRAM_API_HASH not set in .env — aborting")
        sys.exit(1)

    try:
        from telethon.sync import TelegramClient
        from telethon import errors
    except ImportError:
        log.error("telethon not installed — run: pip install -e '.[telegram]'")
        sys.exit(1)

    if not MANIFEST.exists():
        log.error("%s not found — run scripts/232 first", MANIFEST)
        sys.exit(1)

    rows = [json.loads(line) for line in MANIFEST.read_text(encoding="utf-8").splitlines() if line.strip()]
    by_channel: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_channel[_channel_of(row["url"])].append(row)

    if args.channel:
        by_channel = {args.channel: by_channel.get(args.channel, [])}

    log.info("document manifest: %d files across %d channels", len(rows), len(by_channel))

    client = TelegramClient(config.TELEGRAM_SESSION, config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH)
    client.start(phone=config.TELEGRAM_PHONE_NUMBER)

    con = forensics.open_state()
    n_pulled = 0
    n_skipped_no_media = 0
    n_errors = 0

    try:
        for channel, channel_rows in by_channel.items():
            if not channel_rows:
                continue
            try:
                entity = client.get_entity(channel)
            except (errors.UsernameInvalidError, ValueError) as e:
                log.error("channel %r not resolvable: %s — skipping %d files", channel, e, len(channel_rows))
                n_errors += len(channel_rows)
                continue

            ids = [row["msg_id"] for row in channel_rows]
            row_by_id = {row["msg_id"]: row for row in channel_rows}
            log.info("@%s: fetching %d flagged document messages", channel, len(ids))

            for batch_start in range(0, len(ids), 100):
                batch_ids = ids[batch_start: batch_start + 100]
                messages = client.get_messages(entity, ids=batch_ids)
                for message in messages:
                    if message is None or message.media is None:
                        n_skipped_no_media += 1
                        continue
                    row = row_by_id.get(message.id)
                    try:
                        buf = io.BytesIO()
                        client.download_media(message, file=buf)
                        content = buf.getvalue()
                    except Exception as e:  # noqa: BLE001 — log and continue the batch
                        log.error("@%s/%d download failed: %s", channel, message.id, e)
                        n_errors += 1
                        continue

                    url = row["url"] if row else f"https://t.me/{channel}/{message.id}"
                    filename = (row or {}).get("filename") or f"{message.id}"
                    forensics.capture_source(
                        content, url=url,
                        source_type=SOURCE_TYPE,
                        title=f"@{channel}/{message.id} — {filename}",
                        description=(
                            f"Document attachment from @{channel} msg {message.id} "
                            f"({(row or {}).get('date', '?')}, {(row or {}).get('mime', '?')}). "
                            f"filename={filename}. caption: '{(row or {}).get('caption', '')}'"
                        ),
                        content_type=(row or {}).get("mime", "application/octet-stream"),
                        http_status=200, con=con,
                    )
                    n_pulled += 1
                log.info("… %d/%d fetched for @%s", min(batch_start + 100, len(ids)), len(ids), channel)
    finally:
        client.disconnect()

    total_stored = con.execute(
        "SELECT COUNT(*) FROM source_document WHERE source_type=?", (SOURCE_TYPE,)
    ).fetchone()[0]

    print(f"\n{'='*72}")
    print(f"DOCUMENT MEDIA PULL — {n_pulled} pulled this run "
          f"({n_skipped_no_media} no-longer-has-media, {n_errors} errors)")
    print(f"total {SOURCE_TYPE} artifacts in store: {total_stored}")
    print(f"{'='*72}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
