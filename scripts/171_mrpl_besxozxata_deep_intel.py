#!/usr/bin/env python3
"""Deep intelligence extraction over the @mrpl_besxozxata corpus
(61,752 messages captured `scripts/165`, 2026-06-26).

Unlike the 28 building chats scripts/148 sweeps, this channel is NOT
building-specific -- it is a dedicated, city-wide peer-advice forum about
the ownerless ("бесхоз") registry process. This script reuses script 148's
actor/legal-citation/process-event taxonomy (same regex families, so hits
are comparable across both corpora) and adds two channel-specific passes:

  1. MECHANISM mentions -- named procedures/bodies residents discuss that
     aren't simple law citations (e.g. "СРК" / Special Regional Commission
     for Ukrainian-citizen property registration).
  2. URL extraction -- residents paste links to gosuslugi.ru lists, news
     articles, etc.; these are candidate follow-up capture targets.

Pure local analysis over the forensic store (no network). Safe to run.

Run:
    .venv312/bin/python scripts/171_mrpl_besxozxata_deep_intel.py
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

OUT_RECORDS = ROOT / "data" / "parsed" / "mrpl_besxozxata_intel_records.jsonl"
OUT_SUMMARY = ROOT / "data" / "parsed" / "mrpl_besxozxata_intel_summary.json"

# Same actor/legal/process taxonomy as scripts/148, for cross-corpus comparability.
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
]
ACTOR_RX = [(name, re.compile(rx, re.I)) for name, rx in ACTORS]

LEGAL_RX = re.compile(
    r"(Указ|Распоряжени\w*|Постановлени\w*|Решени\w*|Приказ\w*|Закон\w*|ГКО)"
    r"[^\n.№]{0,40}?№\s*([0-9][0-9\-/А-Яа-я.]*)",
    re.I,
)

PROCESS = [
    ("forced_entry",   re.compile(r"вскрыл|с полицией|в присутствии полиции|комисси\w*\s+откр|взлома\w*\s+дверь|срезал\w*\s+замок", re.I)),
    ("sealing",        re.compile(r"опечат|пломб|запечат", re.I)),
    ("inventory",      re.compile(r"инвентаризац|обход\s+квартир|комисси\w*\s+осматр|акт осмотр|акт обследован", re.I)),
    ("ownerless_pub",  re.compile(r"призн\w*\s+бесхоз|список\w*\s+бесхоз|перечень\w*\s+бесхоз|бесхозяйн\w*\s+жил", re.I)),
    ("exclusion",      re.compile(r"исключ\w{0,6}\s+из\s+бесхоз|вывел\w*\s+из\s+бесхоз|снял\w*\s+с\s+учёт|снят\w*\s+с\s+учет|убрал\w*\s+из\s+списк", re.I)),
    ("reg_advice",     re.compile(r"росреестр|ЕГРН|зарегистрир\w*\s+квартир|госуслуг|mrplChekHomeBot|проверк\w*\s+бесхоз", re.I)),
    ("removal_decree", re.compile(r"сняти\w*\s+с\s+учёт|сняти\w*\s+с\s+учет|муниципальн\w*\s+собственност", re.I)),
    ("court",          re.compile(r"суд\b|судебн|иск\b|апелляц|решени\w*\s+суда|кассац", re.I)),
]

# Channel-specific: named mechanisms/bodies beyond simple law citations.
MECHANISMS = [
    ("СРК (Special Regional Commission)",
     re.compile(r"\bСРК\b|специальн\w*\s+регионал\w*\s+комисси", re.I)),
    ("two-tier RU/UA citizen ruling",
     re.compile(r"гражда\w*\s+украин\w*.{0,80}гражда\w*\s+росси|росси\w*\s+гражда\w*.{0,80}украин\w*\s+гражда", re.I)),
    ("doverennost/power-of-attorney route",
     re.compile(r"доверенност", re.I)),
]
MECHANISM_RX = [(name, rx) for name, rx in MECHANISMS]

URL_RX = re.compile(r"https?://[^\s)>\]]+", re.I)

HIGH_VALUE_TAGS = {"forced_entry", "sealing", "exclusion", "removal_decree"}


def main() -> None:
    con = forensics.open_state()
    rows = con.execute(
        "SELECT url, raw_path FROM source_document "
        "WHERE source_type='telegram_building_chat_msg' AND url LIKE '%mrpl_besxozxata%' "
        "ORDER BY url"
    ).fetchall()
    log.info("scanning %d mrpl_besxozxata messages", len(rows))

    actor_counts: Counter = Counter()
    legal_counts: Counter = Counter()
    legal_examples: dict = {}
    process_counts: Counter = Counter()
    mechanism_counts: Counter = Counter()
    mechanism_examples: dict = defaultdict(list)
    url_counts: Counter = Counter()
    n_msg = 0
    records = []

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
        date = (obj.get("date") or "")[:10]
        msg_id = obj.get("id")

        hit_actors, hit_legal, hit_proc, hit_mech = [], [], [], []

        for name, rx in ACTOR_RX:
            if rx.search(text):
                actor_counts[name] += 1
                hit_actors.append(name)

        for m in LEGAL_RX.finditer(text):
            kind = m.group(1).split()[0].capitalize()
            num = m.group(2).strip(" .")
            key = f"{kind} №{num}"
            legal_counts[key] += 1
            hit_legal.append(key)
            if key not in legal_examples:
                s = max(0, m.start() - 60)
                legal_examples[key] = {"date": date, "msg_id": msg_id,
                                        "ctx": text[s:m.end() + 60].replace("\n", " ")}

        for tag, rx in PROCESS:
            if rx.search(text):
                process_counts[tag] += 1
                hit_proc.append(tag)

        for name, rx in MECHANISM_RX:
            if rx.search(text):
                mechanism_counts[name] += 1
                hit_mech.append(name)
                if len(mechanism_examples[name]) < 5:
                    mechanism_examples[name].append(
                        {"date": date, "msg_id": msg_id, "text": text[:400]}
                    )

        for m in URL_RX.finditer(text):
            url_counts[m.group(0)] += 1

        if hit_legal or hit_mech or (set(hit_proc) & HIGH_VALUE_TAGS):
            rec = {
                "msg_id": msg_id, "date": date,
                "actors": hit_actors, "legal": hit_legal,
                "process": hit_proc, "mechanisms": hit_mech,
                "text": text[:600],
            }
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            records.append(rec)

    fh.close()

    summary = {
        "messages_with_text": n_msg,
        "high_value_records": len(records),
        "actors": dict(actor_counts),
        "legal_citations": {k: {"hits": legal_counts[k], **legal_examples.get(k, {})}
                             for k in legal_counts},
        "process_events": dict(process_counts),
        "mechanisms": {k: {"hits": mechanism_counts[k], "examples": mechanism_examples[k]}
                        for k in mechanism_counts},
        "top_urls": url_counts.most_common(40),
    }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{'='*72}")
    print(f"@mrpl_besxozxata DEEP INTEL — {n_msg} text messages, "
          f"{len(records)} high-value records")
    print(f"{'='*72}")

    print(f"\n── ACTORS ──")
    for name, cnt in actor_counts.most_common():
        print(f"  {name:24s}  {cnt:5d} hits")

    print(f"\n── LEGAL CITATIONS (top 30) ──")
    for key, cnt in legal_counts.most_common(30):
        ex = legal_examples.get(key, {})
        print(f"  {key:22s} ×{cnt:<4d} [{ex.get('date','')}]")

    print(f"\n── PROCESS EVENTS ──")
    for tag, cnt in process_counts.most_common():
        print(f"  {tag:18s}  {cnt:6d} hits")

    print(f"\n── MECHANISMS ──")
    for name, cnt in mechanism_counts.most_common():
        print(f"  {name:40s}  {cnt:5d} hits")
        for ex in mechanism_examples[name][:2]:
            print(f"      {ex['date']}: {ex['text'][:150]}")

    print(f"\n── TOP URLS ──")
    for u, cnt in url_counts.most_common(20):
        print(f"  ×{cnt:<3d} {u}")

    print(f"\n  Records → {OUT_RECORDS}")
    print(f"  Summary → {OUT_SUMMARY}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
