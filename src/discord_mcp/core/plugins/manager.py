from __future__ import annotations

import functools
import inspect
import types
import typing as t

from mcp.types import CallToolRequest, GetPromptRequest, ReadResourceRequest, ToolAnnotations

from discord_mcp.core.plugins.cooldowns import (
    CooldownManager,
    FixedWindowRateLimiter,
    MovingWindowRateLimiter,
    RateLimiter,
    TokenBucketRateLimiter,
    get_bucket_key,
)
from discord_mcp.core.server.middleware import MiddlewareContext
from discord_mcp.core.server.shared.manifests import BaseManifest, PromptManifest, ResourceManifest, ToolManifest
from discord_mcp.utils.enums import RateLimitType

if t.TYPE_CHECKING:
    from discord_mcp.core.server.shared.context import DiscordMCPContext

__all__: tuple[str, ...] = (
    "DiscordMCPPluginManager",
    "ManifestT",
    "CoroFuncT",
    "PredicateRequestT",
    "PredicateT",
    "Check",
)

T = t.TypeVar("T", bound=t.Any)

ManifestT = t.TypeVar("ManifestT", bound=BaseManifest)
CoroFuncT = t.Coroutine[t.Any, t.Any, T]

PredicateRequestT = t.TypeVar("PredicateRequestT", bound=CallToolRequest | GetPromptRequest | ReadResourceRequest)
PredicateT = t.Callable[[MiddlewareContext[PredicateRequestT]], T]


class Check(t.Protocol[PredicateRequestT]):
    __predicate__: PredicateT[PredicateRequestT, CoroFuncT[bool]]

    def __call__(self, fn: T) -> T: ...


class DiscordMCPPluginManager:
    def __init__(self, name: str | None = None) -> None:
        self.name = name
        self._manifests: list[BaseManifest] = []

    @t.overload
    def _deco_helper(
        self,
        name_or_fn: t.Callable[..., t.Any],
        manifest_cls: type[ManifestT],
        **attrs: t.Any,
    ) -> ManifestT: ...

    @t.overload
    def _deco_helper(
        self,
        name_or_fn: str | None,
        manifest_cls: type[ManifestT],
        **attrs: t.Any,
    ) -> t.Callable[[t.Callable[..., t.Any]], ManifestT]: ...

    def _deco_helper(
        self,
        name_or_fn: t.Callable[..., t.Any] | str | None,
        manifest_cls: type[ManifestT],
        **attrs: t.Any,
    ) -> ManifestT | t.Callable[[t.Callable[..., t.Any]], ManifestT]:
        def callable_deco(fn: t.Callable[..., t.Any]) -> ManifestT:
            manifest = manifest_cls(
                fn=fn,
                **attrs,
            )
            self._manifests.append(manifest)
            return manifest

        if isinstance(name_or_fn, types.FunctionType):
            manifest = manifest_cls(fn=name_or_fn, **attrs)
            self._manifests.append(manifest)
            return manifest
        else:
            if isinstance(attrs.get("uri"), types.FunctionType):
                raise RuntimeError(
                    "Incorrect usage: You must call the resource decorator with required arguments, e.g. `@register_resource(uri=...)`. The 'uri' argument is not optional. Example:\n\n    @register_resource(uri='your_resource_uri')\n    def my_resource(...):\n        ...\n"
                )

            return callable_deco

    @t.overload
    def register_tool(
        self,
        name: t.Callable[..., t.Any] = ...,
    ) -> ToolManifest: ...

    @t.overload
    def register_tool(
        self,
        name: str | None = ...,
        title: str | None = ...,
        description: str | None = ...,
        annotations: ToolAnnotations | None = ...,
        structured_output: bool | None = ...,
    ) -> t.Callable[[t.Callable[..., t.Any]], ToolManifest]: ...

    def register_tool(
        self,
        name: t.Callable[..., t.Any] | str | None = None,
        title: str | None = None,
        description: str | None = None,
        annotations: ToolAnnotations | None = None,
        structured_output: bool | None = None,
    ) -> ToolManifest | t.Callable[[t.Callable[..., t.Any]], ToolManifest]:
        """Decorator to register a tool.

        Tools can optionally request a Context object by adding a parameter with the
        Context type annotation. The context provides access to MCP capabilities like
        logging, progress reporting, and resource access.

        If no args are passed they are determined by inspecting the signature of the function
        and the function docstrings.

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
            @register_tool()
            def my_tool(x: int) -> str:
                return str(x)

            @register_tool()
            def tool_with_context(x: int, ctx: Context) -> str:
                ctx.info(f"Processing {x}")
                return str(x)

            @register_tool
            async def async_tool(context: Context, x: int) -> str:
                await context.report_progress(50, 100)
                return str(x)
        """
        return self._deco_helper(
            name_or_fn=name,
            manifest_cls=ToolManifest,
            name=(name if not isinstance(name, types.FunctionType) else name.__name__),
            title=title,
            description=description,
            annotations=annotations,
            structured_output=structured_output,
        )

    def register_resource(
        self,
        uri: str,
        name: str | None = None,
        title: str | None = None,
        description: str | None = None,
        mime_type: str | None = None,
    ) -> t.Callable[[t.Callable[..., t.Any]], ResourceManifest]:
        """Decorator to register a function as a resource.

        The function will be called when the resource is read to generate its content.
        The function can return:
            - str for text content
            - bytes for binary content
            - other types will be converted to JSON

        If the URI contains parameters (e.g. "resource://{param}") or the function
        has parameters, it will be registered as a template resource.

        Resources can optionally request a Context object by adding a parameter with the
        Context type annotation. The context provides access to MCP capabilities like
        logging, progress reporting, and resource access.

        If no args are passed they are determined by inspecting the signature of the function
        and the function docstrings.

        Args:
            uri: URI for the resource (e.g. "resource://my-resource" or "resource://{param}")
            name: Optional name for the resource
            title: Optional human-readable title for the resource
            description: Optional description of the resource
            mime_type: Optional MIME type for the resource. If not passed it's automatically inferred from the return type hint.

        Example:
            @register_resource("resource://my-resource")
            def get_data() -> str:
                return "Hello, world!"

            @register_resource("resource://my-resource")
            async get_data() -> str:
                data = await fetch_data()
                return f"Hello, world! {data}"

            @register_resource("resource://{city}/weather")
            def get_weather(city: str) -> str:
                return f"Weather for {city}"

            @register_resource("resource://{city}/weather")
            async def get_weather(city: str) -> str:
                data = await fetch_weather(city)
                return f"Weather for {city}: {data}"
        """
        return self._deco_helper(
            name_or_fn=name,
            manifest_cls=ResourceManifest,
            name=name,
            title=title,
            description=description,
            mime_type=mime_type,
            uri=uri,
        )

    @t.overload
    def register_prompt(
        self,
        name: t.Callable[..., t.Any] = ...,
    ) -> PromptManifest: ...

    @t.overload
    def register_prompt(
        self,
        name: str | None = ...,
        title: str | None = None,
        description: str | None = None,
    ) -> t.Callable[[t.Callable[..., t.Any]], PromptManifest]: ...

    def register_prompt(
        self,
        name: t.Callable[..., t.Any] | str | None = None,
        title: str | None = None,
        description: str | None = None,
    ) -> PromptManifest | t.Callable[[t.Callable[..., t.Any]], PromptManifest]:
        """Decorator to register a prompt.

        Prompts can optionally request a Context object by adding a parameter with the
        Context type annotation. The context provides access to MCP capabilities like
        logging, progress reporting, and resource access.

        If no args are passed they are determined by inspecting the signature of the function
        and the function docstrings.

        Args:
            name: Optional name for the prompt (defaults to function name)
            title: Optional human-readable title for the prompt
            description: Optional description of what the prompt does

        Example:
            @register_prompt()
            def analyze_table(table_name: str) -> list[Message]:
                schema = read_table_schema(table_name)
                return [
                    {
                        "role": "user",
                        "content": f"Analyze this schema:\n{schema}"
                    }
                ]

            @register_prompt
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
        return self._deco_helper(
            name_or_fn=name,
            manifest_cls=PromptManifest,
            name=(name if not isinstance(name, types.FunctionType) else name.__name__),
            title=title,
            description=description,
        )

    @staticmethod
    def limit(
        ratelimiter_or_type: type[RateLimiter] | RateLimitType,
        rate: int,
        per: float,
        get_bucket_key: t.Callable[[DiscordMCPContext], t.Hashable] = get_bucket_key,
    ) -> t.Callable[[t.Callable[..., t.Any]], t.Callable[..., t.Any]]:
        """
        Decorator to apply rate limiting to a function.
        This decorator adds rate limiting functionality to any function by attaching a
        CooldownManager instance. The rate limiter controls how frequently the decorated
        function can be called based on the specified parameters.
        Args:
            ratelimiter_or_type (type[RateLimiter] | RateLimitType): Either a RateLimitType
                enum value (FIXED_WINDOW, TOKEN_BUCKET, MOVING_WINDOW) or a custom
                RateLimiter subclass.
            rate (int): The maximum number of calls allowed within the time window.
            per (float): The time window duration in seconds.
            get_bucket_key (Callable[[DiscordMCPContext], Hashable], optional): A function
                that takes a DiscordMCPContext and returns a hashable key for bucketing
                rate limits. Defaults to the global get_bucket_key function.
        Returns:
            Callable: A decorator function that can be applied to any callable to add
            rate limiting functionality.
        Raises:
            ValueError: If ratelimiter_or_type is neither a valid RateLimitType enum
                nor a RateLimiter subclass.
        Example:
            @manager.limit(RateLimitType.FIXED_WINDOW, rate=5, per=60.0)
            def my_function():
                pass
            @manager.limit(CustomRateLimiter, rate=10, per=30.0)
            def another_function():
                pass
        """
        _limiter_map: dict[RateLimitType, t.Type[RateLimiter]] = {
            RateLimitType.FIXED_WINDOW: FixedWindowRateLimiter,
            RateLimitType.TOKEN_BUCKET: TokenBucketRateLimiter,
            RateLimitType.MOVING_WINDOW: MovingWindowRateLimiter,
        }

        def decorator(fn: t.Callable[..., t.Any]) -> t.Callable[..., t.Any]:
            if isinstance(ratelimiter_or_type, RateLimitType) and ratelimiter_or_type in _limiter_map:
                _limiter_cls = _limiter_map[ratelimiter_or_type]
            elif isinstance(ratelimiter_or_type, type) and issubclass(ratelimiter_or_type, RateLimiter):  # type: ignore
                _limiter_cls = ratelimiter_or_type
            else:
                raise ValueError(
                    f"ratelimiter_or_type must be a RateLimitType enum or a RateLimiter subclass, got {ratelimiter_or_type.__class__.__name__!r}."
                )
            setattr(fn, "__cooldown_manager__", CooldownManager(_limiter_cls(rate, per), get_bucket_key))
            return fn

        return decorator

    @staticmethod
    def check(predicate: PredicateT[PredicateRequestT, CoroFuncT[bool] | bool]) -> Check[PredicateRequestT]:
        """
        A decorator that adds a predicate check to a function.
        This decorator allows you to attach predicate functions to other functions,
        which can be used for validation or authorization purposes. The predicate
        can be either synchronous or asynchronous.
        Args:
            predicate (PredicateT): A callable that takes a MiddlewareContext
                and returns a boolean or awaitable boolean.  The predicate is wrapped
                in a coroutine to ensure consistent behavior.
        Returns:
            Callable: A decorator function that can be applied to other functions
                to add the predicate check.
        Example:
            ```python
            def has_bot(ctx):
                return ctx.context.bot.user is not None
            @manager.check(has_bot)
            def bot_command():
                pass
            ```
        Note:
            The decorated function will have a `__checks__` attribute containing
            a list of all applied predicates, and the decorator itself will have
            a `__predicate__` attribute containing the (possibly wrapped) predicate.
            This can be used for extending already defined checks.
        """

        @functools.wraps(predicate)
        async def wrapped_predicate(context: MiddlewareContext[PredicateRequestT]) -> bool:
            if inspect.iscoroutinefunction(predicate):
                return await predicate(context)
            return t.cast(bool, predicate(context))

        def decorator(fn: t.Callable[..., t.Any]) -> t.Callable[..., t.Any]:
            if not hasattr(fn, "__checks__"):
                setattr(fn, "__checks__", [])
            getattr(fn, "__checks__").append(wrapped_predicate)
            return fn

        setattr(decorator, "__predicate__", wrapped_predicate)

        return decorator  # type: ignore
