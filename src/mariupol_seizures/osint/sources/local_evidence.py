"""Source 0 — assemble everything the project ALREADY holds for the address.

Purely local (Postgres + files under data/). No captures — the artifacts
already live in the raw store; this module's findings are the dossier's
"already-held evidence" header that separates new finds from old.

Covers: spine property row, seizure_event stages, corroboration families,
unit rows (if the two-tier schema is applied), DEMOLITION_NEWBUILD_CROSSWALK
membership (parsed side-effect-free out of scripts/164 via ast), nearby
ЕИСЖС newbuild objects, and chat-corpus mentions (parsed jsonl greps).
"""
from __future__ import annotations

import ast
import json
import logging
import re
from pathlib import Path

from ... import config
from ..variants import match_regexes
from .base import SourceResult, find_urls, haversine_m, is_geoblocked

log = logging.getLogger(__name__)

NAME = "local_evidence"
RUN = "C"
NETWORK = False
DESCRIPTION = "spine/corroboration/crosswalk/ЕИСЖС/chat-corpus — what we already hold"

_CORPUS_JSONL = [
    "mariupolrip_messages.jsonl",
    "testimony_full_all_chats.jsonl",
    "kadryvoyny_property_matched.jsonl",
    "nash_flagged_messages.jsonl",
]


def plan(bundle) -> str:
    return (f"query Postgres for pid={bundle.pid}; parse scripts/164 crosswalk; "
            f"scan ЕИСЖС geojson ≤200m; grep {len(_CORPUS_JSONL)} parsed corpora")


def _crosswalk_entries() -> list[dict]:
    """DEMOLITION_NEWBUILD_CROSSWALK from scripts/164, without importing
    (module name starts with a digit; import would also risk side effects).
    ast.literal_eval on the assignment keeps this read-only and safe."""
    path = config.PROJECT_ROOT / "scripts" / "164_export_map_layers.py"
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name) and t.id == "DEMOLITION_NEWBUILD_CROSSWALK":
                        return ast.literal_eval(node.value)
    except Exception:  # noqa: BLE001
        log.warning("could not parse crosswalk out of %s", path, exc_info=True)
    return []


def collect_source_urls(bundle) -> list[dict]:
    """Every original-source URL on record for this property: the
    `seizure_event.source_doc_id -> source_document.url` join (the court/
    decree/register crawlers' own capture target) PLUS any URL embedded in
    `seizure_event.detail` or `corroboration.detail` JSONB (registry-style
    loaders that never got a matching source_document row store the URL
    directly in detail instead — scanned via find_urls() rather than a
    fixed key name, since that key isn't consistent across loaders).

    Deduped by URL. Each row is tagged `geoblocked` per base.is_geoblocked()
    so the dossier can badge which links need the user's Russia-routed
    access to actually open — CLAUDE.md: always hyperlink regardless, the
    badge is informational, never a reason to omit the link.
    """
    if bundle.pid is None:
        return []
    import psycopg2
    import psycopg2.extras

    pcon = psycopg2.connect(config.DATABASE_URL)
    seen: dict[str, dict] = {}
    try:
        cur = pcon.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """SELECT se.stage, se.event_date, sd.url, sd.kind
               FROM seizure_event se JOIN source_document sd
                    ON sd.id = se.source_doc_id
               WHERE se.property_id=%s AND sd.url IS NOT NULL""",
            (bundle.pid,),
        )
        for r in cur.fetchall():
            seen.setdefault(r["url"], {
                "url": r["url"], "via": f"seizure_event:{r['stage']}",
                "source_kind": r["kind"], "date": str(r["event_date"] or ""),
                "geoblocked": is_geoblocked(r["url"]),
            })

        cur.execute(
            """SELECT stage, event_date, detail FROM seizure_event
               WHERE property_id=%s AND detail IS NOT NULL""",
            (bundle.pid,),
        )
        for r in cur.fetchall():
            for url in find_urls(r["detail"]):
                seen.setdefault(url, {
                    "url": url, "via": f"seizure_event.detail:{r['stage']}",
                    "source_kind": "", "date": str(r["event_date"] or ""),
                    "geoblocked": is_geoblocked(url),
                })

        cur.execute(
            """SELECT kind, detail FROM corroboration WHERE property_id=%s
               AND detail IS NOT NULL""",
            (bundle.pid,),
        )
        for r in cur.fetchall():
            for url in find_urls(r["detail"]):
                seen.setdefault(url, {
                    "url": url, "via": f"corroboration:{r['kind']}",
                    "source_kind": "", "date": "",
                    "geoblocked": is_geoblocked(url),
                })
    finally:
        pcon.close()
    return sorted(seen.values(), key=lambda r: (not r["geoblocked"], r["url"]))


def fetch(bundle, con, radius_m: float = 150.0) -> SourceResult:
    findings: list[dict] = []

    for src in collect_source_urls(bundle):
        findings.append({"kind": "source_document", **src})

    # ── Postgres: spine row + events + corroboration ───────────────────────
    import psycopg2
    import psycopg2.extras

    pcon = psycopg2.connect(config.DATABASE_URL)
    try:
        cur = pcon.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if bundle.pid is not None:
            cur.execute(
                """SELECT stage, COUNT(*) AS n, MIN(event_date) AS first,
                          MAX(event_date) AS last
                   FROM seizure_event WHERE property_id=%s
                   GROUP BY stage ORDER BY stage""",
                (bundle.pid,),
            )
            for r in cur.fetchall():
                findings.append({
                    "kind": "seizure_stage", "stage": r["stage"], "count": r["n"],
                    "first": str(r["first"] or ""), "last": str(r["last"] or ""),
                })
            cur.execute(
                """SELECT kind, COUNT(*) AS n FROM corroboration
                   WHERE property_id=%s GROUP BY kind ORDER BY n DESC""",
                (bundle.pid,),
            )
            for r in cur.fetchall():
                findings.append({"kind": "corroboration_family",
                                 "family": r["kind"], "count": r["n"]})
            try:
                cur.execute("SELECT COUNT(*) AS n FROM unit WHERE property_id=%s",
                            (bundle.pid,))
                n_units = cur.fetchone()["n"]
                if n_units:
                    findings.append({"kind": "units", "count": n_units})
            except Exception:  # noqa: BLE001 — unit table optional (two-tier P1)
                pcon.rollback()
    finally:
        pcon.close()

    # ── crosswalk membership ───────────────────────────────────────────────
    for entry in _crosswalk_entries():
        if entry.get("property_id") == bundle.pid:
            findings.append({"kind": "crosswalk", **{k: entry[k] for k in
                             ("eisghs_id", "demolished_building_id") if k in entry},
                             "note": (entry.get("note") or "")[:300]})

    # ── nearby ЕИСЖС newbuilds ─────────────────────────────────────────────
    gj = config.DATA_DIR / "exports" / "qgis" / "eisghs_newbuilds.geojson"
    if gj.exists():
        try:
            data = json.loads(gj.read_text(encoding="utf-8"))
            for f in data.get("features", []):
                geom = f.get("geometry") or {}
                if geom.get("type") != "Point":
                    continue
                lon, lat = geom["coordinates"][:2]
                d = haversine_m(bundle.lat, bundle.lon, lat, lon)
                if d <= 200:
                    p = f.get("properties", {})
                    findings.append({
                        "kind": "eisghs_nearby",
                        "eisghs_id": p.get("eisghs_id") or p.get("id"),
                        "address": p.get("address") or p.get("declared_address"),
                        "developer": p.get("developer") or p.get("dev_name"),
                        "distance_m": round(d, 1),
                    })
        except Exception:  # noqa: BLE001
            log.warning("eisghs geojson scan failed", exc_info=True)

    # ── chat-corpus grep ───────────────────────────────────────────────────
    regexes = match_regexes(bundle)
    for fname in _CORPUS_JSONL:
        path = config.DATA_DIR / "parsed" / fname
        if not path.exists():
            continue
        n_hits = 0
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                if not any(rx.search(line) for rx in regexes):
                    continue
                try:
                    row = json.loads(line)
                except Exception:  # noqa: BLE001
                    continue
                text = row.get("text") or ""
                mrx = next((rx for rx in regexes if rx.search(text)), None)
                if mrx is None:      # matched only in url/meta noise
                    continue
                n_hits += 1
                if n_hits <= 40:
                    findings.append({
                        "kind": "corpus_mention", "corpus": fname,
                        "url": row.get("url", ""), "date": str(row.get("date", ""))[:10],
                        "excerpt": _excerpt(text, mrx),
                    })
        if n_hits > 40:
            findings.append({"kind": "corpus_mention_overflow", "corpus": fname,
                             "total_hits": n_hits, "shown": 40})

    n_stage = sum(1 for f in findings if f["kind"] == "seizure_stage")
    n_corp = sum(1 for f in findings if f["kind"] == "corpus_mention")
    n_src = sum(1 for f in findings if f["kind"] == "source_document")
    n_geo = sum(1 for f in findings if f["kind"] == "source_document" and f["geoblocked"])
    return SourceResult(NAME, True,
                        f"{n_stage} seizure stages, "
                        f"{sum(1 for f in findings if f['kind']=='corroboration_family')} corroboration families, "
                        f"{sum(1 for f in findings if f['kind']=='crosswalk')} crosswalk links, "
                        f"{sum(1 for f in findings if f['kind']=='eisghs_nearby')} ЕИСЖС ≤200m, "
                        f"{n_corp} corpus mentions, "
                        f"{n_src} original-source URLs ({n_geo} geoblocked)",
                        findings)


def _excerpt(text: str, rx: re.Pattern, width: int = 160) -> str:
    m = rx.search(text)
    if not m:
        return text[:width]
    a = max(0, m.start() - width // 2)
    return text[a:a + width].replace("\n", " | ")
