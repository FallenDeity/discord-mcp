from __future__ import annotations

import logging
import typing as t

from mcp.server.fastmcp.tools import Tool, ToolManager
from mcp.types import ToolAnnotations

from discord_mcp.core.server.common.context import DiscordMCPContext
from discord_mcp.utils.checks import find_kwarg_by_type
from discord_mcp.utils.converters import convert_name_to_title, transform_function_signature

__all__: tuple[str, ...] = (
    "DiscordMCPTool",
    "DiscordMCPToolManager",
)


logger = logging.getLogger(__name__)


class DiscordMCPTool(Tool):
    @classmethod
    def from_function(
        cls,
        fn: t.Callable[..., t.Any],
        *args: t.Any,
        **kwargs: t.Any,
    ) -> DiscordMCPTool:
        # Allow reading typehints and param doc strings from the function docstring.
        fn = transform_function_signature(fn)
        tool = super().from_function(*args, fn=fn, context_kwarg=find_kwarg_by_type(fn, DiscordMCPContext), **kwargs)
        tool.title = tool.title or convert_name_to_title(tool.name)
        return t.cast(DiscordMCPTool, tool)


class DiscordMCPToolManager(ToolManager):
    def add_tool(
        self,
        fn: t.Callable[..., t.Any],
        name: str | None = None,
        title: str | None = None,
        description: str | None = None,
        annotations: ToolAnnotations | None = None,
        structured_output: bool | None = None,
    ) -> Tool:
        tool = DiscordMCPTool.from_function(
            fn,
            name=name,
            title=title,
            description=description,
            annotations=annotations,
            structured_output=structured_output,
        )
        existing = self._tools.get(tool.name)
        if existing:
            if self.warn_on_duplicate_tools:
                logger.warning(f"Tool already exists: {tool.name}")
            return existing
        self._tools[tool.name] = tool
        return tool
