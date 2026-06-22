#!/usr/bin/env python3
"""Stage 2: keyword/regex signal-scan of developer-site narrative HTML pages.

Companion to scripts/160 (which handles the structured PDF declarations).
The 11 developer-site crawlers (120, 121, 124, 126-133) also captured ~296
HTML pages -- mostly JS-rendered marketing pages, news/listing teasers, and
boilerplate (terms, privacy policy chrome) -- that have never been examined.

Unlike the chat-signal scripts (122, 123, etc.) these pages are not a
conversation to mine for testimony; they are a developer's own published
claims about specific addresses, prices, and unit counts. This script does
NOT attempt full structured extraction (most of the value here, if any, is
in the PDFs already handled by script 160) -- it flags pages that mention
a cadastral number, an INN, a known Mariupol street, or a decree/RPD
reference, with surrounding context, for human triage. Nothing is loaded
into the DB by this script.

OUTPUT
------
data/parsed/developer_site_pages_signals.jsonl
  One record per page that matched at least one signal. Pages with zero
  hits are skipped (not written) to keep the file to the pages worth
  reading -- but a console summary reports the total pages scanned.

Re-running is safe: pure read of the local raw store, no network, no DB
writes, output overwritten each run.

Run (offline, no network):
    .venv312/bin/python scripts/161_parse_developer_site_pages.py
"""
import json
import logging
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import forensics  # noqa: E402

log = logging.getLogger(__name__)

SITE_PREFIXES = [
    "proektinvest", "evoinfo", "mars_group", "rskdnr", "sadovoe_kolco",
    "sz_antares", "vertikal_ug", "su2007", "rks_development",
    "lazurnieberega", "mirapolis",
]

OUT = ROOT / "data" / "parsed" / "developer_site_pages_signals.jsonl"

_CADASTRAL = re.compile(r"93:\d+:\d+:\d+")
_INN = re.compile(r"\bИНН\s*:?\s*(\d{10,12})\b", re.I)
_RPD_NUM = re.compile(r"\b93-0{4,5}\d{1,3}\b")
_DECREE = re.compile(
    r"Распоряжени[ея]\s*(?:№|N|номер)?\s*[\d/-]+|"
    r"Постановлени[ея]\s*(?:№|N|номер)?\s*[\d/-]+",
    re.I,
)

# Streets already documented elsewhere in the project (demolition register,
# ownerless registry, land orders) -- a hit here means this developer's own
# marketing copy independently names an address already on the spine.
_KNOWN_STREETS = re.compile(
    r"Нахимов|Строителей|Хмельницк|Зелинск|Куприна|Шевченко|Латышев|"
    r"Киевск|Апатов|Ленина|Мира\b|Металлург|Морск|Азовстальск|Будивельник|"
    r"Олимпийск|Лазурн",
    re.I,
)

SKIP_BOILERPLATE = re.compile(
    r"персональных данных|cookie|политика обработки|условия использования",
    re.I,
)


def _context(text: str, m: re.Match, radius: int = 80) -> str:
    a = max(0, m.start() - radius)
    b = min(len(text), m.end() + radius)
    return re.sub(r"\s+", " ", text[a:b]).strip()


def scan_page(text: str) -> dict:
    hits: dict[str, list[str]] = {}

    cadastrals = list(dict.fromkeys(_CADASTRAL.findall(text)))
    if cadastrals:
        hits["cadastral_numbers"] = cadastrals

    inns = list(dict.fromkeys(_INN.findall(text)))
    if inns:
        hits["inn_mentions"] = inns

    rpds = list(dict.fromkeys(_RPD_NUM.findall(text)))
    if rpds:
        hits["rpd_numbers"] = rpds

    decree_matches = [_context(text, m) for m in list(_DECREE.finditer(text))[:5]]
    if decree_matches:
        hits["decree_mentions"] = decree_matches

    street_matches = [_context(text, m) for m in list(_KNOWN_STREETS.finditer(text))[:8]]
    if street_matches:
        hits["known_street_mentions"] = street_matches

    return hits


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        log.error("beautifulsoup4 not installed")
        return

    con = forensics.open_state()
    where = " OR ".join(f"source_type = '{p}_page'" for p in SITE_PREFIXES)
    sources = con.execute(
        f"SELECT sha256, url, source_type, raw_path, title FROM source_document WHERE {where} ORDER BY source_type, url"
    ).fetchall()

    if not sources:
        log.error("No developer-site page records found — run the crawl scripts first.")
        return

    log.info("Scanning %d developer-site HTML pages across %d sites", len(sources), len(SITE_PREFIXES))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    n_with_hits = 0
    per_site_hits: dict[str, int] = {}

    with OUT.open("w", encoding="utf-8") as fh:
        for sha256, url, source_type, raw_path, title in sources:
            path = Path(raw_path)
            if not path.exists():
                continue
            try:
                html = path.read_bytes()
                soup = BeautifulSoup(html, "html.parser")
                text = soup.get_text(" ", strip=True)
            except Exception:
                log.exception("failed to parse %s", url)
                continue

            if SKIP_BOILERPLATE.search(text[:200]):
                continue

            hits = scan_page(text)
            if not hits:
                continue

            site = source_type.rsplit("_page", 1)[0]
            record = {
                "site": site, "source_sha256": sha256, "url": url,
                "page_title": title, **hits,
            }
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            n_with_hits += 1
            per_site_hits[site] = per_site_hits.get(site, 0) + 1
            log.info("[hit] %s %s (%s)", site, url, ",".join(hits.keys()))

    print(f"\n{'='*60}")
    print(f"developer-site page signal-scan complete: {len(sources)} pages scanned")
    print(f"  Pages with at least one signal: {n_with_hits}")
    for site, n in sorted(per_site_hits.items()):
        print(f"    {site}: {n}")
    print(f"  Output: {OUT}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
