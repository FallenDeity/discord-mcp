from __future__ import annotations

import asyncio
import typing as t

from mcp.types import (
    Completion,
    CompletionArgument,
    CompletionContext,
    PromptReference,
    ResourceTemplateReference,
    ToolAnnotations,
)

from discord_mcp.core.server.common.context import DiscordMCPContext, get_context
from discord_mcp.core.server.common.prompts.manager import DiscordMCPPrompt
from discord_mcp.core.server.common.resources.manager import DiscordMCPResourceTemplate
from discord_mcp.utils.checks import autocomplete_validate_argument_name, autocomplete_validate_resource_template

__all__: tuple[str, ...] = (
    "BaseManifest",
    "ToolManifest",
    "ResourceManifest",
    "PromptManifest",
)

AutocompleteCallback = t.Callable[
    [DiscordMCPPrompt | DiscordMCPResourceTemplate, CompletionArgument, CompletionContext | None],
    t.Any,
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


class AutocompleteHandler:
    def __init__(self, manifest: PromptManifest | ResourceManifest) -> None:
        self.manifest = manifest
        self._autocomplete_fns: dict[str, AutocompleteCallback] = dict()

    def wrap_result(self, result: t.Any) -> Completion:
        if isinstance(result, Completion):
            return result
        elif isinstance(result, (list, tuple, set)):
            return Completion(values=list(map(str, result)))  # type: ignore
        elif isinstance(result, dict):
            return Completion(values=list(map(str, result.values())))  # type: ignore
        else:
            return Completion(values=[str(result)])

    def promote_reference_to_type(
        self,
        reference: PromptReference | ResourceTemplateReference,
        mcp_context: DiscordMCPContext,
    ) -> DiscordMCPPrompt | DiscordMCPResourceTemplate:
        if isinstance(reference, PromptReference):
            return t.cast(DiscordMCPPrompt, mcp_context.mcp_server._prompt_manager._prompts[reference.name])
        else:
            return t.cast(
                DiscordMCPResourceTemplate, mcp_context.mcp_server._resource_manager._templates[reference.uri]
            )

    async def __call__(
        self,
        reference: PromptReference | ResourceTemplateReference,
        argument: CompletionArgument,
        context: CompletionContext | None,
    ) -> Completion:
        mcp_context = get_context()

        try:
            promoted = self.promote_reference_to_type(reference, mcp_context)
        except KeyError as e:
            # normally should never happen if you don't play at removing
            # handler from the managers at runtime
            raise RuntimeError("An autocomplete for an unregistered prompt or template has been called!") from e

        if self._autocomplete_fns:
            result = self._autocomplete_fns[argument.name](promoted, argument, context)
        else:
            raise RuntimeError(f"autocomplete callback is `None` for {promoted.name}!")

        if asyncio.iscoroutine(result):
            return self.wrap_result(await result)
        else:
            return self.wrap_result(result)

    def autocomplete(self, argument_name: str) -> t.Callable[[AutocompleteCallback], AutocompleteCallback]:
        """Provides completions for prompts and resource templates"""

        def decorator(fn: AutocompleteCallback) -> AutocompleteCallback:
            if isinstance(self.manifest, ResourceManifest):
                autocomplete_validate_resource_template(self.manifest.fn, self.manifest.uri)
            autocomplete_validate_argument_name(self.manifest.fn, argument_name)
            self._autocomplete_fns[argument_name] = fn
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


class ResourceManifest(BaseManifest):
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
        self.autocomplete_handler = AutocompleteHandler(self)
        self.autocomplete_handler.autocomplete = self.autocomplete

    @property
    def autocomplete(self):
        return self.autocomplete_handler.autocomplete


class PromptManifest(BaseManifest):
    def __init__(
        self,
        fn: t.Callable[..., t.Any],
        name: str | None = None,
        title: str | None = None,
        description: str | None = None,
    ) -> None:
        super().__init__(fn, name, title, description)
        self.name = name or fn.__name__
        self.autocomplete_handler = AutocompleteHandler(self)

    @property
    def autocomplete(self):
        return self.autocomplete_handler.autocomplete
