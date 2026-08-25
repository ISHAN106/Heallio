import threading
import time
from collections import defaultdict, deque


class InMemoryRateLimiter:
    """Simple thread-safe sliding-window rate limiter.

    ponytail: in-process only — correct for a single worker (the default deploy).
    Move to a shared store (Redis) before running multiple workers, or each worker
    enforces the limit independently.
    """

    def __init__(self):
        self._events = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.time()
        threshold = now - window_seconds

        with self._lock:
            bucket = self._events[key]
            while bucket and bucket[0] < threshold:
                bucket.popleft()

            if len(bucket) >= limit:
                return False

            bucket.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


rate_limiter = InMemoryRateLimiter()
