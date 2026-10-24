"""Tiny event log: enough to answer "how many people actually used this?".

Uses Postgres when DATABASE_URL is set (production: Render's free disk is wiped
every time the service sleeps, so stats must live in a real database), and a
local SQLite file otherwise.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from typing import Any, Iterator, Optional

ALLOWED_EVENTS = {"visit", "parse", "parse_error", "correction", "export_csv", "export_qbo", "feedback"}


class Store:
    def __init__(self, path: Optional[str] = None, database_url: Optional[str] = None):
        self.pg_url = database_url
        self._lock = threading.Lock()
        if self.pg_url:
            self.ph = "%s"
            self.item_expr = "meta::jsonb->>'item'"
            schema = (
                "CREATE TABLE IF NOT EXISTS events ("
                " id BIGSERIAL PRIMARY KEY, ts DOUBLE PRECISION NOT NULL, client TEXT NOT NULL,"
                " event TEXT NOT NULL, meta TEXT NOT NULL DEFAULT '{}')"
            )
        else:
            path = path or "data/shoebox.db"
            if path != ":memory:":
                os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            self._sqlite = sqlite3.connect(path, check_same_thread=False)
            self.ph = "?"
            self.item_expr = "json_extract(meta,'$.item')"
            schema = (
                "CREATE TABLE IF NOT EXISTS events ("
                " id INTEGER PRIMARY KEY, ts REAL NOT NULL, client TEXT NOT NULL,"
                " event TEXT NOT NULL, meta TEXT NOT NULL DEFAULT '{}')"
            )
        with self._cursor() as cur:
            cur.execute(schema)
            cur.execute("CREATE INDEX IF NOT EXISTS ix_events_event ON events(event)")

    @contextmanager
    def _cursor(self) -> Iterator[Any]:
        if self.pg_url:
            import psycopg

            # A short-lived connection per call: Neon suspends idle compute, which
            # would silently kill a long-held connection.
            with psycopg.connect(self.pg_url, autocommit=True, connect_timeout=15) as conn:
                with conn.cursor() as cur:
                    yield cur
        else:
            with self._lock:
                cur = self._sqlite.cursor()
                try:
                    yield cur
                    self._sqlite.commit()
                finally:
                    cur.close()

    def log(self, client: str, event: str, meta: dict[str, Any] | None = None) -> None:
        if event not in ALLOWED_EVENTS:
            raise ValueError(f"unknown event {event}")
        blob = json.dumps(meta or {})[:2000]
        p = self.ph
        with self._cursor() as cur:
            cur.execute(
                f"INSERT INTO events (ts, client, event, meta) VALUES ({p}, {p}, {p}, {p})",
                (time.time(), client, event, blob),
            )

    def delete_client(self, client: str) -> int:
        """Remove every event recorded for one anonymous ID. Returns rows deleted."""
        with self._cursor() as cur:
            cur.execute(f"DELETE FROM events WHERE client = {self.ph}", (client,))
            return cur.rowcount

    def stats(self) -> dict[str, Any]:
        with self._cursor() as cur:
            def q(sql: str) -> int:
                cur.execute(sql)
                return int(cur.fetchone()[0])

            visitors = q("SELECT COUNT(DISTINCT client) FROM events")
            users = q("SELECT COUNT(DISTINCT client) FROM events WHERE event='parse'")
            returning = q(
                "SELECT COUNT(*) FROM (SELECT client FROM events WHERE event='parse'"
                " GROUP BY client HAVING MAX(ts) - MIN(ts) > 86400) t"
            )
            parsed = q("SELECT COUNT(*) FROM events WHERE event='parse'")
            errors = q("SELECT COUNT(*) FROM events WHERE event='parse_error'")
            corrected = q(f"SELECT COUNT(DISTINCT {self.item_expr}) FROM events WHERE event='correction'")
            exports = q("SELECT COUNT(*) FROM events WHERE event IN ('export_csv','export_qbo')")
            cur.execute("SELECT ts, meta FROM events WHERE event='feedback' ORDER BY ts DESC LIMIT 50")
            feedback = [{"ts": r[0], "text": json.loads(r[1]).get("text", "")} for r in cur.fetchall()]
        accepted = (parsed - corrected) / parsed if parsed else None
        return {
            "visitors": visitors,
            "users": users,
            "returning_users": returning,
            "receipts_parsed": parsed,
            "parse_errors": errors,
            "categories_corrected": corrected,
            "category_acceptance_rate": round(accepted, 3) if accepted is not None else None,
            "exports": exports,
            "feedback": feedback,
        }
