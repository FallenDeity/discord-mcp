from __future__ import annotations

import types
import typing as t

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
