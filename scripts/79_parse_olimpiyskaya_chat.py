#!/usr/bin/env python3
"""Parse captured "Олимпийская д.71,73,75,77,79" Telegram messages for evidentiary signals.

Reads raw message JSON from data/raw/ (captured by script 78) and applies signal
extraction adapted for the TITLE-STRIPPING track (NOT demolished):
  - Five buildings still standing; apartments being declared бесхозяйные one-by-one
  - д.77 has 96 ownerless events, д.79 has 76 ownerless events in the registry
  - Primary evidentiary value: residents present WHILE apartments declared ownerless
    → directly rebuts the "abandoned" predicate for RD4U A3.6 / Art.8 purposes

Key additions vs scripts 76/77:
  OWNERLESS regex   — residents describing the бесхозяйность process
  REGISTRATION regex — госуслуги, реестр, ЕГРН references
  SEALING regex      — пломб/опечатан/закрыт актом (physical sealing events)
  BUILDING numbers   — д.71/73/75/77/79

Date window covered: 2022-01-01 → 2024-05-31 (~17,487 messages in the group).

Outputs:
  Console summary with evidentiary highlights
  data/parsed/olimpiyskaya_chat_signals.jsonl

Run AFTER script 78 completes:
    python scripts/79_parse_olimpiyskaya_chat.py
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

OUT          = ROOT / "data" / "parsed" / "olimpiyskaya_chat_signals.jsonl"
CHANNEL_SLUG = "olimpiyskaya_71_79"

# ── Signal keyword groups ──────────────────────────────────────────────────────

SIEGE = re.compile(
    r"подвал|бомбёжк|бомбежк|обстрел|прилёт|прилет|снаряд|ракет|взрыв|"
    r"эвакуац|укрыт|убежищ|без света|без воды|без газ|без тепл|"
    r"март|апрел|май 2022|2022\s*год|весна 2022",
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
    r"Кольцов|Иващенко|Моргун|Кириленко",
    re.I,
)
OWNERLESS = re.compile(
    r"бесхозяйн|бесхоз|признали|муниципальн.{0,20}собствен|"
    r"признание права|передали городу|передали муниципали|собственность города|"
    r"отобрали квартир|изъяли|изъять|конфисков",
    re.I,
)
REGISTRATION = re.compile(
    r"госуслуг|ЕГРН|росреестр|кадастр|реестр|регистрац|свидетельство|"
    r"выписка|перерегистрац|смена собственн",
    re.I,
)
SEALING = re.compile(
    r"опечатал|пломб|запечатал|закрыли акт|вскрытие|замок сменил|"
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
    r"хозяин|хозяйка|владелец|собственник|я живу|мы живём|люди живут",
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
    r"кран стоит|забор поставили|огородили|плиты везут",
    re.I,
)

APT_NUM  = re.compile(r"\bкв\.?\s*№?\s*(\d{1,3})\b", re.I)
BLDG_NUM = re.compile(r"\b(?:д\.?\s*|дом\s*)(71|73|75|77|79)\b", re.I)


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
    print(f"Олимпийская д.71/73/75/77/79  —  {len(rows)} messages parsed")
    print(f"{'='*70}")

    print("\n── Message volume by month ──")
    for ym in sorted(month_counter):
        bar = "█" * (month_counter[ym] // 10)
        print(f"  {ym}  {month_counter[ym]:5d}  {bar}  [{media_months.get(ym,0):3d} media]")

    print("\n── Signal flags ──")
    for flag, cnt in flag_counter.most_common():
        print(f"  {flag:<26}  {cnt:4d}")

    print("\n── Building numbers mentioned (д.71/73/75/77/79) ──")
    for b, cnt in sorted(bldg_counter.items(), key=lambda x: int(x[0])):
        print(f"  д.{b}  {cnt}x")

    print("\n── Apartment numbers mentioned (top 30) ──")
    for apt, cnt in apt_counter.most_common(30):
        print(f"  кв.{apt:<5}  {cnt}x")

    # Key evidence sections
    for label, flag in [
        ("OWNERLESS PROCESS", "ownerless_process"),
        ("SEALING EVENTS", "sealing"),
        ("REGISTRATION / REGISTRY", "registration"),
        ("OFFICIAL NOTICES", "official_notice"),
        ("DEMOLITION THREAT", "demolition"),
        ("COMPENSATION", "compensation"),
    ]:
        hits = [s for s in signals if flag in s["flags"]]
        if not hits:
            continue
        print(f"\n── {label} ({len(hits)} messages) ──")
        for s in sorted(hits, key=lambda x: x["date"])[:15]:
            print(f"  {s['date'][:10]}  {s['url']}")
            if s["text_preview"]:
                print(f"    {s['text_preview'][:200]}")

    print("\n── RESIDENT PRESENCE — earliest 15 ──")
    pres = sorted([s for s in signals if "resident_presence" in s["flags"]], key=lambda x: x["date"])
    for s in pres[:15]:
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
