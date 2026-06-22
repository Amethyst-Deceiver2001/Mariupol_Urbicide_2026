"""Stage 2: parse. Extract lifecycle fields from raw store (re-runnable).

Reads captured case-card HTML from data/raw/, extracts the fields that map
onto the schema (court_case + seizure_event + owner/address), and emits JSON.

Owner names are extracted to support the claimant's own dossier, then must be
minimized before any shared output (see CLAUDE.md PRIVACY). Every owner field
is tagged owner_sensitive=True in the output.

The portal renders hidden tabs per case card:
  cont1 — case metadata (судья, категория, дата поступления, УИД)
  cont2 — движение дела / lifecycle events
  cont3 — стороны / parties (заявитель, представитель, заинтересованные лица)
  cont4 — ЖАЛОБА №N* blocks (apellate/cassation complaints), present only on
          appealed cases — see _extract_complaints().
cont1-cont3 use <table id="tablcont">; cont4's ЖАЛОБА blocks are bare
top-level <table> elements (no id).
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from bs4 import BeautifulSoup

from .. import config
from ..normalize.toponym import normalize_address

# ── Case number ──────────────────────────────────────────────────────────────
CASE_NO_RE = re.compile(r"\b\d{1,2}-\d+/\d{4}\b")

# ── Dates ────────────────────────────────────────────────────────────────────
DATE_RE = re.compile(r"\b(\d{2}\.\d{2}\.\d{4})\b")

# ── Address ──────────────────────────────────────────────────────────────────
ADDR_RE = re.compile(
    # \b-anchor the bare full-word alternatives (улица, дорога, тупик, ...) so
    # they only match whole words -- without it "дорога" matches the first 6
    # letters of the surname "Дорогань", leaking a живой owner's name (PII)
    # into property.occupation_address. Confirmed 2026-06-10: ЗАИНТЕРЕСОВАННОЕ
    # ЛИЦО Дорогань Мария Александровна -> false-positive "address".
    # Abbreviated forms ending in '.'/'-X' don't need this (already bounded).
    r"(?:ул\.|улица\b|пр-т|просп?\.|проспект\b|пер\.|переулок\b|б-р|бульвар\b"
    r"|пл\.|площадь\b|ш\.|шоссе\b|наб\.|набережная\b|туп\.|тупик\b|пр-д|проезд\b"
    r"|д-т|дорога\b|мкр\.?|микрорайон\b)\s*[^,\n]{1,60}"
    r"(?:,\s*(?:д(?:ом)?\.?\s*\d+[А-Яа-яA-Za-z]?(?:\s*/\s*\d+)?))?"
    r"(?:,\s*(?:кв(?:артира)?|оф(?:ис)?|ком(?:ната)?)\.?\s*\d+)?",
    re.I | re.U,
)

# ── Cadastral number (ЕГРН format) ───────────────────────────────────────────
CADASTRAL_RE = re.compile(r"\b\d{2}:\d{2}:\d{6,7}:\d+\b")

# ── Property area ────────────────────────────────────────────────────────────
AREA_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*кв\.?\s*м(?:[^²]|$)", re.I | re.U
)

# ── Property type ────────────────────────────────────────────────────────────
PROP_TYPE_RE = re.compile(
    r"\b(квартир[ауе]?|жил(?:ой)?\s+дом[ае]?|нежил\w+\s+помещени\w+"
    r"|помещени[ея]|домовладени\w+|гараж\w*|земельн\w+\s+участ\w+)\b",
    re.I | re.U,
)

# ── Judge (fallback: flat-text) ──────────────────────────────────────────────
JUDGE_RE = re.compile(
    r"[Сс]удь[яи][:\s]+([А-ЯЁ][а-яё]{1,30}(?:\s+[А-ЯЁ]\.?){1,2})",
    re.U,
)

# ── Parties (fallback: flat-text) ────────────────────────────────────────────
INTERESTED_PARTY_RE = re.compile(
    r"[Зз]аинтересованн\w+\s+лиц\w+[:\s—–-]+"
    r"([А-ЯЁ][а-яё]{1,30}\s+[А-ЯЁ][а-яё]{1,20}"
    r"(?:\s+[А-ЯЁ][а-яё]{1,20})?)",
    re.U,
)
PETITIONER_RE = re.compile(
    r"[Зз]аявител[ья][:\s—–]+([^\n,;]{5,120})",
    re.U,
)
OWNER_NEAR_RE = re.compile(
    r"(?:собственник[аи]?|правообладател\w+|владел[её]ц)[:\s—–]+"
    r"([А-ЯЁ][а-яё]{1,30}\s+[А-ЯЁ][а-яё]{1,20}"
    r"(?:\s+[А-ЯЁ][а-яё]{1,20})?)",
    re.I | re.U,
)

# ── Legal grounds ────────────────────────────────────────────────────────────
_GROUNDS: list[tuple[re.Pattern, str]] = [
    (
        re.compile(r"не\s+зарегистрир|отсутств\w+\s+регистрац", re.I),
        "no_egrn_registration",
    ),
    (
        re.compile(r"не\s+обратил\w*\s+.{0,20}срок|не\s+явил\w*", re.I),
        "owner_failed_to_appear",
    ),
    (
        re.compile(
            r"признак[иа]\s+бесхозяйн\w+|бесхозяйн\w+\s+недвиж", re.I
        ),
        "ownerless_indicators",
    ),
    (
        re.compile(
            r"66.?[РP][ЗЗ]|Закон\w*\s+(?:ДНР|Республик\w+).{0,30}66",
            re.I,
        ),
        "law_66_rz",
    ),
]

# ── Decision outcome — matched against "Результат рассмотрения" from cont1 ──
# Order matters: most specific first.
_OUTCOME_MAP: list[tuple[re.Pattern, str]] = [
    (re.compile(r"УДОВЛЕТВОРЕН", re.I),                        "granted"),
    (re.compile(r"ОТКАЗАНО\s+в\s+удовлетворени", re.I),        "denied"),
    (re.compile(r"ОТКАЗАНО\s+в\s+принятии", re.I),             "rejected"),
    (re.compile(r"ОСТАВЛЕН\s+БЕЗ\s+РАССМОТРЕНИЯ", re.I),      "left_without_consideration"),
    (re.compile(r"ПРЕКРАЩЕНО", re.I),                          "discontinued"),
    (re.compile(r"ВОЗВРАЩЕНО", re.I),                          "returned"),
    (re.compile(r"[Пп]ередано\s+по\s+подсудности", re.I),      "transferred_jurisdiction"),
]

# Fallback patterns for flat-text when cont1 result field is absent.
_OUTCOMES_FALLBACK: list[tuple[re.Pattern, str]] = [
    (re.compile(r"удовлетвор", re.I),                          "granted"),
    (re.compile(r"отказ\w+\s+в\s+удовлетворени", re.I),        "denied"),
    (re.compile(r"прекратить\s+производство", re.I),           "discontinued"),
]

# ── cont2 ДВИЖЕНИЕ ДЕЛА: the only two movement events that are seizure
# milestones (exact match on the lowercased event name). Everything else in the
# timeline (Передача материалов судье, Дело сдано в отдел делопроизводства,
# Вынесено определение о подготовке…, etc.) is court-internal housekeeping —
# preserved in the movement timeline (forensics) but NOT emitted as a seizure
# act. The canonical court_petition / court_transfer dates come from cont1
# (Дата поступления / Дата рассмотрения, authoritative); these movement events
# are used only as a fallback when cont1 is silent.
#
# Rejected substring traps from the old _STAGE_MAP (do NOT reintroduce):
#   "решение"  swept in "Решение вопроса о ПРИНЯТИИ иска… к рассмотрению"
#              (petition admission, day after filing — NOT a merits ruling) and
#              "Изготовлено мотивированное РЕШЕНИЕ" (written text finalised,
#              weeks after the decision) -> mislabeled 54% of court_transfer.
#   "удовлетвор"/"законную силу"/"вступил"/"направлен" matched NO cont2 event
#              name at all (those words live in cont1 result / appeal blocks).
_PETITION_EVENTS = frozenset({
    "регистрация иска (заявления, жалобы) в суде",
    "регистрация иска (заявления, жалобы) в суде и принятие его к производству",
})
_HEARING_EVENTS = frozenset({
    "судебное заседание",
    "предварительное судебное заседание",
})
_MOTIVATED_DECISION_EVENT = "изготовлено мотивированное решение в окончательной форме"

# Individual Cyrillic name pattern used in cont3 owner detection.
_NAME_RE = re.compile(
    r"^[А-ЯЁ][а-яё]{1,30}\s+[А-ЯЁ][а-яё]{1,20}"
    r"(?:\s+[А-ЯЁ][а-яё]{1,20})?$",
    re.U,
)

# ── Appeal/cassation complaints (cont4 "ЖАЛОБА № N*" blocks) ────────────────
COMPLAINT_NO_RE = re.compile(r"№\s*(\d+)")

# Most-specific first: "апелляц"/"кассац" never co-occur, order is cosmetic.
_COMPLAINT_TYPE_MAP: list[tuple[re.Pattern, str]] = [
    (re.compile(r"апелляц", re.I), "appellate"),
    (re.compile(r"кассац", re.I), "cassation"),
    (re.compile(r"надзорн", re.I), "supervisory"),
    (re.compile(r"частн", re.I), "interlocutory"),
]

# "БЕЗ ИЗМЕНЕНИЯ" must be checked before bare "измен" -- "оставить решение
# БЕЗ ИЗМЕНЕНИЯ" (denied/upheld) would otherwise false-match "modified".
_COMPLAINT_OUTCOME_MAP: list[tuple[re.Pattern, str]] = [
    (re.compile(r"без\s+изменени\w*", re.I), "upheld"),
    (re.compile(r"отмен\w*", re.I), "reversed"),
    (re.compile(r"измен\w*", re.I), "modified"),
    (re.compile(r"без\s+рассмотрени\w*", re.I), "left_without_consideration"),
    (re.compile(r"прекращ\w*", re.I), "discontinued"),
    (re.compile(r"возвращ\w*", re.I), "returned"),
]


def _text(node) -> str:
    return node.get_text(" ", strip=True) if node else ""


def _first_match(
    patterns: list[tuple[re.Pattern, str]], text: str
) -> list[str]:
    return [label for pat, label in patterns if pat.search(text)]


def _extract_cont1(soup) -> dict:
    """Case metadata from ДЕЛО tab (div#cont1).

    Case number lives in div.casenumber above the tabs.
    Key/value rows: <td><b>label</b></td><td>value</td>.
    """
    rec: dict = {}
    cn_div = soup.find("div", class_="casenumber")
    if cn_div:
        m = CASE_NO_RE.search(cn_div.get_text())
        if m:
            rec["case_number"] = m.group(0)

    cont1 = soup.find("div", id="cont1")
    if not cont1:
        return rec
    for row in cont1.select("table#tablcont tr"):
        tds = row.find_all("td")
        if len(tds) < 2:
            continue
        label = tds[0].get_text(" ", strip=True).lower()
        value = tds[1].get_text(" ", strip=True)
        if not value:
            continue
        if "судья" in label:
            rec["judge"] = value
        elif "категория" in label:
            rec["case_category"] = value
        elif "дата поступления" in label:
            m = DATE_RE.search(value)
            if m:
                rec["filed_date"] = m.group(0)
        elif "дата рассмотрения" in label:
            m = DATE_RE.search(value)
            if m:
                rec["decided_date"] = m.group(0)
        elif "результат рассмотрения" in label:
            for pat, outcome in _OUTCOME_MAP:
                if pat.search(value):
                    rec["outcome"] = outcome
                    rec["outcome_raw"] = value
                    break
        elif "уникальный идентификатор" in label:
            rec["judicial_uid"] = value
    return rec


def _extract_movement(soup) -> dict:
    """Structured ДВИЖЕНИЕ ДЕЛА timeline from div#cont2.

    Columns: Наименование события | Дата | Время | Место | Результат | ...

    Returns {"movement": [{"event","date","result"?}, ...]} (the full timeline,
    preserved for forensic completeness) plus private date hints
    (_petition_date / _hearing_date / _motivated_date) used ONLY as a fallback
    when cont1 lacks the authoritative Дата поступления / Дата рассмотрения.

    The canonical court_petition / court_transfer milestones are synthesised
    later, in _synthesise_court_stages(), from cont1 — never overwritten by this
    timeline. cont2 is restricted to its own #tablcont (no flat-text fallback:
    a card missing cont2 also lacks any other reliable movement source).
    """
    cont2 = soup.find("div", id="cont2")
    if not cont2:
        return {}

    movement: list[dict] = []
    petition_date = hearing_date = motivated_date = None
    for row in cont2.select("table#tablcont tr"):
        tds = row.find_all("td")
        if len(tds) < 2:
            continue
        event = tds[0].get_text(" ", strip=True)
        if not event or event.lower().startswith("наименование"):
            continue
        d = DATE_RE.search(tds[1].get_text(" ", strip=True))
        if not d:
            continue
        date = d.group(0)
        entry = {"event": event, "date": date}
        if len(tds) >= 5:
            result = tds[4].get_text(" ", strip=True)
            if result:
                entry["result"] = result
        movement.append(entry)

        ev_lc = event.lower()
        if ev_lc in _PETITION_EVENTS and petition_date is None:
            petition_date = date            # first registration = the filing
        elif ev_lc in _HEARING_EVENTS:
            hearing_date = date             # keep the LAST hearing (deciding)
        elif ev_lc == _MOTIVATED_DECISION_EVENT:
            motivated_date = date

    out: dict = {}
    if movement:
        out["movement"] = movement
    if petition_date:
        out["_petition_date"] = petition_date
    if hearing_date:
        out["_hearing_date"] = hearing_date
    if motivated_date:
        out["_motivated_date"] = motivated_date
    return out


def _synthesise_court_stages(rec: dict, mv: dict) -> None:
    """Build the canonical court seizure milestones from cont1 (authoritative)
    dates + outcome, with the cont2 movement timeline as fallback only.

    Two milestones at most:
      court_petition — the occupation authority's filing (any disposition).
      court_transfer — title actually transferred to the municipality, i.e.
                       ONLY when the petition was GRANTED (Иск УДОВЛЕТВОРЕН).
                       A returned / withdrawn / «спор о праве» disposition
                       transfers nothing and gets no court_transfer.

    entered_force is intentionally NOT synthesised here: this portal's case
    cards carry no «вступило в законную силу» movement event; that rung is
    sourced from the «снятие с учёта» removal decrees instead.
    """
    # cont1 wins; fill only when cont1 was silent.
    if not rec.get("filed_date") and mv.get("_petition_date"):
        rec["filed_date"] = mv["_petition_date"]
    if not rec.get("decided_date"):
        fallback = mv.get("_hearing_date") or mv.get("_motivated_date")
        if fallback:
            rec["decided_date"] = fallback

    movement = mv.get("movement", [])
    stages: list[dict] = []

    if rec.get("filed_date"):
        stages.append({
            "stage": "court_petition",
            "date": rec["filed_date"],
            "event": "Регистрация иска (заявления, жалобы) в суде",
            "detail": {"movement": movement} if movement else {},
        })

    if rec.get("outcome") == "granted" and rec.get("decided_date"):
        detail: dict = {}
        if rec.get("outcome_raw"):
            detail["outcome_raw"] = rec["outcome_raw"]
        if mv.get("_motivated_date"):
            detail["motivated_decision_date"] = mv["_motivated_date"]
        stages.append({
            "stage": "court_transfer",
            "date": rec["decided_date"],
            "event": "Судебное заседание — решение (иск удовлетворён)",
            "detail": detail,
        })

    if stages:
        rec["stages"] = stages


def _extract_cont3(soup) -> dict:
    """Parties from СТОРОНЫ tab (div#cont3).

    Columns: Вид лица | Фамилия/наименование | ИНН | КПП | ОГРН | ОГРНИП

    ЗАЯВИТЕЛЬ  — occupation municipal authority (petitioner).
    ЗАИНТЕРЕСОВАННОЕ ЛИЦО — includes Rosreestr (org, has INN/OGRN) and the
    displaced property owner (individual Cyrillic name, no INN).
    """
    rec: dict = {}
    cont3 = soup.find("div", id="cont3")
    if not cont3:
        return rec

    owner_candidates: list[str] = []
    for row in cont3.select("table#tablcont tr"):
        tds = row.find_all("td")
        if len(tds) < 2:
            continue
        role = tds[0].get_text(" ", strip=True).upper()
        name = tds[1].get_text(" ", strip=True)
        if not name:
            continue
        if "ЗАЯВИТЕЛЬ" in role and "petitioner" not in rec:
            rec["petitioner"] = name
        elif "ЗАИНТЕРЕСОВАННОЕ" in role:
            inn = tds[2].get_text(strip=True) if len(tds) > 2 else ""
            if _NAME_RE.match(name) and not inn:
                owner_candidates.append(name)
    if owner_candidates:
        # SENSITIVE — minimize before any shared output
        rec["owner_raw"] = owner_candidates[0]
        rec["owner_sensitive"] = True
        if len(owner_candidates) > 1:
            rec["owner_raw_additional"] = owner_candidates[1:]
    return rec


def _extract_complaints(soup) -> list[dict]:
    """Apellate/cassation complaints from div#cont4 ("ЖАЛОБА № N*" blocks).

    Each complaint is a top-level <table> (no #tablcont id, unlike cont1-3):
      ['ЖАЛОБА № N*']
      ['Вид жалобы (представления)', '<Апелляционная|Кассационная> жалоба ...']
      ['Заявитель', '<role>']
      ['Вышестоящий суд', '<court>']
      ['---=== ДВИЖЕНИЕ ЖАЛОБЫ ===---']
      <nested movement table: Событие | Дата | Результат | ...>
      ['Назначено в вышестоящий суд на дату', '<date>']
      ['Дата рассмотрения жалобы', '<date>']          (absent if still pending)
      ['Результат обжалования', '<outcome text>']      (absent if still pending)

    These map onto seizure_event(stage='appeal') -- see db/load.py.
    """
    cont4 = soup.find("div", id="cont4")
    if not cont4:
        return []

    complaints: list[dict] = []
    for table in cont4.find_all("table", recursive=False):
        rows = table.find_all("tr", recursive=False)
        if not rows:
            continue
        c: dict = {}

        m = COMPLAINT_NO_RE.search(_text(rows[0]))
        if m:
            c["complaint_no"] = m.group(1)

        movement: list[dict] = []
        for row in rows[1:]:
            nested = row.find("table")
            if nested:
                for nrow in nested.find_all("tr"):
                    cells = [td.get_text(" ", strip=True)
                             for td in nrow.find_all(["td", "th"])]
                    if len(cells) < 2 or cells[0].lower().startswith("событие"):
                        continue
                    d = DATE_RE.search(cells[1])
                    if d:
                        movement.append({"event": cells[0], "date": d.group(0)})
                continue

            tds = row.find_all("td", recursive=False)
            if len(tds) < 2:
                continue
            label = tds[0].get_text(" ", strip=True).lower()
            value = tds[1].get_text(" ", strip=True)
            if not value:
                continue

            if "вид жалобы" in label:
                c["complaint_type_raw"] = value
                for pat, instance in _COMPLAINT_TYPE_MAP:
                    if pat.search(value):
                        c["instance"] = instance
                        break
                else:
                    c["instance"] = "other"
            elif "заявитель" in label:
                c["complainant_role"] = value
            elif "назначено" in label:
                # Check before "вышестоящий суд" -- this label is "Назначено
                # в вышестоящий суд на дату" and would otherwise match that
                # branch first, overwriting higher_court with a date.
                d = DATE_RE.search(value)
                if d:
                    c["scheduled_date"] = d.group(0)
            elif "вышестоящий суд" in label:
                c["higher_court"] = value
            elif "дата рассмотрения жалобы" in label:
                d = DATE_RE.search(value)
                if d:
                    c["decision_date"] = d.group(0)
            elif "результат обжалования" in label:
                c["outcome_raw"] = value
                for pat, outcome in _COMPLAINT_OUTCOME_MAP:
                    if pat.search(value):
                        c["outcome"] = outcome
                        break

        if movement:
            c["movement"] = movement
        if c:
            complaints.append(c)
    return complaints


def parse_case_card(html: str) -> dict:
    """Extract all structured fields from a single ГАС Правосудие case card.

    Fields absent in the source are omitted (not set to None) so callers can
    distinguish "not found" from "found and empty."

    owner_raw / owner_raw_additional are tagged owner_sensitive=True and MUST
    be minimized before any shared output.
    """
    soup = BeautifulSoup(html, "lxml")
    flat = soup.get_text(" ", strip=True)

    rec: dict = {}

    # ── Structured tab extraction ────────────────────────────────────────────
    rec.update(_extract_cont1(soup))
    mv = _extract_movement(soup)         # synthesised into stages at the end
    rec.update(_extract_cont3(soup))

    complaints = _extract_complaints(soup)
    if complaints:
        rec["complaints"] = complaints

    # ── Fallbacks: flat-text regex when tabs are absent ──────────────────────
    if "case_number" not in rec:
        m = CASE_NO_RE.search(flat)
        if m:
            rec["case_number"] = m.group(0)

    if "judge" not in rec:
        m = JUDGE_RE.search(flat)
        if m:
            rec["judge"] = m.group(1).strip()

    if "petitioner" not in rec:
        m = PETITIONER_RE.search(flat)
        if m:
            rec["petitioner"] = m.group(1).strip()

    if "owner_raw" not in rec:
        owner_raw = None
        m = INTERESTED_PARTY_RE.search(flat)
        if m:
            owner_raw = m.group(1).strip()
        else:
            m = OWNER_NEAR_RE.search(flat)
            if m:
                owner_raw = m.group(1).strip()
        if owner_raw:
            rec["owner_raw"] = owner_raw
            rec["owner_sensitive"] = True

    # ── Property fields — search cont2/cont3 only, not the page header ──────
    # The court's own address (e.g. "улица Казанцева, дом 7Б") appears in the
    # page header / cont1, in a "Адрес суда: ..." line that flat also
    # contains -- so do NOT fall back to flat when cont2/cont3 are absent
    # (confirmed 2026-06-10: every case currently missing both tabs matches
    # ADDR_RE only on this courthouse-address line, never a real property
    # address). No cont2/cont3 means no address, like any other absent field.
    cont2 = soup.find("div", id="cont2")
    cont3 = soup.find("div", id="cont3")
    addr_scope = " ".join(_text(n) for n in (cont2, cont3) if n)
    addresses = sorted(
        {m.group(0).strip(" ,") for m in ADDR_RE.finditer(addr_scope)}
    )
    if addresses:
        rec["addresses"] = addresses
        enriched = [normalize_address(a) for a in addresses]
        rec["addresses_enriched"] = enriched
        matched = [e for e in enriched if e["prewar_name"]]
        if matched:
            # Prefer the first toponym match for the canonical prewar field.
            rec["prewar_address_hint"] = matched[0]["prewar_name"]
            rec["toponym_source"] = matched[0]["toponym_source"]

    m = CADASTRAL_RE.search(flat)
    if m:
        rec["cadastral_no"] = m.group(0)

    m = AREA_RE.search(flat)
    if m:
        rec["area_sqm"] = m.group(1).replace(",", ".")

    m = PROP_TYPE_RE.search(flat)
    if m:
        rec["property_type"] = m.group(1).lower()

    # ── Legal grounds (all matching) ─────────────────────────────────────────
    grounds = _first_match(_GROUNDS, flat)
    if grounds:
        rec["legal_grounds"] = grounds

    # ── Decision outcome — fallback to flat text if cont1 didn't yield one ──
    if "outcome" not in rec:
        outcomes = _first_match(_OUTCOMES_FALLBACK, flat)
        if outcomes:
            rec["outcome"] = outcomes[0]

    # ── Canonical court milestones — synthesised AFTER outcome is final, so
    #    court_transfer is emitted iff the petition was actually granted. ─────
    _synthesise_court_stages(rec, mv)

    # ── RD4U category hint ───────────────────────────────────────────────────
    if rec.get("outcome") == "granted" or rec.get("stages"):
        rec["rd4u_category_hint"] = "A3.6"

    # ── Confidence ───────────────────────────────────────────────────────────
    filled = sum(
        1 for k in ("case_number", "judge", "addresses", "stages",
                    "outcome", "cadastral_no")
        if k in rec
    )
    rec["parse_confidence"] = round(min(filled / 6, 1.0), 2)
    rec["raw_len"] = len(flat)
    return rec


def run(out_path: str = "data/parsed_cases.jsonl") -> None:
    con = sqlite3.connect(config.STATE_DB)
    rows = con.execute(
        "SELECT c.case_uid, c.court, f.raw_path "
        "FROM cases c "
        "JOIN fetch_log f ON f.url = c.card_url "
        "WHERE c.relevant = 1"
    ).fetchall()
    out = Path(config.PROJECT_ROOT / out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    n = skipped = 0
    with out.open("w", encoding="utf-8") as fh:
        for case_uid, court, raw_path in rows:
            p = Path(raw_path)
            if not p.exists():
                skipped += 1
                continue
            raw = p.read_bytes()
            # Portals declare charset in the meta tag; default to windows-1251
            # (the encoding used by all ГАС Правосудие portals seen so far).
            enc = (
                "windows-1251" if b"windows-1251" in raw[:512].lower()
                else "utf-8"
            )
            rec = parse_case_card(raw.decode(enc, errors="replace"))
            rec["case_uid"] = case_uid
            rec["court"] = court
            rec["raw_path"] = raw_path
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    print(
        f"parsed {n} case cards -> {out}"
        f"  (skipped {skipped} missing raw files)"
    )
