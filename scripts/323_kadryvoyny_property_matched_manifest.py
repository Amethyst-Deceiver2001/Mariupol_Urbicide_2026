#!/usr/bin/env python3
"""Address-match-driven media manifest for @kadryVoynyMariypol2022 --
the scripts/309 pattern (built for @mariupolRIP), applied here after
scripts/318's generic seizure-policy signal taxonomy (built for the
@mariupol_nash admin/policy channel) turned out to be the wrong lens for
this channel.

@kadryVoynyMariypol2022 ("Кадры войны, Мариуполь 2022") is a war-footage/
casualty documentation channel: most of its address-bearing content is
either a named-victim record ("Известные имена погибших..." + address) or a
photo/video caption naming a street directly. Neither shape reliably
contains bezkhoz/ownerless/зхк-style policy language, so scripts/318's
manifest (161 targets, almost entirely dated-photo captions with no
address) missed the channel's real evidentiary content: found by direct
inspection (2026-07-15) -- 183 address mentions across the 843-message text
corpus resolve to a spine property_id, and 121 of those messages carry
media that scripts/319's pull (against the 318 manifest) never fetched.

Read-only, local, no network -- reads the already-captured
"telegram_kadryvoyny_msg" raw store + Postgres (for address matching),
writes:

  1. data/parsed/kadryvoyny_property_matched.jsonl -- every address mention
     that resolved to a spine property_id, with media kind/size and whether
     it's already been pulled.
  2. data/parsed/kadryvoyny_property_matched_manifest.jsonl -- the subset
     carrying UN-pulled media, ready for scripts/319 to fetch
     (--manifest data/parsed/kadryvoyny_property_matched_manifest.jsonl).
  3. console summary, with the Зелинского/Бахчиванджи cluster addresses
     (docs/case_studies/death_sites_new_construction.md Case 2) called out
     separately since several turned up here as NEW named-victim leads.

Run (safe, read-only):
    PYTHONPATH=src python scripts/323_kadryvoyny_property_matched_manifest.py
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

import psycopg2
import psycopg2.extras

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402
from mariupol_seizures.normalize.address import address_to_building_key  # noqa: E402

log = logging.getLogger(__name__)

SOURCE_TYPE = "telegram_kadryvoyny_msg"
MEDIA_SOURCE_TYPE = "telegram_kadryvoyny_media"
OUT_FLAGGED = ROOT / "data" / "parsed" / "kadryvoyny_property_matched.jsonl"
OUT_MANIFEST = ROOT / "data" / "parsed" / "kadryvoyny_property_matched_manifest.jsonl"

ZELINSKOGO_CLUSTER_PIDS = {
    4837, 4841, 4838, 10640, 4778,   # 17А/19Б/17Б/Бахчиванджи 27/25 -- crosswalk entries
    4844, 4845, 4836, 4835, 4871, 7230, 4776, 4773, 4774,  # other Зелинского/Бахчиванджи addresses
}

# same TYPED_RE shape as scripts/309/304 -- but crucially captures the
# street-TYPE word itself (group 1) so address_to_building_key()'s
# classify_street() can recognize the class (STREET/AVENUE/BOULEVARD/...);
# scripts/309's own TYPED_RE drops the type word, which is fine there
# because it re-derives class via stem_to_classes fallback, but this
# channel's captions are short enough that a direct classify is more
# reliable and worth getting right explicitly here.
STREET_TYPE = (
    r"(ул\.?|улица|пр-?кт\.?|просп\.?|проспект|б-р|бул\.?|бульвар|"
    r"пер\.?|переулок|пл\.?|площадь|наб\.?|набережная|проезд|шоссе)"
)
TYPED_RE = re.compile(
    rf"{STREET_TYPE}\.?\s+([а-яёА-ЯЁ][а-яёА-ЯЁ\-\s]{{2,25}}?)[,\s\.]+(?:д\.?\s*)?(\d+[а-яА-Я]?)\b",
    re.IGNORECASE,
)


def _media_info(obj) -> tuple[str, int | None]:
    m = obj.get("media")
    if not m:
        return "none", None
    t = m.get("_")
    if t == "MessageMediaPhoto":
        return "photo", None
    if t == "MessageMediaDocument":
        doc = m.get("document") or {}
        mime = (doc.get("mime_type") or "")
        size = doc.get("size")
        if mime.startswith("video/"):
            return "video", size
        if mime.startswith("audio/"):
            return "audio", size
        return "document", size
    if t == "MessageMediaWebPage":
        return "webpage", None
    return t.replace("MessageMedia", "").lower() if t else "none", None


def main() -> None:
    con_state = sqlite3.connect(config.STATE_DB)
    rows = con_state.execute(
        "SELECT url, raw_path FROM source_document WHERE source_type=? ORDER BY url",
        (SOURCE_TYPE,),
    ).fetchall()
    if not rows:
        log.error("no %s rows found — run scripts/317 first", SOURCE_TYPE)
        sys.exit(1)
    pulled_urls = {u.replace("/media", "") for (u,) in con_state.execute(
        "SELECT url FROM source_document WHERE source_type=?", (MEDIA_SOURCE_TYPE,)
    ).fetchall()}
    log.info("scanning %d %s messages (%d media already pulled)",
             len(rows), SOURCE_TYPE, len(pulled_urls))

    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("select id, building_id, prewar_address, occupation_address from property where building_id is not null")
    all_props = cur.fetchall()
    by_key = {r["building_id"]: r for r in all_props}
    log.info("loaded %d property building_id keys for matching", len(by_key))

    OUT_FLAGGED.parent.mkdir(parents=True, exist_ok=True)
    fh = OUT_FLAGGED.open("w", encoding="utf-8")
    mh = OUT_MANIFEST.open("w", encoding="utf-8")

    media_counts: Counter = Counter()
    n_msg = n_match = n_unpulled = n_cluster = 0
    cluster_hits = []

    for url, raw_path in rows:
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
        n_msg += 1

        msg_id = url.rstrip("/").rsplit("/", 1)[-1]
        text = (obj.get("message") or "").strip()
        date = (obj.get("date") or "")[:10]
        if not text:
            continue

        media_kind, media_size = _media_info(obj)

        seen_pids = set()
        for m in TYPED_RE.finditer(text):
            prefix, stem, house = m.group(1), m.group(2).strip(), m.group(3).strip()
            street_raw = f"{prefix} {stem}"
            key = address_to_building_key(street_raw, house)
            prop = by_key.get(key) if key else None
            if not prop or prop["id"] in seen_pids:
                continue
            seen_pids.add(prop["id"])
            n_match += 1
            already_pulled = url in pulled_urls
            has_media = media_kind != "none"
            is_cluster = prop["id"] in ZELINSKOGO_CLUSTER_PIDS
            if is_cluster:
                n_cluster += 1
                cluster_hits.append((msg_id, url, street_raw, house, prop["id"], date, text[:200]))

            rec = {
                "msg_id": msg_id, "url": url, "date": date,
                "matched_street": street_raw, "matched_house": house,
                "property_id": prop["id"], "matched_building_id": prop["building_id"],
                "zelinskogo_cluster": is_cluster,
                "media_kind": media_kind, "media_size_bytes": media_size,
                "already_pulled": already_pulled,
                "text": text[:400],
            }
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            media_counts[media_kind] += 1

            if has_media and not already_pulled:
                n_unpulled += 1
                priority = 1 if is_cluster else 2
                mh.write(json.dumps({
                    "msg_id": msg_id, "url": url, "date": date,
                    "media_kind": media_kind, "media_size_bytes": media_size,
                    "pull_priority": priority,
                    "tags": ["property_matched"] + (["zelinskogo_cluster"] if is_cluster else []),
                    "lead_note": f"property_id={prop['id']} address={street_raw} {house}",
                }, ensure_ascii=False) + "\n")

    fh.close()
    mh.close()
    con.close()

    print(f"\n{'='*72}")
    print(f"@kadryVoynyMariypol2022 PROPERTY-MATCH MANIFEST — {n_msg} messages scanned")
    print(f"{'='*72}")
    print(f"\n  {n_match} address mentions matched to a spine property_id")
    print(f"  {n_unpulled} of those carry media NOT yet pulled -> written to manifest")
    print("\n── media on matched messages ──")
    for k, c in media_counts.most_common():
        print(f"  {k:12s} {c}")
    print(f"\n── Зелинского/Бахчиванджи cluster hits ── {n_cluster}")
    for h in cluster_hits:
        print(f"  msg {h[0]:>6s}  {h[2]} {h[3]}  pid={h[4]}  {h[5]}  {h[6][:80]!r}")
    print(f"\n  Flagged  → {OUT_FLAGGED}")
    print(f"  Manifest → {OUT_MANIFEST}")
    print(f"\n  Next: .venv312/bin/python scripts/319_pull_kadryvoyny_flagged_media.py "
          f"--manifest {OUT_MANIFEST} --max-priority 2")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
