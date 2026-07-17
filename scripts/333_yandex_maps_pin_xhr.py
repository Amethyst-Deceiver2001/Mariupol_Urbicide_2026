#!/usr/bin/env python3
"""Interactive diagnostic: pin the real Yandex Maps photo-layer XHR shape.

yandex_maps.py (source 10) drives the photo layer headlessly, but a passive
page load never fires the photo-data request — Yandex's photo layer only
requests photo metadata once a photo POINT/PIN is clicked. A headless
`--allow` run therefore only ever captures generic noise (layers/info,
discoveryFeed) and reliably MISSES the real endpoint. This script is not
part of the sweep — it's a one-off diagnostic you run interactively to find
the real URL, so yandex_maps.py's `_XHR_HINTS` can be corrected to actually
catch it.

Opens a VISIBLE (non-headless) browser at the photo layer for the given
point, logs EVERY network response (method/status/content-type/size/url) to
the terminal AND to a JSONL log file, and saves the body of every
JSON/plausibly-photo response to data/reports/yandex_xhr_diagnostic/ for
inspection. The browser stays open until you press Enter in the terminal —
click around the photo-layer pins/thumbnails while it's open; each click
should trigger new requests you'll see logged live.

Usage:
    PYTHONPATH=src .venv312/bin/python scripts/333_yandex_maps_pin_xhr.py \
        --lat 47.095450 --lon 37.517486
    # or
    PYTHONPATH=src .venv312/bin/python scripts/333_yandex_maps_pin_xhr.py --pid 4837

After running: look at the printed/logged URLs for anything that returned a
JSON body containing photo ids/urls/dates when you clicked a pin (NOT
layers/info or discoveryFeed, which are always-present noise). Paste that
URL pattern back so yandex_maps.py's _XHR_HINTS + parsing can be fixed to
match it for real, headless, unattended runs.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402

log = logging.getLogger(__name__)

# Always-present noise seen in a prior passive-load run — de-emphasized in
# the live log (still recorded to the JSONL) so genuinely new endpoints
# stand out when you click.
_KNOWN_NOISE = ("/layers/info", "/discoveryFeed/", "/getHomeFeed",
               ".css", ".woff", ".png", ".svg", "google-analytics",
               "mc.yandex", "yandex.ru/ads", "/favicon")


def _outdir() -> Path:
    d = config.DATA_DIR / "reports" / "yandex_xhr_diagnostic"
    d.mkdir(parents=True, exist_ok=True)
    return d


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pid", type=int, help="resolve lat/lon from this property id")
    ap.add_argument("--lat", type=float)
    ap.add_argument("--lon", type=float)
    ap.add_argument("--zoom", type=int, default=18)
    args = ap.parse_args()

    lat, lon = args.lat, args.lon
    if args.pid and (lat is None or lon is None):
        from mariupol_seizures.osint.bundle import resolve_bundle
        b = resolve_bundle(pid=args.pid)
        lat, lon = b.lat, b.lon
    if lat is None or lon is None:
        log.error("need --pid or --lat/--lon")
        sys.exit(1)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.error("playwright not installed — pip install -e '.[browser]' "
                 "&& playwright install chromium")
        sys.exit(1)

    url = (f"https://yandex.com/maps/?l=pht&ll={lon:.6f},{lat:.6f}&z={args.zoom}"
           f"&photos%5Bpoint%5D={lon:.6f},{lat:.6f}")

    out_dir = _outdir()
    log_path = out_dir / f"xhr_log_{lat:.5f}_{lon:.5f}.jsonl"
    n_saved = 0

    print(f"\n{'='*72}")
    print(f"Opening: {url}")
    print(f"Logging every response to: {log_path}")
    print(f"Bodies saved to: {out_dir}/body_*.json")
    print(f"{'='*72}")
    print("\nA browser window will open. Once the map loads:")
    print("  1. Look for photo-layer markers/pins/thumbnails on the map")
    print("  2. CLICK one")
    print("  3. Watch this terminal — new request URLs will print live")
    print("  4. Click a few more if the first doesn't look like photo data")
    print("  5. When done, come back here and press Enter to close\n")

    with open(log_path, "w", encoding="utf-8") as logf, sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        page = browser.new_page(user_agent=config.USER_AGENT)

        def _handle(resp):
            nonlocal n_saved
            try:
                u = resp.url
                ct = (resp.headers or {}).get("content-type", "")
                is_noise = any(n in u for n in _KNOWN_NOISE)
                entry = {"url": u, "status": resp.status, "content_type": ct}
                logf.write(json.dumps(entry, ensure_ascii=False) + "\n")
                logf.flush()
                if not is_noise:
                    tag = "  <-- NEW (not known noise)" if "json" in ct else ""
                    print(f"  [{resp.status}] {ct[:30]:30s} {u[:110]}{tag}")
                if "json" in ct and resp.status == 200 and not is_noise:
                    try:
                        body = resp.body()
                        if 20 < len(body) < 2_000_000:
                            n_saved += 1
                            fp = out_dir / f"body_{n_saved:03d}.json"
                            fp.write_bytes(body)
                            print(f"       -> saved {fp.name} ({len(body)} bytes)")
                    except Exception:  # noqa: BLE001
                        pass
            except Exception:  # noqa: BLE001
                pass

        page.on("response", _handle)
        page.goto(url, wait_until="networkidle", timeout=45000)
        print("(page loaded — click a photo pin now)\n")

        input(">>> Press Enter here when you're done clicking around... ")
        browser.close()

    print(f"\ndone — {n_saved} non-noise JSON bodies saved to {out_dir}/")
    print(f"full request log: {log_path}")
    print("\nInspect the saved bodies for one containing photo ids/urls/dates, "
          "then report its URL pattern back so yandex_maps.py can be fixed.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
