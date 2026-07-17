"""Source 7b / geocoder #3 — Visicom Data API (api.visicom.ua).

Ukrainian commercial GIS: authoritative PRE-WAR Ukrainian street spelling
and a building-footprint dataset independent of OSM. Documented REST API
(https://api.visicom.ua/en/products/data-api), key-gated:
  * /geocode  — address/POI search near a point; returns geo_centroid + bbox
    only (no full geometry).
  * /feature/{id} — full object geometry (building footprint polygon) +
    all attributes for a given feature id, e.g. those returned by /geocode.

Exposes geocode_one() for osint.geocode Engine 2 — returns a {lat,lon,...}
dict or None (never raises; absence just means "this geocoder didn't
answer").

RUN=C: plain HTTPS + JSON, keyed, non-geoblocked — Claude-runnable. Skips
cleanly if config.VISICOM_KEY is unset.
"""
from __future__ import annotations

import logging
import time

import requests

from ... import config, forensics
from .base import SourceResult, http_headers

log = logging.getLogger(__name__)

NAME = "visicom"
RUN = "C"
NETWORK = True
DESCRIPTION = "Visicom Data API — pre-war UA spelling + building footprint (key-gated)"

BASE = "https://api.visicom.ua/data-api/5.0"

# Visicom's free-tier key returns a bare {"status":"Unauthorized"} 401 on a
# valid key intermittently — confirmed empirically (2026-07-16: 1 in 5
# identical back-to-back requests failed this way) — this is a disguised
# rate limit, not a real auth rejection. Retry with backoff before giving up.
_MAX_401_RETRIES = 3
_RETRY_BACKOFF_S = 1.5


def _get(url: str, params: dict) -> requests.Response | None:
    for attempt in range(_MAX_401_RETRIES + 1):
        try:
            r = requests.get(url, params=params, headers=http_headers(), timeout=30)
        except requests.RequestException as e:
            log.warning("visicom request failed: %s", e)
            return None
        if r.status_code == 401 and attempt < _MAX_401_RETRIES:
            log.info("visicom 401 (rate-limit, not auth) — retry %d/%d",
                     attempt + 1, _MAX_401_RETRIES)
            time.sleep(_RETRY_BACKOFF_S * (attempt + 1))
            continue
        return r
    return None


def plan(bundle) -> str:
    if not config.VISICOM_KEY:
        return "SKIP — no VISICOM_KEY in .env (free key: api.visicom.ua/en/)"
    return "geocode search near the point (uk), then /feature for matched buildings' footprints"


def _geocode(text: str, lang: str = "uk", near: str | None = None,
            radius: int | None = None, limit: int = 5) -> list[dict]:
    """Raw /geocode call. Returns the GeoJSON 'features' list (possibly
    empty). Never raises — caller treats [] and exceptions the same way."""
    if not config.VISICOM_KEY:
        return []
    params = {"text": text, "key": config.VISICOM_KEY, "limit": limit}
    if near:
        params["near"] = near
    if radius:
        params["radius"] = radius
    r = _get(f"{BASE}/{lang}/geocode.json", params)
    if r is None or not r.ok:
        if r is not None:
            log.warning("visicom geocode failed for %r: HTTP %s", text, r.status_code)
        return []
    try:
        data = r.json()
    except ValueError:
        return []
    # /geocode returns a bare Feature (not FeatureCollection) when there's a
    # single strong match — same shape quirk as /feature. Normalize.
    if data.get("type") == "FeatureCollection":
        return data.get("features", [])
    if data.get("type") == "Feature":
        return [data]
    return []


def _feature(feature_ids: list[str], lang: str = "uk") -> dict | None:
    """Raw /feature/{ids} call (up to 250 comma-joined ids). Returns the
    parsed JSON dict, or None on failure."""
    if not config.VISICOM_KEY or not feature_ids:
        return None
    ids = ",".join(feature_ids[:250])
    r = _get(f"{BASE}/{lang}/feature/{ids}.json", {"key": config.VISICOM_KEY})
    if r is None or not r.ok:
        if r is not None:
            log.warning("visicom feature lookup failed for %s: HTTP %s", ids, r.status_code)
        return None
    try:
        return r.json()
    except ValueError:
        return None


def geocode_one(address: str) -> dict | None:
    """Best-effort geocode via Visicom's Data API. Returns {lat,lon,source,
    display_name} or None. Never raises."""
    feats = _geocode(f"Маріуполь, {address}", lang="uk", limit=1)
    if not feats:
        return None
    geom = (feats[0] or {}).get("geo_centroid", {})
    coords = geom.get("coordinates")
    if not (isinstance(coords, list) and len(coords) >= 2):
        return None
    props = feats[0].get("properties", {})
    return {"lat": float(coords[1]), "lon": float(coords[0]), "source": "visicom",
            "display_name": props.get("name", "") or address}


def fetch(bundle, con, radius_m: float = 60.0) -> SourceResult:
    if not config.VISICOM_KEY:
        return SourceResult(NAME, True, "skipped — no VISICOM_KEY set "
                            "(free key: api.visicom.ua/en/)")

    findings: list[dict] = []
    captured: list[str] = []
    near = f"{bundle.lon:.6f},{bundle.lat:.6f}"

    # ── geocode search near the point, uk-language (pre-war spelling) ──────
    query_texts = sorted({v.text for v in bundle.variants if v.lang in ("ru", "ua")})[:6]
    seen_ids: set[str] = set()
    for text in query_texts:
        feats = _geocode(text, lang="uk", near=near, radius=int(radius_m), limit=5)
        if not feats:
            continue
        for f in feats:
            props = f.get("properties", {})
            fid = str(f.get("id") or props.get("id") or "")
            centroid = f.get("geo_centroid", {}).get("coordinates")
            findings.append({
                "kind": "visicom_geocode_hit",
                "query": text,
                "feature_id": fid,
                "name": props.get("name", ""),
                "categories": props.get("categories", []),
                "lat": centroid[1] if centroid else None,
                "lon": centroid[0] if centroid else None,
            })
            if fid:
                seen_ids.add(fid)

    if query_texts:
        # capture one representative raw response for the chain of custody
        r = _get(f"{BASE}/uk/geocode.json",
                {"text": query_texts[0], "key": config.VISICOM_KEY,
                 "near": near, "radius": int(radius_m), "limit": 5})
        if r is not None and r.ok:
            captured.append(forensics.capture_source(
                r.content, url=r.url, source_type="osint_visicom_geocode",
                title=f"visicom geocode {bundle.slug}",
                description=(f"Visicom /geocode near pid={bundle.pid} point "
                             f"({bundle.lat:.6f},{bundle.lon:.6f}), query={query_texts[0]!r}."),
                content_type="application/json", http_status=r.status_code, con=con,
            ))

    # ── full footprint geometry for matched building features ──────────────
    if seen_ids:
        data = _feature(sorted(seen_ids), lang="uk")
        if data is not None:
            import json
            captured.append(forensics.capture_source(
                json.dumps(data, ensure_ascii=False).encode("utf-8"),
                url=f"{BASE}/uk/feature/{','.join(sorted(seen_ids))}.json",
                source_type="osint_visicom_feature",
                title=f"visicom feature {bundle.slug}",
                description=f"Visicom /feature geometry for {len(seen_ids)} matched objects "
                            f"near pid={bundle.pid}.",
                content_type="application/json", http_status=200, con=con,
            ))
            # /feature returns a bare Feature for one id, a FeatureCollection
            # for 2+ comma-joined ids — normalize both to a list of Features.
            feats = data.get("features") if data.get("type") == "FeatureCollection" \
                else [data]
            for feat in feats:
                props = feat.get("properties", {})
                geom = feat.get("geometry", {})
                findings.append({
                    "kind": "visicom_footprint",
                    "feature_id": str(feat.get("id") or props.get("id", "")),
                    "name": props.get("name", ""),
                    "geometry_type": geom.get("type", ""),
                    "has_polygon": geom.get("type") in ("Polygon", "MultiPolygon"),
                })

    n_hits = sum(1 for f in findings if f["kind"] == "visicom_geocode_hit")
    n_foot = sum(1 for f in findings if f["kind"] == "visicom_footprint")
    return SourceResult(NAME, True,
                        f"{n_hits} geocode hits, {n_foot} footprint geometries "
                        f"({len(seen_ids)} feature ids resolved)",
                        findings, captured)
