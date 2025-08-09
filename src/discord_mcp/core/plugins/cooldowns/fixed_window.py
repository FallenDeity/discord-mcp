from __future__ import annotations

import time

from discord_mcp.core.plugins.cooldowns.base import RateLimiter, WindowStats

__all__: tuple[str, ...] = ("FixedWindowRateLimiter",)


class FixedWindowRateLimiter(RateLimiter):
    def __init__(self, rate: int, per: float) -> None:
        super().__init__(rate, per)
        self._tokens = rate
        self._window_start = time.time()

    def _refresh(self, now: float | None = None) -> None:
        now = now or time.time()
        if now >= self._window_start + self.per:
            self._tokens = self.rate
            self._window_start = now

    def consume(self, amount: int = 1) -> bool:
        self._refresh()
        if self._tokens >= amount:
            self._tokens -= amount
            return True
        return False

    def reset(self) -> None:
        self._tokens = self.rate
        self._window_start = time.time()

    @property
    def stats(self) -> WindowStats:
        now = time.time()
        if now >= self._window_start + self.per:
            windows_passed = int((now - self._window_start) // self.per)
            virtual_window_start = self._window_start + windows_passed * self.per
            virtual_tokens = self.rate
        else:
            virtual_window_start = self._window_start
            virtual_tokens = self._tokens

        retry_after = 0.0 if virtual_tokens > 0 else max(0.0, virtual_window_start + self.per - now)
        return WindowStats(
            remaining=virtual_tokens,
            retry_after=retry_after,
            reset_at=virtual_window_start + self.per,
            last_request=virtual_window_start,
        )
