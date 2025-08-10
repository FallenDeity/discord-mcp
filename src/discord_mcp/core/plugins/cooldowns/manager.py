from __future__ import annotations

import time
import typing as t

from discord_mcp.core.plugins.cooldowns.base import RateLimiter

if t.TYPE_CHECKING:
    from starlette.requests import Request

    from discord_mcp.core.server.shared.context import DiscordMCPContext


def get_bucket_key(context: DiscordMCPContext) -> t.Hashable:
    """Generate a unique key for the rate limit bucket based on the context."""
    request_obj: Request | None = context.request_context.request
    if request_obj is None:
        return "global"
    return request_obj.headers.get("mcp-session-id", "global")


class CooldownManager:
    def __init__(
        self, rate_limiter: RateLimiter, get_bucket_key: t.Callable[[DiscordMCPContext], t.Hashable] = get_bucket_key
    ) -> None:
        self._original_rate_limiter = rate_limiter
        self._cache: t.Dict[t.Hashable, RateLimiter] = {}
        self._get_bucket_key = get_bucket_key

    def _prune_cache(self) -> None:
        current_time = time.time()
        keys_to_remove = [k for k, v in self._cache.items() if current_time > v.stats.last_request + v.per]
        for key in keys_to_remove:
            del self._cache[key]

    def get_bucket(self, context: DiscordMCPContext) -> RateLimiter:
        self._prune_cache()
        bucket_key = self._get_bucket_key(context)
        if bucket_key not in self._cache:
            self._cache[bucket_key] = self._original_rate_limiter.copy()
        return self._cache[bucket_key]

    def update_bucket(self, context: DiscordMCPContext, amount: int = 1) -> bool:
        bucket = self.get_bucket(context)
        return bucket.consume(amount)
