from __future__ import annotations

import typing as t

from mcp.types import (
    Completion,
    CompletionArgument,
    CompletionContext,
    PromptReference,
    ResourceTemplateReference,
    ToolAnnotations,
)

from discord_mcp.utils.checks import autocomplete_validate_argument_name, autocomplete_validate_resource_template

__all__: tuple[str, ...] = (
    "BaseManifest",
    "ToolManifest",
    "ResourceManifest",
    "PromptManifest",
)

AutocompleteCallback = t.Callable[
    [PromptReference | ResourceTemplateReference, CompletionArgument, CompletionContext | None], Completion
]


class BaseManifest:
    def __init__(
        self,
        fn: t.Callable[..., t.Any],
        name: str | None = None,
        title: str | None = None,
        description: str | None = None,
    ) -> None:
        self.fn = fn
        self.name = name
        self.title = title
        self.description = description

    def __call__(self, *_: t.Any, **__: t.Any) -> t.Any:
        raise NotImplementedError


class AutoCompletable:
    autocomplete_fn: AutocompleteCallback

    def autocomplete(self, argument_name: str) -> t.Callable[[AutocompleteCallback], AutocompleteCallback]:
        def decorator(fn: AutocompleteCallback) -> AutocompleteCallback:
            autocomplete_validate_argument_name(fn, argument_name)
            self.autocomplete_fn = fn
            return fn

        return decorator


class ToolManifest(BaseManifest):
    def __init__(
        self,
        fn: t.Callable[..., t.Any],
        name: str | None = None,
        title: str | None = None,
        description: str | None = None,
        annotations: ToolAnnotations | None = None,
        structured_output: bool | None = None,
    ) -> None:
        super().__init__(fn, name, title, description)
        self.annotations = annotations
        self.structured_output = structured_output


class ResourceManifest(BaseManifest, AutoCompletable):
    def __init__(
        self,
        fn: t.Callable[..., t.Any],
        uri: str,
        name: str | None = None,
        title: str | None = None,
        description: str | None = None,
        mime_type: str | None = None,
    ) -> None:
        super().__init__(fn, name, title, description)
        self.uri = uri
        self.mime_type = mime_type

    def autocomplete(self, argument_name: str) -> t.Callable[..., t.Any]:
        def decorator(fn: t.Callable[..., t.Any]) -> t.Callable[..., t.Any]:
            autocomplete_validate_resource_template(fn, self.uri)
            autocomplete_validate_argument_name(fn, argument_name)
            self.autocomplete_fn = fn
            return fn

        return decorator


class PromptManifest(BaseManifest, AutoCompletable): ...
