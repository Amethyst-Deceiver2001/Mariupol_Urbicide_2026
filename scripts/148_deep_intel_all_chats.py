#!/usr/bin/env python3
"""Deep cross-chat intelligence extraction over the ENTIRE building-chat corpus.

Sweeps all ~145K captured messages across all 28 building chats and mines
"ground intelligence" that single-chat parsers miss because it only emerges
at corpus scale:

  1. NAMED ACTORS — occupation officials, contractors, застройщики — counted
     by frequency AND by how many distinct buildings/chats they appear in
     (cross-building footprint = systemic involvement).
  2. LEGAL CITATIONS — Указ/Распоряжение/Постановление/Решение/Приказ/ГКО/
     Закон ДНР with number + surrounding context, deduplicated, ranked. Lets
     us discover decree numbers residents cite that we haven't captured.
  3. PROCESS EVENTS — tagged occurrences of the seizure-lifecycle mechanics
     (forced entry under police, sealing, inventory commission, ownerless
     publication, EXCLUSION-from-ownerless, registration advice, removal
     decrees). The exclusion + removal tags are the chat-side echo of the
     temporal-differential hypothesis (script 150).
  4. TOOLS — bots / portals residents used (mrplChekHomeBot, госуслуги, etc.)

Outputs:
  data/parsed/deep_intel_records.jsonl   — one row per high-value message
  data/parsed/deep_intel_summary.json    — corpus-level aggregates
  console report

Pure local analysis over the forensic store (no network). Safe to run.

Run:
    PYTHONPATH=src python scripts/148_deep_intel_all_chats.py
"""
import json
import logging
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import forensics  # noqa: E402

log = logging.getLogger(__name__)

OUT_RECORDS = ROOT / "data" / "parsed" / "deep_intel_records.jsonl"
OUT_SUMMARY = ROOT / "data" / "parsed" / "deep_intel_summary.json"

# ── NAMED ACTORS ────────────────────────────────────────────────────────────
# (display_name, regex) — officials, contractors, and the developer entities
# surfaced across this session's site crawls.
ACTORS = [
    ("Кольцов",            r"Кольцов"),
    ("Иващенко",           r"Иващенко"),
    ("Моргун",             r"Моргун"),
    ("Пушилин",            r"Пушилин"),
    ("Хоценко",            r"Хоценко"),
    ("РКС/РКС-НР",         r"РКС[\s\-–]?НР|\bРКС\b|РКС[- ]?Девелопмент"),
    ("Тиволион",           r"Тиволион"),
    ("Трансстройинвест",   r"Трансстрой"),
    ("Монотек",            r"Монотек"),
    ("ИНТЕКО",             r"ИНТЕКО"),
    ("ПОРФИР",             r"Порфир|ПОРФИР"),
    ("ЮгСтройИнвест",      r"ЮгСтрой|югстрой|УСИ\b"),
    ("Проект Инвест",      r"Проект\s*Инвест|ПроектИнвест"),
    ("Эволюция",           r"Эволюци"),
    ("ТЕМП/МАР-С",         r"\bТЕМП\b|МАР[\-\s]?С\b"),
    ("РСК",                r"\bРСК\b"),
    ("Сириус Билд",        r"Сириус"),
    ("Мирастрой/Мираполис",r"Мирастрой|Мираполис|мираполис"),
    ("Вертикаль",          r"Вертикал"),
    ("СУ-2007",            r"СУ[\-\s]?2007"),
    ("Военстрой/ВСК",      r"Военстрой|\bВСК\b|Военно[\-\s]?строит"),
    ("Нахимовское училище",r"Нахимовск\w*\s+(военно|училищ)|НВМУ"),
]
ACTOR_RX = [(name, re.compile(rx, re.I)) for name, rx in ACTORS]

# ── LEGAL CITATIONS ─────────────────────────────────────────────────────────
LEGAL_RX = re.compile(
    r"(Указ|Распоряжени\w*|Постановлени\w*|Решени\w*|Приказ\w*|Закон\w*|ГКО)"
    r"[^\n.№]{0,40}?№\s*([0-9][0-9\-/А-Яа-я.]*)",
    re.I,
)

# ── PROCESS EVENTS ──────────────────────────────────────────────────────────
PROCESS = [
    ("forced_entry",   re.compile(r"вскрыл|с полицией|в присутствии полиции|комисси\w*\s+откр|взлома\w*\s+дверь|срезал\w*\s+замок", re.I)),
    ("sealing",        re.compile(r"опечат|пломб|запечат", re.I)),
    ("inventory",      re.compile(r"инвентаризац|обход\s+квартир|комисси\w*\s+осматр|акт осмотр|акт обследован", re.I)),
    ("ownerless_pub",  re.compile(r"призн\w*\s+бесхоз|список\w*\s+бесхоз|перечень\w*\s+бесхоз|бесхозяйн\w*\s+жил", re.I)),
    ("exclusion",      re.compile(r"исключ\w{0,6}\s+из\s+бесхоз|вывел\w*\s+из\s+бесхоз|снял\w*\s+с\s+учёт|снят\w*\s+с\s+учет|убрал\w*\s+из\s+списк", re.I)),
    ("reg_advice",     re.compile(r"росреестр|ЕГРН|зарегистрир\w*\s+квартир|госуслуг|mrplChekHomeBot|проверк\w*\s+бесхоз", re.I)),
    ("removal_decree", re.compile(r"сняти\w*\s+с\s+учёт|сняти\w*\s+с\s+учет|муниципальн\w*\s+собственност", re.I)),
    ("court",          re.compile(r"суд\b|судебн|иск\b|апелляц|решени\w*\s+суда|кассац", re.I)),
    ("demolition",     re.compile(r"\bснос\w*|демонтаж|сносят|снесл|снесут", re.I)),
    ("new_build",      re.compile(r"новый дом|новостройк|застройщик|стройплощад|залива\w*\s+фундамент|кран\b", re.I)),
]

# ── TOOLS ───────────────────────────────────────────────────────────────────
TOOL_RX = re.compile(r"mrplChekHomeBot|@\w*[Cc]hek\w*|госуслуг|реши?м\s+вместе|@mrpl\w+", re.I)

HIGH_VALUE_TAGS = {"forced_entry", "sealing", "exclusion", "removal_decree", "court"}


def _slug_of(url: str) -> str:
    parts = url.split("/")
    return parts[3] if len(parts) >= 5 else "?"


def main() -> None:
    con = forensics.open_state()
    rows = con.execute(
        "SELECT url, raw_path FROM source_document "
        "WHERE source_type='telegram_building_chat_msg' ORDER BY url"
    ).fetchall()
    log.info("scanning %d chat messages", len(rows))

    actor_counts: Counter = Counter()
    actor_chats: dict = defaultdict(set)
    legal_counts: Counter = Counter()
    legal_examples: dict = {}
    process_counts: Counter = Counter()
    process_chats: dict = defaultdict(set)
    tool_counts: Counter = Counter()
    records = []
    n_msg = 0

    OUT_RECORDS.parent.mkdir(parents=True, exist_ok=True)
    fh = OUT_RECORDS.open("w", encoding="utf-8")

    for i, (url, raw_path) in enumerate(rows):
        if i and i % 20000 == 0:
            log.info("  ...%d / %d", i, len(rows))
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
        text = (obj.get("message") or "").strip()
        if not text:
            continue
        n_msg += 1
        slug = _slug_of(url)
        date = (obj.get("date") or "")[:10]

        tags = []

        # actors
        hit_actors = []
        for name, rx in ACTOR_RX:
            if rx.search(text):
                actor_counts[name] += 1
                actor_chats[name].add(slug)
                hit_actors.append(name)

        # legal citations
        hit_legal = []
        for m in LEGAL_RX.finditer(text):
            kind = m.group(1).split()[0].capitalize()
            num = m.group(2).strip(" .")
            key = f"{kind} №{num}"
            legal_counts[key] += 1
            hit_legal.append(key)
            if key not in legal_examples:
                s = max(0, m.start() - 60)
                legal_examples[key] = {"chat": slug, "date": date, "url": url,
                                        "ctx": text[s:m.end() + 60].replace("\n", " ")}

        # process events
        hit_proc = []
        for tag, rx in PROCESS:
            if rx.search(text):
                process_counts[tag] += 1
                process_chats[tag].add(slug)
                hit_proc.append(tag)
                tags.append(tag)

        # tools
        if TOOL_RX.search(text):
            tool_counts[slug] += 1
            tags.append("tool")

        # record if high-value
        if hit_legal or (set(hit_proc) & HIGH_VALUE_TAGS) or len(hit_actors) >= 1:
            rec = {
                "chat": slug, "url": url, "date": date,
                "actors": hit_actors, "legal": hit_legal,
                "process": hit_proc, "text": text[:600],
            }
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            records.append((slug, date, hit_legal, hit_proc, hit_actors))

    fh.close()

    summary = {
        "messages_with_text": n_msg,
        "high_value_records": len(records),
        "actors": {name: {"hits": actor_counts[name], "chats": sorted(actor_chats[name])}
                    for name in actor_counts},
        "legal_citations": {k: {"hits": legal_counts[k], **legal_examples.get(k, {})}
                             for k in legal_counts},
        "process_events": {t: {"hits": process_counts[t], "chats": len(process_chats[t])}
                            for t in process_counts},
        "tool_mentions_by_chat": dict(tool_counts),
    }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── console report ──────────────────────────────────────────────────────
    print(f"\n{'='*72}")
    print(f"DEEP CROSS-CHAT INTELLIGENCE — {n_msg} text messages, "
          f"{len(records)} high-value records")
    print(f"{'='*72}")

    print(f"\n── NAMED ACTORS (by cross-building footprint, then frequency) ──")
    for name in sorted(actor_counts, key=lambda n: (-len(actor_chats[n]), -actor_counts[n])):
        print(f"  {name:24s}  {actor_counts[name]:5d} hits  in {len(actor_chats[name]):2d} chats")

    print(f"\n── LEGAL CITATIONS (top 40 by frequency) ──")
    for key, cnt in legal_counts.most_common(40):
        ex = legal_examples.get(key, {})
        print(f"  {key:22s} ×{cnt:<4d} [{ex.get('chat','?')} {ex.get('date','')}]")
        if ex.get("ctx"):
            print(f"      …{ex['ctx'][:150]}…")

    print(f"\n── PROCESS EVENTS (hits / distinct chats) ──")
    for tag, cnt in process_counts.most_common():
        print(f"  {tag:18s}  {cnt:6d} hits   {len(process_chats[tag]):2d} chats")

    print(f"\n── EXCLUSION / REMOVAL echoes (hypothesis-relevant) ──")
    excl = [r for r in records if ("exclusion" in r[3] or "removal_decree" in r[3])]
    print(f"  {len(excl)} messages mention exclusion-from-ownerless / removal-from-register")
    for slug, date, _, proc, _ in sorted(excl)[:20]:
        print(f"    {date}  {slug}  {[t for t in proc if t in ('exclusion','removal_decree')]}")

    print(f"\n  Records → {OUT_RECORDS}")
    print(f"  Summary → {OUT_SUMMARY}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
