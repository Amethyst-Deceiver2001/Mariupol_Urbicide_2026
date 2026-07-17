#!/usr/bin/env python3
"""Diagnostic: does Yandex Maps actually RENDER the photo-layer pins in
headless Chromium, or is _photo_detail_pass's spiral-click miss (0/8 twice,
2026-07-17) actually a rendering failure, not a targeting failure?

WebGL-heavy map renderers commonly fail to draw anything under headless
Chromium (no real GPU -> software fallback or blank canvas) even though
page.goto()/networkidle succeeds and the underlying data (hotspot search)
is unaffected, since that's a separate keyless REST call with no rendering
involved.

This takes two screenshots of the exact same URL/viewport used by
_photo_detail_pass — one headless, one headed — so they can be compared by
eye. If the headless one is blank/missing pins where the headed one shows
them clearly, that confirms a headless-rendering gap (fixable only by
running headed, e.g. Xvfb, or by finding a DOM-level hit target instead of
relying on canvas pixels).

Run:
    PYTHONPATH=src .venv312/bin/python scripts/348_yandex_headless_render_check.py --pid 4837
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402
from mariupol_seizures.osint.sources.yandex_maps import (  # noqa: E402
    _DETAIL_CLICK_ZOOM, _DETAIL_VIEWPORT, _hotspot_search,
)

log = logging.getLogger(__name__)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int)
    ap.add_argument("--lat", type=float)
    ap.add_argument("--lon", type=float)
    args = ap.parse_args()

    lat, lon = args.lat, args.lon
    if args.pid and (lat is None or lon is None):
        from mariupol_seizures.osint.bundle import resolve_bundle
        b = resolve_bundle(pid=args.pid)
        lat, lon = b.lat, b.lon
    if lat is None or lon is None:
        sys.exit("need --pid or --lat/--lon")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("playwright not installed")

    from mariupol_seizures import forensics
    con = forensics.open_state()
    hotspots, _ = _hotspot_search(lat, lon, con)
    if not hotspots:
        sys.exit("no hotspots found near this point — nothing to render-check")
    hs = hotspots[0]
    h_lat, h_lon = hs["lat"], hs["lon"]
    url = f"https://yandex.com/maps/?l=pht&ll={h_lon:.6f},{h_lat:.6f}&z={_DETAIL_CLICK_ZOOM}"
    out_dir = config.DATA_DIR / "reports" / "yandex_headless_render_check"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"URL: {url}")
    print(f"Target hotspot: {hs['id']}\n")

    with sync_playwright() as pw:
        for mode, headless in (("headless", True), ("headed", False)):
            browser = pw.chromium.launch(headless=headless)
            context = browser.new_context(user_agent=config.USER_AGENT,
                                           viewport=_DETAIL_VIEWPORT)
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=45000)
            page.wait_for_timeout(2000)
            fp = out_dir / f"{mode}.png"
            page.screenshot(path=str(fp))
            print(f"[{mode}] screenshot saved: {fp}")
            # also report the WebGL renderer string — a software/SwiftShader
            # renderer confirms the no-GPU headless fallback hypothesis.
            try:
                renderer = page.evaluate("""() => {
                    const c = document.createElement('canvas');
                    const gl = c.getContext('webgl') || c.getContext('experimental-webgl');
                    if (!gl) return 'no webgl context';
                    const dbg = gl.getExtension('WEBGL_debug_renderer_info');
                    return dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
                }""")
                print(f"[{mode}] WebGL renderer: {renderer}")
            except Exception as e:  # noqa: BLE001
                print(f"[{mode}] WebGL check failed: {e}")
            browser.close()

    print(f"\nCompare {out_dir}/headless.png vs headed.png — "
         "if headless is blank/missing the pin cluster the headed one shows, "
         "that's the root cause (not click targeting).")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
