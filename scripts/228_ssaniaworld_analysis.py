#!/usr/bin/env python3
"""Local analysis of the newly-captured @ssaniaworld corpus (4,365 msgs).

Sania Denisova's personal channel — see scripts/227's docstring for who she
is and why this project cares (organizing collective prosecutor complaints
for bezkhoz/demolished-property owners, per @mariupol_nash msg 91318). This
script is the @ssaniaworld counterpart to scripts/224+225 combined into one
pass, since the corpus is two orders of magnitude smaller than @mariupol_nash
(4,365 vs 159,363 messages) and doesn't need to be split across two runs.

Reuses the exact term taxonomy validated on @mariupol_nash
(docs/mariupol_channel_research_terms.md) — actors, legal-instrument
citations, seizure-lifecycle process tags, named builder entities, free-text
address candidates — PLUS the flag/media-manifest step from scripts/225, so
any high-value lead's media can be pulled later without hauling down the
whole channel. There is no curated LEADS dict yet (unlike scripts/225's
Nash-specific one) — this run's OWN job is to discover what belongs in one,
which the console report + JSONL make easy to build by hand afterward.

Outputs:
  data/parsed/ssaniaworld_flagged_messages.jsonl — one row per flagged msg
  data/parsed/ssaniaworld_media_pull_manifest.jsonl — media targets, tiered
  data/parsed/ssaniaworld_deep_intel_summary.json — actor/legal/process aggregates
  console report

Pure local analysis over the forensic store (no network, no DB writes). Safe
to run.

Run:
    PYTHONPATH=src python scripts/228_ssaniaworld_analysis.py
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

SOURCE_TYPE = "telegram_ssaniaworld_msg"
CHANNEL = "ssaniaworld"
OUT_FLAGGED = ROOT / "data" / "parsed" / "ssaniaworld_flagged_messages.jsonl"
OUT_MANIFEST = ROOT / "data" / "parsed" / "ssaniaworld_media_pull_manifest.jsonl"
OUT_SUMMARY = ROOT / "data" / "parsed" / "ssaniaworld_deep_intel_summary.json"

# ── SIGNAL PATTERNS ─────────────────────────────────────────────────────────
# Identical taxonomy to scripts/225 (validated on @mariupol_nash) — see
# docs/mariupol_channel_research_terms.md for why each pattern is shaped
# this way and what noise it avoids.
SIGNALS = [
    ("ownerless",       True,  re.compile(r"бесхозя\w*|бесхозн\w*", re.I)),
    ("manevr_fond",     True,  re.compile(r"маневренн\w*\s+фонд\w*|маневренн\w*\s+жил", re.I)),
    ("removal_register",True,  re.compile(r"снят\w*\s+с\s+учёт|снят\w*\s+с\s+учет|обращ\w*\s+в\s+муниципальн\w*\s+собственност|изыма\w*\s+с\s+обращен", re.I)),
    ("forced_entry",    True,  re.compile(r"вскрыл|с полицией|в присутствии полиции|взлома\w*\s+дверь|срезал\w*\s+замок|порядок\s+вскрыт", re.I)),
    ("sealing",         True,  re.compile(r"опечат|пломб|запечат", re.I)),
    ("military_builder",True,  re.compile(r"военн\w*\s+строит\w*|военно[\-\s]?строит\w*|\bВСК\b|Минобороны|МО\s*РФ|Оборонспецстрой|ОборонСпецСтрой", re.I)),
    ("zhk",             True,  re.compile(r"\bЖК\s*[«\"]|микрорайон\w*\s+[«\"А-ЯЁ]|новостройк|жилой\s+комплекс", re.I)),
    ("testimony",       True,  re.compile(r"#нампишут|#сообщают|#крикдуши|#отподписчика|#жалоба|#нужнапомощь|#какбыть", re.I)),
    ("poa",             True,  re.compile(r"доверенност\w*", re.I)),
    ("fraud",           True,  re.compile(r"мошенн\w*|афер\w*", re.I)),
    ("renaming",        True,  re.compile(r"переименова\w*\s+улиц|переименова\w*\s+проспект|аннулир\w*\s+незаконн\w*\s+судебн", re.I)),
    ("prosecutor",      True,  re.compile(r"прокуратур\w*|прокурор\w*", re.I)),  # her own documented mechanism
    ("demolition_ctx",  False, re.compile(r"\bснос\w*|снесл\w*|снесут|демонтаж\w*", re.I)),
    ("collapse_ctx",    False, re.compile(r"обруш\w*|обвал\w*|трещин\w*|треснул\w*|аварийн\w*", re.I)),
    ("passport_ctx",    False, re.compile(r"паспорт\w*|гражданств\w*", re.I)),
    ("compensation_ctx",False, re.compile(r"компенсац\w*|сертификат\w*|ипотек\w*", re.I)),
    ("court_ctx",       False, re.compile(r"\bсуд\b|судебн\w*|\bиск[аеомуй]{0,3}\b|апелляц\w*|кассац\w*", re.I)),
    ("notary_ctx",      False, re.compile(r"нотариус\w*|нотариальн\w*", re.I)),
    ("citizenship_gate_ctx", False, re.compile(r"спец\w*\s+разрешени|разрешени\w*\s+на\s+(регистрац|распоряжен)|коллегиальн\w*\s+орган", re.I)),
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

# named actors — same roster validated on the Nash sweep (scripts/148/224)
ACTORS = [
    ("Кольцов",            r"Кольцов"),
    ("Иващенко",           r"Иващенко"),
    ("Моргун",             r"Моргун"),
    ("Пушилин",            r"Пушилин"),
    ("Хоценко",            r"Хоценко"),
    ("Ходос (МИЗО)",       r"Ходос"),
    ("Тимур Иванов",       r"Тимур Иванов"),
    ("РКС/РКС-НР",         r"РКС[\s\-–]?НР|\bРКС\b|РКС[- ]?Девелопмент"),
    ("Военстрой/ВСК",      r"Военстрой|\bВСК\b|Военно[\-\s]?строит"),
    ("ЮгСтройИнвест",      r"ЮгСтрой|югстрой|УСИ\b"),
    ("МИЗО",               r"\bМИЗО\b"),
    ("Роскадастр",         r"Роскадастр"),
]
ACTOR_RX = [(name, re.compile(rx, re.I)) for name, rx in ACTORS]

ADDRESS_RX = re.compile(
    r"(?:ул\.?|улиц\w*|пр(?:осп)?\.?|проспект\w*|пер\.?|переулок\w*|б-р|бульвар\w*|"
    r"пл\.?|площад\w*|наб\.?|набережн\w*|шоссе|кв-л|квартал\w*)\s+"
    r"([А-ЯЁA-Z][\w\-]*(?:\s+[А-ЯЁA-Zа-яёa-z][\w\-]*){0,3}?)"
    r"[,\s]+(?:д\.?\s*)?(\d{1,4}[А-Яа-яA-Za-z\-/]{0,4})\b",
    re.U,
)

HIGH_VALUE_TAGS = {"forced_entry", "sealing", "removal_register", "prosecutor"}
PRIORITY_2_TAGS = {
    "ownerless", "manevr_fond", "removal_register", "forced_entry", "sealing",
    "military_builder", "zhk", "renaming", "poa", "prosecutor",
}


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
    log.info("scanning %d @%s messages", len(rows), CHANNEL)

    OUT_FLAGGED.parent.mkdir(parents=True, exist_ok=True)
    fh = OUT_FLAGGED.open("w", encoding="utf-8")
    mh = OUT_MANIFEST.open("w", encoding="utf-8")

    tag_counts: Counter = Counter()
    media_counts: Counter = Counter()
    pull_priority_counts: Counter = Counter()
    actor_counts: Counter = Counter()
    legal_counts: Counter = Counter()
    legal_examples: dict = {}
    address_counts: Counter = Counter()
    address_examples: dict = {}
    n_msg = n_text = flagged = pull_photo = pull_video = 0
    high_value_records = []

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

        if text:
            n_text += 1
            for name, rx in ACTOR_RX:
                if rx.search(text):
                    actor_counts[name] += 1
            for m in ADDRESS_RX.finditer(text):
                street = re.sub(r"\s+", " ", m.group(1)).strip()
                house = m.group(2).strip()
                key = f"{street}, {house}"
                address_counts[key] += 1
                if key not in address_examples:
                    s = max(0, m.start() - 40)
                    address_examples[key] = {"date": date, "url": url,
                                              "ctx": text[s:m.end() + 40].replace("\n", " ")}

        tags, legal_hits, ent_hits = _tags_for(text) if text else ([], [], [])
        strong = [t for t in tags if not t.endswith("?")]

        for key in legal_hits:
            legal_counts[key] += 1
            if key not in legal_examples:
                legal_examples[key] = {"date": date, "url": url,
                                        "ctx": text[:150].replace("\n", " ")}
        if set(strong) & HIGH_VALUE_TAGS:
            high_value_records.append({"msg_id": msg_id, "date": date, "url": url,
                                        "tags": strong, "text": text[:400]})

        if not strong:
            continue

        flagged += 1
        for t in strong:
            tag_counts[t] += 1

        media_kind, media_size = _media_info(obj)
        media_counts[media_kind] += 1

        rec = {
            "msg_id": msg_id, "url": url, "date": date,
            "tags": tags,
            "legal_citations": legal_hits,
            "builder_entities": ent_hits,
            "media_kind": media_kind,
            "media_size_bytes": media_size,
            "text": text[:800],
        }
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

        want = media_kind == "photo"
        if want:
            priority = 2 if any(t in PRIORITY_2_TAGS for t in strong) else 3
            pull_photo += 1
            pull_priority_counts[priority] += 1
            mh.write(json.dumps({
                "msg_id": msg_id, "url": url, "date": date,
                "media_kind": media_kind, "media_size_bytes": media_size,
                "pull_priority": priority, "tags": strong,
            }, ensure_ascii=False) + "\n")

    fh.close()
    mh.close()

    summary = {
        "channel": CHANNEL,
        "messages_with_text": n_text,
        "high_value_records": len(high_value_records),
        "actors": {name: actor_counts[name] for name in actor_counts},
        "legal_citations": {k: {"hits": legal_counts[k], **legal_examples.get(k, {})}
                             for k in legal_counts},
        "address_candidates": {k: {"hits": address_counts[k], **address_examples.get(k, {})}
                                for k in address_counts},
    }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{'='*72}")
    print(f"@{CHANNEL} ANALYSIS — {n_msg} messages scanned, {n_text} with text, "
          f"{flagged} flagged")
    print(f"{'='*72}")

    print("\n── flags by signal (strong only) ──")
    for tag, c in tag_counts.most_common():
        print(f"  {tag:22s} {c}")

    print("\n── NAMED ACTORS ──")
    for name, c in actor_counts.most_common():
        print(f"  {name:24s} {c}")

    print(f"\n── LEGAL CITATIONS ({len(legal_counts)} distinct) ──")
    for key, cnt in legal_counts.most_common(30):
        ex = legal_examples.get(key, {})
        print(f"  {key:22s} ×{cnt:<3d} [{ex.get('date','')}]  {ex.get('ctx','')[:90]}")

    print(f"\n── ADDRESS CANDIDATES ({len(address_counts)} distinct, UNVERIFIED leads) ──")
    for key, cnt in address_counts.most_common(30):
        ex = address_examples.get(key, {})
        print(f"  {key:30s} ×{cnt:<3d} [{ex.get('date','')}]")

    print(f"\n── HIGH-VALUE RECORDS (forced_entry/sealing/removal_register/prosecutor) "
          f"── {len(high_value_records)}")
    for r in sorted(high_value_records, key=lambda r: r["date"])[:20]:
        print(f"  {r['date']}  msg {r['msg_id']}  {r['tags']}")
        print(f"    {r['text'][:150].replace(chr(10), ' ')}")

    print("\n── media on flagged messages ──")
    for k, c in media_counts.most_common():
        print(f"  {k:12s} {c}")
    print(f"\n── media-pull manifest ── {pull_photo} photos "
          f"(P2 core-seizure={pull_priority_counts[2]}, "
          f"P3 broad={pull_priority_counts[3]})")

    print(f"\n  Flagged  → {OUT_FLAGGED}")
    print(f"  Manifest → {OUT_MANIFEST}")
    print(f"  Summary  → {OUT_SUMMARY}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
