"""Tiny SQLite event log — enough to answer "how many people actually used this?"."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from typing import Any

ALLOWED_EVENTS = {"visit", "parse", "parse_error", "correction", "export_csv", "export_qbo", "feedback"}


class Store:
    def __init__(self, path: str):
        if path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock:
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS events ("
                " id INTEGER PRIMARY KEY, ts REAL NOT NULL, client TEXT NOT NULL,"
                " event TEXT NOT NULL, meta TEXT NOT NULL DEFAULT '{}')"
            )
            self._db.execute("CREATE INDEX IF NOT EXISTS ix_events_event ON events(event)")
            self._db.commit()

    def log(self, client: str, event: str, meta: dict[str, Any] | None = None) -> None:
        if event not in ALLOWED_EVENTS:
            raise ValueError(f"unknown event {event}")
        blob = json.dumps(meta or {})[:2000]
        with self._lock:
            self._db.execute(
                "INSERT INTO events (ts, client, event, meta) VALUES (?, ?, ?, ?)",
                (time.time(), client, event, blob),
            )
            self._db.commit()

    def stats(self) -> dict[str, Any]:
        q = lambda sql, *a: self._db.execute(sql, a).fetchone()[0]  # noqa: E731
        with self._lock:
            visitors = q("SELECT COUNT(DISTINCT client) FROM events")
            users = q("SELECT COUNT(DISTINCT client) FROM events WHERE event='parse'")
            returning = q(
                "SELECT COUNT(*) FROM (SELECT client FROM events WHERE event='parse'"
                " GROUP BY client HAVING MAX(ts) - MIN(ts) > 86400)"
            )
            parsed = q("SELECT COUNT(*) FROM events WHERE event='parse'")
            errors = q("SELECT COUNT(*) FROM events WHERE event='parse_error'")
            corrected = q(
                "SELECT COUNT(DISTINCT json_extract(meta,'$.item')) FROM events WHERE event='correction'"
            )
            exports = q("SELECT COUNT(*) FROM events WHERE event IN ('export_csv','export_qbo')")
            feedback = [
                {"ts": r[0], "text": json.loads(r[1]).get("text", "")}
                for r in self._db.execute(
                    "SELECT ts, meta FROM events WHERE event='feedback' ORDER BY ts DESC LIMIT 50"
                )
            ]
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
