#!/usr/bin/env python3
"""Consolidate the 2026-07 @mariupol_nash mining session into one flagged set.

Read-only, local, no network. Re-runs every productive pattern found during
the manual mining session (see docs/nash_channel_findings_2026-07.md) in a
single pass over the captured `telegram_nash_msg` raw store, tags each message
by signal type, and emits:

  1. data/parsed/nash_flagged_messages.jsonl — one row per message that hit at
     least one signal pattern (or is on the curated LEADS list), with all tags,
     any curated lead-note, the media kind + byte size, and a text excerpt.
  2. data/parsed/nash_media_pull_manifest.jsonl — the subset of flagged rows
     that carry a PHOTO (small, evidentiary) or a curated high-value VIDEO, i.e.
     the targets a media-pull run (scripts/226) should fetch WITHOUT downloading
     the channel's ~1,000 unrelated videos. Each row carries msg_id, media kind,
     and size so the puller can enforce a byte cap.
  3. console summary — counts per signal, media breakdown, curated-lead status.

The pattern taxonomy here is the reusable output of the session — it is mirrored
in docs/mariupol_channel_research_terms.md so the SAME sweep can be pointed at
any other captured Telegram channel by swapping SOURCE_TYPE.

Run (safe, read-only):
    PYTHONPATH=src python scripts/225_nash_flag_and_media_manifest.py
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
OUT_FLAGGED = ROOT / "data" / "parsed" / "nash_flagged_messages.jsonl"
OUT_MANIFEST = ROOT / "data" / "parsed" / "nash_media_pull_manifest.jsonl"

# ── SIGNAL PATTERNS ─────────────────────────────────────────────────────────
# Each (tag, high_value, regex). high_value tags are the ones whose mere
# presence flags a message; contextual tags only annotate. Anchored/co-occurrence
# patterns (a AND b) are written as two-part checks in _tags_for(), not here.
SIGNALS = [
    # core seizure lifecycle — highest signal, low noise
    ("ownerless",       True,  re.compile(r"бесхозя\w*|бесхозн\w*", re.I)),
    ("manevr_fond",     True,  re.compile(r"маневренн\w*\s+фонд\w*|маневренн\w*\s+жил", re.I)),
    ("removal_register",True,  re.compile(r"снят\w*\s+с\s+учёт|снят\w*\s+с\s+учет|обращ\w*\s+в\s+муниципальн\w*\s+собственност|изыма\w*\s+с\s+обращен", re.I)),
    ("forced_entry",    True,  re.compile(r"вскрыл|с полицией|в присутствии полиции|взлома\w*\s+дверь|срезал\w*\s+замок|порядок\s+вскрыт", re.I)),
    ("sealing",         True,  re.compile(r"опечат|пломб|запечат", re.I)),
    # military / state builder — the Nevsky-track signal
    ("military_builder",True,  re.compile(r"военн\w*\s+строит\w*|военно[\-\s]?строит\w*|\bВСК\b|Минобороны|МО\s*РФ|Оборонспецстрой|ОборонСпецСтрой", re.I)),
    # residential complexes & new-build
    ("zhk",             True,  re.compile(r"\bЖК\s*[«\"]|микрорайон\w*\s+[«\"А-ЯЁ]|новостройк|жилой\s+комплекс", re.I)),
    # resident-submitted testimony (channel's own tags)
    ("testimony",       True,  re.compile(r"#нампишут|#сообщают|#крикдуши|#отподписчика|#жалоба|#нужнапомощь|#какбыть", re.I)),
    # power of attorney / diaspora owners acting remotely
    ("poa",             True,  re.compile(r"доверенност\w*", re.I)),
    # fraud with property nexus
    ("fraud",           True,  re.compile(r"мошенн\w*|афер\w*", re.I)),
    # de-Ukrainianization / street renaming (a documented court-loss vector)
    ("renaming",        True,  re.compile(r"переименова\w*\s+улиц|переименова\w*\s+проспект|аннулир\w*\s+незаконн\w*\s+судебн", re.I)),
    # contextual-only (annotate, do not by themselves flag)
    ("demolition_ctx",  False, re.compile(r"\bснос\w*|снесл\w*|снесут|демонтаж\w*", re.I)),
    ("collapse_ctx",    False, re.compile(r"обруш\w*|обвал\w*|трещин\w*|треснул\w*|аварийн\w*", re.I)),
    ("passport_ctx",    False, re.compile(r"паспорт\w*|гражданств\w*", re.I)),
    ("compensation_ctx",False, re.compile(r"компенсац\w*|сертификат\w*|ипотек\w*", re.I)),
    ("court_ctx",       False, re.compile(r"\bсуд\b|судебн\w*|\bиск[аеомуй]{0,3}\b|апелляц\w*|кассац\w*|прокуратур\w*", re.I)),
    ("notary_ctx",      False, re.compile(r"нотариус\w*|нотариальн\w*", re.I)),
    ("citizenship_gate_ctx", False, re.compile(r"спец\w*\s+разрешени|разрешени\w*\s+на\s+(регистрац|распоряжен)|коллегиальн\w*\s+орган", re.I)),
]

# property nexus, used to promote otherwise-noisy contextual tags to flags
PROPERTY_NEXUS = re.compile(
    r"квартир\w*|недвижимост\w*|собственност\w*|имуществ\w*|жиль\w*|дом[а-я]?\b|"
    r"бесхоз\w*|переименова\w*|застройщик\w*|компенсац\w*",
    re.I,
)

# legal-instrument citation, anchored (instrument-type word must precede №)
LEGAL_RX = re.compile(
    r"(Указ|Распоряжени\w*|Постановлени\w*|Решени\w*|Приказ\w*|Закон\w*|ГКО)"
    r"[^\n.№]{0,40}?№\s*([0-9][0-9\-/А-Яа-я.]*)",
    re.I,
)

# named legal entity (construction-context filtered downstream)
ENTITY_RX = re.compile(
    r"(ООО|АО|ЗАО|ОАО|ПАО|ГУП|МУП|ФГУП|ППК)\s*[«\"]([^»\"]{2,60})[»\"]", re.U)
BUILDER_HINT = re.compile(
    r"строит\w*|застройщик|восстанавл\w*|возвод\w*|подрядчик|девелоп|СЗ\b|"
    r"специализированн\w*\s+застройщик|ремонт", re.I)

# ── CURATED LEADS ───────────────────────────────────────────────────────────
# Standout messages surfaced this session, each guaranteed into the output with
# a one-line note even if the regexes above ever change. msg_id -> note.
LEADS = {
    # bezkhoz / policy
    "134412": "Admin investigating ownership of former 'railway workers hospital' — designation-in-progress",
    "145593": "Mariupol to AUCTION ownerless COMMERCIAL real estate — first commercial-auction endpoint reference",
    "158705": "'more than 6,000' ownerless apartments to be distributed to needy — reconcile vs 12,948",
    "160632": "developers hand over 2% of new-build units to municipality — distinct mechanism",
    "167428": "sports/winter-swimming club building tagged bezkhoz + told it'll be demolished — non-residential victim class",
    "156241": "Putin law applies to all 4 regions, до 2030; recipient list силовики/военные/чиновники/учителя/врачи",
    "109055": "Morgun on-record: 'а вдруг придёт собственник?... Мы действуем в рамках закона' — self-incrimination quote",
    "177366": "2026-06-06 актуальный bezkhoz перечень (jointly жилой/нежилой), MIZO пер. Черноморский 10",
    "167525": "12948 адресов bezkhoz list, 17.03.2026 — direct primary corroboration of STATS.md figure",
    "168833": "8163 combined жилой+нежилой list, 27.03.2026 — office moved УЖКХ->МИЗО; count-discrepancy to reconcile",
    # registration freeze (№341/№307)
    "82512":  "AG_DPR admits ГКО №341 'техническая накладка' froze property registration DNR-wide",
    "85263":  "Пушилин Указ №307 to resolve registration suspended by ГКО №341",
    "88180":  "affected owners file with Head's Administration; ОНФ involved — №341 freeze remediation",
    # prosecutor / court / civil resistance
    "91318":  "activist Sania Denisova organizing collective prosecutor letters for demolished/bezkhoz owners",
    "116648": "пр. Ленина 97 — 7 apts refuse to vacate; coercion-via-repair-logistics eviction pressure",
    "154471": "ВС ДНР REJECTED collective suit vs renaming Азовстальская->пр. Тульский — de-Ukrainianization court loss",
    "64952":  "Novinsky (Akhmetov partner) ECtHR claim over Амстор supermarket destruction — add to Metinvest/SCM thread",
    # collapse / restoration-theatre / demolish-rebuild suspicion
    "95692":  "пр. Победы 123 — foundation cracks, load-bearing walls separating; residents suspect quiet demolish-rebuild",
    "97196":  "пр. Победы 123 — Moscow expert taking soil samples; demolish-and-rebuild suspicion (follow-up)",
    "108832": "пр. Металлургов 221 — contractor took 80% advance on аварийный building, 'жить ОПАСНО'",
    "109976": "пр. Металлургов 221 — Строймонолит full report; 1 of 80 doors replaced",
    # entities / new-build
    "16377":  "ООО «Геострой-2010» (Moscow) pouring foundations for 2 new apt blocks on ул. Куприна, Sep-Oct 2022",
    # NEVSKY — military-built showcase microdistrict (МКР)
    "13817":  "МКР Невский launch: Turchak attends Ponomareva family move-in, ул. Куприна кв.87, 2022-09-26",
    "12967":  "resident Marina Kazina shows МО РФ-built flat in МКР Невский — earliest resident feature",
    "13240":  "МО РФ: 3 five-storey buildings in ЖК Невский built since 20 May 2022",
    "17762":  "Тимур Иванов (Deputy Defence Minister) + Turchak + Пушилин inspect Невский; 189 families next",
    "17868":  "Хоценко: 42 families in ЖК Невский built by военные строители; hundreds of ордеров",
    "18097":  "МО РФ builders to add school + kindergarten in МКР Невский",
    "30422":  "6 nine-storey buildings by ВСК in МКР Невский; kindergarten 150; done end-2023",
    "30922":  "Невский заселение; built by ВСК in 181 days 2022; PUTIN visited the microdistrict (March 2023)",
    "33210":  "ВСК finishing 1,100-student school in МКР Невский",
    "43475":  "6 nine-storey ЖК Невский buildings near улиц Ленина и Куприна ready for заселение",
    "64629":  "CHANNEL CORRECTION: ЖК Невский (ООО ОборонСпецСтрой, commercial) != МКР Невский (ВСК МО РФ)",
    "134492": "МКР Невский infrastructure buildout — shops, pharmacy, ПСБ bank, etc.",
    # cross-neighbor
    "135880": "ЖК Изумрудный — cement-plant dust + power-cable fire cut power/water (Nevsky neighbor)",
}

MEDIA_PULL_KINDS = {"photo"}          # always pull these (small, evidentiary)
# curated video/doc leads worth pulling despite size (verified high-value)
MEDIA_PULL_VIDEO_LEADS = {"30922", "108832", "109976", "95692", "97196",
                          "18263", "59583", "134492"}

# tag -> pull priority for media (lower = pull first). A message's priority is
# the min over its strong tags; a curated lead always gets priority 1.
#   1 curated lead      2 core seizure signal      3 broad testimony/context
PRIORITY_2_TAGS = {
    "ownerless", "manevr_fond", "removal_register", "forced_entry", "sealing",
    "military_builder", "zhk", "builder_entity", "legal_instrument", "renaming",
    "poa",
}


def _media_info(obj) -> tuple[str, int | None]:
    m = obj.get("media")
    if not m:
        return "none", None
    t = m.get("_")
    if t == "MessageMediaPhoto":
        return "photo", None
    if t == "MessageMediaDocument":
        doc = m.get("document") or {}
        mime = (doc.get("mime_type") or "")
        size = doc.get("size")
        if mime.startswith("video/"):
            return "video", size
        if mime.startswith("audio/"):
            return "audio", size
        return "document", size
    if t == "MessageMediaWebPage":
        return "webpage", None
    return t.replace("MessageMedia", "").lower() if t else "none", None


def _tags_for(text: str) -> list[str]:
    tags = []
    has_nexus = bool(PROPERTY_NEXUS.search(text))
    for tag, high, rx in SIGNALS:
        if rx.search(text):
            if high:
                tags.append(tag)
            else:
                # contextual tag becomes a flag only with a property nexus
                if has_nexus:
                    tags.append(tag)
                else:
                    tags.append(tag + "?")   # weak, annotate-only
    # legal citation, anchored
    legal_hits = sorted({f"{m.group(1).split()[0].capitalize()} №{m.group(2).strip(' .')}"
                         for m in LEGAL_RX.finditer(text)})
    if legal_hits:
        tags.append("legal_instrument")
    # named builder entity
    ent_hits = []
    for m in ENTITY_RX.finditer(text):
        # look at a 120-char window around the entity for a construction hint
        s = max(0, m.start() - 60)
        window = text[s:m.end() + 60]
        if BUILDER_HINT.search(window):
            ent_hits.append(f"{m.group(1)} «{m.group(2).strip()}»")
    if ent_hits:
        tags.append("builder_entity")
    return tags, legal_hits, ent_hits


def main() -> None:
    con = forensics.open_state()
    rows = con.execute(
        "SELECT url, raw_path FROM source_document WHERE source_type=? ORDER BY url",
        (SOURCE_TYPE,),
    ).fetchall()
    log.info("scanning %d %s messages", len(rows), SOURCE_TYPE)

    OUT_FLAGGED.parent.mkdir(parents=True, exist_ok=True)
    fh = OUT_FLAGGED.open("w", encoding="utf-8")
    mh = OUT_MANIFEST.open("w", encoding="utf-8")

    tag_counts: Counter = Counter()
    media_counts: Counter = Counter()
    pull_priority_counts: Counter = Counter()
    flagged = 0
    pull_photo = 0
    pull_video = 0
    leads_seen = set()
    n_msg = 0

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
        n_msg += 1
        msg_id = url.rstrip("/").rsplit("/", 1)[-1]
        text = (obj.get("message") or "").strip()
        date = (obj.get("date") or "")[:10]

        tags, legal_hits, ent_hits = _tags_for(text) if text else ([], [], [])
        # strong tags = those without a trailing '?'
        strong = [t for t in tags if not t.endswith("?")]
        lead_note = LEADS.get(msg_id)

        if not strong and not lead_note:
            continue

        flagged += 1
        for t in strong:
            tag_counts[t] += 1
        if lead_note:
            leads_seen.add(msg_id)

        media_kind, media_size = _media_info(obj)
        media_counts[media_kind] += 1

        rec = {
            "msg_id": msg_id, "url": url, "date": date,
            "tags": tags,
            "legal_citations": legal_hits,
            "builder_entities": ent_hits,
            "lead_note": lead_note,
            "media_kind": media_kind,
            "media_size_bytes": media_size,
            "text": text[:800],
        }
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

        # media pull manifest
        want = (media_kind in MEDIA_PULL_KINDS) or \
               (media_kind == "video" and msg_id in MEDIA_PULL_VIDEO_LEADS)
        if want:
            if lead_note:
                priority = 1
            elif any(t in PRIORITY_2_TAGS for t in strong):
                priority = 2
            else:
                priority = 3
            if media_kind == "photo":
                pull_photo += 1
            else:
                pull_video += 1
            pull_priority_counts[priority] += 1
            mh.write(json.dumps({
                "msg_id": msg_id, "url": url, "date": date,
                "media_kind": media_kind, "media_size_bytes": media_size,
                "pull_priority": priority,
                "tags": strong, "lead_note": lead_note,
            }, ensure_ascii=False) + "\n")

    fh.close()
    mh.close()

    print(f"\n{'='*72}")
    print(f"@mariupol_nash FLAGGING — {n_msg} messages scanned, {flagged} flagged")
    print(f"{'='*72}")
    print("\n── flags by signal (strong only) ──")
    for tag, c in tag_counts.most_common():
        print(f"  {tag:22s} {c}")
    print("\n── media on flagged messages ──")
    for k, c in media_counts.most_common():
        print(f"  {k:12s} {c}")
    print(f"\n── curated LEADS ──  {len(leads_seen)}/{len(LEADS)} present in store")
    missing = sorted(set(LEADS) - leads_seen)
    if missing:
        print(f"  MISSING (not found in capture): {', '.join(missing)}")
    print(f"\n── media-pull manifest ──")
    print(f"  {pull_photo} photos (small, pull all) + {pull_video} curated videos")
    print(f"  by pull_priority: "
          f"P1(curated leads)={pull_priority_counts[1]}  "
          f"P2(core seizure)={pull_priority_counts[2]}  "
          f"P3(broad testimony/ctx)={pull_priority_counts[3]}")
    print(f"\n  Flagged  → {OUT_FLAGGED}")
    print(f"  Manifest → {OUT_MANIFEST}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
