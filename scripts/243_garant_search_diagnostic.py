#!/usr/bin/env python3
"""One-shot diagnostic: scripts/242's search-box selector guess
(`input[name="text"]`) matched the wrong widget -- it landed on a generic
"Система ГАРАНТ" product-locator search ("Например, ндс на товары с
маркетплейсов") instead of base.garant.ru's own document search. This script
doesn't guess -- it dumps every <input>/<button> on the real homepage plus a
full-page screenshot, so the correct selector can be picked by inspection
instead of another trial-and-error round.

I (Claude) have no outbound network access from this sandbox, so I can't
browse the live page myself -- this script's output (console dump + the
screenshot file) is what lets me pick the real selector once you run it and
share the result.

Run:
    PYTHONPATH=src .venv312/bin/python3 scripts/243_garant_search_diagnostic.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
log = logging.getLogger(__name__)

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    log.error("playwright not installed. Run: .venv312/bin/pip install -e '.[browser]' && "
              ".venv312/bin/playwright install chromium")
    sys.exit(1)

OUT_DIR = ROOT / "data" / "raw"
OUT_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOT_PATH = OUT_DIR / "_debug_garant_homepage.png"
DUMP_PATH = OUT_DIR / "_debug_garant_inputs.txt"


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale="ru-RU", user_agent=config.USER_AGENT, viewport={"width": 1366, "height": 900},
        )
        page = context.new_page()
        log.info("Navigating to https://base.garant.ru/")
        page.goto("https://base.garant.ru/", timeout=30000, wait_until="networkidle")

        # Dump every input/button with its useful attributes.
        lines = []
        inputs = page.locator("input").all()
        lines.append(f"=== {len(inputs)} <input> elements ===")
        for i, inp in enumerate(inputs):
            try:
                attrs = page.eval_on_selector(
                    f"input >> nth={i}",
                    "el => ({name: el.name, id: el.id, type: el.type, "
                    "placeholder: el.placeholder, className: el.className, "
                    "visible: el.offsetParent !== null})",
                )
            except Exception as e:
                attrs = {"error": str(e)}
            lines.append(f"[{i}] {attrs}")

        buttons = page.locator("button").all()
        lines.append(f"\n=== {len(buttons)} <button> elements (first 20) ===")
        for i, btn in enumerate(buttons[:20]):
            try:
                attrs = page.eval_on_selector(
                    f"button >> nth={i}",
                    "el => ({id: el.id, className: el.className, text: "
                    "el.textContent.trim().slice(0,60), visible: el.offsetParent !== null})",
                )
            except Exception as e:
                attrs = {"error": str(e)}
            lines.append(f"[{i}] {attrs}")

        dump = "\n".join(lines)
        DUMP_PATH.write_text(dump, encoding="utf-8")
        log.info("Input/button dump written to %s", DUMP_PATH)
        print(dump)

        page.screenshot(path=str(SCREENSHOT_PATH), full_page=False)
        log.info("Screenshot saved to %s", SCREENSHOT_PATH)

        # The selector matched fine in scripts/242's run, but the captured
        # "results" were suspiciously small/generic -- run one real query and
        # see what actually happens: where does it navigate, what renders.
        try:
            form_info = page.eval_on_selector(
                'input[name="text"]',
                "el => { const f = el.closest('form'); return f ? "
                "{action: f.action, method: f.method} : {action: null, method: null}; }",
            )
            log.info("Enclosing <form>: %s", form_info)
        except Exception as e:
            log.warning("Could not read enclosing form: %s", e)

        log.info("Running one test query: 'Указ 307 Донецкая Народная Республика'")
        box = page.locator('input[name="text"]').first
        box.click()
        box.fill("Указ 307 Донецкая Народная Республика")
        box.press("Enter")
        try:
            page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            log.warning("networkidle timeout -- capturing current state anyway")
        log.info("URL after submit: %s", page.url)

        # First run's screenshot showed a spinner still active -- this SPA
        # likely keeps a connection open (websocket/long-poll) so networkidle
        # fires before real results render. Poll for the spinner to clear
        # instead of trusting networkidle alone.
        for i in range(6):
            page.wait_for_timeout(3000)
            spinner_visible = page.locator(
                "svg, .spinner, [class*='load' i], [class*='spin' i]"
            ).first.is_visible() if page.locator(
                "svg, .spinner, [class*='load' i], [class*='spin' i]"
            ).count() else False
            body_text_len = len(page.inner_text("body"))
            log.info("  poll %d/6: spinner_visible=%s body_text_len=%d", i + 1, spinner_visible, body_text_len)

        results_shot = OUT_DIR / "_debug_garant_results.png"
        page.screenshot(path=str(results_shot), full_page=False)
        log.info("Results screenshot saved to %s", results_shot)
        results_html_path = OUT_DIR / "_debug_garant_results.html"
        results_html_path.write_text(page.content(), encoding="utf-8")
        log.info("Results HTML saved to %s (%d bytes)", results_html_path, len(page.content()))
        log.info("Visible body text (first 1000 chars): %r", page.inner_text("body")[:1000])

        browser.close()

    log.info("Done. Share the printed dump above (or the two files at %s / %s) "
             "and the real search selector can be picked from it.", DUMP_PATH, SCREENSHOT_PATH)


if __name__ == "__main__":
    main()
