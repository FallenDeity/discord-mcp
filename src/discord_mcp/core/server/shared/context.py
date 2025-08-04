from __future__ import annotations

import asyncio
import collections
import contextlib
import logging
import typing as t

import attrs
from mcp.server.fastmcp.server import Context, FastMCP
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server.lowlevel.server import request_ctx
from mcp.server.session import ServerSession
from mcp.shared.context import RequestContext
from pydantic import AnyUrl
from typing_extensions import TypeVar

if t.TYPE_CHECKING:
    from discord_mcp.core.discord_ext.bot import DiscordMCPBot
    from discord_mcp.core.server.base import BaseDiscordMCPServer
    from discord_mcp.core.server.http_server import DiscordMCPStarletteApp
    from discord_mcp.core.server.stdio_server import STDIODiscordMCPServer

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
    bot: DiscordMCPBot
    mcp_server: ServerT

    def __attrs_post_init__(self) -> None:
        self.data = attrs.asdict(self, recurse=True)

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(data={self.data})"


class DiscordMCPContext(Context[ServerSession, DiscordMCPLifespanResult[ServerT], t.Any]):
    def __init__(
        self,
        *,
        request_context: RequestContext[ServerSession, t.Any, t.Any] | None,
        fastmcp: FastMCP | None,
        **kwargs: t.Any,
    ) -> None:
        super().__init__(request_context=request_context, fastmcp=fastmcp, **kwargs)

    @property
    def bot(self) -> DiscordMCPBot:
        """Returns :class:`Bot`: a shortcut property, this is equivalent to `DiscordMCPContext.request_context.lifespan_context.bot`."""
        return self.request_context.lifespan_context.bot

    @property
    def mcp_server(self) -> ServerT:
        """Returns :class:`BaseDiscordMCPServer`: a shortcut property, this is equivalent to `DiscordMCPContext.request_context.lifespan_context.mcp_server`."""
        return self.request_context.lifespan_context.mcp_server

    async def read_resource(self, uri: str | AnyUrl) -> t.Iterable[ReadResourceContents]:
        return await self.mcp_server._read_resource(uri)


@contextlib.asynccontextmanager
async def _manage_bot_lifecycle(
    bot: DiscordMCPBot, mcp_server: BaseDiscordMCPServer[t.Any]
) -> t.AsyncIterator[DiscordMCPLifespanResult[BaseDiscordMCPServer[t.Any]]]:
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
async def starlette_lifespan(
    app: DiscordMCPStarletteApp,
) -> t.AsyncIterator[DiscordMCPLifespanResult[BaseDiscordMCPServer[t.Any]]]:
    if not app.session_manager:
        raise RuntimeError("Session manager is not initialized, cannot run lifespan context")

    logger.info("Starting application with StreamableHTTP session manager...")

    async with app.session_manager.run():
        async with _manage_bot_lifecycle(app.bot, mcp_server=app.mcp_server) as result:
            yield result


@contextlib.asynccontextmanager
async def stdio_lifespan(
    app: STDIODiscordMCPServer,
) -> t.AsyncIterator[DiscordMCPLifespanResult[BaseDiscordMCPServer[t.Any]]]:
    async with _manage_bot_lifecycle(app.bot, mcp_server=app) as result:
        yield result
        logger.info("Application shutting down...")


def get_context() -> DiscordMCPContext:
    try:
        request_context = request_ctx.get()
    except LookupError:
        request_context = None
    return DiscordMCPContext(request_context=request_context, fastmcp=None)
