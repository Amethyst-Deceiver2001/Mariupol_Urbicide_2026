"""Capture and catalogue primary reference sources for the toponym table.

This script downloads, SHA-256 hashes, and stores every known reference source
(decrees, news articles, official registers) into data/raw/ with sidecar
.meta.json files and a source_document table in data/state.sqlite.

Run modes
---------
  python scripts/00_capture_sources.py            # capture all missing sources
  python scripts/00_capture_sources.py --catalogue # print catalogue, no downloads
  python scripts/00_capture_sources.py --verify    # re-hash store, report mismatches

Some sources are geoblocked and must be run from a Russia-routed VPS
(same requirement as the court crawler).  These are marked with
requires_proxy=True in SOURCE_CATALOGUE below.

Forensic rules (Berkeley Protocol / CLAUDE.md):
  - Raw bytes written verbatim; never modified after first write.
  - Every file keyed by SHA-256; sidecar .meta.json records provenance.
  - Already-captured sources are skipped (idempotent).
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from dataclasses import dataclass

import requests

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "src"))

from mariupol_seizures import config
from mariupol_seizures.forensics import capture_source, list_sources, open_state

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
log = logging.getLogger(__name__)


@dataclass
class SourceEntry:
    url: str
    source_type: str     # decree | news_article | register | other
    title: str
    description: str
    requires_proxy: bool = False


SOURCE_CATALOGUE: list[SourceEntry] = [
    # ── Official occupation decrees (primary evidence) ───────────────────────
    SourceEntry(
        url="https://base.garant.ru/407380704/",
        source_type="decree",
        title="DNR Mariupol Admin Order No. 262 (29 Sep 2022)",
        description=(
            "Official occupation decree signed by K.V. Ivashchenko (DNR-appointed "
            "Administrator of Mariupol), restoring Soviet-era street names in "
            "Zhovtnevy, Ilyichevskyy, and Ordzhonikidzevskyy districts. "
            "952 street entries; 93 actual renames. "
            "Parent decree: DNR Head Decree No. 72, 12 Mar 2022."
        ),
        requires_proxy=True,
    ),
    SourceEntry(
        url="https://mariupol-r897.gosweb.gosuslugi.ru/netcat_files/46/469/97_21_11_2022.pdf",
        source_type="decree",
        title="DNR Mariupol Admin Order No. 97 (21 Nov 2022) — Amendment PDF",
        description=(
            "38-page scanned PDF amending Decree 262. Covers all 4 pre-decommunization "
            "districts including Primorsky (absent from garant.ru version). "
            "Source of the 12 Primorsky district rename entries in toponyms.csv."
        ),
        requires_proxy=True,
    ),
    # ── Official Ukrainian pre-war name register ──────────────────────────────
    SourceEntry(
        url="https://streets.in.ua/rename.php?town_code=mariup",
        source_type="register",
        title="streets.in.ua — Mariupol 2016 decommunization rename register",
        description=(
            "79 pairs mapping Soviet-era names to 2016 Ukrainian decommunization names. "
            "Used inverted (Soviet = probable occupation revert target; "
            "Ukrainian = prewar name) to corroborate decree entries."
        ),
        requires_proxy=False,
    ),
    # ── News / reporting sources ──────────────────────────────────────────────
    SourceEntry(
        url="https://armyinform.com.ua/2023/02/03/okupanty-zminyuyut-nazvy-vulycz-navit-z-imenamy-radyanskyh-geroyiv/",
        source_type="news_article",
        title="ArmyInform (Ukrainian MoD): Occupiers rename streets even with Soviet heroes' names (Feb 2023)",
        description=(
            "Ukrainian Ministry of Defence outlet. Confirms площа Ленінського "
            "комсомолу and вул. Дзержинського renames; mentions Sverdlov, Vorovsky etc."
        ),
        requires_proxy=False,
    ),
    SourceEntry(
        url="https://khpg.org/en/1608814070",
        source_type="news_article",
        title="KHPG — Kharkiv Human Rights Protection Group: Mariupol street renames",
        description=(
            "Human rights reporting confirming Azovstalska→Tula rename and "
            "~101 total renames; mentions Hrushevsky→60 Years of USSR."
        ),
        requires_proxy=False,
    ),
    SourceEntry(
        url="https://www.donetsk.kp.ru/daily/27391/4585348/",
        source_type="news_article",
        title="KP.ru (Komsomolskaya Pravda Donetsk): Mariupol street renames",
        description=(
            "Russian-language pro-occupation source. Confirms площадь Ленинского "
            "Комсомола, ул. Урицкого, ул. 60 лет СССР renames; cites Mar 16 2022 date."
        ),
        requires_proxy=False,
    ),
    SourceEntry(
        url=(
            "https://web.archive.org/web/20260412065144/"
            "https://www.radiosvoboda.org/a/novyny-pryazovya-rosiya-povertaye-radyanski-nazvy-v-okupatsiyi/33073708.html"
        ),
        source_type="news_article",
        title="Radio Svoboda Pryazovya (Wayback): Russia restores Soviet street names (archived 2026-04-12)",
        description=(
            "Wayback Machine archive of Radio Svoboda Pryazovya article on occupation "
            "street renames. Original URL was 403-blocked; this is the archived copy."
        ),
        requires_proxy=False,
    ),
]


def _ext_from_url(url: str) -> str:
    """Quick heuristic: return likely content-type from URL path, for logging only."""
    if url.lower().endswith(".pdf"):
        return "application/pdf"
    return "text/html"


def run_capture(proxy: str | None = None) -> None:
    con = open_state()
    already = {r["url"] for r in list_sources(con)}
    session = requests.Session()
    if proxy:
        session.proxies = {"http": proxy, "https": proxy}
    session.headers["User-Agent"] = config.USER_AGENT

    skipped = captured = failed = 0
    for entry in SOURCE_CATALOGUE:
        if entry.url in already:
            log.info("SKIP (already captured): %s", entry.title)
            skipped += 1
            continue
        if entry.requires_proxy and not proxy:
            log.warning(
                "SKIP (proxy required, none set): %s — pass --proxy socks5h://… to capture",
                entry.title,
            )
            skipped += 1
            continue

        log.info("Fetching: %s", entry.url)
        try:
            r = session.get(entry.url, timeout=config.TIMEOUT, stream=False)
            content_type = r.headers.get("Content-Type", _ext_from_url(entry.url))
            sha = capture_source(
                r.content,
                url=entry.url,
                source_type=entry.source_type,
                title=entry.title,
                description=entry.description,
                content_type=content_type,
                http_status=r.status_code,
                con=con,
            )
            log.info(
                "CAPTURED %s  sha256=%s…  status=%d  bytes=%d",
                entry.title, sha[:16], r.status_code, len(r.content),
            )
            captured += 1
            time.sleep(2.0)
        except Exception as exc:
            log.error("FAILED %s: %s", entry.url, exc)
            failed += 1

    log.info("Done. captured=%d  skipped=%d  failed=%d", captured, skipped, failed)


def print_catalogue() -> None:
    con = open_state()
    rows = list_sources(con)
    if not rows:
        print("No sources captured yet. Run without --catalogue to download.")
        return
    print(f"{'#':<4} {'TYPE':<14} {'STATUS':<8} {'BYTES':>8}  {'SHA256[:12]':<14}  TITLE")
    print("-" * 100)
    for i, r in enumerate(rows, 1):
        p = __import__("pathlib").Path(r["raw_path"])
        size = p.stat().st_size if p.exists() else 0
        status = str(r["http_status"]) if r["http_status"] else "local"
        print(
            f"{i:<4} {r['source_type']:<14} {status:<8} {size:>8}  {r['sha256'][:12]:<14}  {r['title']}"
        )
    print(f"\nTotal: {len(rows)} source(s) captured to {config.RAW_DIR}")


def run_verify() -> None:
    from mariupol_seizures.forensics import sha256_bytes
    con = open_state()
    rows = list_sources(con)
    bad = []
    for r in rows:
        p = __import__("pathlib").Path(r["raw_path"])
        if not p.exists():
            bad.append((r["url"], "FILE MISSING"))
        elif sha256_bytes(p.read_bytes()) != r["sha256"]:
            bad.append((r["url"], "HASH MISMATCH"))
    if bad:
        for url, reason in bad:
            print(f"FAIL  {reason}  {url}")
        sys.exit(1)
    else:
        print(f"OK — {len(rows)} source(s) verified.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--catalogue", action="store_true", help="Print catalogue of captured sources and exit")
    ap.add_argument("--verify", action="store_true", help="Re-hash store and report mismatches")
    ap.add_argument("--proxy", default=config.PROXY or None,
                    help="SOCKS5/HTTP proxy for geoblocked sources (e.g. socks5h://user:pass@host:port)")
    args = ap.parse_args()

    if args.catalogue:
        print_catalogue()
    elif args.verify:
        run_verify()
    else:
        run_capture(proxy=args.proxy)


if __name__ == "__main__":
    main()
