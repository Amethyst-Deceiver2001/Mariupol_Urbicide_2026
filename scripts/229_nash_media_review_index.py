#!/usr/bin/env python3
"""Index + browsable export of the media scripts/226 just pulled for @mariupol_nash.

scripts/226 landed 761 captured files under source_type "telegram_nash_media"
(790 download attempts this run, 0 errors — the gap is expected: several of the
manifest's photo targets are reposts of the same image across different
messages, so distinct SHA-256 content collapses onto fewer unique files;
capture_source() is content-addressed by design, see forensics.py).

This script does NOT touch the raw store (append-only/immutable, per
CLAUDE.md) — it only reads source_document rows and:

  1. Reconciles the pull against data/parsed/nash_media_pull_manifest.jsonl —
     reports any manifest target that never got a matching captured file
     (deleted/edited message, media-type change between manifest-build time
     and pull time, etc.) so nothing silently falls through.
  2. Writes data/parsed/nash_media_review_index.jsonl — one row per captured
     file: msg_id, date, priority, tags, lead_note (if this msg_id is one of
     scripts/225's 35 curated leads), caption excerpt, raw_path, sha256, size.
  3. Builds a **symlinked** review tree under data/exports/nash_media_review/
     so the photos can be browsed in Finder/Preview without duplicating the
     immutable raw store:
         <priority>/<lead-slug-or-tag>/<date>_<msg_id>.<ext>          -> symlink to raw file
         <priority>/<lead-slug-or-tag>/<date>_<msg_id>.<ext>.caption.txt  -> plain-text caption + tags

Pure local analysis, no network, no writes to data/raw or the DB. Safe to
re-run (rebuilds the export tree from scratch each time).

Run:
    PYTHONPATH=src python scripts/229_nash_media_review_index.py
"""
import json
import logging
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import forensics  # noqa: E402

log = logging.getLogger(__name__)

SOURCE_TYPE = "telegram_nash_media"
MANIFEST = ROOT / "data" / "parsed" / "nash_media_pull_manifest.jsonl"
OUT_INDEX = ROOT / "data" / "parsed" / "nash_media_review_index.jsonl"
EXPORT_DIR = ROOT / "data" / "exports" / "nash_media_review"

# same curated-lead notes as scripts/225, kept in sync manually — see that
# file's LEADS dict if this needs updating.
from importlib import util as _il_util  # noqa: E402


def _load_leads() -> dict:
    """Import LEADS straight from scripts/225 so the two never drift apart."""
    spec = _il_util.spec_from_file_location(
        "nash_flag_module", ROOT / "scripts" / "225_nash_flag_and_media_manifest.py")
    mod = _il_util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.LEADS


# scripts/226 writes the description as either
#   "...priority N. tags=a,b,c. https://t.me/.../<id> (date, mime). caption: '...'"
# or, when a curated lead note exists (script 225 LEADS dict), the lead note's
# own prose REPLACES the "tags=..." segment entirely:
#   "...priority N. <lead note text>. https://t.me/.../<id> (date, mime). caption: '...'"
DESC_RX = re.compile(
    r"priority (\d+)\. (.+?)\. https://t\.me/mariupol_nash/(\d+) "
    r"\(([\d\-]+), ([\w/]+)\)\. caption: '(.*)'\s*$",
    re.S,
)


def _slugify(s: str) -> str:
    s = re.sub(r"[«»\"']", "", s)
    s = re.sub(r"[^\w\-]+", "_", s, flags=re.U)
    return s.strip("_")[:60] or "untagged"


def _ext_for(mime: str) -> str:
    return {"image/jpeg": ".jpg", "image/png": ".png", "video/mp4": ".mp4",
            "video/quicktime": ".mov"}.get(mime, "")


def main() -> None:
    leads = _load_leads()
    con = forensics.open_state()
    rows = con.execute(
        "SELECT url, raw_path, description, sha256 FROM source_document WHERE source_type=? ORDER BY url",
        (SOURCE_TYPE,),
    ).fetchall()
    log.info("indexing %d captured %s files", len(rows), SOURCE_TYPE)

    # reconcile against the manifest
    manifest_ids = set()
    manifest_by_id = {}
    if MANIFEST.exists():
        for line in MANIFEST.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            manifest_ids.add(row["msg_id"])
            manifest_by_id[row["msg_id"]] = row
    else:
        log.warning("manifest not found at %s — skipping reconciliation", MANIFEST)

    captured_ids = set()
    OUT_INDEX.parent.mkdir(parents=True, exist_ok=True)
    fh = OUT_INDEX.open("w", encoding="utf-8")

    priority_counts: Counter = Counter()
    tag_counts: Counter = Counter()
    lead_hits = []
    n_written = 0
    n_missing_raw = 0

    if EXPORT_DIR.exists():
        import shutil
        shutil.rmtree(EXPORT_DIR)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    for url, raw_path, description, sha256 in rows:
        m = DESC_RX.search(description or "")
        if not m:
            log.debug("description didn't match expected shape: %s", (description or "")[:120])
            continue
        priority = int(m.group(1))
        note_or_tags = (m.group(2) or "").strip()
        msg_id = m.group(3)
        date = m.group(4)
        mime = m.group(5)
        caption = m.group(6)

        captured_ids.add(msg_id)
        # authoritative source is scripts/225's own LEADS dict (re-imported
        # above); note_or_tags is "tags=a,b,c" unless a lead note replaced it
        lead_note = leads.get(msg_id)
        manifest_row = manifest_by_id.get(msg_id, {})
        tags = manifest_row.get("tags") or (
            note_or_tags[len("tags="):].split(",") if note_or_tags.startswith("tags=") else [])
        for t in tags:
            tag_counts[t] += 1
        priority_counts[priority] += 1

        rec = {
            "msg_id": msg_id, "url": f"https://t.me/mariupol_nash/{msg_id}",
            "date": date, "priority": priority, "tags": tags,
            "lead_note": lead_note, "mime": mime, "caption": caption[:400],
            "raw_path": raw_path, "sha256": sha256,
        }
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        n_written += 1
        if lead_note:
            lead_hits.append(rec)

        # symlinked browse tree
        src = Path(raw_path)
        if not src.exists():
            n_missing_raw += 1
            continue
        bucket = _slugify(lead_note) if lead_note else _slugify(tags[0] if tags else "untagged")
        dest_dir = EXPORT_DIR / f"P{priority}" / bucket
        dest_dir.mkdir(parents=True, exist_ok=True)
        ext = _ext_for(mime) or src.suffix
        dest = dest_dir / f"{date}_{msg_id}{ext}"
        if not dest.exists():
            dest.symlink_to(src)
        cap_file = dest_dir / f"{date}_{msg_id}{ext}.caption.txt"
        if not cap_file.exists():
            cap_file.write_text(
                f"https://t.me/mariupol_nash/{msg_id}\n"
                f"date: {date}   priority: P{priority}   tags: {', '.join(tags)}\n"
                f"lead: {lead_note or '(none)'}\n\n{caption}\n",
                encoding="utf-8")

    fh.close()

    # scripts/226 defaults to --max-priority 2, so P3 manifest targets are
    # OUT OF SCOPE by design, not "missing" — reconcile only against what a
    # default-scope pull was actually asked to fetch (P1+P2), and report P3
    # separately as "available for a future --max-priority 3 run."
    in_scope_ids = {mid for mid, row in manifest_by_id.items() if row.get("pull_priority", 3) <= 2}
    out_of_scope_ids = manifest_ids - in_scope_ids
    missing_from_pull = sorted(in_scope_ids - captured_ids)

    print(f"\n{'='*72}")
    print(f"@mariupol_nash MEDIA REVIEW INDEX — {n_written} captured files indexed")
    print(f"{'='*72}")
    print(f"\n── by priority ──")
    for p, c in sorted(priority_counts.items()):
        print(f"  P{p}  {c}")
    print(f"\n── by tag (top 20) ──")
    for t, c in tag_counts.most_common(20):
        print(f"  {t:22s} {c}")
    print(f"\n── curated-lead media captured ── {len(lead_hits)}")
    for r in sorted(lead_hits, key=lambda r: r["date"]):
        print(f"  {r['date']}  msg {r['msg_id']}  {r['lead_note'][:70]}")

    print(f"\n── reconciliation vs manifest ──")
    print(f"  in-scope targets (P1+P2, default --max-priority 2): {len(in_scope_ids)}   "
          f"captured (unique msg_id): {len(captured_ids)}")
    print(f"  out-of-scope (P3, not requested at default priority): {len(out_of_scope_ids)} "
          f"— re-run scripts/226 with --max-priority 3 to include these")
    if missing_from_pull:
        print(f"  {len(missing_from_pull)} IN-SCOPE targets NEVER CAPTURED "
              f"(message likely deleted/edited between manifest-build and pull, "
              f"media type changed, or two messages shared identical photo bytes "
              f"and collapsed onto one already-captured file): "
              f"{', '.join(missing_from_pull[:30])}"
              + (" ..." if len(missing_from_pull) > 30 else ""))
    else:
        print("  all in-scope (P1+P2) manifest targets accounted for")
    if n_missing_raw:
        print(f"  WARNING: {n_missing_raw} indexed rows point at a raw_path that "
              f"no longer exists on disk")

    print(f"\n  Index      → {OUT_INDEX}")
    print(f"  Browse at  → {EXPORT_DIR}  (symlinks into data/raw/, organized "
          f"by priority then lead/tag, each with a .caption.txt sidecar)")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
