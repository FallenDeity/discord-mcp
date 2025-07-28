import logging
import typing as t

import uvicorn
from mcp.types import ContentBlock, TextContent, Tool

from discord_mcp.core.server.mcp_server import HTTPDiscordMCPServer

if t.TYPE_CHECKING:
    from discord_mcp.core.bot import Bot


logger = logging.getLogger(__name__)


# def run_server(bot: "Bot") -> None:
#     mcp = FastMCP("http-server")
#     mcp.bot = bot  # type: ignore

#     @mcp.tool()
#     async def ping(ctx: DiscordMCPContext) -> str:
#         return "Pong!"

#     mcp.run()


def run_server(bot: "Bot") -> None:
    mcp = HTTPDiscordMCPServer(name="http-server", bot=bot)

    @mcp.list_tools()
    async def list_tools() -> list[Tool]:  # type: ignore
        """List available tools."""
        logger.info("Listing tools")
        return [
            Tool(
                name="get_latency",
                description="Get the latency of the discord bot",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            )
        ]

    @mcp.call_tool()
    async def call_tool(name: str, args: t.Any) -> list[ContentBlock]:  # type: ignore
        """Call a tool by name with arguments."""
        logger.info(f"Calling tool: {name} with args: {args}")
        assert mcp.request_context.request is not None, "Request context must have a request"

        if name == "get_latency":
            return [
                TextContent(
                    type="text",
                    text=f"Latency: {mcp.request_context.request.state.bot.latency * 1000:.2f} ms",
                )
            ]
        raise ValueError(f"Tool '{name}' not found")

    uvicorn.run(
        mcp.streamable_http_app,
        host="127.0.0.1",
        port=8000,
        log_config=None,
        access_log=False,
    )
