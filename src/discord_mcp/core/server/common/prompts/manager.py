from __future__ import annotations

import inspect
import logging
import typing as t

import pydantic_core
from mcp.server.fastmcp.prompts import Prompt, PromptManager
from mcp.server.fastmcp.prompts.base import Message, PromptArgument, PromptResult, UserMessage, message_validator
from mcp.types import TextContent

from discord_mcp.core.server.common.context import DiscordMCPContext, get_context
from discord_mcp.utils.checks import context_safe_validate_call, find_kwarg_by_type
from discord_mcp.utils.converters import (
    convert_name_to_title,
    get_cached_typeadapter,
    process_callable_result,
    prune_param,
    transform_function_signature,
)
from discord_mcp.utils.exceptions import PromptError

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

        context_kwarg = find_kwarg_by_type(fn, DiscordMCPContext)

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
            fn=validated_fn,
        )

    def _convert_string_arguments(self, kwargs: dict[str, t.Any]) -> dict[str, t.Any]:
        """Convert string arguments to expected types based on function signature."""

        sig = inspect.signature(self.fn)
        converted_kwargs: dict[str, t.Any] = {}

        # Find context parameter name if any
        context_param_name = find_kwarg_by_type(self.fn, DiscordMCPContext)

        for param_name, param_value in kwargs.items():
            if param_name in sig.parameters:
                param = sig.parameters[param_name]

                # Skip Context parameters - they're handled separately
                if param_name == context_param_name:
                    converted_kwargs[param_name] = param_value
                    continue

                # If parameter has no annotation or annotation is str, pass as-is
                if param.annotation == inspect.Parameter.empty or param.annotation is str:
                    converted_kwargs[param_name] = param_value
                # If argument is not a string, pass as-is (already properly typed)
                elif not isinstance(param_value, str):
                    converted_kwargs[param_name] = param_value
                else:
                    # Try to convert string argument using type adapter
                    try:
                        adapter = get_cached_typeadapter(param.annotation)
                        # Try JSON parsing first for complex types
                        try:
                            converted_kwargs[param_name] = adapter.validate_json(param_value)
                        except (ValueError, TypeError, pydantic_core.ValidationError):
                            # Fallback to direct validation
                            converted_kwargs[param_name] = adapter.validate_python(param_value)
                    except (ValueError, TypeError, pydantic_core.ValidationError) as e:
                        # If conversion fails, provide informative error
                        raise PromptError(
                            f"Could not convert argument '{param_name}' with value '{param_value}' "
                            f"to expected type {param.annotation}. Error: {e}"
                        )
            else:
                # Parameter not in function signature, pass as-is
                converted_kwargs[param_name] = param_value

        return converted_kwargs

    async def render(self, arguments: dict[str, t.Any] | None = None) -> list[Message]:
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
            context_kwarg = find_kwarg_by_type(self.fn, DiscordMCPContext)
            arguments |= {context_kwarg: get_context()} if context_kwarg else {}
            result = await process_callable_result(self.fn, self._convert_string_arguments(arguments))

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
                    raise PromptError(f"Could not convert prompt result to message: {msg}")

            return messages
        except Exception as e:
            raise PromptError(f"Error rendering prompt {self.name}: {e}")


class DiscordMCPPromptManager(PromptManager): ...
