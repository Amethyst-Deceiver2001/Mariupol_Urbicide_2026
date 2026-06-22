#!/usr/bin/env python3
"""Build a per-building media lifecycle manifest from all captured chat photos/videos.

Part 4 of this session's deep-analysis program: "collect all media showing
specific buildings at specific points in their lifecycle -- intact, damaged by
war, in process of demolition or an already cleared lot, new construction
sites on the same spot and finally new buildings."

For every photo/video posted in the 28 building chats, this script:
  1. Recovers the building's display name from the channel's own service
     message (MessageActionChannelMigrateFrom / ChannelCreate title at msg
     id=1) -- the same recovery every per-chat parser (135-147) already uses,
     done generically here so this script needs no per-chat PIDS import.
  2. Classifies the media's lifecycle stage from the parent message's caption
     + (when the photo itself has no caption) the nearest preceding captioned
     message in the same chat within a short time window -- captions often
     land on a *different* message than the photo in these chats.
  3. Buckets into one manifest entry per (chat, stage), with the full
     chronological media list inside, so a reviewer can see the building's
     visual progression end-to-end and spot missing stages (the gaps are as
     informative as the hits).

Lifecycle stages (first match wins, in lifecycle order so an ambiguous
caption resolves to the most-specific/late stage mentioned):
  new_build        - new building completed / handed over / move-in
  construction      - crane, foundation pour, fence around a cleared site, builders
  cleared_lot       - rubble removed, site cleared, empty lot
  demolition        - снос / демонтаж in progress
  siege_damage      - shelling, fire, destruction (2022 siege era)
  resident_presence - normal life continuing (baseline "intact" signal)
  unclassified       - photo/video with no resolvable caption signal

Pure local analysis over the forensic store (no network). Safe to run.

Outputs:
  data/parsed/media_lifecycle_manifest.jsonl  -- one row per (chat, stage)
        bucket, with the ordered list of media items
  data/parsed/media_lifecycle_summary.json    -- per-building stage coverage
  console report highlighting buildings with full vs partial lifecycle coverage

Run:
    PYTHONPATH=src python scripts/151_media_lifecycle_manifest.py
"""
import json
import logging
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import forensics  # noqa: E402

log = logging.getLogger(__name__)

OUT_MANIFEST = ROOT / "data" / "parsed" / "media_lifecycle_manifest.jsonl"
OUT_SUMMARY = ROOT / "data" / "parsed" / "media_lifecycle_summary.json"

# caption -> nearest-preceding-caption search window (captions often land on
# the message right before/after the photo in these chats, not on it)
CAPTION_SEARCH_WINDOW = 3  # messages either side

# ── lifecycle classifiers, in resolution priority order (latest stage wins
# when multiple match, since a caption like "снесли, теперь стройка" should
# resolve to the more specific/later stage) ─────────────────────────────────
STAGES = [
    ("new_build", re.compile(
        r"новый дом готов|сдали дом|сдан в эксплуатаци|заселя|новосёл|"
        r"новоселье|ввод[а-я]* в эксплуатаци|дом построен|открыт[а-я]* дом",
        re.I)),
    ("construction", re.compile(
        r"стройк|строител[ьи]|застройщик|кран стоит|кран\b|залива[а-я]*\s*фундамент|"
        r"фундамент|плиты везут|забор поставили|огородили забором|новостройк|"
        r"котлован|свайн|опалубк", re.I)),
    ("cleared_lot", re.compile(
        r"расчист[а-я]*\s*(участок|площадк|территори)|вывезли мусор|убрали завал|"
        r"пустой участок|пустырь|расчищенн|вывоз\s*мусора|разобрали завал",
        re.I)),
    ("demolition", re.compile(
        r"\bснос\w*|демонтаж|сносят|снесл|снесут|разбира[а-я]*\s*здани|"
        r"экскаватор\w*\s*ломает|техника снос", re.I)),
    ("siege_damage", re.compile(
        r"обстрел|прилёт|прилет|снаряд|ракет|разрушен|сгорел|пожар|выгорел|"
        r"бомбёжк|бомбежк|воронк|осколк|пробит\w*\s*стен", re.I)),
    ("resident_presence", re.compile(
        r"живём|живем|жильцы|жители|сосед|наша квартира|дом стоит|дом цел|"
        r"мы живём|мы живем|люди живут", re.I)),
]


def _slug_of(url: str) -> str:
    parts = url.split("/")
    return parts[3] if len(parts) >= 5 else "?"


def _msg_id_of(url: str) -> int | None:
    parts = url.rstrip("/").split("/")
    try:
        return int(parts[-1])
    except (ValueError, IndexError):
        return None


def _classify(text: str) -> str | None:
    if not text:
        return None
    hit = None
    for stage, rx in STAGES:
        if rx.search(text):
            hit = stage  # keep overwriting -- later entries in STAGES are later-lifecycle
    return hit


def _building_title(con, slug: str) -> str:
    """Recover the channel's display name from its own migration/creation
    service message (msg id=1), the same recovery scripts 135-147 use."""
    row = con.execute(
        "SELECT raw_path FROM source_document WHERE source_type='telegram_building_chat_msg' "
        "AND url=?", (f"https://t.me/{slug}/1",)
    ).fetchone()
    if not row:
        return slug
    try:
        obj = json.loads((ROOT / row[0]).read_bytes())
        action = obj.get("action") or {}
        title = action.get("title")
        if title:
            return title
    except Exception:
        pass
    return slug


def main() -> None:
    con = forensics.open_state()

    # load every chat message (for caption lookup + ordering) keyed by (slug, msg_id)
    log.info("loading all chat messages for caption context...")
    msg_rows = con.execute(
        "SELECT url, raw_path FROM source_document "
        "WHERE source_type='telegram_building_chat_msg' ORDER BY url"
    ).fetchall()
    by_chat: dict[str, dict[int, dict]] = defaultdict(dict)
    for url, raw_path in msg_rows:
        if not raw_path:
            continue
        p = ROOT / raw_path
        if not p.exists():
            continue
        try:
            obj = json.loads(p.read_bytes())
        except Exception:
            continue
        if obj.get("_") != "Message":
            continue
        mid = obj.get("id")
        if mid is None:
            continue
        slug = _slug_of(url)
        by_chat[slug][mid] = {
            "text": (obj.get("message") or "").strip(),
            "date": obj.get("date") or "",
        }
    log.info("indexed %d chats, %d total messages", len(by_chat),
              sum(len(v) for v in by_chat.values()))

    titles = {slug: _building_title(con, slug) for slug in by_chat}

    # media rows
    media_rows = con.execute(
        "SELECT url, content_type, raw_path, sha256 FROM source_document "
        "WHERE source_type='telegram_building_chat_media' ORDER BY url"
    ).fetchall()
    log.info("found %d media items", len(media_rows))

    # bucket: (slug, stage) -> list of items
    buckets: dict[tuple, list] = defaultdict(list)
    n_classified = n_total = 0

    for url, ct, raw_path, sha in media_rows:
        n_total += 1
        parent_url = url.replace("/media", "")
        slug = _slug_of(parent_url)
        mid = _msg_id_of(parent_url)
        chat_msgs = by_chat.get(slug, {})
        parent = chat_msgs.get(mid) if mid is not None else None
        if parent is None:
            continue

        caption = parent["text"]
        date = parent["date"][:10]
        stage = _classify(caption)

        # caption-less photo: search nearby messages for context
        used_mid = mid
        if not stage and mid is not None:
            for delta in range(1, CAPTION_SEARCH_WINDOW + 1):
                for cand_mid in (mid - delta, mid + delta):
                    cand = chat_msgs.get(cand_mid)
                    if cand and cand["text"]:
                        s = _classify(cand["text"])
                        if s:
                            stage, caption, used_mid = s, cand["text"], cand_mid
                            break
                if stage:
                    break

        stage = stage or "unclassified"
        if stage != "unclassified":
            n_classified += 1

        kind = "video" if "video" in (ct or "") else (
            "image" if "image" in (ct or "") else "other")

        buckets[(slug, stage)].append({
            "url": url, "date": date, "kind": kind, "sha256": sha,
            "caption_excerpt": caption[:200] if caption else None,
            "caption_msg_id": used_mid,
        })

    # ── write manifest ──────────────────────────────────────────────────────
    OUT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    manifest_rows = []
    for (slug, stage), items in buckets.items():
        items.sort(key=lambda x: x["date"])
        manifest_rows.append({
            "chat": slug, "building_title": titles.get(slug, slug),
            "stage": stage, "n_items": len(items),
            "date_range": [items[0]["date"], items[-1]["date"]] if items else None,
            "items": items,
        })
    manifest_rows.sort(key=lambda r: (r["building_title"], r["stage"]))
    with OUT_MANIFEST.open("w", encoding="utf-8") as fh:
        for r in manifest_rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    # per-building stage coverage
    coverage: dict[str, dict] = {}
    stage_order = [s for s, _ in STAGES] + ["unclassified"]
    for slug, title in titles.items():
        stages_present = sorted(
            {st for (sl, st) in buckets if sl == slug},
            key=lambda s: stage_order.index(s) if s in stage_order else 99,
        )
        coverage[slug] = {
            "building_title": title,
            "stages_present": stages_present,
            "n_stages": len([s for s in stages_present if s != "unclassified"]),
            "total_media": sum(len(v) for (sl, st), v in buckets.items() if sl == slug),
        }
    summary = {
        "total_media": n_total, "classified": n_classified,
        "unclassified": n_total - n_classified,
        "buildings": coverage,
    }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                           encoding="utf-8")

    # ── console report ──────────────────────────────────────────────────────
    print(f"\n{'='*78}")
    print(f"MEDIA LIFECYCLE MANIFEST — {n_total} media items, "
          f"{n_classified} classified ({100*n_classified/max(1,n_total):.1f}%)")
    print(f"{'='*78}")

    print("\n── PER-BUILDING LIFECYCLE COVERAGE (most stages first) ──")
    for slug, c in sorted(coverage.items(), key=lambda x: -x[1]["n_stages"]):
        stages_disp = ",".join(c["stages_present"]) or "(no media)"
        print(f"  {c['building_title'][:36]:36s}  {c['n_stages']}/6 stages  "
              f"{c['total_media']:4d} media  [{stages_disp}]")

    print("\n── BUCKETS (chat × stage, with item counts + date span) ──")
    for r in manifest_rows:
        if r["stage"] == "unclassified":
            continue
        print(f"  {r['building_title'][:30]:30s}  {r['stage']:18s}  "
              f"{r['n_items']:4d} items  {r['date_range'][0]} → {r['date_range'][1]}")

    print("\n── BUILDINGS WITH FULL DEMOLISH→REBUILD ARC "
          "(demolition + construction/new_build both present) ──")
    for slug, c in coverage.items():
        sp = set(c["stages_present"])
        if "demolition" in sp and ({"construction", "new_build"} & sp):
            print(f"  {c['building_title']}  [{', '.join(sorted(sp))}]")

    print(f"\n  Manifest → {OUT_MANIFEST}  ({len(manifest_rows)} buckets)")
    print(f"  Summary  → {OUT_SUMMARY}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
