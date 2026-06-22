#!/usr/bin/env python3
"""Parse captured "Митрополитская 102" Telegram messages.

Title confirmed exact from the channel-migration service message (msg id=1):
"Митрополитская 102". SPINE GAP: no exact match for "Митрополитская, 102" in
property.occupation_address. Closest entries on the same street:
  pid=13982  ул. Митрополитская, 98                    rd4u=A3.1,A3.6
  pid=10654  УЛ. К.ЛИБКНЕХТА (МИТРОПОЛИТСКАЯ), 1        rd4u=A3.3,A3.6
  pid=10655  УЛ. К.ЛИБКНЕХТА (МИТРОПОЛИТСКАЯ), 23       rd4u=A3.3,A3.6
  pid=10656  УЛ. К.ЛИБКНЕХТА (МИТРОПОЛИТСКАЯ), 31       rd4u=A3.3,A3.6
д.102 is not yet loaded — this run is unmapped to a pid pending that gap
being filled (check the demolition register / ownerless registry for
"Митрополитская, 102" or "К.Либкнехта, 102" entries).

Crawl capped at 2023-02-28 per user direction.

Outputs:
  data/parsed/mitropolitskaya102_chat_signals.jsonl
  Console summary

Run:
    python scripts/102_parse_mitropolitskaya102_chat.py
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

OUT          = ROOT / "data" / "parsed" / "mitropolitskaya102_chat_signals.jsonl"
CHANNEL_SLUG = "Mitropolitskaya102"

SIEGE = re.compile(
    r"подвал|бомбёжк|бомбежк|обстрел|прилёт|прилет|снаряд|ракет|взрыв|"
    r"эвакуац|укрыт|убежищ|без света|без воды|без газ|без тепл|"
    r"март|апрел|май 2022|2022\s*год|весна 2022|осада|штурм",
    re.I,
)
DEMOLITION = re.compile(
    r"снос|сносят|снесли|снесут|демонтаж|разбор|расселени|расселяют|расселили|"
    r"выселени|выселяют|выселили|аварийн|признан|непригодн|подлежит|снести",
    re.I,
)
OFFICIAL = re.compile(
    r"уведомлени|акт осмотр|акт обследован|решение суда|администраци|"
    r"муниципальн|декрет|постановлени|распоряжени|приказ|госуслуг|"
    r"Кольцов|Иващенко|Моргун",
    re.I,
)
OWNERLESS = re.compile(
    r"бесхозяйн|бесхоз|признали|муниципальн.{0,20}собствен|"
    r"передали городу|передали муниципали|собственность города|"
    r"отобрали квартир|изъяли|изъять|конфисков",
    re.I,
)
REGISTRATION = re.compile(
    r"госуслуг|ЕГРН|росреестр|кадастр|реестр|регистрац|свидетельство|"
    r"выписка|перерегистрац|смена собственн",
    re.I,
)
SEALING = re.compile(
    r"опечатал|пломб|запечатал|закрыли акт|замок сменил|"
    r"в квартиру не попасть|доступ закрыт|заварили|заколотили",
    re.I,
)
UTILITY_CUT = re.compile(
    r"отключил|отключат|отрезали|нет воды|нет света|нет газа|нет тепла|"
    r"водоснабжен|электр|теплоснабжен|газоснабжен",
    re.I,
)
PRESENCE = re.compile(
    r"живём|живем|остались|остаёмся|остаемся|не уехали|жильцы|жители|"
    r"соседи|сосед|квартира|наша кварт|мы живём|мы живем|дом стоит|дом цел|"
    r"хозяин|хозяйка|владелец|собственник|я живу|люди живут",
    re.I,
)
COMPENSATION = re.compile(
    r"компенсац|выплат|возмещени|жильё дадут|жильё дают|получить жильё|"
    r"сертификат|жилищн|субсиди|очередь на жильё|постановка на учёт|"
    r"временное жильё|манёвренн",
    re.I,
)
NEW_BUILD = re.compile(
    r"стройк|новостройк|застройщик|новый дом|строят|строится|фундамент|"
    r"кран стоит|забор поставили|огородили|плиты везут|порфир|ПОРФИР|"
    r"югстройинвест",
    re.I,
)
BURIAL = re.compile(
    r"трупы|погибли|тела|тел\b|захоронен|братская|могила|похоронили|"
    r"во дворе.{0,30}(труп|тел|погиб|захорон)|выкопали.{0,20}(труп|тел)|"
    r"пьем трупами|дышем трупами|живём над трупами",
    re.I,
)

APT_NUM  = re.compile(r"\bкв\.?\s*№?\s*(\d{1,3})\b", re.I)
BLDG_NUM = re.compile(r"\b(?:д\.?\s*|дом\s*)(102)\b", re.I)


def _ym(date_str: str) -> str:
    return date_str[:7] if date_str else "unknown"


def _flags(text: str) -> list[str]:
    out = []
    if SIEGE.search(text):        out.append("siege")
    if DEMOLITION.search(text):   out.append("demolition")
    if OFFICIAL.search(text):     out.append("official_notice")
    if OWNERLESS.search(text):    out.append("ownerless_process")
    if REGISTRATION.search(text): out.append("registration")
    if SEALING.search(text):      out.append("sealing")
    if UTILITY_CUT.search(text):  out.append("utility_cut")
    if PRESENCE.search(text):     out.append("resident_presence")
    if COMPENSATION.search(text): out.append("compensation")
    if NEW_BUILD.search(text):    out.append("new_build")
    if BURIAL.search(text):       out.append("burial")
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
        apts  = APT_NUM.findall(text) if text else []
        bldgs = BLDG_NUM.findall(text) if text else []
        for a in apts:  apt_counter[a]  += 1
        for b in bldgs: bldg_counter[b] += 1

        if f or apts or bldgs or has_media:
            rec = {
                "url": url, "msg_id": msg_id, "date": date_str,
                "year_month": ym, "has_media": has_media,
                "flags": f, "apartments": apts, "buildings_mentioned": bldgs,
                "text_preview": text[:400] if text else None,
            }
            signals.append(rec)
            for fl in f:
                flag_counter[fl] += 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        for s in signals:
            fh.write(json.dumps(s, ensure_ascii=False) + "\n")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"Митрополитская 102  —  {len(rows)} messages parsed (capped at 2023-02-28)")
    print("SPINE GAP: pid for д.102 not yet loaded (closest: д.98, д.1/23/31)")
    print(f"{'='*70}")

    print("\n── Message volume by month ──")
    for ym in sorted(month_counter):
        bar = "█" * (month_counter[ym] // 10)
        print(f"  {ym}  {month_counter[ym]:5d}  {bar}  [{media_months.get(ym,0):3d} media]")

    print("\n── Signal flags ──")
    for flag, cnt in flag_counter.most_common():
        print(f"  {flag:<26}  {cnt:4d}")

    print("\n── Building numbers mentioned ──")
    for b, cnt in sorted(bldg_counter.items()):
        print(f"  д.{b}  {cnt}x")

    print("\n── Apartment numbers mentioned (top 30) ──")
    for apt, cnt in apt_counter.most_common(30):
        print(f"  кв.{apt:<5}  {cnt}x")

    for label, flag in [
        ("BURIAL / DEATH REFS", "burial"),
        ("OWNERLESS PROCESS", "ownerless_process"),
        ("SEALING EVENTS", "sealing"),
        ("OFFICIAL NOTICES", "official_notice"),
        ("DEMOLITION", "demolition"),
        ("NEW BUILD", "new_build"),
        ("COMPENSATION", "compensation"),
    ]:
        hits = [s for s in signals if flag in s["flags"]]
        if not hits:
            continue
        print(f"\n── {label} ({len(hits)} messages) ──")
        for s in sorted(hits, key=lambda x: x["date"])[:12]:
            print(f"  {s['date'][:10]}  {s['url']}")
            if s["text_preview"]:
                print(f"    {s['text_preview'][:220]}")

    print("\n── RESIDENT PRESENCE — earliest 15 ──")
    for s in sorted([s for s in signals if "resident_presence" in s["flags"]], key=lambda x: x["date"])[:15]:
        print(f"  {s['date'][:10]}  {s['url']}")
        if s["text_preview"]:
            print(f"    {s['text_preview'][:200]}")

    print("\n── SIEGE-ERA — earliest 10 ──")
    for s in sorted([s for s in signals if "siege" in s["flags"]], key=lambda x: x["date"])[:10]:
        print(f"  {s['date'][:10]}  {s['url']}")
        if s["text_preview"]:
            print(f"    {s['text_preview'][:200]}")

    print(f"\n── Output ──")
    print(f"  {len(signals)} signal records → {OUT}")
    print(f"  service msgs skipped: {service}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
