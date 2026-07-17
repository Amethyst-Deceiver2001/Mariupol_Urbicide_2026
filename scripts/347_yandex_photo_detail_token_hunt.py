#!/usr/bin/env python3
"""Interactive diagnostic: find the REAL credential(s) the getById full-
photo-detail endpoint needs, closing the open follow-up left in
yandex_maps.py's _photo_detail_pass (source 10 — the hotspot search itself
is validated/working; only the full-photo-detail pull is not).

WHY THE CURRENT CODE FAILS (diagnosed 2026-07-17 by re-reading
_photo_detail_pass): it loads the bare map page HEADLESSLY (no click, no
interaction), then regexes the static page.content() HTML for a literal
`"csrfToken":"..."` substring and fires a raw API GET with that value. This
was ALWAYS going to fail two different ways:
  1. scripts/333's own diagnostic (2026-07-16) already showed a
     token-less/wrong-token request just gets ECHOED a fresh token back
     instead of erroring — i.e. what's grepped out of static HTML is very
     likely a page-level anti-forgery SEED, not a credential the getById
     API itself will accept.
  2. Even a correct token value might be part of a double-submit-cookie
     CSRF scheme — needing a specific session COOKIE to be present
     alongside it, freshly minted by whatever XHR the frontend fires when a
     photo pin is actually clicked. A headless page.goto() with no click
     never triggers that XHR at all, so no such cookie/token pair is ever
     established.

Neither problem can be fixed by reading static HTML harder — both require
watching a REAL click-through happen. This script opens a visible browser,
lets you click an actual photo pin AND open its full-size viewer, and logs
THREE things scripts/333 never captured:
  1. Full REQUEST headers (not just response headers) for any XHR whose URL
     contains "photo" — catches a header-based token/session scheme.
  2. The full cookie jar at the moment of that request — catches a
     double-submit-cookie scheme.
  3. window-level JS state matching /csrf|token/i via page.evaluate() —
     catches a token minted into client-side state (React/Redux/etc.) that
     never appears in server-rendered HTML at all.

Usage:
    PYTHONPATH=src .venv312/bin/python scripts/347_yandex_photo_detail_token_hunt.py --pid 4837
    PYTHONPATH=src .venv312/bin/python scripts/347_yandex_photo_detail_token_hunt.py --lat 47.095450 --lon 37.517486

When the browser opens: click a photo-layer pin, then click again to open
the FULL photo viewer (not just the pin marker) — the getById-style request
most likely fires at THAT second click, not the first. Click a couple more
photos if the first doesn't show anything promising, then press Enter here.

After running: inspect the printed request log + saved
data/reports/yandex_photo_token_hunt/*.json for the request that actually
returned real photo data (image URL, uploader, date — not a
{"csrfToken":...} stub). Report back its full URL, headers, and whether a
specific cookie was present, so yandex_maps.py's _photo_detail_pass can be
rewritten to replicate the real flow instead of guessing at static HTML.
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

_NOISE = ("/layers/info", "/discoveryFeed/", "/getHomeFeed", ".css", ".woff",
          ".png", ".svg", "google-analytics", "mc.yandex", "yandex.ru/ads",
          "/favicon", ".jpg", ".webp")


def _outdir() -> Path:
    d = config.DATA_DIR / "reports" / "yandex_photo_token_hunt"
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

    url = f"https://yandex.com/maps/?l=pht&ll={lon:.6f},{lat:.6f}&z={args.zoom}"
    out_dir = _outdir()
    req_log_path = out_dir / f"requests_{lat:.5f}_{lon:.5f}.jsonl"
    n_saved = 0

    print(f"\n{'='*72}")
    print(f"Opening: {url}")
    print(f"Request log: {req_log_path}")
    print(f"Response bodies + JS-state dumps: {out_dir}/")
    print(f"{'='*72}")
    print("\nOnce the map loads:")
    print("  1. Find a photo-layer marker/pin near the point")
    print("  2. Click it, THEN click again to open the FULL photo viewer")
    print("     (the real getById-style request most likely fires on that")
    print("     SECOND click, opening the photo — not the first pin click)")
    print("  3. Try 2-3 different photos if the first shows nothing new")
    print("  4. Come back here and press Enter when done\n")

    with open(req_log_path, "w", encoding="utf-8") as reqlog, sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context(user_agent=config.USER_AGENT)
        page = context.new_page()

        def _on_request(req):
            try:
                u = req.url
                if any(n in u for n in _NOISE):
                    return
                if "photo" not in u.lower() and "getbyid" not in u.lower():
                    return
                entry = {
                    "url": u, "method": req.method,
                    "headers": dict(req.headers),
                }
                reqlog.write(json.dumps(entry, ensure_ascii=False) + "\n")
                reqlog.flush()
                print(f"  >>> REQUEST [{req.method}] {u[:130]}")
                for hk, hv in req.headers.items():
                    if any(t in hk.lower() for t in ("cookie", "csrf", "token", "auth")):
                        print(f"        header {hk}: {hv[:100]}")
            except Exception:  # noqa: BLE001
                pass

        def _on_response(resp):
            nonlocal n_saved
            try:
                u = resp.url
                if any(n in u for n in _NOISE):
                    return
                if "photo" not in u.lower() and "getbyid" not in u.lower():
                    return
                ct = (resp.headers or {}).get("content-type", "")
                print(f"  <<< RESPONSE [{resp.status}] {ct[:30]:30s} {u[:110]}")
                if "json" in ct and resp.status == 200:
                    body = resp.body()
                    if 10 < len(body) < 2_000_000:
                        n_saved += 1
                        fp = out_dir / f"body_{n_saved:03d}.json"
                        fp.write_bytes(body)
                        is_stub = body.strip().startswith(b'{"csrfToken"')
                        print(f"       -> saved {fp.name} ({len(body)} bytes)"
                             f"{' *** TOKEN STUB, not real data' if is_stub else ' *** LOOKS REAL — inspect this one'}")
            except Exception:  # noqa: BLE001
                pass

        page.on("request", _on_request)
        page.on("response", _on_response)
        page.goto(url, wait_until="networkidle", timeout=45000)
        print("(page loaded — click a photo pin, then open the full photo)\n")

        input(">>> Press Enter here when you're done clicking around... ")

        # snapshot cookies + any JS-state token/csrf globals at the end,
        # after whatever interaction happened
        cookies = context.cookies()
        interesting_cookies = [c for c in cookies
                               if any(t in c["name"].lower() for t in ("csrf", "token", "session", "yandexuid"))]
        (out_dir / "cookies.json").write_text(
            json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n{len(cookies)} total cookies saved to cookies.json "
             f"({len(interesting_cookies)} look token/session-related):")
        for c in interesting_cookies:
            print(f"  {c['name']} = {c['value'][:60]}")

        try:
            js_state = page.evaluate("""() => {
                const hits = {};
                const walk = (obj, path, depth) => {
                    if (depth > 3 || obj === null || typeof obj !== 'object') return;
                    for (const k of Object.keys(obj)) {
                        try {
                            if (/csrf|token/i.test(k) && typeof obj[k] !== 'object') {
                                hits[path + '.' + k] = String(obj[k]).slice(0, 100);
                            }
                        } catch (e) {}
                    }
                };
                try { walk(window, 'window', 0); } catch (e) {}
                return hits;
            }""")
            (out_dir / "js_state.json").write_text(
                json.dumps(js_state, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"\n{len(js_state)} window-level csrf/token-like key(s) found "
                 f"(saved js_state.json):")
            for k, v in js_state.items():
                print(f"  {k} = {v}")
        except Exception as e:  # noqa: BLE001
            print(f"\n(js_state dump failed: {e})")

        browser.close()

    print(f"\ndone — {n_saved} response bodies saved, request log: {req_log_path}")
    print("\nReport back: which body_NNN.json (if any) looks like REAL photo data "
         "(not a csrfToken stub), its matching request's headers/cookies from "
         "the log above, and any promising js_state.json entries.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
