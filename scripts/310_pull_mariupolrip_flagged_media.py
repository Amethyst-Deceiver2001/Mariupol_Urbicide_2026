#!/usr/bin/env python3
"""Pull media for ONLY the flagged @mariupolRIP obituary messages -- never
the whole channel. Same shape as scripts/226 (the @mariupol_nash puller),
pointed at the manifest scripts/309 built from the full mariupolRIP scan.

Consumes data/parsed/mariupolrip_media_pull_manifest.jsonl and downloads
media (mostly victim/grave photos, a handful of videos and documents) for
those specific message ids, keyed by pull_priority:
    1 = message matched to a property on the spine (102 messages)
    2 = named-victim record with death/burial language, no property match (1,169)
    3 = weaker obituary signal only (955)

Everything captured lands in the forensic store as source_type
"telegram_mariupolrip_media", chain-of-custody identical to every other
Telegram media capture in this project (SHA-256 + timestamp via
forensics.capture_source).

Claude must NEVER run this -- it hits Telegram (a geoblocked foreign-state-
adjacent service) and must be run by you, from your own Russia-routed
terminal (CLAUDE.md).

    .venv312/bin/python scripts/310_pull_mariupolrip_flagged_media.py                  # P1+P2 (default), skip video >50MB
    .venv312/bin/python scripts/310_pull_mariupolrip_flagged_media.py --max-priority 1 # only the 102 property-matched leads
    .venv312/bin/python scripts/310_pull_mariupolrip_flagged_media.py --max-priority 3 # everything in the manifest (2,226 items)
    .venv312/bin/python scripts/310_pull_mariupolrip_flagged_media.py --max-video-mb 0 # photos/documents only, no video at all

Re-runs are idempotent: capture_source() is keyed by SHA-256, already-captured
media is skipped for free, so interrupt/resume is safe.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

CHANNEL = "mariupolRIP"
SOURCE_TYPE = "telegram_mariupolrip_media"
MANIFEST = ROOT / "data" / "parsed" / "mariupolrip_media_pull_manifest.jsonl"
BATCH = 100   # telethon get_messages ids= batch size


def _load_manifest(manifest_path: Path, max_priority: int, max_video_mb: float) -> list[dict]:
    if not manifest_path.exists():
        log.error("manifest not found: %s — run scripts/309 (or scripts/312) first", manifest_path)
        sys.exit(1)
    cap = max_video_mb * 1024 * 1024 if max_video_mb > 0 else 0
    targets = []
    skipped_pri = skipped_vid = 0
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("pull_priority", 3) > max_priority:
            skipped_pri += 1
            continue
        if row.get("media_kind") == "video":
            size = row.get("media_size_bytes") or 0
            if max_video_mb == 0 or (cap and size > cap):
                skipped_vid += 1
                continue
        targets.append(row)
    log.info("manifest: %d targets (skipped %d over priority %d, %d oversized/blocked video)",
             len(targets), skipped_pri, max_priority, skipped_vid)
    return targets


def _media_content_type(message) -> str:
    f = getattr(message, "file", None)
    mime = getattr(f, "mime_type", None) if f is not None else None
    if mime:
        return mime
    if getattr(message, "photo", None) is not None:
        return "image/jpeg"
    return "application/octet-stream"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-priority", type=int, default=2, choices=[1, 2, 3],
                    help="pull manifest rows up to this priority (1=property-matched, "
                         "2=+named obituary records, 3=+weaker signal). Default 2.")
    ap.add_argument("--max-video-mb", type=float, default=50.0,
                    help="skip videos larger than this (MB). 0 = no video at all. Default 50.")
    ap.add_argument("--manifest", type=Path, default=MANIFEST,
                    help="manifest JSONL to pull from (default: scripts/309's full obituary manifest). "
                         "Pass scripts/312's gravefinder manifest to pull only that targeted subset.")
    args = ap.parse_args()

    if not (config.TELEGRAM_API_ID and config.TELEGRAM_API_HASH):
        log.error("TELEGRAM_API_ID / TELEGRAM_API_HASH not set in .env — aborting")
        sys.exit(1)
    try:
        import telethon  # noqa: F401
    except ImportError:
        log.error("telethon not installed — run: pip install -e '.[telegram]'")
        sys.exit(1)

    targets = _load_manifest(args.manifest, args.max_priority, args.max_video_mb)
    if not targets:
        log.info("nothing to pull")
        return
    by_id = {int(t["msg_id"]): t for t in targets if t["msg_id"].isdigit()}
    ids = sorted(by_id)

    from telethon.sync import TelegramClient
    from telethon import errors

    con = forensics.open_state()
    client = TelegramClient(
        config.TELEGRAM_SESSION, config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH)
    client.start(phone=config.TELEGRAM_PHONE_NUMBER)
    n_pulled = n_empty = n_err = 0
    try:
        try:
            entity = client.get_entity(CHANNEL)
        except (errors.UsernameInvalidError, ValueError) as e:
            log.error("channel %r not resolvable: %s", CHANNEL, e)
            return

        for i in range(0, len(ids), BATCH):
            chunk = ids[i:i + BATCH]
            messages = client.get_messages(entity, ids=chunk)
            for msg in messages:
                if msg is None or getattr(msg, "media", None) is None:
                    continue
                meta = by_id.get(msg.id, {})
                url = f"https://t.me/{CHANNEL}/{msg.id}"
                try:
                    blob = client.download_media(msg, file=bytes)
                except Exception:  # noqa: BLE001
                    log.exception("download failed for %s", url)
                    n_err += 1
                    continue
                if not blob:
                    n_empty += 1
                    continue
                ct = _media_content_type(msg)
                caption = (msg.message or "").strip()
                forensics.capture_source(
                    blob, url=url + "/media",
                    source_type=SOURCE_TYPE,
                    title=f"@{CHANNEL}/{msg.id} media",
                    description=(
                        f"Flagged @{CHANNEL} obituary media, priority "
                        f"{meta.get('pull_priority','?')}. property_id="
                        f"{meta.get('property_id') or '-'} {meta.get('note','')}. "
                        f"{url} ({msg.date.date() if msg.date else '?'}, {ct}). "
                        f"caption: {caption[:200]!r}"),
                    content_type=ct, http_status=200, con=con,
                )
                n_pulled += 1
                if n_pulled % 50 == 0:
                    log.info("  ...%d media captured", n_pulled)
    finally:
        client.disconnect()

    total = con.execute(
        "SELECT COUNT(*) FROM source_document WHERE source_type=?", (SOURCE_TYPE,)
    ).fetchone()[0]
    log.info("done — %d pulled this run (%d empty, %d errors); %d total %s in store",
             n_pulled, n_empty, n_err, total, SOURCE_TYPE)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
