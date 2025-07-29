from __future__ import annotations

import logging
import typing as t

from mcp.server.fastmcp.server import Context, Settings, StreamableHTTPASGIApp
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import AnyFunction, ContentBlock, Tool, ToolAnnotations
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount

from discord_mcp.core.bot import Bot
from discord_mcp.core.server.common.context import (
    DiscordMCPContext,
    DiscordMCPLifespanResult,
    starlette_lifespan,
    stdio_lifespan,
)
from discord_mcp.core.server.common.middleware import RequestLoggingMiddleware
from discord_mcp.core.server.common.tools.manager import DiscordMCPToolManager
from discord_mcp.persistence.adapters.sqlite_adapter import SQLiteAdapeter
from discord_mcp.persistence.event_store import PersistentEventStore

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
        settings: Settings[DiscordMCPLifespanResult] = Settings(lifespan=None),
        **kwargs: t.Any,
    ) -> None:
        self.bot = bot
        self.settings = settings
        self._tool_manager = DiscordMCPToolManager(warn_on_duplicate_tools=self.settings.warn_on_duplicate_tools)
        super().__init__(*args, name=name, **kwargs)
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Set up core MCP protocol handlers."""
        self.list_tools()(self._list_tools)
        # Note: we disable the lowlevel server's input validation.
        # FastMCP does ad hoc conversion of incoming data before validating -
        # for now we preserve this for backwards compatibility.
        self.call_tool(validate_input=False)(self._call_tool)

    async def _list_tools(self) -> list[Tool]:
        """List all available tools."""
        tools = self._tool_manager.list_tools()
        return [
            Tool(
                name=info.name,
                title=info.title,
                description=info.description,
                inputSchema=info.parameters,
                outputSchema=info.output_schema,
                annotations=info.annotations,
            )
            for info in tools
        ]

    def get_context(self) -> DiscordMCPContext:
        """
        Returns a Context object. Note that the context will only be valid
        during a request; outside a request, most methods will error.
        """
        try:
            request_context = self.request_context
        except LookupError:
            request_context = None
        return Context(request_context=request_context, fastmcp=None)

    async def _call_tool(self, name: str, arguments: dict[str, t.Any]) -> t.Sequence[ContentBlock] | dict[str, t.Any]:
        result = await self._tool_manager.call_tool(name, arguments, context=self.get_context(), convert_result=True)
        if isinstance(result, tuple):
            return t.cast(dict[str, t.Any], result[1])
        return t.cast(t.Sequence[ContentBlock], result)

    # TODO: Offload these decorator functions into a central registry, and just load them here using a plugin system.
    def add_tool(
        self,
        fn: AnyFunction,
        name: str | None = None,
        title: str | None = None,
        description: str | None = None,
        annotations: ToolAnnotations | None = None,
        structured_output: bool | None = None,
    ) -> None:
        """Add a tool to the server.

        The tool function can optionally request a Context object by adding a parameter
        with the Context type annotation. See the @tool decorator for examples.

        Args:
            fn: The function to register as a tool
            name: Optional name for the tool (defaults to function name)
            title: Optional human-readable title for the tool
            description: Optional description of what the tool does
            annotations: Optional ToolAnnotations providing additional tool information
            structured_output: Controls whether the tool's output is structured or unstructured
                - If None, auto-detects based on the function's return type annotation
                - If True, unconditionally creates a structured tool (return type annotation permitting)
                - If False, unconditionally creates an unstructured tool
        """
        self._tool_manager.add_tool(
            fn,
            name=name,
            title=title,
            description=description,
            annotations=annotations,
            structured_output=structured_output,
        )

    def tool(
        self,
        name: str | None = None,
        title: str | None = None,
        description: str | None = None,
        annotations: ToolAnnotations | None = None,
        structured_output: bool | None = None,
    ) -> t.Callable[[AnyFunction], AnyFunction]:
        """Decorator to register a tool.

        Tools can optionally request a Context object by adding a parameter with the
        Context type annotation. The context provides access to MCP capabilities like
        logging, progress reporting, and resource access.

        Args:
            name: Optional name for the tool (defaults to function name)
            title: Optional human-readable title for the tool
            description: Optional description of what the tool does
            annotations: Optional ToolAnnotations providing additional tool information
            structured_output: Controls whether the tool's output is structured or unstructured
                - If None, auto-detects based on the function's return type annotation
                - If True, unconditionally creates a structured tool (return type annotation permitting)
                - If False, unconditionally creates an unstructured tool

        Example:
            @server.tool()
            def my_tool(x: int) -> str:
                return str(x)

            @server.tool()
            def tool_with_context(x: int, ctx: Context) -> str:
                ctx.info(f"Processing {x}")
                return str(x)

            @server.tool()
            async def async_tool(x: int, context: Context) -> str:
                await context.report_progress(50, 100)
                return str(x)
        """
        # Check if user passed function directly instead of calling decorator
        if callable(name):
            raise TypeError(
                "The @tool decorator was used incorrectly. Did you forget to call it? Use @tool() instead of @tool"
            )

        def decorator(fn: AnyFunction) -> AnyFunction:
            self.add_tool(
                fn,
                name=name,
                title=title,
                description=description,
                annotations=annotations,
                structured_output=structured_output,
            )
            return fn

        return decorator


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
            debug=True,
            routes=[Mount("/mcp", app=StreamableHTTPASGIApp(session_manager))],
        )
        return starlette_app

    def get_context(self) -> DiscordMCPContext:
        """
        Returns a Context object. Note that the context will only be valid
        during a request; outside a request, most methods will error. For a Starlette app,
        this will return a Context with the lifespan context set to the current request's state.
        """
        ctx = super().get_context()
        if ctx.request_context and ctx.request_context.request:
            ctx.request_context.lifespan_context = t.cast(DiscordMCPLifespanResult, ctx.request_context.request.state)
        return ctx


class STDIODiscordMCPServer(BaseDiscordMCPServer[Request]):
    def __init__(self, *args: t.Any, name: str, bot: Bot, **kwargs: t.Any) -> None:
        super().__init__(
            *args, name=name, bot=bot, **kwargs, lifespan=stdio_lifespan
        )  # pyright: ignore[reportUnknownLambdaType]
