from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class SlidingWindowRateLimiter:
    def __init__(self, *, limit: int, window_seconds: int = 60) -> None:
        self.limit = max(1, int(limit))
        self.window_seconds = max(1, int(window_seconds))
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        self._calls = 0

    def allow(self, key: str) -> tuple[bool, int]:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        clean_key = str(key or "anonymous")
        with self._lock:
            self._calls += 1
            if self._calls % 1024 == 0:
                stale = [name for name, queue in self._events.items() if not queue or queue[-1] <= cutoff]
                for name in stale:
                    self._events.pop(name, None)
            events = self._events[clean_key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.limit:
                retry_after = max(1, int(self.window_seconds - (now - events[0])))
                return False, retry_after
            events.append(now)
            return True, 0
