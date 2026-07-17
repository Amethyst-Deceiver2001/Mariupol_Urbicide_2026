"""Source 22 — cross-source death-record aggregator, local tier
(docs/address_osint_assistant_design.md §Death records).

Queries the corpora ALREADY captured/integrated — no network:
  1. Mariupol Destruction and Victims Map TSV (scripts/299 capture, located
     via source_document; columns: место проживания/смерти/захоронения).
  2. grave-sites master evidence CSV (scripts/308 — the 3-source merge).
  3. memorial.ua obituaries jsonl (scripts/305-306; UA-language text, so UA
     street variants matter here).
  4. @mariupolRIP parsed messages (scripts/303).
  5. @kadryVoynyMariypol2022 raw store (scripts/317; the "Известные имена
     погибших" digests — matched the same way scripts/323 does).

Dedup: hits are grouped by extracted victim-name string when one is
present (NAME_START_RE shape, same as scripts/309); different sources
naming the same person merge into one finding with a source list. Fuzzy
cross-name merging is deliberately NOT done — confidence-score, never
silently merge two similar names (project rule).
"""
from __future__ import annotations

import csv
import json
import logging
import re
import sqlite3
from pathlib import Path

from ... import config
from ..variants import match_regexes
from .base import SourceResult

log = logging.getLogger(__name__)

NAME = "death_records"
RUN = "C"
NETWORK = False
DESCRIPTION = "named victims/deaths/burials at this address across all local corpora"

NAME_RE = re.compile(
    r"(?:✝️\s*)?([А-ЯЁІЇЄ][а-яёіїє'’]{2,20}\s+[А-ЯЁІЇЄ][а-яёіїє'’]{2,20}"
    r"(?:\s+[А-ЯЁІЇЄ][а-яёіїє'’]{2,20})?)"
)
DEATH_RE = re.compile(
    r"погиб\w*|умер\w*|скончал\w*|убит\w*|не стало|ушел из жизни|ушёл из жизни|"
    r"пропал\w*|похорон\w*|захорон\w*|загинул\w*|помер\w*",
    re.IGNORECASE,
)


def plan(bundle) -> str:
    return "grep victims TSV + grave master CSV + memorial.ua + mariupolRIP + kadryVoyny (all local)"


def _victims_tsv_path(scon: sqlite3.Connection) -> Path | None:
    row = scon.execute(
        "SELECT raw_path FROM source_document "
        "WHERE source_type IN ('mariupoldestruction_victims_tsv',"
        "                      'mariupoldestruction_victims_full_sheet') "
        "ORDER BY captured_at DESC LIMIT 1"
    ).fetchone()
    if not row or not row[0]:
        return None
    p = Path(row[0])
    return p if p.exists() else None


def _pull_name(text: str) -> str | None:
    m = NAME_RE.search(text)
    return m.group(1) if m else None


_STOP_WORDS = {"Над", "Под", "При", "Известные", "Имена", "Хроника", "Кадры"}


def _pull_name_near(text: str, match_start: int) -> str | None:
    """Name nearest the address match, not the first in the message —
    digest posts ('Известные имена погибших...') list many victims at many
    addresses; attributing the message's first name to OUR address match is
    wrong (caught on @kadryVoynyMariypol2022 msg 636: Алфёрова died at
    пр. Мира 86, the Зелинского 17а victим is further down).

    Two fixes layered on top of "search the containing line":
    1. Many digests are a SINGLE line with '|'-separated event/address
       bullets ("10 | событие | адрес | событие | адрес ..."); splitting
       only on '\\n' made the whole line one giant search window, so a
       capitalized-word-pair ANYWHERE in the line (even the first bullet)
       could be returned as "nearest" — caught 2026-07-16 on pid 4841,
       msg with no newlines at all matched a name from bullet 1 onto an
       address from bullet 4. Split on '|' too, and use the segment
       actually containing match_start, not the whole line.
    2. Require death language (or a ✝️ marker) in the same segment or an
       immediate neighbor before accepting a name at all — otherwise a
       capitalized two-word phrase that isn't a death record at all gets
       returned (caught same day: "Разграбили Обжору" — "[they] looted
       [the café] Obzhora", a burglary note with zero death language,
       matched purely on capitalization shape). No death language nearby
       -> return None, the caller then records an anonymous
       address_mention instead of fabricating a named victim.
    """
    line_start = text.rfind("\n", 0, match_start) + 1
    line_end = text.find("\n", match_start)
    line = text[line_start:line_end if line_end != -1 else len(text)]
    segments = [s.strip() for s in line.split("|")]
    # locate the segment containing match_start (offsets within `line`)
    rel = match_start - line_start
    offset, seg_idx = 0, 0
    for i, seg in enumerate(line.split("|")):
        if offset <= rel < offset + len(seg) + 1:
            seg_idx = i
            break
        offset += len(seg) + 1
    ordered_segments = ([segments[seg_idx]] +
                        segments[seg_idx - 1::-1] if seg_idx > 0 else [segments[seg_idx]])
    prior_lines = reversed(text[:line_start].splitlines())
    for cand in (*ordered_segments, *prior_lines):
        m = NAME_RE.search(cand)
        if not m:
            continue
        name = m.group(1)
        if name.split()[0] in _STOP_WORDS:
            continue
        if DEATH_RE.search(cand) or "✝️" in cand:
            return name
        # name-shaped but no death language in its own segment — still
        # worth a look at the immediate next segment (many digests put the
        # verb before the name: "погиб ... капитан Валерий Лесной")
    return None


def fetch(bundle, con, radius_m: float = 150.0) -> SourceResult:
    regexes = match_regexes(bundle)
    if not regexes:
        return SourceResult(NAME, False, "no matchable street stem for this address")
    hits: list[dict] = []

    def matched(text: str) -> re.Pattern | None:
        return next((rx for rx in regexes if rx.search(text)), None)

    # 1 — victims TSV
    tsv = _victims_tsv_path(con)
    if tsv:
        delim = "\t" if tsv.suffix != ".csv" else ","
        try:
            with tsv.open(encoding="utf-8", errors="replace") as fh:
                rdr = csv.reader(fh, delimiter=delim)
                header = next(rdr, [])
                for row in rdr:
                    line = delim.join(row)
                    if matched(line) is None:
                        continue
                    rec = dict(zip(header, row))
                    # name lives in the "Фамилия Имя Отчество" column, NOT
                    # positionally at row[0] — this sheet has a blank leading
                    # column that isn't always empty (e.g. carries a "б/в"
                    # missing-without-trace status marker on some rows),
                    # which silently became the "victim name" when read
                    # positionally (caught 2026-07-16 on pid 10640).
                    name_val = next((rec[k] for k in rec if "фамилия" in k.lower()
                                     and rec[k] and rec[k].strip()), None)
                    hits.append({
                        "source": "victims_tsv",
                        "victim_name": name_val.strip() if name_val else None,
                        "date": next((rec[k] for k in rec if "смерти" in k.lower() and rec[k]), ""),
                        "detail": {k: v for k, v in rec.items() if v},
                        "url": next((v for v in rec.values() if "t.me/" in v or "http" in v), ""),
                    })
        except Exception:  # noqa: BLE001
            log.warning("victims TSV scan failed (%s)", tsv, exc_info=True)
    else:
        log.warning("victims TSV not found in raw store — run scripts/299 first")

    # 2 — grave master CSV (already pid-matched by scripts/301/308)
    master = config.DATA_DIR / "reports" / "grave_sites_master_evidence.csv"
    if master.exists():
        with master.open(encoding="utf-8") as fh:
            for rec in csv.DictReader(fh):
                pid_match = (bundle.pid is not None
                             and rec.get("property_id", "").strip() == str(bundle.pid))
                if not pid_match and matched(",".join(rec.values())) is None:
                    continue
                hits.append({
                    "source": "grave_master",
                    "victim_name": rec.get("victim_name") or None,
                    "date": rec.get("event_date", ""),
                    "url": rec.get("evidence_url", ""),
                    "excerpt": (rec.get("quote") or "")[:200],
                    "via": rec.get("source", ""),
                })

    # 3 — memorial.ua (UA text — the UA variants in match_regexes carry this)
    mem = config.DATA_DIR / "parsed" / "memorial_ua_obituaries.jsonl"
    if mem.exists():
        with mem.open(encoding="utf-8") as fh:
            for line in fh:
                if matched(line) is None:
                    continue
                try:
                    row = json.loads(line)
                except Exception:  # noqa: BLE001
                    continue
                blob = " ".join(str(v) for v in row.values())
                rx = matched(blob)
                if rx is None:
                    continue
                hits.append({
                    "source": "memorial_ua",
                    "victim_name": row.get("name"),
                    "date": row.get("death_date", ""),
                    "url": row.get("url", ""),
                    "excerpt": _around(blob, rx),
                })

    # 4 — mariupolRIP parsed messages
    rip = config.DATA_DIR / "parsed" / "mariupolrip_messages.jsonl"
    if rip.exists():
        with rip.open(encoding="utf-8") as fh:
            for line in fh:
                if matched(line) is None:
                    continue
                try:
                    row = json.loads(line)
                except Exception:  # noqa: BLE001
                    continue
                text = row.get("text") or ""
                rx = matched(text)
                if rx is None:
                    continue
                hits.append({
                    "source": "mariupolRIP",
                    "victim_name": _pull_name_near(text, rx.search(text).start()),
                    "death_language": bool(DEATH_RE.search(text)),
                    "date": str(row.get("date", ""))[:10],
                    "url": row.get("url", ""),
                    "excerpt": _around(text, rx),
                })

    # 5 — kadryVoyny raw store (same access pattern as scripts/323)
    krows = con.execute(
        "SELECT url, raw_path FROM source_document "
        "WHERE source_type='telegram_kadryvoyny_msg'"
    ).fetchall()
    for url, raw_path in krows:
        if not raw_path:
            continue
        p = Path(raw_path)
        if not p.is_absolute():
            p = config.PROJECT_ROOT / raw_path
        if not p.exists():
            continue
        try:
            obj = json.loads(p.read_bytes())
        except Exception:  # noqa: BLE001
            continue
        text = (obj.get("message") or "")
        rx = matched(text)
        if rx is None:
            continue
        hits.append({
            "source": "kadryVoyny",
            "victim_name": _pull_name_near(text, rx.search(text).start()),
            "death_language": bool(DEATH_RE.search(text)),
            "date": (obj.get("date") or "")[:10],
            "url": url,
            "excerpt": _around(text, rx),
        })

    # group by victim name (exact-string, per project fuzzy-merge rule)
    grouped: dict[str, dict] = {}
    anon: list[dict] = []
    for h in hits:
        nm = (h.get("victim_name") or "").strip()
        if nm:
            g = grouped.setdefault(nm, {"kind": "victim", "victim_name": nm,
                                        "sources": [], "records": []})
            g["sources"].append(h["source"])
            g["records"].append(h)
        else:
            anon.append({"kind": "address_mention", **h})
    findings = list(grouped.values()) + anon
    for g in grouped.values():
        g["sources"] = sorted(set(g["sources"]))

    return SourceResult(
        NAME, True,
        f"{len(grouped)} named victims, {len(anon)} unnamed address mentions "
        f"across {len(set(h['source'] for h in hits)) if hits else 0} local sources",
        findings)


def _around(text: str, rx: re.Pattern, width: int = 180) -> str:
    m = rx.search(text)
    if not m:
        return text[:width]
    a = max(0, m.start() - width // 3)
    return text[a:a + width].replace("\n", " | ")
