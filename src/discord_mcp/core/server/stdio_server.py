from __future__ import annotations

import logging
import typing as t

from mcp import stdio_server

from discord_mcp.core.discord_ext.bot import DiscordMCPBot
from discord_mcp.core.server.base import BaseDiscordMCPServer
from discord_mcp.core.server.shared.context import stdio_lifespan

__all__: tuple[str, ...] = ("STDIODiscordMCPServer",)


logger = logging.getLogger(__name__)


class STDIODiscordMCPServer(BaseDiscordMCPServer[None]):
    def __init__(self, *args: t.Any, name: str, bot: DiscordMCPBot, **kwargs: t.Any) -> None:
        super().__init__(*args, name=name, bot=bot, **kwargs, lifespan=stdio_lifespan)

    @classmethod
    async def start(cls) -> None:
        """Start the STDIO server."""
        mcp = cls(name="stdio-server", bot=DiscordMCPBot())
        async with stdio_server() as (read_stream, write_stream):
            await mcp.run(read_stream, write_stream, mcp.create_initialization_options())
