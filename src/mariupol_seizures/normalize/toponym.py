"""Address normalization against the Mariupol toponym table.

Court records use Russian-occupation street names. Restitution claims need
the prewar Ukrainian name so a displaced owner can recognise their property.
This module loads data/toponyms.csv into an in-memory index and exposes
normalize_address(raw) -> {occupation_name, prewar_name, source_ref, ...}.

Matching is exact on the street stem (case- and prefix-insensitive). Fuzzy
matching is intentionally NOT done here — false positives in toponym data
would corrupt the evidence chain. Unmatched addresses return the raw input
with prewar_name = None; downstream code decides what to do.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .. import config

# Street-type vocabulary, grouped by physical class. Keys MUST keep the class
# distinct: a "проспект Леніна" and "Площа Леніна" are different objects, so
# their lookup keys must not collide. Each variant maps to a canonical class
# token used in the lookup key.
_CLASS_MAP: dict[str, str] = {
    # streets
    "ул":  "STREET", "ул.": "STREET", "улица":  "STREET",
    "вул": "STREET", "вул.": "STREET", "вулиця": "STREET",
    # avenues
    "пр":  "AVENUE", "пр.": "AVENUE", "пр-т":  "AVENUE", "пр-т.": "AVENUE",
    "пр-кт": "AVENUE", "пр-кт.": "AVENUE", "п-т": "AVENUE", "п-т.": "AVENUE",
    "просп": "AVENUE", "просп.": "AVENUE",
    "проспект": "AVENUE", "проспекта": "AVENUE",
    # OCR typo for "проспект" (п/т transposition): "простект Строителей"
    # vs "проспект Строителей" at the same house, geom_dist 9.8m -- confirmed
    # 2026-06-11 (corroboration_candidates.csv row 82). No other Russian
    # street-type word resembles "простект", so this can't collide.
    "простект": "AVENUE",
    # boulevards
    "б-р": "BOULEVARD", "б-р.": "BOULEVARD", "бул": "BOULEVARD", "бул.": "BOULEVARD",
    "бульвар": "BOULEVARD",
    # OCR misread of "Б-р" (capital Б resembling '6' in low-quality scans):
    # "6-р Шевченко" vs "бульвар Шевченко" at the same house, geom_dist 4.4m
    # -- confirmed 2026-06-11 (corroboration_candidates.csv row 97).
    "6-р": "BOULEVARD",
    # squares
    "пл":  "SQUARE", "пл.": "SQUARE",
    "площадь": "SQUARE", "площа": "SQUARE",
    # lanes / passages
    "пер": "LANE", "пер.": "LANE", "переулок": "LANE", "провулок": "LANE",
    "пр-д": "PASSAGE", "проезд": "PASSAGE", "проїзд": "PASSAGE",
    # embankments
    "наб": "EMBANKMENT", "наб.": "EMBANKMENT",
    "набережная": "EMBANKMENT", "набережна": "EMBANKMENT",
    # highways / dead ends / microdistricts / roads
    "ш": "HIGHWAY", "ш.": "HIGHWAY", "шоссе": "HIGHWAY", "шосе": "HIGHWAY",
    "туп": "DEAD_END", "туп.": "DEAD_END",
    "тупик": "DEAD_END", "тупік": "DEAD_END",
    "мкр": "MICRODISTRICT", "мкр.": "MICRODISTRICT",
    "микрорайон": "MICRODISTRICT", "мікрорайон": "MICRODISTRICT",
    # "ЖМС Азовский" / "Азовский жилмассив" / "жилмасив Азовский" (damage
    # assessment) / "жилмассив Азовскиий" (minstroy, OCR) all name the same
    # Soviet-era residential complex in Primorsky district, addressed as
    # "<type> Азовский, <building>[, <apt>]" -- officially "ул. Азовский
    # жилмассив, N" (ua-region.com.ua), i.e. трailing-type form, same pattern
    # as "Тульский проспект". Folding the abbreviation + both common spelling
    # variants (1-с/2-с) to MICRODISTRICT (alongside мкр/микрорайон, the same
    # kind of numbered-complex addressing) lets _classify() handle both the
    # leading ("ЖМС Азовский") and trailing ("Азовский жилмассив") forms via
    # the existing head/tail logic, with no bespoke parsing. Confirmed
    # 2026-06-10: house numbers in the new ownerless-registry XLSX (5, 10)
    # don't collide with damage_assessment's existing "жилмасив Азовский"
    # entries (4, 9) -- different buildings in the same complex, not a merge.
    "жмс": "MICRODISTRICT", "жилмасив": "MICRODISTRICT", "жилмассив": "MICRODISTRICT",
    "д-т": "ROAD", "дорога": "ROAD",
    # parks / small urban gardens
    "сквер": "PARK",
    # descents / slopes
    "спуск": "DESCENT", "спуск.": "DESCENT",
}

# Token used when the prefix is missing or unrecognised. We deliberately keep
# this distinct from any real class so unprefixed inputs never match prefixed
# entries — better to miss than to misattribute.
_CLASS_UNKNOWN = "UNKNOWN"

# Canonical full-word Russian street-type prefix per class, used to build
# Nominatim queries. Empirically, abbreviated prefixes like "пр-т.", "пр-кт",
# "б-р" return zero results from Nominatim's free-text search even when the
# identical street in full-word form ("проспект", "бульвар") resolves at
# house level — so geocode queries should always use these canonical forms,
# while street_occupation keeps the raw/cleaned form for the record.
_CANONICAL_PREFIX: dict[str, str] = {
    "STREET": "улица",
    "AVENUE": "проспект",
    "BOULEVARD": "бульвар",
    "SQUARE": "площадь",
    "LANE": "переулок",
    "PASSAGE": "проезд",
    "EMBANKMENT": "набережная",
    "HIGHWAY": "шоссе",
    "DEAD_END": "тупик",
    "MICRODISTRICT": "микрорайон",
    "ROAD": "дорога",
    "PARK": "сквер",
    "DESCENT": "спуск",
}


def canonical_form(cls: str, stem: str) -> str | None:
    """Combine a class token and a stem into a Nominatim-friendly full-word
    street name, e.g. ("AVENUE", "Металлургов") -> "проспект Металлургов".
    Returns None if the class is unrecognised or has no canonical prefix."""
    if cls == _CLASS_UNKNOWN or not stem:
        return None
    prefix = _CANONICAL_PREFIX.get(cls)
    if not prefix:
        return None
    return f"{prefix} {stem}"


def canonical_street_name(name: str) -> str | None:
    """Return a Nominatim-friendly full-word form of `name`, e.g.
    'пр-т. Металлургов' -> 'проспект Металлургов'. Returns None if the street
    type is unrecognised (_CLASS_UNKNOWN) or has no canonical form — callers
    should fall back to the raw/cleaned name in that case."""
    cls, stem = _classify(name)
    return canonical_form(cls, stem)

# Ukrainian → Russian Cyrillic letter folding for stem comparison only. This
# does NOT change stored data; it only collapses spelling drift so that
# "Леніна" (UA) and "Ленина" (RU) hit the same key.
_FOLD = str.maketrans({
    "і": "и", "І": "и",
    "ї": "и", "Ї": "и",
    "є": "е", "Є": "е",
    "ґ": "г", "Ґ": "г",
    "ё": "е", "Ё": "е",
})


@dataclass(frozen=True)
class Toponym:
    prewar_name: str
    occupation_name: str
    kind: str
    changed_on: str
    source_ref: str
    notes: str


def _classify(name: str) -> tuple[str, str]:
    """Split a street name into (class_token, stem).

    Handles both leading (`ул. Артёма`) and trailing (`Тульский проспект`)
    street-type prefixes, in either Ukrainian or Russian. Returns
    (_CLASS_UNKNOWN, full_text) if no class word is recognised — we'd rather
    miss a match than collide two different street types.
    """
    s = name.strip()
    tokens = re.split(r"\s+", s)
    if not tokens:
        return _CLASS_UNKNOWN, ""

    # Leading prefix?
    head = tokens[0].lower()
    cls = _CLASS_MAP.get(head)
    if cls:
        stem = " ".join(tokens[1:])
        return cls, stem.strip(" .,")

    # Trailing prefix? (e.g. "Тульский проспект", "Лесная улица")
    tail = tokens[-1].lower()
    cls = _CLASS_MAP.get(tail)
    if cls:
        stem = " ".join(tokens[:-1])
        return cls, stem.strip(" .,")

    return _CLASS_UNKNOWN, s.strip(" .,")


def _key(name: str) -> str:
    """Canonical lookup key, used for building_key grouping.

    Form: f"{CLASS}:{folded_stem}". Folding collapses Ukrainian↔Russian
    Cyrillic letter drift so that variant spellings of the same proper name
    match: і↔и, ї↔и, є↔е, ё↔е, ґ↔г (alphabet differences).

    The soft sign ь is preserved here -- it's part of the correct spelling
    for streets like "Азовстальская" (Азовсталь + -ская) and "Львовская"
    (Львов + -ская), and stripping it would corrupt building_key (e.g.
    "STREET:азовсталская"/"STREET:лвовская"). See _toponym_match_key() for
    the separate, ь-folding key used for data/toponyms.csv lookups, where
    OCR'd/occupation-era spellings sometimes drop ь (e.g. "Энгелса" for
    "Энгельса"). Confirmed 2026-06-10: dropping ь here does not change the
    address_registry building count (no internal spelling collisions depend
    on it).

    Class is preserved so that a square and an avenue of the same proper
    name do NOT match.
    """
    cls, stem = _classify(name)
    stem = stem.lower().translate(_FOLD)
    stem = re.sub(r"\s+", " ", stem).strip()
    return f"{cls}:{stem}"


def _toponym_match_key(name: str) -> str:
    """Lookup key for data/toponyms.csv matching only -- _key() plus
    dropping the soft sign ь, to bridge UA -ський ↔ RU -ский endings and
    OCR'd Russian forms that drop ь (e.g. "Энгелса" for "ул. Энгельса").
    Not used for building_key (see _key()): 53 of 449 prewar-name matches in
    the current registry depend on this fold. Confirmed 2026-06-10."""
    return _key(name).replace("ь", "")


def _csv_path() -> Path:
    return config.PROJECT_ROOT / "data" / "toponyms.csv"


@lru_cache(maxsize=1)
def load_toponyms(path: str | None = None) -> dict[str, Toponym]:
    """Load data/toponyms.csv into an occupation_name-keyed index.

    Comment lines (starting with '#') are skipped. Rows without source_ref
    are skipped with no warning — forensic data MUST be cited.
    """
    p = Path(path) if path else _csv_path()
    if not p.exists():
        return {}
    index: dict[str, Toponym] = {}
    with p.open(encoding="utf-8") as fh:
        # Skip comment lines before handing to DictReader so headers parse OK.
        lines = [
            ln for ln in fh
            if ln.strip() and not ln.lstrip().startswith("#")
        ]
    reader = csv.DictReader(lines)
    for row in reader:
        if not row.get("source_ref", "").strip():
            continue
        t = Toponym(
            prewar_name=row.get("prewar_name", "").strip(),
            occupation_name=row.get("occupation_name", "").strip(),
            kind=row.get("kind", "").strip() or "rename",
            changed_on=row.get("changed_on", "").strip(),
            source_ref=row["source_ref"].strip(),
            notes=row.get("notes", "").strip(),
        )
        if not t.occupation_name or not t.prewar_name:
            continue
        index[_toponym_match_key(t.occupation_name)] = t
    return index


def normalize_address(raw: str, path: str | None = None) -> dict:
    """Look up an occupation-era address and enrich with prewar data.

    Returns a dict with:
      occupation_address  — input (unchanged)
      prewar_name         — if matched, otherwise None
      toponym_source      — source URL/citation, if matched
      toponym_confidence  — 1.0 exact match | 0.0 no match
                            (fuzzy matching deliberately excluded)

    The optional `path` argument overrides the default CSV path (used by
    tests). Never raises; unknown addresses round-trip with prewar_name=None.
    """
    result = {
        "occupation_address": raw,
        "prewar_name": None,
        "toponym_source": None,
        "toponym_confidence": 0.0,
    }
    if not raw:
        return result
    # Extract the street-name portion: everything up to the first comma,
    # which is where house/apt info begins in our ADDR_RE matches.
    street_part = raw.split(",", 1)[0]
    hit = load_toponyms(path).get(_toponym_match_key(street_part))
    if hit:
        result["prewar_name"] = hit.prewar_name
        result["toponym_source"] = hit.source_ref
        result["toponym_confidence"] = 1.0
    return result
