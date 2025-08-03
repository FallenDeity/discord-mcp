from __future__ import annotations

import logging
import typing as t

import uvicorn
from mcp.server.fastmcp.server import StreamableHTTPASGIApp
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount

from discord_mcp.core.discord_ext.bot import DiscordMCPBot
from discord_mcp.core.server.base import BaseDiscordMCPServer
from discord_mcp.core.server.shared.context import starlette_lifespan
from discord_mcp.persistence.adapters.sqlite_adapter import SQLiteAdapeter
from discord_mcp.persistence.event_store import PersistentEventStore

__all__: tuple[str, ...] = (
    "DiscordMCPStarletteApp",
    "HTTPDiscordMCPServer",
)


logger = logging.getLogger(__name__)


class DiscordMCPStarletteApp(Starlette):
    def __init__(
        self,
        bot: DiscordMCPBot,
        mcp_server: HTTPDiscordMCPServer,
        session_manager: StreamableHTTPSessionManager | None = None,
        *args: t.Any, 
        **kwargs: t.Any,
    ) -> None:
        self.bot = bot
        self.mcp_server = mcp_server
        self.session_manager = session_manager
        super().__init__(*args, **kwargs, lifespan=starlette_lifespan)


class HTTPDiscordMCPServer(BaseDiscordMCPServer[Request]):
    @property
    def streamable_http_app(self) -> Starlette:
        # TODO: Make this configurable from cli
        event_store = PersistentEventStore(adapter=SQLiteAdapeter())
        session_manager = StreamableHTTPSessionManager(app=self, event_store=event_store)

        # TODO: Add auth stuff here, and make mount path configurable from cli
        starlette_app = DiscordMCPStarletteApp(
            bot=self.bot,
            session_manager=session_manager,
            mcp_server=self,
            debug=True,
            routes=[Mount("/mcp", app=StreamableHTTPASGIApp(session_manager))],
        )
        return starlette_app

    @classmethod
    def start(cls) -> None:
        mcp = cls(name="http-server", bot=DiscordMCPBot())
        uvicorn.run(
            mcp.streamable_http_app,
            host=mcp.settings.host,
            port=mcp.settings.port,
            log_config=None,
            access_log=False,
        )
