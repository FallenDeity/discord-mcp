import logging
import typing as t

from mcp import stdio_server

from discord_mcp.core.server.common.context import DiscordMCPContext
from discord_mcp.core.server.mcp_server import STDIODiscordMCPServer

if t.TYPE_CHECKING:
    from discord_mcp.core.bot import Bot


logger = logging.getLogger(__name__)


async def run_server(bot: "Bot") -> None:
    """Run the Discord MCP server."""
    mcp = STDIODiscordMCPServer(name="stdio-server", bot=bot)

    # TODO: This will be replaced with a more dynamic tool loading system.
    @mcp.tool()
    async def get_latency(ctx: DiscordMCPContext) -> str:  # type: ignore
        """Get the latency of the discord bot."""
        return f"Latency: {ctx.request_context.lifespan_context.bot.latency * 1000:.2f} ms"

    async with stdio_server() as (read_stream, write_stream):
        await mcp.run(read_stream, write_stream, mcp.create_initialization_options())
