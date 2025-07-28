from __future__ import annotations

import logging
import typing as t

from mcp.server.fastmcp.server import StreamableHTTPASGIApp
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount

from discord_mcp.core.bot import Bot
from discord_mcp.core.server.common.context import DiscordMCPLifespanResult, starlette_lifespan, stdio_lifespan
from discord_mcp.core.server.common.middleware import RequestLoggingMiddleware

if t.TYPE_CHECKING:
    from discord_mcp.core.bot import Bot


__all__: tuple[str, ...] = ("DiscordMCPStarletteApp", "BaseDiscordMCPServer", "HTTPDiscordMCPServer")


RequestT = t.TypeVar("RequestT", bound=t.Any)


logger = logging.getLogger(__name__)


class DiscordMCPStarletteApp(Starlette):
    def __init__(
        self, *args: t.Any, bot: Bot, session_manager: StreamableHTTPSessionManager | None = None, **kwargs: t.Any
    ) -> None:
        self.bot = bot
        self.session_manager = session_manager
        super().__init__(*args, **kwargs, lifespan=starlette_lifespan)
        self.add_middleware(RequestLoggingMiddleware)


class BaseDiscordMCPServer(Server[DiscordMCPLifespanResult, RequestT]):
    def __init__(
        self,
        *args: t.Any,
        name: str,
        bot: Bot,
        **kwargs: t.Any,
    ) -> None:
        self.bot = bot
        super().__init__(*args, name=name, **kwargs)


class HTTPDiscordMCPServer(BaseDiscordMCPServer[Request]):
    @property
    def streamable_http_app(self) -> Starlette:
        # TODO: Add event store and other stuff here
        session_manager = StreamableHTTPSessionManager(app=self)

        # TODO: Add auth stuff here, and make mount path configurable
        starlette_app = DiscordMCPStarletteApp(
            bot=self.bot,
            session_manager=session_manager,
            debug=True,
            routes=[Mount("/mcp", app=StreamableHTTPASGIApp(session_manager))],
        )
        return starlette_app


class STDIODiscordMCPServer(BaseDiscordMCPServer[Request]):
    def __init__(self, *args: t.Any, name: str, bot: Bot, **kwargs: t.Any) -> None:
        super().__init__(
            *args, name=name, bot=bot, **kwargs, lifespan=stdio_lifespan
        )  # pyright: ignore[reportUnknownLambdaType]
