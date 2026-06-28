#!/usr/bin/env python3
"""Parse the first-instance DNR district/city-court ownerless-property
(бесхозяйная недвижимая вещь) case-cards captured by the full-population
district crawl (`scripts/178` pattern, run 2026-06-27/28 across all enabled
courts in `crawl/courts.py`). Pure local parse over `data/raw/` — no network.

WHY THIS EXISTS
---------------
`scripts/176` analyses the ВС ДНР *appellate* layer (`33-xxxx` cards). That
layer is self-selected to cases someone contested, so it cannot show the
**base rate** of seizure. This script parses the *first-instance* (`2-xxxx`,
особое производство) cards — the layer where the administration's petition is
first granted or refused — for the 26 courts that actually returned records
(the front-line/ghost courts returned zero; see
`docs/dnr_bezkhoz_appellate_outcomes_2026-06.md`).

WHAT EVERY FIRST-INSTANCE CARD CARRIES (confirmed by sampling, 2026-06-28)
-------------------------------------------------------------------------
  - case no            ДЕЛО № 2-2044/2025 ~ М-1377/2025
  - УИД                93RS0037-01-2025-002559-17  (encodes court of origin)
  - Дата поступления   filing date
  - Категория дела     the bezkhoz category string (the case-type filter)
  - Судья              single named judge  (official -> kept)
  - Дата рассмотрения  decision date
  - Результат          standardized result code (the seizure outcome)
  - СТОРОНЫ:           ЗАЯВИТЕЛЬ = administration/fund (+ INN/OGRN, official -> kept)
                       ЗАИНТЕРЕСОВАННОЕ ЛИЦО = the owner (natural person) +
                       Rosreestr.
  - Судебный акт       full РЕШЕНИЕ text is embedded on most cards (unlike the
                       appellate layer's 49% text-unpublished) -> property
                       ADDRESS is recoverable from the ruling body, the escape
                       hatch for the long-standing court-islands address gap.

PRIVACY (CLAUDE.md hard rule)
-----------------------------
The ЗАИНТЕРЕСОВАННОЕ ЛИЦО is a lawful owner, a living private individual. This
parser NEVER writes an owner's name to its output. It records only
`owner_natural_persons` (a count) and `has_named_owner` (bool). Petitioner
organisations and judges act in official capacity and ARE kept. The address
extractor captures only the property-address substring, and the regexes are
anchored on address cue words ("по адресу"), not on personal names.

Run:
    .venv312/bin/python scripts/182_parse_dnr_district_bezkhoz.py
"""
from __future__ import annotations

import csv
import json
import logging
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from bs4 import BeautifulSoup  # noqa: E402

log = logging.getLogger(__name__)

RAW = ROOT / "data" / "raw"
OUT_JSON = ROOT / "data" / "parsed" / "dnr_district_bezkhoz.json"
OUT_CSV = ROOT / "data" / "parsed" / "dnr_district_bezkhoz.csv"

# appellate / cassation domains are handled by scripts/176 + the 2kas reader
SKIP_DOMAINS = ("vs--dnr.sudrf.ru", "2kas.sudrf.ru")

# domain code -> municipality (for the cards whose ruling text doesn't name a city)
DOMAIN_CITY = {
    "mar-zhovt": "Mariupol", "mar-prim": "Mariupol",
    "mar-ordzh": "Mariupol", "mar-ilich": "Mariupol",
    "mng": "Mangush", "harc": "Khartsyzk", "enak": "Enakievo",
    "vr": "Donetsk", "kir": "Donetsk", "bud": "Donetsk",
    "cg-gorl": "Horlivka", "gorn": "Makiivka",
    "centralno-gorodskoy": "Makiivka", "vln": "Volnovakha",
    "amv": "Amvrosievka", "tlm": "Telmanove", "yasin": "Yasynuvata",
    "star": "Starobesheve", "nva": "Novoazovsk", "vld": "Volodarske",
    "dok": "Dokuchaievsk", "deb": "Debaltseve", "marin": "Marinka",
    "krasn": "Pokrovsk(Krasnoarmeysk)",
}

CASE_RX = re.compile(r"ДЕЛО\s*№\s*(2-\d+/\d{4})")
UID_RX = re.compile(r"(\d{2}RS\d{4}-\d{2}-\d{4}-\d{6}-\d{2})")
FILED_RX = re.compile(r"Дата поступления\n(\d{2}\.\d{2}\.\d{4})")
DECIDED_RX = re.compile(r"Дата рассмотрения\n(\d{2}\.\d{2}\.\d{4})")
JUDGE_RX = re.compile(r"Судья\n([^\n]+)")
RESULT_RX = re.compile(r"Результат рассмотрения\n([^\n]+)")
CAT_RX = re.compile(r"Категория дела\n[\s\S]{0,120}?бесхозяйн", re.I)

# party block: between the data-bearing "СТОРОНЫ ПО ДЕЛУ" header (2nd occurrence)
# and the embedded ruling / end of card.
ROLE_TOKENS = ("ЗАЯВИТЕЛЬ", "ИСТЕЦ", "ОТВЕТЧИК", "ЗАИНТЕРЕСОВАННОЕ ЛИЦО",
               "ТРЕТЬЕ ЛИЦО", "ЛИЦО, В ОТНОШЕНИИ")
INN_RX = re.compile(r"^\d{10}$|^\d{12}$")
# administration / fund / ministry / state-body petitioner names (kept)
ORG_HINT = re.compile(
    r"дминистрац|Фонд|инистерств|Управлени|Росреестр|кадастр|ФГУП|ГУП|"
    r"унитарн|комитет|Совет|РОСРЕЕСТР|Росимуществ|предприят|ТУ |учрежден|"
    r"«|\"|ООО|ОАО|АО |ПАО|товарищест|кооператив|department|инспекци", re.I)

# owner-side outcome of the FIRST-INSTANCE result code
RESULT_MAP = [
    (re.compile(r"УДОВЛЕТВОРЕН ЧАСТИЧНО", re.I), "LOSE_granted_partial"),
    (re.compile(r"УДОВЛЕТВОРЕН", re.I), "LOSE_seizure_granted"),
    (re.compile(r"ОТКАЗАНО в принятии", re.I), "NEUTRAL_petition_not_accepted"),
    (re.compile(r"ОТКАЗАНО", re.I), "WIN_refused_on_merits"),
    (re.compile(r"ОСТАВЛЕН\w* БЕЗ РАССМОТР", re.I), "WIN_left_without_consideration"),
    (re.compile(r"ВОЗВРАЩЕНО", re.I), "NEUTRAL_returned_to_petitioner"),
    (re.compile(r"ПРЕКРАЩЕНО", re.I), "WITHDRAWN_terminated"),
    (re.compile(r"присоединено", re.I), "NEUTRAL_joined_to_other_case"),
    (re.compile(r"Передано по подсудности", re.I), "NEUTRAL_transferred_venue"),
]
ROLLUP = {
    "LOSE_seizure_granted": "LOSE (seizure granted)",
    "LOSE_granted_partial": "LOSE (seizure granted)",
    "WIN_refused_on_merits": "WIN (refused/bounced)",
    "WIN_left_without_consideration": "WIN (refused/bounced)",
    "NEUTRAL_returned_to_petitioner": "NEUTRAL (procedural, refileable)",
    "NEUTRAL_petition_not_accepted": "NEUTRAL (procedural, refileable)",
    "NEUTRAL_joined_to_other_case": "NEUTRAL (procedural, refileable)",
    "NEUTRAL_transferred_venue": "NEUTRAL (procedural, refileable)",
    "WITHDRAWN_terminated": "WITHDRAWN/terminated",
}

# Property identity from the embedded ruling text. NOTE: the GAS «Правосудие»
# anonymizer redacts the street address to `<адрес>` on 100% of published
# rulings (and owner names to ФИО1/ФИО2), so address recovery is mostly closed
# AT SOURCE. What leaks through the redaction inconsistently: a partial street
# (~15% of published cards) and a cadastral number (~2%). The cadastral number
# is the more valuable target — a unique property identifier that links to the
# spine/Rosreestr without the street. Both are extracted where present; the
# rest are flagged `address_redacted`, which is the honest state.
ADDR_REAL_RX = re.compile(
    r"по адресу:?\s*([^<\n]{0,15}(?:ул|пр|бул|пер|кв-?л|просп|г\.|город|мкр|"
    r"бульвар|переул)[^<\n;]{5,80})", re.I)
CADASTRAL_RX = re.compile(r"\b(9[03]:\d{2}:\d{6,7}:\d{1,5})\b")
MARIUPOL_TEXT_RX = re.compile(r"Мариупол", re.I)
PARTY_HEADER = "Вид лица, участвующего в деле"


def result_to_outcome(code: str) -> str:
    for rx, label in RESULT_MAP:
        if rx.search(code):
            return label
    return "UNCLASSIFIED:" + code[:40]


def parse_parties(block: str) -> dict:
    """Return petitioner org(s) + counts only. NEVER returns owner names."""
    # split the block into lines, walk role -> name(+optional INN/OGRN)
    lines = [l.strip() for l in block.split("\n") if l.strip()]
    petitioners, owner_count, rosreestr = [], 0, False
    i = 0
    while i < len(lines):
        ln = lines[i]
        role = next((r for r in ROLE_TOKENS if ln == r or ln.startswith(r)), None)
        if role:
            name = lines[i + 1] if i + 1 < len(lines) else ""
            is_org = bool(ORG_HINT.search(name))
            if "Росреестр" in name or "кадастр" in name.lower() or "РОСРЕЕСТР" in name:
                rosreestr = True
            elif role in ("ЗАЯВИТЕЛЬ", "ИСТЕЦ") and is_org:
                petitioners.append(name)
            elif role.startswith("ЗАИНТЕРЕСОВАН") and not is_org:
                owner_count += 1  # natural-person owner — counted, never named
            i += 2
        else:
            i += 1
    return {"petitioners": petitioners, "owner_natural_persons": owner_count,
            "rosreestr_party": rosreestr}


def classify_petitioner(names: list[str]) -> str:
    blob = " ".join(names)
    if "Фонд" in blob:
        return "state_property_fund"
    if "дминистрац" in blob:
        return "municipal_administration"
    if "инистерств" in blob:
        return "ministry"
    if not names:
        return "none_listed"
    return "other_state_body"


def main() -> None:
    metas = list(RAW.glob("*.meta.json"))
    log.info("scanning %d meta sidecars", len(metas))
    records, n_seen, n_card = [], 0, 0
    for mp in metas:
        try:
            url = json.loads(mp.read_text()).get("url", "")
        except Exception:
            continue
        if "name_op=case" not in url or "sudrf.ru" not in url:
            continue
        if any(d in url for d in SKIP_DOMAINS):
            continue
        dm = re.search(r"https?://([^/.]+)", url)
        code = dm.group(1) if dm else "?"
        n_card += 1
        raw = Path(str(mp)[:-len(".meta.json")])
        if not raw.exists():
            continue
        try:
            text = BeautifulSoup(raw.read_bytes().decode("cp1251", "replace"),
                                 "lxml").get_text("\n", strip=True)
        except Exception as e:
            log.warning("parse fail %s: %s", raw.name, e)
            continue
        if not CAT_RX.search(text) and "бесхозяйн" not in text.lower():
            continue  # not a bezkhoz case
        cm = CASE_RX.search(text)
        if not cm:
            continue
        n_seen += 1

        result = (RESULT_RX.search(text).group(1).strip()
                  if RESULT_RX.search(text) else "<none>")
        outcome = result_to_outcome(result)
        text_published = "Судебный акт" in text and "ИМЕНЕМ РОССИЙСКОЙ" in text

        # party block: anchor on the DATA-table header (`Вид лица…`), not the
        # tab label — the tab-area match was leaving ~64% of cards party-less.
        st = text.rfind(PARTY_HEADER)
        end = text.find("Судебный акт", st) if st >= 0 else -1
        party_block = text[st:end if end > 0 else st + 1500] if st >= 0 else ""
        parties = parse_parties(party_block)

        # property identity from the embedded ruling text (street mostly
        # redacted to <адрес>; cadastral number survives more reliably)
        addr, cadastral, redacted = None, None, False
        if text_published:
            body = re.sub(r"\s+", " ", text[text.find("ИМЕНЕМ РОССИЙСКОЙ"):])
            redacted = "<адрес>" in body
            am = ADDR_REAL_RX.search(body)
            if am:
                addr = am.group(1).strip(" ,")
            cdm = CADASTRAL_RX.search(body)
            if cdm:
                cadastral = cdm.group(1)

        is_mariupol = bool(MARIUPOL_TEXT_RX.search(text)) or \
            DOMAIN_CITY.get(code) == "Mariupol"
        jm = JUDGE_RX.search(text)
        fm, dm2 = FILED_RX.search(text), DECIDED_RX.search(text)
        records.append({
            "court_code": code,
            "municipality": DOMAIN_CITY.get(code, code),
            "case": cm.group(1),
            "filed": fm.group(1) if fm else None,
            "decided": dm2.group(1) if dm2 else None,
            "judge": jm.group(1).strip() if jm else None,   # official, kept
            "result_code": result,
            "outcome": outcome,
            "rollup": ROLLUP.get(outcome, "UNKNOWN/UNCLASSIFIED"),
            "petitioner_type": classify_petitioner(parties["petitioners"]),
            "petitioner_name": "; ".join(parties["petitioners"]) or None,
            "owner_natural_persons": parties["owner_natural_persons"],
            "has_named_owner": parties["owner_natural_persons"] > 0,
            "rosreestr_party": parties["rosreestr_party"],
            "text_published": text_published,
            "property_address": addr,          # owner name NOT included
            "cadastral_number": cadastral,     # unique spine/Rosreestr link
            "address_redacted": redacted,
            "is_mariupol": is_mariupol,
            "raw_sha": raw.stem,
        })
        if n_seen % 1000 == 0:
            log.info("  parsed %d bezkhoz cards", n_seen)

    # de-dup by (court, case) keeping the text-published copy if any
    best: dict[tuple, dict] = {}
    for r in records:
        k = (r["court_code"], r["case"])
        if k not in best or (r["text_published"] and not best[k]["text_published"]):
            best[k] = r
    deduped = list(best.values())

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(deduped, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(deduped[0].keys()))
        w.writeheader()
        w.writerows(deduped)

    log.info("case-cards scanned: %d | bezkhoz parsed: %d | unique cases: %d",
             n_card, n_seen, len(deduped))
    log.info("  -> %s", OUT_JSON)
    log.info("  -> %s", OUT_CSV)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
