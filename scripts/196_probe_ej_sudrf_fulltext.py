#!/usr/bin/env python3
"""Discovery probe (progress_report_2026-06.md §5 item 9 / pre_petition_sourcing.md
§4-5): does ej.sudrf.ru -- the federal "электронное правосудие" full-text
search portal, separate from the per-court GAS «Правосудие» docket-card
pages already crawled -- expose full judicial-act texts per case? If yes,
this is the only known path to closing the address gap on the 2,657+
court-record islands (docket cards carry no address field at all, see
court_islands_address_gap memory / pre_petition_sourcing.md §4).

This is NOT a build-ready crawler -- the form structure, search parameters,
and whether особое-производство rulings (which name private individuals) are
published here at all are all unknown. Two phases:

  PHASE 1 (this run, always). Fetch the base portal page
  (https://ej.sudrf.ru/?fromOa=93RS0006 -- court code for Жовтневый районный
  суд г. Мариуполя, the court explicitly confirmed to handle 66-РЗ
  ownerless-property cases) and a couple of likely-API variants. Forensically
  capture every response. Parse out <form> structure (action/method/inputs)
  and any visible search-result/error text, and print a structured summary --
  enough to tell a human whether (a) the page is a search FORM that needs
  parameters we don't have yet, (b) it 404s / redirects to something else
  entirely, or (c) it already exposes case-search results.

  PHASE 2 (separate follow-up script, written only after reading Phase 1's
  output -- the actual search parameters can't be guessed correctly without
  seeing the live form).

CLAUDE MUST NEVER RUN THIS -- ej.sudrf.ru is part of the same geoblocked
federal court-portal infrastructure as the per-court GAS «Правосудие» sites
(see CLAUDE.md, src/mariupol_seizures/crawl/court_crawler.py's identical
warning). Run only from your own Russia-routed VPS:

  PYTHONPATH=src .venv312/bin/python scripts/196_probe_ej_sudrf_fulltext.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import requests  # noqa: E402
import urllib3  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

if not config.SSL_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Жовтневый районный суд г. Мариуполя's GAS «Правосудие» court code --
# confirmed live + the court explicitly handling 66-РЗ ownerless-property
# cases (src/mariupol_seizures/crawl/courts.py). Used here only as the
# {court} parameter for ej.sudrf.ru's "fromOa" scoping, per
# pre_petition_sourcing.md §4's original citation.
COURT_CODE = "93RS0006"

PROBE_URLS = [
    f"https://ej.sudrf.ru/?fromOa={COURT_CODE}",
    "https://ej.sudrf.ru/",
    # Common GAS «Правосудие» full-text search endpoint pattern -- a guess,
    # not a confirmed URL; harmless to probe, logged either way.
    f"https://ej.sudrf.ru/index.php?fromOa={COURT_CODE}",
]

# A known case from this court already in our docket-card store, to try
# against the search form IF phase 1 reveals usable parameters. Not used
# automatically here -- printed for the human reading the output to try
# manually if the form needs a case-number field.
KNOWN_SAMPLE_CASE = "9-36/2026"


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": config.USER_AGENT, "Accept-Language": "ru,en;q=0.8"})
    if config.PROXY:
        s.proxies.update({"http": config.PROXY, "https": config.PROXY})
    return s


def summarize_html(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    forms = []
    for form in soup.find_all("form"):
        inputs = []
        for el in form.find_all(["input", "select", "textarea"]):
            inputs.append({
                "tag": el.name,
                "name": el.get("name"),
                "type": el.get("type"),
                "value": el.get("value"),
            })
        forms.append({
            "action": form.get("action"),
            "method": form.get("method"),
            "inputs": inputs,
        })
    title = soup.title.get_text(strip=True) if soup.title else None
    body_text = soup.get_text(" ", strip=True)
    return {
        "title": title,
        "n_forms": len(forms),
        "forms": forms,
        "body_text_preview": body_text[:600],
        "body_text_len": len(body_text),
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    con = forensics.open_state()
    s = make_session()

    for url in PROBE_URLS:
        log.info("Fetching %s", url)
        try:
            r = s.get(url, timeout=config.TIMEOUT, verify=config.SSL_VERIFY,
                      allow_redirects=True)
        except requests.RequestException as e:
            log.error("  FAILED: %s", e)
            continue

        sha = forensics.capture_source(
            r.content, url=url, source_type="ej_sudrf_probe",
            title=f"ej.sudrf.ru probe: {url}",
            description=(
                "Discovery probe for whether ej.sudrf.ru exposes per-case "
                "full judicial-act texts (progress_report_2026-06.md §5 "
                "item 9). Phase 1 -- structure inspection only, no search "
                "submitted yet."
            ),
            content_type=r.headers.get("Content-Type", "text/html"),
            http_status=r.status_code, con=con,
        )

        log.info("  status=%d final_url=%s sha=%s", r.status_code, r.url, sha[:16])

        ctype = r.headers.get("Content-Type", "")
        if "html" not in ctype and "text" not in ctype:
            log.info("  non-HTML content-type (%s) -- skipping structure parse", ctype)
            continue

        summary = summarize_html(r.text)
        log.info("  title: %r", summary["title"])
        log.info("  forms found: %d", summary["n_forms"])
        for i, form in enumerate(summary["forms"]):
            log.info("    form[%d] action=%r method=%r", i, form["action"], form["method"])
            for inp in form["inputs"]:
                log.info("      input: %s", inp)
        log.info("  body text (%d chars), preview:\n%s\n",
                  summary["body_text_len"], summary["body_text_preview"])

    log.info("=" * 70)
    log.info("PHASE 1 done. Read the form/input dump above. If a usable search")
    log.info("form appeared (case-number or date-range fields), the next step")
    log.info("is a phase-2 script that submits it with a known sample case:")
    log.info("  court=%s case=%s (already in our docket-card store)",
              COURT_CODE, KNOWN_SAMPLE_CASE)
    log.info("If the page 404s, redirects elsewhere, or shows no form at all,")
    log.info("that itself answers item 9: no full-text path exists here.")


if __name__ == "__main__":
    main()
