#!/usr/bin/env python3
"""Stage 4 (one-shot): load data/toponyms.csv into the PostGIS toponym table.

Idempotent: re-running updates existing rows by (occupation_name, source_ref).
Comment lines and rows missing source_ref are skipped silently.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mariupol_seizures import config  # noqa: E402
from mariupol_seizures.normalize.toponym import load_toponyms  # noqa: E402


def run() -> None:
    toponyms = load_toponyms()
    if not toponyms:
        print("data/toponyms.csv is empty or missing — nothing to load.")
        sys.exit(0)

    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()
    cur.execute(
        """CREATE UNIQUE INDEX IF NOT EXISTS toponym_occ_src_uidx
           ON toponym (occupation_name, source_ref)"""
    )
    n_ins = n_upd = 0
    for t in toponyms.values():
        cur.execute(
            """INSERT INTO toponym
                   (prewar_name, occupation_name, kind, changed_on,
                    source_ref)
               VALUES (%s, %s, %s,
                       NULLIF(%s,''),
                       %s)
               ON CONFLICT (occupation_name, source_ref) DO UPDATE
                   SET prewar_name = EXCLUDED.prewar_name,
                       kind        = EXCLUDED.kind,
                       changed_on  = EXCLUDED.changed_on
               RETURNING (xmax = 0) AS inserted""",
            (
                t.prewar_name, t.occupation_name, t.kind,
                t.changed_on, t.source_ref,
            ),
        )
        if cur.fetchone()[0]:
            n_ins += 1
        else:
            n_upd += 1
    con.commit()
    cur.close()
    con.close()
    print(f"toponyms: inserted {n_ins}, updated {n_upd}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    run()
