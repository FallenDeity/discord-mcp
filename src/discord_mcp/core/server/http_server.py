from __future__ import annotations

import logging
import typing as t

from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.types import Receive, Scope, Send

from discord_mcp.core.server.common.context import lifespan

if t.TYPE_CHECKING:
    from discord_mcp.core.bot import Bot


logger = logging.getLogger(__name__)


def run_server(bot: Bot) -> None:
    """Run the Discord MCP server."""
    mcp = Server("http-server")

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

    import uvicorn

    uvicorn.run(starlette_app, host="127.0.0.1", port=8000, log_config=None, access_log=False)
