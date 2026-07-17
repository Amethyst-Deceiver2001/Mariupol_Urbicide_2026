"""Source 12 — Google Earth Pro KML placemark (manual-assist, no network).

Google Earth Pro's free desktop app has a historical-imagery time slider
that no public API exposes. This module emits a per-address .kml placemark
(point + a small footprint box) into the sweep dir, so the user can open it
in Earth Pro and scrub the address through every dated satellite pass by
hand — the richest free historical-imagery source there is, just not
automatable. Pure local file generation.
"""
from __future__ import annotations

import logging

from ... import config
from .base import SourceResult

log = logging.getLogger(__name__)

NAME = "google_earth_kml"
RUN = "C"
NETWORK = False
DESCRIPTION = "emit a Google Earth Pro .kml placemark for the historical time-slider"

PAD_DEG = 0.00035  # ≈ 30m box half-width


def plan(bundle) -> str:
    return "write <slug>.kml placemark + footprint box to the sweep dir"


def _kml(bundle) -> str:
    lat, lon = bundle.lat, bundle.lon
    name = bundle.occupation_address or bundle.prewar_address or bundle.slug
    box = [
        (lon - PAD_DEG, lat - PAD_DEG), (lon + PAD_DEG, lat - PAD_DEG),
        (lon + PAD_DEG, lat + PAD_DEG), (lon - PAD_DEG, lat + PAD_DEG),
        (lon - PAD_DEG, lat - PAD_DEG),
    ]
    ring = " ".join(f"{x:.7f},{y:.7f},0" for x, y in box)
    desc = (f"pid={bundle.pid}; building_id={bundle.building_id}; "
            f"prewar={bundle.prewar_address or '?'}. Open in Google Earth Pro "
            f"and use the historical-imagery time slider to scrub this footprint "
            f"through every dated satellite pass (2015-present).")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{name}</name>
    <Placemark>
      <name>{name}</name>
      <description>{desc}</description>
      <Point><coordinates>{lon:.7f},{lat:.7f},0</coordinates></Point>
    </Placemark>
    <Placemark>
      <name>{name} — footprint box (~60m)</name>
      <Style><LineStyle><color>ff00aaff</color><width>2</width></LineStyle>
        <PolyStyle><fill>0</fill></PolyStyle></Style>
      <Polygon><outerBoundaryIs><LinearRing>
        <coordinates>{ring}</coordinates>
      </LinearRing></outerBoundaryIs></Polygon>
    </Placemark>
  </Document>
</kml>
"""


def fetch(bundle, con, radius_m: float = 0.0) -> SourceResult:
    out_dir = config.DATA_DIR / "reports" / "osint" / bundle.slug
    out_dir.mkdir(parents=True, exist_ok=True)
    kml_path = out_dir / f"{bundle.slug}.kml"
    kml_path.write_text(_kml(bundle), encoding="utf-8")
    return SourceResult(
        NAME, True, f"wrote {kml_path.name} — open in Google Earth Pro (time slider)",
        [{"kind": "google_earth_kml", "path": str(kml_path),
          "note": "historical-imagery time slider is manual; open the .kml in "
                  "Earth Pro desktop"}])
