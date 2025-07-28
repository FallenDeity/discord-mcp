from __future__ import annotations

import asyncio
import collections
import contextlib
import logging
import typing as t

import attrs
from mcp.server.fastmcp import Context
from mcp.server.session import ServerSession

if t.TYPE_CHECKING:
    from discord_mcp.core.bot import Bot
    from discord_mcp.core.server.mcp_server import DiscordMCPStarletteApp, STDIODiscordMCPServer


__all__: tuple[str, ...] = (
    "DiscordMCPLifespanResult",
    "DiscordMCPContext",
    "starlette_lifespan",
    "stdio_lifespan",
)


logger = logging.getLogger(__name__)


@attrs.define
class DiscordMCPLifespanResult(collections.UserDict[str, t.Any]):
    bot: Bot

    def __attrs_post_init__(self) -> None:
        self.data = attrs.asdict(self, recurse=True)

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(data={self.data})"


class DiscordMCPContext(Context[ServerSession, DiscordMCPLifespanResult, t.Any]): ...


@contextlib.asynccontextmanager
async def starlette_lifespan(app: DiscordMCPStarletteApp) -> t.AsyncIterator[DiscordMCPLifespanResult]:
    if not app.session_manager:
        raise RuntimeError("Session manager is not initialized, cannot run lifespan context")

    logger.info("Starting application with StreamableHTTP session manager...")

    async with app.session_manager.run():
        logger.info("Application started with StreamableHTTP session manager!")

        await app.bot.login(str(app.bot.environment.DISCORD_TOKEN))
        _bot_task = asyncio.create_task(app.bot.connect())
        try:
            await app.bot.wait_until_ready()
            logger.info(f"Discord bot connected as {app.bot.user}")
            yield DiscordMCPLifespanResult(bot=app.bot)
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
            await app.bot.close()

            logger.info("Application shutdown complete.")


@contextlib.asynccontextmanager
async def stdio_lifespan(app: STDIODiscordMCPServer) -> t.AsyncIterator[DiscordMCPLifespanResult]:
    await app.bot.login(str(app.bot.environment.DISCORD_TOKEN))
    _bot_task = asyncio.create_task(app.bot.connect())
    try:
        await app.bot.wait_until_ready()
        logger.info(f"Discord bot connected as {app.bot.user}")
        yield DiscordMCPLifespanResult(bot=app.bot)
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
        await app.bot.close()

        logger.info("Application shutdown complete.")
