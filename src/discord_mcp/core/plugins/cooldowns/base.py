from __future__ import annotations

import abc
import time

import attrs

__all__: tuple[str, ...] = ("RateLimiter",)


@attrs.define
class WindowStats:
    remaining: int
    retry_after: float
    reset_at: float
    last_request: float

    def __str__(self) -> str:
        return (
            f"WindowStats(remaining={self.remaining}, "
            f"retry_after={self.retry_after} seconds, "
            f"reset_at={time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.reset_at))}, "
            f"last_request={time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.last_request))})"
        )


class RateLimiter(abc.ABC):
    def __init__(self, rate: int, per: float) -> None:
        self.rate = rate
        self.per = per

    @abc.abstractmethod
    def consume(self, amount: int = 1) -> bool:
        """Consume a certain amount of tokens from the rate limit."""

    @abc.abstractmethod
    def reset(self) -> None:
        """Reset the rate limit."""

    @property
    @abc.abstractmethod
    def stats(self) -> WindowStats:
        """Get the current stats of the rate limiter, including remaining tokens, retry after time, and reset time."""

    def copy(self) -> RateLimiter:
        return self.__class__(self.rate, self.per)
