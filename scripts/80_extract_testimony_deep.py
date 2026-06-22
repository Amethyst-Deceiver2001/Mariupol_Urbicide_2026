#!/usr/bin/env python3
"""Deep testimony + media extraction from all captured resident Telegram chats.

Processes three building chats already in the forensics store:
  - @Azovstalskaya31   (script 74) — pid=6259, demolished
  - morskoy_38_36_30   (script 75) — pid=10724, demolished
  - olimpiyskaya_71_79 (script 78) — pids 5171/5034/5172/5173/5174, title-stripping

Outputs:
  data/parsed/testimony_full_all_chats.jsonl
    Full-text testimony records (not truncated) ready for DB corroboration load.
    One record per message that has either text content or media.

  data/parsed/media_manifest_all_chats.csv
    Inventory of all captured media with: chat, date, raw_path, sha256,
    content_type, caption (first 300 chars), parent_msg_url.
    For manual visual triage — sort by date to find siege-era photos.

  Console: evidentiary highlights + apartment cross-reference vs ownerless events.

Cross-reference:
  For the Олимпийская buildings, apartment numbers mentioned in chat messages are
  matched against the ownerless registry events in PostgreSQL (property_events table,
  stage='registry_inclusion') to find cases where a resident-occupied apartment was
  simultaneously declared бесхозяйная.

Run:
    python scripts/80_extract_testimony_deep.py
    # Works on whichever chats have been crawled so far — partial results are fine.
"""
import csv
import json
import logging
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

OUT_TESTIMONY = ROOT / "data" / "parsed" / "testimony_full_all_chats.jsonl"
OUT_MEDIA     = ROOT / "data" / "parsed" / "media_manifest_all_chats.csv"

# (channel_slug_or_username, label, property_ids, track)
CHATS = [
    ("Azovstalskaya31",   "Азовстальська 31",       [6259],                   "demolished"),
    ("morskoy_38_36_30",  "Морський 38/36/30",       [10724],                  "demolished"),
    ("olimpiyskaya_71_79","Олімпійська 71/73/75/77/79",[5171,5034,5172,5173,5174],"title_stripping"),
    ("stroiteley_175_177_163_171_166_152","Строителей 152/163/166/171/175/177",
     [4610,4618,4621,4624,4625,4626],"title_stripping"),
]

APT_NUM = re.compile(r"\bкв\.?\s*№?\s*(\d{1,3})\b", re.I)

# Broad signal — catches anything of potential evidentiary value
SIGNAL = re.compile(
    r"подвал|бомбёжк|бомбежк|обстрел|снаряд|ракет|взрыв|эвакуац|"
    r"снос|сносят|снесли|выселени|выселяют|расселени|аварийн|непригодн|"
    r"бесхозяйн|бесхоз|муниципальн.{0,20}собствен|передали городу|изъяли|"
    r"опечатал|пломб|запечатал|замок сменил|"
    r"уведомлени|акт осмотр|акт обследован|решение суда|администраци|"
    r"госуслуг|ЕГРН|росреестр|кадастр|реестр|регистрац|"
    r"отключил|отрезали|нет воды|нет света|нет газа|"
    r"живём|живем|остались|жильцы|жители|хозяин|владелец|собственник|"
    r"компенсац|выплат|возмещени|сертификат|жилищн|субсиди|"
    r"кран стоит|стройк|новостройк|застройщик|фундамент|огородили|"
    r"трупы|погибли|тела|тела|захоронен|братская|братского|могила",
    re.I,
)


def _load_ownerless_events(pg_dsn: str | None):
    """Load ownerless registry events keyed by (pid, apt_number) from PostgreSQL."""
    if not pg_dsn:
        return {}
    try:
        import psycopg2
        conn = psycopg2.connect(pg_dsn)
        cur  = conn.cursor()
        title_stripping_pids = [5171, 5034, 5172, 5173, 5174,
                                4610, 4618, 4621, 4624, 4625, 4626]
        cur.execute("""
            SELECT p.id, se.event_date,
                   se.detail->>'apt_raw'       AS apt_num,
                   se.detail->>'decree_number' AS decree_num,
                   p.occupation_address
            FROM seizure_event se
            JOIN property p ON p.id = se.property_id
            WHERE se.stage = 'registry_inclusion'
              AND p.id = ANY(%s)
            ORDER BY se.event_date NULLS LAST
        """, (title_stripping_pids,))
        rows = cur.fetchall()
        conn.close()
        log.info("loaded %d ownerless events for title-stripping buildings", len(rows))
        # Key: (pid, apt_str) → event info
        idx = {}
        for pid, evt_date, apt_num, decree, addr in rows:
            if apt_num:
                k = (pid, str(apt_num).strip())
                idx[k] = {
                    "property_id": pid, "apartment": apt_num,
                    "event_date": str(evt_date) if evt_date else None,
                    "decree": decree, "address": addr,
                }
        return idx
    except Exception as e:
        log.warning("could not load ownerless events from PostgreSQL: %s", e)
        return {}


def _iter_chat_messages(con, slug: str):
    """Yield (url, raw_path, media_url, media_path) tuples for a chat."""
    prefix = f"https://t.me/{slug}/"
    rows = con.execute(
        "SELECT url, raw_path FROM source_document "
        "WHERE source_type='telegram_building_chat_msg' AND url LIKE ? "
        "ORDER BY url",
        (prefix + "%",),
    ).fetchall()
    # Build media lookup: parent_url → (media_url, media_path, sha, content_type)
    media_rows = con.execute(
        "SELECT url, raw_path, sha256, content_type FROM source_document "
        "WHERE source_type='telegram_building_chat_media' AND url LIKE ? "
        "ORDER BY url",
        (prefix + "%",),
    ).fetchall()
    media_by_msg = {}
    for murl, mpath, msha, mct in media_rows:
        parent_url = murl.replace("/media", "")
        media_by_msg[parent_url] = {"url": murl, "raw_path": mpath,
                                    "sha256": msha, "content_type": mct}
    return rows, media_by_msg


def main() -> None:
    con = forensics.open_state()

    pg_dsn = getattr(config, "DATABASE_URL", None)
    ownerless_idx = _load_ownerless_events(pg_dsn)

    OUT_TESTIMONY.parent.mkdir(parents=True, exist_ok=True)

    media_rows_out = []
    testimony_count = 0
    flag_by_chat: dict[str, Counter] = {}
    apt_hits: list[dict] = []  # cross-ref: apt mentioned in chat while in ownerless registry

    with OUT_TESTIMONY.open("w", encoding="utf-8") as fh_t:
        for slug, label, pids, track in CHATS:
            rows, media_by_msg = _iter_chat_messages(con, slug)
            log.info("%s: %d messages, %d media", label, len(rows), len(media_by_msg))

            chat_flags: Counter = Counter()
            service = 0

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
                    service += 1
                    continue

                text     = (obj.get("message") or "").strip()
                date_str = obj.get("date") or ""
                msg_id   = obj.get("id")
                has_media = url in media_by_msg

                # Only store messages with content
                if not text and not has_media:
                    continue

                has_signal = bool(SIGNAL.search(text)) if text else False
                apts = APT_NUM.findall(text) if text else []

                rec = {
                    "chat":      slug,
                    "chat_label": label,
                    "track":     track,
                    "property_ids": pids,
                    "url":       url,
                    "msg_id":    msg_id,
                    "date":      date_str,
                    "has_media": has_media,
                    "has_signal": has_signal,
                    "apartments_mentioned": apts,
                    "text":      text,  # FULL text, not truncated
                }

                if has_signal:
                    fh_t.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    testimony_count += 1
                elif apts or has_media:
                    # Media items and apartment refs always included
                    fh_t.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    testimony_count += 1

                # Media manifest entry
                if has_media:
                    m = media_by_msg[url]
                    media_rows_out.append({
                        "chat":         slug,
                        "chat_label":   label,
                        "track":        track,
                        "date":         date_str,
                        "msg_id":       msg_id,
                        "msg_url":      url,
                        "media_url":    m["url"],
                        "raw_path":     m.get("raw_path") or "",
                        "sha256":       m.get("sha256") or "",
                        "content_type": m.get("content_type") or "",
                        "caption":      text[:300] if text else "",
                        "has_signal":   has_signal,
                    })

                # Cross-reference apt mentions with ownerless registry
                if apts and track == "title_stripping":
                    for apt in apts:
                        for pid in pids:
                            key = (pid, apt)
                            if key in ownerless_idx:
                                apt_hits.append({
                                    "chat":      slug,
                                    "msg_url":   url,
                                    "date":      date_str,
                                    "apt":       apt,
                                    **ownerless_idx[key],
                                    "text_excerpt": text[:300] if text else None,
                                })

            flag_by_chat[slug] = chat_flags
            log.info("  → %d signal/media records written (service: %d)", testimony_count, service)

    # Write media manifest CSV
    if media_rows_out:
        fieldnames = ["chat", "chat_label", "track", "date", "msg_id", "msg_url",
                      "media_url", "raw_path", "sha256", "content_type",
                      "caption", "has_signal"]
        with OUT_MEDIA.open("w", encoding="utf-8", newline="") as fh_c:
            w = csv.DictWriter(fh_c, fieldnames=fieldnames)
            w.writeheader()
            for r in sorted(media_rows_out, key=lambda x: x["date"]):
                w.writerow(r)
        log.info("media manifest: %d entries → %s", len(media_rows_out), OUT_MEDIA)

    # ── Console report ────────────────────────────────────────────────────────
    print(f"\n{'='*72}")
    print("DEEP TESTIMONY EXTRACTION — ALL RESIDENT CHATS")
    print(f"{'='*72}")

    print(f"\n  Total testimony records written : {testimony_count}")
    print(f"  Total media items catalogued    : {len(media_rows_out)}")
    print(f"  Output (full text)              : {OUT_TESTIMONY}")
    print(f"  Output (media manifest)         : {OUT_MEDIA}")

    # Per-chat breakdown
    print(f"\n{'─'*72}")
    print("PER-CHAT BREAKDOWN")
    print(f"{'─'*72}")
    for slug, label, pids, track in CHATS:
        rows, media_by_msg = _iter_chat_messages(con, slug)
        chat_signal = [r for r in media_rows_out if r["chat"] == slug and r["has_signal"]]
        print(f"\n  {label}  [{track}]")
        print(f"    messages in store  : {len(rows)}")
        print(f"    media items        : {len([r for r in media_rows_out if r['chat'] == slug])}")
        print(f"    signal media       : {len(chat_signal)}")

    # Apartment cross-reference hits
    if apt_hits:
        print(f"\n{'─'*72}")
        print(f"APARTMENT CROSS-REFERENCE: chat mention × ownerless registry  ({len(apt_hits)} hits)")
        print("(resident mentioned кв.X in chat while that apartment is in the ownerless registry)")
        print(f"{'─'*72}")
        # Sort by apt_hit date to see if chat evidence predates ownerless declaration
        for h in sorted(apt_hits, key=lambda x: x["date"])[:40]:
            ow_date = h.get("event_date") or "date unknown"
            print(f"\n  кв.{h['apt']}  @ {h['address']}")
            print(f"    chat message  : {h['date'][:10]}  {h['msg_url']}")
            print(f"    ownerless evt : {ow_date}  decree={h.get('decree')}")
            if h["text_excerpt"]:
                print(f"    excerpt       : {h['text_excerpt'][:180]}")
    else:
        print("\n  (Ownerless cross-reference: no PostgreSQL hits — check DATABASE_URL "
              "or run after Олімпійська crawl/load completes)")

    # Media triage guide
    print(f"\n{'─'*72}")
    print("MEDIA TRIAGE GUIDE")
    print(f"{'─'*72}")
    print("  Sort media_manifest_all_chats.csv by date ASC to find siege-era content.")
    print("  has_signal=True rows are highest priority for visual review.")

    # Earliest media by chat
    for slug, label, _, _ in CHATS:
        slug_media = sorted(
            [r for r in media_rows_out if r["chat"] == slug],
            key=lambda x: x["date"],
        )
        if slug_media:
            earliest = slug_media[0]
            print(f"\n  Earliest media  — {label}:")
            print(f"    {earliest['date'][:10]}  {earliest['msg_url']}")
            print(f"    {earliest['raw_path']}")
            if earliest["caption"]:
                print(f"    caption: {earliest['caption'][:140]}")

        # High-signal media
        hs = [r for r in slug_media if r["has_signal"]]
        if hs:
            print(f"  First signal media — {label}:")
            print(f"    {hs[0]['date'][:10]}  {hs[0]['msg_url']}")
            if hs[0]["caption"]:
                print(f"    caption: {hs[0]['caption'][:140]}")

    print(f"\n{'='*72}")
    print("Next step: review testimony_full_all_chats.jsonl, then run script 81")
    print("to load selected records into PostgreSQL corroboration table.")
    print(f"{'='*72}\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
