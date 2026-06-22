#!/usr/bin/env python3
"""Parse captured "Морской 38, 36, 30" Telegram messages for evidentiary signals.

Reads raw message JSON from data/raw/ (captured by script 75) and applies the
same signal extraction as script 76 (Azovstalskaya31), adapted for three buildings:
  бульвар Морской (Комсомольский), д.30 / д.36 / д.38
  pid=10724 (д.38); д.30 and д.36 not yet in spine.

Outputs:
  Console summary
  data/parsed/morskoy_chat_signals.jsonl

Run:
    python scripts/77_parse_morskoy_chat.py
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

OUT          = ROOT / "data" / "parsed" / "morskoy_chat_signals.jsonl"
CHANNEL_SLUG = "morskoy_38_36_30"

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
COMPENSATION = re.compile(
    r"компенсац|выплат|возмещени|жильё (дадут|дают|получить)|"
    r"сертификат|жилищн|субсиди|очередь на жильё|постановка на учёт",
    re.I,
)

APT_NUM = re.compile(r"\bкв\.?\s*№?\s*(\d{1,3})\b", re.I)
BLDG_NUM = re.compile(r"\b(?:д\.?\s*|дом\s*)(30|36|38)\b", re.I)


def _ym(date_str: str) -> str:
    return date_str[:7] if date_str else "unknown"


def _flags(text: str) -> list[str]:
    out = []
    if SIEGE.search(text):        out.append("siege")
    if DEMOLITION.search(text):   out.append("demolition")
    if OFFICIAL.search(text):     out.append("official_notice")
    if UTILITY_CUT.search(text):  out.append("utility_cut")
    if PRESENCE.search(text):     out.append("resident_presence")
    if NEW_BUILD.search(text):    out.append("new_build")
    if COMPENSATION.search(text): out.append("compensation")
    return out


def main() -> None:
    con = forensics.open_state()
    rows = con.execute(
        "SELECT url, raw_path FROM source_document "
        "WHERE source_type='telegram_building_chat_msg' AND url LIKE ? "
        "ORDER BY url",
        (f"https://t.me/{CHANNEL_SLUG}/%",),
    ).fetchall()
    log.info("found %d captured messages", len(rows))

    signals = []
    month_counter: Counter = Counter()
    media_months:  Counter = Counter()
    flag_counter:  Counter = Counter()
    apt_counter:   Counter = Counter()
    bldg_counter:  Counter = Counter()
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

        text      = (obj.get("message") or "").strip()
        date_str  = obj.get("date") or ""
        has_media = obj.get("media") is not None
        msg_id    = obj.get("id")

        ym = _ym(date_str)
        month_counter[ym] += 1
        if has_media:
            media_months[ym] += 1

        f     = _flags(text) if text else []
        apts  = APT_NUM.findall(text)
        bldgs = BLDG_NUM.findall(text)
        for a in apts:  apt_counter[a]  += 1
        for b in bldgs: bldg_counter[b] += 1

        if f or apts or bldgs or has_media:
            rec = {
                "url": url, "msg_id": msg_id, "date": date_str,
                "year_month": ym, "has_media": has_media,
                "flags": f, "apartments": apts, "buildings_mentioned": bldgs,
                "text_preview": text[:300] if text else None,
            }
            signals.append(rec)
            for fl in f:
                flag_counter[fl] += 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        for s in signals:
            fh.write(json.dumps(s, ensure_ascii=False) + "\n")

    # ── Print summary ─────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"Морской 38/36/30  —  {len(rows)} messages parsed")
    print(f"{'='*70}")

    print("\n── Message volume by month ──")
    for ym in sorted(month_counter):
        bar = "█" * (month_counter[ym] // 10)
        print(f"  {ym}  {month_counter[ym]:5d}  {bar}  [{media_months.get(ym,0):3d} media]")

    print("\n── Signal flags ──")
    for flag, cnt in flag_counter.most_common():
        print(f"  {flag:<22}  {cnt:4d}")

    print("\n── Building numbers mentioned (д.30/36/38) ──")
    for b, cnt in sorted(bldg_counter.items()):
        print(f"  д.{b}  {cnt}x")

    print("\n── Apartment numbers mentioned ──")
    for apt, cnt in apt_counter.most_common(20):
        print(f"  кв.{apt:<5}  {cnt}x")

    for label, flag in [
        ("DEMOLITION", "demolition"),
        ("OFFICIAL NOTICES", "official_notice"),
        ("COMPENSATION", "compensation"),
        ("NEW BUILD", "new_build"),
    ]:
        hits = [s for s in signals if flag in s["flags"]]
        print(f"\n── {label} ({len(hits)} messages) ──")
        for s in hits[:12]:
            print(f"  {s['date'][:10]}  {s['url']}")
            if s["text_preview"]:
                print(f"    {s['text_preview'][:140]}")

    print("\n── SIEGE-ERA — earliest 15 ──")
    for s in sorted([s for s in signals if "siege" in s["flags"]], key=lambda x: x["date"])[:15]:
        print(f"  {s['date'][:10]}  {s['url']}")
        if s["text_preview"]:
            print(f"    {s['text_preview'][:140]}")

    print("\n── RESIDENT PRESENCE — earliest 10 ──")
    for s in sorted([s for s in signals if "resident_presence" in s["flags"]], key=lambda x: x["date"])[:10]:
        print(f"  {s['date'][:10]}  {s['url']}")
        if s["text_preview"]:
            print(f"    {s['text_preview'][:140]}")

    print(f"\n── Output ──")
    print(f"  {len(signals)} signal records → {OUT}")
    print(f"  service msgs skipped: {service}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
