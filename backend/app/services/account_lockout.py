import threading
import time
from collections import defaultdict


class AccountLockoutService:
    """Tracks failed login attempts and applies temporary lockout.

    ponytail: in-process only — correct for a single worker (the default deploy).
    Move to a shared store (Redis) before running multiple workers, or lockout
    counts are tracked per-worker.
    """

    def __init__(self):
        self._failed_attempts = defaultdict(int)
        self._locked_until = {}
        self._lock = threading.Lock()

    def _key(self, identifier: str) -> str:
        return identifier.lower().strip()

    def is_locked(self, identifier: str) -> bool:
        now = time.time()
        key = self._key(identifier)
        with self._lock:
            unlock_at = self._locked_until.get(key)
            if unlock_at is None:
                return False
            if now >= unlock_at:
                self._locked_until.pop(key, None)
                self._failed_attempts.pop(key, None)
                return False
            return True

    def register_failure(self, identifier: str, max_attempts: int, lockout_seconds: int) -> None:
        key = self._key(identifier)
        with self._lock:
            self._failed_attempts[key] += 1
            if self._failed_attempts[key] >= max_attempts:
                self._locked_until[key] = time.time() + lockout_seconds

    def reset(self, identifier: str) -> None:
        key = self._key(identifier)
        with self._lock:
            self._failed_attempts.pop(key, None)
            self._locked_until.pop(key, None)


account_lockout_service = AccountLockoutService()
