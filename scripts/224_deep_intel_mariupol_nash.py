#!/usr/bin/env python3
"""Deep intelligence extraction over the @mariupol_nash text-only corpus.

City-wide channel, captured text-only by scripts/212 (159,363 messages as of
2026-07). Unlike the building-chat corpus (scripts/148-151), this channel has
NO verified chat->spine-pid mapping (see chat_buildings.py) and its
affiliation/reliability is not yet profiled — treat every hit here as a LEAD
for manual review, not a claim-grade finding. Nothing in this script writes
to the database or the spine; it only mines the raw captured JSON for four
signal types, same taxonomy as script 148 plus a free-text address-candidate
scanner specific to a channel with no building-scoping:

  1. NAMED ACTORS      — officials / contractors / developer SPVs, counted by
                          hit frequency (no cross-chat footprint here, single
                          channel).
  2. LEGAL CITATIONS    — Указ/Распоряжение/Постановление/Решение/Приказ/ГКО/
                          Закон with a number, deduplicated, ranked. Surfaces
                          decree numbers not yet in this project's normative
                          scaffolding.
  3. PROCESS EVENTS     — seizure-lifecycle mechanics (forced entry, sealing,
                          inventory, ownerless publication, exclusion,
                          registration advice, removal, court, demolition,
                          new-build).
  4. ADDRESS CANDIDATES — free-text street-type + house-number mentions.
                          NOT normalized, NOT matched to the spine — raw
                          leads only, confidence-scored 0 (unverified) per
                          this project's no-false-precision rule. A human
                          (or a follow-on fuzzy-match script, run and
                          confidence-scored the normal way) still has to
                          decide whether a given mention is claim-grade.

Outputs:
  data/parsed/nash_deep_intel_records.jsonl   — one row per high-value message
  data/parsed/nash_deep_intel_summary.json    — corpus-level aggregates
  console report

Pure local analysis over the forensic store (no network, no DB writes). Safe
to run, but the corpus is large (~159K messages) — expect several minutes.

Run:
    PYTHONPATH=src python scripts/224_deep_intel_mariupol_nash.py
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

SOURCE_TYPE = "telegram_nash_msg"
OUT_RECORDS = ROOT / "data" / "parsed" / "nash_deep_intel_records.jsonl"
OUT_SUMMARY = ROOT / "data" / "parsed" / "nash_deep_intel_summary.json"

# ── NAMED ACTORS ────────────────────────────────────────────────────────────
# Same roster as scripts/148, extended with city-wide administration figures
# more likely to surface in a general channel than in a single building chat.
ACTORS = [
    ("Кольцов",            r"Кольцов"),
    ("Иващенко",           r"Иващенко"),
    ("Моргун",             r"Моргун"),
    ("Пушилин",            r"Пушилин"),
    ("Хоценко",            r"Хоценко"),
    ("Ходос (МИЗО)",       r"Ходос"),
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
    ("МИЗО",               r"\bМИЗО\b"),
    ("Роскадастр",         r"Роскадастр"),
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

# ── ADDRESS CANDIDATES ──────────────────────────────────────────────────────
# Deliberately loose: street-type token, then up to 4 words/hyphens (the
# street name), then a house-number-shaped token. This is a LEAD scanner,
# not a normalizer — no attempt to resolve abbreviations, alt-names, or
# building keys here. Every hit is raw text for a human (or a follow-on
# fuzzy-match pass through normalize/address.py, confidence-scored the
# normal way) to review before it touches the spine.
ADDRESS_RX = re.compile(
    r"(?:ул\.?|улиц\w*|пр(?:осп)?\.?|проспект\w*|пер\.?|переулок\w*|б-р|бульвар\w*|"
    r"пл\.?|площад\w*|наб\.?|набережн\w*|шоссе|кв-л|квартал\w*)\s+"
    r"([А-ЯЁA-Z][\w\-]*(?:\s+[А-ЯЁA-Zа-яёa-z][\w\-]*){0,3}?)"
    r"[,\s]+(?:д\.?\s*)?(\d{1,4}[А-Яа-яA-Za-z\-/]{0,4})\b",
    re.U,
)

HIGH_VALUE_TAGS = {"forced_entry", "sealing", "exclusion", "removal_decree", "court"}


def main() -> None:
    con = forensics.open_state()
    rows = con.execute(
        "SELECT url, raw_path FROM source_document WHERE source_type=? ORDER BY url",
        (SOURCE_TYPE,),
    ).fetchall()
    log.info("scanning %d @mariupol_nash messages", len(rows))

    actor_counts: Counter = Counter()
    legal_counts: Counter = Counter()
    legal_examples: dict = {}
    process_counts: Counter = Counter()
    tool_hits = 0
    address_counts: Counter = Counter()
    address_examples: dict = {}
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
        date = (obj.get("date") or "")[:10]
        msg_id = url.rstrip("/").rsplit("/", 1)[-1]

        tags = []

        # actors
        hit_actors = []
        for name, rx in ACTOR_RX:
            if rx.search(text):
                actor_counts[name] += 1
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
                legal_examples[key] = {"date": date, "url": url,
                                        "ctx": text[s:m.end() + 60].replace("\n", " ")}

        # process events
        hit_proc = []
        for tag, rx in PROCESS:
            if rx.search(text):
                process_counts[tag] += 1
                hit_proc.append(tag)
                tags.append(tag)

        # tools
        if TOOL_RX.search(text):
            tool_hits += 1
            tags.append("tool")

        # address candidates (leads only — see module docstring)
        hit_addr = []
        for m in ADDRESS_RX.finditer(text):
            street = re.sub(r"\s+", " ", m.group(1)).strip()
            house = m.group(2).strip()
            key = f"{street}, {house}"
            address_counts[key] += 1
            hit_addr.append(key)
            if key not in address_examples:
                s = max(0, m.start() - 40)
                address_examples[key] = {"date": date, "url": url,
                                          "ctx": text[s:m.end() + 40].replace("\n", " ")}

        # record if high-value
        if hit_legal or (set(hit_proc) & HIGH_VALUE_TAGS) or hit_addr:
            rec = {
                "msg_id": msg_id, "url": url, "date": date,
                "actors": hit_actors, "legal": hit_legal,
                "process": hit_proc, "address_candidates": hit_addr,
                "text": text[:600],
            }
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            records.append(rec)

    fh.close()

    summary = {
        "note": "Leads only — @mariupol_nash has no verified spine mapping "
                "and is not yet affiliation/reliability-profiled. Nothing "
                "here is claim-grade until independently corroborated.",
        "messages_with_text": n_msg,
        "high_value_records": len(records),
        "actors": {name: actor_counts[name] for name in actor_counts},
        "legal_citations": {k: {"hits": legal_counts[k], **legal_examples.get(k, {})}
                             for k in legal_counts},
        "process_events": {t: process_counts[t] for t in process_counts},
        "tool_mentions": tool_hits,
        "address_candidates": {k: {"hits": address_counts[k], **address_examples.get(k, {})}
                                for k in address_counts},
    }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── console report ──────────────────────────────────────────────────────
    print(f"\n{'='*72}")
    print(f"@MARIUPOL_NASH DEEP INTEL — {n_msg} text messages, "
          f"{len(records)} high-value records")
    print(f"{'='*72}")

    print(f"\n── NAMED ACTORS (by frequency) ──")
    for name, cnt in actor_counts.most_common():
        print(f"  {name:24s}  {cnt:5d} hits")

    print(f"\n── LEGAL CITATIONS (top 40 by frequency) ──")
    for key, cnt in legal_counts.most_common(40):
        ex = legal_examples.get(key, {})
        print(f"  {key:22s} ×{cnt:<4d} [{ex.get('date','')}]")
        if ex.get("ctx"):
            print(f"      …{ex['ctx'][:150]}…")

    print(f"\n── PROCESS EVENTS (hits) ──")
    for tag, cnt in process_counts.most_common():
        print(f"  {tag:18s}  {cnt:6d} hits")

    print(f"\n── ADDRESS CANDIDATES (top 40 by frequency, UNVERIFIED leads) ──")
    for key, cnt in address_counts.most_common(40):
        ex = address_examples.get(key, {})
        print(f"  {key:32s} ×{cnt:<4d} [{ex.get('date','')}]")

    print(f"\n── EXCLUSION / REMOVAL echoes (hypothesis-relevant) ──")
    excl = [r for r in records if ("exclusion" in r["process"] or "removal_decree" in r["process"])]
    print(f"  {len(excl)} messages mention exclusion-from-ownerless / removal-from-register")
    for r in sorted(excl, key=lambda r: r["date"])[:20]:
        print(f"    {r['date']}  msg {r['msg_id']}  "
              f"{[t for t in r['process'] if t in ('exclusion','removal_decree')]}")

    print(f"\n  {len(address_counts)} distinct address candidates, "
          f"{sum(address_counts.values())} total mentions — all UNVERIFIED, "
          f"not linked to the spine. Run a normalize/address.py fuzzy-match "
          f"pass (confidence-scored, ≥0.8 to be claim-grade) before using "
          f"any of these in an exhibit.")
    print(f"\n  Records → {OUT_RECORDS}")
    print(f"  Summary → {OUT_SUMMARY}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
