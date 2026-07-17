"""Quota bookkeeping for budget-limited OSINT sources (state.sqlite).

P0 only needs the table + read-out (the sweep's --plan prints quota state);
the sole budgeted source, Telegram global post search (10/day), is P1 —
but the ledger exists now so the P1 runner has nothing to migrate.
"""
from __future__ import annotations

import datetime as _dt
import json
import logging
import sqlite3

log = logging.getLogger(__name__)

# source name -> max spends per UTC day. None = unlimited (not ledgered).
DAILY_BUDGETS: dict[str, int] = {
    "telegram_global": 10,
}


def ensure_schema(con: sqlite3.Connection) -> None:
    con.execute(
        """CREATE TABLE IF NOT EXISTS osint_search_ledger (
               day TEXT NOT NULL,
               source TEXT NOT NULL,
               query TEXT NOT NULL,
               meta TEXT,
               created_at TEXT NOT NULL
           )"""
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS osint_ledger_day_source "
        "ON osint_search_ledger(day, source)"
    )
    con.commit()


def _today() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")


def spent_today(con: sqlite3.Connection, source: str) -> int:
    ensure_schema(con)
    row = con.execute(
        "SELECT COUNT(*) FROM osint_search_ledger WHERE day=? AND source=?",
        (_today(), source),
    ).fetchone()
    return int(row[0])


def remaining_today(con: sqlite3.Connection, source: str) -> int | None:
    budget = DAILY_BUDGETS.get(source)
    if budget is None:
        return None
    return max(0, budget - spent_today(con, source))


def record(con: sqlite3.Connection, source: str, query: str, meta: dict | None = None) -> None:
    ensure_schema(con)
    con.execute(
        "INSERT INTO osint_search_ledger (day, source, query, meta, created_at) "
        "VALUES (?,?,?,?,?)",
        (_today(), source, query,
         json.dumps(meta or {}, ensure_ascii=False),
         _dt.datetime.now(_dt.timezone.utc).isoformat()),
    )
    con.commit()


def spend_or_raise(con: sqlite3.Connection, source: str, query: str,
                   meta: dict | None = None) -> None:
    """Record one spend, refusing past the daily budget (hard cap)."""
    rem = remaining_today(con, source)
    if rem is not None and rem <= 0:
        raise RuntimeError(
            f"{source}: daily budget ({DAILY_BUDGETS[source]}) exhausted — "
            "queue persists; re-run tomorrow"
        )
    record(con, source, query, meta)
