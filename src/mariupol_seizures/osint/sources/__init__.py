"""Source-module registry for the per-address OSINT sweep.

Each module exposes:
    NAME: str            — registry key / output filename stem
    RUN: str             — "C" (Claude-runnable), "U" (user terminal), "V" (VPS)
    NETWORK: bool        — touches the network at all
    DESCRIPTION: str     — one line for --plan output
    plan(bundle) -> str  — what a fetch would do (no side effects)
    fetch(bundle, con, radius_m) -> base.SourceResult

REGISTRY order is also the default execution order for `--sources all`:
local/cheap first, image sources before reverse_image (which pivots off
them), remote (U/V) sources last.
"""
from __future__ import annotations

from . import (
    archives,
    commons,
    death_records,
    eyesonrussia,
    flickr,
    google_earth_kml,
    google_imagery,
    kartaview,
    local_evidence,
    mapillary,
    osm,
    panoramax,
    pastvu,
    planet_imagery,
    planetary_computer,
    realestate_prewar,
    resale,
    reverse_image,
    sentinel2,
    telegram_channels,
    telegram_global,
    telegram_local,
    visicom,
    vk,
    wayback_tiles,
    wikidata,
    wikimapia,
    yandex_maps,
    youtube,
)

_ORDER = (
    # local, keyless, cheap
    local_evidence,
    telegram_local,
    death_records,
    # network C — keyless
    eyesonrussia,
    wikidata,
    pastvu,
    commons,
    osm,
    wayback_tiles,
    realestate_prewar,
    archives,
    panoramax,
    kartaview,
    planetary_computer,
    # network C — key-gated
    wikimapia,
    mapillary,
    flickr,
    # local manual-assist
    google_earth_kml,
    # remote (user/VPS)
    google_imagery,
    planet_imagery,
    sentinel2,
    youtube,
    telegram_channels,
    telegram_global,
    yandex_maps,
    visicom,
    vk,
    resale,
    # pivots off captured images — must run last
    reverse_image,
)

REGISTRY = {m.NAME: m for m in _ORDER}

LOCAL_ONLY = [name for name, m in REGISTRY.items() if not m.NETWORK]
CLAUDE_RUNNABLE = [name for name, m in REGISTRY.items() if m.RUN == "C"]
