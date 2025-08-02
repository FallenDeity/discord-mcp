from __future__ import annotations

import types
import typing as t

from mcp.types import ToolAnnotations

from discord_mcp.core.server.common.manifests import BaseManifest, PromptManifest, ResourceManifest, ToolManifest

ManifestT = t.TypeVar("ManifestT", bound=BaseManifest)
AnyManifest = ToolManifest | ResourceManifest | PromptManifest


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
