#!/usr/bin/env python3
"""Deep-intel extraction over the four channels captured by `scripts/174`
(2026-06-26/27): one apparent OFFICIAL ministry channel and three resident
legal-advice channels surfaced as top-cited URLs in the @mrpl_besxozxata
pass (`scripts/171`).

    @mizodnr                          -- OFFICIAL channel of МИЗО ДНР
                                         (Минимущества/Ministry of Property &
                                         Land Relations). Confirmed primary
                                         source: weekly «Итоги работы
                                         министерства», #вопрос_ответ procedure
                                         explainers, land/property-policy posts,
                                         signed "МИЗО ДНР". The ministry that
                                         administers the seizure/registration
                                         regime, in its own voice.
    @donurcenter                      -- resident legal-services channel (40k+
    @yuridicheskiyeuslugiMariupolDon     msgs). Commentary, NOT primary -- use
    @advocate_Basivskiy                  to map which decrees/mechanisms
                                         residents are fighting; verify any
                                         decree claim against the decree text
                                         before citing as fact.

Reuses the scripts/148/171 actor/legal/process/mechanism taxonomy so hits are
comparable across all telegram corpora. Adds a mizodnr-specific pass:
  * post-type classifier (#вопрос_ответ explainer / weekly ministry digest /
    other) -- isolates the ministry's self-incriminating procedure narration;
  * a relevance filter for the bezkhoz/ownerless + registration-ban +
    Mariupol nexus this project tracks.

Pure local analysis over the forensic store (no network). Safe to run.

Run:
    .venv312/bin/python scripts/177_new_channels_deep_intel.py
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

CHANNELS = {
    "mizodnr": "official",
    "donurcenter": "legal_advice",
    "yuridicheskiyeuslugiMariupolDon": "legal_advice",
    "advocate_Basivskiy": "legal_advice",
}

OUT_DIR = ROOT / "data" / "parsed"
OUT_RECORDS = OUT_DIR / "new_channels_intel_records.jsonl"
OUT_SUMMARY = OUT_DIR / "new_channels_intel_summary.json"

# --- shared taxonomy (scripts/148/171) ----------------------------------
ACTORS = [
    ("Кольцов",            r"Кольцов"),
    ("Иващенко",           r"Иващенко"),
    ("Моргун",             r"Моргун"),
    ("Пушилин",            r"Пушилин"),
    ("Хоценко",            r"Хоценко"),
    ("РКС/РКС-НР",         r"РКС[\s\-–]?НР|\bРКС\b|РКС[- ]?Девелопмент"),
    ("МИЗО/Минимущества",  r"МИЗО|Минимущест|имуществен\w+\s+отношен"),
    ("СПК/ФГИ/Фонд",       r"Фонд\w*\s+госимущест|ФГИ|Госимущест"),
    ("Сарапулов",          r"Сарапулов"),
]
ACTOR_RX = [(name, re.compile(rx, re.I)) for name, rx in ACTORS]

LEGAL_RX = re.compile(
    r"(Указ|Распоряжени\w*|Постановлени\w*|Решени\w*|Приказ\w*|Закон\w*|ГКО|ФКЗ|ФЗ)"
    r"[^\n.№]{0,40}?№\s*([0-9][0-9\-/А-Яа-я.]*)",
    re.I,
)

PROCESS = [
    ("forced_entry",   re.compile(r"вскрыл|с полицией|в присутствии полиции|комисси\w*\s+откр|взлома\w*\s+дверь|срезал\w*\s+замок", re.I)),
    ("sealing",        re.compile(r"опечат|пломб|запечат", re.I)),
    ("inventory",      re.compile(r"инвентаризац|обход\s+квартир|комисси\w*\s+осматр|акт осмотр|акт обследован", re.I)),
    ("ownerless_pub",  re.compile(r"призн\w*\s+бесхоз|список\w*\s+бесхоз|перечень\w*\s+бесхоз|бесхозяйн\w*\s+(жил|вещ|недвиж|имуществ)", re.I)),
    ("exclusion",      re.compile(r"исключ\w{0,6}\s+из\s+бесхоз|вывел\w*\s+из\s+бесхоз|снял\w*\s+с\s+учёт|снят\w*\s+с\s+учет|убрал\w*\s+из\s+списк", re.I)),
    ("reg_advice",     re.compile(r"росреестр|ЕГРН|зарегистрир\w*\s+(прав|квартир)|госуслуг|проверк\w*\s+бесхоз", re.I)),
    ("reg_ban",        re.compile(r"запрет\w*\s+регистрац|приостанов\w*\s+регистрац|недружествен\w*\s+госуд|гражда\w*\s+украин\w*.{0,40}регистрац", re.I)),
    ("court",          re.compile(r"суд\b|судебн|иск\b|апелляц|решени\w*\s+суда|кассац|верховн\w*\s+суд", re.I)),
    ("compensation",   re.compile(r"компенсац|выплат\w*\s+за\s+жил|возмещени\w*\s+ущерб|сертификат\w*\s+на\s+жил", re.I)),
]

MECHANISMS = [
    ("СРК (Special Regional Commission)",
     re.compile(r"\bСРК\b|специальн\w*\s+регионал\w*\s+комисси", re.I)),
    ("two-tier RU/UA citizen rule",
     re.compile(r"гражда\w*\s+украин\w*.{0,80}гражда\w*\s+росси|росси\w*\s+гражда\w*.{0,80}украин\w*\s+гражда|недружествен\w*\s+госуд", re.I)),
    ("doverennost / power-of-attorney",
     re.compile(r"доверенност", re.I)),
    ("personal-appearance requirement",
     re.compile(r"лично\w*\s+(явк|присут|обращ)|личн\w*\s+присутстви|должен\w*\s+явит", re.I)),
    ("legalisation of UA documents",
     re.compile(r"легализац|апостил", re.I)),
]
MECHANISM_RX = [(name, rx) for name, rx in MECHANISMS]

URL_RX = re.compile(r"https?://[^\s)>\]]+", re.I)

# mizodnr post-type tells
RX_QA = re.compile(r"#вопрос_ответ|#вопрос|Можно ли|Как оформить|Что нужно знать|разъясн", re.I)
RX_WEEKLY = re.compile(r"Итоги работы министерства|в фокусе|за неделю", re.I)
# project-nexus relevance
RX_NEXUS = re.compile(
    r"бесхоз|выморочн|Мариупол|недружествен|запрет\w*\s+регистрац|"
    r"муниципальн\w*\s+собственност|изъят\w*\s+имуществ|снос|снят\w*\s+с\s+учёт",
    re.I,
)
HIGH_VALUE_TAGS = {"forced_entry", "sealing", "exclusion", "reg_ban", "ownerless_pub"}


def load_msgs(con, channel):
    prefix = f"https://t.me/{channel}/"
    rows = con.execute(
        "SELECT url, raw_path FROM source_document "
        "WHERE source_type='telegram_building_chat_msg' AND url LIKE ? ORDER BY url",
        (prefix + "%",),
    ).fetchall()
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
        yield obj


def scan_channel(con, channel, role, fh):
    actor_counts = Counter()
    legal_counts = Counter()
    legal_examples = {}
    process_counts = Counter()
    mechanism_counts = Counter()
    mechanism_examples = defaultdict(list)
    url_counts = Counter()
    post_types = Counter()
    nexus_examples = []
    n_msg = n_text = 0

    for obj in load_msgs(con, channel):
        n_msg += 1
        text = (obj.get("message") or "").strip()
        if not text:
            continue
        n_text += 1
        date = (obj.get("date") or "")[:10]
        msg_id = obj.get("id")

        if role == "official":
            if RX_WEEKLY.search(text):
                post_types["weekly_digest"] += 1
            elif RX_QA.search(text):
                post_types["qa_explainer"] += 1
            else:
                post_types["other"] += 1

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
                                       "ctx": text[s:m.end() + 80].replace("\n", " ")}
        for tag, rx in PROCESS:
            if rx.search(text):
                process_counts[tag] += 1
                hit_proc.append(tag)
        for name, rx in MECHANISM_RX:
            if rx.search(text):
                mechanism_counts[name] += 1
                hit_mech.append(name)
                if len(mechanism_examples[name]) < 6:
                    mechanism_examples[name].append(
                        {"date": date, "msg_id": msg_id, "text": text[:400]})
        for m in URL_RX.finditer(text):
            url_counts[m.group(0)] += 1

        is_nexus = bool(RX_NEXUS.search(text))
        if is_nexus and len(nexus_examples) < 60:
            nexus_examples.append({"date": date, "msg_id": msg_id,
                                   "text": text[:500].replace("\n", " ")})

        if hit_legal or hit_mech or (set(hit_proc) & HIGH_VALUE_TAGS) or \
                (role == "official" and is_nexus):
            rec = {
                "channel": channel, "role": role,
                "msg_id": msg_id, "date": date, "url": f"https://t.me/{channel}/{msg_id}",
                "actors": hit_actors, "legal": hit_legal,
                "process": hit_proc, "mechanisms": hit_mech,
                "nexus": is_nexus, "text": text[:700],
            }
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    return {
        "channel": channel, "role": role,
        "messages": n_msg, "messages_with_text": n_text,
        "post_types": dict(post_types),
        "actors": dict(actor_counts),
        "legal_citations": {k: {"hits": legal_counts[k], **legal_examples.get(k, {})}
                            for k, _ in legal_counts.most_common()},
        "process_events": dict(process_counts),
        "mechanisms": {k: {"hits": mechanism_counts[k], "examples": mechanism_examples[k]}
                       for k in mechanism_counts},
        "nexus_examples": nexus_examples,
        "top_urls": url_counts.most_common(40),
    }


def main():
    con = forensics.open_state()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fh = OUT_RECORDS.open("w", encoding="utf-8")
    summaries = {}
    for channel, role in CHANNELS.items():
        log.info("scanning @%s (%s)", channel, role)
        summaries[channel] = scan_channel(con, channel, role, fh)
    fh.close()
    OUT_SUMMARY.write_text(json.dumps(summaries, ensure_ascii=False, indent=2),
                           encoding="utf-8")

    for channel, s in summaries.items():
        print(f"\n{'='*72}")
        print(f"@{channel}  [{s['role']}]  {s['messages_with_text']} text / "
              f"{s['messages']} msgs")
        print(f"{'='*72}")
        if s["post_types"]:
            print("  post types:", s["post_types"])
        if s["actors"]:
            print("  ── actors ──")
            for n, c in Counter(s["actors"]).most_common():
                print(f"     {n:24s} {c:5d}")
        print("  ── legal citations (top 20) ──")
        for k, info in list(s["legal_citations"].items())[:20]:
            print(f"     {k:22s} ×{info['hits']:<4d} [{info.get('date','')}]")
        print("  ── process events ──")
        for t, c in Counter(s["process_events"]).most_common():
            print(f"     {t:16s} {c:6d}")
        print("  ── mechanisms ──")
        for n, info in s["mechanisms"].items():
            print(f"     {n:40s} {info['hits']:5d}")
        print("  ── top urls ──")
        for u, c in s["top_urls"][:12]:
            print(f"     ×{c:<3d} {u}")
    print(f"\n  Records → {OUT_RECORDS}")
    print(f"  Summary → {OUT_SUMMARY}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
