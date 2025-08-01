from __future__ import annotations

import asyncio
import collections
import contextlib
import logging
import typing as t

import attrs
from mcp.server.fastmcp.server import Context
from mcp.server.lowlevel.server import request_ctx
from mcp.server.session import ServerSession
from starlette.requests import Request

if t.TYPE_CHECKING:
    from discord_mcp.core.bot import Bot
    from discord_mcp.core.server.mcp_server import DiscordMCPStarletteApp, STDIODiscordMCPServer


__all__: tuple[str, ...] = (
    "DiscordMCPLifespanResult",
    "DiscordMCPContext",
    "starlette_lifespan",
    "stdio_lifespan",
    "get_context",
)


logger = logging.getLogger(__name__)


DiscordMCPContext: t.TypeAlias = Context[ServerSession, "DiscordMCPLifespanResult", t.Any]


@attrs.define
class DiscordMCPLifespanResult(collections.UserDict[str, t.Any]):
    bot: Bot

    def __attrs_post_init__(self) -> None:
        self.data = attrs.asdict(self, recurse=True)

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(data={self.data})"


@contextlib.asynccontextmanager
async def _manage_bot_lifecycle(bot: Bot) -> t.AsyncIterator[DiscordMCPLifespanResult]:
    """Common bot lifecycle management for both server types."""
    await bot.login(str(bot.environment.DISCORD_TOKEN))
    _bot_task = asyncio.create_task(bot.connect())
    try:
        await bot.wait_until_ready()
        logger.info(f"Discord bot connected as {bot.user}")
        yield DiscordMCPLifespanResult(bot=bot)
    finally:
        logger.info("Application shutting down...")

        if _bot_task:
            _bot_task.cancel()
            try:
                await _bot_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error during bot shutdown: {e}")
        await bot.close()

        logger.info("Application shutdown complete.")


@contextlib.asynccontextmanager
async def starlette_lifespan(app: DiscordMCPStarletteApp) -> t.AsyncIterator[DiscordMCPLifespanResult]:
    if not app.session_manager:
        raise RuntimeError("Session manager is not initialized, cannot run lifespan context")

    logger.info("Starting application with StreamableHTTP session manager...")

    app.mcp_server._apply_middlewares()

    async with app.session_manager.run():
        async with _manage_bot_lifecycle(app.bot) as result:
            yield result


@contextlib.asynccontextmanager
async def stdio_lifespan(app: STDIODiscordMCPServer) -> t.AsyncIterator[DiscordMCPLifespanResult]:
    app._apply_middlewares()
    async with _manage_bot_lifecycle(app.bot) as result:
        yield result
        logger.info("Application shutting down...")


def get_context() -> DiscordMCPContext:
    try:
        request_context = request_ctx.get()
    except LookupError:
        request_context = None
    ctx = Context(request_context=request_context, fastmcp=None)
    if ctx.request_context and ctx.request_context.request and isinstance(ctx.request_context.request, Request):
        ctx.request_context.lifespan_context = t.cast(DiscordMCPLifespanResult, ctx.request_context.request.state)
    return ctx
