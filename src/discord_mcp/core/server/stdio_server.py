from __future__ import annotations

import logging
import typing as t

from mcp import stdio_server
from mcp.types import ContentBlock, TextContent, Tool

from discord_mcp.core.server.mcp_server import STDIODiscordMCPServer

if t.TYPE_CHECKING:
    from discord_mcp.core.bot import Bot


logger = logging.getLogger(__name__)


async def run_server(bot: Bot) -> None:
    """Run the Discord MCP server."""
    mcp = STDIODiscordMCPServer(name="stdio-server", bot=bot)

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

        if name == "get_latency":
            return [
                TextContent(
                    type="text",
                    text=f"Latency: {mcp.request_context.lifespan_context.bot.latency * 1000:.2f} ms",
                )
            ]
        raise ValueError(f"Tool '{name}' not found")

    async with stdio_server() as (read_stream, write_stream):
        await mcp.run(read_stream, write_stream, mcp.create_initialization_options())
