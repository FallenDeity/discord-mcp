from __future__ import annotations

import logging
import typing as t

from mcp import stdio_server
from mcp.server.lowlevel import Server

from discord_mcp.core.server.common.context import ServerLifespan

if t.TYPE_CHECKING:
    from discord_mcp.core.bot import Bot


logger = logging.getLogger(__name__)


async def run_server(bot: Bot) -> None:
    """Run the Discord MCP server."""
    mcp = Server("stdio-server", lifespan=ServerLifespan)
    mcp.bot = bot  # type: ignore

    async with stdio_server() as (read_stream, write_stream):
        await mcp.run(read_stream, write_stream, mcp.create_initialization_options())
