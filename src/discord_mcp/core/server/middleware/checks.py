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
from discord_mcp.utils.exceptions import CheckFailureError

from .middleware import CallNext, Middleware, MiddlewareContext

logger = logging.getLogger(__name__)


__all__: tuple[str, ...] = ("ChecksMiddleware",)


class ChecksMiddleware(Middleware):
    async def _process_checks(
        self,
        ctx: MiddlewareContext[Request[t.Any, t.Any]],
        call_next: CallNext[Request[t.Any, t.Any], Result],
        manifest_cls: type[BaseManifest],
        key: str,
    ) -> Result:
        server = ctx.context.mcp_server
        manifest = server._manifest_repository.get_manifest(manifest_cls, key)
        if manifest is None or not manifest.enabled or not manifest.checks:
            return await call_next(ctx)
        check_results = {predicate: await predicate(ctx) for predicate in manifest.checks}
        if not all(check_results.values()):
            raise CheckFailureError(f"Checks failed for {ctx.method} on {key}! [Predicates: {check_results}]")
        return await call_next(ctx)

    async def on_call_tool(
        self, ctx: MiddlewareContext[CallToolRequest], call_next: CallNext[CallToolRequest, CallToolResult]
    ) -> CallToolResult:
        return await self._process_checks(ctx, call_next, ToolManifest, ctx.message.params.name)  # type: ignore

    async def on_get_prompt(
        self, ctx: MiddlewareContext[GetPromptRequest], call_next: CallNext[GetPromptRequest, GetPromptResult]
    ) -> GetPromptResult:
        return await self._process_checks(ctx, call_next, PromptManifest, ctx.message.params.name)  # type: ignore

    async def on_read_resource(
        self, ctx: MiddlewareContext[ReadResourceRequest], call_next: CallNext[ReadResourceRequest, ReadResourceResult]
    ) -> ReadResourceResult:
        return await self._process_checks(ctx, call_next, ResourceManifest, str(ctx.message.params.uri))  # type: ignore
