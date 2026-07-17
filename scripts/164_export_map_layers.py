"""Export GeoJSON layers for the public interactive map and QGIS project.

Local-DB-only (no crawl, no network) — reads the spine and writes:
  - data/exports/qgis/property_spine_context.geojson   (full popup detail, QGIS copy)
  - data/exports/qgis/demolition_sites.geojson          (demolition + demolish->rebuild)
  - docs/exhibits/assets/map/property_spine_context.geojson   (trimmed public copy)
  - docs/exhibits/assets/map/demolition_sites.geojson          (public copy)

Re-run whenever seizure_event/corroboration/property data changes; both QGIS
and public copies are regenerated from the same query so they never drift.

A property only makes the spine_context layer if it carries SOME evidentiary
basis (rd4u_category, a seizure_event, a corroboration row, or a court_case) —
bare geocoded address stubs with none of those (98 as of 2026-06) are excluded
rather than shown as clickable "seized" points with nothing behind them.

Public-map points are additionally restricted to the original Mariupol city
hromada boundary (data/boundaries/mariupol_hromada_boundary.geojson) — NOT the
extended okrug boundary scripts/23 now searches against. The satellite
villages (Сартана/Талаківка/Гнутове/Ломакине/Калинівка/Старий Крим) merged
into "городской округ Мариуполь" by the occupation's 06.04.2023 reform sit
outside this polygon on purpose: as of 2026-07 their geocoding is a mix of
0.5-confidence street-centroid matches and unresolved candidates (see
memory/satellite_villages_geocoding_2026-07-10.md), not yet building-verified,
so they are held off the public map rather than shown at street-level
precision next to building-verified city points. Re-run this script (no code
change needed) once village geocoding clears the same bar and the exhibit's
"not yet exhaustive" note (see docs/exhibits/interactive-map.html footer) can
be dropped.
"""

import json
import logging
import re
from pathlib import Path

import psycopg2
import psycopg2.extras

from mariupol_seizures.config import DATABASE_URL, PROJECT_ROOT

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

QGIS_DIR = PROJECT_ROOT / "data" / "exports" / "qgis"
PUBLIC_DIR = PROJECT_ROOT / "docs" / "exhibits" / "assets" / "map"

STAGE_LABELS = {
    "demolition": "Demolition order",
    "ownerless_designation": "Designated “ownerless” (decree)",
    "court_transfer": "Court-ordered municipal transfer",
    "registry_inclusion": "Included in ownerless-property registry",
    "reallocation": "Land reallocated to developer",
    "appeal": "Appeal",
    "court_petition": "Court petition filed",
    "utility_cutoff": "Utility cut-off",
    "notice": "Notice posted",
    "inspection": "Inspection",
    "resale": "Resale",
}

STAGE_PRIORITY = {
    "demolition": 1,
    "ownerless_designation": 2,
    "court_transfer": 3,
    "reallocation": 4,
    "registry_inclusion": 5,
}

CORROB_LABELS = {
    "ownerless_disposition": "Ownerless-registry disposition (Telegram-corpus cross-check)",
    "mirror_source": "Federal damage/reconstruction tracker",
    "unosat_damage": "UNOSAT satellite damage assessment",
    "displacement_claim": "Housing-distribution / displacement list",
    "lifecycle_media": "Resident-posted media (demolition/clearance lifecycle)",
    "ijss_ownerless_list": "ЕИСЖС new-build crosswalk",
    "developer_new_build_same_block": "Developer new-build, same block",
    "damage_assessment_corpse_note": "Damage assessment record",
    "market_listing": "Resale listing (unconfirmed unit match — weakest tier)",
}

RD4U_LABELS = {
    "A3.1": "destruction of residential property",
    "A3.2": "destruction of non-residential property",
    "A3.3": "loss of housing/residence",
    "A3.6": "loss of access/control under occupation",
}


def rd4u_label(cat):
    """'A3.1,A3.6' -> 'A3.1 destruction of residential property; A3.6 loss
    of access/control under occupation' -- the bare codes mean nothing
    without RD4U context, so always show the plain-English gloss with them."""
    if not cat:
        return None
    codes = [c.strip() for c in cat.split(",") if c.strip()]
    return "; ".join(f"{c} {RD4U_LABELS.get(c, '')}".strip() for c in codes)


CORROB_PRIORITY = {
    "ownerless_disposition": 1,
    "mirror_source": 2,
    "unosat_damage": 3,
    "displacement_claim": 4,
    "lifecycle_media": 5,
    "ijss_ownerless_list": 6,
    "developer_new_build_same_block": 6,
    "damage_assessment_corpse_note": 6,
    "market_listing": 9,
}

# %s placeholder = boundary GeoJSON (city hromada polygon only, not the
# extended okrug boundary) — public-map layers are scoped to it; see module
# docstring. ST_Contains, not ST_Within, since we're testing points, not geoms.
BOUNDARY_FILTER_SQL = "and ST_Contains(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), p.geom)"

PROPERTY_SQL = """
select p.id, p.prewar_address, p.occupation_address, p.rd4u_category,
       st_x(p.geom) as lon, st_y(p.geom) as lat
from property p
where p.geom is not null
{boundary}
"""

SEIZURE_EVENT_SQL = """
select property_id, stage, event_date, detail, confidence from seizure_event
where stage in ('demolition','ownerless_designation','court_transfer','reallocation','registry_inclusion')
"""

CORROBORATION_SQL = """
select property_id, kind, detail, captured_at, confidence from corroboration
where property_id is not null and kind is not null
"""

# This project's standing rule (see address_normalization_pitfalls memory /
# CLAUDE.md): a fuzzy match needs >=0.8 confidence to be "claim-grade". Below
# that, the record exists but hasn't cleared the bar for restitution/criminal
# use — surfaced on the map as "pending verification" rather than silently
# shown the same as a verified record.
CLAIM_GRADE_THRESHOLD = 0.8

COURT_CASE_PROPERTY_SQL = "select distinct property_id from court_case where property_id is not null"

DEMOLITION_SQL = """
select
    p.id,
    p.prewar_address, p.occupation_address,
    st_x(p.geom) as lon, st_y(p.geom) as lat,
    d.event_date as demolition_date, d.detail as demolition_detail, d.confidence as demolition_confidence,
    r.event_date as reallocation_date, r.detail as reallocation_detail, r.confidence as reallocation_confidence
from property p
join seizure_event d on d.property_id = p.id and d.stage = 'demolition'
left join lateral (
    select event_date, detail, confidence from seizure_event
    where property_id = p.id and stage = 'reallocation'
    order by event_date asc nulls last limit 1
) r on true
where p.geom is not null
{boundary}
"""

TOPONYM_SQL = "select prewar_name, occupation_name from toponym where kind = 'rename'"

# Non-residential ownerless-designation events (scripts/290/292): commercial +
# industrial "признаки бесхозности" objects. One seizure_event per object, many
# per building (e.g. four shops at one address) -> aggregated per building below.
NONRES_OWNERLESS_SQL = """
select
    p.id, p.prewar_address, p.occupation_address, p.property_kind,
    st_x(p.geom) as lon, st_y(p.geom) as lat,
    e.detail as detail
from property p
join seizure_event e
    on e.property_id = p.id
   and e.detail->>'source' = 'nonresidential_ownerless'
where p.geom is not null
{boundary}
"""

# Non-residential demolition list («Снос.pdf», scripts/291/292): shopping
# centres, hotels, warehouses, a bakery, Дом связи, Ледо, ДОСААФ.
NONRES_DEMOLITION_SQL = """
select
    p.id, p.prewar_address, p.occupation_address, p.property_kind,
    st_x(p.geom) as lon, st_y(p.geom) as lat,
    e.detail as detail
from property p
join seizure_event e
    on e.property_id = p.id
   and e.detail->>'source' = 'nonresidential_demolition'
where p.geom is not null
{boundary}
"""

# ---------------------------------------------------------------------------
# Transliteration — always Ukrainian-standard (this project treats the
# Ukrainian name as canonical; the occupation/Russian spelling is evidence of
# the occupier's act, never the reference form — same rule as CLAUDE.md's
# "occupation records are evidence of the act, not valid title"). г/и/ь read
# differently in Russian than Ukrainian, so transliterating a Russian-spelled
# string with this table only works once it's been run through
# ukrainianize_for_latin() below. Good-enough for a public exhibit, not an
# academic transliteration standard.
# ---------------------------------------------------------------------------
UA_TABLE = {
    "а": "a", "б": "b", "в": "v", "г": "h", "ґ": "g", "д": "d", "е": "e",
    "є": "ie", "ж": "zh", "з": "z", "и": "y", "і": "i", "ї": "i", "й": "i",
    "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch",
    "ш": "sh", "щ": "shch", "ь": "'", "ю": "iu", "я": "ia",
    # Russian-only letters with no Ukrainian equivalent — some raw addresses
    # mix Russian spelling (district names, etc.) even on the Ukrainian side;
    # fall back to a sane rendering rather than leaving Cyrillic unconverted.
    "ы": "y", "э": "e", "ъ": "", "ё": "e",
}


def transliterate(text):
    if not text:
        return None
    out = []
    for ch in text:
        lower = ch.lower()
        if lower in UA_TABLE:
            t = UA_TABLE[lower]
            if ch.isupper() and t:
                t = t[0].upper() + t[1:]
            out.append(t)
        else:
            out.append(ch)
    return "".join(out)


# Drop a leading district/city qualifier ("р-н Жовтневый, ", "г. Мариуполь, ")
# so the street-type canon below (which only matches at the start of the
# string) reaches the actual street word instead of stopping at the qualifier.
LEADING_QUALIFIER_RE = re.compile(
    r"^\s*(г\.|город|р-н|район|пос(?:\.|елок)?(?:\s+городского\s+типа)?)\s+\S+,\s*",
    re.IGNORECASE,
)

# Canonicalize the street-type word/abbreviation to one fixed Ukrainian form
# before transliterating, so the Latin rendering doesn't vary between "просп."
# and "проспект" depending on which source happened to capture this address.
STREET_TYPE_CANON = [
    (re.compile(r"^(просп\.?|проспект|пр-кт|пр-т|пр\.)\s+", re.IGNORECASE), "просп. "),
    (re.compile(r"^(вул\.?|вулиця|ул\.?|улица)\s+", re.IGNORECASE), "вул. "),
    (re.compile(r"^(бул\.?|бульвар|б-р)\s+", re.IGNORECASE), "бул. "),
    (re.compile(r"^(пров\.?|провулок|пер\.?|переулок)\s+", re.IGNORECASE), "пер. "),
    (re.compile(r"^(пл\.?|площа|площадь)\s+", re.IGNORECASE), "пл. "),
]

STREET_PREFIX_RE = re.compile(
    r"^\s*(просп\.?|проспект|вул\.?|вулиця|ул\.?|улица|бул\.?|бульвар|"
    r"пер\.?|переулок|пров\.?|провулок|пл\.?|площа|площадь|б-р|пр-т|пр\.)\s*",
    re.IGNORECASE,
)

# Common Russian adjectival endings (-ский/-цкий surname/place-name suffixes)
# approximated to their Ukrainian counterparts (-ський/-цький, with the soft
# sign Russian drops) so a Russian-only-sourced address still Latinizes as
# Ukrainian rather than as transliterated Russian. Best-effort: covers the
# regular pattern, not irregular declensions.
SURNAME_ADJ_RU_TO_UA = [
    (re.compile(r"цкого\b", re.IGNORECASE), "цького"),
    (re.compile(r"ского\b", re.IGNORECASE), "ського"),
    (re.compile(r"цкой\b", re.IGNORECASE), "цької"),
    (re.compile(r"ской\b", re.IGNORECASE), "ської"),
    (re.compile(r"цкая\b", re.IGNORECASE), "цька"),
    (re.compile(r"ская\b", re.IGNORECASE), "ська"),
    (re.compile(r"цкое\b", re.IGNORECASE), "цьке"),
    (re.compile(r"ское\b", re.IGNORECASE), "ське"),
    (re.compile(r"цкий\b", re.IGNORECASE), "цький"),
    (re.compile(r"ский\b", re.IGNORECASE), "ський"),
]

# Common given-name/root spelling differences between Russian and Ukrainian
# that aren't captured by a suffix rule (e.g. Владимир vs Володимир) — applied
# to the stem before the adjectival-ending rules above. Best-effort, not
# exhaustive: covers names actually seen in this project's street data.
ROOT_RU_TO_UA = [
    (re.compile(r"владимир", re.IGNORECASE), "володимир"),
    # Никола(й)/Mykola: the Russian "-аев-" infix in this name's adjectival
    # forms doesn't correspond to a regular Ukrainian suffix substitution
    # (Russian Николаевская / Ukrainian Миколаївська), so the full adjective
    # is overridden per case ending rather than derived from a general rule.
    (re.compile(r"николаевская\b", re.IGNORECASE), "миколаївська"),
    (re.compile(r"николаевской\b", re.IGNORECASE), "миколаївської"),
    (re.compile(r"николаевский\b", re.IGNORECASE), "миколаївський"),
    (re.compile(r"николаевского\b", re.IGNORECASE), "миколаївського"),
    (re.compile(r"николаевское\b", re.IGNORECASE), "миколаївське"),
    # Строитель/builder: the Ukrainian word is "будівельник", an entirely
    # different root from Russian "строитель" — not a suffix variation, so
    # transliterating the Russian root directly (-> "Stroytelei") is wrong
    # regardless of which adjectival ending is attached. Cover the case
    # forms seen on the spine plus the standard adjective endings.
    (re.compile(r"строителей\b", re.IGNORECASE), "будівельників"),
    (re.compile(r"строители\b", re.IGNORECASE), "будівельники"),
    (re.compile(r"строительный\b", re.IGNORECASE), "будівельний"),
    (re.compile(r"строительная\b", re.IGNORECASE), "будівельна"),
    (re.compile(r"строительное\b", re.IGNORECASE), "будівельне"),
    (re.compile(r"строительного\b", re.IGNORECASE), "будівельного"),
    (re.compile(r"строительной\b", re.IGNORECASE), "будівельної"),
    (re.compile(r"строительные\b", re.IGNORECASE), "будівельні"),
    (re.compile(r"строительных\b", re.IGNORECASE), "будівельних"),
]


def ukrainianize_for_latin(text):
    """Best-effort normalization to Ukrainian orthography before transliterating."""
    if not text:
        return text
    qualifier = ""
    m = LEADING_QUALIFIER_RE.match(text)
    if m:
        qualifier, text = m.group(0), text[m.end():]
    for pat, repl in STREET_TYPE_CANON:
        if pat.match(text):
            text = pat.sub(repl, text, count=1)
            break
    def case_preserving_sub(pat, repl, text):
        def _sub(m):
            return repl[0].upper() + repl[1:] if m.group(0)[0].isupper() else repl
        return pat.sub(_sub, text)

    for pat, repl in ROOT_RU_TO_UA:
        text = case_preserving_sub(pat, repl, text)
    for pat, repl in SURNAME_ADJ_RU_TO_UA:
        text = case_preserving_sub(pat, repl, text)
    return qualifier + text


def normalize_street(name):
    if not name:
        return None
    core = STREET_PREFIX_RE.sub("", name).strip().lower().rstrip(".,")
    return core or None


def build_toponym_index(rows):
    """Map normalized street-core (either direction) -> (prewar_name, occupation_name).

    Every 'rename' row in this table is, on inspection, the occupation
    administration reverting a 2016 decommunization-law rename back to its
    pre-2016 Soviet/Communist-figure name (e.g. "просп. Миру" — the 2016
    replacement for Soviet-era "просп. Леніна" — reverted by the occupier
    back to Lenin). So prewar_name is treated as canonical pre-invasion
    Ukrainian (post-decommunization); occupation_name is the Soviet-era name
    being restored, not a fresh occupation invention.
    """
    index = {}
    for row in rows:
        pair = (row["prewar_name"], row["occupation_name"])
        pre_core, occ_core = normalize_street(row["prewar_name"]), normalize_street(row["occupation_name"])
        if pre_core:
            index[pre_core] = pair
        if occ_core:
            index[occ_core] = pair
    return index


def rename_lookup(address, toponym_index):
    """Find the toponym pair for `address`'s street, and which side it is."""
    if not address:
        return None
    street = address.rsplit(",", 1)[0] if "," in address else address
    core = normalize_street(street)
    if not core or core not in toponym_index:
        return None
    prewar_name, occupation_name = toponym_index[core]
    is_prewar_side = core == normalize_street(prewar_name)
    return {
        "prewar_name": prewar_name,
        "occupation_name": occupation_name,
        "matched_side": "prewar" if is_prewar_side else "occupation",
    }


# English glosses for the institutions/document types that show up in
# `detail` fields — the public popup should read in English even though the
# underlying decree is a Russian/occupation-administration instrument; the
# original-language citation is still surfaced in `event_basis`/`corrob_basis`
# output in parentheses so the source document remains identifiable.
AUTHORITY_LABELS_EN = {
    "ГКО ДНР": "State Defense Committee of the DNR (GKO DNR)",
    "Администрация г. Мариуполя": "Mariupol occupation administration",
}


def event_basis(stage, detail):
    detail = detail or {}
    if stage == "demolition":
        authority = detail.get("order_authority")
        authority_en = AUTHORITY_LABELS_EN.get(authority, authority)
        number = detail.get("order_number")
        date = detail.get("order_date")
        ref_raw = detail.get("order_reference_raw")
        if authority_en or number or date:
            bits = ["Demolition order"]
            if authority_en:
                bits.append(f"by {authority_en}")
            if number:
                bits.append(f"No. {number}")
            if date:
                bits.append(f"dated {date}")
            return " ".join(bits)
        return ref_raw or "Demolition order on file (details not extracted)"
    if stage == "ownerless_designation":
        num = detail.get("decree_number")
        reg = detail.get("rosreestr_reg_date")
        bits = [f"Designated “ownerless” by decree No. {num}" if num else "Designated “ownerless”"]
        if reg:
            bits.append(f"entered in Rosreestr {reg}")
        return "; ".join(bits)
    if stage == "registry_inclusion":
        marker = detail.get("recognition_marker")
        return f"Included in the ownerless-property registry (basis: {marker})" if marker else "Included in the ownerless-property registry"
    if stage == "reallocation":
        dev = detail.get("developer")
        rpd = detail.get("rpd_num")
        bits = [b for b in [f"Developer: {dev}" if dev else None, f"Project declaration RPD {rpd}" if rpd else None] if b]
        return "; ".join(bits) if bits else "Land parcel reallocated to a developer"
    if stage == "court_transfer":
        return "Transferred to municipal ownership by ruling of an occupation court"
    return None


def corrob_basis(kind, detail):
    detail = detail or {}
    if kind == "ownerless_disposition":
        snap = detail.get("snapshot_date", "")
        cls = detail.get("classification", "")
        return f"Registry snapshot {snap}: {cls}".strip(": ") if (snap or cls) else None
    if kind == "mirror_source":
        pct = detail.get("destruction_pct")
        contractor = detail.get("contractor")
        bits = [f"Damage {pct}%" if pct is not None else None, f"contractor {contractor}" if contractor else None]
        bits = [b for b in bits if b]
        return "; ".join(bits) if bits else "Recorded in the federal reconstruction/damage tracker"
    if kind == "unosat_damage":
        return f"{detail.get('damage_class', '')} ({detail.get('sensor_date', '')}, {detail.get('sensor', '')})".strip()
    if kind == "displacement_claim":
        n = detail.get("households_displaced")
        return f"{n} households on the housing-distribution list" if n else "On a housing-distribution list"
    if kind == "lifecycle_media":
        return f"Resident media, stage: {detail.get('stage', '')} ({'–'.join(detail.get('date_range', []) or [])})"
    if kind == "market_listing":
        return "Resale listing posted — building-level match only, not a confirmed seizure record"
    return None


def best_event(rows):
    if not rows:
        return None
    # Coerce event_date to a comparable ISO string (date objects and the
    # missing-date sentinel must not be compared directly — a NULL date on one
    # event and a real date on another, same stage, otherwise raises
    # "'<' not supported between 'date' and 'str'").
    def _key(r):
        d = r["event_date"]
        d = d.isoformat() if hasattr(d, "isoformat") else (d or "9999-99-99")
        return (STAGE_PRIORITY.get(r["stage"], 9), d)
    return min(rows, key=_key)


def best_corrob(rows):
    if not rows:
        return None
    return min(rows, key=lambda r: (CORROB_PRIORITY.get(r["kind"], 9), r["captured_at"] or ""))


# Rough UNOSAT/REACH damage-class bands, used only to sanity-check the
# occupier's own federal tracker percentage against an independent satellite
# read -- not a precise equivalence, since the two scales aren't the same
# instrument. Each band lists the damage_class values considered "consistent"
# with that pct range; anything else is flagged as a disagreement worth a
# second look (e.g. the tracker claiming 100% destruction where UNOSAT only
# sees "Moderate Damage" -- a discrepancy this project has already observed
# in the data and that matters for assessing whether "ownerless" damage
# claims are overstated to justify seizure).
DAMAGE_CLASS_BANDS = [
    (0, 25, {"No Visible Damage", "Possible Damage"}),
    (25, 50, {"Possible Damage", "Moderate Damage"}),
    (50, 75, {"Moderate Damage", "Severe Damage"}),
    (75, 100.01, {"Severe Damage", "Destroyed"}),
]


def expected_damage_classes(pct):
    for lo, hi, classes in DAMAGE_CLASS_BANDS:
        if lo <= pct < hi:
            return classes
    return None


def damage_corrob(corrobs):
    """Surface the federal-tracker destruction_pct and the independent UNOSAT
    damage_class side by side when either (or both) exist for a property,
    flagging agreement/disagreement when both are present. This runs
    independently of best_corrob's single-row pick -- the two sources are
    each other's corroboration, not competitors for "best" evidence."""
    mirror = next((c for c in corrobs if c["kind"] == "mirror_source" and (c["detail"] or {}).get("destruction_pct") is not None), None)
    unosat = next((c for c in corrobs if c["kind"] == "unosat_damage" and (c["detail"] or {}).get("damage_class")), None)
    if not mirror and not unosat:
        return None

    pct = float(mirror["detail"]["destruction_pct"]) if mirror else None
    cls = unosat["detail"].get("damage_class") if unosat else None

    if pct is not None and cls:
        expected = expected_damage_classes(pct)
        agree = bool(expected and cls in expected)
        if agree:
            note = f"Corroborated: federal tracker reports {pct:.0f}% destruction; UNOSAT satellite assessment independently rates this “{cls}” — consistent."
        else:
            note = f"Discrepancy: federal tracker reports {pct:.0f}% destruction, but UNOSAT satellite assessment independently rates this “{cls}” — sources disagree."
    elif pct is not None:
        agree = None
        note = f"Federal tracker reports {pct:.0f}% destruction (no independent UNOSAT assessment on file for this property)."
    else:
        agree = None
        note = f"UNOSAT satellite assessment rates this “{cls}” (no federal-tracker damage percentage on file for this property)."

    return {"pct": pct, "class": cls, "agree": agree, "note": note}


def address_block(prewar, occupation, toponym_index):
    ua, ru = prewar, occupation
    match = (rename_lookup(ua, toponym_index) if ua else None) or (rename_lookup(ru, toponym_index) if ru else None)

    ua_documented = None  # post-2016 Ukrainian name recovered from the toponym record, not property's own field
    soviet_name = None
    note = None
    if match:
        soviet_name = match["occupation_name"]
        if match["matched_side"] == "occupation" and not ua:
            # We only have the occupation/Soviet-reverted spelling on file; the
            # toponym table tells us the canonical post-2016 Ukrainian name —
            # show it, clearly labeled as sourced from the toponym record, not
            # from this property's own captured address field.
            ua_documented = match["prewar_name"]
            note = (
                f"Pre-invasion Ukrainian name (per toponym record, post-2016 decommunization): "
                f"“{match['prewar_name']}” — this property is documented here only via its "
                f"occupation-era reverted name."
            )
        else:
            note = (
                f"Occupation reverted this street to its pre-2016 Soviet-era name: “{soviet_name}”."
            )

    # Prefer the property's own captured Ukrainian address; fall back to the
    # toponym-documented canonical name; only then fall back to a heuristic
    # Ukrainianization of the Russian/occupation spelling.
    if ua:
        latin_source = ua
    elif ua_documented:
        latin_source = ua_documented
    else:
        latin_source = ru

    return {
        "ua": ua,
        "ru": ru,
        "ua_documented": ua_documented,
        "soviet_name": soviet_name,
        "latin": transliterate(ukrainianize_for_latin(latin_source)),
        "renamed_note": note,
    }


def verification_label(confidence):
    """'Verified'/'pending verification' wording per this project's >=0.8
    claim-grade threshold. None means no fuzzy-match confidence was scored
    for this record at all (treated as not yet verified, not as verified)."""
    if confidence is None:
        return "unscored", "Confidence not yet scored for this record."
    confidence = float(confidence)
    if confidence >= CLAIM_GRADE_THRESHOLD:
        return "verified", None
    return "pending_verification", f"Below this project's claim-grade confidence threshold (confidence {confidence:.2f} < {CLAIM_GRADE_THRESHOLD}) — pending further verification."


def build_spine_features(rows, events_by_prop, corrob_by_prop, court_props, toponym_index):
    full, public = [], []
    skipped = 0
    for row in rows:
        pid = row["id"]
        events = events_by_prop.get(pid, [])
        corrobs = corrob_by_prop.get(pid, [])
        has_basis = bool(row["rd4u_category"]) or bool(events) or bool(corrobs) or pid in court_props
        if not has_basis:
            skipped += 1
            continue

        addr = address_block(row["prewar_address"], row["occupation_address"], toponym_index)
        ev = best_event(events)
        co = None if ev else best_corrob(corrobs)

        if ev:
            stage_label, date, basis, evidence_tier, confidence = (
                STAGE_LABELS.get(ev["stage"]),
                ev["event_date"].isoformat() if ev["event_date"] else None,
                event_basis(ev["stage"], ev["detail"]),
                "lifecycle_event",
                ev.get("confidence"),
            )
        elif co:
            stage_label, date, basis, evidence_tier, confidence = (
                CORROB_LABELS.get(co["kind"], co["kind"]),
                co["captured_at"].date().isoformat() if co["captured_at"] else None,
                corrob_basis(co["kind"], co["detail"]),
                "corroboration",
                co.get("confidence"),
            )
        else:
            stage_label, date, basis, evidence_tier, confidence = None, None, None, "category_only", None

        verif_status, verif_note = verification_label(confidence) if evidence_tier != "category_only" else (None, None)
        confidence_val = float(confidence) if confidence is not None else None

        cat_label = rd4u_label(row["rd4u_category"])
        dmg = damage_corrob(corrobs)

        full_props = {
            "id": pid, "addr_ua": addr["ua"], "addr_ua_documented": addr["ua_documented"],
            "addr_ru": addr["ru"], "addr_soviet": addr["soviet_name"], "addr_latin": addr["latin"],
            "renamed_note": addr["renamed_note"], "cat": row["rd4u_category"], "cat_label": cat_label,
            "evidence_tier": evidence_tier, "stage_label": stage_label, "date": date, "basis": basis,
            "confidence": confidence_val, "verification_status": verif_status, "verification_note": verif_note,
            "damage_pct": dmg["pct"] if dmg else None, "damage_class": dmg["class"] if dmg else None,
            "damage_agree": dmg["agree"] if dmg else None, "damage_note": dmg["note"] if dmg else None,
        }
        public_props = {
            "ua": addr["ua"], "ua_doc": addr["ua_documented"], "ru": addr["ru"],
            "soviet": addr["soviet_name"], "latin": addr["latin"], "renamed": addr["renamed_note"],
            "cat": row["rd4u_category"], "cat_label": cat_label,
            "tier": evidence_tier, "stage": stage_label, "date": date, "basis": basis,
            "confidence": confidence_val, "verif": verif_status, "verif_note": verif_note,
            "dmg_pct": dmg["pct"] if dmg else None, "dmg_class": dmg["class"] if dmg else None,
            "dmg_agree": dmg["agree"] if dmg else None, "dmg_note": dmg["note"] if dmg else None,
        }
        geom = {"type": "Point", "coordinates": [round(row["lon"], 5), round(row["lat"], 5)]}
        full.append({"type": "Feature", "geometry": geom, "properties": full_props})
        public.append({"type": "Feature", "geometry": geom, "properties": public_props})
    log.info("spine: %d kept, %d skipped (no rd4u_category/seizure_event/corroboration/court_case)", len(full), skipped)
    return full, public


# Manually curated demolished-property -> eisghs_id links, for the cases where
# the new build's own address doesn't resolve to the same property_id as its
# demolished predecessor (letter-suffix renaming, brand-name/литера addressing,
# a separate fragmented property row, etc.) -- so the property_id-level SQL
# join in DEMOLITION_SQL can't catch the link automatically. Kept as a Python
# constant, not a data/ file, since data/ is fully gitignored (raw evidence
# store + PII) and this table needs to ship with the repo for scripts/164 to
# be reproducible -- same convention as load.py's _ALIAS_REVIEWED.
#
# Add an entry ONLY when a case study states the pair explicitly -- never from
# proximity/address-similarity alone. death_sites_new_construction.md's
# Металлургов 96/98 finding is the cautionary example: a new-build complex on
# the SAME street turned out to be built on a completely different, non-
# adjacent set of demolished addresses ~50-130m away, not the ones an address-
# proximity guess would have picked. Before adding a pair, check the DB first:
# Case 7's five пр. Строителей 74-88 buildings looked like they'd need an
# entry here too, but turned out to already be auto-matched (their eisghs
# reallocation events land on the same property_id as their demolition
# events) -- only add a pair once you've confirmed the automatic join misses it.
DEMOLITION_NEWBUILD_CROSSWALK = [
    {
        "property_id": 4638,
        "demolished_building_id": "AVENUE:строителей|70",
        "eisghs_id": 65280,
        "note": "Case 1 — Пр. Строителей 70 → «Резиденция II», 70Б (СЗ-1 ПОРФИР). "
                "eisghs's reallocation event lands on a third, separate property_id "
                "(20577) rather than 4638 (the demolished '70' row) or 28450 (a "
                "stray '70б' row) — exactly the fragmentation this crosswalk exists "
                "to patch.",
        "source": "docs/case_studies/death_sites_new_construction.md#case-1",
    },
    # 2026-07-14 letter-suffix sweep: tested the hypothesis that some of the
    # "unmatched" newbuild layer differs from a demolished address by a single
    # trailing letter (X -> XБ/Xа/etc, the same pattern as Строителей 70/70Б).
    # 10 candidates found; only these 3 held up against BOTH an independently
    # derived signal (scripts/18's own "address_laundering" flag — INN matched
    # a confirmed land order, but the object's address didn't fuzzy-match any
    # demolished building) AND a plausible date sequence (demolition precedes
    # new-build publication/commissioning). The other 7 were investigated and
    # deliberately NOT added — see the review note below.
    {
        "property_id": 5774,
        "demolished_building_id": "BOULEVARD:богдана хмельницкого|8",
        "eisghs_id": 59762,
        "note": "Б-р Богдана Хмельницкого 8 → «Жилой дом на Хмельницкого 8А» (СЗ-1 "
                "ПОРФИР). Demolished under ГКО №56 (29.09.2022); new build "
                "published 2024-05-25, commissioned 2024-11-08 — plausible "
                "sequence. eisghs flags this object 'address_laundering' on its "
                "own (INN matched a land order, address didn't fuzzy-match the "
                "demolition register). Land decree №125 (2026-04-24), shared "
                "with Нахимова 134а below — decree_address is a block-level "
                "description ('квартал между ул…'), consistent with one decree "
                "covering multiple buildings in the same block, not a parsing "
                "artifact (contrast with the Жукова/Киевская case rejected below).",
        "source": "2026-07-14 letter-suffix sweep",
    },
    {
        "property_id": 5839,
        "demolished_building_id": "AVENUE:нахимова|134",
        "eisghs_id": 61646,
        "note": "Пр. Нахимова 134 → «Жилой дом на Нахимова 134а» (СЗ-1 ПОРФИР). "
                "Demolished under ГКО №56 (29.09.2022); new build published "
                "2024-08-23, commissioned 2024-12-20. Same 'address_laundering' "
                "flag and same shared block decree №125 as Хмельницкого 8А above.",
        "source": "2026-07-14 letter-suffix sweep",
    },
    {
        "property_id": 5139,
        "demolished_building_id": "STREET:киевская|59",
        "eisghs_id": 64116,
        "note": "Ул. Киевская 59 → ЖК «Олимпийский», 59Б (СЗ РСК). Demolished under "
                "ГКО №39 (16.09.2022); new build published 2025-01-10, "
                "commissioned 2026-06-05. 'address_laundering' flag, and land "
                "decree №339 (2024-09-02) whose OWN captured decree_address text "
                "reads 'Орджоникидзевский район, улица Киевская, 59 Б' — the "
                "decree explicitly names this address, the strongest evidentiary "
                "basis of the three added here.",
        "source": "2026-07-14 letter-suffix sweep",
    },
    # NOT added, investigated and rejected:
    #   - Пр. Маршала Жукова 90 -> eisghs 66286 (90Б, СЗ РСК): carries the same
    #     decree number/date/decree_address text as Киевская 59Б above ("улица
    #     Киевская, 59 Б") despite being a different street — almost certainly
    #     an artifact of scripts/18's INN-only matching reusing one developer's
    #     single captured decree across every object under that INN, not a real
    #     shared land grant. Needs the developer's actual decree history checked
    #     by hand before this pair is added.
    #   - Пр. Ленина 77 -> eisghs 60781 (77Б, СЗ НР-ДЕВЕЛОПМЕНТ, "Дом с часами
    #     Корпус 2"): does NOT carry the 'address_laundering' flag -- flagged
    #     'no_land_order_for_inn+single_source_inn_only' instead, meaning no
    #     land order was found for this developer's INN at all. A materially
    #     weaker evidentiary tier than the three added above.
    #   - Б-р Богдана Хмельницкого 33 -> eisghs 62717 (33б, СЗ ТЕМП-80): the
    #     demolished property (id 4333) already has ITS OWN reallocation event
    #     from a different source/developer (mar_s_group_proektnaya_deklaratsiya)
    #     and is already correctly shown as demolished_rebuilt_same. Adding a
    #     second crosswalk link to a DIFFERENT eisghs object here would put two
    #     competing "replacement" claims on the same demolished address --
    #     needs a human to determine which (if either, or both, on a subdivided
    #     plot) is correct before this is resolved either way.

    # 2026-07-15: construction-progress-photo OCR sweep (scripts/314/315).
    # СЗ-1 ПОРФИР burns a red address+date caption into every monthly photo —
    # confirmed to be Porfir-specific, no other developer does this. Cross-
    # referenced each OCR'd house number against (a) the nearest demolished
    # property by coordinate and (b) whether that property already had a
    # reallocation event from a different source (several did — see the
    # "already resolved elsewhere" objects skipped below, not added here).
    {
        "property_id": 4321,
        "demolished_building_id": "BOULEVARD:богдана хмельницкого|12",
        "eisghs_id": 66544,
        "note": "Б-р Богдана Хмельницкого 12 → «Дом со вкусом АУРА 1», 12А "
                "(СЗ-1 ПОРФИР). OCR of the developer's own construction-progress "
                "captions read 'БУЛЬВАР БОГДАНА ХМЕЛЬНИЦКОГО 12А' cleanly on "
                "15/17 monthly photos (Jul 2025 – Feb 2026); object's own "
                "geocoded point sits 9m from this property.",
        "source": "2026-07-15 construction-photo OCR sweep",
    },
    {
        "property_id": 4323,
        "demolished_building_id": "BOULEVARD:богдана хмельницкого|16",
        "eisghs_id": 66593,
        "note": "Ул. Богдана Хмельницкого 16 → 16А (СЗ-1 ПОРФИР). OCR read "
                "'БУЛЬВАР БОГДАНА ХМЕЛЬНИЦКОГО 16А' cleanly on 11/16 monthly "
                "photos; object's own geocoded point sits 17m from this property.",
        "source": "2026-07-15 construction-photo OCR sweep",
    },
    {
        "property_id": 4322,
        "demolished_building_id": "BOULEVARD:богдана хмельницкого|14",
        "eisghs_id": 66594,
        "note": "Б-р Богдана Хмельницкого 14 → 14А (СЗ-1 ПОРФИР). OCR was initially "
                "split — 4 clean Jul-Aug 2025 photos read plain '...ХМЕЛЬНИЦКОГО 14' "
                "(no suffix), 6 clean Sep 2025+ photos read '...14А', suggesting a "
                "provisional caption before the final address was assigned. "
                "Confirmed as 14А on the ground 2026-07-15: a March 2026 "
                "construction photo (well after the caption stabilized) reads "
                "'БУЛЬВАР БОГДАНА ХМЕЛЬНИЦКОГО 12А' for the neighboring 12А "
                "object at the same late date, and a наш.дом.рф map view places "
                "the new-build pin for this object directly on the '14' plot "
                "(the old '12' plot one row south carries its own already-linked "
                "marker) — both 12А and 14А confirmed occupying their respective "
                "demolished footprints.",
        "source": "2026-07-15 construction-photo OCR sweep + on-the-ground correction",
    },
    {
        "property_id": 4649,
        "demolished_building_id": "AVENUE:строителей|93",
        "eisghs_id": 64690,
        "note": "Пр. Строителей 93 → same house number, 93 (СЗ-1 ПОРФИР) — rebuilt "
                "at the original address, not a laundered one. OCR read 'ПР. "
                "СТРОИТЕЛЕЙ 93' on 4/8 monthly photos; object's own geocoded "
                "point sits 3m from this property, the tightest spatial match "
                "found in this sweep.",
        "source": "2026-07-15 construction-photo OCR sweep",
    },
    {
        "property_id": 4844,
        "demolished_building_id": "STREET:зелинского|23",
        "eisghs_id": 71846,
        "note": "Ул. Зелинского 23 (pre-war 23А) → «Резиденция Концепт», 30А "
                "(СЗ-1 ПОРФИР) — block redevelopment, NOT same-footprint rebuild "
                "(60m+ from the demolished property, unlike every other entry "
                "here). OCR of the caption was thin (only 2 photos exist for "
                "this object, 1 clean 'УЛ. ЗЕЛИНСКОГО 30А'). The naming ('30А') "
                "references a nearby INTACT building at Зелинского 30 (confirmed "
                "still standing by on-the-ground review, 2026-07-15) — that "
                "'30' address is NOT the demolished predecessor here — despite "
                "minstroy_demolition_register's source CSV genuinely, explicitly "
                "listing 'ул. Зелинского д. 30' as its own row under the same "
                "decree (ГКО ДНР №53, 29.09.2022) that also names 27, 17Б, 19Б. "
                "That's not a parsing error (confirmed against the raw register "
                "row-by-row, 2026-07-15) — the decree really did order 30's "
                "demolition. It was apparently never carried out (confirmed "
                "still standing on the ground, 2026-07-15): a decree-vs-execution "
                "gap, the same M4 'restoration without restitution' pattern "
                "already documented for Ленина 106 (MUP-CS-002) — a candidate "
                "lead for that case study, not a data bug. Predecessor/new-corpus "
                "pairing (23↔30А vs 27↔30Б) confirmed by direct site inspection, "
                "not by the closer-but-ambiguous 15m proximity gap alone.",
        "source": "2026-07-15 construction-photo OCR sweep + on-the-ground correction",
    },
    {
        "property_id": 4845,
        "demolished_building_id": "STREET:зелинского|27",
        "eisghs_id": 71848,
        "note": "Ул. Зелинского 27 → «Резиденция Концепт», 30Б (СЗ-1 ПОРФИР). See "
                "the 23/30А entry above for the full block-redevelopment context "
                "— same site, same caveats (thin OCR, 63m from predecessor, "
                "pairing confirmed on the ground rather than by coordinate alone).",
        "source": "2026-07-15 construction-photo OCR sweep + on-the-ground correction",
    },
    # 2026-07-15, on-the-ground identification (user, no OCR — both developers
    # below are non-Porfir, so the construction-photo caption technique doesn't
    # apply; see scripts/315's docstring for that scope limit).
    {
        "property_id": 4945,
        "demolished_building_id": "STREET:куприна|63",
        "eisghs_id": 69766,
        "note": "Ул. Куприна 63 → one new building (СЗ АНТАРЕС) spanning the "
                "combined footprint of 63 AND 65 — see the 65 entry below for the "
                "other half. Object's own geocoded point sits ~67m from 63 and "
                "~34m from 65 (closer to 65's centroid, consistent with one "
                "footprint covering both, not evidence against 63). No confirmed "
                "final house number yet — object still under construction "
                "(foundation stage, June 2026 progress photo) and its own ЕИСЖС "
                "address field is still bare ('р-н Жовтневый, ул Куприна').",
        "source": "2026-07-15 on-the-ground identification",
    },
    {
        "property_id": 4946,
        "demolished_building_id": "STREET:куприна|65",
        "eisghs_id": 69766,
        "note": "Ул. Куприна 65 → same new building as the 63 entry above (СЗ "
                "АНТАРЕС) — one new construction spanning both demolished plots. "
                "This address also carries 4 named deaths (Mariupol Destruction "
                "and Victims Map TSV, checked 2026-07-15) — a single-building "
                "fire: Гапонов С.В. и Гримани Т.И. (both kv.132), Овчаренко Р. "
                "(kv.123), Овчинникова Н. (kv.120, 80y/o, jumped from the "
                "burning apartment). See death_sites_new_construction.md, Case 3.",
        "source": "2026-07-15 on-the-ground identification + Mariupol Destruction and Victims Map TSV",
    },
    {
        "property_id": 4947,
        "demolished_building_id": "STREET:куприна|69",
        "eisghs_id": 66292,
        "note": "Ул. Куприна 69 → 69Б (СЗ СИРИУС БИЛД). Object's own geocoded "
                "point sits 5m from this property — the tightest spatial match in "
                "this whole crosswalk alongside Строителей 93.",
        "source": "2026-07-15 on-the-ground identification",
    },
    # 2026-07-15, on-the-ground identification: ЖК "Ленинградский квартал"
    # (СЗ СУ-2007, part of the already-tracked 15-МКД complex on Металлургов —
    # see death_sites_new_construction.md's "Meduza gravedigger cross-section"
    # row) — one new building, two towers on a shared stylobate, named 89А,
    # standing on the combined footprint of three demolished neighbors, all
    # under the same demolition order (№56).
    {
        "property_id": 4551,
        "demolished_building_id": "AVENUE:металлургов|91",
        "eisghs_id": 61271,
        "note": "Пр. Металлургов 91 → 89А (ЖК «Ленинградский квартал», литера "
                "15, СЗ СУ-2007) — closest of the three predecessor plots (34m). "
                "Commissioned 2025-09-26.",
        "source": "2026-07-15 on-the-ground identification",
    },
    {
        "property_id": 4550,
        "demolished_building_id": "AVENUE:металлургов|89",
        "eisghs_id": 61271,
        "note": "Пр. Металлургов 89 → 89А, same building as the 91 entry above "
                "(52m from this plot).",
        "source": "2026-07-15 on-the-ground identification",
    },
    {
        "property_id": 4548,
        "demolished_building_id": "AVENUE:металлургов|87",
        "eisghs_id": 61271,
        "note": "Пр. Металлургов 87 → 89А, same building as the 91/89 entries "
                "above — only PARTLY on this footprint per on-the-ground "
                "identification (112m from this plot's own point, the weakest "
                "of the three; the stylobate/podium apparently only clips this "
                "plot's corner rather than sitting fully on it).",
        "source": "2026-07-15 on-the-ground identification",
    },
    # ЖК «Нахимовский» (СЗ КОРПОРАЦИЯ СМУ-5) — the case study's "ЖК
    # Нахимовский zone" group. Originally worked out via on-the-ground/DMS-
    # coordinate identification (2026-07-15, see individual notes below —
    # pure spatial matching was ambiguous/misleading, since this developer's
    # objects report similarly-imprecise shared site coordinates that don't
    # cleanly separate onto individual footprints). THEN independently
    # confirmed at the strongest possible evidentiary tier: an official
    # pro-occupation Telegram post (t.me/russkiy_mariupol/13451, 2026-07-15)
    # quotes decree text by name — "Распоряжение №178" granting two land
    # parcels to «Корпорация СМУ-5» explicitly "на месте бывших домов №17А,
    # 17Б, 19Б по ул. Зелинского, №25, 27, по ул. Бахчиванджи" ("on the site
    # of former buildings..."), describing a planned 6-building complex. Every
    # eisghs object below carries decree_number '178' in its own record,
    # independently matching the post. This is the same tier of evidence as
    # the Киевская 59Б entry above (a decree naming the address directly).
    {
        "property_id": 4837,
        "demolished_building_id": "STREET:зелинского|17а",
        "eisghs_id": 66986,
        "note": "Ул. Зелинского 17А → one new building (СЗ КОРПОРАЦИЯ СМУ-5), "
                "part of ЖК «Нахимовский» (decree №178 — see block note above). "
                "Identified as the corpus running parallel to Zelinskogo street "
                "itself (single-family homes visible across the street in its "
                "January 2026 foundation-pit photo). This footprint also covers "
                "two smaller structures with NO property record on this spine — "
                "a non-residential building locals describe as a boiler house, "
                "informally also called '17Б' despite being ~90m from this "
                "project's tracked 'Зелинского 17Б' record (see the 66989 entry "
                "below) — a real-world address duplication, not a data error — "
                "and a small single-family home at plain '17' (death record: "
                "Иванов Виктор Евгеньевич, d. 13.03.2022, t.me/mariupolRIP/11748 "
                "— his own testimony message actually reads '17а', suggesting "
                "the TSV database dropped the letter, not a second building). "
                "Precise DMS coordinates for 17А read off a damaged-building "
                "photo (t.me/mariupolnow/24389, /7634) land 11.4m from this "
                "project's own geocoding for the property. Also 2 more named "
                "deaths at this address (Ахтырский Максим, 12, airstrike "
                "18.03.2022; a missing-person post for Горпенко Владимир "
                "Иванович, apt 14 or 22) — see death_sites_new_construction.md.",
        "source": "2026-07-15 on-the-ground identification + decree №178 (t.me/russkiy_mariupol/13451)",
    },
    {
        "property_id": 4841,
        "demolished_building_id": "STREET:зелинского|19б",
        "eisghs_id": 66987,
        "note": "Ул. Зелинского 19Б → one new building (СЗ КОРПОРАЦИЯ СМУ-5), "
                "part of ЖК «Нахимовский» (decree №178 — see block note above). "
                "Identified by its flank facing the courtyard of the L-shaped "
                "building at Зелинского 15. Precise DMS coordinates for 19Б "
                "land 7.7m from this project's own geocoding for the property. "
                "This was a railway-workers' dormitory (ж/д общежитие), not an "
                "ordinary apartment building — named death: Микикечко Максим "
                "Игоревич, killed by shrapnel 04.03.2022, body collected by "
                "the 'Орфей' removal service, burial location unknown "
                "(t.me/mariupolRIP/32958).",
        "source": "2026-07-15 on-the-ground identification + decree №178 (t.me/russkiy_mariupol/13451)",
    },
    {
        "property_id": 4838,
        "demolished_building_id": "STREET:зелинского|17б",
        "eisghs_id": 66989,
        "note": "Ул. Зелинского 17Б → one new building (СЗ КОРПОРАЦИЯ СМУ-5), "
                "part of ЖК «Нахимовский» (decree №178 — see block note above). "
                "Identified by elimination once 17А (→66986) and 19Б (→66987) "
                "above were pinned down. Precise DMS coordinates for this 17Б "
                "(read off a damaged-building photo, t.me/mariupolnow/2584) "
                "land 1.2m from this project's own geocoding for the property "
                "— the tightest match in this entire crosswalk.",
        "source": "2026-07-15 on-the-ground identification + decree №178 (t.me/russkiy_mariupol/13451)",
    },
    {
        "property_id": 10640,
        "demolished_building_id": "STREET:бахчиванджи|27",
        "eisghs_id": 71399,
        "note": "Ул. Бахчиванджи 27 → one new building (СЗ КОРПОРАЦИЯ СМУ-5), "
                "part of ЖК «Нахимовский» (decree №178 — see block note above). "
                "NOT part of the Зелинского 17А/17Б/19Б group above despite "
                "being the same complex and originally suspected of belonging "
                "there — its June 2026 foundation-pit photo (which also shows "
                "the other corpuses nearby, confirming they're one project) "
                "places it on Бахчиванджи 27's footprint instead. 91m from "
                "this project's geocoding for that property — looser than the "
                "Зелинского matches above, but far tighter than the 236m+ this "
                "object sits from any of the Зелинского trio, which is what "
                "originally made this pairing look wrong.",
        "source": "2026-07-15 on-the-ground identification + decree №178 (t.me/russkiy_mariupol/13451)",
    },
    {
        "property_id": 4778,
        "demolished_building_id": "STREET:бахчиванджи|25",
        "eisghs_id": 71400,
        "note": "Ул. Бахчиванджи 25 → «ЖК Нахимовский, 2 очередь» (СЗ КОРПОРАЦИЯ "
                "СМУ-5). Found directly from decree №178's own text (see block "
                "note above) rather than site inspection — this object's own "
                "record carries decree_number '178', an exact match, and its "
                "geocoded point sits 8m from this property, the tightest "
                "coordinate match in the whole ЖК Нахимовский group.",
        "source": "2026-07-15 decree №178 (t.me/russkiy_mariupol/13451)",
    },
    # NOT added, investigated and rejected/deferred this sweep:
    #   - Пр. Строителей 74/76/78/80/88 -> eisghs 69427/69749/69751/70147/70142:
    #     OCR independently confirmed all five house numbers, but each demolished
    #     property already carries its OWN reallocation event to the SAME eisghs
    #     object via a decree/land-order path (scripts/252, source
    #     'dnr_land_orders (reconciled)') — already correctly linked, nothing to add.
    #   - Ул. Латышева 2/23 -> eisghs 71674/71675: only 1-2 photos exist per
    #     object and the OCR reads were noisy/inconsistent (single-digit
    #     fragments) — too thin to act on.
]


def load_crosswalk() -> dict:
    """demolished property_id -> crosswalk entry. See DEMOLITION_NEWBUILD_CROSSWALK."""
    return {link["property_id"]: link for link in DEMOLITION_NEWBUILD_CROSSWALK}


def load_newbuild_lookup() -> dict:
    """eisghs_id -> {lon, lat, addr, dev, flats, decree, decree_date, commissioned,
    project_name} for every ЕИСЖС object -- used to enrich a linked demolition
    point (same-address or crosswalk) with its replacement's own details, and to
    draw a before/after connector line without a second DB round-trip."""
    src = QGIS_DIR / "eisghs_newbuilds.geojson"
    if not src.exists():
        return {}
    gj = json.loads(src.read_text(encoding="utf-8"))
    out = {}
    for f in gj["features"]:
        p = f["properties"]
        eid = p.get("eisghs_id")
        if eid is None:
            continue
        coords = f["geometry"]["coordinates"] if f.get("geometry") else None
        out[eid] = {
            "lon": round(coords[0], 5) if coords else None,
            "lat": round(coords[1], 5) if coords else None,
            "addr": p.get("address"),
            "dev": p.get("dev_name_short"),
            "flats": p.get("flat_cnt"),
            "decree": p.get("decree_number"),
            "decree_date": p.get("decree_date"),
            "commissioned": p.get("commissioned_dt"),
            "project_name": p.get("nameObj"),
        }
    return out


def build_demolition_features(rows, toponym_index, crosswalk_by_pid, newbuild_lookup):
    full, public = [], []
    for row in rows:
        realloc_eisghs_id = (row["reallocation_detail"] or {}).get("eisghs_id") if row["reallocation_detail"] else None
        is_rebuilt_same = row["reallocation_date"] is not None or row["reallocation_detail"] is not None
        crosswalk = None if is_rebuilt_same else crosswalk_by_pid.get(row["id"])
        demo_date = row["demolition_date"].isoformat() if row["demolition_date"] else None
        realloc_date = row["reallocation_date"].isoformat() if row["reallocation_date"] else None

        linked_new, link_basis = None, None
        if is_rebuilt_same:
            kind = "demolished_rebuilt_same"
            link_basis = "same_address"
            if realloc_eisghs_id is not None:
                linked_new = newbuild_lookup.get(realloc_eisghs_id)
        elif crosswalk is not None:
            kind = "demolished_rebuilt_nearby"
            link_basis = "crosswalk"
            linked_new = newbuild_lookup.get(crosswalk["eisghs_id"])
        else:
            kind = "demolished"

        addr = address_block(row["prewar_address"], row["occupation_address"], toponym_index)
        verif_status, verif_note = verification_label(row["demolition_confidence"])
        confidence_val = float(row["demolition_confidence"]) if row["demolition_confidence"] is not None else None
        link_fields = {
            "link_basis": link_basis,
            "link_note": crosswalk["note"] if crosswalk else None,
            "linked_new_lon": linked_new["lon"] if linked_new else None,
            "linked_new_lat": linked_new["lat"] if linked_new else None,
            "linked_new_addr": linked_new["addr"] if linked_new else None,
            "linked_new_dev": linked_new["dev"] if linked_new else None,
            "linked_new_flats": linked_new["flats"] if linked_new else None,
            "linked_new_decree": linked_new["decree"] if linked_new else None,
            "linked_new_commissioned": linked_new["commissioned"] if linked_new else None,
            "linked_new_project": linked_new["project_name"] if linked_new else None,
        }
        full_props = {
            "id": row["id"], "addr_ua": addr["ua"], "addr_ua_documented": addr["ua_documented"],
            "addr_ru": addr["ru"], "addr_soviet": addr["soviet_name"], "addr_latin": addr["latin"],
            "renamed_note": addr["renamed_note"],
            "kind": kind,
            "demolition_date": demo_date,
            "demolition_basis": event_basis("demolition", row["demolition_detail"]),
            "reallocation_date": realloc_date,
            "reallocation_basis": event_basis("reallocation", row["reallocation_detail"]) if is_rebuilt_same else None,
            "confidence": confidence_val, "verification_status": verif_status, "verification_note": verif_note,
            **link_fields,
        }
        public_props = {
            "ua": addr["ua"], "ua_doc": addr["ua_documented"], "ru": addr["ru"], "soviet": addr["soviet_name"],
            "latin": addr["latin"], "renamed": addr["renamed_note"], "kind": kind,
            "demo_date": demo_date,
            "demo_basis": event_basis("demolition", row["demolition_detail"]),
            "realloc_date": realloc_date,
            "realloc_basis": event_basis("reallocation", row["reallocation_detail"]) if is_rebuilt_same else None,
            "confidence": confidence_val, "verif": verif_status, "verif_note": verif_note,
            **link_fields,
        }
        geom = {"type": "Point", "coordinates": [round(row["lon"], 5), round(row["lat"], 5)]}
        full.append({"type": "Feature", "geometry": geom, "properties": full_props})
        public.append({"type": "Feature", "geometry": geom, "properties": public_props})
    return full, public


_OBJ_TYPE_MAX = 8  # cap the object-type list shown in a popup


def _aggregate_nonres(rows, toponym_index):
    """Group per-object non-residential events into one feature per building."""
    by_prop = {}
    for row in rows:
        by_prop.setdefault(row["id"], []).append(row)
    full, public = [], []
    for pid, group in by_prop.items():
        first = group[0]
        addr = address_block(first["prewar_address"], first["occupation_address"], toponym_index)
        obj_types, cadastrals, areas, premises, districts = [], [], [], set(), set()
        for r in group:
            d = r["detail"] or {}
            ot = d.get("object_type")
            if ot and ot not in obj_types:
                obj_types.append(ot)
            if d.get("cadastral_no"):
                cadastrals.append(d["cadastral_no"])
            if d.get("parcel_area_ha"):
                areas.append(d["parcel_area_ha"])
            if d.get("premises_class"):
                premises.add(d["premises_class"])
            if d.get("district"):
                districts.add(d["district"])
        premises_class = ("industrial" if "industrial" in premises
                          else "commercial" if "commercial" in premises else None)
        full_props = {
            "id": pid, "addr_ua": addr["ua"], "addr_ua_documented": addr["ua_documented"],
            "addr_ru": addr["ru"], "addr_soviet": addr["soviet_name"], "addr_latin": addr["latin"],
            "renamed_note": addr["renamed_note"],
            "premises_class": premises_class, "property_kind": first["property_kind"],
            "object_count": len(group), "object_types": obj_types,
            "cadastral_nos": cadastrals or None,
            "parcel_area_ha": round(sum(areas), 4) if areas else None,
            "district": "; ".join(sorted(districts)) or None,
        }
        public_props = {
            "ua": addr["ua"], "ua_doc": addr["ua_documented"], "ru": addr["ru"],
            "soviet": addr["soviet_name"], "latin": addr["latin"], "renamed": addr["renamed_note"],
            "premises": premises_class, "count": len(group),
            "types": "; ".join(obj_types[:_OBJ_TYPE_MAX]) + (" …" if len(obj_types) > _OBJ_TYPE_MAX else ""),
            "cadastral": "; ".join(cadastrals) if cadastrals else None,
            "area_ha": round(sum(areas), 4) if areas else None,
            "district": "; ".join(sorted(districts)) or None,
        }
        geom = {"type": "Point", "coordinates": [round(first["lon"], 5), round(first["lat"], 5)]}
        full.append({"type": "Feature", "geometry": geom, "properties": full_props})
        public.append({"type": "Feature", "geometry": geom, "properties": public_props})
    return full, public


def build_nonres_demolition_features(rows, toponym_index):
    """One feature per building on the non-residential demolition list."""
    by_prop = {}
    for row in rows:
        by_prop.setdefault(row["id"], []).append(row)
    full, public = [], []
    for pid, group in by_prop.items():
        first = group[0]
        addr = address_block(first["prewar_address"], first["occupation_address"], toponym_index)
        obj_types = []
        for r in group:
            ot = (r["detail"] or {}).get("object_type")
            if ot and ot not in obj_types:
                obj_types.append(ot)
        district = next((r["detail"].get("district") for r in group
                         if (r["detail"] or {}).get("district")), None)
        full_props = {
            "id": pid, "addr_ua": addr["ua"], "addr_ua_documented": addr["ua_documented"],
            "addr_ru": addr["ru"], "addr_soviet": addr["soviet_name"], "addr_latin": addr["latin"],
            "renamed_note": addr["renamed_note"],
            "object_types": obj_types, "district": district,
        }
        public_props = {
            "ua": addr["ua"], "ua_doc": addr["ua_documented"], "ru": addr["ru"],
            "soviet": addr["soviet_name"], "latin": addr["latin"], "renamed": addr["renamed_note"],
            "types": "; ".join(obj_types), "district": district,
        }
        geom = {"type": "Point", "coordinates": [round(first["lon"], 5), round(first["lat"], 5)]}
        full.append({"type": "Feature", "geometry": geom, "properties": full_props})
        public.append({"type": "Feature", "geometry": geom, "properties": public_props})
    return full, public


def build_landgrant_public():
    """Trim the QGIS land-grant export (scripts/68) into a public map copy.
    Beneficiary + decree + cadastral + parcel area; drops nothing sensitive
    (occupation officials/beneficiaries are in-scope for accountability)."""
    src = QGIS_DIR / "land_order_grants.geojson"
    if not src.exists():
        log.warning("land_order_grants.geojson absent — run scripts/68 first; skipping land-grant layer")
        return None
    gj = json.loads(src.read_text(encoding="utf-8"))
    feats = []
    for f in gj["features"]:
        p = f["properties"]
        cads = p.get("cadastral_numbers")
        if isinstance(cads, list):
            cads = "; ".join(cads)
        feats.append({
            "type": "Feature", "geometry": f["geometry"],
            "properties": {
                "decree": p.get("decree_number"), "date": p.get("decree_date"),
                "beneficiary": p.get("beneficiary_name"), "project": p.get("project_name"),
                "addr": p.get("address_normalized") or p.get("address_raw"),
                "area_sqm": p.get("area_sqm"), "cadastral": cads or None,
                "conf": p.get("geocode_confidence"),
            },
        })
    return feats


def build_newbuild_public(matched_eisghs_ids: set):
    """Trim the ЕИСЖС new-build export (scripts/71) into a public map copy --
    ONLY the objects with no demolished predecessor confirmed on the spine
    (neither the automatic same-property_id match nor the curated crosswalk
    caught them). Objects that ARE matched are not emitted here at all: they
    already appear as the linked_new_* fields on their demolished-property
    point (build_demolition_features), rendered as a connector line + small
    marker by the front-end's "of those, rebuilt" layer -- showing them again
    as a second, unrelated-looking top-level layer is exactly the confusion
    this split exists to remove (see docs/case_studies -- "why are there two
    layers for one real-world event" review, 2026-07-13)."""
    src = QGIS_DIR / "eisghs_newbuilds.geojson"
    if not src.exists():
        log.warning("eisghs_newbuilds.geojson absent — run scripts/71 first; skipping new-build layer")
        return None
    gj = json.loads(src.read_text(encoding="utf-8"))
    feats = []
    n_matched = 0
    for f in gj["features"]:
        p = f["properties"]
        if p.get("eisghs_id") in matched_eisghs_ids:
            n_matched += 1
            continue
        feats.append({
            "type": "Feature", "geometry": f["geometry"],
            "properties": {
                "addr": p.get("address"), "dev": p.get("dev_name_short"),
                "flats": p.get("flat_cnt"), "living_sqm": p.get("area_sqm_living"),
                "commissioned": p.get("commissioned_dt"),
                "decree": p.get("decree_number"), "decree_date": p.get("decree_date"),
            },
        })
    log.info("newbuilds: %d matched to a demolished predecessor (folded into the demolition layer), "
              "%d unmatched (own layer)", n_matched, len(feats))
    return feats


def write_geojson(path: Path, features: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f, ensure_ascii=False)
    log.info("wrote %s (%d features, %d bytes)", path, len(features), path.stat().st_size)


def group_by(rows, key):
    out = {}
    for row in rows:
        out.setdefault(row[key], []).append(row)
    return out


BOUNDARY_PATH = PROJECT_ROOT / "data" / "boundaries" / "mariupol_hromada_boundary.geojson"


def load_boundary_geojson() -> str:
    """City hromada boundary only (not the extended okrug boundary scripts/23
    searches against) — see module docstring for why villages are excluded."""
    gj = json.loads(BOUNDARY_PATH.read_text(encoding="utf-8"))
    geom = gj["features"][0]["geometry"]
    return json.dumps(geom)


def main():
    boundary_geojson = load_boundary_geojson()
    prop_sql = PROPERTY_SQL.format(boundary=BOUNDARY_FILTER_SQL)
    demo_sql = DEMOLITION_SQL.format(boundary=BOUNDARY_FILTER_SQL)
    nonres_own_sql = NONRES_OWNERLESS_SQL.format(boundary=BOUNDARY_FILTER_SQL)
    nonres_demo_sql = NONRES_DEMOLITION_SQL.format(boundary=BOUNDARY_FILTER_SQL)
    unfiltered_prop_sql = PROPERTY_SQL.format(boundary="")

    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with conn.cursor() as cur:
            cur.execute(unfiltered_prop_sql)
            all_geocoded_count = len(cur.fetchall())
            cur.execute(prop_sql, (boundary_geojson,))
            prop_rows = cur.fetchall()
            cur.execute(SEIZURE_EVENT_SQL)
            event_rows = cur.fetchall()
            cur.execute(CORROBORATION_SQL)
            corrob_rows = cur.fetchall()
            cur.execute(COURT_CASE_PROPERTY_SQL)
            court_props = {r["property_id"] for r in cur.fetchall()}
            cur.execute(TOPONYM_SQL)
            toponym_rows = cur.fetchall()
            cur.execute(demo_sql, (boundary_geojson,))
            demo_rows = cur.fetchall()
            cur.execute(nonres_own_sql, (boundary_geojson,))
            nonres_own_rows = cur.fetchall()
            cur.execute(nonres_demo_sql, (boundary_geojson,))
            nonres_demo_rows = cur.fetchall()
    finally:
        conn.close()

    log.info(
        "boundary filter: %d geocoded properties total, %d inside city hromada boundary "
        "(%d outside — satellite villages + any other out-of-boundary points, held off the public map)",
        all_geocoded_count, len(prop_rows), all_geocoded_count - len(prop_rows),
    )

    toponym_index = build_toponym_index(toponym_rows)
    events_by_prop = group_by(event_rows, "property_id")
    corrob_by_prop = group_by(corrob_rows, "property_id")

    log.info(
        "properties: %d, seizure_events: %d, corroborations: %d, demolition rows: %d, toponym pairs: %d",
        len(prop_rows), len(event_rows), len(corrob_rows), len(demo_rows), len(toponym_rows),
    )

    crosswalk_by_pid = load_crosswalk()
    newbuild_lookup = load_newbuild_lookup()
    log.info("demolition->newbuild crosswalk: %d curated links loaded", len(crosswalk_by_pid))

    spine_full, spine_public = build_spine_features(prop_rows, events_by_prop, corrob_by_prop, court_props, toponym_index)
    demo_full, demo_public = build_demolition_features(demo_rows, toponym_index, crosswalk_by_pid, newbuild_lookup)
    nonres_own_full, nonres_own_public = _aggregate_nonres(nonres_own_rows, toponym_index)
    nonres_demo_full, nonres_demo_public = build_nonres_demolition_features(nonres_demo_rows, toponym_index)

    write_geojson(QGIS_DIR / "property_spine_context.geojson", spine_full)
    write_geojson(QGIS_DIR / "demolition_sites.geojson", demo_full)
    write_geojson(QGIS_DIR / "nonresidential_ownerless.geojson", nonres_own_full)
    write_geojson(QGIS_DIR / "nonresidential_demolition.geojson", nonres_demo_full)
    write_geojson(PUBLIC_DIR / "property_spine_context.geojson", spine_public)
    write_geojson(PUBLIC_DIR / "demolition_sites.geojson", demo_public)
    write_geojson(PUBLIC_DIR / "nonresidential_ownerless.geojson", nonres_own_public)
    write_geojson(PUBLIC_DIR / "nonresidential_demolition.geojson", nonres_demo_public)

    # Land-grant + new-build public copies (trimmed from the scripts/68 & 71
    # QGIS exports; these layers are geocoded outside the DB spine).
    landgrants = build_landgrant_public()
    if landgrants is not None:
        write_geojson(PUBLIC_DIR / "land_grants.geojson", landgrants)
    matched_eisghs_ids = {crosswalk["eisghs_id"] for crosswalk in crosswalk_by_pid.values()}
    matched_eisghs_ids |= {
        (row["reallocation_detail"] or {}).get("eisghs_id")
        for row in demo_rows
        if row["reallocation_detail"] and row["reallocation_detail"].get("eisghs_id") is not None
    }
    newbuilds = build_newbuild_public(matched_eisghs_ids)
    if newbuilds is not None:
        write_geojson(PUBLIC_DIR / "newbuilds.geojson", newbuilds)

    log.info("non-res ownerless buildings: %d, non-res demolition buildings: %d",
             len(nonres_own_public), len(nonres_demo_public))


if __name__ == "__main__":
    main()
