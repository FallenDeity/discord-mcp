from __future__ import annotations

import logging
import typing as t

import pydantic
import uvicorn

from discord_mcp.core.server.common.context import DiscordMCPContext
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
    async def get_latency(ctx: DiscordMCPContext) -> str:  # type: ignore[misc]
        """Get the latency of the discord bot."""
        return f"Latency: {ctx.request_context.lifespan_context.bot.latency * 1000:.2f} ms"

    @mcp.tool()
    async def get_bot_info(ctx: DiscordMCPContext) -> dict[str, t.Any]:  # type: ignore[misc]
        """Get information about the discord bot."""
        bot = ctx.request_context.lifespan_context.bot
        if not bot.user:
            logger.warning("Bot user is not available.")
            raise ValueError("Bot user is not available.")
        return bot.user._to_minimal_user_json()

    @mcp.resource("resource://greeting")
    def get_greeting() -> str:  # type: ignore[misc]
        """Provides a simple greeting message."""
        return "Hello from FastMCP Resources!"

    # Resource returning JSON data (dict is auto-serialized)
    @mcp.resource("data://config")
    def get_config() -> dict[str, t.Any]:  # type: ignore[misc]
        """Provides application configuration as JSON."""
        return {
            "theme": "dark",
            "version": "1.2.0",
            "features": ["tools", "resources"],
        }

    @mcp.resource("resource://system-status")
    async def get_system_status(ctx: DiscordMCPContext) -> dict[str, t.Any]:  # type: ignore[misc]
        """Provides system status information."""
        return {
            "status": "operational",
            "request_id": ctx.request_id,
            "uptime": f"{ctx.request_context.lifespan_context.bot.uptime.total_seconds()} seconds",
        }

    @mcp.resource("resource://user-info/{user_id}")
    async def get_user_info(ctx: DiscordMCPContext, user_id: int) -> UserInfo:  # type: ignore[misc]
        """Get information about a user by ID."""
        bot = ctx.request_context.lifespan_context.bot
        user = bot.get_user(user_id) or await bot.fetch_user(user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found.")
        return UserInfo(
            id=user.id, username=user.name, discriminator=user.discriminator, avatar_url=user.display_avatar.url
        )

    @mcp.prompt()
    def ask_about_topic(topic: str) -> str:  # type: ignore[misc]
        """Generates a user message asking for an explanation of a topic."""
        return f"Can you please explain the concept of '{topic}'?"

    @mcp.prompt()
    def analyze_data(numbers: list[int], metadata: dict[str, str], threshold: float) -> str:  # type: ignore[misc]
        """Analyze numerical data."""
        avg = sum(numbers) / len(numbers)
        return f"Average: {avg}, above threshold: {avg > threshold}"

    @mcp.prompt()
    def data_analysis_prompt(  # type: ignore[misc]
        data_uri: str,  # Required - no default value
        analysis_type: str = "summary",  # Optional - has default value
        include_charts: bool = False,  # Optional - has default value
    ) -> str:
        """Creates a request to analyze data with specific parameters."""
        prompt = f"Please perform a '{analysis_type}' analysis on the data found at {data_uri}."
        if include_charts:
            prompt += " Include relevant charts and visualizations."
        return prompt

    @mcp.prompt()
    async def generate_report_request(user_id: int, ctx: DiscordMCPContext) -> str:  # type: ignore[misc]
        """
        Generate a request for creating a user report.

        This MCP prompt function retrieves user information from Discord and formats
        it into a report generation request. It fetches user details including ID,
        username, discriminator, and avatar URL, then returns a formatted request
        string containing the user information in JSON format.

        Args:
            user_id (int): The Discord user ID to generate a report for.
            ctx (DiscordMCPContext): The MCP context containing bot instance and request metadata.

        Returns:
            str: A formatted request string containing user information in JSON format
                and the associated request ID.

        Raises:
            ValueError: If the user with the specified ID cannot be found.

        Example:
            The returned string will be in the format:
            "Please create a user {user_json} report. Request ID: {request_id}"
        """
        bot = ctx.request_context.lifespan_context.bot
        user = bot.get_user(user_id) or await bot.fetch_user(user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found.")
        user_info = UserInfo(
            id=user.id, username=user.name, discriminator=user.discriminator, avatar_url=user.display_avatar.url
        )
        return f"Please create a user {user_info.model_dump_json()} report. Request ID: {ctx.request_id}"

    mcp.load_plugins("src/discord_mcp/core/server/p_test")

    uvicorn.run(
        mcp.streamable_http_app,
        host="127.0.0.1",
        port=8000,
        log_config=None,
        access_log=False,
    )
