#!/usr/bin/env python3
"""Manifest of PDF/DOCX/XLSX **document attachments** across every captured
Telegram channel — a media class every prior flagging pass (scripts/148-155,
224-229) was blind to, because it only ever looked at photo/video media
(`MessageMediaPhoto` / video `MessageMediaDocument`), never plain-file
`MessageMediaDocument` with an office/PDF mime type.

This matters more than the photo/video troves: a channel-posted PDF/XLSX is
frequently the **primary source document itself** — a signed decree, an
official ownerless-property list, a court ruling, a resident's own complaint
letter — not a photo *of* one. On @mariupol_nash alone this surfaces the
actual district-level bezkhoz PDFs (Приморский/Орджоникидзевский/Ильичевский/
Жовтневый.pdf, 17.03.2026 — the same count already corroborated in STATS.md)
and the "ЕДИНЫЙ СВОД" combined ownerless list, both currently sitting
uncaptured despite already being cited by msg_id in
docs/nash_channel_findings_2026-07.md. On @ssaniaworld it surfaces resident
complaint letters (Ген прокуратура, отчуждение.docx), a court ruling
(Решение суда.pdf), a letter to Matvienko (Федерации Совет chair) about
bezkhoz, and an MKD inventory spreadsheet.

No priority tiering needed here (unlike scripts/225/226's photo/video
manifest) — the whole document class across every channel scanned is a few
hundred small files (single/low-digit MB each), trivial next to the ~2,900
photo/video targets or the channels' own video-heavy media pool. Pull
everything scripts/233 finds.

Scans every SOURCE_TYPE in SOURCE_TYPES below. Pure local analysis: reads
data/raw/ via source_document rows only. No network, no writes to data/raw or
the DB.

Run:
    PYTHONPATH=src python scripts/232_document_media_manifest.py
"""
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import forensics  # noqa: E402

log = logging.getLogger(__name__)

# every Telegram-sourced source_type this project has crawled so far;
# extend when a new channel/chat crawler is added
SOURCE_TYPES = [
    "telegram_nash_msg",
    "telegram_ssaniaworld_msg",
    "telegram_channel_msg",
    "telegram_building_chat_msg",
    "telegram_nmrpl_msg",
]

DOC_MIMES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-excel": ".xls",
    "application/msword": ".doc",
}

OUT = ROOT / "data" / "parsed" / "document_media_manifest.jsonl"


def _filename(doc: dict) -> str | None:
    for attr in doc.get("attributes") or []:
        if attr.get("_") == "DocumentAttributeFilename":
            return attr.get("file_name")
    return None


def main() -> None:
    con = forensics.open_state()
    fh = OUT.open("w", encoding="utf-8")

    totals = {}
    n_written = 0

    for source_type in SOURCE_TYPES:
        rows = con.execute(
            "SELECT url, raw_path FROM source_document WHERE source_type=?",
            (source_type,),
        ).fetchall()
        log.info("scanning %d %s messages for document attachments", len(rows), source_type)

        n_docs = 0
        n_size = 0
        for url, raw_path in rows:
            p = Path(raw_path)
            if not p.exists():
                continue
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue

            media = d.get("media")
            if not media or media.get("_") != "MessageMediaDocument":
                continue
            doc = media.get("document") or {}
            mime = doc.get("mime_type")
            ext = DOC_MIMES.get(mime)
            if not ext:
                continue

            n_docs += 1
            size = doc.get("size") or 0
            n_size += size
            rec = {
                "source_type": source_type,
                "msg_id": d.get("id"),
                "url": url,
                "date": (d.get("date") or "")[:10],
                "mime": mime,
                "ext": ext,
                "filename": _filename(doc),
                "size_bytes": size,
                "document_id": doc.get("id"),
                "access_hash": doc.get("access_hash"),
                "file_reference_note": (
                    "file_reference is short-lived — scripts/233 re-fetches the "
                    "live Message object via client.get_messages(ids=msg_id), "
                    "does not reuse this stale reference"
                ),
                "caption": (d.get("message") or "")[:300],
            }
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n_written += 1

        totals[source_type] = {"messages_scanned": len(rows), "documents_found": n_docs,
                                "total_size_mb": round(n_size / 1e6, 1)}

    fh.close()

    print(f"\n{'='*72}")
    print(f"DOCUMENT-MEDIA MANIFEST — {n_written} PDF/DOCX/XLSX files across "
          f"{len(SOURCE_TYPES)} channels")
    print(f"{'='*72}")
    for st, t in totals.items():
        print(f"  {st:28s} scanned={t['messages_scanned']:>7}  "
              f"docs={t['documents_found']:>4}  size={t['total_size_mb']:>6.1f}MB")
    print(f"\n  → {OUT}")
    print(f"\n  Next: PYTHONPATH=src .venv312/bin/python scripts/233_pull_document_media.py "
          f"— downloads every file in this manifest (network, run yourself).")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
