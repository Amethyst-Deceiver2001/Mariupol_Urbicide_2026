#!/usr/bin/env python3
"""Parse the captured mariupoldestruction.com victims TSV (scripts/407,
sha256 f6a2a3b9...) for the Levoberezhny quarter bounded by Lomizova/50 let
Oktyabrya(Meotidy)/Azovstalskaya/Komsomolsky-Morskoy -- identified 2026-07-21
as a candidate "demolish-and-abandon" case study: a fully razed, never-
rebuilt block (confirmed by the user via cadastral map + satellite pairs)
carrying an unusually dense civilian-casualty record.

Matches each row's residence/death-place/burial-place text against the
quarter's four streets (Meotidy and 50 let Oktyabrya are the same boulevard
under two names on this stretch -- alias confirmed this session via a
cadastral-map cross-check; Morskoy and Komsomolsky bulvar are likewise the
same boulevard, confirmed by geocoding both names' house numbers onto the
same coordinate range), extracts the house number, and resolves it against
the property spine restricted to a bounding box built from properties
already confirmed in-quarter (scripts/402/403/405/406 loads).

A 25-row manual spot-check of this extraction (2026-07-21) found zero false
address matches, and every row's cited source (mostly t.me/mariupolRIP/<id>)
traced to an identifiable post -- several independently rediscovered via a
parallel manual sweep of the mariupolRIP corpus earlier the same session.

Groups the resolved rows by building (matching the civilian_casualty
`deceased`-list pattern already used for the Lomizova 1 five-person record,
scripts/403) rather than one row per person -- at 196 records across 48
buildings, per-person rows would fragment the evidence past readability.
"без вести" (б/в) / "без вести пропал" (б/п) rows are kept as a distinct
`status: missing` entry, not conflated with confirmed deaths.

Output: data/parsed/levoberezhny_quarter_casualties.jsonl, one row per
building, for scripts/409 to load.
"""
import csv
import json
import logging
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import psycopg2  # noqa: E402
from mariupol_seizures import config  # noqa: E402

log = logging.getLogger(__name__)

TSV_SHA = "f6a2a3b9ad4b39cb207405382ee8ef2068cfbc983282a63f9f6f1d61665119cd"
OUT_PATH = ROOT / "data" / "parsed" / "levoberezhny_quarter_casualties.jsonl"

BOX_LON = (37.6262 - 0.0025, 37.6352 + 0.0025)
BOX_LAT = (47.0989 - 0.0018, 47.1033 + 0.0018)

STREET_PATTERNS = [
    (re.compile(r"ломизов", re.I), "STREET:ломизова"),
    (re.compile(r"50\s*лет\s*окт", re.I), "BOULEVARD:50 лет октября"),
    (re.compile(r"меотид", re.I), "BOULEVARD:50 лет октября"),
    (re.compile(r"азовстальск", re.I), "STREET:азовстальская"),
    (re.compile(r"комсомольск", re.I), "BOULEVARD:комсомольский"),
    (re.compile(r"морск", re.I), "BOULEVARD:комсомольский"),
]

HOUSE_RE = re.compile(r"(?:д\.?\s*|дом\s*)?(\d+)(?:[/\-][\dа-я]+)?", re.I)

MISSING_STATUSES = ("б/в", "б/п", "Б/п", "Б/в")


def find_raw_path(sha: str) -> Path:
    con = sqlite3.connect(ROOT / "data" / "state.sqlite")
    row = con.execute(
        "SELECT raw_path FROM source_document WHERE sha256=?", (sha,)
    ).fetchone()
    con.close()
    if not row:
        raise SystemExit(f"sha {sha} not found in state.sqlite -- run scripts/407 first")
    return Path(row[0])


def extract_house(text: str, start_idx: int) -> str | None:
    tail = text[start_idx:start_idx + 40]
    m = HOUSE_RE.search(tail)
    return m.group(1) if m else None


def main() -> None:
    tsv_path = find_raw_path(TSV_SHA)

    conn = psycopg2.connect(config.DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        SELECT building_id, ST_X(geom), ST_Y(geom) FROM property
        WHERE building_id LIKE 'STREET:ломизова|%'
           OR building_id LIKE 'BOULEVARD:50 лет октября|%'
           OR building_id LIKE 'STREET:азовстальская|%'
           OR building_id LIKE 'BOULEVARD:комсомольский|%'
    """)
    spine = {bid: (lon, lat) for bid, lon, lat in cur.fetchall()}
    conn.close()

    def resolve(prefix: str, house: str | None):
        if not house:
            return None
        bid = f"{prefix}|{house}"
        coords = spine.get(bid)
        if not coords or coords[0] is None:
            return None
        lon, lat = coords
        if (BOX_LON[0] <= lon <= BOX_LON[1]) and (BOX_LAT[0] <= lat <= BOX_LAT[1]):
            return bid
        return None

    buildings: dict[str, list[dict]] = {}
    n_total = 0
    with open(tsv_path, encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        next(reader)  # header
        for r in reader:
            if len(r) < 9:
                r = r + [""] * (9 - len(r))
            status, name, dob, dod, cause, residence, death_place, burial_place, source = r[:9]
            notes = r[9] if len(r) > 9 else ""
            if not name.strip():
                continue
            combined = " ".join([residence, death_place, burial_place, notes])
            for pat, prefix in STREET_PATTERNS:
                m = pat.search(combined)
                if not m:
                    continue
                house = extract_house(combined, m.end())
                bid = resolve(prefix, house)
                if not bid:
                    break
                n_total += 1
                buildings.setdefault(bid, []).append({
                    "name": name.strip(),
                    "dob": dob.strip() or None,
                    "dod": dod.strip() or None,
                    "cause": cause.strip() or None,
                    "residence": residence.strip() or None,
                    "death_place": death_place.strip() or None,
                    "burial_place": burial_place.strip() or None,
                    "notes": notes.strip() or None,
                    "status": "missing" if status.strip().lower().startswith(MISSING_STATUSES) else "deceased",
                    "source_url": source.strip() or None,
                })
                break

    with open(OUT_PATH, "w", encoding="utf-8") as out:
        for bid, deceased in sorted(buildings.items()):
            out.write(json.dumps({
                "building_id": bid,
                "deceased": deceased,
                "n_deceased": sum(1 for d in deceased if d["status"] == "deceased"),
                "n_missing": sum(1 for d in deceased if d["status"] == "missing"),
            }, ensure_ascii=False) + "\n")

    log.info("=== %d buildings, %d total records -> %s ===", len(buildings), n_total, OUT_PATH)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
