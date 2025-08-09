from __future__ import annotations

import collections
import time

from discord_mcp.core.plugins.cooldowns.base import RateLimiter, WindowStats

__all__: tuple[str, ...] = ("MovingWindowRateLimiter",)


class MovingWindowRateLimiter(RateLimiter):
    def __init__(self, rate: int, per: float) -> None:
        super().__init__(rate, per)
        self._tokens: collections.deque[float] = collections.deque()

    def _refresh(self, now: float | None = None) -> None:
        now = now or time.time()
        while self._tokens and now - self._tokens[0] > self.per:
            self._tokens.popleft()

    def consume(self, amount: int = 1) -> bool:
        now = time.time()
        self._refresh(now)
        if len(self._tokens) + amount <= self.rate:
            for _ in range(amount):
                self._tokens.append(now)
            return True
        return False

    def reset(self) -> None:
        self._tokens.clear()

    @property
    def stats(self) -> WindowStats:
        now = time.time()
        n = len(self._tokens)
        idx = 0
        while idx < n and now - self._tokens[idx] > self.per:
            idx += 1
        in_window = n - idx
        remaining = self.rate - in_window

        if remaining > 0:
            retry_after = 0.0
            reset_at = now
        else:
            earliest_valid = self._tokens[idx]
            retry_after = max(0.0, earliest_valid + self.per - now)
            reset_at = now + retry_after

        last_check = self._tokens[-1] if self._tokens else 0.0
        return WindowStats(
            remaining=remaining,
            retry_after=retry_after,
            reset_at=reset_at,
            last_request=last_check,
        )
