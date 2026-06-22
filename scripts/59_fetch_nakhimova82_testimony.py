#!/usr/bin/env python3
"""Capture two Telegram posts bearing on the Нахимова 82 case (Exhibit A).

Tier-3 corroboration layer, sub-layer S5 (testimony_ref, currently pure
design in docs/tier3_corroboration_design.md). These are the first two
candidate testimony/admission artifacts for that sub-layer:

  - t.me/olegtsarov/9754 (27 Dec 2023, 180K views): reader testimony naming
    "Нахимова, 82" directly -- former OSMD-managed building demolished,
    rebuilt as a mortgage development, sold off, no former owner retained a
    unit; complaints to Russian federal bodies redirected back to the DNR.
  - t.me/mariupol24tv/104461 (3 Oct 2025, 1.52K views): occupation-
    administration press item -- the replacement building at "просп.
    Нахимова, 82" won a bronze diploma at the "АРХИТАВР" architecture
    competition; AGO Mariupol's head of city-planning/architecture,
    Natalya Klochkova, frames it as part of "transforming Mariupol into a
    modern comfortable Russian city".

Both are public Telegram channels -- the `?embed=1` widget renders the post
as static server-side HTML with no auth, same non-geoblocked-host precedent
as scripts 52/54-58 (Claude runs this directly; no VPS needed).

Output: data/raw/<sha256>.html + .meta.json for each post (forensics
capture_source(), logged to data/state.sqlite's source_document table), plus
a small manifest at data/parsed/nakhimova82_testimony_manifest.json mapping
each post to its sha256/raw_path for downstream reference (e.g. a future
testimony_ref corroboration row, or citation in docs/exhibits/).

Idempotent: re-running re-fetches (Telegram view counts/reactions drift) but
capture_source() only writes new bytes if the SHA-256 changed; the manifest
is rewritten each run with the latest capture for each URL.
"""
import json
import logging
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger("fetch_nakhimova82_testimony")

MANIFEST_PATH = config.DATA_DIR / "parsed" / "nakhimova82_testimony_manifest.json"
REQUEST_PAUSE_S = 1.0

TARGETS = [
    {
        "url": "https://t.me/olegtsarov/9754?embed=1",
        "canonical_url": "https://t.me/olegtsarov/9754",
        "source_type": "telegram_post",
        "title": "Олег Царёв channel, post 9754 (27 Dec 2023) -- "
                 "Mariupol housing-distribution testimony incl. Нахимова, 82",
        "description": (
            "Telegram post by Oleg Tsarev (180K views, edited), relaying "
            "reader testimony about unfair post-occupation housing "
            "distribution in Mariupol. One quoted comment names "
            "Нахимова, 82 directly: "
            "the OSMD-managed building was demolished, rebuilt as a "
            "mortgage development, and sold off with no former owner "
            "retaining a unit; complaints to the Russian Investigative "
            "Committee, Prosecutor's Office, Presidential Administration "
            "and a United Russia deputy were all redirected back to the "
            "DNR. Candidate testimony_ref for property 5865 "
            "(docs/exhibits/nakhimova-82-exhibit.html, 'Exhibit A')."
        ),
    },
    {
        "url": "https://t.me/mariupol24tv/104461?embed=1",
        "canonical_url": "https://t.me/mariupol24tv/104461",
        "source_type": "telegram_post",
        "title": "МАРИУПОЛЬ 24 channel, post 104461 (3 Oct 2025) -- "
                 "АРХИТАВР architecture award for просп. Нахимова, 82 rebuild",
        "description": (
            "Telegram post by the occupation-administration-aligned "
            "channel МАРИУПОЛЬ 24 (1.52K views), announcing that the "
            "replacement multi-apartment building at просп. "
            "Нахимова, 82 (design by Проектный институт Архитектуры и "
            "Строительства) "
            "won a bronze diploma at the XVII Forum of Architects of South "
            "Russia and the North Caucasus ('Архитавр'). "
            "Quotes Natalya Klochkova, AGO Mariupol's head of "
            "city-planning/architecture, framing the award as part of "
            "'transforming Mariupol into a modern comfortable Russian city'. "
            "Source line: НМ! / АГО Мариуполь. Same footprint as the "
            "demolition described in t.me/olegtsarov/9754 -- "
            "demolish->rebuild->award, 2023-2025."
        ),
    },
]


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"generated_at": None, "posts": []}


def save_manifest(manifest: dict) -> None:
    from datetime import datetime, timezone

    manifest["generated_at"] = datetime.now(timezone.utc).isoformat()
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def fetch(url: str) -> tuple[bytes, str, int]:
    """Return (content, content_type, http_status). Retries transient errors."""
    for attempt in range(config.MAX_RETRIES):
        try:
            resp = requests.get(
                url,
                headers={"User-Agent": config.USER_AGENT},
                timeout=config.TIMEOUT,
                allow_redirects=True,
            )
            resp.raise_for_status()
            return resp.content, resp.headers.get("Content-Type", "text/html"), resp.status_code
        except requests.exceptions.RequestException as exc:
            if attempt == config.MAX_RETRIES - 1:
                raise
            log.warning("transient error fetching %s (attempt %d/%d): %s -- retrying",
                         url, attempt + 1, config.MAX_RETRIES, exc)
            time.sleep(2.0 * (attempt + 1))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")

    state = forensics.open_state()
    manifest = load_manifest()
    posts = []

    for target in TARGETS:
        log.info("Fetching %s", target["url"])
        content, content_type, http_status = fetch(target["url"])
        sha = forensics.capture_source(
            content,
            url=target["canonical_url"],
            source_type=target["source_type"],
            title=target["title"],
            description=target["description"],
            content_type=content_type,
            http_status=http_status,
            con=state,
        )
        raw_path = str((config.RAW_DIR / f"{sha}.html").relative_to(config.PROJECT_ROOT))
        log.info("  captured -> %s (sha256=%s, %d bytes)", raw_path, sha, len(content))
        posts.append({
            "url": target["canonical_url"],
            "title": target["title"],
            "sha256": sha,
            "raw_path": raw_path,
            "content_length": len(content),
            "http_status": http_status,
        })
        time.sleep(REQUEST_PAUSE_S)

    manifest["posts"] = posts
    save_manifest(manifest)
    state.close()
    log.info("Done -> %s", MANIFEST_PATH)


if __name__ == "__main__":
    main()
