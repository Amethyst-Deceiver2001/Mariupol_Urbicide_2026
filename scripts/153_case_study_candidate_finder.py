#!/usr/bin/env python3
"""Find buildings with the strongest end-to-end, multi-source corroborated
lifecycle -- the candidates worth writing up as a case study like
docs/case_studies/nakhimova_82_chernomorsky_1b.md.

A building scores well when it has BOTH:
  - a visual arc (script 151 media manifest: siege_damage -> demolition ->
    construction/new_build, with dated, hashed photos/videos), AND
  - a documentary chain in the DB (seizure_event stages: demolition,
    reallocation, registry_inclusion, court_transfer) and/or an explicit
    occupation-admission disposition (script 150: municipal_seized /
    seized_court), AND, ideally,
  - a captured primary-source decree/court-ruling document (script 149
    inventory) whose text mentions the same street -- weak signal (substring
    match on street name), included as a lead to verify, not as proof.

This is a pure cross-reference over already-loaded data (run script 152
first so DB corroboration rows exist) -- no new captures, no DB writes.

Output:
  data/parsed/case_study_candidates.jsonl  -- one row per chat/building,
        ranked by total evidence-leg count, with every matched item's
        sha256/url/date so a case-study writer can cite it directly.
  console report (top 15)

Run:
    PYTHONPATH=src python scripts/153_case_study_candidate_finder.py
"""
import json
import logging
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402
from mariupol_seizures.normalize.address import address_to_building_key  # noqa: E402
from mariupol_seizures.chat_buildings import CHAT_PIDS, CHAT_STREET_HOUSES  # noqa: E402

log = logging.getLogger(__name__)

MEDIA_MANIFEST = ROOT / "data" / "parsed" / "media_lifecycle_manifest.jsonl"
DOC_INVENTORY = ROOT / "data" / "parsed" / "chat_document_inventory.jsonl"
DIFF_RECORDS = ROOT / "data" / "parsed" / "ownerless_differential_records.jsonl"
OUT = ROOT / "data" / "parsed" / "case_study_candidates.jsonl"

DB_STAGE_WEIGHT = {
    "demolition": 1, "reallocation": 1, "registry_inclusion": 1,
    "court_transfer": 1, "ownerless_designation": 1, "court_petition": 0.5,
    "appeal": 0.5, "entered_force": 0.5, "resale": 1,
}
MEDIA_STAGE_ORDER = ["resident_presence", "siege_damage", "demolition",
                     "cleared_lot", "construction", "new_build"]

_STREET_NAME_RE = re.compile(r"([А-ЯЁ][а-яёА-ЯЁ\-]{3,})")


def _building_key_for_title(title: str) -> str | None:
    """Last-resort fallback for chats not in chat_buildings.CHAT_PIDS /
    CHAT_STREET_HOUSES -- guesses from the free-text channel title. Known to
    silently fail or mis-resolve multi-building/abbreviated titles; only used
    when the verified table has nothing for this chat."""
    bk = address_to_building_key(title, None)
    if bk:
        return bk
    m = re.search(r"([А-ЯЁа-яё .]+?)\s+(\d+[\/\-]?\d*[а-яёА-ЯЁ]?)\b", title)
    if m:
        return address_to_building_key(m.group(1), m.group(2))
    return None


def resolve_chat_buildings(chat: str, title: str, cur) -> list[tuple[str, int | None]]:
    """Resolve a chat to its verified (building_key, property_id) pairs.

    Priority: CHAT_PIDS (parser-verified spine pids) > CHAT_STREET_HOUSES
    (parser-documented canonical address) > free-text title guess (fallback
    of last resort, flagged separately by the caller via the empty-pids case
    not applying here)."""
    if chat in CHAT_PIDS:
        pids = CHAT_PIDS[chat]
        if not pids:
            return []
        cur.execute("SELECT id, building_id FROM property WHERE id = ANY(%s)", (pids,))
        return [(bk, pid) for pid, bk in cur.fetchall() if bk]
    if chat in CHAT_STREET_HOUSES:
        street, houses = CHAT_STREET_HOUSES[chat]
        out = []
        for h in houses:
            bk = address_to_building_key(street, h)
            if not bk:
                continue
            cur.execute("SELECT id FROM property WHERE building_id = %s", (bk,))
            row = cur.fetchone()
            out.append((bk, row[0] if row else None))
        return out
    bk = _building_key_for_title(title)
    if not bk:
        return []
    cur.execute("SELECT id FROM property WHERE building_id = %s", (bk,))
    row = cur.fetchone()
    return [(bk, row[0] if row else None)]


def _street_stem(title: str) -> str | None:
    m = _STREET_NAME_RE.search(title)
    return m.group(1).lower() if m else None


def load_media_by_chat():
    by_chat = defaultdict(lambda: {"title": None, "stages": {}})
    if not MEDIA_MANIFEST.exists():
        log.warning("missing %s -- run script 151 first", MEDIA_MANIFEST)
        return by_chat
    for line in MEDIA_MANIFEST.open(encoding="utf-8"):
        d = json.loads(line)
        by_chat[d["chat"]]["title"] = d["building_title"]
        if d["stage"] != "unclassified":
            by_chat[d["chat"]]["stages"][d["stage"]] = {
                "n_items": d["n_items"], "date_range": d["date_range"],
                "sample": d["items"][:3],
            }
    return by_chat


def load_differential_by_building():
    out = defaultdict(list)
    if not DIFF_RECORDS.exists():
        return out
    for line in DIFF_RECORDS.open(encoding="utf-8"):
        d = json.loads(line)
        if d.get("classification") in ("seized_municipal", "seized_court"):
            out[d["building_key"]].append(d)
    return out


def load_doc_leads():
    """street-stem -> list of decree/ruling/planning docs mentioning it."""
    out = defaultdict(list)
    if not DOC_INVENTORY.exists():
        return out
    interesting = {"gko_decree", "admin_postanovlenie", "court_ruling", "planning_ppt"}
    for line in DOC_INVENTORY.open(encoding="utf-8"):
        d = json.loads(line)
        if d["category"] not in interesting:
            continue
        text = ""
        if d.get("text_path"):
            p = ROOT / d["text_path"]
            if p.exists():
                text = p.read_text(encoding="utf-8")[:6000]
        out["__all__"].append({**d, "_text": text})
    return out


def _doc_mentions_street(doc: dict, street_stem: str) -> bool:
    if not street_stem:
        return False
    hay = f"{doc.get('filename') or ''} {doc.get('_text') or ''}".lower()
    return street_stem in hay


def main() -> None:
    media_by_chat = load_media_by_chat()
    diff_by_bk = load_differential_by_building()
    all_docs = load_doc_leads().get("__all__", [])

    db_stages_by_pid = {}
    cur = None
    try:
        import psycopg2
        con = psycopg2.connect(config.DATABASE_URL)
        cur = con.cursor()
        cur.execute("SELECT property_id, stage, event_date FROM seizure_event")
        for pid, stage, edate in cur.fetchall():
            db_stages_by_pid.setdefault(pid, []).append((stage, str(edate) if edate else None))
    except Exception as e:
        log.warning("DB unreachable (%s) -- scoring without DB stages; run script 152 first", e)

    candidates = []
    for chat, info in media_by_chat.items():
        title = info["title"] or chat
        buildings = resolve_chat_buildings(chat, title, cur) if cur else []

        # aggregate evidence across every building this chat actually covers
        stages_db, disposition, seen_pids = [], [], set()
        for bk, pid in buildings:
            disposition.extend(diff_by_bk.get(bk, []))
            if pid:
                seen_pids.add(pid)
                stages_db.extend(db_stages_by_pid.get(pid, []))
        # primary property_id for citation = whichever building has the most
        # seizure_event rows (the best-documented one in a multi-building chat)
        primary_pid = max(seen_pids, key=lambda p: len(db_stages_by_pid.get(p, [])),
                           default=None)
        all_building_keys = sorted({bk for bk, _ in buildings})

        street_stem = _street_stem(title)
        doc_leads = [d for d in all_docs if _doc_mentions_street(d, street_stem)] if street_stem else []

        media_legs = sorted(info["stages"].keys(),
                             key=lambda s: MEDIA_STAGE_ORDER.index(s) if s in MEDIA_STAGE_ORDER else 9)
        db_leg_names = sorted({s for s, _ in stages_db})
        score = (
            len(media_legs) * 2
            + sum(DB_STAGE_WEIGHT.get(s, 0.3) for s in db_leg_names) * 3
            + len(disposition) * 2
            + min(len(doc_leads), 3)
        )
        has_visual_arc = ("demolition" in media_legs and
                           ({"construction", "new_build"} & set(media_legs)))
        has_db_chain = bool({"demolition", "reallocation", "registry_inclusion",
                              "court_transfer"} & set(db_leg_names))

        candidates.append({
            "chat": chat, "building_title": title,
            "building_key": all_building_keys[0] if all_building_keys else None,
            "all_building_keys": all_building_keys,
            "property_id": primary_pid, "all_property_ids": sorted(seen_pids),
            "score": round(score, 1),
            "has_visual_arc": bool(has_visual_arc), "has_db_chain": has_db_chain,
            "media_legs": media_legs, "media_detail": info["stages"],
            "db_stages": stages_db,
            "disposition_evidence": disposition,
            "doc_leads": [{"filename": d["filename"], "category": d["category"],
                           "date": d.get("date"), "sha256": d["sha256"]}
                          for d in doc_leads],
        })

    if cur:
        cur.connection.close()

    candidates.sort(key=lambda c: -c["score"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        for c in candidates:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")

    print(f"\n{'='*78}")
    print(f"CASE STUDY CANDIDATES — {len(candidates)} buildings scored "
          f"({sum(1 for c in candidates if not db_stages_by_pid)} scored without DB -- run 152 first if 0)")
    print(f"{'='*78}")
    print(f"\n  {'score':>5s}  {'visual':6s} {'db':3s} {'disp':4s} {'docs':4s}  building")
    for c in candidates[:20]:
        print(f"  {c['score']:5.1f}  {'arc' if c['has_visual_arc'] else '-':6s} "
              f"{'Y' if c['has_db_chain'] else '-':3s} "
              f"{len(c['disposition_evidence']):4d} {len(c['doc_leads']):4d}  "
              f"{c['building_title'][:40]}  "
              f"(legs: {','.join(c['media_legs'])})")

    print("\n── TOP CANDIDATES WITH FULL VISUAL ARC + DB CHAIN (write-up ready) ──")
    best = [c for c in candidates if c["has_visual_arc"] and c["has_db_chain"]]
    if not best:
        print("  none yet -- run script 152 to load corroboration, or these buildings'")
        print("  demolition/reallocation events simply aren't in the spine yet (see")
        print("  gap_register_undocumented_disappearance.csv for the textual half).")
    for c in best:
        print(f"\n  {c['building_title']}  (property_id={c['property_id']}, score={c['score']})")
        print(f"    media legs: {c['media_legs']}")
        stage_counts = sorted(Counter(s for s, _ in c["db_stages"]).items())
        print(f"    db stages: {stage_counts}  (across pids {c['all_property_ids']})")
        if c["doc_leads"]:
            print(f"    doc leads: {[d['filename'] for d in c['doc_leads']]}")

    print(f"\n  Candidates → {OUT}  ({len(candidates)} rows)")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
