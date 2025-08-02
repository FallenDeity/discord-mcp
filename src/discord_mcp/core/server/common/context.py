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
from typing_extensions import TypeVar

if t.TYPE_CHECKING:
    from discord_mcp.core.bot import Bot
    from discord_mcp.core.server.mcp_server import BaseDiscordMCPServer, DiscordMCPStarletteApp, STDIODiscordMCPServer

    ServerT = TypeVar("ServerT", bound=BaseDiscordMCPServer[t.Any], default=BaseDiscordMCPServer[t.Any])
else:
    # to avoid importing BaseDiscordMCPServer at runtime causing circular imports errors
    ServerT = TypeVar("ServerT")


__all__: tuple[str, ...] = (
    "DiscordMCPLifespanResult",
    "DiscordMCPContext",
    "starlette_lifespan",
    "stdio_lifespan",
    "get_context",
)


logger = logging.getLogger(__name__)


@attrs.define
class DiscordMCPLifespanResult(t.Generic[ServerT], collections.UserDict[str, t.Any]):
    bot: Bot
    mcp_server: ServerT

    def __attrs_post_init__(self) -> None:
        self.data = attrs.asdict(self, recurse=True)

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(data={self.data})"


class DiscordMCPContext(Context[ServerSession, DiscordMCPLifespanResult[ServerT], t.Any]):
    @property
    def bot(self) -> Bot:
        """Returns :class:`Bot`: a shortcut property, this is equivalent to `DiscordMCPContext.request_context.lifespan_context.bot`."""
        return self.request_context.lifespan_context.bot

    @property
    def mcp_server(self) -> ServerT:
        """Returns :class:`BaseDiscordMCPServer`: a shortcut property, this is equivalent to `DiscordMCPContext.request_context.lifespan_context.mcp_server`."""
        return self.request_context.lifespan_context.mcp_server


@contextlib.asynccontextmanager
async def _manage_bot_lifecycle(
    bot: Bot, mcp_server: BaseDiscordMCPServer[t.Any]
) -> t.AsyncIterator[DiscordMCPLifespanResult]:
    """Common bot lifecycle management for both server types."""
    await bot.login(str(bot.environment.DISCORD_TOKEN))
    _bot_task = asyncio.create_task(bot.connect())
    try:
        await bot.wait_until_ready()
        logger.info(f"Discord bot connected as {bot.user}")
        yield DiscordMCPLifespanResult(
            bot=bot,
            mcp_server=mcp_server,
        )
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

    await app.mcp_server.setup()
    async with app.session_manager.run():
        async with _manage_bot_lifecycle(app.bot, mcp_server=app.mcp_server) as result:
            yield result


@contextlib.asynccontextmanager
async def stdio_lifespan(app: STDIODiscordMCPServer) -> t.AsyncIterator[DiscordMCPLifespanResult]:
    await app.setup()
    async with _manage_bot_lifecycle(app.bot, mcp_server=app) as result:
        yield result
        logger.info("Application shutting down...")


def get_context() -> DiscordMCPContext:
    try:
        request_context = request_ctx.get()
    except LookupError:
        request_context = None
    ctx = DiscordMCPContext(_request_context=request_context, _fastmcp=None)
    if ctx.request_context and ctx.request_context.request and isinstance(ctx.request_context.request, Request):
        ctx.request_context.lifespan_context = t.cast(DiscordMCPLifespanResult, ctx.request_context.request.state)
    return ctx
