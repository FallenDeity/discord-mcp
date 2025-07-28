from __future__ import annotations

import logging
import typing as t

from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import TextContent, Tool
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.types import Receive, Scope, Send

from discord_mcp.core.server.common.context import lifespan
from discord_mcp.core.server.common.middleware import RequestLoggingMiddleware

if t.TYPE_CHECKING:
    from discord_mcp.core.bot import Bot


logger = logging.getLogger(__name__)


def run_server(bot: Bot) -> None:
    """Run the Discord MCP server."""
    mcp = Server("http-server")

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
    async def call_tool(name: str, args: t.Any) -> list[TextContent]:  # type: ignore
        """Call a tool by name with arguments."""
        logger.info(f"Calling tool: {name} with args: {args}")
        print(mcp.request_context.lifespan_context)
        if name == "get_latency":
            return [
                TextContent(
                    type="text",
                    text=f"Latency: {bot.latency * 1000:.2f} ms",
                )
            ]
        raise ValueError(f"Tool '{name}' not found")

    session_manager = StreamableHTTPSessionManager(app=mcp)

    # ASGI handler for streamable HTTP connections
    async def handle_streamable_http(scope: Scope, receive: Receive, send: Send) -> None:
        await session_manager.handle_request(scope, receive, send)

    starlette_app = Starlette(
        debug=True,
        routes=[
            Mount("/mcp", app=handle_streamable_http),
        ],
        lifespan=lifespan,
    )
    starlette_app.session_manager = session_manager  # type: ignore
    starlette_app.bot = bot  # type: ignore

    starlette_app.add_middleware(RequestLoggingMiddleware)

    import uvicorn

    uvicorn.run(starlette_app, host="127.0.0.1", port=8000, log_config=None, access_log=False)
