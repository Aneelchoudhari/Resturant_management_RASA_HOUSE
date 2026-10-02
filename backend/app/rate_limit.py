from collections import deque
from math import ceil
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    """Per-process limiter; use a shared store when running multiple workers/replicas."""

    def __init__(self, max_buckets: int = 10000):
        self._attempts: dict[tuple[str, str], deque[float]] = {}
        self._max_buckets = max_buckets
        self._lock = Lock()

    def check(self, scope: str, client_ip: str, limit: int, window_seconds: int) -> None:
        now = monotonic()
        cutoff = now - window_seconds
        key = (scope, client_ip)
        with self._lock:
            attempts = self._attempts.get(key)
            if attempts is None:
                if len(self._attempts) >= self._max_buckets:
                    self._attempts.pop(next(iter(self._attempts)))
                attempts = deque()
                self._attempts[key] = attempts
            while attempts and attempts[0] <= cutoff:
                attempts.popleft()
            if len(attempts) >= limit:
                retry_after = max(1, ceil(window_seconds - (now - attempts[0])))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many authentication attempts. Try again later.",
                    headers={"Retry-After": str(retry_after)},
                )
            attempts.append(now)

    def clear(self) -> None:
        with self._lock:
            self._attempts.clear()


auth_rate_limiter = InMemoryRateLimiter()
MAX_LOGIN_ATTEMPTS = 10
LOGIN_WINDOW_SECONDS = 60
MAX_REGISTRATIONS = 5
REGISTRATION_WINDOW_SECONDS = 3600


def limit_auth_attempt(request: Request, scope: str, limit: int, window_seconds: int) -> None:
    client_ip = request.client.host if request.client else "unknown"
    auth_rate_limiter.check(scope, client_ip, limit, window_seconds)