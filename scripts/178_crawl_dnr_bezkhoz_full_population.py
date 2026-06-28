#!/usr/bin/env python3
"""Enumerate the COMPLETE DNR Supreme Court ownerless-property (бесхозяйная
недвижимая вещь) appellate population — **including cases with no published
ruling text** — and capture each case card.

WHY THIS SCRIPT EXISTS
----------------------
The existing SC crawler (`src/.../crawl/dnr_supreme_court.py`) searches by
free-text subject and then follows only `name_op=doc` links — i.e. published
*ruling documents*. A case whose судебный акт is not published has no
`name_op=doc` link and is therefore structurally invisible to it. The batches
captured by `scripts/175` were hand-collected from the browser and are
likewise only the text-bearing cases people happened to page to.

The complete population is reachable the same way the **district** docket was
saturated (`crawl/court_crawler.py`, 2,666 cases): hit the **results list**
(`name_op=r`) filtered to the case *category* (`lawbookarticles[]`), **paginate
to the end**, and capture the **`name_op=case` card** for every row. The card
exists for EVERY case — text or not — and always carries the structured
«Результат рассмотрения» metadata (which `scripts/176` classifies); when a
ruling is published, its text is embedded in the same card HTML.

So this script = district-crawler pagination pattern, pointed at
`vs--dnr.sudrf.ru`, writing cards in the exact `source_type` `scripts/176`
already reads. Re-runs are idempotent and dedupe against `scripts/175`
(shared done-key `dnr_bezkhoz_case::<case_id>`).

THE ONE INPUT ONLY YOU CAN SUPPLY
---------------------------------
The SC results URL is portal-specific: its `delo_id` (appellate-civil instance)
and the exact `lawbookarticles[]`/category value are NOT guessable and differ
from the district template. Capture it once from the browser session you have
already confirmed works:

  1. On vs--dnr.sudrf.ru open «Поиск информации по делам» → Гражданские дела,
     set Категория = «О признании движимой вещи бесхозяйной и признании права
     муниципальной собственности на бесхозяйную недвижимую вещь» (особое
     производство), set the date range, Найти.
  2. Copy the full results URL from the address bar / DevTools (it contains
     name_op=r … &page=1 …). This is the same filter you used for the 4 manual
     batches.
  3. Replace the page number with the literal token {page}, and export it:

       export SC_RESULTS_TEMPLATE='https://vs--dnr.sudrf.ru/modules.php?...&page={page}&...'

  Optionally also: export COURT_PROXY=... (your Russia-routed proxy/VPS), and
  CRAWL_DATE_FROM / CRAWL_DATE_TO if your URL uses {date_from}/{date_to} slots.

Claude must never run this (geoblocked foreign-state system) — you run it from
your VPS, like every other court crawl (CLAUDE.md).

  .venv312/bin/python scripts/178_crawl_dnr_bezkhoz_full_population.py

Output:
  * case cards  -> data/raw/<sha>.html  (source_type=dnr_supreme_court_docket_case)
  * enumeration -> data/parsed/dnr_bezkhoz_population_manifest.jsonl
                   (one row per result, incl. text-less; never silently dropped)
Then re-run scripts/176 to re-classify outcomes over the expanded population.

FALLBACK if the server-side fetch returns 0 rows (session/JS gating rather than
geoblock): run `--print-harvester` to print a browser-console snippet; paste it
into DevTools on your working results page. It auto-pages the whole docket and
dumps every case_id/case_uid as JSON. Save that to
data/parsed/dnr_bezkhoz_population_seed.json and re-run with `--from-seed` to
capture the cards (still from your VPS).
"""
import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import requests  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

from mariupol_seizures import config, forensics  # noqa: E402
from mariupol_seizures.crawl import court_crawler  # noqa: E402 (reuse session/sleep)

log = logging.getLogger(__name__)

ORIGIN = "https://vs--dnr.sudrf.ru"
SOURCE_TYPE = "dnr_supreme_court_docket_case"   # matches scripts/175 + 176
MANIFEST = ROOT / "data" / "parsed" / "dnr_bezkhoz_population_manifest.jsonl"
SEED = ROOT / "data" / "parsed" / "dnr_bezkhoz_population_seed.json"

SC_RESULTS_TEMPLATE = os.environ.get("SC_RESULTS_TEMPLATE", "")

# Browser-console fallback: paste into DevTools on the working results page.
# Auto-pages the docket via the page= param and dumps every case to JSON.
CONSOLE_HARVESTER = r"""
// --- DNR SC bezkhoz population harvester — paste in DevTools console on the
// --- working results page (name_op=r). Auto-pages to the end, dumps JSON.
(async () => {
  const base = location.href.replace(/&page=\d+/, '');
  const setPage = (n) => base.includes('page=')
      ? base.replace(/page=\d+/, 'page=' + n) : base + '&page=' + n;
  const out = []; const seen = new Set(); let prev = '';
  for (let p = 1; p < 500; p++) {
    const html = await (await fetch(setPage(p), {credentials: 'include'})).text();
    const doc = new DOMParser().parseFromString(html, 'text/html');
    const rows = [...doc.querySelectorAll('table#tablcont tr')];
    const ids = [];
    for (const tr of rows) {
      const a = tr.querySelector('a[href*="name_op=case"]'); if (!a) continue;
      const cid = (a.href.match(/case_id=(\d+)/) || [])[1];
      const uid = (a.href.match(/case_uid=([0-9a-fA-F-]+)/) || [])[1] || '';
      const num = (tr.querySelector('td') || {}).innerText || '';
      if (!cid || seen.has(cid)) continue;
      seen.add(cid); ids.push(cid);
      out.push({case_id: cid, case_uid: uid, case_number: num.trim(),
                row_text: [...tr.querySelectorAll('td')].map(t=>t.innerText.trim()).join(' | ')});
    }
    const sig = ids.join(','); console.log('page', p, '+', ids.length, 'total', out.length);
    if (ids.length === 0 || sig === prev) break; prev = sig;
    await new Promise(r => setTimeout(r, 1500));
  }
  const blob = new Blob([JSON.stringify(out, null, 2)], {type: 'application/json'});
  const u = URL.createObjectURL(blob); const link = document.createElement('a');
  link.href = u; link.download = 'dnr_bezkhoz_population_seed.json'; link.click();
  console.log('DONE —', out.length, 'cases. Saved dnr_bezkhoz_population_seed.json');
})();
"""

# Keep cards whose result-row text matches the ownerless / municipal-property
# frame. If the SC_RESULTS_TEMPLATE already filters to exactly the bezkhoz
# category, every row passes; if it uses the broad особое-производство parent,
# this narrows to bezkhoz. Either way ALL rows are written to the manifest.
RELEVANT = re.compile(r"бесхозяйн|муниципальн\w*\s+собственност|признани\w*\s+права", re.I)
_CASE_ID = re.compile(r"case_id=(\d+)", re.I)
_CASE_UID = re.compile(r"case_uid=([0-9a-fA-F-]+)", re.I)


def _card_url(case_id: str, case_uid: str = "") -> str:
    uid = f"&case_uid={case_uid}" if case_uid else ""
    return (f"{ORIGIN}/modules.php?name=sud_delo&srv_num=1"
            f"&name_op=case&case_id={case_id}{uid}&delo_id=5&new=5")


def parse_rows(html: str):
    """Yield {case_id, case_uid, case_number, row_text, card_href} per result row.

    Mirrors court_crawler.parse_results but also extracts case_id (needed for the
    shared done-key) and keeps the whole row text for outcome pre-screening.
    """
    soup = BeautifulSoup(html, "lxml")
    for row in soup.select("table#tablcont tr"):
        cells = [c.get_text(" ", strip=True) for c in row.find_all("td")]
        link = row.find("a", href=re.compile(r"name_op=case"))
        if not cells or not link:
            continue
        href = urljoin(ORIGIN + "/", link["href"])
        cid = _CASE_ID.search(href)
        uid = _CASE_UID.search(href)
        yield {
            "case_id": cid.group(1) if cid else None,
            "case_uid": uid.group(1) if uid else "",
            "case_number": cells[0],
            "row_text": " | ".join(cells),
            "card_href": href,
        }


def _get(s, url):
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            r = s.get(url, timeout=config.TIMEOUT, verify=config.SSL_VERIFY)
            if "charset" not in r.headers.get("content-type", "").lower():
                r.encoding = "cp1251"
            return r
        except requests.RequestException as e:
            wait = min(60, 2 ** attempt)
            log.warning("GET failed (%d/%d): %s; wait %ds", attempt,
                        config.MAX_RETRIES, e, wait)
            time.sleep(wait)
    return None


def capture_card(s, con, case_id, case_uid, case_number, manifest_fh, row_text):
    """Capture one case card (idempotent; shared done-key with scripts/175)."""
    key = f"dnr_bezkhoz_case::{case_id}"
    already = forensics.is_done(con, key)
    if not already:
        url = _card_url(case_id, case_uid)
        r = _get(s, url)
        time.sleep(2.0)
        if r is None or r.status_code != 200:
            log.warning("card not fetched: case_id %s (%s)", case_id, case_number)
            return False
        forensics.capture_source(
            r.content, url=url, source_type=SOURCE_TYPE,
            title=f"ВС ДНР — карточка дела (case_id {case_id}) — {case_number}",
            description=(
                "Full-population capture of DNR Supreme Court ownerless-property "
                "(бесхозяйная недвижимая вещь) appeal, enumerated via the portal's "
                "category-filtered results list incl. cases with no published "
                f"ruling text. Case {case_number}. Row: {row_text[:200]}"),
            content_type=r.headers.get("Content-Type", "text/html; charset=cp1251"),
            http_status=r.status_code, con=con,
        )
        forensics.mark_done(con, key)
        log.info("captured case_id %s (%s)", case_id, case_number)
    manifest_fh.write(json.dumps({
        "case_id": case_id, "case_uid": case_uid,
        "case_number": case_number, "row_text": row_text,
        "relevant": bool(RELEVANT.search(row_text)),
        "already_captured": already,
    }, ensure_ascii=False) + "\n")
    manifest_fh.flush()
    return True


def crawl_results(s, con, manifest_fh) -> int:
    if not SC_RESULTS_TEMPLATE or "{page}" not in SC_RESULTS_TEMPLATE:
        raise SystemExit(
            "SC_RESULTS_TEMPLATE not set (or missing {page}). Capture the working "
            "results URL from your browser session and export it — see this file's "
            "module docstring for the 3-step procedure.")
    page, empty_streak, n_rows, n_cards = 1, 0, 0, 0
    prev_ids: set | None = None
    while True:
        url = SC_RESULTS_TEMPLATE.format(
            page=page, date_from=config.DATE_FROM, date_to=config.DATE_TO)
        r = _get(s, url)
        court_crawler.polite_sleep()
        if r is None or r.status_code != 200:
            log.warning("results page %d unavailable", page)
            break
        # Preserve the docket state for reproducibility (not permalink-stable).
        forensics.capture_source(
            r.content, url=url, source_type="dnr_supreme_court_index",
            title=f"ВС ДНР bezkhoz results — page {page}",
            description=("DNR Supreme Court category-filtered results list "
                         f"(ownerless property), page {page}, full-population enumeration."),
            content_type=r.headers.get("Content-Type", "text/html"),
            http_status=r.status_code, con=con,
        )
        rows = list(parse_rows(r.text))
        ids = {row["case_id"] for row in rows if row["case_id"]}
        empty_streak = empty_streak + 1 if not rows else 0
        for row in rows:
            if not row["case_id"]:
                continue
            n_rows += 1
            if capture_card(s, con, row["case_id"], row["case_uid"],
                            row["case_number"], manifest_fh, row["row_text"]):
                n_cards += 1
        log.info("page %d: %d rows (%d cumulative)", page, len(rows), n_rows)
        if empty_streak >= 2:
            break
        if rows and ids == prev_ids:
            log.info("page %d repeats page %d verbatim (server clamp) — end", page, page - 1)
            break
        prev_ids = ids
        page += 1
    return n_cards


def capture_from_seed(s, con, manifest_fh) -> int:
    """Fallback: capture cards from a browser-console-harvested seed JSON
    (list of {case_id, case_uid?, case_number?})."""
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    n = 0
    for item in seed:
        cid = str(item["case_id"])
        if capture_card(s, con, cid, item.get("case_uid", ""),
                        item.get("case_number", "?"), manifest_fh, item.get("row_text", "")):
            n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-seed", action="store_true",
                    help=f"capture cards listed in {SEED} (browser-console fallback)")
    ap.add_argument("--print-harvester", action="store_true",
                    help="print the DevTools console snippet for the fallback path and exit")
    args = ap.parse_args()

    if args.print_harvester:
        print(CONSOLE_HARVESTER)
        return

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    con = forensics.open_state()
    s = court_crawler.make_session()
    with MANIFEST.open("a", encoding="utf-8") as fh:
        if args.from_seed:
            n = capture_from_seed(s, con, fh)
        else:
            n = crawl_results(s, con, fh)
    total = con.execute(
        "SELECT COUNT(*) FROM source_document WHERE source_type=?", (SOURCE_TYPE,)
    ).fetchone()[0]
    log.info("done; %d cards captured this run; %d total %s in store",
             n, total, SOURCE_TYPE)
    log.info("manifest -> %s ; now re-run scripts/176 to re-classify outcomes", MANIFEST)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
