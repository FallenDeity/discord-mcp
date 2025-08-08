from __future__ import annotations

import logging
import typing as t

from mcp.types import (
    CallToolRequest,
    CallToolResult,
    GetPromptRequest,
    GetPromptResult,
    ReadResourceRequest,
    ReadResourceResult,
    Request,
    Result,
)

from discord_mcp.core.server.shared.manifests import BaseManifest, PromptManifest, ResourceManifest, ToolManifest
from discord_mcp.utils.exceptions import RateLimitExceededError

from .middleware import CallNext, Middleware, MiddlewareContext

logger = logging.getLogger(__name__)


__all__: tuple[str, ...] = ("RateLimitMiddleware",)


class RateLimitMiddleware(Middleware):
    async def _process_rate_limit(
        self,
        ctx: MiddlewareContext[Request[t.Any, t.Any]],
        call_next: CallNext[Request[t.Any, t.Any], Result],
        manifest_cls: type[BaseManifest],
        key: str,
    ) -> Result:
        server = ctx.context.mcp_server
        manifest = server._manifest_repository.get_manifest(manifest_cls, key)
        if manifest is None or not manifest.enabled or not manifest.cooldown:
            return await call_next(ctx)
        rate_limit = manifest.cooldown.update_bucket(ctx.context)
        if not rate_limit:
            bucket_stats = manifest.cooldown.get_bucket(ctx.context).stats
            raise RateLimitExceededError(
                message=f"Rate limit exceeded for {ctx.method} on {key} | {str(bucket_stats)}", data=bucket_stats
            )
        return await call_next(ctx)

    async def on_call_tool(
        self, ctx: MiddlewareContext[CallToolRequest], call_next: CallNext[CallToolRequest, CallToolResult]
    ) -> CallToolResult:
        return await self._process_rate_limit(ctx, call_next, ToolManifest, ctx.message.params.name)  # type: ignore

    async def on_get_prompt(
        self, ctx: MiddlewareContext[GetPromptRequest], call_next: CallNext[GetPromptRequest, GetPromptResult]
    ) -> GetPromptResult:
        return await self._process_rate_limit(ctx, call_next, PromptManifest, ctx.message.params.name)  # type: ignore

    async def on_read_resource(
        self, ctx: MiddlewareContext[ReadResourceRequest], call_next: CallNext[ReadResourceRequest, ReadResourceResult]
    ) -> ReadResourceResult:
        return await self._process_rate_limit(ctx, call_next, ResourceManifest, str(ctx.message.params.uri))  # type: ignore
