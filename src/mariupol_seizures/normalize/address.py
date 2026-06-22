"""Shared occupation-era address cleaning + building_key computation.

Extracted from scripts/21_build_address_registry.py so that both the address
registry builder (script 21, many source extractors) and db/load.py (which
needs to compute the same building_key for court-case addresses, to join
property rows to address_registry.jsonl / geocoded_buildings.jsonl) use one
identical normalization pipeline. Behaviour is unchanged from script 21 --
this is a relocation, not a rewrite.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .toponym import _classify, _key, canonical_form

# Latin lookalikes -> Cyrillic for house-number suffixes. Source spreadsheets
# / OCR mix scripts (e.g. "12A" vs "12А") for visually identical letters.
_LATIN_TO_CYRILLIC = str.maketrans({
    "A": "А", "a": "а", "B": "В", "C": "С", "c": "с", "E": "Е", "e": "е",
    "H": "Н", "K": "К", "k": "к", "M": "М", "O": "О", "o": "о",
    "P": "Р", "p": "р", "T": "Т", "X": "Х", "x": "х",
})


def norm_house(raw: str | None) -> str | None:
    """Normalize a house-number token: 'д. 54А' / 'дом № 9' / '12A' -> '54а' / '9' / '12а'."""
    if not raw:
        return None
    s = raw.strip()
    # "дом №, 56" -- some sources render "Дом №56" with a stray comma between
    # "№" and the digits (e.g. occupation_address "ул. Греческая, дом №, 44").
    # split(",", 1) on that address yields house_raw="дом №, 44"; "№"/"дом"
    # can never be followed by punctuation that's part of the actual house
    # number, so consuming trailing [\s,]* after them is unconditionally
    # safe (and also mops up a bare leading "," with no "дом №" at all).
    # Confirmed 2026-06-11: 18 properties (50 лет ссср|56, металургов|19,
    # фрунзе|29, греческая|44/206/219, etc.) had house_norm "', N'" without
    # this -- a stray-comma artifact, not a different building.
    s = re.sub(r"^(?:дом\s*)?№?[\s,]*", "", s, flags=re.I)
    s = re.sub(r"^д\.?\s*", "", s, flags=re.I)
    s = re.sub(r"^литера\s*", "", s, flags=re.I)
    s = s.strip(" .")
    if not s:
        return None
    s = s.translate(_LATIN_TO_CYRILLIC).lower()
    # "18, г. мариуполь" -- one source appends a trailing city-name annotation
    # after the house number ("улица Набережная, 18, г. Мариуполь"). A real
    # house number can never end in ", г. <name>", so stripping this trailing
    # annotation is unconditionally safe. Confirmed 2026-06-11: property 10624
    # (STREET:набережная) -- this is the only occurrence.
    s = re.sub(r",\s*г\.?\s*[а-яё\-]+$", "", s)
    # "12 а" -> "12а": some sources insert a space before a single-letter
    # building suffix; Russian addressing treats these as the same building.
    s = re.sub(r"^(\d+)\s+([а-яё])$", r"\1\2", s)
    return s


def strip_garbage_prefix(s: str) -> str:
    """Drop leading OCR-table-extraction artefacts like '| ', '_ ', '__'.

    '_' is itself a \\w character, so a plain "non-word" class doesn't strip
    it -- [\\W_] explicitly adds it back to the garbage set. Confirmed
    2026-06-11: '_ Мл. 50 лет СССР' / '__Мл. 50 лет СССР' / '_ пр-кт
    Строителей' were all left unstripped (UNKNOWN class) by the old regex
    (corroboration_candidates.csv rows 54, 71, 72, 95)."""
    return re.sub(r"^[\W_]+", "", s).strip()


def fix_abbrev_spacing(s: str) -> str:
    """'ул.Киевская' -> 'ул. Киевская' so toponym._classify() recognises the prefix."""
    return re.sub(r"^([а-яёА-ЯЁa-zA-Z\-]{1,8}\.)(?=\S)", r"\1 ", s.strip())


def norm_commas(s: str) -> str:
    """OCR sometimes renders ',' as U+201A (single low-9 quote) -- normalize before split."""
    return s.replace("‚", ",")


# "N кв-л" / "N-й квартал" / "N квартал" all denote the same Soviet-era
# numbered residential block, addressed as "N квартал, <house>" -- treat
# "N квартал" as the street-equivalent so all sources land in one
# building_key namespace. Confirmed for 27 квартал/27 кв-л: minstroy uses
# "27 кв-л" (e.g. "...г. Мариуполь, 27 кв-л, д. 7.") for the same buildings
# damage_assessment lists as "27 квартал , 7" -- without this they'd be
# duplicate registry rows for the same building.
_KVARTAL_RE = re.compile(r"^(\d+)\s*-?\s*(?:[а-яё]{1,2}\s+)?(?:кв-л|кв\.|квартал)\.?$", re.I)


def normalize_kvartal(s: str) -> str:
    m = _KVARTAL_RE.match(s.strip())
    if not m:
        return s
    return f"{m.group(1)} квартал"


# Some "N/M" house numbers in damage_assessment are корпус notation ("block M
# of complex N", small sequential M = 1,2,3...) rather than cross-street/
# corner addressing -- normalize "N/M" -> "NкM" so building_key and geocode
# queries match OSM's addr:housenumber=NкM tags instead of (mis)matching via
# _house_matches's cross-street "/"-split intersection logic. Each (street,
# base) pair below is individually map-verified; do NOT generalize this to
# all "N/M" entries -- most others (e.g. "ул. Мамина-Сибиряка, 40/14", "бул.
# Шевченко, 234/147") are genuine corner buildings addressed from two streets,
# where the "/"-split match is correct (per CLAUDE.md: rather miss a match
# than collide two different addresses).
#
# Confirmed корпус (2026-06-10, street-level map):
#   AVENUE:маршала жукова, 60 -> 60/1,60/2,60/3    (seq_no 1183-1185)
#   STREET:9 мая, 5           -> 5/1,5/2,5/3       (seq_no 1187-1189)
#   STREET:9 мая, 19          -> 19/1,19/2,19/3    (seq_no 1194-1196)
#   STREET:киевская, 48       -> 48/1,48/2,48/3    (seq_no 1198-1200)
#
# Confirmed NOT корпус -- genuine "N/M" address as printed on maps (e.g.
# Google Maps labels the building itself "63/1" and shows "Myru Avenue, 63/2"
# as the formatted address) -- left unchanged:
#   AVENUE:ленина, 63/1, 63/2 (seq_no 148-149)
_CORPUS_HOUSE_BASES: dict[str, set[str]] = {
    "AVENUE:маршала жукова": {"60"},
    "STREET:9 мая": {"5", "19"},
    "STREET:киевская": {"48"},
}
_CORPUS_HOUSE_RE = re.compile(r"^(\d+)\s*/\s*([1-3])$")


def normalize_corpus_house(street_key: str, house_raw: str | None) -> str | None:
    if not house_raw:
        return house_raw
    m = _CORPUS_HOUSE_RE.match(house_raw.strip())
    if not m:
        return house_raw
    base, corpus = m.groups()
    if base in _CORPUS_HOUSE_BASES.get(street_key, set()):
        return f"{base}к{corpus}"
    return house_raw


# "50ЛЕТ Октября" / "60ЛЕТ СССР" -- some sources (minstroy, housing
# distribution) drop the space between the digit and "лет" in Soviet
# anniversary street names. "N" immediately followed by "лет" is always
# "N лет" in Russian (never part of a longer word with a different meaning),
# so inserting the space is unconditionally safe. Without it, "50ЛЕТ
# Октября" and "50 лет Октября" fold to different stems and split the same
# building across two property rows. Confirmed 2026-06-11
# (corroboration_candidates.csv rows 2,3,6,7).
_NUMERAL_LET_RE = re.compile(r"(?<=\d)(лет)", re.I)


def _space_numeral_let(s: str) -> str:
    return _NUMERAL_LET_RE.sub(r" \1", s)


# "9-й Авиадивизии" / "9 Авиадивизии", "ПР-КТ 1-ГО МАЯ" / "улица 1 мая":
# occupation-era addressing sometimes spells out the ordinal-adjective
# suffix on a leading street number and sometimes drops it -- both forms
# name the same street. The leading digit (not the suffix) is what
# distinguishes streets, so stripping "-й/-я/-го/..." cannot collide two
# differently-numbered streets ("1-й Кальчик" stays "1 Кальчик", distinct
# from "2-й Кальчик" -> "2 Кальчик"); it only unites a numbered street with
# itself. Confirmed 2026-06-11 (corroboration_candidates.csv rows 14-20,
# 47-53; non-collision verified against rows 62-64).
_ORDINAL_SUFFIX_RE = re.compile(
    r"(?<![\wа-яёА-ЯЁ])(\d+)-(?:ый|ой|ий|ая|яя|ое|ее|ых|их|й|я|е|го)(?=\s)",
    re.I,
)


def _strip_ordinal_suffix(s: str) -> str:
    return _ORDINAL_SUFFIX_RE.sub(r"\1", s)


_ALT_NAME_RE = re.compile(r"^(.*?)\s*\(([^()]+)\)\s*$")


def split_alt_name(s: str) -> tuple[str, str | None]:
    """Split a trailing parenthetical alt-name, e.g. 'проспект Ленина (Мира)'
    -> ('проспект Ленина', 'Мира'). Source spreadsheets sometimes annotate the
    occupation-era street name with its decommunization-era/alternate name in
    parentheses -- this is a query hint already present in the row (no
    source_ref), so it's kept separately as street_alt rather than folded into
    the toponym crosswalk."""
    m = _ALT_NAME_RE.match(s.strip())
    if not m:
        return s, None
    main, alt = m.group(1).strip(), m.group(2).strip()
    if not main or not alt:
        return s, None
    return main, alt


# Curated street_key aliases: the variant key (as produced by _key() after
# the general normalizations above) maps to the canonical key the building
# should be grouped under. Each entry is individually justified by either
# tight geocoded proximity (geom_dist_m) between rows sharing a house number
# in corroboration_candidates.csv, or an unambiguous single-named-street
# reading with no other plausible referent. Following the _CORPUS_HOUSE_BASES
# precedent: a curated map of confirmed identities, not a fuzzy/regex rule.
# Only street_key is remapped (the building_key grouping key); street_clean/
# stem/cls keep the as-cleaned spelling for display and geocoding.
_STREET_KEY_ALIASES: dict[str, str] = {
    # OCR drop of 'т': "Кронштадская" (demolition register) for
    # "Кронштадтская". geom_dist 3.2m (house 12) / 5.6m (house 5) --
    # confirmed 2026-06-11, corroboration_candidates.csv rows 4-5.
    "STREET:кронштадская": "STREET:кронштадтская",
    # Systematic typo (extra 'а'): damage_assessment spells this street
    # "Амурскаая" for "Амурская" across all 5 houses it lists (3,5,7,9,13).
    # geom_dist 9.9m at house 9 confirms identity; the larger distances at
    # the other houses reflect damage_assessment's coarser geocoding, not a
    # different street. Confirmed 2026-06-11, rows 8,9,11-13.
    "STREET:амурскаая": "STREET:амурская",
    # OCR extra 'и': minstroy demolition register spells "Азовскиий" for
    # "Азовский" (жилмассив). Confirmed 2026-06-11, row 10.
    "MICRODISTRICT:азовскиий": "MICRODISTRICT:азовский",
    # Short/full official name: "Б-р Хмельницкого" (housing distribution)
    # vs "бульвар Богдана Хмельницкого" (damage_assessment/demolition) --
    # the same boulevard (Hetman Bohdan Khmelnytsky), there is no other
    # "Хмельницкого" street to confuse with. 8 houses confirm the same
    # short<->full pattern. Confirmed 2026-06-11, rows 21-26,33,36.
    "BOULEVARD:хмельницкого": "BOULEVARD:богдана хмельницкого",
    # Decommunization rename: "ул. Краснофлотская" (demolition register) ==
    # "улица Флотская" (damage_assessment) at houses 157 and 159, geom_dist
    # 1.5-2.5m (essentially the same point for both). Confirmed 2026-06-11,
    # rows 41-42.
    "STREET:краснофлотская": "STREET:флотская",
    # Initial dropped: "ул. Я.Гугеля" (housing distribution) == "улица
    # Гугеля" (damage_assessment) -- Yakov Gugel St., the only "Гугеля"
    # street in Mariupol. Confirmed 2026-06-11, row 46.
    #
    # "О.Дундича" / "О Дундича": same pattern, "улица О.Дундича"
    # (damage_assessment) == "улица О Дундича" (ownerless_registry) at
    # house 59б -- Oleg Dundich St., the only "Дундича" street in Mariupol.
    # Confirmed 2026-06-11, row 45.
    #
    # A general "single Cyrillic letter + dot = initial" regex was tried and
    # reverted: it also matched non-initial single-letter abbreviations
    # ("г." = город, "с." = село, "м." in "М. Гонды") and multi-initial names
    # ("А.Ф.Полетаева"), corrupting their building_ids with no corroborating
    # evidence. These two streets are curated individually instead, keyed on
    # the as-printed dot form (no general dot-stripping is applied upstream).
    "STREET:я.гугеля": "STREET:гугеля",
    # Spelled-out first name: "ул. Якова Гугеля" (MinStroy demolition
    # register, 9 houses: 12,14,16,22,24,26,28,30,32) is the same street as
    # "Я.Гугеля"/"Гугеля" above -- Yakov Hugel St., the only "Гугеля" street
    # in Mariupol. "ул. Якова Гугеля 20" already geocodes successfully as
    # "Гугеля 20" (STREET:гугеля|20, conf 0.9); Nominatim has no match for
    # the spelled-out "Якова Гугеля" form. Confirmed 2026-06-15 via aerial
    # imagery: the Huhelya St block is heavily damaged, consistent with the
    # demolition register entries.
    "STREET:якова гугеля": "STREET:гугеля",
    "STREET:о.дундича": "STREET:о дундича",
    # OCR Г/Т typo with no other reading: "ул. Гаганрогская" (ownerless
    # decree) for "улица Таганрогская" (Taganrog St., a real, common
    # Russian street name -- "Гаганрог" is not a place). Confirmed
    # 2026-06-11, row 55.
    "STREET:гаганрогская": "STREET:таганрогская",
    # Initial-dot abbreviation: "ул. К.Либкнехта" (18 houses, mostly
    # damage_assessment) is the same street as "улица Карла Либкнехта"
    # (8 houses, with prewar toponym match "вул. Митрополитська" --
    # data/toponyms.csv) -- Karl Liebknecht St., the only "Либкнехта" street
    # in Mariupol. As-printed "К.Либкнехта" carries no toponym match and no
    # Nominatim house-level hit (stuck at 0.5/street-level); the aliased
    # canonical form picks up both. 5 houses (94,100,102,110,110а) collide
    # with existing "карла либкнехта" entries and will need a script-34
    # near-miss merge after the registry/geocode reload. Confirmed 2026-06-15.
    "STREET:к.либкнехта": "STREET:карла либкнехта",
    # Same alias, space-after-dot variant: "К. Либкнехта" (with a space after
    # the initial's dot, as printed in the 2025-01-13 ownerless snapshot, "ул
    # К. Либкнехта(Митрополитская), 102") folds to a DIFFERENT _key() than the
    # no-space "К.Либкнехта" form above because _key() only collapses
    # whitespace, not punctuation-adjacent spacing. Same street (Karl
    # Liebknecht), confirmed by the identical "Митрополитская" prewar-name
    # parenthetical already matched to this street above. Confirmed 2026-06-18.
    "STREET:к. либкнехта": "STREET:карла либкнехта",
    # "Воинов Освободителей" (space) vs "Воинов-Освободителей" (hyphen) --
    # both name the same street (liberator-soldiers); the 2025-01-13 ownerless
    # snapshot drops the hyphen for some house numbers while damage_assessment
    # and other ownerless-registry rows keep it. No other "Освободителей"
    # street exists in Mariupol, so this cannot collide. Confirmed 2026-06-18.
    "STREET:воинов освободителей": "STREET:воинов-освободителей",
    # OCR drop of 'к': "Карла Либнехта" (missing 'к') found in ownerless
    # registry for the same Karl Liebknecht St. geom=0.0 confirmed for all
    # 7 pairs surfaced 2026-06-16.
    "STREET:карла либнехта": "STREET:карла либкнехта",
    # Typo (missing 'о'): damage_assessment spells "ул. Кацюбинского" for
    # "ул. Коцюбинского" (Mykhailo Kotsiubynskyi St., the only "...юбинского"
    # street in Mariupol). "Кацюбинского 5" never geocoded at all (no
    # Nominatim match for the misspelled form); "Коцюбинского 34" geocodes
    # house-level. No house-number collision (5 vs 34). Confirmed 2026-06-15.
    "STREET:кацюбинского": "STREET:коцюбинского",
}


@dataclass(frozen=True)
class ClassifiedStreet:
    street_clean: str
    street_alt: str | None
    cls: str
    stem: str
    street_key: str
    street_alias_canonical: str | None = None


def classify_street(street_raw: str | None) -> ClassifiedStreet | None:
    """Run the full street-name cleanup pipeline (garbage-prefix strip, abbrev
    spacing fix, alt-name split, kvartal normalization, classification) and
    return the resulting ClassifiedStreet, or None if street_raw is empty or
    has no recognisable stem -- callers should treat None as "skip, can't
    classify" (rather miss than collide)."""
    if not street_raw or not street_raw.strip():
        return None
    street_clean, street_alt = split_alt_name(
        fix_abbrev_spacing(strip_garbage_prefix(street_raw)))
    street_clean = _space_numeral_let(street_clean)
    street_clean = _strip_ordinal_suffix(street_clean)
    street_clean = normalize_kvartal(street_clean)
    cls, stem = _classify(street_clean)
    if not stem:
        return None
    street_key = _key(street_clean)
    aliased_key = _STREET_KEY_ALIASES.get(street_key, street_key)
    street_alias_canonical = None
    if aliased_key != street_key:
        # The alias target's street_key is "CLASS:folded stem" -- rebuild a
        # Nominatim-friendly display form ("улица Гугеля") from it, since the
        # as-written spelling (e.g. "улица Якова Гугеля") doesn't geocode but
        # the aliased canonical name does.
        alias_cls, _, alias_stem = aliased_key.partition(":")
        street_alias_canonical = canonical_form(alias_cls, alias_stem.capitalize())
    return ClassifiedStreet(street_clean, street_alt, cls, stem, aliased_key,
                             street_alias_canonical)


def compute_building_key(street_key: str, house_raw: str | None) -> tuple[str | None, str | None]:
    """Normalize house_raw and combine with street_key into a building_key.
    Returns (building_key, house_norm), or (None, None) if house_raw doesn't
    yield a usable house number (caller may fall back to an @lat,lon key for
    already-geocoded sites with no house number)."""
    house_norm = norm_house(normalize_corpus_house(street_key, house_raw))
    if not house_norm:
        return None, None
    return f"{street_key}|{house_norm}", house_norm


def address_to_building_key(street_raw: str | None, house_raw: str | None) -> str | None:
    """classify_street + compute_building_key in one call, returning just the
    building_key (or None if either step fails -- no usable street class or
    no usable house number). Convenience for callers (db/load.py) that only
    need the key, not the intermediate ClassifiedStreet."""
    classified = classify_street(street_raw)
    if classified is None:
        return None
    building_key, _ = compute_building_key(classified.street_key, house_raw)
    return building_key
