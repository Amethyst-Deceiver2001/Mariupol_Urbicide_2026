"""Source 14 — Sentinel-2 change detection (hand-off to scripts/54-56).

10m/px optical is coarser than the Esri Wayback tiles (source 13) but has
denser temporal coverage — useful where Wayback is thin between dated
releases. This project already has a full S2 pipeline (scripts/54 build
worklist → 55 fetch pairs → 56 render chips). This module doesn't
re-implement it; it reports whether THIS property is already covered by the
existing satellite worklist and, if not, emits the command to add it — a
deliberate hand-off, since an S2 fetch is a heavier job the user runs.

RUN=U (the S2 fetch is external + slow); the check itself is local.
"""
from __future__ import annotations

import json
import logging

from ... import config
from .base import SourceResult

log = logging.getLogger(__name__)

NAME = "sentinel2"
RUN = "U"
NETWORK = False   # this module only CHECKS coverage; the fetch is scripts/55
DESCRIPTION = "Sentinel-2 change-detection coverage check + hand-off to scripts/54-56"

WORKLIST = config.DATA_DIR / "parsed" / "satellite_worklist.json"


def plan(bundle) -> str:
    return "check satellite_worklist.json for this pid; emit scripts/54-56 command if absent"


def fetch(bundle, con, radius_m: float = 0.0) -> SourceResult:
    if not WORKLIST.exists():
        return SourceResult(NAME, True,
                            "no satellite_worklist.json yet — run scripts/54 to "
                            "build one (S2 pipeline)",
                            [{"kind": "sentinel2_handoff",
                              "note": "S2 pipeline not initialized; scripts/54 builds "
                                      "the worklist, 55 fetches pairs, 56 renders chips"}])
    try:
        data = json.loads(WORKLIST.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return SourceResult(NAME, False, "satellite_worklist.json unreadable")

    entries = data if isinstance(data, list) else data.get("aois", data.get("entries", []))
    covered = False
    for e in entries if isinstance(entries, list) else []:
        # scripts/54 writes each AOI's members as a list of dicts keyed by
        # `property_id` (confirmed against the real worklist 2026-07-16).
        # The old guessed keys (member_property_ids/property_ids) never
        # matched, so coverage silently ALWAYS returned False — even for the
        # 10 properties genuinely in the worklist (e.g. pid 5865, Нахимова
        # 82), wrongly triggering a full S2 re-fetch. Read `members` first;
        # keep the old keys only as a fallback for any alternate schema.
        members = e.get("members", [])
        pids = [m.get("property_id") for m in members
                if isinstance(m, dict) and m.get("property_id") is not None]
        if not pids:
            pids = e.get("member_property_ids", []) or e.get("property_ids", [])
        if bundle.pid in pids:
            covered = True
            break

    if covered:
        return SourceResult(NAME, True, "property already in the S2 satellite worklist",
                            [{"kind": "sentinel2_covered", "pid": bundle.pid,
                              "note": "chips render via scripts/56; see data/parsed/ output"}])
    return SourceResult(NAME, True,
                        "property NOT in the S2 worklist — hand-off command emitted",
                        [{"kind": "sentinel2_handoff", "pid": bundle.pid,
                          "note": f"add pid {bundle.pid} (point {bundle.lat:.5f},"
                                  f"{bundle.lon:.5f}) to scripts/54's AOI list, then "
                                  f"run scripts/55 + 56 for 10m before/after chips"}])
