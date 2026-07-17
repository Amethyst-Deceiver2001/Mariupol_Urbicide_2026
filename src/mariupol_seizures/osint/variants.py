"""Engine 1 — query-variant expansion (docs/address_osint_assistant_design.md).

From one address produce the ranked search-string set: house-number forms,
street-type-word forms, RU/UA duality (via data/toponyms.csv rename pairs),
and Latin transliteration. Also compiles the match regexes the local-corpus
sources (death_records, local_evidence) grep with — the same fixed
TYPED_RE-style pattern proven in scripts/323 (street-TYPE word captured so
classify_street() resolves, letter-suffix flexibility on house numbers).
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from ..normalize.address import classify_street, norm_house
from ..normalize.toponym import _key, _toponym_match_key, load_toponyms

log = logging.getLogger(__name__)

# class token -> type-word spellings, most common first. RU then UA.
CLASS_TYPE_WORDS: dict[str, list[str]] = {
    "STREET": ["ул.", "улица", "ул", "вул.", "вулиця"],
    "AVENUE": ["пр.", "просп.", "проспект", "пр-т", "пр-кт"],
    "BOULEVARD": ["б-р", "бул.", "бульвар"],
    "LANE": ["пер.", "переулок", "провулок"],
    "SQUARE": ["пл.", "площадь", "площа"],
    "EMBANKMENT": ["наб.", "набережная", "набережна"],
    "HIGHWAY": ["шоссе", "ш.", "шосе"],
    "PASSAGE": ["проезд", "пр-д", "проїзд"],
    "DEAD_END": ["тупик", "туп."],
    "MICRODISTRICT": ["мкр", "микрорайон", "мікрорайон"],
    "UNKNOWN": [""],
}

_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    "і": "i", "ї": "yi", "є": "ye", "ґ": "g",
}


def translit(s: str) -> str:
    out = []
    for ch in s:
        low = ch.lower()
        t = _TRANSLIT.get(low, ch if low.isascii() else "")
        out.append(t.capitalize() if ch.isupper() and t else t)
    return "".join(out)


def slugify(pid: int | None, key: str) -> str:
    base = translit(key.lower())
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    return f"{pid}_{base}" if pid is not None else base or "unknown"


@dataclass(frozen=True)
class Variant:
    text: str
    lang: str      # ru | ua | translit
    kind: str      # typed | bare | geoquery
    rank: int      # lower = more specific / spend budget here first


def house_forms(house_raw: str | None) -> list[str]:
    """'17а' -> ['17а','17А','17-а','17-А','17 а','17 А']; '37/39' also
    keeps the slash form + first part."""
    if not house_raw:
        return []
    h = norm_house(house_raw) or house_raw.strip().lower()
    forms: list[str] = []
    m = re.match(r"^(\d+)\s*([а-яёa-z]?)(?:/(\d+.*))?$", h)
    if not m:
        return [h]
    num, let, slash = m.group(1), m.group(2), m.group(3)
    if let:
        for sep in ("", "-", " "):
            forms.append(f"{num}{sep}{let}")
            forms.append(f"{num}{sep}{let.upper()}")
    else:
        forms.append(num)
    if slash:
        forms.insert(0, f"{num}/{slash}")
    seen, out = set(), []
    for f in forms:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


def _street_name_pairs(street_raw: str) -> list[tuple[str, str]]:
    """[(name, lang)] — the given name plus its toponym rename counterpart
    (prewar UA name <-> occupation name from data/toponyms.csv) when the
    street participates in a documented rename."""
    pairs: list[tuple[str, str]] = [(street_raw, "ru")]
    try:
        tops = load_toponyms()
        mk = _toponym_match_key(street_raw)
        t = tops.get(mk)
        if t is not None:
            for attr, lang in (("prewar_name", "ua"), ("occupation_name", "ru")):
                other = getattr(t, attr, None)
                if other and _toponym_match_key(other) != mk:
                    pairs.append((other, lang))
    except Exception:  # noqa: BLE001 — toponym table absent is non-fatal
        log.debug("toponym lookup failed for %r", street_raw, exc_info=True)
    return pairs


def expand_variants(prewar_address: str | None,
                    occupation_address: str | None) -> list[Variant]:
    """Full ranked variant set for one property (both address forms in)."""
    out: list[Variant] = []
    seen: set[str] = set()

    def add(text: str, lang: str, kind: str, rank: int) -> None:
        text = re.sub(r"\s+", " ", text).strip()
        if text and text.lower() not in seen:
            seen.add(text.lower())
            out.append(Variant(text, lang, kind, rank))

    for raw in filter(None, {occupation_address, prewar_address}):
        street_part, house_part = _split(raw)
        cs = classify_street(street_part)
        if cs is None:
            add(raw, "ru", "bare", 50)
            continue
        stem = cs.street_clean
        # strip a leading type word from the cleaned form to get the bare stem
        m = re.match(r"^\s*\S+\.?\s+(.*)$", stem)
        bare_stem = stem
        cls = cs.street_key.partition(":")[0]
        for tw in CLASS_TYPE_WORDS.get(cls, [""]):
            if m and stem.lower().startswith(tuple(w.lower() for w in CLASS_TYPE_WORDS.get(cls, []) if w)):
                bare_stem = m.group(1)
                break
        hforms = house_forms(house_part) or [""]
        rank = 0
        for name, lang in _street_name_pairs(bare_stem):
            type_words = CLASS_TYPE_WORDS.get(cls, [""])
            for i, tw in enumerate(type_words):
                for j, hf in enumerate(hforms):
                    q = f"{tw} {name} {hf}".strip() if tw else f"{name} {hf}".strip()
                    add(q, lang, "typed" if tw else "bare", rank + i + j)
            add(f"{name} {hforms[0]}".strip(), lang, "bare", rank + 5)
            rank += 10
        # Latin transliteration of the most specific form (YouTube/Western)
        add(translit(f"{bare_stem} {hforms[0]}".strip()), "translit", "bare", 40)
        add(f"Mariupol {translit(bare_stem)}", "translit", "bare", 45)
    out.sort(key=lambda v: v.rank)
    return out


def _split(raw: str) -> tuple[str, str | None]:
    raw = raw.strip()
    if "," in raw:
        s, _, h = raw.partition(",")
        return s.strip(), h.strip() or None
    m = re.search(r"^(.*?)[\s]+(?:д\.?\s*)?(\d+[а-яА-ЯёЁa-zA-Z]?(?:/\d+)?)\s*$", raw)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return raw, None


# ── local-corpus match regexes ─────────────────────────────────────────────

_FOLD = str.maketrans({"і": "и", "ї": "и", "є": "е", "ё": "е", "ґ": "г"})


def street_stems(bundle) -> set[str]:
    """Plain folded lowercase street stems for this address (both address
    forms + toponym rename counterparts), e.g. {'зелинского'}. Used as a
    cheap byte-substring pre-filter over large raw corpora before the full
    match_regexes() pass (a byte `in` check is ~1000× cheaper than json.loads
    per file — see telegram_local)."""
    stems: set[str] = set()
    for raw in filter(None, {bundle.prewar_address, bundle.occupation_address}):
        street_part, _house = _split(raw)
        cs = classify_street(street_part)
        stem_src = cs.street_clean if cs else street_part
        m = re.match(r"^\s*\S+\.?\s+(.+)$", stem_src)
        bare = m.group(1) if m and classify_street(stem_src) else stem_src
        for name, _lang in _street_name_pairs(bare):
            stems.add(name.lower().translate(_FOLD))
    return stems


def match_regexes(bundle) -> list[re.Pattern]:
    """Compiled regexes that hit any street-stem variant followed (within a
    short window) by any house form. Applied to raw corpus text, so folded
    UA/RU letter drift is matched via character classes, not translate()."""
    stems: set[str] = set()
    houses: set[str] = set()
    for raw in filter(None, {bundle.prewar_address, bundle.occupation_address}):
        street_part, house_part = _split(raw)
        cs = classify_street(street_part)
        stem_src = cs.street_clean if cs else street_part
        m = re.match(r"^\s*\S+\.?\s+(.+)$", stem_src)
        bare = m.group(1) if m and classify_street(stem_src) else stem_src
        for name, _lang in _street_name_pairs(bare):
            stems.add(name.lower().translate(_FOLD))
        for hf in house_forms(house_part):
            houses.add(hf.lower())
    pats = []
    for stem in stems:
        # fold RU<->UA letter drift: и<->і, е<->є/ё, and the -ского <-> -ського
        # suffix (optional soft sign before к), so "Зелинского" also matches
        # "Зелінського" in UA-language corpora (memorial.ua etc.)
        stem_rx = (re.escape(stem)
                   .replace("и", "[иі]").replace("е", "[еєё]")
                   .replace("ск", "с[ьъ]?к"))
        if houses:
            house_alt = "|".join(
                re.escape(h).replace("\\-", r"\s*-?\s*") for h in sorted(houses, key=len, reverse=True)
            )
            # allow "стем, д. 17а" / "стем 17-а" / "стем,17а" / "стем17а"
            # (zero-gap: confirmed in real corpus text, e.g. a VK post
            # captured 2026-07-16 literally reads "Зелинского17а" with no
            # separator). No leading \b before house_alt — Cyrillic-letter
            # -> digit is NOT a Unicode word-boundary transition (both
            # count as \w), so a leading \b silently failed to match this
            # real zero-gap pattern. Trailing \b is kept to stop the group
            # matching a prefix of a longer house number (e.g. "17" inside
            # "170").
            pats.append(re.compile(
                rf"{stem_rx}[^\n.;]{{0,15}}?(?:д\.?\s*)?({house_alt})\b",
                re.IGNORECASE))
        else:
            pats.append(re.compile(stem_rx, re.IGNORECASE))
    return pats
