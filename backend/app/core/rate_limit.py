from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from math import ceil
from threading import Lock
from time import monotonic


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int = 0


class SlidingWindowRateLimiter:
    """Small, concurrency-safe limiter for the single API process.

    Keys are already one-way hashes when they reach this class. The limiter keeps
    no request bodies, provider tokens, session tokens, email addresses, or raw IP
    addresses.
    """

    def __init__(self, clock: Callable[[], float] = monotonic) -> None:
        self._clock = clock
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, *, limit: int, window_seconds: int) -> RateLimitDecision:
        now = self._clock()
        cutoff = now - window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                retry_after = max(1, ceil(window_seconds - (now - events[0])))
                return RateLimitDecision(allowed=False, retry_after_seconds=retry_after)
            events.append(now)
            return RateLimitDecision(allowed=True)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()


@lru_cache
def get_auth_rate_limiter() -> SlidingWindowRateLimiter:
    return SlidingWindowRateLimiter()
