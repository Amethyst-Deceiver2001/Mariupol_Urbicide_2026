"""Source 1 — Telegram LOCAL corpus search (all already-captured channels).

The cheapest Telegram tier (design §budget): grep every parsed jsonl corpus
AND every raw telegram_*_msg store already on disk for the address, before
spending any live/budgeted search. Distinct from local_evidence's lighter
4-file corpus scan — this walks the full set (all channels this project has
ever crawled), matched via the same fixed variant regexes.
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
from pathlib import Path

from ... import config
from ..variants import match_regexes, street_stems
from .base import SourceResult

log = logging.getLogger(__name__)

NAME = "telegram_local"
RUN = "C"
NETWORK = False
DESCRIPTION = "search ALL already-captured Telegram corpora (free, no budget spend)"

# raw-store source_types that hold one Telegram message per row
RAW_MSG_SOURCE_TYPES = (
    "telegram_kadryvoyny_msg", "telegram_mariupolrip_msg", "telegram_nash_msg",
    "telegram_nmrpl_msg", "telegram_ssaniaworld_msg",
)


def plan(bundle) -> str:
    return "grep data/parsed/*.jsonl chat corpora + raw telegram_*_msg stores"


def _iter_parsed_jsonl():
    d = config.DATA_DIR / "parsed"
    for p in sorted(d.glob("*.jsonl")):
        # skip obvious non-message corpora
        if any(k in p.name for k in ("manifest", "graph", "survey", "intel_records")):
            continue
        yield p


def _byte_probes(stems: set[str]) -> list[bytes]:
    """Superset byte-substring probes for a cheap pre-filter over large raw
    corpora: each stem expanded across RU↔UA letter drift (и/і, е/є/ё,
    ь-before-к) in both lowercase and first-capital forms. A file whose raw
    bytes contain NONE of these can't match the full regex, so it's skipped
    without a json.loads (the expensive step on 200K-file stores)."""
    out: set[bytes] = set()
    for stem in stems:
        variants = {stem}
        for a, subs in (("и", "иі"), ("е", "еєё")):
            grown = set()
            for v in variants:
                for ch in subs:
                    grown.add(v.replace(a, ch))
            variants |= grown
        soft = set()
        for v in variants:
            soft.add(v.replace("ск", "ськ"))
            soft.add(v.replace("ськ", "ск"))
        variants |= soft
        for v in variants:
            out.add(v.encode("utf-8"))
            out.add(v.capitalize().encode("utf-8"))
    return list(out)


def fetch(bundle, con, radius_m: float = 0.0) -> SourceResult:
    regexes = match_regexes(bundle)
    if not regexes:
        return SourceResult(NAME, False, "no matchable street stem")

    def matched(text: str) -> re.Pattern | None:
        return next((rx for rx in regexes if rx.search(text)), None)

    findings: list[dict] = []
    seen_urls: set[str] = set()
    corpora_hit: set[str] = set()

    # parsed jsonl corpora
    for p in _iter_parsed_jsonl():
        with p.open(encoding="utf-8") as fh:
            for line in fh:
                if matched(line) is None:
                    continue
                try:
                    row = json.loads(line)
                except Exception:  # noqa: BLE001
                    continue
                text = row.get("text") or row.get("message") or ""
                rx = matched(text)
                if rx is None:
                    continue
                url = row.get("url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                corpora_hit.add(p.name)
                if len([f for f in findings if f["corpus"] == p.name]) < 30:
                    findings.append({
                        "kind": "telegram_mention", "corpus": p.name,
                        "url": url, "date": str(row.get("date", ""))[:10],
                        "excerpt": _around(text, rx),
                    })

    # raw message stores (channels only text-crawled, never parsed to jsonl).
    # These run to 200K+ individual files (nash ~159K, nmrpl ~45K). Two-stage:
    # a cheap byte-substring pre-filter gates the expensive json.loads, and
    # the file reads (the I/O-bound floor) run in a thread pool.
    from concurrent.futures import ThreadPoolExecutor

    probes = _byte_probes(street_stems(bundle))

    def _probe_file(args):
        url, raw_path, st = args
        fp = Path(raw_path)
        if not fp.is_absolute():
            fp = config.PROJECT_ROOT / raw_path
        try:
            data = fp.read_bytes()
        except OSError:
            return None
        if not any(p in data for p in probes):
            return None       # cheap reject — no street stem in the raw bytes
        return (url, st, data)

    scon = sqlite3.connect(config.STATE_DB)
    tasks = []
    for st in RAW_MSG_SOURCE_TYPES:
        for url, raw_path in scon.execute(
            "SELECT url, raw_path FROM source_document WHERE source_type=?", (st,)
        ).fetchall():
            if raw_path and url not in seen_urls:
                tasks.append((url, raw_path, st))
    scon.close()

    per_corpus: dict[str, int] = {}
    with ThreadPoolExecutor(max_workers=16) as pool:
        for hit in pool.map(_probe_file, tasks, chunksize=256):
            if hit is None:
                continue
            url, st, data = hit
            try:
                obj = json.loads(data)
            except Exception:  # noqa: BLE001
                continue
            text = obj.get("message") or ""
            rx = matched(text)
            if rx is None:
                continue
            seen_urls.add(url)
            corpora_hit.add(st)
            per_corpus[st] = per_corpus.get(st, 0) + 1
            if per_corpus[st] <= 30:
                findings.append({
                    "kind": "telegram_mention", "corpus": st,
                    "url": url, "date": (obj.get("date") or "")[:10],
                    "excerpt": _around(text, rx),
                })

    return SourceResult(NAME, True,
                        f"{len(findings)} mentions across {len(corpora_hit)} corpora "
                        f"({len(tasks)} raw files scanned)",
                        findings)


def _around(text: str, rx: re.Pattern, width: int = 170) -> str:
    m = rx.search(text)
    if not m:
        return text[:width]
    a = max(0, m.start() - width // 3)
    return text[a:a + width].replace("\n", " | ")
