from __future__ import annotations

import asyncio
import typing as t

from mcp.types import (
    Completion,
    CompletionArgument,
    CompletionContext,
    PromptReference,
    ResourceTemplateReference,
)

from discord_mcp.core.server.prompts.manager import DiscordMCPPrompt
from discord_mcp.core.server.resources.manager import DiscordMCPResourceTemplate
from discord_mcp.core.server.shared.context import DiscordMCPContext, get_context
from discord_mcp.utils.checks import autocomplete_validate_argument_name, autocomplete_validate_resource_template
from discord_mcp.utils.converters import convert_string_arguments

if t.TYPE_CHECKING:
    from discord_mcp.core.server.shared.manifests import PromptManifest, ResourceManifest

__all__: tuple[str, ...] = (
    "AutoCompletable",
    "AutocompleteHandler",
)

AutocompleteCallback = t.Callable[
    [DiscordMCPPrompt | DiscordMCPResourceTemplate, t.Any, dict[str, t.Any] | None],
    t.Any,
]


# mixin to be used in conjunction to AutocompleteHandler
class AutoCompletable:
    autocomplete_handler: AutocompleteHandler

    def autocomplete(self, argument_name: str) -> t.Callable[[AutocompleteCallback], AutocompleteCallback]:
        """Provides completions for prompts and resource templates.

        The decorated function must take exactly 3 arguments:
            - a ``reference`` which has the type `DiscordMCPPrompt` | `DiscordMCPResourceTemplate`
            - an ``argument`` which has the type of the autocompleted argument
            - a ``context`` which has the type of `dict[str, Any]`

        Note:
            The return type can be any, it is wrapped internally. If you want to override this behaviour
            you just need to return a `mcp.types.Completion` object. All the other objects are automatically
            wrapped.

        Note:
            The ``argument`` parameter contains the user input casted to python a python object. The same applies
            for ``context``.
            It is important that the autocompleted argument in the parent function has the correct type hint
            for the value cast to work correctly.

        Args:
            argument_name: The name of the argument to autocomplete.
        """
        return self.autocomplete_handler.autocomplete(argument_name)


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
            ref_id = f"name='{reference.name}'" if isinstance(reference, PromptReference) else f"uri='{reference.uri}'"
            raise RuntimeError(
                f"An autocomplete for an unregistered prompt or template has been called (reference: {ref_id})."
            ) from e

        promoted_argument_value = convert_string_arguments(promoted.fn, {argument.name: argument.value})[argument.name]
        if context and context.arguments:
            promoted_context_args = convert_string_arguments(promoted.fn, context.arguments)
        else:
            promoted_context_args = None

        if argument.name in self._autocomplete_fns:
            result = self._autocomplete_fns[argument.name](promoted, promoted_argument_value, promoted_context_args)
        else:
            raise RuntimeError(
                f"No autocomplete callback registered for argument '{argument.name}' in {promoted.name}!"
            )

        if asyncio.iscoroutine(result):
            return self.wrap_result(await result)
        else:
            return self.wrap_result(result)

    def autocomplete(self, argument_name: str) -> t.Callable[[AutocompleteCallback], AutocompleteCallback]:
        """Provides completions for prompts and resource templates"""
        from .manifests import ResourceManifest

        def decorator(fn: AutocompleteCallback) -> AutocompleteCallback:
            if isinstance(self.manifest, ResourceManifest):
                autocomplete_validate_resource_template(self.manifest.fn, self.manifest.uri)
            autocomplete_validate_argument_name(self.manifest.fn, argument_name)
            self._autocomplete_fns[argument_name] = fn
            return fn

        return decorator
