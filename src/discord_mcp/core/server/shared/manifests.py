from __future__ import annotations

import typing as t

from mcp.types import PromptReference, ResourceTemplateReference, ToolAnnotations

from discord_mcp.core.server.prompts import DiscordMCPPrompt
from discord_mcp.core.server.resources import DiscordMCPResourceTemplate
from discord_mcp.core.server.shared.autocomplete import AutoCompletable, AutocompleteHandler

__all__: tuple[str, ...] = (
    "BaseManifest",
    "ToolManifest",
    "ResourceManifest",
    "PromptManifest",
)


class BaseManifest:
    def __init__(
        self,
        fn: t.Callable[..., t.Any],
        name: str | None = None,
        title: str | None = None,
        description: str | None = None,
        enabled: bool = True,
    ) -> None:
        self.fn = fn
        self.name = name
        self.title = title
        self.description = description
        self.enabled = enabled

    def __call__(self, *_: t.Any, **__: t.Any) -> t.Any:
        raise NotImplementedError


class ToolManifest(BaseManifest):
    def __init__(
        self,
        fn: t.Callable[..., t.Any],
        name: str | None = None,
        title: str | None = None,
        description: str | None = None,
        annotations: ToolAnnotations | None = None,
        structured_output: bool | None = None,
        enabled: bool = True,
    ) -> None:
        super().__init__(fn, name, title, description, enabled)
        self.annotations = annotations
        self.structured_output = structured_output


class ResourceManifest(BaseManifest, AutoCompletable[DiscordMCPResourceTemplate, ResourceTemplateReference]):
    def __init__(
        self,
        fn: t.Callable[..., t.Any],
        uri: str,
        name: str | None = None,
        title: str | None = None,
        description: str | None = None,
        mime_type: str | None = None,
        enabled: bool = True,
    ) -> None:
        super().__init__(fn, name, title, description, enabled)
        self.uri = uri
        self.mime_type = mime_type
        self._autocomplete_handler = AutocompleteHandler(self)


class PromptManifest(BaseManifest, AutoCompletable[DiscordMCPPrompt, PromptReference]):
    def __init__(
        self,
        fn: t.Callable[..., t.Any],
        name: str | None = None,
        title: str | None = None,
        description: str | None = None,
        enabled: bool = True,
    ) -> None:
        super().__init__(fn, name, title, description, enabled)
        self.name = name or fn.__name__
        self._autocomplete_handler = AutocompleteHandler(self)
