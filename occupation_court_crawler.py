#!/usr/bin/env python3
"""
occupation_court_crawler.py
===========================
Forensic starter crawler for occupation-court (ГАС «Правосудие») portals in the
so-called DNR/LNR, targeting "ownerless property" → municipal-ownership transfers
(особое производство: признание права муниципальной собственности на бесхозяйную
недвижимую вещь, ГПК РФ гл. 33).

DESIGN PRINCIPLES
-----------------
1. Capture-time forensics: every HTTP body is saved verbatim, with SHA-256 +
   ISO-8601 UTC capture timestamp + source URL, before any parsing. Parsing is a
   downstream, re-runnable step on the immutable raw store. (Berkeley Protocol.)
2. Don't trust my guesses for the search form's GET fields. ГАС «Правосудие»
   field names (G1_*, U1_*, delo_id codes) vary by software build. Instead you
   paste ONE working results URL captured from your browser DevTools, with
   {date_from} {date_to} {page} placeholders. The crawler only owns pagination,
   relevance filtering, case-card traversal, capture, politeness and resumability.
3. Polite + resumable: sqlite state, configurable delay/jitter, retries with
   backoff, safe to Ctrl-C and restart. Designed for an 8 GB box behind a
   Russia-routed proxy (the portals are geoblocked).

WHAT IT IS NOT
--------------
A finished extractor. It harvests and forensically stores raw HTML and pulls a
first pass of fields. Structured parsing of the decision text (owner name,
address, grounds, dates) is deliberately a separate stage you run over the raw
store, so you can iterate on parsing without re-hitting the courts.

USAGE
-----
1. Fill COURTS with the real subdomains (see the discovery note at the bottom).
2. On one court, run a manual "ownerless" search in a browser, open DevTools →
   Network, copy the results-page request URL, and paste it into RESULTS_TEMPLATE
   replacing the date and page values with {date_from} {date_to} {page}.
3. Set PROXY to your Russia-routed proxy. Set DATE_FROM / DATE_TO.
4. python occupation_court_crawler.py
"""

import hashlib
import json
import os
import random
import re
import sqlite3
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup  # pip install beautifulsoup4 lxml

# ----------------------------------------------------------------------------- 
# CONFIG — edit these
# ----------------------------------------------------------------------------- 
OUTPUT_ROOT = "./court_evidence"           # raw store + sqlite live here
PROXY = os.environ.get("COURT_PROXY", "")  # e.g. "socks5h://user:pass@host:1080"
DATE_FROM = "01.03.2024"                    # dd.mm.yyyy — start of Law 66-RZ era
DATE_TO   = "01.07.2026"                    # extend past the 01.07.2026 deadline wave
REQUEST_DELAY = (4.0, 9.0)                  # (min, max) seconds between requests
MAX_RETRIES = 4
TIMEOUT = 45

# Court directory: name -> base origin. Seeded with what recon confirmed; the
# rest of the 25 (HRW: 23 district + 2 regional, DNR/LNR) must be added. District
# courts in this system are reachable either under supcourt-dpr.su subpaths or as
# *.sudrf.ru subdomains with the new-region codes — confirm each by hand.
COURTS = {
    # "primorsky_mariupol": "https://primorsky.??.sudrf.ru",   # ул. Казанцева 7б; m.prim@supcourt-dpr.su
    # "pershotravnevy":     "https://...",
    # "telmanovsky":        "https://...",
    # ... add the full set discovered from supcourt-dpr.su / lnr equivalent ...
}

# Paste a REAL working results URL from DevTools, with placeholders.
# The {court} prefix is filled per-court; keep everything after the origin.
# Example shape (DO NOT trust the field names — replace with your captured ones):
RESULTS_TEMPLATE = (
    "{court}/modules.php?name=sud_delo&srv_num=1&name_op=r&delo_id=1540005"
    "&case_type=0&new=0&G1_CASE__ENTRY_DATE1D={date_from}&G1_CASE__ENTRY_DATE2D={date_to}"
    "&page={page}"
)

# Relevance filter applied to each result row's category/subject text.
RELEVANT = re.compile(r"бесхозяйн|муниципальн\w* собственност|признани\w* права", re.I)

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# ----------------------------------------------------------------------------- 
# Infrastructure
# ----------------------------------------------------------------------------- 
def now_iso():
    return datetime.now(timezone.utc).isoformat()

def session():
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "ru,en;q=0.8"})
    if PROXY:
        s.proxies.update({"http": PROXY, "https": PROXY})
    return s

def db_init():
    os.makedirs(os.path.join(OUTPUT_ROOT, "raw"), exist_ok=True)
    con = sqlite3.connect(os.path.join(OUTPUT_ROOT, "state.sqlite"))
    con.executescript("""
        CREATE TABLE IF NOT EXISTS fetch_log (
            url TEXT, court TEXT, kind TEXT, sha256 TEXT,
            raw_path TEXT, http_status INT, captured_at TEXT,
            PRIMARY KEY (url, captured_at)
        );
        CREATE TABLE IF NOT EXISTS cases (
            case_uid TEXT PRIMARY KEY, court TEXT, case_number TEXT,
            category TEXT, parties TEXT, entry_date TEXT, card_url TEXT,
            relevant INT, discovered_at TEXT
        );
        CREATE TABLE IF NOT EXISTS done (key TEXT PRIMARY KEY);
    """)
    con.commit()
    return con

def mark_done(con, key):
    con.execute("INSERT OR IGNORE INTO done(key) VALUES (?)", (key,))
    con.commit()

def is_done(con, key):
    return con.execute("SELECT 1 FROM done WHERE key=?", (key,)).fetchone() is not None

def polite_sleep():
    time.sleep(random.uniform(*REQUEST_DELAY))

def fetch(s, url, con, court, kind):
    """GET with retries; forensically persist the raw body; log it."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = s.get(url, timeout=TIMEOUT)
            body = r.content
            sha = hashlib.sha256(body).hexdigest()
            captured = now_iso()
            raw_path = os.path.join(OUTPUT_ROOT, "raw", f"{sha}.html")
            if not os.path.exists(raw_path):
                with open(raw_path, "wb") as f:
                    f.write(body)
            # sidecar metadata = chain-of-custody record per artifact
            with open(raw_path + ".meta.json", "w", encoding="utf-8") as f:
                json.dump({"url": url, "court": court, "kind": kind,
                           "sha256": sha, "http_status": r.status_code,
                           "captured_at": captured,
                           "content_type": r.headers.get("Content-Type", "")},
                          f, ensure_ascii=False, indent=2)
            con.execute(
                "INSERT OR REPLACE INTO fetch_log VALUES (?,?,?,?,?,?,?)",
                (url, court, kind, sha, raw_path, r.status_code, captured))
            con.commit()
            return r.text, sha
        except requests.RequestException as e:
            wait = min(60, 2 ** attempt) + random.uniform(0, 3)
            print(f"  ! {kind} attempt {attempt}/{MAX_RETRIES} failed: {e}; wait {wait:.0f}s")
            time.sleep(wait)
    print(f"  !! giving up on {url}")
    return None, None

# ----------------------------------------------------------------------------- 
# Parsing (first pass only — refine against the raw store later)
# ----------------------------------------------------------------------------- 
def parse_results(html, court_origin):
    """Yield dicts for each case row in a sud_delo results table.
    Selectors are intentionally loose; tune to the real markup once you see it."""
    soup = BeautifulSoup(html, "lxml")
    for row in soup.select("table#tablcont tr, table.law-case-table tr, tr.tr_results"):
        cells = [c.get_text(" ", strip=True) for c in row.find_all("td")]
        link = row.find("a", href=re.compile(r"name_op=case"))
        if not cells or not link:
            continue
        href = urljoin(court_origin + "/", link["href"])
        uid = re.search(r"case_uid=([0-9a-fA-F-]+)", href)
        yield {
            "case_number": cells[0] if cells else "",
            "category":    " | ".join(cells),     # keep full row text for filtering
            "card_url":    href,
            "case_uid":    uid.group(1) if uid else href,
        }

# ----------------------------------------------------------------------------- 
# Main crawl
# ----------------------------------------------------------------------------- 
def crawl_court(s, con, name, origin):
    print(f"== {name} ({origin}) ==")
    page = 1
    empty_streak = 0
    while True:
        key = f"results::{name}::{page}"
        if is_done(con, key):
            page += 1
            continue
        url = RESULTS_TEMPLATE.format(court=origin, date_from=DATE_FROM,
                                      date_to=DATE_TO, page=page)
        html, _ = fetch(s, url, con, name, "results")
        polite_sleep()
        if html is None:
            break
        rows = list(parse_results(html, origin))
        if not rows:
            empty_streak += 1
            if empty_streak >= 2:        # two empty pages → end of list
                mark_done(con, key)
                break
        else:
            empty_streak = 0
        for row in rows:
            relevant = bool(RELEVANT.search(row["category"]))
            con.execute("""INSERT OR IGNORE INTO cases
                (case_uid, court, case_number, category, parties, entry_date,
                 card_url, relevant, discovered_at)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (row["case_uid"], name, row["case_number"], row["category"],
                 "", "", row["card_url"], int(relevant), now_iso()))
            con.commit()
            if relevant and not is_done(con, f"card::{row['case_uid']}"):
                fetch(s, row["card_url"], con, name, "case_card")
                polite_sleep()
                mark_done(con, f"card::{row['case_uid']}")
        mark_done(con, key)
        print(f"  page {page}: {len(rows)} rows "
              f"({sum(bool(RELEVANT.search(r['category'])) for r in rows)} relevant)")
        page += 1

def main():
    if not COURTS:
        raise SystemExit("Fill COURTS with real court origins first (see note).")
    if "{date_from}" not in RESULTS_TEMPLATE:
        raise SystemExit("Paste a real results URL into RESULTS_TEMPLATE with placeholders.")
    con = db_init()
    s = session()
    for name, origin in COURTS.items():
        try:
            crawl_court(s, con, name, origin.rstrip("/"))
        except KeyboardInterrupt:
            print("interrupted — state saved, safe to rerun.")
            break
        except Exception as e:
            print(f"  !! {name} errored: {e} — continuing")
    n = con.execute("SELECT COUNT(*) FROM cases WHERE relevant=1").fetchone()[0]
    print(f"\nDone. {n} relevant cases captured. Raw store: {OUTPUT_ROOT}/raw/")

if __name__ == "__main__":
    main()

# =============================================================================
# DISCOVERY NOTE — finding the 25 court origins
# =============================================================================
# Confirmed so far:
#   - DNR Supreme Court portal:  https://supcourt-dpr.su  (lists subordinate courts)
#   - Primorskyi District Court, Mariupol — ул. Казанцева 7б; email m.prim@supcourt-dpr.su
#   - Other Mariupol courts named in HRW rulings: Pershotravnevyi, Telmanovskiy.
# To enumerate all 25:
#   1. supcourt-dpr.su → подведомственные/районные суды list (gives DNR district courts).
#   2. LNR equivalent supreme-court portal for the 2 regional + Luhansk district courts.
#   3. Cross-check against *.sudrf.ru: post-2022 the new "subjects" were assigned
#      region codes; district courts may also resolve as <name>--<code>.sudrf.ru.
# Verify each origin actually serves modules.php?name=sud_delo before adding.
# =============================================================================
