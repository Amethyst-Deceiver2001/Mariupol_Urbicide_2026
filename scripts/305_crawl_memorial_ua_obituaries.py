#!/usr/bin/env python3
"""Crawl memorial.ua's civilian + children obituary pages, capture every
page forensically, and flag the ones naming Mariupol (place of death or
place of birth) as candidate leads for the courtyard-grave-site cross-
reference (scripts/300/301/304).

IMPORTANT -- Claude does not run this script. memorial.ua's robots.txt
explicitly disallows "ClaudeBot" (alongside GPTBot/CCBot/Amazonbot/etc.)
while leaving general User-agent:* access (search=yes, use=reference) open:

    User-agent: ClaudeBot
    Disallow: /

This is a deliberate, named restriction, not a generic scraping guard --
routing around it with a different User-Agent string would just be
disguising the request to defeat a rule the site operator wrote with
Claude specifically in mind. So this is YOUR crawl to run, from your own
machine (memorial.ua is a Ukrainian NGO site, not geoblocked -- no VPS
needed, unlike the Telegram/occupation-portal scripts):

    .venv/bin/python scripts/305_crawl_memorial_ua_obituaries.py
    .venv/bin/python scripts/305_crawl_memorial_ua_obituaries.py --categories civilians,children,militaries

Politeness: 4-9s randomized delay between requests (config.REQUEST_DELAY),
same as this project's other rate-limited crawlers. ~3,323 pages
(civilians+children) at that pace is several hours -- runs safely in the
background, resumable (skips URLs already in source_document), safe to
interrupt and re-run.

Source-type: "memorial_ua_obituary_page" (own namespace, independent of the
single-URL memorial.ua capture in scripts/239, which used source_type
"memorial_ua_obituary" for one already-known corroboration target).

Defaults to civilians + children only (militaries category is a different
evidentiary type -- combat deaths, not the demolition/dispossession angle
this project tracks -- and is 3x the volume; pass --categories to include
it if you want it anyway).
"""
from __future__ import annotations

import argparse
import csv
import logging
import random
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

SOURCE_TYPE = "memorial_ua_obituary_page"
SITEMAP_URL = "https://memorial.ua/sitemap.xml"
LEADS_OUT = ROOT / "data" / "reports" / "memorial_ua_mariupol_leads.csv"

MARIUPOL_RE = re.compile(r"маріупол|mariupol", re.IGNORECASE)

FIELD_LABELS = {
    "Місто загибелі": "death_city",
    "Місто народження": "birth_city",
    "Область загибелі": "death_oblast",
    "Дата загибелі": "death_date",
    "Вік": "age",
    "Професія": "profession",
}


def fetch(url: str) -> tuple[bytes, str, int]:
    for attempt in range(config.MAX_RETRIES):
        try:
            resp = requests.get(
                url, headers={"User-Agent": config.USER_AGENT},
                timeout=config.TIMEOUT, allow_redirects=True,
            )
            resp.raise_for_status()
            return resp.content, resp.headers.get("Content-Type", "text/html"), resp.status_code
        except requests.exceptions.RequestException as exc:
            if attempt == config.MAX_RETRIES - 1:
                raise
            log.warning("transient error fetching %s (attempt %d/%d): %s -- retrying",
                        url, attempt + 1, config.MAX_RETRIES, exc)
            time.sleep(3.0 * (attempt + 1))


def already_captured(con) -> set[str]:
    rows = con.execute(
        "SELECT url FROM source_document WHERE source_type=?", (SOURCE_TYPE,)
    ).fetchall()
    return {u for (u,) in rows}


def list_obituary_urls(categories: list[str]) -> list[str]:
    content, _, _ = fetch(SITEMAP_URL)
    text = content.decode("utf-8")
    urls = re.findall(r"<loc>(https://memorial\.ua/obituaries/([a-z]+)/[^<]+)</loc>", text)
    return [u for u, cat in urls if cat in categories]


def parse_fields(html: bytes) -> dict:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    name = ""
    h1 = soup.find("h1")
    if h1:
        name = h1.get_text(" ", strip=True)

    fields = {}
    for label, key in FIELD_LABELS.items():
        m = re.search(re.escape(label) + r"\s*(.{2,80}?)\s*(?:" +
                       "|".join(re.escape(l) for l in FIELD_LABELS if l != label) +
                       r"|$)", text)
        if m:
            fields[key] = m.group(1).strip(" .,")

    return {"name": name, **fields, "raw_text_len": len(text)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--categories", default="civilians,children",
                     help="comma-separated: civilians,children,militaries (default: civilians,children)")
    args = ap.parse_args()
    categories = [c.strip() for c in args.categories.split(",") if c.strip()]

    con = forensics.open_state()
    done = already_captured(con)
    log.info("already captured in a prior run: %d pages", len(done))

    urls = list_obituary_urls(categories)
    todo = [u for u in urls if u not in done]
    log.info("sitemap categories %s: %d total URLs, %d still to fetch", categories, len(urls), len(todo))

    leads = []
    n = 0
    for url in todo:
        try:
            content, ctype, status = fetch(url)
        except requests.exceptions.RequestException as exc:
            log.error("giving up on %s: %s", url, exc)
            continue

        fields = parse_fields(content)
        haystack = " ".join(str(v) for v in fields.values())
        is_mariupol = bool(MARIUPOL_RE.search(haystack))

        forensics.capture_source(
            content, url=url, source_type=SOURCE_TYPE,
            title=f"memorial.ua obituary: {fields.get('name') or url}",
            description=(
                f"{'MARIUPOL MATCH -- ' if is_mariupol else ''}"
                f"death_city={fields.get('death_city', '')!r} "
                f"birth_city={fields.get('birth_city', '')!r} "
                f"age={fields.get('age', '')!r} "
                f"death_date={fields.get('death_date', '')!r}. "
                f"Civilian/children obituary from the memorial.ua platform."
            ),
            content_type=ctype, http_status=status, con=con,
        )

        if is_mariupol:
            leads.append({"url": url, **fields})

        n += 1
        if n % 50 == 0:
            log.info("… %d/%d fetched this run, %d Mariupol matches so far", n, len(todo), len(leads))

        time.sleep(random.uniform(*config.REQUEST_DELAY))

    con.close()

    if leads:
        LEADS_OUT.parent.mkdir(parents=True, exist_ok=True)
        write_header = not LEADS_OUT.exists()
        with LEADS_OUT.open("a", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["url", "name", "death_city", "birth_city",
                                                "death_oblast", "death_date", "age",
                                                "profession", "raw_text_len"])
            if write_header:
                w.writeheader()
            w.writerows(leads)

    log.info("=== SUMMARY (this run) ===")
    log.info("fetched: %d", n)
    log.info("Mariupol matches: %d", len(leads))
    log.info("leads appended -> %s", LEADS_OUT)
    log.info("re-run this script to resume where it left off (already-captured URLs are skipped)")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
