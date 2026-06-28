#!/usr/bin/env python3
"""Backfill `court_case` + `actor` rows for the district bezkhoz cases loaded
by `scripts/185` directly into `seizure_event` (judge/petitioner only ever
landed in `seizure_event.detail` JSONB there, never in the legacy `court_case`
table). Without this, `scripts/40_build_stakeholder_network.py` -- which reads
judges from `court_case` and petitioners from `actor` -- stays blind to the
22 non-Mariupol courts added in June 2026 (33 judges total vs. the 28 it can
currently see).

Source: `seizure_event` rows with dedup_key LIKE 'dnr_district_fi:%'. One
`court_case` row per case (keyed on the `court_petition` event; `court_transfer`,
if present, supplies decided_date). `case_uid` is synthesized as
'district:<court_code>:<portal_case_id>' (prefixed so it can never collide
with the legacy GAS-Pravosudie uid format already in court_case.case_uid).

PRIVACY: owner names are not read here -- detail never carried them
(scripts/182/185 already stripped them at parse time).

Defaults to DRY-RUN. Pass --commit to write.

Run:
    .venv312/bin/python scripts/188_backfill_court_case_into_district.py            # dry-run
    .venv312/bin/python scripts/188_backfill_court_case_into_district.py --commit
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import psycopg2  # noqa: E402

from mariupol_seizures import config  # noqa: E402
from mariupol_seizures.db.load import _upsert_actor  # noqa: E402

log = logging.getLogger(__name__)

DEDUP_PREFIX = "dnr_district_fi"


def main(commit: bool) -> None:
    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()

    cur.execute(
        """SELECT dedup_key, property_id, event_date, source_doc_id, detail
           FROM seizure_event
           WHERE dedup_key LIKE %s AND stage = 'court_petition'""",
        (DEDUP_PREFIX + ":%",),
    )
    petitions = cur.fetchall()

    cur.execute(
        """SELECT dedup_key, event_date, source_doc_id
           FROM seizure_event
           WHERE dedup_key LIKE %s AND stage = 'court_transfer'""",
        (DEDUP_PREFIX + ":%",),
    )
    transfers = {}
    for dk, ev_date, src_id in cur.fetchall():
        # dedup_key: dnr_district_fi:<court>:<case_id>:court_transfer
        csub, cid = dk.split(":")[1:3]
        transfers[(csub, cid)] = (ev_date, src_id)

    stats = {"cases": 0, "court_case_rows": 0, "judges_upserted": 0,
              "petitioners_upserted": 0, "missing_detail": 0}

    for dk, property_id, filed_date, source_doc_id, detail in petitions:
        csub, cid = dk.split(":")[1:3]
        if not detail:
            stats["missing_detail"] += 1
            continue
        stats["cases"] += 1
        case_uid = f"district:{csub}:{cid}"
        court = detail.get("court") or csub
        case_number = detail.get("case")
        judge = detail.get("judge")
        outcome = detail.get("outcome")
        petitioner = detail.get("petitioner")

        decided_date, transfer_src = transfers.get((csub, cid), (None, None))
        src_id = source_doc_id or transfer_src

        if commit:
            cur.execute(
                """INSERT INTO court_case
                       (property_id, court, case_number, case_uid, judge,
                        legal_grounds, outcome, filed_date, decided_date,
                        entered_force, source_doc_id)
                   VALUES (%s, %s, %s, %s, %s, '[]', %s, %s, %s, NULL, %s)
                   ON CONFLICT (case_uid) DO UPDATE
                       SET property_id   = EXCLUDED.property_id,
                           judge         = EXCLUDED.judge,
                           outcome       = EXCLUDED.outcome,
                           filed_date    = EXCLUDED.filed_date,
                           decided_date  = EXCLUDED.decided_date,
                           source_doc_id = EXCLUDED.source_doc_id""",
                (property_id, court, case_number, case_uid, judge,
                 outcome, filed_date, decided_date, src_id),
            )
        stats["court_case_rows"] += 1

        if judge:
            if commit:
                _upsert_actor(cur, judge, "judge", court)
            stats["judges_upserted"] += 1
        if petitioner:
            if commit:
                _upsert_actor(cur, petitioner, "signing_official", None)
            stats["petitioners_upserted"] += 1

    if commit:
        con.commit()

    mode = "COMMITTED" if commit else "DRY-RUN (no writes — pass --commit)"
    print(f"\n{'='*64}\nBackfill court_case from district load — {mode}\n{'='*64}")
    for k, v in stats.items():
        print(f"  {v:7,d}  {k}")
    if commit:
        cur.execute("SELECT count(DISTINCT judge) FROM court_case WHERE judge IS NOT NULL")
        print(f"\n  distinct judges in court_case now = {cur.fetchone()[0]:,}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main(commit="--commit" in sys.argv)
