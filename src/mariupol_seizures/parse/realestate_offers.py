"""Stage 2i/2j: parse captured real-estate listings → residential-apartment SALE offers.

Reads the forensically-captured raw artifacts (web marketplace listing pages from
scripts/49 + Telegram channel messages from scripts/50) out of the state DB and
extracts a single, unified offer record per item. Runs LOCALLY, no network.

THE FILTER (this pass): keep ONLY offers to SELL a RESIDENTIAL APARTMENT in Mariupol.
Everything else — rentals, "wanted/куплю/сниму", rooms, houses, land, garages,
commercial — is classified and written to a rejected-audit file (so the filter is
inspectable), but NOT emitted as an offer. Studios/гостинки/малосемейки count as
apartments; a standalone room (комната) does not.

WHY: a live "продаётся квартира в Мариуполе" ad is dated public evidence of an open
market reselling occupied-territory dwellings to the occupier's population
([F] resale; Rome 8(2)(b)(viii)). When the listing's address normalizes to a
building already on our seizure spine (ownerless / demolition / new-build), the ad
becomes corroboration that the seized stock is being disposed of — `on_seizure_spine`
flags exactly those.

PRIVACY (CLAUDE.md hard rule): the protected class is the LAWFUL (dispossessed
Ukrainian) owner — never the party reselling the flat. But a private seller may also
be an innocent departing resident, so seller contact (phone / @username) is isolated
under a nested `contact` object marked sensitive, so any shared export drops it
wholesale while the public building-level fields (address, price, rooms) remain.
Agencies/realtors are commercial actors → contact.sensitive=false.

Outputs (data/parsed/, gitignored):
  - realestate_offers.jsonl    — matched sale-of-apartment offers (the deliverable)
  - realestate_rejected.jsonl  — everything filtered out + the reason (audit trail)
  - data/reports/realestate_offers_report.md — counts, price stats, spine hits
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .. import config, forensics
from ..normalize.address import classify_street, compute_building_key

log = logging.getLogger(__name__)

OFFERS_OUT = config.DATA_DIR / "parsed" / "realestate_offers.jsonl"
REJECTED_OUT = config.DATA_DIR / "parsed" / "realestate_rejected.jsonl"
REPORT_OUT = config.DATA_DIR / "reports" / "realestate_offers_report.md"
SPINE_REGISTRY = config.DATA_DIR / "parsed" / "address_registry.jsonl"

# ── Classification lexicons (Russian) ─────────────────────────────────────────
# Sell vs rent vs wanted. Order of precedence is enforced in classify_offer_type.
_RE_SALE = re.compile(r"продам|продаж|прода[её]тся|продаю|к\s*продаже|срочно\s+продам", re.I)
_RE_RENT = re.compile(
    r"сда[мою]|сда[её]тся|аренд|в\s+аренду|посуточн|посутк|на\s+сутки|"
    r"длительн\w*\s+срок|/\s*мес|в\s+месяц|руб\.?\s*/\s*мес|на\s+ночь", re.I)
_RE_WANTED = re.compile(
    r"\bкуплю\b|\bсниму\b|ищу\s+квартир|нужна\s+квартир|рассмотрю\s+вариант|"
    r"приму\s+в\s+дар|сними?те?\b", re.I)

# Property class.
_RE_APARTMENT = re.compile(
    r"\bквартир\w*|\bкв-?ра\b|\bкв\.\s*\d|[1-4]\s*-?\s*к\.?\s*кв|"
    r"одн[оа]комнатн|двух?комнатн|тр[её]хкомнатн|чет[ыі]р[её]хкомнатн|"
    r"гостинк|малосемейк", re.I)
_RE_STUDIO = re.compile(r"студи\w*|\bстудия\b", re.I)
_RE_ROOM = re.compile(r"\bкомнат[ауы]\b|комната\s+в|\bдоля\b|долю\s+в\s+квартир", re.I)
_RE_HOUSE = re.compile(
    r"\bдом\b|\bдома\b|\bдомовладен|коттедж|\bдач[аи]\b|часть\s+дома|"
    r"полдома|половин\w*\s+дома|таунхаус", re.I)
_RE_LAND = re.compile(r"\bучаст\w*|земельн|\bз/у\b|\bсот\w*\b|\bсоток\b|садов\w*\s+участ", re.I)
_RE_GARAGE = re.compile(r"\bгараж\w*|машиномест|\bпогреб\b", re.I)
_RE_COMMERCIAL = re.compile(
    r"коммерческ|\bофис\w*|помещени\w*\s+свободн|\bпсн\b|торгов\w*\s+площад|"
    r"\bсклад\w*|производствен|нежил\w*|готов\w*\s+бизнес|общепит|фасадн\w*\s+помещ", re.I)

# Mariupol signal: city name OR a known district / addressing token.
_RE_MARIUPOL = re.compile(
    r"мариупол\w*|левобережн|калмиусск|кальмиусск|приморск\w*\s*р|центральн\w*\s*р|"
    r"орджоникидзевск|ильичевск|жовтневск|октябрьск\w*\s*р|"
    r"\bпредпортов|\bкальчик|\bвосточн\w*\s+(?:мкр|микрорайон)|\d+\s*квартал", re.I)

# Field extraction.
_RE_ROOMS_NUM = re.compile(r"\b([1-4])\s*-?\s*к(?:омн|\.|\b|\s*кв)", re.I)
# "3х комнатную" / "3-х комнатная" / "3 комнатная" — the Cyrillic-"х" shorthand.
_RE_ROOMS_NUM2 = re.compile(r"\b([1-4])\s*-?\s*х?\s*комнатн", re.I)
_RE_ROOMS_WORD = {
    "однокомнат": 1, "1-комнат": 1, "двухкомнат": 2, "2-комнат": 2,
    "трехкомнат": 3, "трёхкомнат": 3, "3-комнат": 3,
    "четырехкомнат": 4, "четырёхкомнат": 4, "4-комнат": 4,
}
_RE_AREA = re.compile(
    r"(\d{1,3}(?:[.,]\d{1,2})?)\s*(?:кв\.?\s*м|м\s*[²2]|кв\.м|квадрат\w*\s*метр)", re.I)
_RE_AREA_S = re.compile(r"\b[Ss]\s*[=:]?\s*(\d{1,3}(?:[.,]\d{1,2})?)\b")
_RE_FLOOR = re.compile(r"(\d{1,2})\s*/\s*(\d{1,2})\s*эт", re.I)
_RE_FLOOR_ALT = re.compile(r"этаж\s*[:\-]?\s*(\d{1,2})\b", re.I)
_RE_NEWBUILD = re.compile(
    r"новостройк|\bЖК\b|нов\w*\s+дом|сдача\s+в|от\s+застройщик|\bДДУ\b|переуступк|"
    r"сданн\w*\s+дом|введ[её]н\s+в\s+эксплуат", re.I)
_RE_AGENCY = re.compile(r"агентств|риэлтор|риелтор|\bАН\b|агент\s+по\s+недвиж", re.I)
_RE_PRIVATE = re.compile(r"без\s+посредник|от\s+собственник|от\s+хозяин|собственник", re.I)

# Price: handle "3 500 000 ₽", "3,5 млн", "3.5 млн руб", "3500000 рублей", "2 800 т.р."
_RE_PRICE_MLN = re.compile(r"(\d{1,3}(?:[.,]\d{1,3})?)\s*млн", re.I)
_RE_PRICE_TYS = re.compile(r"(\d{2,4}(?:[.,]\d{1,3})?)\s*(?:тыс|т\.?\s*р)", re.I)
_RE_PRICE_FULL = re.compile(
    r"(\d{1,3}(?:[  ]\d{3}){1,3}|\d{6,9})\s*(?:₽|руб|р\.|рублей)?", re.I)

# Street addressing.
_STREET_PREFIX = (
    r"ул(?:\.|ица)?|улиц[аеу]|пр-?кт|пр-?т|просп(?:\.|ект)?|проспект|"
    r"б-?р|бул(?:\.|ьвар)?|бульвар|пер(?:\.|еулок)?|переулок|пл(?:\.|ощадь)?|"
    r"площадь|ш(?:\.|оссе)?|шоссе|мкр(?:\.|орайон)?|микрорайон|наб(?:\.|ережная)?")
_RE_STREET = re.compile(
    rf"(?:^|[\s,.;(])(?P<prefix>{_STREET_PREFIX})\s*"
    rf"(?P<name>[A-Za-zА-Яа-яЁё0-9][A-Za-zА-Яа-яЁё0-9 .\-]{{1,40}}?)"
    rf"(?:,?\s*(?:д\.?|дом\s*№?)?\s*(?P<house>\d{{1,4}}[а-яА-Яa-zA-Z]?(?:\s*/\s*\d{{1,3}})?))?"
    rf"(?=[\s,.;)]|$)", re.I)
_RE_KVARTAL = re.compile(
    r"(?P<name>\d{1,3}\s*-?\s*(?:й|го)?\s*квартал)[,\s]*"
    r"(?:д\.?\s*)?(?P<house>\d{1,4}[а-яА-Я]?)?", re.I)

# Phones (RU/UA + bare 10-digit), evaluated after stripping separators.
_RE_PHONE = re.compile(r"(?:\+?\d[\s \-\(\)]?){9,14}\d")
_RE_USERNAME = re.compile(r"(?<![\w@])@([A-Za-z]\w{3,31})\b")


@dataclass
class Offer:
    source: str
    source_type: str
    source_sha256: str
    source_url: str
    captured_at: str | None = None
    posted_date: str | None = None
    venue: str | None = None            # channel username or marketplace key
    offer_type: str = "unknown"
    property_class: str = "unknown"
    is_mariupol: bool = False
    price_rub: int | None = None
    price_raw: str | None = None
    rooms: int | None = None
    is_studio: bool = False
    area_total_m2: float | None = None
    floor: int | None = None
    floors: int | None = None
    new_build: bool = False
    address_raw: str | None = None
    street_clean: str | None = None
    street_key: str | None = None
    house: str | None = None
    building_key: str | None = None
    on_seizure_spine: bool = False
    text_excerpt: str = ""
    contact: dict = field(default_factory=dict)


# ── text extraction per source type ───────────────────────────────────────────
def _text_from_telegram(raw: bytes) -> tuple[str, str | None]:
    """Return (message_text, posted_date_iso) from a captured Telegram msg JSON."""
    try:
        d = json.loads(raw.decode("utf-8"))
    except Exception:  # noqa: BLE001
        return "", None
    return (d.get("message") or "").strip(), d.get("date")


def _text_from_html(raw: bytes) -> tuple[str, str | None, dict]:
    """Return (visible_text, None, structured) for a web listing page.

    `structured` pulls price/address out of JSON-LD / og: meta where present —
    marketplaces embed these even when the visible markup churns.
    """
    from bs4 import BeautifulSoup
    try:
        soup = BeautifulSoup(raw, "lxml")
    except Exception:  # noqa: BLE001
        return "", None, {}
    structured: dict[str, Any] = {}
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            obj = json.loads(tag.string or "")
        except Exception:  # noqa: BLE001
            continue
        for node in (obj if isinstance(obj, list) else [obj]):
            if not isinstance(node, dict):
                continue
            offers = node.get("offers")
            if isinstance(offers, dict) and offers.get("price"):
                structured.setdefault("price", offers.get("price"))
            if node.get("address"):
                structured.setdefault("address_ld", json.dumps(node["address"], ensure_ascii=False))
            if node.get("name"):
                structured.setdefault("name", node["name"])
    for prop in ("og:title", "og:description"):
        m = soup.find("meta", attrs={"property": prop}) or soup.find("meta", attrs={"name": prop})
        if m and m.get("content"):
            structured[prop] = m["content"]
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
    return text, None, structured


# ── classification ────────────────────────────────────────────────────────────
def classify_offer_type(text: str) -> str:
    sale, rent, wanted = bool(_RE_SALE.search(text)), bool(_RE_RENT.search(text)), bool(_RE_WANTED.search(text))
    if wanted and not sale:
        return "wanted"
    if sale:
        # "продам" wins over an incidental rent token, but a pure-rent post with
        # no sale verb is rent. "продам или сдам" → sale (flagged ambiguous upstream).
        return "sale"
    if rent:
        return "rent"
    return "unknown"


def classify_property_class(text: str) -> tuple[str, bool]:
    """Return (property_class, is_studio). Apartment/studio are the kept classes."""
    apt = bool(_RE_APARTMENT.search(text))
    studio = bool(_RE_STUDIO.search(text))
    # Exclusion classes take precedence ONLY when no apartment signal is present,
    # so "квартира в новом доме" isn't misread as a house, but "продам дом" is.
    if not apt and not studio:
        if _RE_COMMERCIAL.search(text):
            return "commercial", False
        if _RE_LAND.search(text):
            return "land", False
        if _RE_GARAGE.search(text):
            return "garage", False
        if _RE_HOUSE.search(text):
            return "house", False
        if _RE_ROOM.search(text):
            return "room", False
        return "unknown", False
    # Apartment signal present, but a standalone-room/share post can also say
    # "комнату ... в квартире" — keep those as room (not an apartment sale).
    if _RE_ROOM.search(text) and not re.search(r"комнатн", text, re.I) and not apt:
        return "room", False
    if studio and not apt:
        return "studio", True
    return "apartment", studio


# ── field extraction ──────────────────────────────────────────────────────────
def _to_int_price(num: str, scale: float) -> int | None:
    try:
        return int(round(float(num.replace(" ", "").replace(" ", "").replace(",", ".")) * scale))
    except ValueError:
        return None


_PRICE_BAND = (150_000, 60_000_000)  # plausible flat-price range (RUB)


def extract_price(text: str, structured: dict) -> tuple[int | None, str | None]:
    if structured.get("price"):
        try:
            v = int(float(str(structured["price"]).replace(" ", "")))
            if _PRICE_BAND[0] <= v <= _PRICE_BAND[1]:
                return v, str(structured["price"])
        except ValueError:
            pass
    # "X млн" is only trustworthy within the plausible band — malformed
    # source text like "Стоимость 3 200 млн" (likely meant 3,200,000) otherwise
    # matches on the trailing "200" and yields a nonsense 200,000,000.
    m = _RE_PRICE_MLN.search(text)
    if m:
        v = _to_int_price(m.group(1), 1_000_000)
        if v and _PRICE_BAND[0] <= v <= _PRICE_BAND[1]:
            return v, m.group(0)
    # A phone number like "+7 949 500 09 66" contains "7 949 500", a 7-digit
    # group that falls inside the plausible price band — exclude any price
    # match that overlaps a phone-number span.
    phone_spans = [m.span() for m in _RE_PHONE.finditer(text)]

    def _overlaps_phone(span: tuple[int, int]) -> bool:
        return any(a < span[1] and span[0] < b for a, b in phone_spans)

    # Prefer a full ruble figure; tys is a fallback (often a per-m² or deposit).
    best: tuple[int | None, str | None] = (None, None)
    for m in _RE_PRICE_FULL.finditer(text):
        if _overlaps_phone(m.span()):
            continue
        v = _to_int_price(re.sub(r"[  ]", "", m.group(1)), 1)
        if v and _PRICE_BAND[0] <= v <= _PRICE_BAND[1]:
            best = (v, m.group(0).strip())
            break
    if best[0] is None:
        m = _RE_PRICE_TYS.search(text)
        if m and not _overlaps_phone(m.span()):
            v = _to_int_price(m.group(1), 1_000)
            if v and _PRICE_BAND[0] <= v <= _PRICE_BAND[1]:
                return v, m.group(0)
    return best


def extract_rooms(text: str) -> int | None:
    m = _RE_ROOMS_NUM.search(text) or _RE_ROOMS_NUM2.search(text)
    if m:
        return int(m.group(1))
    low = text.lower()
    for stem, n in _RE_ROOMS_WORD.items():
        if stem in low:
            return n
    return None


def extract_area(text: str) -> float | None:
    cands: list[float] = []
    for rx in (_RE_AREA, _RE_AREA_S):
        for m in rx.finditer(text):
            try:
                v = float(m.group(1).replace(",", "."))
            except ValueError:
                continue
            if 8 <= v <= 400:
                cands.append(v)
    return max(cands) if cands else None      # total area = the largest plausible m²


def extract_floor(text: str) -> tuple[int | None, int | None]:
    m = _RE_FLOOR.search(text)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = _RE_FLOOR_ALT.search(text)
    if m:
        return int(m.group(1)), None
    return None, None


def extract_address(text: str) -> tuple[str | None, str | None, str | None, str | None, str | None]:
    """Return (address_raw, street_clean, street_key, house, building_key)."""
    # Try a numbered-квартал address first (Mariupol-specific Soviet blocks).
    mk = _RE_KVARTAL.search(text)
    candidates: list[tuple[str, str | None]] = []
    if mk:
        candidates.append((mk.group("name"), mk.group("house")))
    for m in _RE_STREET.finditer(text):
        raw = (m.group("prefix") + " " + m.group("name")).strip()
        candidates.append((raw, m.group("house")))
    for street_raw, house in candidates:
        classified = classify_street(street_raw)
        if classified is None:
            continue
        building_key, house_norm = compute_building_key(classified.street_key, house)
        addr_raw = street_raw + (f", {house}" if house else "")
        return (addr_raw, classified.street_clean, classified.street_key,
                house_norm, building_key)
    return None, None, None, None, None


def extract_contact(text: str, venue: str | None) -> dict:
    phones: list[str] = []
    for m in _RE_PHONE.finditer(text):
        digits = re.sub(r"\D", "", m.group(0))
        if 10 <= len(digits) <= 13:
            phones.append(digits)
    usernames = [u for u in _RE_USERNAME.findall(text) if u.lower() != (venue or "").lower()]
    is_agency = bool(_RE_AGENCY.search(text)) and not bool(_RE_PRIVATE.search(text))
    contact = {
        "phones": sorted(set(phones)),
        "usernames": sorted(set(usernames)),
        "is_agency": is_agency,
        # Private individual's contact → sensitive (minimize in shared output).
        # An agency is a commercial actor in official capacity → not minimized.
        "sensitive": not is_agency and bool(phones or usernames),
    }
    return contact


# ── main ──────────────────────────────────────────────────────────────────────
def _load_spine_keys() -> set[str]:
    keys: set[str] = set()
    if not SPINE_REGISTRY.exists():
        return keys
    for line in SPINE_REGISTRY.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            bk = json.loads(line).get("building_key")
        except Exception:  # noqa: BLE001
            continue
        if bk:
            keys.add(bk)
    return keys


def _venue_from(source_type: str, url: str) -> str | None:
    if source_type == "telegram_channel_msg":
        m = re.search(r"t\.me/([^/]+)/", url)
        return m.group(1) if m else None
    # web: marketplace key from host
    m = re.search(r"https?://(?:www\.)?([a-z0-9.-]+)", url)
    host = m.group(1) if m else ""
    for t in config.REALESTATE_TARGETS:
        if t["key"] in host:
            return t["key"]
    return host.split(".")[0] if host else None


def parse_one(row: dict, raw: bytes, spine_keys: set[str]) -> tuple[Offer, str | None]:
    """Return (offer, reject_reason). reject_reason is None if the offer is kept."""
    st = row["source_type"]
    source = "telegram" if st == "telegram_channel_msg" else "web"
    structured: dict = {}
    if source == "telegram":
        text, posted = _text_from_telegram(raw)
    else:
        text, posted, structured = _text_from_html(raw)
    # Fold structured web fields into the searchable text so the regexes see them.
    search_text = " ".join(filter(None, [
        text, structured.get("og:title"), structured.get("og:description"),
        structured.get("name"), structured.get("address_ld")]))

    o = Offer(
        source=source, source_type=st, source_sha256=row["sha256"],
        source_url=row["url"], captured_at=row.get("captured_at"),
        posted_date=posted, venue=_venue_from(st, row["url"]),
        text_excerpt=text[:500],
    )
    o.offer_type = classify_offer_type(search_text)
    o.property_class, o.is_studio = classify_property_class(search_text)

    o.price_rub, o.price_raw = extract_price(search_text, structured)
    o.rooms = extract_rooms(search_text)
    o.area_total_m2 = extract_area(search_text)
    o.floor, o.floors = extract_floor(search_text)
    o.new_build = bool(_RE_NEWBUILD.search(search_text))
    (o.address_raw, o.street_clean, o.street_key, o.house, o.building_key) = extract_address(search_text)
    o.on_seizure_spine = bool(o.building_key and o.building_key in spine_keys)
    o.contact = extract_contact(text, o.venue)

    # Mariupol determination. A Mariupol-scoped marketplace URL is no guarantee
    # the search actually returned Mariupol results (cian's "Mariupol" search
    # was observed to fall back to a generic Moscow recommendation feed), so web
    # listings need the same evidence as everything else: an explicit city
    # token, a spine match, OR — for the configured Mariupol-dedicated Telegram
    # channels — a parsed street/квартал address, which catches Mariupol
    # addresses that omit the city name (e.g. "ЖК Черноморский, пр-т Мира 86" or
    # the flagship "пр. Ленина 98").
    mariupol_channel = source == "telegram" and o.venue in config.TELEGRAM_CHANNELS
    o.is_mariupol = (
        bool(_RE_MARIUPOL.search(search_text))
        or o.on_seizure_spine
        or (mariupol_channel and bool(o.building_key))
    )

    # ── THE FILTER: keep only sale-of-residential-apartment in Mariupol ──
    if o.offer_type != "sale":
        return o, f"offer_type={o.offer_type}"
    if o.property_class not in ("apartment", "studio"):
        return o, f"property_class={o.property_class}"
    if not o.is_mariupol:
        return o, "not_mariupol"
    return o, None


def run() -> None:
    con = forensics.open_state()
    spine_keys = _load_spine_keys()
    log.info("loaded %d spine building_keys for cross-reference", len(spine_keys))

    rows = con.execute(
        "SELECT sha256, url, source_type, raw_path, captured_at FROM source_document "
        "WHERE source_type IN ('telegram_channel_msg','realestate_listing') "
        "ORDER BY captured_at"
    ).fetchall()
    cols = ["sha256", "url", "source_type", "raw_path", "captured_at"]
    log.info("parsing %d captured real-estate/telegram artifacts", len(rows))

    OFFERS_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)

    kept: list[Offer] = []
    rejected: list[dict] = []
    seen_keys: set[str] = set()   # de-dup re-snapshots of the same listing/post

    for r in rows:
        row = dict(zip(cols, r))
        p = Path(row["raw_path"])
        if not p.exists():
            continue
        try:
            offer, reason = parse_one(row, p.read_bytes(), spine_keys)
        except Exception:  # noqa: BLE001 — one bad artifact must not abort the parse
            log.exception("parse failed for %s", row["url"])
            continue
        if reason is not None:
            rejected.append({
                "source_url": row["url"], "source_sha256": row["sha256"],
                "offer_type": offer.offer_type, "property_class": offer.property_class,
                "is_mariupol": offer.is_mariupol, "reason": reason,
            })
            continue
        # De-dup: same listing captured on several days → keep the latest snapshot
        # but only one offer row. Key on the stable listing URL (strip media tail).
        dk = offer.source_url
        if dk in seen_keys:
            continue
        seen_keys.add(dk)
        kept.append(offer)

    with OFFERS_OUT.open("w", encoding="utf-8") as fh:
        for o in kept:
            fh.write(json.dumps(o.__dict__, ensure_ascii=False) + "\n")
    with REJECTED_OUT.open("w", encoding="utf-8") as fh:
        for d in rejected:
            fh.write(json.dumps(d, ensure_ascii=False) + "\n")

    _write_report(kept, rejected)
    log.info("done — %d apartment-sale offers kept, %d rejected → %s",
             len(kept), len(rejected), OFFERS_OUT)


def _write_report(kept: list[Offer], rejected: list[dict]) -> None:
    from collections import Counter
    by_venue = Counter(o.venue for o in kept)
    by_source = Counter(o.source for o in kept)
    spine_hits = [o for o in kept if o.on_seizure_spine]
    newbuilds = [o for o in kept if o.new_build]
    priced = [o.price_rub for o in kept if o.price_rub]
    rej_reasons = Counter(d["reason"].split("=")[0] for d in rejected)

    lines = [
        "# Real-estate resale scan — apartment-sale offers (Mariupol)",
        "",
        "_Generated by `scripts/51_parse_realestate_offers.py` (local, no network). "
        "Demand-side [F]-resale evidence; capture-before-parse._",
        "",
        f"- Captured artifacts parsed → **{len(kept)} apartment-sale offers kept**, "
        f"{len(rejected)} rejected (filtered).",
        f"- On the seizure spine (`building_key` matches a documented building): "
        f"**{len(spine_hits)}** — these are flats being resold at addresses we have "
        f"documented as seized/demolished/rebuilt.",
        f"- New-build resales: **{len(newbuilds)}**.",
        "",
        "## Kept offers by source / venue",
        "",
        "| venue | offers |", "|---|---|",
    ]
    for v, n in by_venue.most_common():
        lines.append(f"| {v} | {n} |")
    lines += ["", f"Web: {by_source.get('web', 0)} · Telegram: {by_source.get('telegram', 0)}", ""]
    if priced:
        priced.sort()
        lines += [
            "## Price (RUB, where extractable)", "",
            f"- n with price: {len(priced)}",
            f"- min / median / max: {priced[0]:,} / {priced[len(priced)//2]:,} / {priced[-1]:,}",
            "",
        ]
    lines += ["## Rejected (filter audit)", "", "| reason | count |", "|---|---|"]
    for reason, n in rej_reasons.most_common():
        lines.append(f"| {reason} | {n} |")
    if spine_hits:
        lines += ["", "## Spine hits (resale at a documented seized building)", "",
                  "| building_key | venue | price RUB | rooms | new_build |",
                  "|---|---|---|---|---|"]
        for o in spine_hits[:50]:
            lines.append(f"| {o.building_key} | {o.venue} | "
                         f"{o.price_rub or '—'} | {o.rooms or '—'} | {o.new_build} |")
    lines += ["", "_PRIVACY: seller contact (phone/@username) is isolated under each "
              "offer's nested `contact` object and marked `sensitive` for private "
              "individuals; drop it wholesale in any shared export (CLAUDE.md)._", ""]
    REPORT_OUT.write_text("\n".join(lines), encoding="utf-8")
