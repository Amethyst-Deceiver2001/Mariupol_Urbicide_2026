#!/usr/bin/env python3
"""Render human-review chips for the wave-1 satellite manifest
(data/parsed/satellite_manifest.json, built by script 55).

For each AOI x window with status="ok", reads the small windowed Sentinel-2
"visual" (TCI, true-colour uint8) clip, upsamples it ~8x with nearest-neighbour
(no interpolation -- we are NOT inventing detail, just making 10m pixels
visible) and writes a PNG chip. Builds:
  - data/reports/satellite_chips/index.html -- one section per AOI, chips for
    T0..T3 side by side with date/cloud-cover/expected-state captions, so a
    human reviewer can see the siege-end-anchored before/after sequence.
  - data/reports/satellite_chips/verdict_template.csv -- one row per
    (AOI, property, claim) for the reviewer to fill in:
    verdict in {confirms, refutes, indeterminate}, confidence (0-1),
    observed_start, observed_end, notes. This feeds script 57 (not yet
    written), which will turn filled-in verdicts into `corroboration` rows.

This script is local/offline (reads clips already fetched by script 55).
"""
import csv
import json
import logging
import sys
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402

log = logging.getLogger("render_review_chips")

MANIFEST_PATH = config.DATA_DIR / "parsed" / "satellite_worklist.json"
SAT_MANIFEST_PATH = config.DATA_DIR / "parsed" / "satellite_manifest.json"
REPORTS_DIR = config.PROJECT_ROOT / "data" / "reports"
CHIPS_DIR = REPORTS_DIR / "satellite_chips"

UPSAMPLE = 8
WINDOW_ORDER = ["T0", "T1", "T2", "T3"]

# One review claim per property role, matched against the AOI's windows.
CLAIM_TEMPLATES = {
    "demolished": (
        "Building at {address} (property {property_id}): T0 shows it intact; "
        "T1 (post-siege, no new kinetic damage after 2022-05-20) shows war "
        "damage consistent with destruction_pct={destruction_pct}; T2 shows "
        "the footprint cleared. Does the image sequence support "
        "'building destroyed by war, then demolished/cleared'?"
    ),
    "rebuilt": (
        "Parcel at {address} (property {property_id}, project "
        "{project_name}, developer {developer}): T2 shows a cleared lot; T3 "
        "(from land_order_date={land_order_date}, status={obj_status}) "
        "should show {t3_expectation}. Does the image sequence support "
        "'new construction on the cleared footprint'?"
    ),
}


def render_chip(clip_path: Path, out_path: Path) -> tuple[int, int]:
    with rasterio.open(clip_path) as src:
        data = src.read()  # (bands, H, W) uint8
    rgb = np.transpose(data, (1, 2, 0))  # (H, W, bands)
    rgb = np.repeat(np.repeat(rgb, UPSAMPLE, axis=0), UPSAMPLE, axis=1)
    img = Image.fromarray(rgb, mode="RGB")
    img.save(out_path)
    return img.width, img.height


def build_claims(aoi: dict, entries_by_window: dict) -> list[dict]:
    claims = []
    for member in aoi["members"]:
        role = member["role"]
        if role == "demolished":
            claims.append(
                {
                    "aoi_id": aoi["aoi_id"],
                    "property_id": member["property_id"],
                    "role": role,
                    "claim": CLAIM_TEMPLATES["demolished"].format(
                        address=member["occupation_address"],
                        property_id=member["property_id"],
                        destruction_pct=member["destruction_pct"],
                    ),
                    "verdict": "",
                    "confidence": "",
                    "observed_start": "",
                    "observed_end": "",
                    "notes": "",
                }
            )
        elif role == "rebuilt":
            det = member["reallocation_detail"] or {}
            if det.get("commissioned_dt"):
                t3_expectation = f"a finished building (commissioned {det['commissioned_dt']})"
            else:
                t3_expectation = "construction activity (foundation/frame/cranes)"
            claims.append(
                {
                    "aoi_id": aoi["aoi_id"],
                    "property_id": member["property_id"],
                    "role": role,
                    "claim": CLAIM_TEMPLATES["rebuilt"].format(
                        address=member["occupation_address"],
                        property_id=member["property_id"],
                        project_name=det.get("project_name", "?"),
                        developer=det.get("developer", "?"),
                        land_order_date=det.get("land_order_date", "?"),
                        obj_status=det.get("obj_status", "?"),
                        t3_expectation=t3_expectation,
                    ),
                    "verdict": "",
                    "confidence": "",
                    "observed_start": "",
                    "observed_end": "",
                    "notes": "",
                }
            )
    return claims


def html_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    CHIPS_DIR.mkdir(parents=True, exist_ok=True)

    with open(MANIFEST_PATH, encoding="utf-8") as f:
        worklist = json.load(f)
    with open(SAT_MANIFEST_PATH, encoding="utf-8") as f:
        manifest = json.load(f)

    entries_by_aoi: dict[str, dict[str, dict]] = {}
    for e in manifest["entries"]:
        entries_by_aoi.setdefault(e["aoi_id"], {})[e["window_label"]] = e

    html_sections = []
    all_claims: list[dict] = []

    for aoi in worklist["aois"]:
        entries_by_window = entries_by_aoi.get(aoi["aoi_id"], {})
        members_desc = "; ".join(
            f"{m['occupation_address']} (id={m['property_id']}, {m['role']})"
            for m in aoi["members"]
        )

        chip_cells = []
        for label in WINDOW_ORDER:
            entry = entries_by_window.get(label)
            window = next((w for w in aoi["windows"] if w["label"] == label), None)
            if entry is None or window is None:
                continue
            if entry["status"] != "ok":
                chip_cells.append(
                    f'<div class="chip"><div class="chip-label">{label}: NO SCENE FOUND</div></div>'
                )
                continue
            clip_path = config.PROJECT_ROOT / entry["clip_path"]
            png_name = f"{aoi['aoi_id']}__{label}.png"
            png_path = CHIPS_DIR / png_name
            w, h = render_chip(clip_path, png_path)
            cloud = entry.get("eo_cloud_cover")
            cloud_str = f"{cloud:.1f}%" if cloud is not None else "?"
            chip_cells.append(
                f'<div class="chip">'
                f'<div class="chip-label">{label} &mdash; {entry["item_datetime"][:10]} '
                f'(cloud {cloud_str})</div>'
                f'<img src="{png_name}" width="{w}" height="{h}" />'
                f'<div class="chip-caption">{html_escape(window["expected_state"])}</div>'
                f'</div>'
            )
            log.info("%s/%s -> %s (%dx%d)", aoi["aoi_id"], label, png_name, w, h)

        claims = build_claims(aoi, entries_by_window)
        all_claims.extend(claims)
        claim_items = "".join(f"<li>{html_escape(c['claim'])}</li>" for c in claims)

        html_sections.append(
            f"""
<section class="aoi">
  <h2>{html_escape(aoi['title'])} <span class="tier">[tier {aoi['tier']}]</span></h2>
  <p class="rationale">{html_escape(aoi['rationale'])}</p>
  <p class="members">{html_escape(members_desc)}</p>
  <div class="chips">{''.join(chip_cells)}</div>
  <ul class="claims">{claim_items}</ul>
</section>
"""
        )

    index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Wave-1 satellite review chips</title>
<style>
body {{ font-family: sans-serif; margin: 2em; max-width: 1100px; }}
h1 {{ font-size: 1.4em; }}
section.aoi {{ border-top: 2px solid #ccc; padding: 1em 0; }}
.tier {{ color: #888; font-weight: normal; font-size: 0.8em; }}
.rationale, .members {{ color: #444; font-size: 0.9em; }}
.chips {{ display: flex; flex-wrap: wrap; gap: 1em; margin: 1em 0; }}
.chip {{ text-align: center; }}
.chip img {{ image-rendering: pixelated; border: 1px solid #999; }}
.chip-label {{ font-weight: bold; font-size: 0.85em; }}
.chip-caption {{ max-width: 260px; font-size: 0.8em; color: #555; }}
ul.claims {{ font-size: 0.9em; }}
</style>
</head>
<body>
<h1>Wave-1 satellite review chips ({manifest['generated_at']})</h1>
<p>Siege ended ~{worklist['siege_end']}: per project owner, no new kinetic
damage to structures after that date. Any T1&rarr;T2 or T2&rarr;T3 change is
therefore administrative (demolition / construction), not combat.
Images are Sentinel-2 L2A true-colour (10m/px), upsampled {UPSAMPLE}x with
nearest-neighbour (pixelated on purpose -- no detail invented).</p>
{''.join(html_sections)}
</body>
</html>
"""
    index_path = CHIPS_DIR / "index.html"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)
    log.info("Wrote %s", index_path)

    csv_path = CHIPS_DIR / "verdict_template.csv"
    fieldnames = [
        "aoi_id", "property_id", "role", "claim",
        "verdict", "confidence", "observed_start", "observed_end", "notes",
    ]
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_claims)
    log.info("Wrote %s (%d claim rows)", csv_path, len(all_claims))


if __name__ == "__main__":
    main()
