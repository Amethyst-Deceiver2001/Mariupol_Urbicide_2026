"""Source 4 — YouTube search (candidate discovery; download is scripts/321).

yt-dlp flat search over the address variants (RU + transliterated) surfaces
candidate walkthrough / siege-footage / drone videos. This module does
metadata-only discovery (fast, --flat-playlist), captures the search-result
listing, and writes a candidate list to the sweep dir. It does NOT download
videos — that's the deliberate, heavier scripts/321 → 322 pipeline
(download → whisper transcript → address-timecode index → stills), which
the user runs. The dossier links each candidate + the exact 321 command.

RUN=U (external network + hands to a long pipeline).
"""
from __future__ import annotations

import json
import logging
import subprocess

from ... import config, forensics
from .base import SourceResult

log = logging.getLogger(__name__)

NAME = "youtube"
RUN = "U"
NETWORK = True
DESCRIPTION = "yt-dlp search for candidate videos (download = scripts/321)"

RESULTS_PER_QUERY = 8


def plan(bundle) -> str:
    return f"yt-dlp ytsearch{RESULTS_PER_QUERY}: over RU + translit variants, list candidates"


def _search_queries(bundle) -> list[str]:
    qs: list[str] = []
    # RU street + house, plus the ЖК/newbuild name if present, plus translit
    base = bundle.occupation_address or bundle.prewar_address or ""
    if base:
        qs.append(f"Мариуполь {base}")
        qs.append(f"Мариуполь {base} снос")
    for v in bundle.variants:
        if v.lang == "translit":
            qs.append(f"Mariupol {v.text}")
            break
    return list(dict.fromkeys(qs))[:4]


def fetch(bundle, con, radius_m: float = 0.0) -> SourceResult:
    try:
        subprocess.run(["yt-dlp", "--version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return SourceResult(NAME, True, "skipped — yt-dlp not installed "
                                        "(pip install -e '.[media]')")

    findings: list[dict] = []
    captured: list[str] = []
    for q in _search_queries(bundle):
        cmd = ["yt-dlp", f"ytsearch{RESULTS_PER_QUERY}:{q}",
               "--flat-playlist", "--dump-single-json", "--no-warnings"]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        except subprocess.TimeoutExpired:
            log.warning("yt-dlp search timed out for %r", q)
            continue
        if r.returncode != 0 or not r.stdout.strip():
            log.debug("yt-dlp search empty/failed for %r: %s", q, r.stderr[-300:])
            continue
        captured.append(forensics.capture_source(
            r.stdout.encode("utf-8"), url=f"ytsearch:{q}",
            source_type="osint_youtube_search",
            title=f"youtube search {q!r}",
            description=f"yt-dlp flat search {q!r} for pid={bundle.pid}.",
            content_type="application/json", http_status=200, con=con,
        ))
        try:
            data = json.loads(r.stdout)
        except json.JSONDecodeError:
            continue
        for entry in data.get("entries", []):
            vid = entry.get("id", "")
            findings.append({
                "kind": "youtube_candidate", "query": q,
                "video_id": vid, "title": entry.get("title", ""),
                "channel": entry.get("channel", entry.get("uploader", "")),
                "duration": entry.get("duration"),
                "url": f"https://www.youtube.com/watch?v={vid}",
            })

    ids = sorted({f["video_id"] for f in findings if f.get("video_id")})
    if ids:
        out_dir = config.DATA_DIR / "reports" / "osint" / bundle.slug
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "youtube_candidates.txt").write_text(
            "\n".join(ids) + "\n", encoding="utf-8")
        findings.append({
            "kind": "youtube_next_step",
            "note": f"{len(ids)} candidate video IDs written to "
                    f"youtube_candidates.txt — review, then add the relevant "
                    f"ones to scripts/321 (download → transcript → stills)",
            "candidate_ids": ids,
        })

    return SourceResult(NAME, True,
                        f"{len(ids)} candidate videos across "
                        f"{len(_search_queries(bundle))} queries",
                        findings, captured)
