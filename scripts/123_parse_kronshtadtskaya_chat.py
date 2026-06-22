#!/usr/bin/env python3
"""Parse captured "Мариуполь Кронштадтская Chat" Telegram messages.

Title recovered from the channel-create service message (msg id=1):
"Мариуполь Кронштадтская Chat". By far the largest chat captured this
session: 31,495 messages, 4,098 media.

Street-wide chat covering 16 buildings on ул. Кронштадтская:
  pid=7027  д.1    12 registry_inclusion
  pid=7207  д.2     1 registry_inclusion
  pid=7028  д.2в    1 registry_inclusion
  pid=5969  д.3     NO events (gap)
  pid=5970  д.4     4 registry_inclusion
  pid=5971  д.5     demolished
  pid=5972  д.6     1 registry_inclusion
  pid=5973  д.7    30 registry_inclusion
  pid=7186  д.7а    1 registry_inclusion
  pid=5963  д.12    demolished
  pid=5964  д.13   27 registry_inclusion
  pid=5965  д.14    2 registry_inclusion
  pid=5966  д.15   27 registry_inclusion + ownerless_designation
  pid=5967  д.17   55 registry_inclusion
  pid=7185  д.9а    2 registry_inclusion
  pid=5968  д.19   59 registry_inclusion

222 total registry_inclusion events across the street — the richest single
cross-reference target this session. Apartment cross-reference requires
both a house number AND an apartment number in the same message to bind to
a specific pid (apartment numbers alone collide across buildings).

Outputs:
  data/parsed/kronshtadtskaya_chat_signals.jsonl
  Console summary, incl. (house, apartment) cross-reference vs
  registry_inclusion events.

Run:
    python scripts/123_parse_kronshtadtskaya_chat.py
"""
import json
import logging
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

OUT          = ROOT / "data" / "parsed" / "kronshtadtskaya_chat_signals.jsonl"
CHANNEL_SLUG = "invite_ooUT61cOOFZjMDcy"

HOUSE_PIDS = {
    "1": 7027, "2": 7207, "2в": 7028, "3": 5969, "4": 5970, "5": 5971,
    "6": 5972, "7": 5973, "7а": 7186, "9а": 7185, "12": 5963, "13": 5964,
    "14": 5965, "15": 5966, "17": 5967, "19": 5968,
}

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
    r"югстройинвест|проект инвест|эволюция",
    re.I,
)
BURIAL = re.compile(
    r"трупы|погибли|тела|тел\b|захоронен|братская|могила|похоронили|"
    r"во дворе.{0,30}(труп|тел|погиб|захорон)|выкопали.{0,20}(труп|тел)|"
    r"пьем трупами|дышем трупами|живём над трупами",
    re.I,
)

APT_NUM = re.compile(r"\bкв\.?\s*№?\s*(\d{1,3})\b", re.I)
# House+apt pair in the same message — required for a confident cross-reference.
HOUSE_APT_PAIR = re.compile(
    r"кронштадтск\w*[,\s]+д?\.?\s*(\d{1,2}[авбв]?)\D{0,15}?кв\.?\s*№?\s*(\d{1,3})"
    r"|д\.?\s*(\d{1,2}[авбв]?)\s*кронштадтск\w*\D{0,15}?кв\.?\s*№?\s*(\d{1,3})",
    re.I,
)


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


def _load_registry_index(pg_dsn: str | None):
    """Load registry_inclusion events for all Кронштадтская pids, keyed by (house, apt_raw)."""
    if not pg_dsn:
        return {}
    try:
        import psycopg2
        conn = psycopg2.connect(pg_dsn)
        cur  = conn.cursor()
        cur.execute("""
            SELECT p.id, p.occupation_address, se.event_date,
                   se.detail->>'apt_raw' AS apt_num,
                   se.detail->>'decree_number' AS decree_num
            FROM seizure_event se
            JOIN property p ON p.id = se.property_id
            WHERE se.stage = 'registry_inclusion'
              AND p.id = ANY(%s)
            ORDER BY se.event_date NULLS LAST
        """, (list(HOUSE_PIDS.values()),))
        rows = cur.fetchall()
        conn.close()
        log.info("loaded %d registry_inclusion events across %d Кронштадтская buildings",
                  len(rows), len(HOUSE_PIDS))
        pid_to_house = {v: k for k, v in HOUSE_PIDS.items()}
        idx = {}
        for pid, addr, evt_date, apt_num, decree in rows:
            house = pid_to_house.get(pid)
            if house and apt_num:
                idx[(house, str(apt_num).strip())] = {
                    "pid": pid, "address": addr,
                    "event_date": str(evt_date) if evt_date else None,
                    "decree": decree,
                }
        return idx
    except Exception as e:
        log.warning("could not load registry events from PostgreSQL: %s", e)
        return {}


def main() -> None:
    con = forensics.open_state()
    registry_idx = _load_registry_index(getattr(config, "DATABASE_URL", None))

    rows = con.execute(
        "SELECT url, raw_path FROM source_document "
        "WHERE source_type='telegram_building_chat_msg' AND url LIKE ? "
        "ORDER BY url",
        (f"https://t.me/{CHANNEL_SLUG}/%",),
    ).fetchall()
    log.info("found %d captured messages", len(rows))

    signals = []
    pair_hits = []
    month_counter: Counter = Counter()
    media_months:  Counter = Counter()
    flag_counter:  Counter = Counter()
    apt_counter:   Counter = Counter()
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

        f    = _flags(text) if text else []
        apts = APT_NUM.findall(text) if text else []
        for a in apts: apt_counter[a] += 1

        if text:
            for m in HOUSE_APT_PAIR.finditer(text):
                groups = [g for g in m.groups() if g]
                if len(groups) == 2:
                    house, apt = groups
                    house = house.lower()
                    key = (house, apt)
                    if key in registry_idx:
                        pair_hits.append({
                            "msg_url": url, "date": date_str,
                            "house": house, "apt": apt,
                            **registry_idx[key],
                            "text_excerpt": text[:300],
                        })

        if f or apts or has_media:
            rec = {
                "url": url, "msg_id": msg_id, "date": date_str,
                "year_month": ym, "has_media": has_media,
                "flags": f, "apartments": apts,
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
    print(f"Мариуполь Кронштадтская Chat  —  {len(rows)} messages parsed")
    print(f"16 buildings, 222 registry_inclusion events + 2 demolished")
    print(f"{'='*70}")

    print("\n── Message volume by month ──")
    for ym in sorted(month_counter):
        bar = "█" * (month_counter[ym] // 50)
        print(f"  {ym}  {month_counter[ym]:6d}  {bar}  [{media_months.get(ym,0):4d} media]")

    print("\n── Signal flags ──")
    for flag, cnt in flag_counter.most_common():
        print(f"  {flag:<26}  {cnt:5d}")

    print("\n── Apartment numbers mentioned (top 30) ──")
    for apt, cnt in apt_counter.most_common(30):
        print(f"  кв.{apt:<5}  {cnt}x")

    if pair_hits:
        print(f"\n{'─'*70}")
        print(f"HOUSE+APARTMENT CROSS-REFERENCE vs registry_inclusion  ({len(pair_hits)} hits)")
        print(f"{'─'*70}")
        for h in sorted(pair_hits, key=lambda x: x["date"])[:50]:
            print(f"\n  д.{h['house']} кв.{h['apt']}  ({h['address']})")
            print(f"    chat message  : {h['date'][:10]}  {h['msg_url']}")
            print(f"    registry evt  : {h.get('event_date') or 'date unknown'}  decree={h.get('decree')}")
            if h["text_excerpt"]:
                print(f"    excerpt       : {h['text_excerpt'][:180]}")
    else:
        print("\n  (House+apartment cross-reference: no hits — pattern may need tuning "
              "for this chat's address-mention style)")

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
        for s in sorted(hits, key=lambda x: x["date"])[:15]:
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
