from __future__ import annotations

import logging
import typing as t

import pydantic
import uvicorn

from discord_mcp.core.server.common.context import DiscordMCPContext, get_context
from discord_mcp.core.server.mcp_server import HTTPDiscordMCPServer

if t.TYPE_CHECKING:
    from discord_mcp.core.bot import Bot


logger = logging.getLogger(__name__)


class UserInfo(pydantic.BaseModel):
    id: int
    username: str
    discriminator: str
    avatar_url: t.Optional[str] = None


def run_server(bot: Bot) -> None:
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

    @mcp.resource("resource://greeting")
    def get_greeting() -> str:  # type: ignore
        """Provides a simple greeting message."""
        return "Hello from FastMCP Resources!"

    # Resource returning JSON data (dict is auto-serialized)
    @mcp.resource("data://config")
    def get_config() -> dict[str, t.Any]:  # type: ignore
        """Provides application configuration as JSON."""
        return {
            "theme": "dark",
            "version": "1.2.0",
            "features": ["tools", "resources"],
        }

    @mcp.resource("resource://system-status")
    async def get_system_status(ctx: DiscordMCPContext) -> dict[str, t.Any]:  # type: ignore
        """Provides system status information."""
        context = get_context()
        print(f"Context: {context.request_context}, lifespan: {context.request_context.lifespan_context}")
        return {
            "status": "operational",
            "request_id": ctx.request_id,
            "uptime": f"{ctx.request_context.lifespan_context.bot.uptime.total_seconds()} seconds",
        }

    @mcp.resource("resource://user-info/{user_id}")
    async def get_user_info(ctx: DiscordMCPContext, user_id: int) -> UserInfo:  # type: ignore
        """Get information about a user by ID."""
        bot = ctx.request_context.lifespan_context.bot
        user = bot.get_user(user_id) or await bot.fetch_user(user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found.")
        return UserInfo(
            id=user.id, username=user.name, discriminator=user.discriminator, avatar_url=user.display_avatar.url
        )

    uvicorn.run(
        mcp.streamable_http_app,
        host="127.0.0.1",
        port=8000,
        log_config=None,
        access_log=False,
    )
