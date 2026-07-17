#!/usr/bin/env python3
"""Flag+manifest pass over the @mrpl_ctzn full-channel scan
(scripts/338), same shape and same reusable signal taxonomy as scripts/225
(@mariupol_nash) and scripts/309 (@mariupolRIP) -- see
docs/mariupol_channel_research_terms.md for the shared pattern bank this
mirrors.

Read-only, local, no network. Requires scripts/338 to have already run
(needs the "telegram_mrplctzn_msg" raw store populated).

Emits:
  1. data/parsed/mrplctzn_flagged_messages.jsonl -- every message that hit
     at least one strong signal (or is on the curated LEADS list), tagged.
  2. data/parsed/mrplctzn_media_pull_manifest.jsonl -- the subset worth a
     targeted media pull (no dedicated puller script generated yet -- write one following scripts/319's pattern if this channel yields high-value media leads), by priority.
  3. console summary.

Claude MAY run this directly -- read-only, local, no geoblocked network
call. It is only useful after scripts/338 has been run by the user.

Run:
    PYTHONPATH=src python scripts/343_mrplctzn_flag_and_media_manifest.py
"""
from __future__ import annotations

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

SOURCE_TYPE = "telegram_mrplctzn_msg"
OUT_FLAGGED = ROOT / "data" / "parsed" / "mrplctzn_flagged_messages.jsonl"
OUT_MANIFEST = ROOT / "data" / "parsed" / "mrplctzn_media_pull_manifest.jsonl"

# ── SIGNAL PATTERNS (same taxonomy as scripts/225; see that file's header
# for provenance -- mirrored in docs/mariupol_channel_research_terms.md) ───
SIGNALS = [
    ("ownerless",       True,  re.compile(r"бесхозя\w*|бесхозн\w*", re.I)),
    ("manevr_fond",     True,  re.compile(r"маневренн\w*\s+фонд\w*|маневренн\w*\s+жил", re.I)),
    ("removal_register",True,  re.compile(r"снят\w*\s+с\s+учёт|снят\w*\s+с\s+учет|обращ\w*\s+в\s+муниципальн\w*\s+собственност|изыма\w*\s+с\s+обращен", re.I)),
    ("forced_entry",    True,  re.compile(r"вскрыл|с полицией|в присутствии полиции|взлома\w*\s+дверь|срезал\w*\s+замок|порядок\s+вскрыт", re.I)),
    ("sealing",         True,  re.compile(r"опечат|пломб|запечат", re.I)),
    ("inventory",       True,  re.compile(r"инвентаризац\w*", re.I)),
    ("filtration",       True,  re.compile(r"фильтрац\w*|не пуска\w*|не пропуст\w*|не пропускают", re.I)),
    ("military_builder",True,  re.compile(r"военн\w*\s+строит\w*|военно[\-\s]?строит\w*|\bВСК\b|Минобороны|МО\s*РФ|Оборонспецстрой|ОборонСпецСтрой", re.I)),
    ("zhk",             True,  re.compile(r"\bЖК\s*[«\"]|микрорайон\w*\s+[«\"А-ЯЁ]|новостройк|жилой\s+комплекс", re.I)),
    ("testimony",       True,  re.compile(r"#нампишут|#сообщают|#крикдуши|#отподписчика|#жалоба|#нужнапомощь|#какбыть", re.I)),
    ("poa",             True,  re.compile(r"доверенност\w*", re.I)),
    ("fraud",           True,  re.compile(r"мошенн\w*|афер\w*", re.I)),
    ("renaming",        True,  re.compile(r"переименова\w*\s+улиц|переименова\w*\s+проспект|аннулир\w*\s+незаконн\w*\s+судебн", re.I)),
    ("demolition_ctx",  False, re.compile(r"\bснос\w*|снесл\w*|снесут|демонтаж\w*", re.I)),
    ("collapse_ctx",    False, re.compile(r"обруш\w*|обвал\w*|трещин\w*|треснул\w*|аварийн\w*", re.I)),
    ("passport_ctx",    False, re.compile(r"паспорт\w*|гражданств\w*", re.I)),
    ("compensation_ctx",False, re.compile(r"компенсац\w*|сертификат\w*|ипотек\w*", re.I)),
    ("court_ctx",       False, re.compile(r"\bсуд\b|судебн\w*|\bиск[аеомуй]{0,3}\b|апелляц\w*|кассац\w*|прокуратур\w*", re.I)),
    ("notary_ctx",      False, re.compile(r"нотариус\w*|нотариальн\w*", re.I)),
    ("citizenship_gate_ctx", False, re.compile(r"спец\w*\s+разрешени|разрешени\w*\s+на\s+(регистрац|распоряжен)|коллегиальн\w*\s+орган", re.I)),
    # street-name signal for this cluster's own review target, so the video
    # is never missed even if its own caption is bare
    ("zelinskogo_cluster", True, re.compile(r"Зелинск|Бахчиванджи|Нахимовск", re.I)),
]

PROPERTY_NEXUS = re.compile(
    r"квартир\w*|недвижимост\w*|собственност\w*|имуществ\w*|жиль\w*|дом[а-я]?\b|"
    r"бесхоз\w*|переименова\w*|застройщик\w*|компенсац\w*",
    re.I,
)

LEGAL_RX = re.compile(
    r"(Указ|Распоряжени\w*|Постановлени\w*|Решени\w*|Приказ\w*|Закон\w*|ГКО)"
    r"[^\n.№]{0,40}?№\s*([0-9][0-9\-/А-Яа-я.]*)",
    re.I,
)

ENTITY_RX = re.compile(
    r"(ООО|АО|ЗАО|ОАО|ПАО|ГУП|МУП|ФГУП|ППК)\s*[«\"]([^»\"]{2,60})[»\"]", re.U)
BUILDER_HINT = re.compile(
    r"строит\w*|застройщик|восстанавл\w*|возвод\w*|подрядчик|девелоп|СЗ\b|"
    r"специализированн\w*\s+застройщик|ремонт", re.I)

# ── CURATED LEADS ────────────────────────────────────────────────────────
# none yet -- this channel has no hand-verified lead messages at generation
# time; add {msg_id: (note, ...)} entries here once review surfaces one
# worth pinning (see scripts/318 for the pattern).
LEADS = {}



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


def _tags_for(text: str) -> tuple[list[str], list[str], list[str]]:
    tags = []
    has_nexus = bool(PROPERTY_NEXUS.search(text))
    for tag, high, rx in SIGNALS:
        if rx.search(text):
            if high:
                tags.append(tag)
            elif has_nexus:
                tags.append(tag)
            else:
                tags.append(tag + "?")
    legal_hits = sorted({f"{m.group(1).split()[0].capitalize()} №{m.group(2).strip(' .')}"
                         for m in LEGAL_RX.finditer(text)})
    if legal_hits:
        tags.append("legal_instrument")
    ent_hits = []
    for m in ENTITY_RX.finditer(text):
        s = max(0, m.start() - 60)
        window = text[s:m.end() + 60]
        if BUILDER_HINT.search(window):
            ent_hits.append(f"{m.group(1)} «{m.group(2).strip()}»")
    if ent_hits:
        tags.append("builder_entity")
    return tags, legal_hits, ent_hits


def main() -> None:
    con = forensics.open_state()
    rows = con.execute(
        "SELECT url, raw_path FROM source_document WHERE source_type=? ORDER BY url",
        (SOURCE_TYPE,),
    ).fetchall()
    if not rows:
        log.error("no %s rows found — run scripts/338 first (VPS/user terminal)", SOURCE_TYPE)
        sys.exit(1)
    log.info("scanning %d %s messages", len(rows), SOURCE_TYPE)

    OUT_FLAGGED.parent.mkdir(parents=True, exist_ok=True)
    fh = OUT_FLAGGED.open("w", encoding="utf-8")
    mh = OUT_MANIFEST.open("w", encoding="utf-8")

    tag_counts: Counter = Counter()
    media_counts: Counter = Counter()
    pull_priority_counts: Counter = Counter()
    flagged = 0
    pull_photo = 0
    pull_video = 0
    leads_seen = set()
    n_msg = 0

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

        tags, legal_hits, ent_hits = _tags_for(text) if text else ([], [], [])
        strong = [t for t in tags if not t.endswith("?")]
        lead_note = LEADS.get(msg_id)
        media_kind, media_size = _media_info(obj)
        media_counts[media_kind] += 1

        # text-signal flagging (unchanged -- this is a separate concern from
        # media presence: it drives the FLAGGED file, used for text mining)
        if strong or lead_note:
            flagged += 1
            for t in strong:
                tag_counts[t] += 1
            if lead_note:
                leads_seen.add(msg_id)
            rec = {
                "msg_id": msg_id, "url": url, "date": date,
                "tags": tags,
                "legal_citations": legal_hits,
                "builder_entities": ent_hits,
                "lead_note": lead_note,
                "media_kind": media_kind,
                "media_size_bytes": media_size,
                "text": text[:800],
            }
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

        # media-pull manifest -- deliberately NOT gated on text-signal
        # flagging above. This is a war-footage channel ("Кадры войны") with
        # thin/no captions on most posts; gating media on caption text meant
        # almost every photo/video was silently dropped even though the
        # VISUAL content (not the caption) is the evidentiary value. Any
        # message carrying media gets a manifest row; priority still reflects
        # signal strength so the puller can triage without downloading
        # everything blind.
        if media_kind in ("photo", "video", "document"):
            if lead_note:
                priority = 1
            elif strong:
                priority = 2
            elif media_kind == "photo":
                priority = 2   # photos are small -- pull liberally even w/o caption signal
            else:
                priority = 3   # bare-caption video/document -- lowest default priority
            if media_kind == "photo":
                pull_photo += 1
            else:
                pull_video += 1
            pull_priority_counts[priority] += 1
            mh.write(json.dumps({
                "msg_id": msg_id, "url": url, "date": date,
                "media_kind": media_kind, "media_size_bytes": media_size,
                "pull_priority": priority,
                "tags": strong, "lead_note": lead_note,
            }, ensure_ascii=False) + "\n")

    fh.close()
    mh.close()
    con.close()

    print(f"\n{'='*72}")
    print(f"@mrpl_ctzn FLAGGING — {n_msg} messages scanned, {flagged} flagged")
    print(f"{'='*72}")
    print("\n── flags by signal (strong only) ──")
    for tag, c in tag_counts.most_common():
        print(f"  {tag:22s} {c}")
    print("\n── media on flagged messages ──")
    for k, c in media_counts.most_common():
        print(f"  {k:12s} {c}")
    print(f"\n── curated LEADS ──  {len(leads_seen)}/{len(LEADS)} present in store")
    missing = sorted(set(LEADS) - leads_seen)
    if missing:
        print(f"  MISSING (not found in capture — check msg id / channel): {', '.join(missing)}")
    print(f"\n── media-pull manifest ──")
    print(f"  {pull_photo} photos (small, pull all) + {pull_video} curated videos")
    print(f"  by pull_priority: "
          f"P1(curated leads)={pull_priority_counts[1]}  "
          f"P2(core seizure)={pull_priority_counts[2]}  "
          f"P3(broad testimony/ctx)={pull_priority_counts[3]}")
    print(f"\n  Flagged  → {OUT_FLAGGED}")
    print(f"  Manifest → {OUT_MANIFEST}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
