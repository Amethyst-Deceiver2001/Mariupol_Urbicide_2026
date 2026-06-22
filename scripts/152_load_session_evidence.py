#!/usr/bin/env python3
"""Load this session's new evidence into the PostgreSQL spine.

Three independent local JSONL outputs from scripts 148-151 carry evidence that
isn't in the DB yet:

  1. ownerless_differential_records.jsonl (script 150) -- per-apartment
     disposition/disappearance findings against the current ownerless
     registry. Loaded as `corroboration` rows (kind='ownerless_disposition')
     ONLY for apartments whose building already has a property row (matched
     by building_id=building_key). Rows whose building has no existing
     property are skipped here and left in the gap register
     (data/parsed/gap_register_undocumented_disappearance.csv) -- per CLAUDE.md
     "rather miss a match than collide", we do not fabricate new property
     rows from a derived building_key string; that's the address loader's
     job (scripts 21/27/28), not this one.
  2. deep_intel_summary.json (script 148) -- legal citations (Указ/Постановление
     /Распоряжение/Закон/ГКО + number) residents cite in chat, with one
     example message per citation. Loaded as `corroboration` rows
     (kind='cited_legal_instrument') NOT attached to any property (these are
     city/republic-wide instruments, not building-specific) -- attached to
     property_id NULL, for the legal-mechanisms review to pick up.
  3. media_lifecycle_manifest.jsonl (script 151) -- classified photo/video
     buckets per chat. Loaded as `corroboration` rows (kind='lifecycle_media')
     attached to a property ONLY when the chat's building title resolves to
     an existing building_id via address_to_building_key (best-effort parse
     of the often free-text title, e.g. "Мира 111" / "Морской 20"). Chats
     whose title doesn't parse to a clean street+house stay unattached
     (property_id NULL) but are still loaded -- the manifest URL/sha is the
     citable evidence either way.

Idempotent: every row carries a dedup_key, INSERT ... ON CONFLICT DO NOTHING
against corroboration_dedup_uidx. Safe to re-run after re-running 148-151.

PRIVACY: no owner data touched. These are occupation-administration records
and residents' own public chat messages about process events, not owner PII.

Run:
    PYTHONPATH=src python scripts/152_load_session_evidence.py
    PYTHONPATH=src python scripts/152_load_session_evidence.py --dry-run
"""
import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402
from mariupol_seizures.db.load import _upsert_source_doc_by_sha  # noqa: E402
from mariupol_seizures.normalize.address import address_to_building_key  # noqa: E402
from mariupol_seizures.chat_buildings import CHAT_PIDS, CHAT_STREET_HOUSES  # noqa: E402

log = logging.getLogger(__name__)

DIFF_RECORDS = ROOT / "data" / "parsed" / "ownerless_differential_records.jsonl"
INTEL_SUMMARY = ROOT / "data" / "parsed" / "deep_intel_summary.json"
MEDIA_MANIFEST = ROOT / "data" / "parsed" / "media_lifecycle_manifest.jsonl"


def _property_id_for_building(cur, building_key: str | None):
    if not building_key:
        return None
    cur.execute("SELECT id FROM property WHERE building_id = %s", (building_key,))
    row = cur.fetchone()
    return row[0] if row else None


def load_differential(cur, dry_run: bool) -> dict:
    if not DIFF_RECORDS.exists():
        log.warning("missing %s -- run script 150 first", DIFF_RECORDS)
        return {"loaded": 0, "skipped_no_property": 0}
    n_loaded = n_skip = 0
    for line in DIFF_RECORDS.open(encoding="utf-8"):
        d = json.loads(line)
        pid = _property_id_for_building(cur, d.get("building_key"))
        if pid is None:
            n_skip += 1
            continue
        sha = d.get("source_sha256")
        source_doc_id = None if dry_run else _upsert_source_doc_by_sha(cur, sha)
        dedup_key = (f"ownerless_disposition:{sha}:{d.get('building_key')}:"
                     f"{d.get('apt') or ''}")
        detail = {
            "marker_class": d.get("marker_class"),
            "classification": d.get("classification"),
            "snapshot": d.get("snapshot"), "snapshot_date": d.get("snapshot_date"),
            "district": d.get("district"), "street": d.get("street"),
            "house": d.get("house"), "apt": d.get("apt"),
            "spine_stages": d.get("spine_stages"),
        }
        verdict = ("confirms" if d.get("classification") in
                   ("seized_municipal", "seized_court", "returned_to_claimant")
                   else "indeterminate")
        if not dry_run:
            cur.execute(
                """INSERT INTO corroboration
                       (property_id, kind, reference, detail, dedup_key,
                        captured_at, source_doc_id, confidence, verdict)
                   VALUES (%s, 'ownerless_disposition', %s, %s, %s, now(),
                           %s, %s, %s)
                   ON CONFLICT (dedup_key) DO UPDATE SET
                       property_id = EXCLUDED.property_id,
                       detail = EXCLUDED.detail,
                       source_doc_id = EXCLUDED.source_doc_id,
                       verdict = EXCLUDED.verdict""",
                (pid, d.get("snapshot"), json.dumps(detail, ensure_ascii=False),
                 dedup_key, source_doc_id, 0.9, verdict),
            )
        n_loaded += 1
    return {"loaded": n_loaded, "skipped_no_property": n_skip}


def load_legal_citations(cur, dry_run: bool) -> dict:
    if not INTEL_SUMMARY.exists():
        log.warning("missing %s -- run script 148 first", INTEL_SUMMARY)
        return {"loaded": 0}
    summary = json.loads(INTEL_SUMMARY.read_text(encoding="utf-8"))
    n_loaded = 0
    for key, info in summary.get("legal_citations", {}).items():
        dedup_key = f"cited_legal_instrument:{key}"
        detail = {
            "citation": key, "hits": info.get("hits"),
            "first_seen_chat": info.get("chat"), "first_seen_date": info.get("date"),
            "context": info.get("ctx"),
        }
        if not dry_run:
            cur.execute(
                """INSERT INTO corroboration
                       (property_id, kind, reference, detail, dedup_key,
                        captured_at, confidence, verdict)
                   VALUES (NULL, 'cited_legal_instrument', %s, %s, %s, now(),
                           %s, 'indeterminate')
                   ON CONFLICT (dedup_key) DO NOTHING""",
                (key, json.dumps(detail, ensure_ascii=False), dedup_key,
                 min(1.0, 0.5 + 0.05 * info.get("hits", 1))),
            )
        n_loaded += 1
    return {"loaded": n_loaded}


def _resolve_chat_pid_and_buildings(cur, chat: str, title: str):
    """Resolve a chat to (primary_property_id, [building_keys]) using the
    verified chat_buildings table first; free-text title guess is the
    fallback of last resort, same priority as script 153's resolver."""
    if chat in CHAT_PIDS:
        pids = CHAT_PIDS[chat]
        if not pids:
            return None, []
        cur.execute("SELECT id, building_id FROM property WHERE id = ANY(%s)", (pids,))
        rows = cur.fetchall()
        bks = sorted({bk for _, bk in rows if bk})
        return (rows[0][0] if rows else None), bks
    if chat in CHAT_STREET_HOUSES:
        street, houses = CHAT_STREET_HOUSES[chat]
        bks, pid = [], None
        for h in houses:
            bk = address_to_building_key(street, h)
            if not bk:
                continue
            bks.append(bk)
            p = _property_id_for_building(cur, bk)
            if p is not None and pid is None:
                pid = p
        return pid, bks
    bk = address_to_building_key(title, None)
    if not bk:
        import re
        m = re.search(r"([А-ЯЁа-яё .]+?)\s+(\d+[\/\-]?\d*[а-яёА-ЯЁ]?)\b", title)
        if m:
            bk = address_to_building_key(m.group(1), m.group(2))
    if not bk:
        return None, []
    return _property_id_for_building(cur, bk), [bk]


def load_media(cur, dry_run: bool) -> dict:
    if not MEDIA_MANIFEST.exists():
        log.warning("missing %s -- run script 151 first", MEDIA_MANIFEST)
        return {"loaded": 0, "attached_to_property": 0}
    n_loaded = n_attached = 0
    for line in MEDIA_MANIFEST.open(encoding="utf-8"):
        d = json.loads(line)
        if d["stage"] == "unclassified":
            continue
        pid, bks = _resolve_chat_pid_and_buildings(cur, d["chat"], d["building_title"])
        if pid is not None:
            n_attached += 1
        dedup_key = f"lifecycle_media:{d['chat']}:{d['stage']}"
        detail = {
            "chat": d["chat"], "building_title": d["building_title"],
            "building_keys": bks,
            "stage": d["stage"], "n_items": d["n_items"],
            "date_range": d["date_range"],
            "sample_urls": [it["url"] for it in d["items"][:5]],
            "sample_shas": [it["sha256"] for it in d["items"][:5]],
        }
        if not dry_run:
            cur.execute(
                """INSERT INTO corroboration
                       (property_id, kind, reference, detail, dedup_key,
                        captured_at, confidence, verdict,
                        observed_start, observed_end)
                   VALUES (%s, 'lifecycle_media', %s, %s, %s, now(),
                           0.7, 'confirms', %s, %s)
                   ON CONFLICT (dedup_key) DO UPDATE SET
                       property_id = EXCLUDED.property_id,
                       detail = EXCLUDED.detail,
                       observed_start = EXCLUDED.observed_start,
                       observed_end = EXCLUDED.observed_end""",
                (pid, d["chat"], json.dumps(detail, ensure_ascii=False), dedup_key,
                 d["date_range"][0] if d["date_range"] else None,
                 d["date_range"][1] if d["date_range"] else None),
            )
        n_loaded += 1
    return {"loaded": n_loaded, "attached_to_property": n_attached}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                     help="parse + report counts without writing to the DB")
    args = ap.parse_args()

    import psycopg2
    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()

    r1 = load_differential(cur, args.dry_run)
    r2 = load_legal_citations(cur, args.dry_run)
    r3 = load_media(cur, args.dry_run)

    if args.dry_run:
        con.rollback()
    else:
        con.commit()
    con.close()

    print(f"\n{'='*64}")
    print(f"SESSION EVIDENCE LOAD {'(DRY RUN -- nothing written)' if args.dry_run else ''}")
    print(f"{'='*64}")
    print(f"  ownerless_disposition : {r1['loaded']:6d} loaded   "
          f"{r1['skipped_no_property']:6d} skipped (no matching property)")
    print(f"  cited_legal_instrument: {r2['loaded']:6d} loaded   (property_id NULL -- republic-wide)")
    print(f"  lifecycle_media       : {r3['loaded']:6d} loaded   "
          f"{r3['attached_to_property']:6d} attached to a property")
    print()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
