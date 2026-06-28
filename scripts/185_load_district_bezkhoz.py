#!/usr/bin/env python3
"""Load the NET-NEW first-instance DNR district bezkhoz cases (`scripts/182`,
reconciled by `scripts/184`) into the PostgreSQL spine — without
double-counting the ~2,625 Mariupol cases already on the spine from the
original `court_crawler` harvest.

WHAT IT LOADS
-------------
For each net-new case (5,598 rest-of-DNR + 48 newer Mariupol):
  - a `property` row. If the ruling leaked a cadastral number that exact-matches
    an existing spine property, the case is LINKED to that property; otherwise an
    address-less court-island property is created (street redacted to `<адрес>`
    at source — see `docs/dnr_district_first_instance_2026-06.md`).
  - `seizure_event(stage='court_petition')` dated to filing.
  - `seizure_event(stage='court_transfer')` dated to decision, ONLY when the
    petition was granted (the seizure consummated). Refused / bounced /
    withdrawn cases get the petition event only.
  - `source_document` chain-of-custody row (sha256 -> raw card), so the spine
    points back into the immutable forensic store.

IDEMPOTENCY & PRIVACY
---------------------
Re-runnable: dedup_key `dnr_district_fi:<court>:<case_id>:<stage>` +
ON CONFLICT DO UPDATE; property reuse is resolved through the existing
court_petition event, so a second pass creates no duplicate properties.
Owner names are NEVER written — `scripts/182` already stripped them; only the
named-owner *count*, the petitioner organisation, and the judge (officials) go
into `detail`.

Defaults to DRY-RUN. Pass --commit to write.

Run:
    .venv312/bin/python scripts/185_load_district_bezkhoz.py            # dry-run
    .venv312/bin/python scripts/185_load_district_bezkhoz.py --commit
"""
from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import psycopg2  # noqa: E402

from mariupol_seizures import config  # noqa: E402

log = logging.getLogger(__name__)

SRC = ROOT / "data" / "parsed" / "dnr_district_bezkhoz.json"
RAW = ROOT / "data" / "raw"
DEDUP_PREFIX = "dnr_district_fi"
CONF = 0.90  # occupation's own dated record of the act
MARIUPOL_COURTS = {"mar-zhovt--dnr", "mar-prim--dnr",
                   "mar-ordzh--dnr", "mar-ilich--dnr"}


def case_id(url: str) -> str | None:
    m = re.search(r"[?&]case_id=(\d+)", url)
    return m.group(1) if m else None


def court_sub(url: str) -> str | None:
    m = re.search(r"https?://([^/.]+)", url)
    return m.group(1) if m else None


def meta_for(raw_sha: str) -> dict:
    mp = RAW / (raw_sha + ".html.meta.json")
    try:
        return json.loads(mp.read_text())
    except Exception:
        return {}


def to_date(s: str | None):
    if not s:
        return None
    try:
        d, m, y = s.split(".")
        return f"{y}-{m}-{d}"
    except ValueError:
        return None


def main(commit: bool) -> None:
    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()

    # cases already on the spine, by portal case_id
    cur.execute("SELECT url FROM source_document WHERE url LIKE '%name_op=case%'")
    spine_ids = {(court_sub(u), case_id(u)) for (u,) in cur.fetchall()
                 if case_id(u)}

    # cadastral -> existing spine property
    cur.execute("SELECT cadastral_no, id FROM property WHERE cadastral_no IS NOT NULL")
    spine_cad = {c.strip(): pid for c, pid in cur.fetchall()}

    recs = json.loads(SRC.read_text(encoding="utf-8"))

    stats = {"net_new": 0, "linked_by_cadastral": 0, "new_property": 0,
             "reused_property": 0, "petition_events": 0, "transfer_events": 0,
             "skipped_on_spine": 0, "no_case_id": 0}

    for r in recs:
        m = meta_for(r["raw_sha"])
        url = m.get("url", "")
        cid, csub = case_id(url), court_sub(url)
        if not cid:
            stats["no_case_id"] += 1
            continue
        if (csub, cid) in spine_ids:
            stats["skipped_on_spine"] += 1
            continue  # already loaded by the original harvest — no double-count
        stats["net_new"] += 1

        petition_key = f"{DEDUP_PREFIX}:{csub}:{cid}:court_petition"

        # resolve property: cadastral link -> prior-run reuse -> new island
        cad = r.get("cadastral_number")
        property_id = None
        link_kind = None
        if cad and cad in spine_cad:
            property_id = spine_cad[cad]
            link_kind = "linked_by_cadastral"
        else:
            cur.execute("SELECT property_id FROM seizure_event WHERE dedup_key=%s",
                        (petition_key,))
            row = cur.fetchone()
            if row:
                property_id = row[0]
                link_kind = "reused_property"

        if property_id is None:
            link_kind = "new_property"
            note = (f"DNR district ownerless-property court case {r['case']} "
                    f"({r['municipality']}); street address redacted at source "
                    f"(<адрес>); first-instance бесхозяйная-недвижимость petition")
            if commit:
                cur.execute(
                    """INSERT INTO property (occupation_address, cadastral_no,
                                             rd4u_category, notes)
                       VALUES (NULL, %s, 'A3.6', %s) RETURNING id""",
                    (cad, note))
                property_id = cur.fetchone()[0]
        stats[link_kind] += 1

        # source_document chain-of-custody (sha256 -> raw card)
        source_doc_id = None
        if commit:
            cur.execute(
                """INSERT INTO source_document
                       (url, court, kind, sha256, raw_path, http_status, captured_at)
                   VALUES (%s, %s, 'case_card', %s, %s, 200,
                           COALESCE(%s::timestamptz, now()))
                   ON CONFLICT (sha256) DO UPDATE SET url = EXCLUDED.url
                   RETURNING id""",
                (url, r["court_code"], r["raw_sha"],
                 f"data/raw/{r['raw_sha']}.html", m.get("captured_at")))
            source_doc_id = cur.fetchone()[0]

        # detail — officials kept, owners only counted
        detail = {
            "court": r["court_code"], "municipality": r["municipality"],
            "case": r["case"], "result_code": r["result_code"],
            "outcome": r["outcome"], "judge": r.get("judge"),
            "petitioner_type": r["petitioner_type"],
            "petitioner": r.get("petitioner_name"),
            "named_owners": r.get("owner_natural_persons", 0),
            "cadastral": cad, "is_mariupol": r["is_mariupol"],
            "source": "dnr_district_first_instance",
        }

        # court_petition (always) + court_transfer (only if granted)
        events = [("court_petition", to_date(r["filed"]), petition_key)]
        if r["rollup"].startswith("LOSE"):  # seizure granted
            events.append(("court_transfer", to_date(r["decided"]),
                           f"{DEDUP_PREFIX}:{csub}:{cid}:court_transfer"))

        for stage, ev_date, dk in events:
            if commit:
                cur.execute(
                    """INSERT INTO seizure_event
                           (property_id, stage, event_date, confidence,
                            source_doc_id, detail, dedup_key)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (dedup_key) DO UPDATE
                         SET event_date = EXCLUDED.event_date,
                             detail = EXCLUDED.detail""",
                    (property_id, stage, ev_date, CONF, source_doc_id,
                     json.dumps(detail, ensure_ascii=False), dk))
            stats["petition_events" if stage == "court_petition"
                  else "transfer_events"] += 1

    if commit:
        con.commit()

    mode = "COMMITTED" if commit else "DRY-RUN (no writes — pass --commit)"
    print(f"\n{'='*64}\nLoad district first-instance bezkhoz — {mode}\n{'='*64}")
    for k, v in stats.items():
        print(f"  {v:7,d}  {k}")
    if commit:
        cur.execute("SELECT count(*) FROM seizure_event WHERE dedup_key LIKE %s",
                    (DEDUP_PREFIX + ":%",))
        print(f"\n  seizure_event rows now under {DEDUP_PREFIX}:* = {cur.fetchone()[0]:,}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main(commit="--commit" in sys.argv)
