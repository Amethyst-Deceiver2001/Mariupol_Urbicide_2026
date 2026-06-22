"""Stage 1: crawl. Harvest raw HTML from court portals. Capture before parse.

Claude must never run this — it hits a geoblocked foreign-state system and is run
only by the user from their own Russia-routed VPS (see CLAUDE.md).
"""
from __future__ import annotations

import logging
import random
import re
import time
from urllib.parse import urljoin

import requests
import urllib3
from bs4 import BeautifulSoup

from .. import config, forensics
from .courts import Court, enabled_courts

log = logging.getLogger(__name__)

if not config.SSL_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Keep rows whose result-row text matches the ownerless / municipal-property frame.
RELEVANT = re.compile(r"бесхозяйн|муниципальн\w* собственност|признани\w* права", re.I)


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": config.USER_AGENT, "Accept-Language": "ru,en;q=0.8"})
    if config.PROXY:
        s.proxies.update({"http": config.PROXY, "https": config.PROXY})
    return s


def polite_sleep() -> None:
    time.sleep(random.uniform(*config.REQUEST_DELAY))


def fetch(s, url, con, court, kind):
    """GET with retry/backoff; forensically capture the body. Returns (text, sha)."""
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            r = s.get(url, timeout=config.TIMEOUT, verify=config.SSL_VERIFY)
            sha = forensics.capture(r.content, url=url, court=court, kind=kind,
                                    http_status=r.status_code, con=con)
            return r.text, sha
        except requests.RequestException as e:
            wait = min(60, 2 ** attempt) + random.uniform(0, 3)
            log.warning("%s attempt %d/%d failed: %s; wait %.0fs",
                        kind, attempt, config.MAX_RETRIES, e, wait)
            time.sleep(wait)
    log.error("giving up on %s", url)
    return None, None


def parse_results(html: str, origin: str):
    """Yield {case_number, category, card_url, case_uid} per result row.

    The results page renders inside <table id="tablcont">. Each data row has a
    link with name_op=case pointing to the individual case card. The case_uid
    is the GUID in the case_uid= query parameter.
    """
    soup = BeautifulSoup(html, "lxml")
    for row in soup.select("table#tablcont tr"):
        cells = [c.get_text(" ", strip=True) for c in row.find_all("td")]
        link = row.find("a", href=re.compile(r"name_op=case"))
        if not cells or not link:
            continue
        href = urljoin(origin + "/", link["href"])
        uid = re.search(r"case_uid=([0-9a-fA-F-]+)", href, re.I)
        yield {
            "case_number": cells[0],
            "category": " | ".join(cells),
            "card_url": href,
            "case_uid": uid.group(1) if uid else href,
        }


def crawl_court(s, con, court: Court) -> None:
    log.info("== %s (%s) ==", court.name, court.origin)
    page, empty_streak = 1, 0
    prev_uids: set[str] | None = None
    while True:
        rkey = f"results::{court.key}::{page}"
        if forensics.is_done(con, rkey):
            page += 1
            continue
        url = config.RESULTS_TEMPLATE.format(
            court=court.origin, date_from=config.DATE_FROM,
            date_to=config.DATE_TO, page=page)
        html, _ = fetch(s, url, con, court.key, "results")
        polite_sleep()
        if html is None:
            break
        rows = list(parse_results(html, court.origin))
        empty_streak = empty_streak + 1 if not rows else 0
        uids = {row["case_uid"] for row in rows}
        for row in rows:
            relevant = bool(RELEVANT.search(row["category"]))
            con.execute(
                """INSERT OR IGNORE INTO cases
                   (case_uid, court, case_number, category, card_url,
                    relevant, discovered_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (row["case_uid"], court.key, row["case_number"], row["category"],
                 row["card_url"], int(relevant), forensics.now_iso()))
            con.commit()
            if relevant and not forensics.is_done(con, f"card::{row['case_uid']}"):
                fetch(s, row["card_url"], con, court.key, "case_card")
                polite_sleep()
                forensics.mark_done(con, f"card::{row['case_uid']}")
        forensics.mark_done(con, rkey)
        log.info("page %d: %d rows", page, len(rows))
        if empty_streak >= 2:          # two empty pages -> end of docket
            break
        if rows and uids == prev_uids:
            # Some sudrf.ru portals don't return an empty page past the last
            # page of results — they clamp and re-serve the final page for
            # any page= beyond it. Two consecutive pages with the identical
            # set of case_uids means we've hit that clamp; stop here.
            log.info("page %d repeats page %d's rows verbatim "
                     "(server clamped to last page) — end of docket", page, page - 1)
            break
        prev_uids = uids
        page += 1


def run() -> None:
    courts = enabled_courts()
    if not courts:
        raise SystemExit("No enabled courts with origins. Fill crawl/courts.py.")
    if "{date_from}" not in config.RESULTS_TEMPLATE:
        raise SystemExit("Set a real RESULTS_TEMPLATE (DevTools URL + placeholders).")
    con = forensics.open_state()
    s = make_session()
    for court in courts:
        try:
            crawl_court(s, con, court)
        except KeyboardInterrupt:
            log.warning("interrupted — state saved, safe to rerun.")
            break
        except Exception:
            log.exception("%s errored — continuing", court.key)
    n = con.execute("SELECT COUNT(*) FROM cases WHERE relevant=1").fetchone()[0]
    log.info("done; %d relevant cases captured", n)
