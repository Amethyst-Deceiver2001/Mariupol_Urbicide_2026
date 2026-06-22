#!/usr/bin/env python3
"""Temporal differential over the dated ownerless registries (hypothesis test).

We can see the *current* ownerless registry (12,948 MKD apartments) but not the
properties that were *once* flagged ownerless and have since left that track --
either SEIZED into municipal ownership (court / decree completed) or RETURNED to
an owner/heir who came forward. This script reconstructs that hidden population
two ways:

  LAYER A -- DISPOSITION LEDGER (primary evidence, no inference).
    Several captured snapshots carry an explicit per-row disposition marker in a
    «Признаки учёта» column:
        Собственники / Наследники / Заинтересованное лицо  -> claimant_surfaced
        Муницип.Жилье                                      -> municipal_seized
        Признаки бесхозяйности                             -> still_ownerless
    The 02_09_2024 «Исключены из бесхоза» PDF is an entire removal list (1,404
    rows, all «Собственники»). The 13_01_2025 list mixes all five markers,
    including 70 «Муницип.Жилье» -- the occupation administration's own admission
    of which properties it took. We extract every marked address verbatim.

  LAYER B -- DISAPPEARANCE DIFFERENTIAL (present-then-absent).
    For each dated snapshot we compute a building_key (and apt where columnar)
    using the SAME normalization pipeline the spine uses
    (normalize.address.address_to_building_key), then test presence against the
    current registry. Entries present in an older list but ABSENT now are
    classified by cross-referencing:
        - the disposition markers above,
        - the PostgreSQL spine's seizure_event stages for that building_key
          (court_transfer / reallocation / demolition / removal_decree -> seized).
    Anything absent with NO marker and NO spine event lands in an
    `unexplained_disappearance` review queue.

Forensic notes:
  - Occupation registries are evidence of the *act*, never valid title.
  - Living private owners are NOT named here; we key on address + disposition,
    not on any owner personal data (the marker columns carry none).
  - Pure local analysis over already-captured artifacts + the spine DB. No
    network. Safe to run.

Inputs (all already on disk):
  data/parsed/chat_document_inventory.jsonl   (script 149 -- locates snapshots)
  data/parsed/chat_docs/<sha>.txt             (extracted snapshot text)
  data/parsed/ownerless_registry.jsonl        (the current 12,948-row anchor)
  PostgreSQL spine (optional, via config.DATABASE_URL) for seizure_event cross-ref

Outputs:
  data/parsed/ownerless_differential_records.jsonl  -- one row per
        dispositioned-or-disappeared entry (building_key, class, marker,
        spine_stages, classification, source snapshot + date)
  data/parsed/ownerless_differential_summary.json
  console report

Run:
    PYTHONPATH=src python scripts/150_ownerless_temporal_differential.py
"""
import json
import logging
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402
from mariupol_seizures.normalize.address import (  # noqa: E402
    address_to_building_key,
    norm_house,
)

log = logging.getLogger(__name__)

INVENTORY = ROOT / "data" / "parsed" / "chat_document_inventory.jsonl"
REGISTRY = ROOT / "data" / "parsed" / "ownerless_registry.jsonl"
OUT_RECORDS = ROOT / "data" / "parsed" / "ownerless_differential_records.jsonl"
OUT_SUMMARY = ROOT / "data" / "parsed" / "ownerless_differential_summary.json"

# ── disposition marker vocabulary ───────────────────────────────────────────
# Marker text -> (disposition_class, human_label). Matched fuzzily (lower-cased,
# punctuation/space-stripped) so "Муницип.Жилье" / "Муниципальное жилье" / "Муниц.
# жильё" all fold together.
DISPOSITIONS = {
    "claimant_surfaced": "owner / heir / interested party came forward",
    "municipal_seized":  "taken into municipal ownership",
    "still_ownerless":   "still flagged ownerless (in process)",
}


def _classify_marker(cell: str | None) -> str | None:
    if not cell:
        return None
    s = re.sub(r"[\s.,]+", "", cell.lower())
    if not s:
        return None
    if s.startswith("муницип") and "жил" in s:
        return "municipal_seized"
    if "бесхоз" in s:
        return "still_ownerless"
    if s.startswith("собственник") or s.startswith("наследник") or "заинтересован" in s:
        return "claimant_surfaced"
    return None


# ── districts (metadata only; building_key is the real join key) ────────────
_DISTRICTS = [
    ("жовтневый", "Жовтневый"),
    ("ильичёвск", "Ильичёвский"), ("ильичевск", "Ильичёвский"),
    ("орджоникидзевск", "Орджоникидзевский"),
    ("приморск", "Приморский"),
    ("центральн", "Центральный"),
    ("левобережн", "Левобережный"),
    ("кальмиус", "Кальмиусский"),
]


def _district_of(token: str | None) -> str | None:
    if not token:
        return None
    low = token.lower()
    for stem, name in _DISTRICTS:
        if stem in low:
            return name
    return None


# ── address extractor ───────────────────────────────────────────────────────
# Snapshot rows arrive in three shapes, sometimes mixed within one file:
#   (a) "<street>, д. <house>, кв. <apt>"   (2025-01 list -- house+apt embedded)
#   (b) "<street>, <house>"                 (exclusion list, ИЖС -- no apt)
#   (c) columnar  <street>  <house>  <apt>  (besx / Nov-2025 district PDFs)
# Trailing house number = digits + optional letter + optional /N or -N corner.
_HOUSE_TAIL = re.compile(
    r"^(?P<street>.+?)[,\s]+(?P<house>\d+[а-яёa-z]?(?:\s?[/\-]\s?\d+[а-яёa-z]?)?)\s*$",
    re.I,
)
_HOUSE_AFTER_D = re.compile(
    r"\bд\.?\s*(\d+[а-яёa-z]?(?:\s?[/\-]\s?\d+[а-яёa-z]?)?)", re.I)
_APT_KV = re.compile(r"кв\.?\s*№?\s*,?\s*(\d{1,4}[а-яёa-z]?)", re.I)
_PURE_APT = re.compile(r"^\d{1,4}\s*(?:нежилое)?$", re.I)
_HOUSE_CELL = re.compile(r"^\d+[а-яёa-z]?(?:\s?[/\-]\s?\d+[а-яёa-z]?)?$", re.I)
_LEAD_SETTLEMENT = re.compile(
    r"^(?:(?:п|пгт|с|г|пос|село|посёлок|поселок)\.?\s+)?[А-ЯЁ][А-яёЇіЄ\-]+,?\s+"
    r"(?=(?:ул|пер|пр|бул|просп|улица|переулок|проспект|бульвар)\.?\s)",
    re.I,
)


# Street-type vocabulary for the semicolon-delimited registry-style rows
# (`settlement; type; name; house; apt`). Mirrors normalize.toponym._CLASS_MAP.
_STREET_TYPES = {
    "улица", "ул", "переулок", "пер", "проспект", "пр", "пр-т", "пр-кт",
    "просп", "бульвар", "б-р", "бул", "площадь", "пл", "шоссе", "ш",
    "набережная", "наб", "микрорайон", "мкр", "проезд", "пр-д", "тупик",
    "туп", "спуск", "дорога", "д-т", "жилмассив", "жмс", "сквер",
}
_SETTLEMENT_AT_START = re.compile(
    r"^\s*(?:г|гор|пгт|пос|посёлок|поселок|село|с|п)\.?\s+"
    r"([А-ЯЁ][А-Яа-яёІЇЄ\-]+(?:\s+[А-ЯЁ][А-Яа-яёІЇЄ\-]+)?)", re.I)


def _is_village(settlement_text: str | None) -> bool:
    """True if a settlement name is present and is NOT Mariupol proper (the
    current MKD registry only covers г. Мариуполь, so village/пгт rows have no
    comparand and must be excluded from the absence differential)."""
    if not settlement_text:
        return False
    return "мариуполь" not in settlement_text.lower()


def _parse_semicolon(joined: str):
    """Parse a `settlement; type; name; house; apt` registry-style row."""
    parts = [p.strip() for p in joined.split(";") if p.strip()]
    ti = next((i for i, p in enumerate(parts)
               if p.lower().rstrip(".") in _STREET_TYPES), None)
    if ti is None or ti + 1 >= len(parts):
        return None
    street = f"{parts[ti]} {parts[ti + 1]}".strip()
    house = parts[ti + 2] if ti + 2 < len(parts) else None
    apt = parts[ti + 3] if ti + 3 < len(parts) else None
    if not house:
        return None
    settlement = " ".join(parts[:ti])
    return street, house, apt, _is_village(settlement)


def _extract_address(cells: list[str]):
    """Return (street, house, apt, is_village) from one row's address fragments."""
    joined = re.sub(r"\s+", " ", " ".join(cells).replace("‚", ",")).strip()

    # registry-style semicolon layout (district PDFs / xlsx / besx)
    if joined.count(";") >= 2:
        sc = _parse_semicolon(joined)
        if sc:
            return sc

    village = _is_village(m.group(1)) if (m := _SETTLEMENT_AT_START.match(joined)) else False
    apt = None
    # (a) embedded "кв. N"
    ma = _APT_KV.search(joined)
    if ma:
        apt = ma.group(1)
        joined = (joined[:ma.start()] + " " + joined[ma.end():]).strip()
    # (c) columnar pure-apt trailing cell (no "кв" word), with a house before it
    elif len(cells) >= 3 and _PURE_APT.match(cells[-1]) and _HOUSE_CELL.match(cells[-2]):
        apt = cells[-1].split()[0]
        joined = re.sub(r"\s+", " ", " ".join(cells[:-1]).replace("‚", ",")).strip()

    street = house = None
    mh = _HOUSE_AFTER_D.search(joined)       # prefer an explicit "д. N"
    if mh:
        house = mh.group(1).replace(" ", "")
        street = joined[:mh.start()]
    else:
        m2 = _HOUSE_TAIL.match(joined)       # else the trailing number
        if m2:
            street, house = m2.group("street"), m2.group("house").replace(" ", "")
    if not house:
        return None, None, apt, village

    street = _LEAD_SETTLEMENT.sub("", street or "")
    street = re.split(r",", street)[0]                       # street ends at first comma
    street = re.sub(r"\bд(?:ом)?\.?\s*$", "", street).strip(" .,")
    return (street or None), house, apt, village


def _parse_row(line: str, sheet_district: str | None):
    """Parse one snapshot data line -> dict or None.

    Returns {district, street, house, apt, marker_class, raw} or None for
    headers / sheet markers / non-data lines. Updates of sheet_district are the
    caller's job (it watches for '### SHEET:').
    """
    s = line.rstrip("\n")
    if not s.strip():
        return None
    # peel leading row number
    m = re.match(r"^\s*(\d+)[\s\t]+(.*\S)\s*$", s)
    if not m:
        return None
    rest = m.group(2)
    cells = [c.strip() for c in re.split(r"\t|  +", rest) if c.strip()]
    if not cells:
        return None

    # disposition marker = trailing cell that classifies as a known disposition
    marker_class = None
    if len(cells) >= 2:
        mc = _classify_marker(cells[-1])
        if mc:
            marker_class = mc
            cells = cells[:-1]
    if not cells:
        return None

    # leading district cell?
    district = sheet_district
    d = _district_of(cells[0])
    if d and len(cells) >= 2:
        district = d
        cells = cells[1:]
    if not cells:
        return None

    street, house, apt, village = _extract_address(cells)
    if not street or not house:
        return None
    return {"district": district, "street": street, "house": house,
            "apt": apt, "marker_class": marker_class, "village": village}


# ── property-class heuristic ────────────────────────────────────────────────
def _prop_class(filename: str, sheet: str, has_apt: bool) -> str:
    hay = f"{filename} {sheet}".lower()
    if "ижс" in hay:
        return "izhs"          # private houses
    return "mkd" if has_apt else "unknown"


# ── snapshot discovery + parse ──────────────────────────────────────────────
def _snapshot_date(rec: dict) -> str:
    d = rec.get("snapshot_date") or rec.get("date") or ""
    # reject the known Telegram file-id false date (script-149 bug)
    if d and not re.match(r"^(20\d\d)-\d\d-\d\d$", d):
        return rec.get("date") or "????"
    return d or "????"


def load_snapshots():
    inv = [json.loads(l) for l in INVENTORY.open(encoding="utf-8")]
    snaps = []
    for r in inv:
        cat = r.get("category", "")
        if not (cat.startswith("ownerless") or cat == "owners_list"):
            continue
        if not r.get("text_path"):
            continue
        # misfiled non-registry lists: the "НЕ ФУНКЦИОНИРУЮЩИЕ ОБЪЕКТЫ" file is a
        # damage/non-functioning inventory, not an ownerless registry.
        if "ФУНКЦИОНИРУЮЩИЕ" in (r.get("filename") or "").upper():
            continue
        p = ROOT / r["text_path"]
        if not p.exists():
            continue
        date = _snapshot_date(r)
        text = p.read_text(encoding="utf-8")
        sheet_district = None
        rows = []
        for line in text.splitlines():
            sm = re.match(r"^###\s*SHEET:\s*(.*\S)", line)
            if sm:
                sheet_district = _district_of(sm.group(1))
                continue
            row = _parse_row(line, sheet_district)
            if row:
                rows.append(row)
        has_apt = any(x["apt"] for x in rows)
        pcls = _prop_class(r.get("filename") or "", text[:200], has_apt)
        snaps.append({
            "filename": r.get("filename") or "(no name)",
            "date": date, "category": cat, "sha256": r.get("sha256"),
            "prop_class": pcls, "rows": rows,
        })
    return snaps


# ── current registry anchor ─────────────────────────────────────────────────
def load_current_registry():
    bkeys = set()
    apt_keys = set()
    n = 0
    for line in REGISTRY.open(encoding="utf-8"):
        rec = json.loads(line)
        n += 1
        bk = address_to_building_key(rec.get("street_raw"), rec.get("house_raw"))
        if not bk:
            continue
        bkeys.add(bk)
        apt = norm_house(rec.get("apt_raw")) if rec.get("apt_raw") else None
        if apt:
            apt_keys.add(f"{bk}#{apt}")
    log.info("current registry: %d rows -> %d building_keys, %d apt_keys",
             n, len(bkeys), len(apt_keys))
    return n, bkeys, apt_keys


# ── spine seizure_event cross-reference ─────────────────────────────────────
_SEIZED_STAGES = {
    "court_transfer", "reallocation", "demolition", "removal_decree",
    "municipal_ownership", "registry_inclusion_court", "transfer",
}


def load_spine_stages():
    """building_key -> set(stage). Best-effort; empty dict if DB unreachable."""
    dsn = getattr(config, "DATABASE_URL", None)
    if not dsn:
        log.warning("no DATABASE_URL -- skipping spine cross-reference")
        return {}
    try:
        import psycopg2
        conn = psycopg2.connect(dsn)
        cur = conn.cursor()
        cur.execute("SELECT id, occupation_address FROM property")
        pid_bkey = {}
        for pid, addr in cur.fetchall():
            if not addr:
                continue
            if "," in addr:
                street, house = addr.split(",", 1)
            else:
                street, house = addr, ""
            bk = address_to_building_key(street.strip(), house.strip())
            if bk:
                pid_bkey[pid] = bk
        cur.execute("SELECT property_id, stage FROM seizure_event")
        bkey_stages = defaultdict(set)
        for pid, stage in cur.fetchall():
            bk = pid_bkey.get(pid)
            if bk:
                bkey_stages[bk].add(stage)
        conn.close()
        log.info("spine: %d properties keyed, %d building_keys with events",
                 len(pid_bkey), len(bkey_stages))
        return dict(bkey_stages)
    except Exception as e:
        log.warning("spine cross-reference failed (%s) -- continuing without", e)
        return {}


def _classify_disappearance(marker_class, spine_stages):
    """Decide why an entry left the ownerless track."""
    if marker_class == "municipal_seized":
        return "seized_municipal"
    if spine_stages and (spine_stages & _SEIZED_STAGES):
        return "seized_court"
    if marker_class == "claimant_surfaced":
        return "returned_to_claimant"
    return "unexplained_disappearance"


def main():
    snaps = load_snapshots()
    reg_n, reg_bkeys, reg_aptkeys = load_current_registry()
    spine = load_spine_stages()

    records = []
    snap_diag = []
    samples = []                       # (snapshot, date, [parse-sample lines])
    disposition_totals = Counter()
    classif_totals = Counter()

    for snap in snaps:
        rows = snap["rows"]
        is_izhs = snap["prop_class"] == "izhs"   # private houses: no MKD comparand
        bkey_ok = present_n = absent_n = apt_n = 0
        markers = Counter()
        sample_lines = []
        for row in rows:
            bk = address_to_building_key(row["street"], row["house"])
            if bk:
                bkey_ok += 1
            apt_norm = norm_house(row["apt"]) if row["apt"] else None
            if apt_norm:
                apt_n += 1
                present = f"{bk}#{apt_norm}" in reg_aptkeys if bk else False
            else:
                present = bk in reg_bkeys if bk else False
            present_n += int(bool(present))

            if row["marker_class"]:
                markers[row["marker_class"]] += 1
                disposition_totals[row["marker_class"]] += 1

            if len(sample_lines) < 4:
                sample_lines.append(
                    f"st={row['street']!r} h={row['house']!r} apt={row['apt']!r} "
                    f"bk={bk} present={present}")

            # absence is only meaningful for Mariupol-city apartment rows
            # against the apartment-level current registry. Whole-house /
            # no-apt references (private houses, or a snapshot's bare
            # building-level row) have no valid comparand there regardless
            # of outcome -- comparing them would manufacture false "absent"
            # entries for properties the registry was never tracking at
            # apartment granularity in the first place.
            comparable = (not is_izhs) and (not row.get("village")) and apt_norm is not None
            absent = comparable and (bk is not None) and (not present)
            if absent:
                absent_n += 1

            # emit a record only when it carries a story:
            #   - explicit municipal_seized / claimant marker (Layer A, any class), OR
            #   - an MKD entry that has DISAPPEARED from the current registry
            mk = row["marker_class"]
            is_evidence = (mk in ("municipal_seized", "claimant_surfaced")) or absent
            if not is_evidence:
                continue
            spine_stages = spine.get(bk, set()) if bk else set()
            classification = _classify_disappearance(mk, spine_stages)
            classif_totals[classification] += 1
            records.append({
                "snapshot": snap["filename"], "snapshot_date": snap["date"],
                "source_sha256": snap["sha256"],
                "prop_class": snap["prop_class"], "district": row["district"],
                "street": row["street"], "house": row["house"], "apt": row["apt"],
                "building_key": bk, "marker_class": mk,
                "present_in_current_registry": present,
                "absent_from_current": absent,
                "spine_stages": sorted(spine_stages),
                "classification": classification,
            })

        samples.append((snap["filename"], snap["date"], sample_lines))
        snap_diag.append({
            "snapshot": snap["filename"], "date": snap["date"],
            "prop_class": snap["prop_class"], "n_rows": len(rows),
            "bkey_ok": bkey_ok, "bkey_pct": round(100 * bkey_ok / max(1, len(rows)), 1),
            "apt_rows": apt_n, "present_in_current": present_n,
            "absent_from_current": absent_n, "markers": dict(markers),
        })

    # ── write outputs ───────────────────────────────────────────────────────
    OUT_RECORDS.parent.mkdir(parents=True, exist_ok=True)
    with OUT_RECORDS.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    summary = {
        "current_registry_rows": reg_n,
        "current_registry_building_keys": len(reg_bkeys),
        "snapshots": snap_diag,
        "disposition_marker_totals": dict(disposition_totals),
        "classification_totals": dict(classif_totals),
        "spine_building_keys_with_events": len(spine),
    }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                           encoding="utf-8")

    # ── console report ──────────────────────────────────────────────────────
    print(f"\n{'='*78}")
    print("OWNERLESS TEMPORAL DIFFERENTIAL")
    print(f"  current registry: {reg_n} rows -> {len(reg_bkeys)} building_keys, "
          f"{len(reg_aptkeys)} apt_keys")
    print(f"  spine building_keys with seizure events: {len(spine)}")
    print(f"{'='*78}")

    print("\n── SNAPSHOT PARSE + ABSENCE DIAGNOSTICS (chronological) ──")
    print(f"  {'date':11s} {'class':7s} {'rows':>6s} {'apt':>5s} "
          f"{'pres':>6s} {'absent':>7s}  file")
    for d in sorted(snap_diag, key=lambda x: x["date"]):
        print(f"  {d['date']:11s} {d['prop_class']:7s} {d['n_rows']:6d} "
              f"{d['apt_rows']:5d} {d['present_in_current']:6d} "
              f"{d['absent_from_current']:7d}  {d['snapshot'][:34]}")

    print("\n── PARSE SAMPLES (verify street/house/apt + registry match) ──")
    for fn, dt, lines in samples:
        if not lines:
            continue
        print(f"  · {dt} {fn[:40]}")
        for ln in lines[:3]:
            print(f"      {ln}")

    print("\n── DISPOSITION MARKER TOTALS (Layer A, primary evidence) ──")
    for k, v in disposition_totals.most_common():
        print(f"  {k:22s} {v:6d}   ({DISPOSITIONS[k]})")

    print("\n── DISAPPEARANCE / DISPOSITION CLASSIFICATION TOTALS (Layer B) ──")
    for k, v in classif_totals.most_common():
        print(f"  {k:26s} {v:6d}")

    print("\n── SEIZED-INTO-MUNICIPAL examples (occupation's own admission) ──")
    for r in [x for x in records if x["classification"] == "seized_municipal"][:15]:
        print(f"  {r['snapshot_date']}  {r['district'] or '?'}  "
              f"{r['street']}, {r['house']}"
              f"{('  кв.'+r['apt']) if r['apt'] else ''}  bk={r['building_key']}")

    print("\n── SEIZED-VIA-COURT buildings (absent + spine event; deduped) ──")
    seen_bk = set()
    for r in [x for x in records if x["classification"] == "seized_court"]:
        if r["building_key"] in seen_bk:
            continue
        seen_bk.add(r["building_key"])
        n_apt = sum(1 for x in records if x["classification"] == "seized_court"
                    and x["building_key"] == r["building_key"])
        print(f"  {r['snapshot_date']}  {r['street']}, {r['house']}  "
              f"({n_apt} apt)  stages={r['spine_stages']}")
        if len(seen_bk) >= 20:
            break

    print("\n── UNEXPLAINED DISAPPEARANCES (review queue) ──")
    unexpl = [x for x in records if x["classification"] == "unexplained_disappearance"]
    print(f"  {len(unexpl)} entries absent from current registry, no marker, "
          f"no spine event")
    for r in sorted(unexpl, key=lambda x: x["snapshot_date"])[:20]:
        print(f"  {r['snapshot_date']}  {r['prop_class']:6s}  {r['district'] or '?'}  "
              f"{r['street']}, {r['house']}"
              f"{('  кв.'+r['apt']) if r['apt'] else ''}")

    print(f"\n  Records → {OUT_RECORDS}  ({len(records)} rows)")
    print(f"  Summary → {OUT_SUMMARY}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
