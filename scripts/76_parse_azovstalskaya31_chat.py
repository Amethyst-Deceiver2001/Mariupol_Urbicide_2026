#!/usr/bin/env python3
"""Parse captured @Azovstalskaya31 Telegram messages for evidentiary signals.

Reads raw message JSON from data/raw/ (captured by script 74) and extracts:
  - Apartment references (кв. №) → link to ownerless registry on adjacent buildings
  - Siege/occupation keywords → timeline of resident presence, damage, utility cuts
  - Media-bearing messages → damage photo candidates
  - Official notices (снос, выселение, бесхозяйность, акт, уведомление) → admin acts
  - Resident-presence markers → rebuts "бесхозяйность" predicate

Outputs:
  - Console summary with stats and top findings
  - data/parsed/azovstalskaya31_chat_signals.jsonl  — one signal record per hit

Does NOT write to the PostgreSQL DB — load step is separate once signals are reviewed.

Run:
    python scripts/76_parse_azovstalskaya31_chat.py [--verbose]
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

OUT = ROOT / "data" / "parsed" / "azovstalskaya31_chat_signals.jsonl"

CHANNEL = "Azovstalskaya31"

# ── Signal keyword groups ──────────────────────────────────────────────────────

SIEGE = re.compile(
    r"подвал|бомбёжк|бомбежк|обстрел|прилёт|прилет|снаряд|ракет|взрыв|"
    r"эвакуац|укрыт|убежищ|без света|без воды|без газ|без тепл|"
    r"март|апрел|май 2022|2022\s*год|весна 2022",
    re.I,
)

DEMOLITION = re.compile(
    r"снос|сносят|снесли|снесут|демонтаж|разбор|расселени|расселяют|расселили|"
    r"выселени|выселяют|выселили|аварийн|признан|непригодн|подлежит",
    re.I,
)

OFFICIAL = re.compile(
    r"бесхозяйн|уведомлени|акт осмотр|акт обследован|решение суда|"
    r"администраци|муниципальн|реестр|кадастр|декрет|постановлени|"
    r"распоряжени|приказ|госуслуг",
    re.I,
)

UTILITY_CUT = re.compile(
    r"отключил|отключат|отрезали|нет воды|нет света|нет газа|нет тепла|"
    r"водоснабжен|электр|теплоснабжен|газоснабжен",
    re.I,
)

PRESENCE = re.compile(
    r"живём|живем|остались|остаёмся|остаемся|не уехали|жильцы|жители|"
    r"соседи|сосед|квартира|наша кварт|мы живём|мы живем|дом стоит|дом цел",
    re.I,
)

NEW_BUILD = re.compile(
    r"стройк|новостройк|застройщик|новый дом|строят|строится|фундамент|"
    r"кран стоит|забор поставили|огородили|плиты везут|порфир|резиденц",
    re.I,
)

APT_NUM = re.compile(r"\bкв\.?\s*№?\s*(\d{1,3})\b", re.I)
ADDR    = re.compile(
    r"(?:ул\.?\s*|улиц[ауе]\s*|пр\.?\s*|проспект[еу]?\s*|б-?р\.?\s*|бульвар[еу]?\s*)"
    r"[\w\-]+(?:\s*,\s*д\.?\s*\d+\w*)?",
    re.I,
)


def _year_month(date_str: str) -> str:
    if not date_str:
        return "unknown"
    return date_str[:7]  # "2022-03"


def _signal_flags(text: str) -> list[str]:
    flags = []
    if SIEGE.search(text):       flags.append("siege")
    if DEMOLITION.search(text):  flags.append("demolition")
    if OFFICIAL.search(text):    flags.append("official_notice")
    if UTILITY_CUT.search(text): flags.append("utility_cut")
    if PRESENCE.search(text):    flags.append("resident_presence")
    if NEW_BUILD.search(text):   flags.append("new_build")
    return flags


def main(verbose: bool = False) -> None:
    con = forensics.open_state()
    rows = con.execute(
        "SELECT url, raw_path FROM source_document "
        "WHERE source_type='telegram_building_chat_msg' AND url LIKE ? "
        "ORDER BY url",
        (f"https://t.me/{CHANNEL}/%",),
    ).fetchall()
    log.info("found %d captured messages for @%s", len(rows), CHANNEL)

    signals = []
    month_counter: Counter = Counter()
    flag_counter:  Counter = Counter()
    apt_counter:   Counter = Counter()
    media_months:  Counter = Counter()
    no_text = 0
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
            log.warning("failed to parse %s", raw_path)
            continue

        if obj.get("_") != "Message":
            service += 1
            continue

        text      = (obj.get("message") or "").strip()
        date_str  = obj.get("date") or ""
        has_media = obj.get("media") is not None
        msg_id    = obj.get("id")

        ym = _year_month(date_str)
        month_counter[ym] += 1
        if has_media:
            media_months[ym] += 1

        if not text and not has_media:
            no_text += 1
            continue

        flags = _signal_flags(text) if text else []
        apts  = APT_NUM.findall(text)
        for a in apts:
            apt_counter[a] += 1

        if flags or apts or has_media:
            rec = {
                "url":       url,
                "msg_id":    msg_id,
                "date":      date_str,
                "year_month": ym,
                "has_media": has_media,
                "flags":     flags,
                "apartments": apts,
                "text_preview": text[:300] if text else None,
            }
            signals.append(rec)
            for f in flags:
                flag_counter[f] += 1

    # Write output
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        for s in signals:
            fh.write(json.dumps(s, ensure_ascii=False) + "\n")
    log.info("wrote %d signal records to %s", len(signals), OUT)

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"@{CHANNEL}  —  {len(rows)} messages parsed")
    print(f"{'='*70}")

    print(f"\n── Message volume by month ──")
    for ym in sorted(month_counter):
        bar = "█" * (month_counter[ym] // 20)
        med = f"  [{media_months.get(ym,0):3d} media]"
        print(f"  {ym}  {month_counter[ym]:5d}  {bar}{med}")

    print(f"\n── Signal flags (keyword hits) ──")
    for flag, cnt in flag_counter.most_common():
        print(f"  {flag:<22}  {cnt:4d} messages")

    print(f"\n── Apartment numbers mentioned ──")
    for apt, cnt in apt_counter.most_common(30):
        print(f"  кв. {apt:<5}  {cnt:3d}x")

    print(f"\n── Evidentiary highlights ──")

    # Demolition hits
    demo_hits = [s for s in signals if "demolition" in s["flags"]]
    print(f"\n  DEMOLITION ({len(demo_hits)} messages):")
    for s in demo_hits[:10]:
        print(f"    {s['date'][:10]}  {s['url']}")
        if s["text_preview"]:
            print(f"      {s['text_preview'][:120]}")

    # Official notices
    off_hits = [s for s in signals if "official_notice" in s["flags"]]
    print(f"\n  OFFICIAL NOTICES ({len(off_hits)} messages):")
    for s in off_hits[:10]:
        print(f"    {s['date'][:10]}  {s['url']}")
        if s["text_preview"]:
            print(f"      {s['text_preview'][:120]}")

    # Siege-era content
    siege_hits = [s for s in signals if "siege" in s["flags"]]
    print(f"\n  SIEGE-ERA ({len(siege_hits)} messages):")
    for s in sorted(siege_hits, key=lambda x: x["date"])[:15]:
        print(f"    {s['date'][:10]}  {s['url']}")
        if s["text_preview"]:
            print(f"      {s['text_preview'][:120]}")

    # New build mentions
    nb_hits = [s for s in signals if "new_build" in s["flags"]]
    print(f"\n  NEW BUILD MENTIONS ({len(nb_hits)} messages):")
    for s in nb_hits[:10]:
        print(f"    {s['date'][:10]}  {s['url']}")
        if s["text_preview"]:
            print(f"      {s['text_preview'][:120]}")

    # Resident presence — earliest dates
    pres_hits = sorted(
        [s for s in signals if "resident_presence" in s["flags"]],
        key=lambda x: x["date"],
    )
    print(f"\n  RESIDENT PRESENCE — earliest ({len(pres_hits)} total):")
    for s in pres_hits[:10]:
        print(f"    {s['date'][:10]}  {s['url']}")
        if s["text_preview"]:
            print(f"      {s['text_preview'][:120]}")

    # Utility cut
    util_hits = [s for s in signals if "utility_cut" in s["flags"]]
    print(f"\n  UTILITY CUTS ({len(util_hits)} messages):")
    for s in sorted(util_hits, key=lambda x: x["date"])[:10]:
        print(f"    {s['date'][:10]}  {s['url']}")
        if s["text_preview"]:
            print(f"      {s['text_preview'][:120]}")

    print(f"\n── Output ──")
    print(f"  Signal records: {len(signals)}")
    print(f"  Written to:     {OUT}")
    print(f"  Service msgs skipped: {service}  |  empty (no text/media): {no_text}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main(verbose="--verbose" in sys.argv)
