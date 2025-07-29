import logging
import typing as t

import uvicorn

from discord_mcp.core.server.common.context import DiscordMCPContext
from discord_mcp.core.server.mcp_server import HTTPDiscordMCPServer

if t.TYPE_CHECKING:
    from discord_mcp.core.bot import Bot


logger = logging.getLogger(__name__)


def run_server(bot: "Bot") -> None:
    mcp = HTTPDiscordMCPServer(name="http-server", bot=bot)

    # TODO: This will be replaced with a more dynamic tool loading system.
    @mcp.tool()
    async def get_latency(ctx: DiscordMCPContext) -> str:  # type: ignore
        """Get the latency of the discord bot."""
        return f"Latency: {ctx.request_context.lifespan_context.bot.latency * 1000:.2f} ms"

    uvicorn.run(
        mcp.streamable_http_app,
        host="127.0.0.1",
        port=8000,
        log_config=None,
        access_log=False,
    )
