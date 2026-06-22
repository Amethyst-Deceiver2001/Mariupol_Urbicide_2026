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

PROPERTY_SQL = """
select p.id, p.prewar_address, p.occupation_address, p.rd4u_category,
       st_x(p.geom) as lon, st_y(p.geom) as lat
from property p
where p.geom is not null
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
"""

TOPONYM_SQL = "select prewar_name, occupation_name from toponym where kind = 'rename'"

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
    return min(rows, key=lambda r: (STAGE_PRIORITY.get(r["stage"], 9), r["event_date"] or "9999-99-99"))


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


def build_demolition_features(rows, toponym_index):
    full, public = [], []
    for row in rows:
        is_rebuilt = row["reallocation_date"] is not None or row["reallocation_detail"] is not None
        demo_date = row["demolition_date"].isoformat() if row["demolition_date"] else None
        realloc_date = row["reallocation_date"].isoformat() if row["reallocation_date"] else None
        kind = "demolished_rebuilt" if is_rebuilt else "demolished"
        addr = address_block(row["prewar_address"], row["occupation_address"], toponym_index)
        verif_status, verif_note = verification_label(row["demolition_confidence"])
        confidence_val = float(row["demolition_confidence"]) if row["demolition_confidence"] is not None else None
        full_props = {
            "id": row["id"], "addr_ua": addr["ua"], "addr_ua_documented": addr["ua_documented"],
            "addr_ru": addr["ru"], "addr_soviet": addr["soviet_name"], "addr_latin": addr["latin"],
            "renamed_note": addr["renamed_note"],
            "kind": kind,
            "demolition_date": demo_date,
            "demolition_basis": event_basis("demolition", row["demolition_detail"]),
            "reallocation_date": realloc_date,
            "reallocation_basis": event_basis("reallocation", row["reallocation_detail"]) if is_rebuilt else None,
            "confidence": confidence_val, "verification_status": verif_status, "verification_note": verif_note,
        }
        public_props = {
            "ua": addr["ua"], "ua_doc": addr["ua_documented"], "ru": addr["ru"], "soviet": addr["soviet_name"],
            "latin": addr["latin"], "renamed": addr["renamed_note"], "kind": kind,
            "demo_date": demo_date,
            "demo_basis": event_basis("demolition", row["demolition_detail"]),
            "realloc_date": realloc_date,
            "realloc_basis": event_basis("reallocation", row["reallocation_detail"]) if is_rebuilt else None,
            "confidence": confidence_val, "verif": verif_status, "verif_note": verif_note,
        }
        geom = {"type": "Point", "coordinates": [round(row["lon"], 5), round(row["lat"], 5)]}
        full.append({"type": "Feature", "geometry": geom, "properties": full_props})
        public.append({"type": "Feature", "geometry": geom, "properties": public_props})
    return full, public


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


def main():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with conn.cursor() as cur:
            cur.execute(PROPERTY_SQL)
            prop_rows = cur.fetchall()
            cur.execute(SEIZURE_EVENT_SQL)
            event_rows = cur.fetchall()
            cur.execute(CORROBORATION_SQL)
            corrob_rows = cur.fetchall()
            cur.execute(COURT_CASE_PROPERTY_SQL)
            court_props = {r["property_id"] for r in cur.fetchall()}
            cur.execute(TOPONYM_SQL)
            toponym_rows = cur.fetchall()
            cur.execute(DEMOLITION_SQL)
            demo_rows = cur.fetchall()
    finally:
        conn.close()

    toponym_index = build_toponym_index(toponym_rows)
    events_by_prop = group_by(event_rows, "property_id")
    corrob_by_prop = group_by(corrob_rows, "property_id")

    log.info(
        "properties: %d, seizure_events: %d, corroborations: %d, demolition rows: %d, toponym pairs: %d",
        len(prop_rows), len(event_rows), len(corrob_rows), len(demo_rows), len(toponym_rows),
    )

    spine_full, spine_public = build_spine_features(prop_rows, events_by_prop, corrob_by_prop, court_props, toponym_index)
    demo_full, demo_public = build_demolition_features(demo_rows, toponym_index)

    write_geojson(QGIS_DIR / "property_spine_context.geojson", spine_full)
    write_geojson(QGIS_DIR / "demolition_sites.geojson", demo_full)
    write_geojson(PUBLIC_DIR / "property_spine_context.geojson", spine_public)
    write_geojson(PUBLIC_DIR / "demolition_sites.geojson", demo_public)


if __name__ == "__main__":
    main()
