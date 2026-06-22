#!/usr/bin/env python3
"""Stage 4a (geocoding prep): build a deduplicated building-address registry.

Every parsed source that carries a street + house-number address (damage
assessment, demolition decrees, ownerless-property decrees, the MinStroy
demolition register, plus the already-geocoded ЕИСЖС new-builds) is reduced
to one row per *building*: a canonical key, the cleaned occupation-era street
+ house, the prewar Ukrainian name where the toponym crosswalk
(data/toponyms.csv) has it, any cadastral numbers seen for that building, and
which source files reference it.

This is the dedup step ahead of geocoding (scripts/22): geocoding ~3,500 raw
rows one at a time would burn the Nominatim 1 req/s budget on duplicates --
most buildings appear in 2-4 source files. After this script, scripts/22
geocodes ~N unique buildings instead.

OUT OF SCOPE here: dnr_land_orders.jsonl (51 rows). Those are LAND PARCELS
described by territorial-boundary prose ("квартал между ул...", "микрорайон
«6-й участок»") with Russian-federal cadastral numbers (93:37:...), not
street+house addresses. They need a different geocoding path -- the Rosreestr
Public Cadastral Map API (pkk.rosreestr.ru), which returns parcel geometry by
cadastral number but is likely geoblocked like the court portals, so it
belongs on the VPS as a Tier-B follow-up, not here.

Output: data/parsed/address_registry.jsonl (one row per unique building).

Run locally, no network: python3 scripts/21_build_address_registry.py
"""
from __future__ import annotations

import json
import logging
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402
from mariupol_seizures.normalize.address import (  # noqa: E402
    classify_street,
    compute_building_key,
    norm_commas,
    strip_garbage_prefix,
)
from mariupol_seizures.normalize.toponym import (  # noqa: E402
    canonical_form,
    canonical_street_name,
    normalize_address,
)

log = logging.getLogger(__name__)

PARSED_DIR = config.PROJECT_ROOT / "data" / "parsed"


class Registry:
    def __init__(self) -> None:
        self.rows: dict[str, dict] = {}
        self.skipped: dict[str, int] = defaultdict(int)

    def add(self, *, source: str, street_raw: str | None, house_raw: str | None,
            district_key: str | None, cadastral_numbers: list[str] | None = None,
            already_geocoded: dict | None = None) -> None:
        if not street_raw or not street_raw.strip():
            self.skipped[f"{source}:no_street"] += 1
            return
        classified = classify_street(street_raw)
        if classified is None:
            self.skipped[f"{source}:unclassifiable_street"] += 1
            return
        street_clean, street_alt, cls, stem, street_key, street_alias_canonical = (
            classified.street_clean, classified.street_alt, classified.cls,
            classified.stem, classified.street_key, classified.street_alias_canonical)

        building_key, house_norm = compute_building_key(street_key, house_raw)
        if building_key is None:
            if already_geocoded:
                # No house number but we already have coordinates (under-construction
                # ЕИСЖС sites listed by street only) -- key on rounded coords so
                # multiple sites on the same street don't collide.
                building_key = (f"{street_key}|@"
                                f"{already_geocoded['lat']:.4f},{already_geocoded['lon']:.4f}")
            else:
                self.skipped[f"{source}:no_house_no"] += 1
                return

        row = self.rows.get(building_key)
        if row is None:
            top = normalize_address(street_clean)
            if not top["prewar_name"] and street_alias_canonical:
                # As-written spelling has no toponym match, but the aliased
                # canonical form does (e.g. "К.Либкнехта" -> "Карла
                # либкнехта" -> "вул. Митрополитська"). See
                # _STREET_KEY_ALIASES.
                alias_top = normalize_address(street_alias_canonical)
                if alias_top["prewar_name"]:
                    top = alias_top
            row = {
                "building_key": building_key,
                "street_class": cls,
                "street_occupation": street_clean,
                "street_canonical": canonical_street_name(street_clean),
                "street_alt": street_alt,
                "street_alt_canonical": canonical_form(cls, street_alt) if street_alt else None,
                "street_alias_canonical": street_alias_canonical,
                "house_no": house_norm,
                "district_key": district_key,
                "prewar_name": top["prewar_name"],
                "toponym_source": top["toponym_source"],
                "toponym_confidence": top["toponym_confidence"],
                "cadastral_numbers": [],
                "already_geocoded": already_geocoded,
                "source_refs": defaultdict(int),
            }
            self.rows[building_key] = row
        else:
            if district_key and not row["district_key"]:
                row["district_key"] = district_key
            elif (district_key and row["district_key"]
                  and row["district_key"] != district_key):
                row.setdefault("district_conflict", set()).add(district_key)
            if already_geocoded and not row["already_geocoded"]:
                row["already_geocoded"] = already_geocoded
            if not row["prewar_name"]:
                # A later source row for this building (post street_key
                # aliasing) may use a spelling that resolves a toponym match
                # the first-seen row's spelling didn't -- e.g. "К.Либкнехта"
                # (no match) seen before "Карла Либкнехта" (-> "вул.
                # Митрополитська") for the same house. Don't let row order
                # strip a known prewar name.
                top = normalize_address(street_clean)
                if not top["prewar_name"] and street_alias_canonical:
                    alias_top = normalize_address(street_alias_canonical)
                    if alias_top["prewar_name"]:
                        top = alias_top
                if top["prewar_name"]:
                    row["prewar_name"] = top["prewar_name"]
                    row["toponym_source"] = top["toponym_source"]
                    row["toponym_confidence"] = top["toponym_confidence"]

        row["source_refs"][source] += 1
        for c in (cadastral_numbers or []):
            if c and c not in row["cadastral_numbers"]:
                row["cadastral_numbers"].append(c)


def _query_variants(row: dict) -> list[str]:
    """Build ordered Nominatim query candidates: prewar UA name first (if
    known), then a source-annotated alt-name (if any -- e.g. "проспект Ленина
    (Мира)" carries its own "Мира" hint, which Nominatim resolves at house
    level even as the bare RU form "проспект Мира"), then the occupation-era
    RU name (canonical full-word street type if available, since Nominatim's
    free-text search does not resolve abbreviated prefixes like "пр-т."/"б-р"
    even when the full word does), then a _STREET_KEY_ALIASES canonical form
    (if this street_key was remapped -- e.g. "улица Якова Гугеля" ->
    "улица Гугеля" -- since the as-written spelling may not geocode but the
    aliased canonical name does), with house-number then street-only forms."""
    house = row["house_no"] or ""
    occ = row.get("street_canonical") or row["street_occupation"]
    alt = row.get("street_alt_canonical")
    alias = row.get("street_alias_canonical")
    variants = []
    if row["prewar_name"]:
        variants.append(f"{row['prewar_name']} {house}, Маріуполь, Україна".strip())
    if alt:
        variants.append(f"{alt} {house}, Мариуполь, Украина".strip())
    variants.append(f"{occ} {house}, Мариуполь, Украина".strip())
    if alias:
        variants.append(f"{alias} {house}, Мариуполь, Украина".strip())
    if house:
        if row["prewar_name"]:
            variants.append(f"{row['prewar_name']}, Маріуполь, Україна")
        if alt:
            variants.append(f"{alt}, Мариуполь, Украина")
        variants.append(f"{occ}, Мариуполь, Украина")
        if alias:
            variants.append(f"{alias}, Мариуполь, Украина")
    return variants


# --- per-source extractors ---------------------------------------------------

# Trailing whitespace/comma-separated token containing a digit, e.g. matches
# " 46" in "ул. 50 лет СССР, 46" or " 72" in "ул. Осипенко 72".
_TRAILING_HOUSE_RE = re.compile(r"^(.*?)[,\s]+(\S*\d\S*)\s*$")


# "N-Nа"-style combined building numbers in "ХХ квартал" addresses denote TWO
# separate, adjacent buildings sharing one damage-assessment row (e.g. "27
# квартал, 18-18а" = building "18" AND building "18а"), not a single building
# with a number range. Confirmed by the user via Yandex Maps for 27 квартал:
# 18 -> 47.127146,37.555840 and 18а -> 47.126956,37.555957 (distinct
# buildings ~25m apart); 4а -> 47.128715,37.554475 (see
# data/parsed/manual_geocode_overrides.jsonl). Split here so each building
# gets its own building_key/geocode instead of sharing one (previously
# low-confidence, neighbourhood-level) coordinate.
_PAIRED_KVARTAL_HOUSE_RE = re.compile(r"^(\d+)-(\1[а-яё])$", re.I)


def _split_paired_house(house_raw: str | None) -> list[str | None]:
    if not house_raw:
        return [house_raw]
    m = _PAIRED_KVARTAL_HOUSE_RE.match(house_raw.strip())
    if not m:
        return [house_raw]
    return [m.group(1), m.group(2)]


def _from_damage_assessment(reg: Registry) -> None:
    path = PARSED_DIR / "damage_assessment.jsonl"
    n = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        street = f"{d.get('street_type') or ''} {d.get('street_name') or ''}".strip()
        house = d.get("building_no")
        if not street:
            # "нежилое" (non-residential) rows leave street_type/street_name/
            # building_no null but carry a parseable address_raw, e.g.
            # "ул. 50 лет СССР, 46" or "ул. Осипенко 72" (no comma).
            addr = norm_commas(d.get("address_raw") or "").strip()
            m = _TRAILING_HOUSE_RE.match(addr)
            if m:
                street, house = m.group(1).strip().rstrip(","), m.group(2)
        for h in _split_paired_house(house):
            reg.add(source="damage_assessment", street_raw=street,
                    house_raw=h, district_key=d.get("district_key"))
        n += 1
    log.info("damage_assessment: %d rows", n)


def _from_demolition_decrees(reg: Registry) -> None:
    path = PARSED_DIR / "demolition_decrees.jsonl"
    n = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        addr = norm_commas(d.get("address_raw") or "")
        parts = [p.strip() for p in addr.split(",")]
        street = parts[0] if parts else None
        house = None
        for p in parts[1:]:
            m = re.search(r"(?:дом\s*№?\s*|д\.?\s*)(\S+)", p, re.I)
            if m:
                house = m.group(0)
                break
        reg.add(source="demolition_decrees", street_raw=street, house_raw=house,
                district_key=d.get("district_hint"))
        n += 1
    log.info("demolition_decrees: %d rows", n)


def _from_ownerless_decrees(reg: Registry) -> None:
    path = PARSED_DIR / "ownerless_decrees.jsonl"
    n = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        addr = strip_garbage_prefix(norm_commas(d.get("address_raw") or ""))
        parts = [p.strip() for p in addr.split(",")]
        street = parts[0] if parts else None
        house = None
        for p in parts[1:]:
            if re.match(r"д\.?\s*\d", p, re.I):
                house = p
                break
        cad = [d["cadastral_number"]] if d.get("cadastral_number") else []
        reg.add(source="ownerless_decrees", street_raw=street, house_raw=house,
                district_key=None, cadastral_numbers=cad)
        n += 1
    log.info("ownerless_decrees: %d rows", n)


def _from_minstroy(reg: Registry) -> None:
    path = PARSED_DIR / "minstroy_demolition_register.jsonl"
    if not path.exists():
        return
    n = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        if (d.get("address_city") or "").strip().lower() != "мариуполь":
            continue
        reg.add(source="minstroy_demolition_register",
                street_raw=d.get("address_street"), house_raw=d.get("address_building"),
                district_key=d.get("district_normalized"))
        n += 1
    log.info("minstroy_demolition_register (Mariupol rows): %d", n)


def _from_eisghs(reg: Registry) -> None:
    path = PARSED_DIR / "eisghs_mariupol_objects.jsonl"
    if not path.exists():
        return
    n = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        addr = d.get("address") or ""
        parts = [p.strip() for p in addr.split(",")]
        # Drop leading "г. Мариуполь" segment.
        parts = [p for p in parts if not re.match(r"^г\.?\s*мариуполь", p, re.I)]
        if not parts:
            reg.skipped["eisghs_mariupol_objects:no_street"] += 1
            continue
        street = parts[0]
        house = None
        for p in parts[1:]:
            m = re.search(r"(?:д\.?\s*|литера\s*)(\S+)", p, re.I)
            if m:
                house = m.group(0)
                break
        try:
            lat, lon = float(d["lat"]), float(d["lon"])
        except (KeyError, TypeError, ValueError):
            lat = lon = None
        already = ({"lat": lat, "lon": lon, "source": "eisghs_наш.дом.рф"}
                   if lat is not None else None)
        cad = (d.get("rpd_cadastral_match") or {}).get("cadastral_numbers") or []
        reg.add(source="eisghs_mariupol_objects", street_raw=street, house_raw=house,
                district_key="mariupol", cadastral_numbers=cad, already_geocoded=already)
        n += 1
    log.info("eisghs_mariupol_objects: %d rows", n)


def _from_ownerless_registry(reg: Registry) -> None:
    path = PARSED_DIR / "ownerless_registry.jsonl"
    if not path.exists():
        return
    n = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        reg.add(source="ownerless_registry", street_raw=d.get("street_raw"),
                house_raw=d.get("house_raw"), district_key=d.get("district_key"))
        n += 1
    log.info("ownerless_registry: %d rows", n)


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(message)s")
    reg = Registry()
    _from_damage_assessment(reg)
    _from_demolition_decrees(reg)
    _from_ownerless_decrees(reg)
    _from_minstroy(reg)
    _from_eisghs(reg)
    _from_ownerless_registry(reg)

    out_path = PARSED_DIR / "address_registry.jsonl"
    n_with_prewar = 0
    n_already_geo = 0
    with out_path.open("w", encoding="utf-8") as fh:
        for row in reg.rows.values():
            row = dict(row)
            row["source_refs"] = dict(row["source_refs"])
            row["n_sources"] = len(row["source_refs"])
            if row.get("district_conflict"):
                row["district_conflict"] = sorted(row["district_conflict"])
            if not row["cadastral_numbers"]:
                del row["cadastral_numbers"]
            row["geocode_query_variants"] = _query_variants(row)
            if row["prewar_name"]:
                n_with_prewar += 1
            if row["already_geocoded"]:
                n_already_geo += 1
            else:
                del row["already_geocoded"]
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    log.info("Wrote %d unique buildings -> %s", len(reg.rows), out_path)
    log.info("  with toponym (prewar) match: %d", n_with_prewar)
    log.info("  already geocoded (ЕИСЖС): %d", n_already_geo)
    log.info("  needing Nominatim lookup: %d", len(reg.rows) - n_already_geo)
    log.info("Skipped rows (no usable street/house):")
    for k, v in sorted(reg.skipped.items()):
        log.info("  %-45s %d", k, v)
    log.info("Note: dnr_land_orders.jsonl (51 parcel records, cadastral 93:37:...) "
             "is OUT OF SCOPE here -- queue for Rosreestr PKK cadastral lookup "
             "(Tier B, VPS) separately.")


if __name__ == "__main__":
    main()
