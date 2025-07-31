from __future__ import annotations

import types
import typing as t

from mcp.types import ToolAnnotations

from discord_mcp.utils.enums import DiscordMCPFunctionType
from discord_mcp.utils.injections import inject_function


def deco_helper(
    name_or_fn: t.Callable[..., t.Any] | str | None,
    **attrs: t.Any,
) -> t.Callable[..., t.Any]:
    def callable_deco(fn: t.Callable[..., t.Any]) -> t.Callable[..., t.Any]:
        inject_function(fn, attrs)
        return fn

    if isinstance(name_or_fn, types.FunctionType):
        # these will all be None for tools registered using
        # @register_tool
        inject_function(name_or_fn, attrs)
        return name_or_fn
    else:
        return callable_deco


@t.overload
def register_tool(
    name: t.Callable[..., t.Any] = ...,
) -> t.Callable[..., t.Any]: ...


@t.overload
def register_tool(
    name: str | None = ...,
    title: str | None = ...,
    description: str | None = ...,
    annotations: ToolAnnotations | None = ...,
    structured_output: bool | None = ...,
) -> t.Callable[..., t.Any]: ...


def register_tool(
    name: t.Callable[..., t.Any] | str | None = None,
    title: str | None = None,
    description: str | None = None,
    annotations: ToolAnnotations | None = None,
    structured_output: bool | None = None,
) -> t.Callable[..., t.Any]:
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
    return deco_helper(
        name_or_fn=name,
        type=DiscordMCPFunctionType.TOOL,
        name=(name if not isinstance(name, types.FunctionType) else name.__name__),
        title=title,
        description=description,
        annotations=annotations,
        structured_output=structured_output,
    )


def register_resource(
    uri: str,
    name: str | None = None,
    title: str | None = None,
    description: str | None = None,
    mime_type: str | None = None,
) -> t.Callable[..., t.Any]:
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
    return deco_helper(
        name_or_fn=name,
        type=DiscordMCPFunctionType.RESOURCE,
        name=name,
        title=title,
        description=description,
        mime_type=mime_type,
        uri=uri,
    )


@t.overload
def register_prompt(
    name: t.Callable[..., t.Any] = ...,
) -> t.Callable[..., t.Any]: ...


@t.overload
def register_prompt(
    name: str | None = ...,
    title: str | None = None,
    description: str | None = None,
) -> t.Callable[..., t.Any]: ...


def register_prompt(
    name: t.Callable[..., t.Any] | str | None = None,
    title: str | None = None,
    description: str | None = None,
) -> t.Callable[..., t.Any]:
    """Decorator to register a prompt.

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
    return deco_helper(
        name_or_fn=name,
        type=DiscordMCPFunctionType.PROMPT,
        name=(name if not isinstance(name, types.FunctionType) else name.__name__),
        title=title,
        description=description,
    )
