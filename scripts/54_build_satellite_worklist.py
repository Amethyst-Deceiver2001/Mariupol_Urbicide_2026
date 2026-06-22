#!/usr/bin/env python3
"""Build the Tier-3 satellite worklist for the first ("start small") batch of
high-confidence demolition / demolish-rebuild candidates.

See docs/tier3_corroboration_design.md (S2) for the full design. This is a
*curated* wave-1 worklist, not a citywide query: 10 properties / 7 AOIs,
chosen for (a) 100% (or near-100%) destruction in the Russian federal damage
tracker, (b) an exact-coordinate match (<=10m) to a reallocation/new-build
parcel where one exists, and (c) geographic/temporal spread otherwise.

Key evidentiary anchor (per project owner, 2026-06-12): the siege of Mariupol
effectively ended ~20 May 2022; no new *kinetic* damage to structures occurred
after that date. Any change visible between a clear satellite scene taken on
or after 1 June 2022 and a later scene is therefore administrative
(demolition / construction), not combat -- this is what lets a 10m Sentinel-2
pixel grid carry legal weight despite its coarseness.

Window labels:
  T0 - pre-war baseline      (2021-01-01 .. 2022-02-23, day before invasion)
  T1 - post-siege, pre-clear (2022-06-01 .. demolition event_date - 1 day)
  T2 - post-demolition       (demolition event_date + 30 days .. today)
  T3 - current / post-reallocation (land_order_date .. today; Tier A only)

This script is local/offline (DB read + JSON write only -- no network).
Output: data/parsed/satellite_worklist.json
"""
import json
import logging
import math
import sys
from datetime import date
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402

log = logging.getLogger("satellite_worklist")

OUT_PATH = config.DATA_DIR / "parsed" / "satellite_worklist.json"

SIEGE_END = date(2022, 5, 20)
T1_START = date(2022, 6, 1)
T0_START = date(2021, 1, 1)
T0_END = date(2022, 2, 23)  # day before the full-scale invasion
TODAY = date(2026, 6, 12)

# AOI bbox half-extent for single-building AOIs (metres). At ~300x300m a
# 9-storey slab (~80-100m footprint) occupies a recognisable block of pixels
# at 10m GSD, with enough surrounding context (street grid, neighbouring
# buildings) to orient the reviewer. See "resolution honesty" in the design
# doc -- we are not claiming sub-building precision.
SINGLE_MARGIN_M = 150.0
# Extra margin (metres) added around the bbox spanning all member points of a
# multi-building AOI (Tier C).
CLUSTER_MARGIN_M = 75.0

# ---------------------------------------------------------------------------
# Curated wave-1 candidates
# ---------------------------------------------------------------------------
# tier A: demolished building <-> reallocated/new-build parcel, exact-coordinate
#         match (<=10m, verified 2026-06-12). 3-4 window timeline (T0-T3).
# tier B: demolished building only, no known reallocation yet. T0-T2.
# tier C: a cluster of demolished buildings sharing one AOI, to demonstrate
#         scale (one image, several razed apartment blocks). T0-T2.
AOI_DEFS = [
    {
        "aoi_id": "nakhimova_82_chernomorsky_1b",
        "tier": "A",
        "title": "просп. Нахимова 82 -> пер. Черноморский 1Б (flagship)",
        "rationale": (
            "The documented address-laundering flagship "
            "(docs/case_studies/nakhimova_82_chernomorsky_1b.md). 100% "
            "destruction per damage tracker, demolished 2022-09-29; "
            "ЕИСЖС-commissioned 2023-12-29 (СЗ-1 ПОРФИР, 51 apartments). "
            "Geocodes 10.3m apart."
        ),
        "members": [
            {"property_id": 5865, "role": "demolished"},
            {"property_id": 6333, "role": "rebuilt"},
        ],
    },
    {
        "aoi_id": "artema_150_metallurgov_1",
        "tier": "A",
        "title": "ул. Артема 150 (вул. Архипа Куїнджі 150) -> пр-кт Металлургов 1 / "
                 "ЖК \"Ленинградский квартал\"",
        "rationale": (
            "NEW pairing identified 2026-06-12 (not yet in any case study). "
            "100% destruction, demolished 2022-09-29; land granted "
            "2023-09-07 to СЗ СУ-2007 for a 17-floor / 255-flat tower "
            "(eisghs_id 68872, under_construction). Geocodes 8.0m apart."
        ),
        "members": [
            {"property_id": 4741, "role": "demolished"},
            {"property_id": 6341, "role": "rebuilt"},
        ],
    },
    {
        "aoi_id": "kuprina_69_lazurnye_berega",
        "tier": "A",
        "title": "ул. Куприна 69 -> ул. Куприна / ЖК \"Лазурные берега\"",
        "rationale": (
            "NEW pairing identified 2026-06-12 (not yet in any case study). "
            "100% destruction, demolished 2022-09-19; land granted "
            "2024-11-18 to СЗ СИРИУС БИЛД for a 10-floor / 86-flat building "
            "(eisghs_id 66292, under_construction). Geocodes 5.3m apart."
        ),
        "members": [
            {"property_id": 4947, "role": "demolished"},
            {"property_id": 6336, "role": "rebuilt"},
        ],
    },
    {
        "aoi_id": "solnechnaya_3",
        "tier": "B",
        "title": "ул. Солнечная 3",
        "rationale": (
            "100% destruction, demolished 2022-08-09 -- the EARLIEST dated "
            "demolition in the cohort. No confirmed reallocation match yet "
            "(nearest ЖК \"Кленовая Аллея\" parcel is ~199m away -- too far "
            "to claim identity; flagged for S4 footprint follow-up, not "
            "paired here)."
        ),
        "members": [
            {"property_id": 4970, "role": "demolished"},
        ],
    },
    {
        "aoi_id": "geroicheskaya_29",
        "tier": "B",
        "title": "ул. Героическая 29",
        "rationale": (
            "100% destruction, demolished 2022-08-27. Geographically "
            "distinct (Левобережный/NE Mariupol, ~6.4 km from the Нахимова "
            "cluster) -- tests the pipeline outside the Zhovtnevy/Ilyichivsk "
            "core."
        ),
        "members": [
            {"property_id": 5640, "role": "demolished"},
        ],
    },
    {
        "aoi_id": "nakhimova_64",
        "tier": "B",
        "title": "просп. Нахимова 64",
        "rationale": (
            "100% destruction, demolished 2022-09-29 -- same demolition "
            "wave as the Нахимова 82 flagship (~250m away) but with NO "
            "reallocation event yet: a 'cleared, not (yet) rebuilt' "
            "contrast case alongside AOI nakhimova_82_chernomorsky_1b."
        ),
        "members": [
            {"property_id": 5858, "role": "demolished"},
        ],
    },
    {
        "aoi_id": "mira_106_108_110_112_cluster",
        "tier": "C",
        "title": "просп. Миру (Ленина) 106 / 108 / 110 / 112 -- 4-building cleared block",
        "rationale": (
            "All four 100% destruction, all demolished 2022-09-29, all "
            "within ~150m of each other -- a single AOI should show FOUR "
            "razed apartment blocks disappearing at once, demonstrating the "
            "scale of the demolition wave in one image."
        ),
        "members": [
            {"property_id": 4419, "role": "demolished"},
            {"property_id": 4421, "role": "demolished"},
            {"property_id": 4423, "role": "demolished"},
            {"property_id": 4426, "role": "demolished"},
        ],
    },
]


def meters_to_deg(lat: float, dx_m: float, dy_m: float) -> tuple[float, float]:
    """Convert a (dx, dy) metre offset at latitude `lat` to (dlon, dlat)."""
    dlat = dy_m / 111_320.0
    dlon = dx_m / (111_320.0 * math.cos(math.radians(lat)))
    return dlon, dlat


def fetch_property_info(cur, property_id: int) -> dict:
    cur.execute(
        """
        SELECT id, prewar_address, occupation_address, ST_X(geom), ST_Y(geom),
               rd4u_category,
               (SELECT min(event_date) FROM seizure_event
                 WHERE property_id=p.id AND stage='demolition') AS demo_date,
               (SELECT max((c.detail->>'destruction_pct')::numeric)
                  FROM corroboration c
                 WHERE c.property_id=p.id AND c.kind='mirror_source') AS destruction_pct,
               (SELECT detail FROM seizure_event
                 WHERE property_id=p.id AND stage='reallocation' LIMIT 1) AS realloc_detail,
               (SELECT min(event_date) FROM seizure_event
                 WHERE property_id=p.id AND stage='reallocation') AS realloc_date
        FROM property p WHERE p.id = %s
        """,
        (property_id,),
    )
    row = cur.fetchone()
    if row is None:
        raise SystemExit(f"property_id {property_id} not found")
    (pid, prewar, occ, lon, lat, rd4u, demo_date, pct, realloc_detail, realloc_date) = row
    return {
        "property_id": pid,
        "prewar_address": prewar,
        "occupation_address": occ,
        "lon": lon,
        "lat": lat,
        "rd4u_category": rd4u,
        "demolition_date": demo_date.isoformat() if demo_date else None,
        "destruction_pct": float(pct) if pct is not None else None,
        "reallocation_date": realloc_date.isoformat() if realloc_date else None,
        "reallocation_detail": realloc_detail,
    }


def iso(d: date) -> str:
    return d.isoformat()


def build_windows(aoi: dict, members_info: list[dict]) -> list[dict]:
    """Construct the T0/T1/T2/[T3] date windows for one AOI."""
    demo_dates = [
        date.fromisoformat(m["demolition_date"])
        for m in members_info
        if m["demolition_date"]
    ]
    realloc_members = [m for m in members_info if m["reallocation_detail"]]

    windows = [
        {
            "label": "T0",
            "expected_state": "pre-war: building(s) intact",
            "date_from": iso(T0_START),
            "date_to": iso(T0_END),
        }
    ]

    if demo_dates:
        demo_date = min(demo_dates)
        t1_end = demo_date  # exclusive in the search step
        if t1_end <= T1_START:
            t1_end = date(T1_START.year, T1_START.month, T1_START.day + 1)
        windows.append(
            {
                "label": "T1",
                "expected_state": (
                    "post-siege, pre-demolition: building(s) standing but "
                    f"war-damaged ({_pct_summary(members_info)})"
                ),
                "date_from": iso(T1_START),
                "date_to": iso(t1_end),
            }
        )
        t2_start = _add_days(demo_date, 30)
        windows.append(
            {
                "label": "T2",
                "expected_state": "post-demolition: building(s) gone / cleared lot",
                "date_from": iso(t2_start),
                "date_to": iso(TODAY),
            }
        )

    if realloc_members:
        land_order_dates = [
            m["reallocation_detail"].get("land_order_date")
            for m in realloc_members
            if m["reallocation_detail"].get("land_order_date")
        ]
        t3_start = (
            min(date.fromisoformat(d) for d in land_order_dates)
            if land_order_dates
            else (max(demo_dates) if demo_dates else T1_START)
        )
        statuses = {
            m["reallocation_detail"].get("obj_status") for m in realloc_members
        }
        commissioned = [
            m["reallocation_detail"].get("commissioned_dt")
            for m in realloc_members
            if m["reallocation_detail"].get("commissioned_dt")
        ]
        if commissioned:
            expected = (
                "current / post-reallocation: NEW building commissioned "
                f"({min(commissioned)}) -- finished structure expected"
            )
        else:
            expected = (
                "current / post-reallocation: site under construction "
                f"(status={'/'.join(sorted(statuses))}) -- cleared lot with "
                "construction activity (foundation/cranes/frame) expected, "
                "not yet a finished building"
            )
        windows.append(
            {
                "label": "T3",
                "expected_state": expected,
                "date_from": iso(t3_start),
                "date_to": iso(TODAY),
            }
        )

    return windows


def _pct_summary(members_info: list[dict]) -> str:
    pcts = [m["destruction_pct"] for m in members_info if m["destruction_pct"] is not None]
    if not pcts:
        return "destruction % unknown"
    if len(pcts) == 1 or min(pcts) == max(pcts):
        return f"{pcts[0]:.0f}% destruction per damage tracker"
    return f"{min(pcts):.0f}-{max(pcts):.0f}% destruction per damage tracker"


def _add_days(d: date, n: int) -> date:
    from datetime import timedelta
    return d + timedelta(days=n)


def build_bbox(members_info: list[dict], tier: str) -> dict:
    lons = [m["lon"] for m in members_info]
    lats = [m["lat"] for m in members_info]
    center_lat = sum(lats) / len(lats)

    if tier == "C":
        margin_m = CLUSTER_MARGIN_M
        dlon_margin, dlat_margin = meters_to_deg(center_lat, margin_m, margin_m)
        min_lon, max_lon = min(lons) - dlon_margin, max(lons) + dlon_margin
        min_lat, max_lat = min(lats) - dlat_margin, max(lats) + dlat_margin
    else:
        center_lon = sum(lons) / len(lons)
        dlon, dlat = meters_to_deg(center_lat, SINGLE_MARGIN_M, SINGLE_MARGIN_M)
        min_lon, max_lon = center_lon - dlon, center_lon + dlon
        min_lat, max_lat = center_lat - dlat, center_lat + dlat

    return {
        "min_lon": round(min_lon, 6),
        "min_lat": round(min_lat, 6),
        "max_lon": round(max_lon, 6),
        "max_lat": round(max_lat, 6),
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    conn = psycopg2.connect(config.DATABASE_URL)
    cur = conn.cursor()

    worklist = {
        "generated_at": TODAY.isoformat(),
        "siege_end": SIEGE_END.isoformat(),
        "note": (
            "Wave 1 (curated, 'start small'): 10 properties / 7 AOIs. "
            "Per project owner: no new kinetic damage to structures after "
            "the siege ended (~2022-05-20); any T1->T2 or T2->T3 change is "
            "therefore administrative (demolition/construction), not combat."
        ),
        "aois": [],
    }

    for aoi in AOI_DEFS:
        members_info = [fetch_property_info(cur, m["property_id"]) for m in aoi["members"]]
        for m_info, m_def in zip(members_info, aoi["members"]):
            m_info["role"] = m_def["role"]

        bbox = build_bbox(members_info, aoi["tier"])
        windows = build_windows(aoi, members_info)

        log.info(
            "%s (tier %s): %d member(s), bbox=%.4f,%.4f,%.4f,%.4f, %d window(s)",
            aoi["aoi_id"], aoi["tier"], len(members_info),
            bbox["min_lon"], bbox["min_lat"], bbox["max_lon"], bbox["max_lat"],
            len(windows),
        )

        worklist["aois"].append(
            {
                "aoi_id": aoi["aoi_id"],
                "tier": aoi["tier"],
                "title": aoi["title"],
                "rationale": aoi["rationale"],
                "bbox": bbox,
                "members": members_info,
                "windows": windows,
            }
        )

    conn.close()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(worklist, f, ensure_ascii=False, indent=2)
    log.info("Wrote %s (%d AOIs)", OUT_PATH, len(worklist["aois"]))


if __name__ == "__main__":
    main()
