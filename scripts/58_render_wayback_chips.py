#!/usr/bin/env python3
"""Render a side-by-side before/during/after/now comparison page for the
high-resolution Esri World Imagery Wayback mosaics fetched by script 57
(data/parsed/wayback_manifest.json).

For each AOI, copies the four dated mosaics (prewar / post_siege / cleared /
current) into data/reports/wayback_chips/, reads each mosaic's .meta.json
sidecar for its per-release attribution string, and writes
data/reports/wayback_chips/index.html with a members table (address, RD4U
category, destruction %, households displaced, seizure_event row count) and
the four chips with release-date/offset/resolution captions.

This script is local/offline (reads mosaics already fetched by script 57).
"""
import json
import logging
import math
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402

log = logging.getLogger("render_wayback_chips")

MANIFEST_PATH = config.DATA_DIR / "parsed" / "wayback_manifest.json"
REPORTS_DIR = config.PROJECT_ROOT / "data" / "reports"
CHIPS_DIR = REPORTS_DIR / "wayback_chips"

LABEL_TITLES = {
    "prewar": "Before (prewar)",
    "post_siege": "During (post-siege damage)",
    "cleared": "After (cleared)",
    "current": "Now",
}

DASH = "—"


def resolution_m_per_px(zoom: int, lat: float) -> float:
    return 156543.03392 * math.cos(math.radians(lat)) / (2 ** zoom)


def html_escape(value) -> str:
    if value is None:
        return ""
    text = str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def bbox_center(bbox: list[float]) -> tuple[float, float]:
    min_lon, min_lat, max_lon, max_lat = bbox
    return (min_lat + max_lat) / 2.0, (min_lon + max_lon) / 2.0


def render_members_table(members: list[dict]) -> tuple[str, int]:
    rows = []
    n_zero_seizure = 0
    for m in members:
        if m["n_seizure_events"] == 0:
            n_zero_seizure += 1
        addr = m["occupation_address"]
        if m.get("prewar_address") and m["prewar_address"] != addr:
            addr = f"{m['prewar_address']} (occ: {addr})"
        rd4u = m.get("rd4u_category") or DASH
        destruction = m["destruction_pct"]
        destruction_str = f"{destruction:.0f}%" if destruction is not None else DASH
        households = m["households_displaced"]
        households_str = str(households) if households is not None else DASH
        seizure_cls = ' class="flag"' if m["n_seizure_events"] == 0 else ""
        rows.append(
            "<tr>"
            f"<td>{html_escape(m['property_id'])}</td>"
            f"<td>{html_escape(addr)}</td>"
            f"<td>{html_escape(rd4u)}</td>"
            f"<td>{html_escape(destruction_str)}</td>"
            f"<td>{html_escape(households_str)}</td>"
            f"<td{seizure_cls}>{m['n_seizure_events']}</td>"
            "</tr>"
        )
    return "".join(rows), n_zero_seizure


def render_chip(aoi_id: str, entry: dict, resolution: float) -> str:
    label = entry["label"]
    src_path = config.PROJECT_ROOT / entry["mosaic_path"]
    dst_name = f"{aoi_id}__{label}.png"
    dst_path = CHIPS_DIR / dst_name
    shutil.copy2(src_path, dst_path)

    meta_path = config.PROJECT_ROOT / f"{entry['mosaic_path']}.meta.json"
    attribution = ""
    if meta_path.exists():
        with open(meta_path, encoding="utf-8") as f:
            attribution = json.load(f).get("attribution", "")

    release_date = date.fromisoformat(entry["release_date"])
    target_date = date.fromisoformat(entry["target_date"])
    offset_days = abs((release_date - target_date).days)
    width, height = entry["mosaic_size"]

    title = LABEL_TITLES.get(label, label)
    caption = (
        f"Esri World Imagery release <strong>{entry['release_date']}</strong> "
        f"(target {entry['target_date']}, offset {offset_days}d) "
        f"&mdash; zoom {entry['zoom']} (&asymp;{resolution:.2f} m/px), "
        f"{width}&times;{height}px"
    )

    log.info(
        "%s/%s -> %s (%dx%d, release %s, offset %dd)",
        aoi_id, label, dst_name, width, height, entry["release_date"], offset_days,
    )

    return (
        '<div class="chip">'
        f'<div class="chip-label">{html_escape(title)}</div>'
        f'<a href="{dst_name}" target="_blank">'
        f'<img src="{dst_name}" width="{width}" height="{height}" loading="lazy" /></a>'
        f'<div class="chip-caption">{caption}</div>'
        f'<div class="chip-attribution">{html_escape(attribution)}</div>'
        '</div>'
    )


def render_aoi(aoi: dict) -> str:
    lat, _lon = bbox_center(aoi["bbox"])
    resolution = resolution_m_per_px(aoi["zoom"], lat)

    member_rows, n_zero_seizure = render_members_table(aoi["members"])

    gap_note = ""
    if aoi["members"] and n_zero_seizure == len(aoi["members"]):
        gap_note = (
            '<p class="gap-note">⚠ None of the '
            f"{n_zero_seizure} properties in this AOI have any "
            "<code>seizure_event</code> (court) records "
            "&mdash; possible district-coverage gap (this block sits in the "
            "Ordzhonikidzevsky / Left Bank district near Azovstal, outside the "
            "4 saturated district courts).</p>"
        )

    chips = "".join(render_chip(aoi["aoi_id"], entry, resolution) for entry in aoi["entries"])

    return f"""
<section class="aoi">
  <h2>{html_escape(aoi['title'])}</h2>
  {gap_note}
  <table class="members">
    <thead><tr>
      <th>id</th><th>address</th><th>RD4U</th><th>destruction</th>
      <th>households displaced</th><th>seizure_event rows</th>
    </tr></thead>
    <tbody>{member_rows}</tbody>
  </table>
  <div class="chips">{chips}</div>
</section>
"""


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    CHIPS_DIR.mkdir(parents=True, exist_ok=True)

    with open(MANIFEST_PATH, encoding="utf-8") as f:
        manifest = json.load(f)

    sections = "".join(render_aoi(aoi) for aoi in manifest["aois"])

    index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Wayback high-resolution before/after chips</title>
<style>
body {{ font-family: sans-serif; margin: 2em; max-width: 1400px; }}
h1 {{ font-size: 1.4em; }}
section.aoi {{ border-top: 2px solid #ccc; padding: 1em 0; }}
table.members {{ border-collapse: collapse; font-size: 0.85em; margin: 0.5em 0 1em; }}
table.members th, table.members td {{ border: 1px solid #ccc; padding: 0.25em 0.5em; text-align: left; }}
td.flag {{ background: #fee; color: #b00; font-weight: bold; }}
.gap-note {{ background: #fee; border: 1px solid #b00; padding: 0.5em; font-size: 0.9em; }}
.chips {{ display: flex; flex-wrap: wrap; gap: 1em; margin: 1em 0; }}
.chip {{ text-align: center; max-width: 380px; }}
.chip img {{ max-width: 380px; width: 100%; border: 1px solid #999; }}
.chip-label {{ font-weight: bold; font-size: 0.9em; }}
.chip-caption {{ font-size: 0.78em; color: #555; margin-top: 0.25em; }}
.chip-attribution {{ font-size: 0.7em; color: #999; margin-top: 0.15em; }}
</style>
</head>
<body>
<h1>Wayback (Esri World Imagery) high-resolution before/after chips</h1>
<p>Source: <a href="https://www.arcgis.com/home/item.html?id=10df2279f9684e4a9f6a7f08febac2a9">Esri
World Imagery Wayback</a> &mdash; a free, public archive of ~194 dated releases
(2014-present) of Esri's World Imagery basemap, served as standard z/x/y JPEG
tiles (no API key, no VPS needed). Each panel below shows the Wayback release
closest to its target date among releases with full tile coverage for this AOI
at the given zoom (date offsets noted under each image). Siege ended
~2022-05-20: per project owner, no new kinetic damage to structures after that
date, so any post_siege&rarr;cleared&rarr;current change is administrative
(demolition / reconstruction), not combat. Click any image to open it
full-size.</p>
{sections}
</body>
</html>
"""
    index_path = CHIPS_DIR / "index.html"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)
    log.info("Wrote %s", index_path)


if __name__ == "__main__":
    main()
