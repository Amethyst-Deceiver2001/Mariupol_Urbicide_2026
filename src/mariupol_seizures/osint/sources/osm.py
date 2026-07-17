"""Source 7 — OpenStreetMap: current footprint/tags (Overpass), full tag/
geometry HISTORY (ohsome), and OSM Notes near the point.

The history angle is the evidentiary one: a building deleted from OSM or
retagged (`demolished:building`, addr change) after 2022 is a dated,
independently-timestamped destruction/renaming signal.
"""
from __future__ import annotations

import datetime as _dt
import json
import logging
import time

import requests

from ... import forensics
from .base import SourceResult, http_headers

log = logging.getLogger(__name__)

NAME = "osm"
RUN = "C"
NETWORK = True
DESCRIPTION = "Overpass footprint/tags + ohsome full history + OSM Notes"

OVERPASS = "https://overpass-api.de/api/interpreter"
OHSOME = "https://api.ohsome.org/v1/elementsFullHistory/geometry"
NOTES = "https://api.openstreetmap.org/api/0.6/notes.json"
PAD_DEG = 0.0007   # ≈ 60-70m


def plan(bundle) -> str:
    return "Overpass around:40m buildings; ohsome 2020->today history; Notes bbox"


def fetch(bundle, con, radius_m: float = 40.0) -> SourceResult:
    findings: list[dict] = []
    captured: list[str] = []
    lat, lon = bundle.lat, bundle.lon
    bbox = (lon - PAD_DEG, lat - PAD_DEG, lon + PAD_DEG, lat + PAD_DEG)

    # ── Overpass: current buildings around the point ───────────────────────
    q = (f'[out:json][timeout:30];('
         f'way(around:{int(radius_m)},{lat},{lon})["building"];'
         f'relation(around:{int(radius_m)},{lat},{lon})["building"];'
         f');out tags center geom;')
    try:
        for attempt in range(2):
            r = requests.post(OVERPASS, data={"data": q}, headers=http_headers(),
                              timeout=60)
            if r.status_code == 504 and attempt == 0:
                # Overpass's public instance 504s under transient load;
                # one retry clears it almost always (no query change needed).
                log.warning("overpass 504, retrying once")
                time.sleep(3.0)
                continue
            break
        r.raise_for_status()
        captured.append(forensics.capture_source(
            r.content, url=f"{OVERPASS}#around{int(radius_m)}m@{lat:.6f},{lon:.6f}",
            source_type="osint_osm_overpass",
            title=f"overpass buildings {bundle.slug}",
            description=f"Overpass building query around pid={bundle.pid}.",
            content_type="application/json", http_status=r.status_code, con=con,
        ))
        for el in r.json().get("elements", []):
            tags = el.get("tags", {})
            geom = el.get("geometry") or []
            findings.append({
                "kind": "osm_building",
                "osm_id": f'{el.get("type","way")}/{el.get("id")}',
                "tags": {k: tags[k] for k in sorted(tags) if k.startswith(
                    ("addr:", "building", "name", "start_date", "demolished"))},
                "footprint": [[p["lat"], p["lon"]] for p in geom][:80],
            })
    except requests.RequestException as e:
        log.warning("overpass failed: %s", e)
        findings.append({"kind": "error", "stage": "overpass", "error": str(e)})

    # ── ohsome: full history in a small bbox ───────────────────────────────
    # ohsome's osh-data snapshot lags "today" by weeks (its /metadata endpoint
    # advertises the true upper bound) — requesting past that bound 404s the
    # whole call. Ask metadata first and clamp to it rather than hardcoding
    # a guessed cutoff that will silently go stale again.
    ohsome_end = _dt.date.today().isoformat()
    try:
        meta = requests.get("https://api.ohsome.org/v1/metadata",
                            headers=http_headers(), timeout=30)
        meta.raise_for_status()
        to_ts = meta.json()["extractRegion"]["temporalExtent"]["toTimestamp"]
        ohsome_end = to_ts[:10]
    except Exception:  # noqa: BLE001
        log.warning("ohsome metadata fetch failed, using today() as end date "
                    "(may 404 if the snapshot lags)", exc_info=True)
    try:
        r = requests.post(OHSOME, data={
            "bboxes": ",".join(f"{v:.6f}" for v in bbox),
            "time": f"2020-01-01,{ohsome_end}",
            "filter": "building=* or demolished:building=*",
            "properties": "tags,metadata",
        }, headers=http_headers(), timeout=120)
        r.raise_for_status()
        captured.append(forensics.capture_source(
            r.content, url=f"{OHSOME}#bbox{bbox}",
            source_type="osint_osm_ohsome_history",
            title=f"ohsome history {bundle.slug}",
            description=f"OSM full history 2020->{ohsome_end} around pid={bundle.pid}.",
            content_type="application/json", http_status=r.status_code, con=con,
        ))
        hist: dict[str, dict] = {}
        n_dropped_transient = 0
        for feat in r.json().get("features", []):
            # /elementsFullHistory/geometry returns the geometry AS-CLIPPED
            # to the query bbox for each version — so a way whose geometry
            # was briefly vandalism-edited onto our coordinates genuinely
            # has a version that "intersects" (confirmed 2026-07-16: a
            # York, UK building's way appeared in a Mariupol bbox query
            # this way — its geometry sat on our coordinates for ~80
            # minutes in 2024-06 before being reverted). A geometry check
            # alone can't catch this since the clipped geometry IS local.
            # Filter on version DURATION instead: a real address/building
            # edit persists; a sub-day version is drive-by vandalism noise
            # regardless of where it geographically lands.
            p = feat.get("properties", {})
            vf_raw, vt_raw = p.get("@validFrom"), p.get("@validTo")
            try:
                from datetime import datetime as _dtm
                dur_h = ((_dtm.fromisoformat(vt_raw.replace("Z", "+00:00"))
                         - _dtm.fromisoformat(vf_raw.replace("Z", "+00:00")))
                        .total_seconds() / 3600) if (vf_raw and vt_raw) else 999
            except (ValueError, AttributeError):
                dur_h = 999
            if dur_h < 24:
                n_dropped_transient += 1
                continue
            oid = p.get("@osmId", "?")
            h = hist.setdefault(oid, {"kind": "osm_history", "osm_id": oid,
                                      "n_versions": 0, "first": None, "last": None,
                                      "tag_events": []})
            h["n_versions"] += 1
            h["first"] = min(filter(None, [h["first"], vf_raw]), default=vf_raw)
            h["last"] = max(filter(None, [h["last"], vt_raw]), default=vt_raw)
            for k in ("demolished:building", "razed:building", "was:building"):
                if p.get(k):
                    h["tag_events"].append({"at": vf_raw, "tag": f"{k}={p[k]}"})
            addr = {k: v for k, v in p.items() if k.startswith("addr:")}
            if addr and (not h["tag_events"] or h["tag_events"][-1].get("addr") != addr):
                h["tag_events"].append({"at": vf_raw, "addr": addr})
        # keep tag_events short
        for h in hist.values():
            h["tag_events"] = h["tag_events"][:12]
        findings.extend(hist.values())
        if n_dropped_transient:
            findings.append({"kind": "osm_history_dropped", "count": n_dropped_transient,
                             "note": "dropped: version valid <24h — drive-by/"
                                     "vandalism edit noise, not a real change"})
    except requests.RequestException as e:
        log.warning("ohsome failed: %s", e)
        findings.append({"kind": "error", "stage": "ohsome", "error": str(e)})

    # ── Notes ──────────────────────────────────────────────────────────────
    try:
        r = requests.get(NOTES, params={"bbox": ",".join(f"{v:.6f}" for v in bbox)},
                         headers=http_headers(), timeout=45)
        r.raise_for_status()
        notes = r.json().get("features", [])
        if notes:
            captured.append(forensics.capture_source(
                r.content, url=r.url,
                source_type="osint_osm_notes",
                title=f"osm notes {bundle.slug}",
                description=f"OSM Notes around pid={bundle.pid}.",
                content_type="application/json", http_status=r.status_code, con=con,
            ))
        for n in notes:
            p = n.get("properties", {})
            comments = p.get("comments", [])
            findings.append({
                "kind": "osm_note",
                "url": p.get("url", ""),
                "status": p.get("status"),
                "created": p.get("date_created", "")[:10],
                "first_comment": (comments[0].get("text", "")[:200]
                                  if comments else ""),
            })
    except requests.RequestException as e:
        log.warning("notes failed: %s", e)

    n_b = sum(1 for f in findings if f["kind"] == "osm_building")
    n_h = sum(1 for f in findings if f["kind"] == "osm_history")
    n_n = sum(1 for f in findings if f["kind"] == "osm_note")
    return SourceResult(NAME, True,
                        f"{n_b} buildings, {n_h} history objects, {n_n} notes",
                        findings, captured)
