#!/usr/bin/env python3
"""
scripts/73_backfill_eisghs_addresses.py
---------------------------------------
Patch the `address` field for ЕИСЖС objects whose API address is generic
("г. Мариуполь" only).  Sources used, in priority order:

  1. RPD project_title_in_pdf  — extract street after "по адресу: … Мариуполь," or
     "по {pref} {street}, {num}" patterns.
  2. land_order_match.address_normalized — only when it is a simple
     "streettype name, number" form (skip territorial descriptions).
  3. Manual overrides dict — for residual cases resolved outside the pipeline.

Writes a patched copy to data/parsed/eisghs_mariupol_objects.jsonl in-place
(original backed up to eisghs_mariupol_objects.jsonl.pre73).

Prints a report of every change made and every object left unresolved.
"""
import json
import logging
import re
import shutil
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
JSONL = ROOT / "data" / "parsed" / "eisghs_mariupol_objects.jsonl"

# ── regex helpers ────────────────────────────────────────────────────────────

# Detect generic city-only address
_GENERIC = re.compile(r"^г\.?\s*мариуполь[,\s]*$", re.I)

# After "по адресу: ... Мариуполь," — grab rest of address (stop at RPD/area noise)
_AFTER_MARIUPOL = re.compile(
    r"(?:г(?:ород(?:ской округ)?)?\.?\s*Мариуполь[ля]?[,\s]+)([\w\s.,\-/\"«»№]+)",
    re.I | re.UNICODE,
)

# "по пр. Строителей, 74" / "по проспекту Строителей 80"
_BY_STREET = re.compile(
    r"по\s+"
    r"(пр-?кт\.?|пр\.?|проспекту|ул\.?|улице|б-?р\.?|бульвару|пер\.?|переулку|набережной|пл\.?|площади)\s+"
    r"([\w\s\-]+?)"          # street name
    r"[,\s]+(\d+[\w/]*)"     # house number
    r"(?:\s+в\s+г\.?\s*Мариуполь|\s*$)",
    re.I | re.UNICODE,
)

# Simple "streettype name, number" in land-order address_normalized
_SIMPLE_LO = re.compile(
    r"^(улица|проспект|бульвар|переулок|площадь|набережная|улица|пр-?кт)\s+([\w\s\-]+?),\s*(\d+[\w/]*)$",
    re.I | re.UNICODE,
)

# Street-type abbreviation normaliser
_STREET_ABBREV = {
    "пр-кт": "пр-кт", "пр-т": "пр-кт", "пр.": "пр-кт", "пр": "пр-кт",
    "проспекту": "пр-кт", "проспект": "пр-кт",
    "ул.": "ул", "ул": "ул", "улице": "ул", "улица": "ул",
    "б-р": "б-р", "б-р.": "б-р", "бульвару": "б-р", "бульвар": "б-р",
    "пер.": "пер", "пер": "пер", "переулку": "пер", "переулок": "пер",
    "пл.": "пл", "пл": "пл", "площади": "пл", "площадь": "пл",
    "набережной": "наб", "набережная": "наб",
}


def _norm_type(raw: str) -> str:
    return _STREET_ABBREV.get(raw.lower().rstrip("."), raw.lower())


def _fmt(street_type: str, name: str, house: str | None) -> str:
    t = _norm_type(street_type)
    n = name.strip().rstrip(",").strip()
    if house:
        return f"г. Мариуполь, {t} {n}, д. {house.strip()}"
    return f"г. Мариуполь, {t} {n}"


# ── extraction functions ─────────────────────────────────────────────────────

def _from_rpd_title(title: str) -> str | None:
    """Try to extract a street address from the RPD project title."""
    if not title:
        return None

    # Pattern 1: "по пр. Строителей, 74 в г. Мариуполь"
    m = _BY_STREET.search(title)
    if m:
        return _fmt(m.group(1), m.group(2), m.group(3))

    # Pattern 2: "по адресу: … г. Мариуполь, ул. Латышева"
    m = _AFTER_MARIUPOL.search(title)
    if m:
        tail = m.group(1).strip().rstrip(".")
        # Reject pure noise
        if re.search(r"(ЗУ\d|жилой блок|Литер|зона\s+\d|кварт)", tail, re.I):
            return None
        # If it has a recognisable street prefix, clean it up
        sm = re.match(
            r"(ул\.?|пр-?кт\.?|пр\.?|б-?р\.?|пер\.?|пл\.?|наб\.?)\s+([\w\s\-]+?)(?:,\s*(\d+[\w/]*))?$",
            tail, re.I | re.UNICODE,
        )
        if sm:
            return _fmt(sm.group(1), sm.group(2), sm.group(3))
        # Bare street name without type prefix — return as-is with city prefix
        if len(tail) > 3 and not re.search(r"\d", tail):
            return f"г. Мариуполь, {tail}"

    return None


def _from_lo_addr(addr: str) -> str | None:
    """Use land_order address_normalized if it is a simple street+number."""
    if not addr:
        return None
    m = _SIMPLE_LO.match(addr.strip())
    if m:
        return _fmt(m.group(1), m.group(2), m.group(3))
    return None


# ── manual overrides (eisghs_id → address string) ───────────────────────────
# Add entries here after manual map lookups for Category-B objects.
MANUAL_OVERRIDES: dict[int, str] = {
    # e.g. 67323: "г. Мариуполь, ул Примерная, д. 5",
}


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    objects = [json.loads(l) for l in JSONL.read_text(encoding="utf-8").splitlines() if l.strip()]

    patched = 0
    unresolved = []

    for obj in objects:
        addr = (obj.get("address") or "").strip()
        if not _GENERIC.match(addr):
            continue  # already has a specific address

        eid = obj["eisghs_id"]

        # 1. Manual override
        if eid in MANUAL_OVERRIDES:
            new_addr = MANUAL_OVERRIDES[eid]
            source = "manual_override"

        else:
            rpd = obj.get("rpd_cadastral_match") or {}
            lo  = obj.get("land_order_match") or {}

            # 2. RPD title
            new_addr = _from_rpd_title(rpd.get("project_title_in_pdf") or "")
            source = "rpd_title"

            # 3. Land-order address_normalized
            if not new_addr:
                new_addr = _from_lo_addr(lo.get("address_normalized") or "")
                source = "land_order_addr"

        if new_addr:
            # Remove redundant "г. Мариуполь, город Мариуполь," prefix if doubled
            new_addr = re.sub(
                r"^г\.\s*Мариуполь,\s*город\s*Мариуполь,\s*",
                "г. Мариуполь, ",
                new_addr,
                flags=re.I,
            )
            log.info(
                "PATCH id=%-6s  %-50s  ← %s",
                eid, new_addr, source,
            )
            obj["address"] = new_addr
            obj.setdefault("flags", [])
            if "address_backfilled" not in obj["flags"]:
                obj["flags"].append("address_backfilled")
            patched += 1
        else:
            unresolved.append(obj)

    # Back up original
    backup = JSONL.with_suffix(".jsonl.pre73")
    shutil.copy2(JSONL, backup)
    log.info("backup → %s", backup)

    # Write patched file
    JSONL.write_text(
        "\n".join(json.dumps(o, ensure_ascii=False) for o in objects) + "\n",
        encoding="utf-8",
    )
    log.info("wrote %d objects (%d patched)", len(objects), patched)

    # ── Unresolved (Category B) report ──────────────────────────────────────
    print("\n=== CATEGORY B — no address recoverable from pipeline data ===")
    print("%-8s %-28s %-20s %-10s %-18s  coords" % (
        "ID", "nameObj", "developer", "status", "RPD num"))
    print("-" * 110)
    for obj in sorted(unresolved, key=lambda x: x["eisghs_id"]):
        rpd = obj.get("rpd_cadastral_match") or {}
        rpd_num = rpd.get("rpd_num_in_pdf") or obj.get("rpd_num") or "—"
        lat = obj.get("lat") or "?"
        lon = obj.get("lon") or "?"
        print("%-8s %-28s %-20s %-10s %-18s  %.4f, %.4f" % (
            obj["eisghs_id"],
            (obj.get("nameObj") or "—")[:28],
            (obj.get("dev_name_short") or "—")[:20],
            (obj.get("obj_status_desc") or "—")[:10],
            rpd_num[:18],
            float(lat), float(lon),
        ))
    print("\nTotal unresolved: %d" % len(unresolved))


if __name__ == "__main__":
    main()
