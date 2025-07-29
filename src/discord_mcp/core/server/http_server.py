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

    @mcp.tool()
    async def get_bot_info(ctx: DiscordMCPContext) -> dict[str, t.Any]:  # type: ignore
        """Get information about the discord bot."""
        bot = ctx.request_context.lifespan_context.bot
        if not bot.user:
            logger.warning("Bot user is not available.")
            raise ValueError("Bot user is not available.")
        return bot.user._to_minimal_user_json()

    uvicorn.run(
        mcp.streamable_http_app,
        host="127.0.0.1",
        port=8000,
        log_config=None,
        access_log=False,
    )
