import time
from collections import deque

from fastapi import HTTPException, Request, status

# Stale keys are swept once the table grows past this, so a flood of distinct
# IPs or emails can't grow memory without bound.
_SWEEP_THRESHOLD = 10_000


class RateLimiter:
    """At most `limit` hits per key within a sliding `window_seconds`.

    In-memory, so it only holds within one process - fine while the API runs
    as a single uvicorn worker; several workers would each count separately."""

    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = {}

    def hit(self, key: str) -> None:
        """Record a hit, or raise 429 if the key is over its limit."""
        now = time.monotonic()
        if len(self._hits) > _SWEEP_THRESHOLD:
            self._sweep(now)

        hits = self._hits.setdefault(key, deque())
        while hits and hits[0] <= now - self.window:
            hits.popleft()

        if len(hits) >= self.limit:
            retry_after = int(hits[0] + self.window - now) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts, try again later",
                headers={"Retry-After": str(retry_after)},
            )
        hits.append(now)

    def _sweep(self, now: float) -> None:
        self._hits = {key: hits for key, hits in self._hits.items() if hits and hits[-1] > now - self.window}


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


login_ip_limiter = RateLimiter(limit=10, window_seconds=60)
# Per account too: a password guessed from many IPs still hits this one.
login_email_limiter = RateLimiter(limit=10, window_seconds=15 * 60)
register_ip_limiter = RateLimiter(limit=5, window_seconds=60 * 60)
