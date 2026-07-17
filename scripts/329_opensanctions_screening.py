#!/usr/bin/env python3
"""Screen named officials + SPV founders against OpenSanctions (free NGO tier).

Two candidate pools, both already in the project, neither yet screened
against sanctions/PEP data:

  1. `actor` table (PostgreSQL) — named occupation officials, judges,
     commission members, notaries, beneficiaries acting in official
     capacity. Per CLAUDE.md's privacy rule these are explicitly IN SCOPE
     for accountability (not the minimized-owner-PII category) — role in
     {signing_official, judge, commission_member, notary, beneficiary}.
     Name-only match (no INN/OGRN on this table) — lower-confidence hits,
     always human-reviewed before citing.

  2. data/parsed/egrul_founders.jsonl (scripts/41 output) — SPV founders/
     shareholders extracted from captured EGRUL records, each carrying a
     structural ИНН/ОГРН identifier — much higher-confidence match input
     than name alone.

Calls OpenSanctions' free `/match/default` bulk endpoint (api.opensanctions.org)
with config.OPENSANCTIONS_API_KEY. Batches of <=100 queries per request (API
limit). Writes a review CSV; never auto-loads hits into the DB or into
stakeholder_network — a sanctions/PEP hit is a lead for a human to verify
and fold in deliberately, not an automated linkage (same posture as
scripts/326 Rekognition triage and scripts/40's own manual-curation model).

Usage:
    PYTHONPATH=src .venv312/bin/python scripts/329_opensanctions_screening.py [--dry-run] [--limit N]
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

MATCH_URL = "https://api.opensanctions.org/match/default"
BATCH_SIZE = 100
PAUSE = 5.0
OUT_CSV = ROOT / "data" / "reports" / "opensanctions_screening.csv"
FOUNDERS_JSONL = ROOT / "data" / "parsed" / "egrul_founders.jsonl"

# OpenSanctions considers a match "safe to act on" above this NameQualifiedScore;
# lower scores are still logged but flagged for extra scrutiny.
SCORE_REVIEW_THRESHOLD = 0.5


def _actor_candidates(limit: int | None) -> list[dict]:
    import psycopg2
    import psycopg2.extras

    con = psycopg2.connect(config.DATABASE_URL)
    try:
        with con.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, full_name, role, org
                FROM actor
                WHERE role IN ('signing_official','judge','commission_member',
                                'notary','beneficiary')
                  AND full_name IS NOT NULL AND full_name != ''
                ORDER BY id
            """)
            rows = cur.fetchall()
    finally:
        con.close()
    if limit:
        rows = rows[:limit]
    return [{"pool": "actor", "actor_id": r["id"], "name": r["full_name"],
             "role": r["role"], "org": r["org"], "inn": None, "ogrn": None}
            for r in rows]


def _founder_candidates(limit: int | None) -> list[dict]:
    if not FOUNDERS_JSONL.exists():
        log.warning("no %s — run scripts/41_parse_egrul_founders.py first", FOUNDERS_JSONL)
        return []
    out = []
    with open(FOUNDERS_JSONL, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            name = r.get("founder_name")
            if not name:
                continue
            out.append({
                "pool": "egrul_founder", "actor_id": None, "name": name,
                "role": r.get("founder_type"), "org": r.get("company_inn"),
                "inn": r.get("founder_inn"), "ogrn": r.get("founder_ogrn"),
            })
    if limit:
        out = out[:limit]
    return out


# Institutional-name markers — actor rows carrying these are administrative
# bodies/ministries/commissions, not individuals, even though the `actor`
# table has no dedicated org flag. Checked case-insensitively.
_ORG_MARKERS = (
    "администрац", "министерств", "комисси", "департамент", "управлени",
    "суд ", " суд", "прокуратур", "нотариальн", "ооо ", "зао ", "оао ",
    "гуп ", "мку ", "мбу ", "фонд ",
)


def _is_org_name(name: str) -> bool:
    low = f" {name.lower()} "
    return any(marker in low for marker in _ORG_MARKERS)


def _build_query(cand: dict) -> dict:
    schema = "Company" if (cand["ogrn"] or (cand["role"] or "").startswith("org")
                            or _is_org_name(cand["name"])) else "Person"
    props = {"name": [cand["name"]]}
    id_numbers = [v for v in (cand["inn"], cand["ogrn"]) if v]
    if id_numbers:
        props["idNumber"] = id_numbers
    props["country"] = ["ru"]
    return {"schema": schema, "properties": props}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="build candidate list + queries, skip the API call")
    ap.add_argument("--limit", type=int, default=None,
                    help="cap total candidates screened (for a smoke test)")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if not config.OPENSANCTIONS_API_KEY:
        log.error("OPENSANCTIONS_API_KEY not set in .env — aborting")
        sys.exit(1)

    candidates = _actor_candidates(args.limit) + _founder_candidates(args.limit)
    if not candidates:
        log.error("no candidates found (empty actor table + no egrul_founders.jsonl)")
        sys.exit(1)
    log.info("%d candidates to screen (%d actor, %d egrul founder)", len(candidates),
             sum(1 for c in candidates if c["pool"] == "actor"),
             sum(1 for c in candidates if c["pool"] == "egrul_founder"))

    if args.dry_run:
        for c in candidates[:15]:
            q = _build_query(c)
            log.info("would screen: %s (%s, schema=%s) inn=%s ogrn=%s",
                     c["name"], c["pool"], q["schema"], c["inn"], c["ogrn"])
        n_org = sum(1 for c in candidates if _build_query(c)["schema"] == "Company")
        log.info("dry-run — %d total (%d schema=Company, %d schema=Person), "
                 "no API calls made", len(candidates), n_org, len(candidates) - n_org)
        return

    con = forensics.open_state()
    rows_out: list[dict] = []
    headers = {"Authorization": f"ApiKey {config.OPENSANCTIONS_API_KEY}",
              "Content-Type": "application/json"}

    for start in range(0, len(candidates), BATCH_SIZE):
        batch = candidates[start:start + BATCH_SIZE]
        queries = {f"q{i}": _build_query(c) for i, c in enumerate(batch)}
        r = None
        for attempt in range(5):
            try:
                r = requests.post(MATCH_URL, headers=headers,
                                  json={"queries": queries}, timeout=60)
            except requests.RequestException as e:
                log.warning("batch %d-%d attempt %d network error: %s",
                           start, start + len(batch), attempt + 1, e)
                time.sleep(2 ** attempt)
                continue
            if r.status_code == 429:
                wait = float(r.headers.get("Retry-After", 2 ** (attempt + 2)))
                log.warning("batch %d-%d rate-limited (429), waiting %.0fs "
                           "(attempt %d/5)", start, start + len(batch), wait, attempt + 1)
                time.sleep(wait)
                continue
            break
        if r is None or r.status_code == 429:
            log.error("batch %d-%d failed after retries — skipping", start, start + len(batch))
            continue
        try:
            r.raise_for_status()
        except requests.RequestException as e:
            log.error("batch %d-%d failed: %s", start, start + len(batch), e)
            continue

        forensics.capture_source(
            r.content, url=f"{MATCH_URL}?batch={start}",
            source_type="osint_opensanctions_match",
            title=f"OpenSanctions match batch {start}-{start+len(batch)}",
            description=(f"OpenSanctions /match/default screening of {len(batch)} "
                         f"named officials/SPV founders, batch starting at {start}."),
            content_type="application/json", http_status=r.status_code, con=con,
        )

        results = r.json().get("responses", {})
        for i, c in enumerate(batch):
            resp = results.get(f"q{i}", {})
            matches = sorted(resp.get("results", []),
                             key=lambda m: m.get("score", 0), reverse=True)
            if not matches:
                rows_out.append({**c, "match_name": "", "match_score": "",
                                 "match_datasets": "", "match_topics": "",
                                 "match_id": "", "flagged": False})
                continue
            for m in matches[:3]:
                score = m.get("score", 0)
                props = m.get("properties", {})
                rows_out.append({
                    **c,
                    "match_name": (props.get("name") or [""])[0],
                    "match_score": round(score, 3),
                    "match_datasets": ";".join(m.get("datasets", [])),
                    "match_topics": ";".join(props.get("topics", [])),
                    "match_id": m.get("id", ""),
                    "flagged": score >= SCORE_REVIEW_THRESHOLD,
                })
        time.sleep(PAUSE)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    import csv
    fieldnames = ["pool", "actor_id", "name", "role", "org", "inn", "ogrn",
                  "match_name", "match_score", "match_datasets", "match_topics",
                  "match_id", "flagged"]
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows_out)

    n_flagged = sum(1 for r in rows_out if r.get("flagged"))
    log.info("done — %d rows written to %s (%d flagged >= score %.2f)",
             len(rows_out), OUT_CSV, n_flagged, SCORE_REVIEW_THRESHOLD)
    log.info("Review flagged rows manually before citing any hit — name-only "
             "matches (actor pool) are lower confidence than INN/OGRN matches "
             "(egrul_founder pool).")


if __name__ == "__main__":
    main()
