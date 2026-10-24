"""In-memory rate limiting: per-client hourly limit plus a global daily cap to bound API spend."""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, per_client_per_hour: int, daily_cap: int):
        self.per_client = per_client_per_hour
        self.daily_cap = daily_cap
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._day = time.strftime("%Y-%m-%d")
        self._day_count = 0
        self._lock = threading.Lock()

    def allow(self, client: str) -> tuple[bool, str]:
        now = time.time()
        with self._lock:
            today = time.strftime("%Y-%m-%d")
            if today != self._day:
                self._day, self._day_count = today, 0
            if self._day_count >= self.daily_cap:
                return False, "Shoebox hit its daily limit. Please try again tomorrow."
            q = self._hits[client]
            while q and now - q[0] > 3600:
                q.popleft()
            if len(q) >= self.per_client:
                return False, "You've uploaded a lot this hour. Please try again in a bit."
            q.append(now)
            self._day_count += 1
            return True, ""
