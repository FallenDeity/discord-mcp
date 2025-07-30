from __future__ import annotations

import types
import typing as t

from mcp.types import ToolAnnotations

from discord_mcp.utils.enums import DiscordMCPFunctionType
from discord_mcp.utils.injections import inject_function


class BaseAttrs(t.TypedDict):
    name: t.Callable[..., t.Any] | str | None
    title: str | None
    description: str | None


class ToolAttrs(BaseAttrs):
    annotations: ToolAnnotations | None
    structured_output: bool | None


class ResourceAttrs(BaseAttrs):
    mime_type: str | None


class PromptAttrs(BaseAttrs): ...


AnyMCPAttrs = type[ToolAttrs] | type[ResourceAttrs] | type[PromptAttrs]


@t.overload
def registry_factory(
    registry_type: t.Literal[DiscordMCPFunctionType.TOOL], attrs: AnyMCPAttrs
) -> t.Callable[..., t.Any]: ...


@t.overload
def registry_factory(
    registry_type: t.Literal[DiscordMCPFunctionType.RESOURCE], attrs: AnyMCPAttrs
) -> t.Callable[..., t.Any]: ...


@t.overload
def registry_factory(
    registry_type: t.Literal[DiscordMCPFunctionType.PROMPT], attrs: AnyMCPAttrs
) -> t.Callable[..., t.Any]: ...


def registry_factory(registry_type: DiscordMCPFunctionType, attrs: AnyMCPAttrs) -> t.Callable[..., t.Any]:
    @t.overload
    def register(
        name: t.Callable[..., t.Any],
    ) -> t.Callable[..., t.Any]: ...

    @t.overload
    def register(
        name: str | None = ...,
        **kwargs: AnyMCPAttrs,
    ) -> t.Callable[..., t.Any]: ...

    def register(
        name: t.Callable[..., t.Any] | str | None = None,
        **kwargs: AnyMCPAttrs,
    ) -> t.Callable[..., t.Any]:
        attrs_: dict[str, t.Any] = {
            "type": registry_type,
        }

        # set default values
        for k in attrs.__annotations__.keys():
            attrs_[k] = None

        for k, v in kwargs.items():
            attrs_[k] = v

        def callable_deco(fn: t.Callable[..., t.Any]) -> t.Callable[..., t.Any]:
            inject_function(fn, attrs_)
            return fn

        if isinstance(name, types.FunctionType):
            # these will all be None for tools registered using
            # @register_tool
            inject_function(name, attrs_)
            return name
        else:
            return callable_deco

    return register


register_tool = registry_factory(
    DiscordMCPFunctionType.TOOL,
    attrs=ToolAttrs,
)
register_resource = registry_factory(
    DiscordMCPFunctionType.RESOURCE,
    attrs=ResourceAttrs,
)
register_prompt = registry_factory(
    DiscordMCPFunctionType.PROMPT,
    attrs=PromptAttrs,
)
