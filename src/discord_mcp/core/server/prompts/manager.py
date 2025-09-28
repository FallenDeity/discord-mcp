from __future__ import annotations

import logging
import typing as t

import pydantic_core
from mcp.server.fastmcp.prompts import Prompt, PromptManager
from mcp.server.fastmcp.prompts.base import Message, PromptArgument, PromptResult, UserMessage, message_validator
from mcp.types import Icon, TextContent

from discord_mcp.core.server.shared.context import DiscordMCPContext, get_context
from discord_mcp.utils.checks import context_safe_validate_call, find_kwarg_by_type
from discord_mcp.utils.converters import (
    convert_name_to_title,
    convert_string_arguments,
    get_cached_typeadapter,
    process_callable_result,
    prune_param,
    transform_function_signature,
)
from discord_mcp.utils.exceptions import PromptRenderError

if t.TYPE_CHECKING:
    from mcp.server.fastmcp.server import Context
    from mcp.server.session import ServerSessionT
    from mcp.shared.context import LifespanContextT, RequestT


__all__: tuple[str, ...] = (
    "DiscordMCPPromptManager",
    "DiscordMCPPrompt",
)


logger = logging.getLogger(__name__)


class DiscordMCPPrompt(Prompt):
    @classmethod
    def from_function(
        cls,
        fn: t.Callable[..., PromptResult | t.Awaitable[PromptResult]],
        name: str | None = None,
        title: str | None = None,
        description: str | None = None,
        icons: list[Icon] | None = None,
        context_kwarg: str | None = None,
    ) -> DiscordMCPPrompt:
        """Create a Prompt from a function.

        The function can return:
        - A string (converted to a message)
        - A Message object
        - A dict (converted to a message)
        - A sequence of any of the above
        """
        func_name = name or fn.__name__

        if func_name == "<lambda>":
            raise ValueError("You must provide a name for lambda functions")

        fn = transform_function_signature(fn)

        context_kwarg = context_kwarg or find_kwarg_by_type(fn, DiscordMCPContext)

        # Get schema from TypeAdapter - will fail if function isn't properly typed
        parameters = get_cached_typeadapter(fn).json_schema()
        parameters = prune_param(parameters, param=context_kwarg) if context_kwarg else parameters

        # Convert parameters to PromptArguments
        arguments: list[PromptArgument] = []
        if "properties" in parameters:
            for param_name, param in parameters["properties"].items():
                required = param_name in parameters.get("required", [])
                arguments.append(
                    PromptArgument(
                        name=param_name,
                        description=param.get("description"),
                        required=required,
                    )
                )

        # ensure the arguments are properly cast
        validated_fn = context_safe_validate_call(fn)

        return cls(
            name=func_name,
            title=title if title else convert_name_to_title(func_name),
            description=description or fn.__doc__ or "",
            arguments=arguments,
            icons=icons,
            fn=validated_fn,
            context_kwarg=context_kwarg,
        )

    async def render(
        self,
        arguments: dict[str, t.Any] | None = None,
        context: Context[ServerSessionT, LifespanContextT, RequestT] | None = None,
    ) -> list[Message]:
        """Render the prompt with arguments."""
        # Validate required arguments
        arguments = arguments or {}

        if self.arguments:
            required = {arg.name for arg in self.arguments if arg.required}
            provided = set(arguments)
            missing = required - provided
            if missing:
                raise ValueError(f"Missing required arguments: {missing}")

        try:
            # Call function and check if result is a coroutine
            arguments |= {self.context_kwarg: context or get_context()} if self.context_kwarg else {}
            result = await process_callable_result(self.fn, convert_string_arguments(self.fn, arguments))

            # Validate messages
            if not isinstance(result, list | tuple):
                result = [result]

            # Convert result to messages
            messages: list[Message] = []
            for msg in result:  # type: ignore[reportUnknownVariableType]
                try:
                    if isinstance(msg, Message):
                        messages.append(msg)
                    elif isinstance(msg, dict):
                        messages.append(message_validator.validate_python(msg))
                    elif isinstance(msg, str):
                        content = TextContent(type="text", text=msg)
                        messages.append(UserMessage(content=content))
                    else:
                        content = pydantic_core.to_json(msg, fallback=str, indent=2).decode()
                        messages.append(Message(role="user", content=content))
                except Exception:
                    raise PromptRenderError(f"Could not convert prompt result to message: {msg}")

            return messages
        except Exception as e:
            raise PromptRenderError(f"Error rendering prompt {self.name}: {e}")


class DiscordMCPPromptManager(PromptManager): ...
