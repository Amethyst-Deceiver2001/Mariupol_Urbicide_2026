#!/usr/bin/env python3
"""Parse captured "Котляревского_NOWAR" Telegram messages.

ул. Котляревского, 6 buildings: pid=4920(2,none),4921(4,registry_inclusion),4922(6,demolished),4923(8,demolished),4924(8а,registry_inclusion),6110(10,none).

Run:
    python scripts/146_parse_kotlyarevskogo_chat.py
"""
import json, logging, re, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)
OUT          = ROOT / "data" / "parsed" / "kotlyarevskogo_chat_signals.jsonl"
CHANNEL_SLUG = "invite_SWCkzbFpPJBkODBi"
PIDS         = {4920: 4920, 4921: 4921, 4922: 4922, 4923: 4923, 4924: 4924, 6110: 6110}

SIEGE = re.compile(r"подвал|бомбёжк|бомбежк|обстрел|прилёт|прилет|снаряд|ракет|взрыв|эвакуац|укрыт|убежищ|без света|без воды|без газ|без тепл|март|апрел|май 2022|2022\s*год|весна 2022|осада|штурм", re.I)
DEMOLITION = re.compile(r"снос|сносят|снесли|снесут|демонтаж|разбор|расселени|расселяют|расселили|выселени|выселяют|выселили|аварийн|признан|непригодн|подлежит|снести", re.I)
OFFICIAL = re.compile(r"уведомлени|акт осмотр|акт обследован|решение суда|администраци|муниципальн|декрет|постановлени|распоряжени|приказ|госуслуг|Кольцов|Иващенко|Моргун", re.I)
OWNERLESS = re.compile(r"бесхозяйн|бесхоз|признали|муниципальн.{0,20}собствен|передали городу|передали муниципали|собственность города|отобрали квартир|изъяли|изъять|конфисков", re.I)
REGISTRATION = re.compile(r"госуслуг|ЕГРН|росреестр|кадастр|реестр|регистрац|свидетельство|выписка|перерегистрац|смена собственн", re.I)
SEALING = re.compile(r"опечатал|пломб|запечатал|закрыли акт|замок сменил|в квартиру не попасть|доступ закрыт|заварили|заколотили", re.I)
UTILITY_CUT = re.compile(r"отключил|отключат|отрезали|нет воды|нет света|нет газа|нет тепла|водоснабжен|электр|теплоснабжен|газоснабжен", re.I)
PRESENCE = re.compile(r"живём|живем|остались|остаёмся|остаемся|не уехали|жильцы|жители|соседи|сосед|квартира|наша кварт|мы живём|мы живем|дом стоит|дом цел|хозяин|хозяйка|владелец|собственник|я живу|люди живут", re.I)
COMPENSATION = re.compile(r"компенсац|выплат|возмещени|жильё дадут|жильё дают|получить жильё|сертификат|жилищн|субсиди|очередь на жильё|постановка на учёт|временное жильё|манёвренн", re.I)
NEW_BUILD = re.compile(r"стройк|новостройк|застройщик|новый дом|строят|строится|фундамент|кран стоит|забор поставили|огородили|плиты везут|порфир|ПОРФИР|югстройинвест|проект инвест|эволюция|мираполис|мирастрой|темп|сириус", re.I)
BURIAL = re.compile(r"трупы|погибли|тела|тел\b|захоронен|братская|могила|похоронили|во дворе.{0,30}(труп|тел|погиб|захорон)|выкопали.{0,20}(труп|тел)|пьем трупами|дышем трупами|живём над трупами", re.I)
APT_NUM = re.compile(r"\bкв\.?\s*№?\s*(\d{1,3})\b", re.I)

def _ym(d): return d[:7] if d else "unknown"
def _flags(t):
    out=[]
    for name,pat in [("siege",SIEGE),("demolition",DEMOLITION),("official_notice",OFFICIAL),
                      ("ownerless_process",OWNERLESS),("registration",REGISTRATION),("sealing",SEALING),
                      ("utility_cut",UTILITY_CUT),("resident_presence",PRESENCE),("compensation",COMPENSATION),
                      ("new_build",NEW_BUILD),("burial",BURIAL)]:
        if pat.search(t): out.append(name)
    return out

def _load_registry_idx(pg_dsn):
    if not pg_dsn or not PIDS: return {}
    try:
        import psycopg2
        conn = psycopg2.connect(pg_dsn); cur = conn.cursor()
        cur.execute("""SELECT property_id, event_date, detail->>'apt_raw', detail->>'decree_number'
                       FROM seizure_event WHERE stage='registry_inclusion' AND property_id = ANY(%s)""",
                    (list(PIDS.values()),))
        rows = cur.fetchall(); conn.close()
        idx = {}
        for pid, d, apt, dec in rows:
            if apt: idx[(pid, str(apt).strip())] = {"event_date": str(d) if d else None, "decree": dec}
        log.info("loaded %d registry_inclusion events", len(rows))
        return idx
    except Exception as e:
        log.warning("registry load failed: %s", e); return {}

def main():
    con = forensics.open_state()
    registry_idx = _load_registry_idx(getattr(config, "DATABASE_URL", None))
    rows = con.execute("SELECT url, raw_path FROM source_document WHERE source_type='telegram_building_chat_msg' AND url LIKE ? ORDER BY url", (f"https://t.me/{CHANNEL_SLUG}/%",)).fetchall()
    log.info("found %d captured messages", len(rows))
    signals=[]; apt_hits=[]; month_counter=Counter(); media_months=Counter(); flag_counter=Counter(); apt_counter=Counter(); service=0
    for url, raw_path in rows:
        if not raw_path: continue
        p = ROOT / raw_path
        if not p.exists(): continue
        try: obj = json.loads(p.read_bytes())
        except Exception: continue
        if obj.get("_") != "Message": service+=1; continue
        text=(obj.get("message") or "").strip(); date_str=obj.get("date") or ""; has_media=obj.get("media") is not None; msg_id=obj.get("id")
        ym=_ym(date_str); month_counter[ym]+=1
        if has_media: media_months[ym]+=1
        f=_flags(text) if text else []; apts=APT_NUM.findall(text) if text else []
        for a in apts: apt_counter[a]+=1
        for a in apts:
            for pid in PIDS.values():
                key=(pid,a)
                if key in registry_idx:
                    apt_hits.append({"msg_url":url,"date":date_str,"pid":pid,"apt":a,**registry_idx[key],"text_excerpt":text[:300]})
        if f or apts or has_media:
            signals.append({"url":url,"msg_id":msg_id,"date":date_str,"year_month":ym,"has_media":has_media,"flags":f,"apartments":apts,"text_preview":text[:400] if text else None})
            for fl in f: flag_counter[fl]+=1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        for s in signals: fh.write(json.dumps(s, ensure_ascii=False)+"\n")
    print(f"\n{'='*70}\n'Котляревского_NOWAR'  —  {len(rows)} messages parsed\n{'='*70}")
    print("\n── Message volume by month ──")
    for ym in sorted(month_counter):
        bar="█"*(month_counter[ym]//10)
        print(f"  {ym}  {month_counter[ym]:5d}  {bar}  [{media_months.get(ym,0):3d} media]")
    print("\n── Signal flags ──")
    for flag,cnt in flag_counter.most_common(): print(f"  {flag:<26}  {cnt:4d}")
    print("\n── Apartment numbers (top 30) ──")
    for apt,cnt in apt_counter.most_common(30): print(f"  кв.{apt:<5}  {cnt}x")
    if apt_hits:
        print(f"\n── APARTMENT CROSS-REFERENCE ({len(apt_hits)} hits) ──")
        for h in sorted(apt_hits, key=lambda x:x["date"])[:30]:
            print(f"\n  pid={h['pid']} кв.{h['apt']}")
            print(f"    chat: {h['date'][:10]} {h['msg_url']}")
            print(f"    registry evt: {h.get('event_date') or 'unknown'} decree={h.get('decree')}")
            if h["text_excerpt"]: print(f"    excerpt: {h['text_excerpt'][:180]}")
    for label,flag in [("BURIAL","burial"),("OWNERLESS","ownerless_process"),("SEALING","sealing"),
                        ("OFFICIAL","official_notice"),("DEMOLITION","demolition"),("NEW BUILD","new_build"),("COMPENSATION","compensation")]:
        hits=[s for s in signals if flag in s["flags"]]
        if not hits: continue
        print(f"\n── {label} ({len(hits)}) ──")
        for s in sorted(hits, key=lambda x:x["date"])[:12]:
            print(f"  {s['date'][:10]}  {s['url']}")
            if s["text_preview"]: print(f"    {s['text_preview'][:220]}")
    print("\n── RESIDENT PRESENCE — earliest 15 ──")
    for s in sorted([s for s in signals if "resident_presence" in s["flags"]], key=lambda x:x["date"])[:15]:
        print(f"  {s['date'][:10]}  {s['url']}")
        if s["text_preview"]: print(f"    {s['text_preview'][:200]}")
    print("\n── SIEGE-ERA — earliest 10 ──")
    for s in sorted([s for s in signals if "siege" in s["flags"]], key=lambda x:x["date"])[:10]:
        print(f"  {s['date'][:10]}  {s['url']}")
        if s["text_preview"]: print(f"    {s['text_preview'][:200]}")
    print(f"\n── Output ──\n  {len(signals)} signal records → {OUT}\n  service msgs skipped: {service}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
