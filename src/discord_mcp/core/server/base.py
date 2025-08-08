from __future__ import annotations

import functools
import importlib
import inspect
import logging
import pathlib
import re
import typing as t
import warnings
from contextlib import AsyncExitStack

import anyio
import mcp.types as types
import pydantic_core
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from mcp.server.fastmcp.resources import Resource
from mcp.server.fastmcp.server import Settings
from mcp.server.lowlevel import Server
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server.lowlevel.server import request_ctx
from mcp.server.models import InitializationOptions
from mcp.server.session import ServerSession
from mcp.shared.context import RequestContext
from mcp.shared.exceptions import McpError
from mcp.shared.message import ClientMessageMetadata, ServerMessageMetadata, SessionMessage
from mcp.shared.session import RequestResponder
from mcp.types import AnyFunction, Completion, CompletionArgument, CompletionContext, ContentBlock, GetPromptResult
from mcp.types import Prompt as MCPPrompt
from mcp.types import PromptArgument as MCPPromptArgument
from mcp.types import PromptReference
from mcp.types import Resource as MCPResource
from mcp.types import ResourceTemplate as MCPResourceTemplate
from mcp.types import ResourceTemplateReference
from mcp.types import Tool as MCPTool
from mcp.types import ToolAnnotations
from pydantic.networks import AnyUrl
from starlette.requests import Request

from discord_mcp.core.discord_ext.bot import DiscordMCPBot
from discord_mcp.core.plugins.manager import DiscordMCPPluginManager
from discord_mcp.core.server.middleware import (
    CallNext,
    LoggingMiddleware,
    Middleware,
    MiddlewareContext,
    RateLimitMiddleware,
)
from discord_mcp.core.server.prompts.manager import DiscordMCPPrompt, DiscordMCPPromptManager
from discord_mcp.core.server.resources.manager import DiscordMCPFunctionResource, DiscordMCPResourceManager
from discord_mcp.core.server.shared.autocomplete import AutocompleteHandler
from discord_mcp.core.server.shared.context import DiscordMCPContext, DiscordMCPLifespanResult, get_context
from discord_mcp.core.server.shared.manifests import BaseManifest, PromptManifest, ResourceManifest, ToolManifest
from discord_mcp.core.server.shared.repository import ManifestRepository
from discord_mcp.core.server.shared.session import DiscordMCPServerSession
from discord_mcp.core.server.tools.manager import DiscordMCPToolManager
from discord_mcp.utils.checks import find_kwarg_by_type
from discord_mcp.utils.converters import convert_name_to_title, extract_mime_type_from_fn_return
from discord_mcp.utils.enums import ErrorCodes
from discord_mcp.utils.exceptions import (
    PromptNotFoundError,
    PromptRenderError,
    ResourceNotFoundError,
    ResourceReadError,
)
from discord_mcp.utils.plugins import search_directory

__all__: tuple[str, ...] = ("BaseDiscordMCPServer",)


PLUGINS_PATH = pathlib.Path(__file__).parent.parent / "discord_ext"


RequestT = t.TypeVar("RequestT", bound=t.Any)


logger = logging.getLogger(__name__)


class BaseDiscordMCPServer(Server[DiscordMCPLifespanResult, RequestT]):
    def __init__(
        self,
        *args: t.Any,
        name: str,
        bot: DiscordMCPBot,
        # TODO: Move this or aquire the settings from env or click command options, and utilize them internally
        settings: Settings[DiscordMCPLifespanResult] = Settings(
            lifespan=None,
            debug=False,
            log_level="INFO",
            host="127.0.0.1",
            port=8000,
            mount_path="/",
            sse_path="/sse",
            message_path="/messages/",
            streamable_http_path="/mcp",
            json_response=False,
            stateless_http=False,
            warn_on_duplicate_prompts=True,
            warn_on_duplicate_resources=True,
            warn_on_duplicate_tools=True,
            dependencies=[],
            auth=None,
            transport_security=None,
        ),
        **kwargs: t.Any,
    ) -> None:
        self.bot = bot
        self.settings = settings
        self.middlewares: list[Middleware] = [LoggingMiddleware(), RateLimitMiddleware()]
        self._tool_manager = DiscordMCPToolManager(warn_on_duplicate_tools=self.settings.warn_on_duplicate_tools)
        self._resource_manager = DiscordMCPResourceManager(
            warn_on_duplicate_resources=self.settings.warn_on_duplicate_resources
        )
        self._prompt_manager = DiscordMCPPromptManager(
            warn_on_duplicate_prompts=self.settings.warn_on_duplicate_prompts
        )
        self._autocomplete_callbacks: dict[str, AutocompleteHandler] = dict()
        self._manifest_repository = ManifestRepository()
        super().__init__(*args, name=name, **kwargs)
        self._setup_handlers()
        self._load_plugins(path=PLUGINS_PATH.as_posix())

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
        self.list_prompts()(self._list_prompts)
        self.get_prompt()(self._get_prompt)
        self.completion()(self._autocomplete_base_handler)

    def add_middleware(self, middleware: Middleware) -> None:
        if middleware in self.middlewares:
            logger.warning(f"Middleware {middleware} is already registered, skipping.")
            return
        self.middlewares.append(middleware)
        logger.info(f"Middleware {middleware} added successfully.")

    def remove_middleware(self, middleware: Middleware | type[Middleware]) -> None:
        """Remove a middleware from the server."""
        original_count = len(self.middlewares)
        if isinstance(middleware, type):
            self.middlewares = [m for m in self.middlewares if not isinstance(m, middleware)]
        else:
            self.middlewares = [m for m in self.middlewares if m is not middleware]
        if len(self.middlewares) == original_count:
            logger.warning(f"Middleware {middleware} not found, skipping removal.")
            return
        logger.info(f"Middleware {middleware} removed successfully.")

    async def _list_tools(self) -> list[MCPTool]:
        """List all available tools."""
        tools = self._tool_manager.list_tools()
        return [
            MCPTool(
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

    async def _call_tool(self, name: str, arguments: dict[str, t.Any]) -> t.Sequence[ContentBlock] | dict[str, t.Any]:
        result = await self._tool_manager.call_tool(name, arguments, context=get_context(), convert_result=True)
        if isinstance(result, tuple):
            return t.cast(dict[str, t.Any], result[1])
        return t.cast(t.Sequence[ContentBlock], result)

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
        enabled: bool = True,
    ) -> t.Callable[[t.Callable[..., t.Any]], ToolManifest]:
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

        def decorator(fn: t.Callable[..., t.Any]) -> ToolManifest:
            if enabled:
                self.add_tool(
                    fn,
                    name=name,
                    title=title,
                    description=description,
                    annotations=annotations,
                    structured_output=structured_output,
                )
            manifest = ToolManifest(
                fn=fn,
                name=name,
                title=title,
                description=description,
                annotations=annotations,
                structured_output=structured_output,
                enabled=enabled,
            )
            return manifest

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
        enabled: bool = True,
    ) -> t.Callable[[t.Callable[..., t.Any]], ResourceManifest]:
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

        def decorator(fn: t.Callable[..., t.Any]) -> ResourceManifest:
            # Check if this should be a template
            has_uri_params = "{" in uri and "}" in uri
            has_func_params = any(
                p
                for p in inspect.signature(fn).parameters.values()
                if p.name != find_kwarg_by_type(fn, DiscordMCPContext)
            )

            # help typecheckers not cry about unbound variables
            nonlocal title, mime_type
            title = title or convert_name_to_title(name or fn.__name__)
            mime_type = mime_type or extract_mime_type_from_fn_return(fn)

            if has_uri_params or has_func_params:
                # Validate that URI params match function params
                uri_params = set(re.findall(r"{(\w+)}", uri))
                func_params = set(inspect.signature(fn).parameters.keys())

                if context_kwarg := find_kwarg_by_type(fn, DiscordMCPContext):
                    func_params.discard(context_kwarg)

                if uri_params != func_params:
                    raise ValueError(
                        f"Mismatch between URI parameters {uri_params} and function parameters {func_params}"
                    )

                # Register as template
                if enabled:
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
                resource = DiscordMCPFunctionResource.from_function(
                    fn=fn,
                    uri=uri,
                    name=name,
                    title=title,
                    description=description,
                    mime_type=mime_type,
                )
                if enabled:
                    self.add_resource(resource)

            manifest = ResourceManifest(
                fn=fn,
                uri=uri,
                name=name,
                title=title,
                description=description,
                mime_type=mime_type,
                enabled=enabled,
            )
            return manifest

        return decorator

    async def _read_resource(self, uri: AnyUrl | str) -> t.Iterable[ReadResourceContents]:
        """Read a resource by URI."""

        resource = await self._resource_manager.get_resource(uri)
        if not resource:
            raise ResourceNotFoundError(f"Unknown resource: {uri}")

        try:
            content = await resource.read()
            return [ReadResourceContents(content=content, mime_type=resource.mime_type)]
        except Exception as e:
            logger.exception(f"Error reading resource {uri}")
            raise ResourceReadError(str(e))

    def add_prompt(self, prompt: DiscordMCPPrompt) -> None:
        """Add a prompt to the server.

        Args:
            prompt: A Prompt instance to add
        """
        self._prompt_manager.add_prompt(prompt)

    def prompt(
        self,
        name: str | None = None,
        title: str | None = None,
        description: str | None = None,
        enabled: bool = True,
    ) -> t.Callable[[t.Callable[..., t.Any]], PromptManifest]:
        """Decorator to register a prompt.

        Args:
            name: Optional name for the prompt (defaults to function name)
            title: Optional human-readable title for the prompt
            description: Optional description of what the prompt does

        Example:
            @server.prompt()
            def analyze_table(table_name: str) -> list[Message]:
                schema = read_table_schema(table_name)
                return [
                    {
                        "role": "user",
                        "content": f"Analyze this schema:\n{schema}"
                    }
                ]

            @server.prompt()
            async def analyze_file(path: str) -> list[Message]:
                content = await read_file(path)
                return [
                    {
                        "role": "user",
                        "content": {
                            "type": "resource",
                            "resource": {
                                "uri": f"file://{path}",
                                "text": content
                            }
                        }
                    }
                ]
        """
        # Check if user passed function directly instead of calling decorator
        if callable(name):
            raise TypeError(
                "The @prompt decorator was used incorrectly. "
                "Did you forget to call it? Use @prompt() instead of @prompt"
            )

        def decorator(func: t.Callable[..., t.Any]) -> PromptManifest:
            prompt = DiscordMCPPrompt.from_function(func, name=name, title=title, description=description)
            if enabled:
                self.add_prompt(prompt)

            manifest = PromptManifest(
                fn=func,
                name=name,
                description=description,
                title=title,
                enabled=enabled,
            )
            return manifest

        return decorator

    async def _list_prompts(self) -> list[MCPPrompt]:
        """List all available prompts."""
        prompts = self._prompt_manager.list_prompts()
        return [
            MCPPrompt(
                name=prompt.name,
                title=prompt.title,
                description=prompt.description,
                arguments=[
                    MCPPromptArgument(
                        name=arg.name,
                        description=arg.description,
                        required=arg.required,
                    )
                    for arg in (prompt.arguments or [])
                ],
            )
            for prompt in prompts
        ]

    async def _get_prompt(self, name: str, arguments: dict[str, t.Any] | None = None) -> GetPromptResult:
        """Get a prompt by name with arguments."""
        try:
            prompt = self._prompt_manager.get_prompt(name)
            if not prompt:
                raise PromptNotFoundError(f"Unknown prompt: {name}")

            messages = await prompt.render(arguments)

            return GetPromptResult(
                description=prompt.description,
                messages=pydantic_core.to_jsonable_python(messages),
            )
        except Exception as e:
            logger.exception(f"Error getting prompt {name}")
            raise PromptRenderError(str(e))

    async def run(
        self,
        read_stream: MemoryObjectReceiveStream[SessionMessage | Exception],
        write_stream: MemoryObjectSendStream[SessionMessage],
        initialization_options: InitializationOptions,
        # When False, exceptions are returned as messages to the client.
        # When True, exceptions are raised, which will cause the server to shut down
        # but also make tracing exceptions much easier during testing and when using
        # in-process servers.
        raise_exceptions: bool = False,
        # When True, the server is stateless and
        # clients can perform initialization with any node. The client must still follow
        # the initialization lifecycle, but can do so with any available node
        # rather than requiring initialization for each connection.
        stateless: bool = False,
    ):
        async with AsyncExitStack() as stack:
            lifespan_context = await stack.enter_async_context(self.lifespan(self))
            session = await stack.enter_async_context(
                DiscordMCPServerSession(
                    read_stream,
                    write_stream,
                    initialization_options,
                    stateless=stateless,
                )
            )

            async with anyio.create_task_group() as tg:
                async for message in session.incoming_messages:
                    logger.debug("Received message: %s", message)

                    tg.start_soon(
                        self._handle_message,
                        message,
                        session,
                        lifespan_context,
                        raise_exceptions,
                    )

    def _apply_middlewares(
        self, handler: CallNext[t.Any, t.Any]
    ) -> t.Callable[[MiddlewareContext[t.Any] | t.Any], t.Awaitable[t.Any]]:
        def make_wrapper(
            handler: CallNext[t.Any, t.Any],
        ) -> t.Callable[[MiddlewareContext[t.Any] | t.Any], t.Awaitable[t.Any]]:
            async def wrapper(ctx: MiddlewareContext[t.Any]) -> t.Any:
                return await handler(ctx.message)

            return wrapper

        chain = make_wrapper(handler)
        for mw in reversed(self.middlewares):
            chain = functools.partial(mw, call_next=chain)

        return chain

    async def _handle_request(
        self,
        message: RequestResponder[types.ClientRequest, types.ServerResult],
        req: t.Any,
        session: ServerSession,
        lifespan_context: DiscordMCPLifespanResult,
        raise_exceptions: bool,
    ):
        if handler := self.request_handlers.get(type(req)):  # type: ignore
            logger.debug("Dispatching request of type %s", type(req).__name__)

            token = None
            try:
                # Extract request context from message metadata
                request_data: Request | None = None
                if message.message_metadata is not None and isinstance(message.message_metadata, ServerMessageMetadata):
                    request_data = t.cast(Request | None, message.message_metadata.request_context)

                chain = self._apply_middlewares(handler)

                # Set our global state that can be retrieved via
                # app.get_request_context()
                token = request_ctx.set(
                    RequestContext(
                        message.request_id,
                        message.request_meta,
                        session,
                        lifespan_context or (request_data.state if request_data else None),
                        request=request_data,
                    )
                )
                response = await chain(req)
            except McpError as err:
                response = err.error
            except anyio.get_cancelled_exc_class():
                logger.info(
                    "Request %s cancelled - duplicate response suppressed",
                    message.request_id,
                )
                return
            except Exception as err:
                if raise_exceptions:
                    raise err
                response = types.ErrorData(
                    code=ErrorCodes.INTERNAL_ERROR,
                    message=f"An uncaught exception occurred while handling request {message.request_id}: {str(err)}",
                    data=None,
                )
            finally:
                # Reset the global state after we are done
                if token is not None:
                    request_ctx.reset(token)

            await message.respond(response)
        else:
            logger.warning("Method %s not found", type(req).__name__)
            await message.respond(
                types.ErrorData(
                    code=ErrorCodes.METHOD_NOT_FOUND,
                    message=f"Method {type(req).__name__} not found",
                )
            )

        logger.debug("Response sent")

    async def _handle_notification(  # type: ignore
        self,
        message: types.Notification[t.Any, t.Any],
        req: ServerMessageMetadata | ClientMessageMetadata | None,
        session: ServerSession,
        lifespan_context: DiscordMCPLifespanResult,
        raise_exceptions: bool = False,
    ) -> None:
        async def blank_handler(message: types.Notification[t.Any, t.Any]) -> None:
            """A blank handler that does nothing."""
            pass

        handler = self.notification_handlers.get(type(message), blank_handler)
        logger.debug("Dispatching notification of type %s", type(message).__name__)
        token = None
        try:
            request_id = None
            request_data: Request | None = None
            if req is not None and isinstance(req, ServerMessageMetadata):
                request_data = t.cast(Request | None, req.request_context)
                request_id = req.related_request_id

            token = request_ctx.set(
                RequestContext(
                    request_id or -1,  # Use -1 if no request_id is available
                    None,
                    session,
                    lifespan_context or (request_data.state if request_data else None),
                    request=request_data,
                )
            )
            chain = self._apply_middlewares(handler)
            await chain(message)
        except Exception as err:
            logger.exception(f"Error handling notification {type(message).__name__}: {err}")
            if raise_exceptions:
                raise err
        finally:
            # Reset the global state after we are done
            if token is not None:
                request_ctx.reset(token)

    async def _handle_message(
        self,
        message: RequestResponder[types.ClientRequest, types.ServerResult] | types.ClientNotification | Exception,
        session: ServerSession,
        lifespan_context: DiscordMCPLifespanResult,
        raise_exceptions: bool = False,
    ):
        logger.debug("Received message of type %s", type(message).__name__)
        with warnings.catch_warnings(record=True) as w:
            # TODO(Marcelo): We should be checking if message is Exception here.
            match message:  # type: ignore[reportMatchNotExhaustive]
                case RequestResponder(request=types.ClientRequest(root=req)) as responder:
                    with responder:
                        await self._handle_request(message, req, session, lifespan_context, raise_exceptions)
                case types.ClientNotification(root=notify):
                    await self._handle_notification(
                        notify, message.__dict__.get("metadata", None), session, lifespan_context, raise_exceptions
                    )

            for warning in w:
                logger.info("Warning: %s: %s", warning.category.__name__, warning.message)

    def _add_autocomplete_callback(self, manifest: ResourceManifest | PromptManifest) -> None:
        if manifest._autocomplete_handler._autocomplete_fns:  # type: ignore
            name = manifest.name if isinstance(manifest, PromptManifest) else manifest.uri
            self._autocomplete_callbacks[name] = manifest._autocomplete_handler  # type: ignore

    def _load_manifests(self, manifests: list[BaseManifest]) -> None:
        self._manifest_repository.add_manifests(manifests)
        for manifest in manifests:
            if isinstance(manifest, ToolManifest):
                if manifest.enabled:
                    self.add_tool(
                        fn=manifest.fn,
                        name=manifest.name,
                        title=manifest.title,
                        description=manifest.description,
                        annotations=manifest.annotations,
                        structured_output=manifest.structured_output,
                    )
            elif isinstance(manifest, ResourceManifest):
                # we use the decorator here to use the
                # validations that we have already defined
                if manifest.enabled:
                    self.resource(
                        uri=manifest.uri,
                        name=manifest.name,
                        title=manifest.title,
                        description=manifest.description,
                        mime_type=manifest.mime_type,
                    )(manifest.fn)
                    self._add_autocomplete_callback(manifest)
            elif isinstance(manifest, PromptManifest):
                if manifest.enabled:
                    self.prompt(
                        name=manifest.name,
                        title=manifest.title,
                        description=manifest.description,
                    )(manifest.fn)
                    self._add_autocomplete_callback(manifest)
            else:
                logger.warning(f"Unknown manifest type: {type(manifest).__name__}")

            logger.info(f"Manifest {manifest.name} loaded")

    def _load_plugin(self, name: str, *, package: str | None = None) -> None:
        mod = importlib.import_module(name, package)

        for member in inspect.getmembers(mod):
            if isinstance(member[1], DiscordMCPPluginManager):
                manager = member[1]
                self._load_manifests(manager._manifests)
                logger.info(f"Plugin {name} loaded with {len(manager._manifests)} manifests")
                break

    def _load_plugins(self, path: str) -> None:
        for plugin in search_directory(path):
            self._load_plugin(plugin)

    async def _autocomplete_base_handler(
        self,
        reference: PromptReference | ResourceTemplateReference,
        argument: CompletionArgument,
        context: CompletionContext | None = None,
    ) -> Completion:
        logger.info(
            f"Autocompleting for {reference.model_dump_json()} with argument {argument.model_dump_json()} and context {context.model_dump_json() if context else None}"
        )
        name = reference.name if isinstance(reference, PromptReference) else reference.uri
        if autocomplete_obj := self._autocomplete_callbacks.get(name):
            return await autocomplete_obj(reference, argument, context)
        return Completion(values=[])
