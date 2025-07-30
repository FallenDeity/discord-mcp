from __future__ import annotations

import inspect
import logging
import re
import typing as t

from mcp.server.fastmcp.exceptions import ResourceError
from mcp.server.fastmcp.resources import FunctionResource, Resource
from mcp.server.fastmcp.resources.resource_manager import ResourceManager
from mcp.server.fastmcp.server import Context, Settings, StreamableHTTPASGIApp
from mcp.server.lowlevel import Server
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import (
    AnyFunction,
    ContentBlock,
)
from mcp.types import Resource as MCPResource
from mcp.types import ResourceTemplate as MCPResourceTemplate
from mcp.types import (
    Tool,
    ToolAnnotations,
)
from pydantic.networks import AnyUrl
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
from discord_mcp.utils.converters import convert_name_to_title, extract_mime_type_from_fn_return

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
        self._resource_manager = ResourceManager(warn_on_duplicate_resources=self.settings.warn_on_duplicate_resources)
        super().__init__(*args, name=name, **kwargs)
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Set up core MCP protocol handlers."""
        self.list_tools()(self._list_tools)
        # Note: we disable the lowlevel server's input validation.
        # FastMCP does ad hoc conversion of incoming data before validating -
        # for now we preserve this for backwards compatibility.
        self.call_tool(validate_input=False)(self._call_tool)
        self.list_resources()(self._list_resources)
        self.list_resource_templates()(self._list_resource_templates)
        self.read_resource()(self._read_resource)

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

    async def _list_resources(self) -> list[MCPResource]:
        """List all available resources."""
        resources = self._resource_manager.list_resources()
        return [
            MCPResource(
                uri=resource.uri,
                name=resource.name or "",
                title=resource.title,
                description=resource.description,
                mimeType=resource.mime_type,
            )
            for resource in resources
        ]

    async def _list_resource_templates(self) -> list[MCPResourceTemplate]:
        templates = self._resource_manager.list_templates()
        return [
            MCPResourceTemplate(
                uriTemplate=template.uri_template,
                name=template.name,
                title=template.title,
                description=template.description,
            )
            for template in templates
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

    def add_resource(self, resource: Resource) -> None:
        self._resource_manager.add_resource(resource)

    def resource(
        self,
        uri: str,
        *,
        name: str | None = None,
        title: str | None = None,
        description: str | None = None,
        mime_type: str | None = None,
    ) -> t.Callable[[AnyFunction], AnyFunction]:
        """Decorator to register a function as a resource.

        The function will be called when the resource is read to generate its content.
        The function can return:
        - str for text content
        - bytes for binary content
        - other types will be converted to JSON

        If the URI contains parameters (e.g. "resource://{param}") or the function
        has parameters, it will be registered as a template resource.

        Args:
            uri: URI for the resource (e.g. "resource://my-resource" or "resource://{param}")
            name: Optional name for the resource
            title: Optional human-readable title for the resource
            description: Optional description of the resource
            mime_type: Optional MIME type for the resource

        Example:
            @server.resource("resource://my-resource")
            def get_data() -> str:
                return "Hello, world!"

            @server.resource("resource://my-resource")
            async get_data() -> str:
                data = await fetch_data()
                return f"Hello, world! {data}"

            @server.resource("resource://{city}/weather")
            def get_weather(city: str) -> str:
                return f"Weather for {city}"

            @server.resource("resource://{city}/weather")
            async def get_weather(city: str) -> str:
                data = await fetch_weather(city)
                return f"Weather for {city}: {data}"
        """
        # Check if user passed function directly instead of calling decorator
        if callable(uri):
            raise TypeError(
                "The @resource decorator was used incorrectly. "
                "Did you forget to call it? Use @resource('uri') instead of @resource"
            )

        def decorator(fn: AnyFunction) -> AnyFunction:
            # Check if this should be a template
            has_uri_params = "{" in uri and "}" in uri
            has_func_params = bool(inspect.signature(fn).parameters)

            # help typecheckers not cry about unbound variables
            nonlocal title, mime_type
            title = title or convert_name_to_title(name or fn.__name__)
            mime_type = mime_type or extract_mime_type_from_fn_return(fn)

            if has_uri_params or has_func_params:
                # Validate that URI params match function params
                uri_params = set(re.findall(r"{(\w+)}", uri))
                func_params = set(inspect.signature(fn).parameters.keys())

                if uri_params != func_params:
                    raise ValueError(
                        f"Mismatch between URI parameters {uri_params} and function parameters {func_params}"
                    )

                # Register as template
                self._resource_manager.add_template(
                    fn=fn,
                    uri_template=uri,
                    name=name,
                    title=title,
                    description=description,
                    mime_type=mime_type,
                )
            else:
                # Register as regular resource
                resource = FunctionResource.from_function(
                    fn=fn,
                    uri=uri,
                    name=name,
                    title=title,
                    description=description,
                    mime_type=mime_type,
                )
                self.add_resource(resource)
            return fn

        return decorator

    async def _read_resource(self, uri: AnyUrl | str) -> t.Iterable[ReadResourceContents]:
        """Read a resource by URI."""

        resource = await self._resource_manager.get_resource(uri)
        if not resource:
            raise ResourceError(f"Unknown resource: {uri}")

        try:
            content = await resource.read()
            return [ReadResourceContents(content=content, mime_type=resource.mime_type)]
        except Exception as e:
            logger.exception(f"Error reading resource {uri}")
            raise ResourceError(str(e))


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
