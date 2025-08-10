from __future__ import annotations

import time

from discord_mcp.core.plugins.cooldowns.base import RateLimiter, WindowStats

__all__: tuple[str, ...] = ("TokenBucketRateLimiter",)


class TokenBucketRateLimiter(RateLimiter):
    def __init__(self, rate: int, per: float) -> None:
        super().__init__(rate, per)
        self._capacity = rate
        self._tokens = rate
        self._last_check = time.time()

    def _refill(self, now: float | None = None) -> None:
        now = now or time.time()
        elapsed = now - self._last_check
        refill_rate = self.rate / self.per
        new_tokens = elapsed * refill_rate
        self._tokens = min(self._capacity, self._tokens + new_tokens)
        self._last_check = now

    def consume(self, amount: int = 1) -> bool:
        self._refill()
        if self._tokens >= amount:
            self._tokens -= amount
            return True
        return False

    def reset(self) -> None:
        self._tokens = self.rate
        self._last_check = time.time()

    @property
    def stats(self) -> WindowStats:
        now = time.time()
        refill_rate = self.rate / self.per
        tokens = max(0.0, min(self._capacity, self._tokens + (now - self._last_check) * refill_rate))
        remaining = int(tokens)
        retry_after = 0.0 if tokens >= 1.0 else max(0.0, (1.0 - tokens) / refill_rate)
        reset_at = now + max(0.0, (self._capacity - tokens) / refill_rate)
        return WindowStats(
            remaining=remaining,
            retry_after=retry_after,
            reset_at=reset_at,
            last_request=self._last_check,
        )
