from __future__ import annotations

import asyncio
import contextlib
import logging
import typing as t
from types import TracebackType

import attrs

if t.TYPE_CHECKING:
    from mcp.server.lowlevel import Server
    from starlette.applications import Starlette

    from discord_mcp.core.bot import Bot


logger = logging.getLogger(__name__)


@attrs.define
class ServerContext:
    bot: Bot


class ServerLifespan:
    def __init__(self, server: Server[ServerContext, t.Any]) -> None:
        self._server = server
        self._bot = t.cast("Bot", server.bot)  # type: ignore
        self._bot_task: asyncio.Task[None] | None = None

    async def __aenter__(self) -> ServerContext:
        await self._bot.login(str(self._bot.environment.DISCORD_TOKEN))
        self._bot_task = asyncio.create_task(self._bot.connect())
        await self._bot.wait_until_ready()
        return ServerContext(bot=self._bot)

    async def __aexit__(
        self,
        exc_type: t.Optional[type[BaseException]],
        exc_value: t.Optional[BaseException],
        traceback: t.Optional[TracebackType],
    ) -> None:
        if self._bot_task:
            self._bot_task.cancel()
        return await self._bot.close()


@contextlib.asynccontextmanager
async def lifespan(app: Starlette) -> t.AsyncIterator[None]:
    session_manager = app.session_manager  # type: ignore
    bot = t.cast("Bot", app.bot)  # type: ignore

    # Start Streamable session manager
    async with session_manager.run():
        logger.info("Session manager running-MCP transport ready")

        await bot.login(str(bot.environment.DISCORD_TOKEN))
        _bot_task = asyncio.create_task(bot.connect())

        # Wait for bot ready
        await bot.wait_until_ready()
        logger.info(f"Discord bot connected as {bot.user}")

        try:
            yield  # now accepting both HTTP sessions & Discord bot commands
        finally:
            logger.info("Shutting down Discord bot …")
            # Cancel background task if exists
            if _bot_task:
                _bot_task.cancel()
            await bot.close()
            logger.info("Lifespan teardown complete")
